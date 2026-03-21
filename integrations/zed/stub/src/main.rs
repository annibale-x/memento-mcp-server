//! memento-stub — Native MCP launcher for the mcp-memento Zed extension.
//!
//! ## FAST PATH (venv already valid)
//!   exec() Python directly with inherited stdio. Zero overhead.
//!
//! ## SLOW PATH (first install / upgrade / concurrent launch)
//!
//!   The process that receives stdin from Zed is the ACTIVE process.
//!   It must BOTH serve MCP responses to Zed AND wait for setup.
//!
//!   1. Try to acquire the setup lock (flock LOCK_EX|LOCK_NB on a file).
//!      - If acquired → spawn setup thread (venv + pip).
//!      - If not acquired → poll venv_is_valid() every 300ms; retries flock
//!        every 2s to detect a dead owner (kernel releases flock on SIGKILL).
//!
//!   2. Bootstrap MCP server loop (always runs in the ACTIVE process):
//!      - Reader thread feeds lines from Zed's stdin into a channel.
//!      - Main loop responds to initialize / tools/list / ping etc.
//!      - ALL messages are BUFFERED (preserved for replay).
//!      - Every 300ms checks if setup is Done/Failed.
//!
//!   3. When setup is Done:
//!      - Spawn Python with PIPED stdin/stdout.
//!      - Replay every buffered message into Python's stdin.
//!      - Proxy loop: Zed stdin → Python stdin, Python stdout → Zed stdout.
//!      - Python handles the real session; stub exits when Python exits.
//!
//!   This eliminates every race condition:
//!   - The active process (with live Zed stdin) always does the handoff.
//!   - No bytes are lost: initialize + everything else is replayed.
//!   - Python sees a clean ordered message stream.
//!   - Zed never sees silence or a dead process.

use std::env;
use std::fs;
use std::io::{self, BufRead, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc::{self, Receiver, SyncSender};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::Duration;

#[cfg(unix)]
use std::os::unix::process::CommandExt;

// ---------------------------------------------------------------------------
// Version — must match STUB_EXT_RELEASE in lib.rs
// ---------------------------------------------------------------------------

const STUB_VERSION: &str = "v0.2.29";

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

macro_rules! log {
    ($($arg:tt)*) => {{
        use std::io::Write as _;
        let msg = format!($($arg)*);
        let _ = writeln!(std::io::stderr(), "[MEMENTO-STUB] {}", msg);
        if let Ok(mut f) = std::fs::OpenOptions::new()
            .create(true).append(true)
            .open(std::env::temp_dir().join("memento_stub_debug.log"))
        {
            let _ = writeln!(f, "{}", msg);
        }
    }};
}

// ---------------------------------------------------------------------------
// Python discovery
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
fn python_candidates() -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = Vec::new();

    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "default" {
            v.push(PathBuf::from(cmd));
        }
    }

    v.push(PathBuf::from("py.exe"));
    v.push(PathBuf::from("python.exe"));
    v.push(PathBuf::from("python3.exe"));

    if let Ok(local) = env::var("LOCALAPPDATA") {
        let base = Path::new(&local).join("Programs").join("Python");
        if let Ok(rd) = std::fs::read_dir(&base) {
            let mut dirs: Vec<_> = rd.flatten().collect();
            dirs.sort_by(|a, b| b.file_name().cmp(&a.file_name()));
            for entry in dirs {
                let exe = entry.path().join("python.exe");
                if exe.exists() {
                    v.push(exe);
                }
            }
        }
    }

    v
}

#[cfg(not(target_os = "windows"))]
fn python_candidates() -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = Vec::new();

    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "default" {
            v.push(PathBuf::from(cmd));
        }
    }

    v.push(PathBuf::from("python3"));
    v.push(PathBuf::from("python"));

    for prefix in &[
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/bin",
        "/opt/local/bin",
    ] {
        v.push(PathBuf::from(prefix).join("python3"));
        v.push(PathBuf::from(prefix).join("python"));
    }

    v
}

fn find_python() -> Option<PathBuf> {
    for candidate in python_candidates() {
        let ok = Command::new(&candidate)
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);

        if ok {
            log!("Found Python: {}", candidate.display());
            return Some(candidate);
        }
    }

    None
}

// ---------------------------------------------------------------------------
// Venv helpers
// ---------------------------------------------------------------------------

