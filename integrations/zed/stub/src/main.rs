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
//!   1. Try to acquire the setup lock (O_CREAT|O_EXCL + PID written inside).
//!      - If acquired → spawn setup thread (venv + pip).
//!      - If not acquired → just wait; check for stale lock every 500ms.
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

const STUB_VERSION: &str = "v0.2.22";

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

fn lock_path(venv: &Path) -> PathBuf {
    venv.parent().unwrap_or(venv).join("memento_setup.lock")
}

fn venv_is_valid(venv: &Path) -> bool {
    if !venv_python(venv).exists() {
        return false;
    }

    match fs::read_to_string(marker_path(venv)) {
        Ok(c) if c.trim() == STUB_VERSION => true,
        Ok(c) => {
            log!(
                "Venv version mismatch: marker='{}' expected='{}'.",
                c.trim(),
                STUB_VERSION
            );
            false
        }
        Err(_) => false,
    }
}

// ---------------------------------------------------------------------------
// PID-based lockfile
// ---------------------------------------------------------------------------

fn pid_is_alive(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }

    #[cfg(target_os = "linux")]
    {
        Path::new(&format!("/proc/{}", pid)).exists()
    }

    #[cfg(not(target_os = "linux"))]
    {
        // Fallback: try kill -0
        unsafe { libc::kill(pid as libc::pid_t, 0) == 0 }
    }
}

fn lock_is_stale(lock: &Path) -> bool {
    match fs::read_to_string(lock) {
        Err(_) => false,
        Ok(content) => {
            let owner_pid: u32 = content.trim().parse().unwrap_or(0);
            // Empty file or dead PID → stale
            !pid_is_alive(owner_pid)
        }
    }
}

/// Try to atomically create the lockfile and write our PID.
/// Removes a stale lock first if the previous owner is dead.
fn acquire_setup_lock(venv: &Path) -> bool {
    let lock = lock_path(venv);

    if lock.exists() && lock_is_stale(&lock) {
        log!("Removing stale lock (pid in file is dead or empty).");
        let _ = fs::remove_file(&lock);
    }

    match fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&lock)
    {
        Ok(mut f) => {
            let _ = writeln!(f, "{}", std::process::id());
            true
        }
        Err(_) => false,
    }
}

fn release_setup_lock(venv: &Path) {
    let _ = fs::remove_file(lock_path(venv));
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

    fs::write(marker_path(venv), STUB_VERSION).map_err(|e| format!("write marker: {e}"))?;

    log!("Venv ready. Marker written: {}", STUB_VERSION);
    Ok(())
}

fn install_memento(python: &Path) -> Result<(), String> {
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

    for var in &["MEMENTO_DB_PATH", "MEMENTO_PROFILE", "PYTHON_COMMAND"] {
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
                        r#"{{"protocolVersion":"2024-11-05","serverInfo":{{"name":"mcp-memento-bootstrap","version":"{STUB_VERSION}"}},"capabilities":{{"tools":{{}}}}}}"#
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

    // Replay buffered messages + forward future ones from the reader channel
    thread::spawn(move || {
        log!(
            "Replaying {} buffered message(s) to Python.",
            buffered.len()
        );

        for msg in &buffered {
            log!("Replay → Python: {}", &msg[..msg.len().min(120)]);
            if writeln!(py_stdin, "{}", msg).is_err() {
                log!("Write error during replay.");
                return;
            }
        }

        if py_stdin.flush().is_err() {
            log!("Flush error after replay.");
            return;
        }

        log!("Replay done — forwarding live messages.");

        // Forward remaining live messages from Zed → Python
        loop {
            match recv_line(Duration::from_secs(60)) {
                None => continue, // timeout, keep waiting
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

    // Forward Python stdout → Zed stdout
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

    let we_own_lock = acquire_setup_lock(&venv);

    if we_own_lock {
        log!("Acquired setup lock (pid={}).", std::process::id());
    } else {
        log!("Setup lock busy — waiting (pid={}).", std::process::id());
    }

    let state = Arc::new(Mutex::new(SetupState::Running));
    let state_for_thread = Arc::clone(&state);
    let venv_for_thread = venv.clone();
    let python_for_thread = system_python.clone();

    thread::spawn(move || {
        let mut need_setup = we_own_lock;

        if !we_own_lock {
            // Poll until venv is valid OR we can steal a dead owner's lock
            loop {
                thread::sleep(Duration::from_millis(500));

                if venv_is_valid(&venv_for_thread) {
                    log!(
                        "Other process finished — venv valid (pid={}).",
                        std::process::id()
                    );
                    *state_for_thread.lock().unwrap() = SetupState::Done;
                    return;
                }

                // Try to take over if the owner is dead
                let lock = lock_path(&venv_for_thread);
                let stale = !lock.exists() || lock_is_stale(&lock);

                if stale {
                    log!(
                        "Lock is stale/gone — trying takeover (pid={}).",
                        std::process::id()
                    );

                    if lock.exists() {
                        let _ = fs::remove_file(&lock);
                    }

                    let grabbed = fs::OpenOptions::new()
                        .write(true)
                        .create_new(true)
                        .open(&lock)
                        .map(|mut f| {
                            let _ = writeln!(f, "{}", std::process::id());
                            true
                        })
                        .unwrap_or(false);

                    if grabbed {
                        log!("Takeover successful (pid={}).", std::process::id());
                        need_setup = true;
                        break;
                    }

                    log!("Another process grabbed the lock first — keep polling.");
                }
            }
        }

        if need_setup {
            match setup_venv(&python_for_thread, &venv_for_thread) {
                Ok(()) => {
                    release_setup_lock(&venv_for_thread);
                    log!("Setup complete (pid={}).", std::process::id());
                    *state_for_thread.lock().unwrap() = SetupState::Done;
                }
                Err(e) => {
                    release_setup_lock(&venv_for_thread);
                    log!("Setup failed: {e}");
                    *state_for_thread.lock().unwrap() = SetupState::Failed(e);
                }
            }
        }
    });

    run_bootstrap_and_proxy(state, venv_python(&venv));
}
