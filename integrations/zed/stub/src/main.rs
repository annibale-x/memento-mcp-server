//! memento-stub
//!
//! Native launcher for the mcp-memento Zed extension.
//!
//! Responsibilities:
//!   1. Discover a working Python executable on the host system.
//!   2. Create/validate an isolated venv inside the Zed extension work dir.
//!   3. Ensure mcp-memento is installed in that venv (auto-install via pip).
//!   4. Spawn `python -u -m memento` with inherited stdin/stdout/stderr,
//!      then exit immediately (fast path: venv already valid).
//!
//! When the venv is NOT yet ready (first install / version upgrade), the stub
//! acts as a temporary MCP bootstrap proxy:
//!
//!   - A background thread runs the venv setup (python -m venv + pip install).
//!   - The main thread serves a minimal JSON-RPC 2.0 / MCP server on stdio so
//!     that Zed's 60-second "initialize" timeout does not fire.
//!   - The bootstrap server advertises a single `memento_status` tool that
//!     returns a human-readable "still installing…" message.
//!   - Once setup completes, the stub re-execs itself (Unix) or spawns Python
//!     as a pipe-proxy child (Windows / fallback) and exits.
//!
//! This eliminates the "Context Server Stopped Running" error that occurred
//! when the user clicked "Configure Server" while pip was still running.

use std::env;
use std::fs;
use std::io::{self, BufRead, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;

// ---------------------------------------------------------------------------
// Version marker — must match STUB_EXT_RELEASE in lib.rs.
// ---------------------------------------------------------------------------

/// Injected by scripts/deploy.py during a version bump.
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
            .create(true)
            .append(true)
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
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "default" {
            candidates.push(PathBuf::from(cmd));
        }
    }

    candidates.push(PathBuf::from("py.exe"));
    candidates.push(PathBuf::from("python.exe"));
    candidates.push(PathBuf::from("python3.exe"));

    if let Ok(local) = env::var("LOCALAPPDATA") {
        let base = Path::new(&local).join("Programs").join("Python");

        if let Ok(rd) = std::fs::read_dir(&base) {
            let mut dirs: Vec<_> = rd.flatten().collect();
            dirs.sort_by(|a, b| b.file_name().cmp(&a.file_name()));

            for entry in dirs {
                let exe = entry.path().join("python.exe");

                if exe.exists() {
                    candidates.push(exe);
                }
            }
        }
    }

    candidates
}

#[cfg(not(target_os = "windows"))]
fn python_candidates() -> Vec<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "default" {
            candidates.push(PathBuf::from(cmd));
        }
    }

    candidates.push(PathBuf::from("python3"));
    candidates.push(PathBuf::from("python"));

    for prefix in &[
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/bin",
        "/opt/local/bin",
    ] {
        candidates.push(PathBuf::from(prefix).join("python3"));
        candidates.push(PathBuf::from(prefix).join("python"));
    }

    candidates
}