fn venv_dir() -> PathBuf {
    if let Ok(work) = env::var("MEMENTO_WORK_DIR") {
        if !work.is_empty() {
            return PathBuf::from(work).join("venv");
        }
    }

    let mut dir = env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("."))
        .parent()
        .unwrap_or(Path::new("."))
        .to_path_buf();
    dir.push("venv");
    dir
}

#[cfg(target_os = "windows")]
fn venv_python(venv: &Path) -> PathBuf {
    venv.join("Scripts").join("python.exe")
}

#[cfg(not(target_os = "windows"))]
fn venv_python(venv: &Path) -> PathBuf {
    venv.join("bin").join("python")
}

fn marker_path(venv: &Path) -> PathBuf {
    venv.join("memento_version.txt")
}

/// Dev-mode sentinel data read from `local_wheel.txt`.
/// Written by `scripts/deploy.py rebuild` as "<path>:<sha256[:12]>".
/// The full raw string (path+hash) is used as the venv marker fingerprint,
/// so any rebuild that changes the wheel content invalidates the venv.
struct LocalWheel {
    /// Absolute path to the .whl file — passed to pip install.
    path: String,
    /// Raw sentinel string (path:hash or just path) — used as marker key.
    fingerprint: String,
}

fn local_wheel_path(venv: &Path) -> Option<LocalWheel> {
    let sentinel = venv.parent().unwrap_or(venv).join("local_wheel.txt");
    match fs::read_to_string(&sentinel) {
        Ok(s) => {
            let trimmed = s.trim().to_string();
            if trimmed.is_empty() {
                return None;
            }
            // Format: "<path>|<hash>"  (pipe separator — safe on all platforms).
            // Legacy format "<path>" (no separator) is also accepted.
            // NOTE: we do NOT split on ':' because Windows drive letters
            // (e.g. "C:/foo") contain a colon and would be mis-parsed.
            let path = if let Some((p, _)) = trimmed.split_once('|') {
                p.to_string()
            } else {
                trimmed.clone()
            };
            Some(LocalWheel {
                path,
                fingerprint: trimmed,
            })
        }
        Err(_) => None,
    }
}

fn lock_path(venv: &Path) -> PathBuf {
    venv.parent().unwrap_or(venv).join("memento_setup.lock")
}

fn expected_marker() -> String {
    let venv = venv_dir();
    match local_wheel_path(&venv) {
        Some(w) => format!("{}+local:{}", STUB_VERSION, w.fingerprint),
        None => STUB_VERSION.to_string(),
    }
}

fn venv_is_valid(venv: &Path) -> bool {
    if !venv_python(venv).exists() {
        return false;
    }

    let expected = expected_marker();
    match fs::read_to_string(marker_path(venv)) {
        Ok(c) if c.trim() == expected => true,
        Ok(c) => {
            log!(
                "Venv version mismatch: marker='{}' expected='{}'.",
                c.trim(),
                expected
            );
            false
        }
        Err(_) => false,
    }
}

// ---------------------------------------------------------------------------
// flock-based setup lock
//
// We use an advisory LOCK_EX flock on the lockfile. The kernel automatically
// releases the lock when the owning process dies (even via SIGKILL), so there
// are no stale-PID zombies to deal with. The File handle must be kept alive
// for the duration of ownership.
// ---------------------------------------------------------------------------

#[cfg(unix)]
fn try_flock_exclusive(file: &fs::File) -> bool {
    use std::os::unix::io::AsRawFd;

    let fd = file.as_raw_fd();
    let ret = unsafe { libc::flock(fd, libc::LOCK_EX | libc::LOCK_NB) };
    ret == 0
}

#[cfg(windows)]
fn try_flock_exclusive(file: &fs::File) -> bool {
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::Foundation::HANDLE;
    use windows_sys::Win32::Storage::FileSystem::{
        LockFileEx, LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY,
    };
    use windows_sys::Win32::System::IO::OVERLAPPED;

    let handle = file.as_raw_handle() as HANDLE;
    let mut overlapped: OVERLAPPED = unsafe { std::mem::zeroed() };
    let flags = LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY;
    let ret = unsafe { LockFileEx(handle, flags, 0, 1, 0, &mut overlapped) };
    ret != 0
}

#[cfg(not(any(unix, windows)))]
fn try_flock_exclusive(_file: &fs::File) -> bool {
    // Unknown platform — optimistically assume we own the lock.
    true
}