fn find_python() -> Option<PathBuf> {
    for candidate in python_candidates() {
        log!("Trying Python candidate: {}", candidate.display());

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
// Venv management
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

fn venv_is_valid(venv: &Path) -> bool {
    if !venv_python(venv).exists() {
        log!("Venv missing or incomplete at: {}", venv.display());
        return false;
    }

    match fs::read_to_string(marker_path(venv)) {
        Ok(content) if content.trim() == STUB_VERSION => {
            log!("Venv is valid (marker={}).", content.trim());
            true
        }
        Ok(content) => {
            log!(
                "Venv version mismatch: marker='{}' expected='{}'. Rebuilding.",
                content.trim(),
                STUB_VERSION
            );
            false
        }
        Err(_) => {
            log!("Venv marker missing. Rebuilding.");
            false
        }
    }
}

fn setup_venv(system_python: &Path, venv: &Path) -> Result<(), String> {
    if venv.exists() {
        log!("Removing stale venv at: {}", venv.display());
        fs::remove_dir_all(venv).map_err(|e| format!("Failed to remove stale venv: {e}"))?;
    }

    log!("Creating venv at: {}", venv.display());
    let status = Command::new(system_python)
        .args(["-m", "venv", &venv.to_string_lossy()])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("Failed to create venv: {e}"))?;

    if !status.success() {
        return Err(format!("python -m venv failed (status: {status})"));
    }

    let pip = venv_python(venv);
    install_memento(&pip)?;

    fs::write(marker_path(venv), STUB_VERSION)
        .map_err(|e| format!("Failed to write venv marker: {e}"))?;
    log!("Venv ready. Marker written: {}", STUB_VERSION);

    Ok(())
}

// ---------------------------------------------------------------------------
// mcp-memento installation
// ---------------------------------------------------------------------------

fn install_memento(python: &Path) -> Result<(), String> {
    log!("Trying: pip install --upgrade --timeout 120 mcp-memento");

    let status = Command::new(python)
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
        .map_err(|e| format!("Failed to launch pip: {e}"))?;

    if status.success() {
        log!("mcp-memento installed successfully (standard pip).");
        return Ok(());
    }

    log!("Standard pip failed (status: {status}), trying --break-system-packages...");

    let status = Command::new(python)
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
        .map_err(|e| format!("Failed to launch pip --break-system-packages: {e}"))?;

    if status.success() {
        log!("mcp-memento installed successfully (--break-system-packages).");
        return Ok(());
    }

    Err(
        "All install strategies failed. Please install mcp-memento manually:\n  \
         pip install mcp-memento\n  \
         pip install --break-system-packages mcp-memento  (if PEP 668 blocks)"
            .to_string(),
    )
}

// ---------------------------------------------------------------------------
// Minimal JSON-RPC 2.0 / MCP bootstrap server
//
// Serves on stdin/stdout while the venv setup runs in a background thread.
// Handles only the messages Zed sends during server startup:
//   - initialize         → responds with server capabilities (no tools yet)
//   - notifications/initialized → ignored (no response required)
//   - tools/list         → returns the single `memento_status` diagnostic tool
//   - tools/call         → returns setup progress for `memento_status`
//   - ping               → responds with empty result
//   - anything else      → responds with method-not-found error
//
// Once setup finishes (signalled via the shared SetupState), the proxy loop
// exits and the caller re-launches Python.
// ---------------------------------------------------------------------------

#[derive(Clone, PartialEq)]
enum SetupState {
    Running,
    Done,
    Failed(String),
}

/// Read one JSON-RPC frame from stdin.
///
/// The MCP stdio transport uses Content-Length framing identical to LSP:
///
///   Content-Length: <N>\r\n
///   \r\n
///   <N bytes of JSON>
fn read_jsonrpc_message(reader: &mut impl BufRead) -> Option<String> {
    let mut content_length: Option<usize> = None;

    loop {
        let mut line = String::new();

        if reader.read_line(&mut line).ok()? == 0 {
            return None;
        }

        let trimmed = line.trim_end_matches(['\r', '\n']);

        if trimmed.is_empty() {
            break;
        }

        if let Some(rest) = trimmed.strip_prefix("Content-Length:") {
            if let Ok(n) = rest.trim().parse::<usize>() {
                content_length = Some(n);
            }
        }
    }

    let n = content_length?;
    let mut buf = vec![0u8; n];
    reader.read_exact(&mut buf).ok()?;
    String::from_utf8(buf).ok()
}

/// Write one JSON-RPC frame to stdout (Content-Length framing).
fn write_jsonrpc_message(writer: &mut impl Write, body: &str) -> io::Result<()> {
    write!(writer, "Content-Length: {}\r\n\r\n{}", body.len(), body)?;
    writer.flush()
}

/// Tiny JSON string escaper — avoids pulling in serde.
fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 4);

    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }

    out
}

/// Extract the string value of a key from a flat JSON object (best-effort,
/// no full parser needed — we only deal with small Zed-generated messages).
fn json_get_str<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    let needle = format!("\"{}\"", key);
    let pos = json.find(&needle)?;
    let after_key = &json[pos + needle.len()..];
    let colon = after_key.find(':')? + 1;
    let value_start = &after_key[colon..].trim_start();

    if value_start.starts_with('"') {
        let inner = &value_start[1..];
        let end = inner.find('"')?;
        Some(&inner[..end])
    } else {
        None
    }
}

/// Extract a raw (possibly non-string) value for a key — used for `id`
/// which may be a number or a string.
fn json_get_id(json: &str) -> Option<String> {
    let needle = "\"id\"";
    let pos = json.find(needle)?;
    let after = &json[pos + needle.len()..];
    let colon = after.find(':')? + 1;
    let value = after[colon..].trim_start();

    if value.starts_with('"') {
        let inner = &value[1..];
        let end = inner.find('"')?;
        Some(format!("\"{}\"", &inner[..end]))
    } else {
        let end = value
            .find([',', '}', ']', ' ', '\n', '\r', '\t'])
            .unwrap_or(value.len());
        Some(value[..end].to_string())
    }
}