/// Try to atomically acquire the setup lock (non-blocking flock).
/// Returns (file_handle, true) if we own the lock, (file_handle, false) otherwise.
/// The caller MUST keep the returned File alive to maintain the lock.
fn acquire_setup_lock(venv: &Path) -> (fs::File, bool) {
    let lock = lock_path(venv);

    let file = fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(false)
        .open(&lock)
        .expect("Cannot open/create lock file");

    let owned = try_flock_exclusive(&file);
    (file, owned)
}

fn release_setup_lock(_lock_file: fs::File) {
    // Dropping the file releases the flock automatically.
    // Explicit drop makes intent clear.
    log!("Setup lock released (pid={}).", std::process::id());
}

// ---------------------------------------------------------------------------
// Venv setup
// ---------------------------------------------------------------------------

fn setup_venv(system_python: &Path, venv: &Path) -> Result<(), String> {
    if venv.exists() {
        log!("Removing stale venv at: {}", venv.display());
        fs::remove_dir_all(venv).map_err(|e| format!("rm venv: {e}"))?;
    }

    log!("Creating venv at: {}", venv.display());
    let s = Command::new(system_python)
        .args(["-m", "venv", &venv.to_string_lossy()])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("venv create: {e}"))?;

    if !s.success() {
        return Err(format!("python -m venv failed ({s})"));
    }

    install_memento(&venv_python(venv))?;

    let marker = expected_marker();
    fs::write(marker_path(venv), &marker).map_err(|e| format!("write marker: {e}"))?;

    log!("Venv ready. Marker written: {}", marker);
    Ok(())
}

fn install_memento(python: &Path) -> Result<(), String> {
    // Dev-mode: if a local wheel sentinel file exists, install from it directly.
    let venv = venv_dir();
    if let Some(wheel) = local_wheel_path(&venv) {
        log!("local_wheel.txt found — installing from local wheel: {} (fingerprint: {})", wheel.path, wheel.fingerprint);

        // Step 1: install dependencies from PyPI (use the published package
        //         just to pull its deps; the code itself is overwritten in step 2).
        let s_deps = Command::new(python)
            .args([
                "-m", "pip", "install", "--upgrade", "--timeout", "120",
                "mcp-memento",
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map_err(|e| format!("pip (deps from PyPI): {e}"))?;

        if !s_deps.success() {
            log!("Warning: could not pre-install deps from PyPI ({s_deps}). Continuing anyway.");
        }

        // Step 2: overwrite with the local wheel (--no-deps: deps already present).
        let s = Command::new(python)
            .args([
                "-m", "pip", "install",
                "--force-reinstall", "--no-deps",
                &wheel.path,
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map_err(|e| format!("pip (local wheel): {e}"))?;

        if s.success() {
            log!("mcp-memento installed from local wheel.");
            return Ok(());
        }

        return Err(format!(
            "pip install from local wheel failed ({s}). Check local_wheel.txt path: {}", wheel.path
        ));
    }

    log!("pip install --upgrade mcp-memento (standard)");

    let s = Command::new(python)
        .args([
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--timeout",
            "120",
            "mcp-memento",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("pip: {e}"))?;

    if s.success() {
        log!("mcp-memento installed (standard pip).");
        return Ok(());
    }

    log!("Standard pip failed ({s}), trying --break-system-packages...");

    let s = Command::new(python)
        .args([
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--timeout",
            "120",
            "--break-system-packages",
            "mcp-memento",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("pip --break-system-packages: {e}"))?;

    if s.success() {
        log!("mcp-memento installed (--break-system-packages).");
        return Ok(());
    }

    Err("All pip strategies failed. Run: pip install mcp-memento".to_string())
}

// ---------------------------------------------------------------------------
// Fast-path: exec() Python replacing this process (Unix) or spawn+wait (Windows)
// ---------------------------------------------------------------------------

fn exec_python(venv_py: &Path) -> ! {
    log!("exec() Python: {} -u -m memento", venv_py.display());

    let mut cmd = Command::new(venv_py);
    cmd.args(["-u", "-m", "memento"])
        .env("PYTHONUNBUFFERED", "1");

    for var in &["MEMENTO_DB_PATH", "MEMENTO_PROFILE", "PYTHON_COMMAND", "MEMENTO_LOCAL_WHEEL"] {
        if let Ok(val) = env::var(var) {
            cmd.env(var, val);
        }
    }

    #[cfg(unix)]
    {
        let err = cmd.exec();
        log!("exec() failed: {err}");
        std::process::exit(1);
    }

    #[cfg(not(unix))]
    match cmd.status() {
        Ok(s) => std::process::exit(s.code().unwrap_or(1)),
        Err(e) => {
            log!("spawn Python failed: {e}");
            std::process::exit(1);
        }
    }
}

// ---------------------------------------------------------------------------
// Minimal JSON-RPC helpers (no external crates)
// ---------------------------------------------------------------------------

fn send_json(s: &str) {
    log!("→ Zed: {}", &s[..s.len().min(200)]);
    let mut out = io::stdout();
    let _ = writeln!(out, "{}", s);
    let _ = out.flush();
}

/// Parse just enough to extract "id" and "method" from a JSON-RPC message.
fn extract_id_method(raw: &str) -> (String, String) {
    let id = extract_str_or_num(raw, "\"id\"");
    let method = extract_quoted(raw, "\"method\"").unwrap_or_default();
    (id, method)
}

fn extract_quoted(s: &str, key: &str) -> Option<String> {
    let after_key = s.find(key)?;
    let after_colon = s[after_key + key.len()..].find(':')? + after_key + key.len() + 1;
    let trimmed = s[after_colon..].trim_start();
    if trimmed.starts_with('"') {
        let inner = &trimmed[1..];
        let end = inner.find('"')?;
        Some(inner[..end].to_string())
    } else {
        None
    }
}

fn extract_str_or_num(s: &str, key: &str) -> String {
    let after_key = match s.find(key) {
        Some(i) => i,
        None => return "null".to_string(),
    };
    let after_colon = match s[after_key + key.len()..].find(':') {
        Some(i) => i + after_key + key.len() + 1,
        None => return "null".to_string(),
    };
    let trimmed = s[after_colon..].trim_start();
    if trimmed.starts_with('"') {
        // string id
        let inner = &trimmed[1..];
        if let Some(end) = inner.find('"') {
            return format!("\"{}\"", &inner[..end]);
        }
    } else {
        // numeric or null id
        let end = trimmed
            .find(|c: char| !c.is_ascii_digit() && c != '-')
            .unwrap_or(trimmed.len());
        let token = trimmed[..end].trim();
        if !token.is_empty() {
            return token.to_string();
        }
    }
    "null".to_string()
}

fn is_notification(raw: &str) -> bool {
    // Notifications have no "id" field (or id is null/absent)
    // Quick heuristic: look for "id" key
    if let Some(pos) = raw.find("\"id\"") {
        let after = raw[pos + 4..].trim_start();
        if let Some(after_colon) = after.strip_prefix(':') {
            let val = after_colon.trim_start();
            return val.starts_with("null") || val.is_empty();
        }
    }
    true
}

fn make_response(id: &str, result_json: &str) -> String {
    format!(r#"{{"jsonrpc":"2.0","id":{id},"result":{result_json}}}"#)
}

fn make_error(id: &str, code: i32, message: &str) -> String {
    format!(r#"{{"jsonrpc":"2.0","id":{id},"error":{{"code":{code},"message":"{message}"}}}}"#)
}

// ---------------------------------------------------------------------------
// Stdin reader thread — feeds lines into a channel
// ---------------------------------------------------------------------------

static LINE_RX: OnceLock<Mutex<Receiver<Option<String>>>> = OnceLock::new();

fn start_reader_thread() {
    let (tx, rx): (SyncSender<Option<String>>, _) = mpsc::sync_channel(64);
    let _ = LINE_RX.set(Mutex::new(rx));

    thread::spawn(move || {
        let stdin = io::stdin();
        let mut reader = io::BufReader::new(stdin.lock());
        let mut line = String::new();

        loop {
            line.clear();
            match reader.read_line(&mut line) {
                Ok(0) => {
                    let _ = tx.send(None);
                    break;
                }
                Err(_) => {
                    let _ = tx.send(None);
                    break;
                }
                Ok(_) => {
                    let trimmed = line.trim_end_matches(['\r', '\n']).to_string();
                    if tx.send(Some(trimmed)).is_err() {
                        break;
                    }
                }
            }
        }
    });
}

fn recv_line(timeout: Duration) -> Option<Result<String, ()>> {
    let rx_lock = LINE_RX.get()?;
    let rx = rx_lock.lock().unwrap();

    match rx.recv_timeout(timeout) {
        Ok(Some(line)) => Some(Ok(line)),
        Ok(None) => Some(Err(())),
        Err(mpsc::RecvTimeoutError::Timeout) => None,
        Err(mpsc::RecvTimeoutError::Disconnected) => Some(Err(())),
    }
}

// ---------------------------------------------------------------------------
// Setup state
// ---------------------------------------------------------------------------

#[derive(Clone, PartialEq)]
enum SetupState {
    Running,
    Done,
    Failed(String),
}

// ---------------------------------------------------------------------------
// Bootstrap + proxy
//
// This function runs in the ACTIVE process (the one whose stdin Zed owns).
// It serves MCP while setup runs, buffers every message, then hands off
// to Python by replaying the buffer and proxying bidirectionally.
// ---------------------------------------------------------------------------

fn run_bootstrap_and_proxy(state: Arc<Mutex<SetupState>>, venv_py: PathBuf) -> ! {
    log!("Bootstrap server started (pid={}).", std::process::id());

    let mut buffered: Vec<String> = Vec::new();
    let mut initialized = false;

    loop {
        // ── 1. Check setup state ──────────────────────────────────────────
        {
            let s = state.lock().unwrap();
            match &*s {
                SetupState::Done => {
                    drop(s);
                    log!(
                        "Setup done — handing off to Python (pid={}).",
                        std::process::id()
                    );
                    proxy_to_python(&venv_py, buffered);
                }
                SetupState::Failed(e) => {
                    log!("Setup failed: {e}");
                    std::process::exit(1);
                }
                SetupState::Running => {}
            }
        }

        // ── 2. Read next line from Zed (300ms timeout) ───────────────────
        let raw = match recv_line(Duration::from_millis(300)) {
            None => continue, // timeout → loop back and re-check state
            Some(Err(())) => {
                log!("stdin EOF (pid={}).", std::process::id());
                // Zed closed stdin. We keep running until setup finishes
                // so we can still do the proxy handoff if needed.
                // But if Zed dropped us, there's no point — just wait for
                // setup to finish and exit cleanly.
                loop {
                    thread::sleep(Duration::from_millis(300));
                    let s = state.lock().unwrap();
                    if *s != SetupState::Running {
                        drop(s);
                        log!("Setup finished after stdin EOF — exiting.");
                        std::process::exit(0);
                    }
                }
            }
            Some(Ok(s)) => s,
        };

        let trimmed = raw.trim().to_string();
        if trimmed.is_empty() {
            continue;
        }

        log!("← Zed: {}", &trimmed[..trimmed.len().min(300)]);

        // Buffer EVERY message (we replay all of them to Python later)
        buffered.push(trimmed.clone());

        // ── 3. Serve minimal MCP response ────────────────────────────────
        let (id, method) = extract_id_method(&trimmed);
        let notif = is_notification(&trimmed);

        match method.as_str() {
            "initialize" => {
                initialized = true;
                let resp = make_response(
                    &id,
                    &format!(
                        r#"{{"protocolVersion":"2024-11-05","serverInfo":{{"name":"mcp-memento-bootstrap","version":"{STUB_VERSION}"}},"capabilities":{{"tools":{{"listChanged":true}}}}}}"#
                    ),
                );
                send_json(&resp);
            }

            "notifications/initialized" | "initialized" => {
                // notification — no response
            }

            "tools/list" => {
                if !notif {
                    let resp = make_response(
                        &id,
                        r#"{"tools":[{"name":"memento_status","description":"mcp-memento is being installed. Please wait.","inputSchema":{"type":"object","properties":{},"required":[]}}]}"#,
                    );
                    send_json(&resp);
                }
            }

            "tools/call" => {
                if !notif {
                    let resp = make_response(
                        &id,
                        r#"{"content":[{"type":"text","text":"mcp-memento is being installed in the background.\nThis usually takes 10\u201360 seconds on first run.\nPlease wait \u2014 the server will be ready shortly."}]}"#,
                    );
                    send_json(&resp);
                }
            }

            "ping" => {
                if !notif {
                    send_json(&make_response(&id, "{}"));
                }
            }

            _ => {
                if !notif {
                    if initialized {
                        send_json(&make_error(&id, -32601, "Method not found"));
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Proxy handoff: spawn Python with pipes, replay buffer, then forward forever
// ---------------------------------------------------------------------------

fn proxy_to_python(venv_py: &Path, buffered: Vec<String>) -> ! {
    log!("Spawning Python proxy (pid={}).", std::process::id());

    let mut child = match Command::new(venv_py)
        .args(["-u", "-m", "memento"])
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            log!("Failed to spawn Python: {e}");
            std::process::exit(1);
        }
    };

    let mut py_stdin = child.stdin.take().expect("child stdin");
    let py_stdout = child.stdout.take().expect("child stdout");

    // Synchronisation: replay thread signals main thread when done, so we
    // can inject listChanged before forwarding Python's output to Zed.
    let (ready_tx, ready_rx) = mpsc::sync_channel::<()>(1);

    // Replay buffered messages + forward future ones from the reader channel.
    thread::spawn(move || {
        // During bootstrap we already responded to requests like tools/list.
        // Zed considers those request IDs closed. If we replay them, Python
        // responds with the same IDs but Zed discards the responses (orphan).
        // Worse, Zed may also have already timed out waiting for tools/list.
        //
        // Strategy: replay ONLY initialize + notifications (no-id messages).
        // After listChanged, Zed will send a fresh tools/list with a new ID
        // that Python can answer correctly.
        // Send Python a synthetic initialize using a stub-internal ID (-1)
        // that Zed is not tracking. This way Python's initialize response
        // goes to Zed with id:-1 which Zed silently discards as orphan,
        // instead of colliding with the id:1 the bootstrap already answered.
        let init_msg = buffered.iter().find(|m| {
            let (_, method) = extract_id_method(m);
            method == "initialize"
        });

        let notifs: Vec<&String> = buffered
            .iter()
            .filter(|m| is_notification(m))
            .collect();

        if let Some(orig) = init_msg {
            // Replace the original id with -1
            let synthetic = orig.replacen(
                &format!("\"id\":{}", extract_str_or_num(orig, "\"id\"")),
                "\"id\":-1",
                1,
            );
            log!("Replay → Python (synthetic initialize id=-1): {}", &synthetic[..synthetic.len().min(120)]);
            if writeln!(py_stdin, "{}", synthetic).is_err() {
                log!("Write error during initialize replay.");
                let _ = ready_tx.send(());
                return;
            }
        }

        log!("Replaying {} notification(s) to Python.", notifs.len());
        for msg in notifs {
            log!("Replay → Python: {}", &msg[..msg.len().min(120)]);
            if writeln!(py_stdin, "{}", msg).is_err() {
                log!("Write error during notification replay.");
                let _ = ready_tx.send(());
                return;
            }
        }

        if py_stdin.flush().is_err() {
            log!("Flush error after replay.");
            let _ = ready_tx.send(());
            return;
        }

        log!("Replay done.");

        // Signal main thread that replay is complete.
        let _ = ready_tx.send(());

        // Forward remaining live messages from Zed → Python.
        loop {
            match recv_line(Duration::from_secs(60)) {
                None => continue,
                Some(Err(())) => {
                    log!("stdin EOF in proxy forwarder.");
                    break;
                }
                Some(Ok(msg)) => {
                    log!("Proxy → Python: {}", &msg[..msg.len().min(120)]);

                    if writeln!(py_stdin, "{}", msg).is_err() {
                        log!("Write error in proxy forwarder.");
                        break;
                    }
                }
            }
        }

        log!("Forwarder thread done.");
    });

    // Wait for replay to finish, then inject a tools/listChanged notification
    // so Zed re-fetches tools/list from Python (our bootstrap only had 1 tool).
    // We are the sole writer on Zed stdout at this point — no race condition.
    let _ = ready_rx.recv();
    {
        let notif = "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/tools/list_changed\"}\n";
        let mut zed_out = io::stdout();
        let _ = zed_out.write_all(notif.as_bytes());
        let _ = zed_out.flush();
        log!("Injected notifications/tools/listChanged → Zed.");
    }

    // Forward Python stdout → Zed stdout.
    {
        let mut buf = [0u8; 4096];
        let mut py_out = py_stdout;
        let mut zed_out = io::stdout();

        loop {
            match py_out.read(&mut buf) {
                Ok(0) => {
                    log!("Python stdout EOF.");
                    break;
                }
                Err(e) => {
                    log!("Python stdout read error: {e}");
                    break;
                }
                Ok(n) => {
                    log!("Python → Zed: {} bytes", n);

                    if zed_out.write_all(&buf[..n]).is_err() || zed_out.flush().is_err() {
                        log!("Write error forwarding to Zed.");
                        break;
                    }
                }
            }
        }
    }

    let code = child.wait().map(|s| s.code().unwrap_or(1)).unwrap_or(1);
    log!("Python proxy exited: {code}");
    std::process::exit(code);
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

fn main() {
    log!(
        "Starting. version={} pid={} os={}",
        STUB_VERSION,
        std::process::id(),
        std::env::consts::OS
    );

    let system_python = match find_python() {
        Some(p) => p,
        None => {
            log!("No Python found.");
            std::process::exit(1);
        }
    };

    let venv = venv_dir();
    log!("Venv directory: {}", venv.display());

    // ── Fast path ──────────────────────────────────────────────────────────
    if venv_is_valid(&venv) {
        log!("Fast path: venv valid.");
        exec_python(&venv_python(&venv));
    }

    // ── Slow path ──────────────────────────────────────────────────────────
    // Start the reader thread immediately so Zed's initialize is captured.
    start_reader_thread();

    log!("Slow path (pid={}).", std::process::id());

    if let Some(parent) = lock_path(&venv).parent() {
        let _ = fs::create_dir_all(parent);
    }

    let (lock_file, we_own_lock) = acquire_setup_lock(&venv);

    if we_own_lock {
        log!("Acquired setup lock via flock (pid={}).", std::process::id());
    } else {
        log!("Setup lock busy — polling (pid={}).", std::process::id());
    }

    let state = Arc::new(Mutex::new(SetupState::Running));
    let state_for_thread = Arc::clone(&state);
    let venv_for_thread = venv.clone();
    let python_for_thread = system_python.clone();

    thread::spawn(move || {
        // Split the lock_file into either "owned" or "waiter" based on who
        // acquired it. Both paths receive ownership via Option destructuring.
        let (mut lock_holder, waiter): (Option<fs::File>, Option<fs::File>) = if we_own_lock {
            (Some(lock_file), None)
        } else {
            (None, Some(lock_file))
        };
        let mut need_setup = we_own_lock;

        if !we_own_lock {
            // lock_file not owned — use it only for flock retry attempts.
            let mut waiter_file = waiter.expect("waiter file");
            let mut ticks: u32 = 0;

            loop {
                thread::sleep(Duration::from_millis(300));
                ticks += 1;

                if venv_is_valid(&venv_for_thread) {
                    log!(
                        "Other process finished setup — venv valid (pid={}).",
                        std::process::id()
                    );
                    *state_for_thread.lock().unwrap() = SetupState::Done;
                    return;
                }

                // Every ~2.1s retry flock. The kernel releases the advisory
                // lock the moment the owning process dies (even SIGKILL), so
                // this detects dead owners reliably without PID inspection.
                if ticks % 7 == 0 {
                    log!("Poll tick={}: retrying flock (pid={}).", ticks, std::process::id());

                    if try_flock_exclusive(&waiter_file) {
                        log!(
                            "Acquired lock via flock retry — owner was dead (pid={}).",
                            std::process::id()
                        );
                        lock_holder = Some(waiter_file);
                        need_setup = true;
                        break;
                    }

                    // Re-open so next iteration gets a fresh fd to try.
                    if let Ok(f) = fs::OpenOptions::new()
                        .write(true)
                        .create(true)
                        .truncate(false)
                        .open(lock_path(&venv_for_thread))
                    {
                        waiter_file = f;
                    }
                }
            }
        }

        if need_setup {
            match setup_venv(&python_for_thread, &venv_for_thread) {
                Ok(()) => {
                    release_setup_lock(lock_holder.take().expect("lock file"));
                    log!("Setup complete (pid={}).", std::process::id());
                    *state_for_thread.lock().unwrap() = SetupState::Done;
                }
                Err(e) => {
                    drop(lock_holder.take());
                    log!("Setup failed: {e}");
                    *state_for_thread.lock().unwrap() = SetupState::Failed(e);
                }
            }
        }
    });

    run_bootstrap_and_proxy(state, venv_python(&venv));
}