/// Run the bootstrap MCP proxy on stdin/stdout, then seamlessly hand off
/// to Python once the venv setup completes.
///
/// Phase 1 — Bootstrap: answer Zed's `initialize` (and any other messages)
///   while the venv setup runs in a background thread.
///
/// Phase 2 — Proxy: spawn Python as a child with piped stdio, then forward
///   bytes bidirectionally between Zed (our stdin/stdout) and Python.
///   This keeps the same stdin/stdout pipe that Zed opened — no re-exec,
///   no lost messages.
fn run_bootstrap_proxy(state: Arc<Mutex<SetupState>>, venv_py: PathBuf) -> ! {
    use std::sync::mpsc;
    use std::time::Duration;

    log!("Bootstrap proxy started.");

    // -----------------------------------------------------------------------
    // Phase 1: read messages from stdin on a dedicated thread, handle them
    // in the main thread with a 200 ms poll so we notice when setup finishes.
    // -----------------------------------------------------------------------
    let (tx, rx) = mpsc::channel::<Option<String>>();

    thread::spawn(move || {
        let stdin = io::stdin();
        let mut reader = io::BufReader::new(stdin.lock());

        loop {
            match read_jsonrpc_message(&mut reader) {
                Some(msg) => {
                    if tx.send(Some(msg)).is_err() {
                        break;
                    }
                }
                None => {
                    let _ = tx.send(None);
                    break;
                }
            }
        }
    });

    {
        let stdout = io::stdout();
        let mut writer = stdout.lock();

        'bootstrap: loop {
            match rx.recv_timeout(Duration::from_millis(200)) {
                Ok(None) => {
                    log!("stdin closed during bootstrap — exiting.");
                    std::process::exit(0);
                }

                Ok(Some(msg)) => {
                    log!("Bootstrap RX: {}", &msg[..msg.len().min(200)]);

                    let method = json_get_str(&msg, "method").unwrap_or("").to_string();
                    let id = json_get_id(&msg);

                    if method.starts_with("notifications/") || method == "$/cancelRequest" {
                        log!("Bootstrap: ignoring notification '{}'", method);
                    }
                    else if let Some(id) = id {
                        let response = build_response(&method, &id, &state);
                        log!("Bootstrap TX: {}", &response[..response.len().min(200)]);

                        if let Err(e) = write_jsonrpc_message(&mut writer, &response) {
                            log!("Bootstrap write error: {e}");
                            std::process::exit(1);
                        }
                    }
                    else {
                        log!("Bootstrap: no id, skipping '{}'", method);
                    }
                }

                Err(mpsc::RecvTimeoutError::Timeout) => {}

                Err(mpsc::RecvTimeoutError::Disconnected) => {
                    log!("Reader thread disconnected — exiting.");
                    std::process::exit(1);
                }
            }

            let s = state.lock().unwrap();

            if *s != SetupState::Running {
                log!("Setup finished — moving to proxy phase.");
                break 'bootstrap;
            }
        }
    } // release stdout lock before proxy

    // -----------------------------------------------------------------------
    // Phase 2: check setup outcome.
    // -----------------------------------------------------------------------
    let final_state = state.lock().unwrap().clone();

    if let SetupState::Failed(e) = final_state {
        log!("Setup failed — cannot start Python: {e}");
        std::process::exit(1);
    }

    // -----------------------------------------------------------------------
    // Phase 3: spawn Python and proxy stdin/stdout.
    //
    // The channel `rx` already owns the reader thread that holds stdin.
    // We forward messages from the channel → Python's stdin, and forward
    // Python's stdout → our stdout.
    // -----------------------------------------------------------------------
    log!("Spawning Python for proxy: {}", venv_py.display());

    let mut child = match Command::new(&venv_py)
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

    let mut child_stdin = child.stdin.take().expect("child stdin");
    let child_stdout = child.stdout.take().expect("child stdout");

    // Forward channel messages → Python stdin.
    thread::spawn(move || {
        while let Ok(Some(msg)) = rx.recv() {
            // Re-frame as Content-Length message for Python's MCP reader.
            let frame = format!("Content-Length: {}\r\n\r\n{}", msg.len(), msg);

            if child_stdin.write_all(frame.as_bytes()).is_err() {
                break;
            }
        }
        // When channel closes (stdin EOF), child_stdin drop closes Python's stdin.
    });

    // Forward Python stdout → our stdout.
    {
        let mut buf = [0u8; 4096];
        let mut py_out = child_stdout;
        let mut out = io::stdout();

        loop {
            match py_out.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    if out.write_all(&buf[..n]).is_err() || out.flush().is_err() {
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

fn build_response(method: &str, id: &str, state: &Arc<Mutex<SetupState>>) -> String {
    match method {
        "initialize" => {
            format!(
                r#"{{"jsonrpc":"2.0","id":{id},"result":{{"protocolVersion":"2024-11-05","capabilities":{{"tools":{{}}}},"serverInfo":{{"name":"memento-bootstrap","version":"{ver}"}}}}}}"#,
                id = id,
                ver = json_escape(STUB_VERSION),
            )
        }

        "tools/list" => {
            format!(
                r#"{{"jsonrpc":"2.0","id":{id},"result":{{"tools":[{{"name":"memento_status","description":"Returns the current Memento server setup status.","inputSchema":{{"type":"object","properties":{{}}}}}}]}}}}"#,
                id = id,
            )
        }

        "tools/call" => {
            let status_text = {
                let s = state.lock().unwrap();

                match &*s {
                    SetupState::Running => {
                        "Memento is being set up (installing mcp-memento via pip). \
                         This usually takes 10-60 seconds on first run. \
                         The server will restart automatically when ready."
                            .to_string()
                    }
                    SetupState::Done => "Memento setup complete. Restarting\u{2026}".to_string(),
                    SetupState::Failed(e) => format!(
                        "Memento setup failed: {}. Please check your Python installation.",
                        e
                    ),
                }
            };

            format!(
                r#"{{"jsonrpc":"2.0","id":{id},"result":{{"content":[{{"type":"text","text":"{text}"}}]}}}}"#,
                id = id,
                text = json_escape(&status_text),
            )
        }

        "ping" => {
            format!(r#"{{"jsonrpc":"2.0","id":{id},"result":{{}}}}"#, id = id)
        }

        _ => {
            log!("Bootstrap: unknown method '{}' -> method-not-found", method);
            format!(
                r#"{{"jsonrpc":"2.0","id":{id},"error":{{"code":-32601,"message":"Method not found: {method}"}}}}"#,
                id = id,
                method = json_escape(method),
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Entry point
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
            log!("No Python found. Exiting.");
            std::process::exit(1);
        }
    };

    let venv = venv_dir();
    log!("Venv directory: {}", venv.display());

    if venv_is_valid(&venv) {
        log!("Fast path: venv ready, launching Python directly.");
        launch_python(&venv_python(&venv));
    }

    log!("Slow path: venv not ready, starting bootstrap proxy + setup thread.");

    let state = Arc::new(Mutex::new(SetupState::Running));
    let state_bg = Arc::clone(&state);
    let venv_bg = venv.clone();
    let python_bg = system_python.clone();

    thread::spawn(move || {
        log!("Setup thread started.");

        let result = setup_venv(&python_bg, &venv_bg);
        let mut s = state_bg.lock().unwrap();

        match result {
            Ok(()) => {
                log!("Setup thread: setup complete.");
                *s = SetupState::Done;
            }
            Err(e) => {
                log!("Setup thread: setup failed: {e}");
                *s = SetupState::Failed(e);
            }
        }
    });

    run_bootstrap_proxy(Arc::clone(&state), venv_python(&venv));
}

// ---------------------------------------------------------------------------
// Launch helpers
// ---------------------------------------------------------------------------

/// Fast-path: venv is ready, spawn Python with inherited stdio and wait.
/// The stub exits with Python's exit code.
fn launch_python(venv_py: &Path) -> ! {
    log!("Launching: {} -u -m memento", venv_py.display());

    let mut cmd = Command::new(venv_py);
    cmd.args(["-u", "-m", "memento"]);
    cmd.env("PYTHONUNBUFFERED", "1");

    for var in &["MEMENTO_DB_PATH", "MEMENTO_PROFILE", "PYTHON_COMMAND"] {
        if let Ok(val) = env::var(var) {
            cmd.env(var, val);
        }
    }

    // No .stdin() / .stdout() / .stderr() → all inherited.
    match cmd.status() {
        Ok(s) => {
            log!("Python exited: {s}");
            std::process::exit(s.code().unwrap_or(1));
        }
        Err(e) => {
            log!("Failed to spawn Python: {e}");
            std::process::exit(1);
        }
    }
}


