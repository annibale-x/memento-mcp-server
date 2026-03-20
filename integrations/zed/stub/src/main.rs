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

fn debug_enabled() -> bool {
    if let Ok(work) = env::var("MEMENTO_WORK_DIR") {
        if !work.is_empty() {
            return Path::new(&work).join("debug.enable").exists();
        }
    }

    if let Ok(exe) = env::current_exe() {
        if let Some(dir) = exe.parent() {
            return dir.join("debug.enable").exists();
        }
    }

    false
}

macro_rules! log {
    ($($arg:tt)*) => {{
        if debug_enabled() {
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

/// Run the bootstrap MCP proxy on stdin/stdout.
///
/// Returns when setup is done (or failed) and it is safe to launch Python.
fn run_bootstrap_proxy(state: Arc<Mutex<SetupState>>) {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut reader = io::BufReader::new(stdin.lock());
    let mut writer = stdout.lock();

    log!("Bootstrap proxy started.");

    loop {
        // Check if setup finished before blocking on the next message.
        {
            let s = state.lock().unwrap();

            if *s != SetupState::Running {
                log!("Setup finished — exiting bootstrap proxy.");
                break;
            }
        }

        let msg = match read_jsonrpc_message(&mut reader) {
            Some(m) => m,
            None => {
                log!("stdin closed — exiting bootstrap proxy.");
                break;
            }
        };

        log!("Bootstrap RX: {}", &msg[..msg.len().min(200)]);

        let method = json_get_str(&msg, "method").unwrap_or("").to_string();
        let id = json_get_id(&msg);

        // Notifications have no id and require no response.
        if method.starts_with("notifications/") || method == "$/cancelRequest" {
            log!("Bootstrap: ignoring notification '{}'", method);
            continue;
        }

        // No id → notification we don't recognise; skip.
        let id = match id {
            Some(i) => i,
            None => {
                log!("Bootstrap: no id, skipping '{}'", method);
                continue;
            }
        };

        let response = match method.as_str() {
            // ------------------------------------------------------------------
            // initialize — advertise a minimal MCP 2024-11-05 server.
            // ------------------------------------------------------------------
            "initialize" => {
                format!(
                    r#"{{"jsonrpc":"2.0","id":{id},"result":{{"protocolVersion":"2024-11-05","capabilities":{{"tools":{{}}}},"serverInfo":{{"name":"memento-bootstrap","version":"{ver}"}}}}}}"#,
                    id = id,
                    ver = json_escape(STUB_VERSION),
                )
            }

            // ------------------------------------------------------------------
            // tools/list — expose the diagnostic status tool.
            // ------------------------------------------------------------------
            "tools/list" => {
                format!(
                    r#"{{"jsonrpc":"2.0","id":{id},"result":{{"tools":[{{"name":"memento_status","description":"Returns the current Memento server setup status.","inputSchema":{{"type":"object","properties":{{}}}}}}]}}}}"#,
                    id = id,
                )
            }

            // ------------------------------------------------------------------
            // tools/call — return setup progress.
            // ------------------------------------------------------------------
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
                        SetupState::Done => "Memento setup complete. Restarting…".to_string(),
                        SetupState::Failed(e) => {
                            format!(
                                "Memento setup failed: {}. Please check your Python installation.",
                                e
                            )
                        }
                    }
                };

                format!(
                    r#"{{"jsonrpc":"2.0","id":{id},"result":{{"content":[{{"type":"text","text":"{text}"}}]}}}}"#,
                    id = id,
                    text = json_escape(&status_text),
                )
            }

            // ------------------------------------------------------------------
            // ping — required by some MCP clients.
            // ------------------------------------------------------------------
            "ping" => {
                format!(r#"{{"jsonrpc":"2.0","id":{id},"result":{{}}}}"#, id = id)
            }

            // ------------------------------------------------------------------
            // Anything else — method not found.
            // ------------------------------------------------------------------
            _ => {
                log!("Bootstrap: unknown method '{}' → method-not-found", method);
                format!(
                    r#"{{"jsonrpc":"2.0","id":{id},"error":{{"code":-32601,"message":"Method not found: {method}"}}}}"#,
                    id = id,
                    method = json_escape(&method),
                )
            }
        };

        log!("Bootstrap TX: {}", &response[..response.len().min(200)]);

        if let Err(e) = write_jsonrpc_message(&mut writer, &response) {
            log!("Bootstrap write error: {e}");
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Pipe proxy (used after setup completes to hand off stdio to Python)
//
// On Unix we re-exec the stub itself — the new instance finds a valid venv
// and goes straight to `cmd.status()` with inherited stdio.
//
// On Windows (and as Unix fallback) we spawn Python as a child with piped
// stdio and manually forward bytes in both directions.
// ---------------------------------------------------------------------------

/// Attempt re-exec on Unix by replacing this process image with a fresh stub.
/// Returns only if exec failed (falls through to pipe_proxy).
#[cfg(unix)]
fn try_reexec() -> ! {
    use std::os::unix::process::CommandExt;

    let exe = match env::current_exe() {
        Ok(p) => p,
        Err(e) => {
            log!("current_exe failed: {e}");
            std::process::exit(1);
        }
    };

    log!("Re-execing stub: {}", exe.display());

    // CommandExt::exec() replaces the process image; only returns on error.
    let err = Command::new(&exe).exec();
    log!("Re-exec failed: {err}");
    std::process::exit(1);
}

/// Spawn Python as a child with piped stdio and forward bytes bidirectionally.
/// Used on Windows, and as a fallback if re-exec is unavailable.
#[cfg_attr(unix, allow(dead_code))]
fn pipe_proxy(venv_py: &Path) {
    log!("Starting pipe proxy to: {}", venv_py.display());

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
            log!("Failed to spawn Python for pipe proxy: {e}");
            std::process::exit(1);
        }
    };

    let mut child_stdin = child.stdin.take().expect("child stdin");
    let mut child_stdout = child.stdout.take().expect("child stdout");

    // stdin → child stdin (separate thread)
    let stdin_thread = thread::spawn(move || {
        let mut buf = [0u8; 4096];
        let mut stdin = io::stdin();

        loop {
            match stdin.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    if child_stdin.write_all(&buf[..n]).is_err() {
                        break;
                    }
                }
            }
        }
    });

    // child stdout → stdout (main thread)
    {
        let mut buf = [0u8; 4096];
        let mut stdout = io::stdout();

        loop {
            match child_stdout.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    if stdout.write_all(&buf[..n]).is_err() || stdout.flush().is_err() {
                        break;
                    }
                }
            }
        }
    }

    let _ = stdin_thread.join();
    let code = child.wait().map(|s| s.code().unwrap_or(1)).unwrap_or(1);
    log!("Pipe proxy child exited: {code}");
    std::process::exit(code);
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

    // ------------------------------------------------------------------
    // Phase 1: find system Python.
    // ------------------------------------------------------------------
    let system_python = match find_python() {
        Some(p) => p,
        None => {
            log!("No Python found. Exiting.");
            std::process::exit(1);
        }
    };

    // ------------------------------------------------------------------
    // Phase 2: check venv validity.
    // ------------------------------------------------------------------
    let venv = venv_dir();
    log!("Venv directory: {}", venv.display());

    if venv_is_valid(&venv) {
        // Fast path — venv is ready, hand off to Python immediately.
        log!("Fast path: venv ready, launching Python directly.");
        launch_python(&venv_python(&venv));
    }

    // ------------------------------------------------------------------
    // Slow path — venv needs setup.
    // Spin up setup in a background thread, serve MCP bootstrap on stdio
    // so Zed does not time out waiting for `initialize`.
    // ------------------------------------------------------------------
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

    // Run bootstrap proxy until setup finishes (or stdin closes).
    run_bootstrap_proxy(Arc::clone(&state));

    // ------------------------------------------------------------------
    // Phase 3: setup done — check outcome and hand off to Python.
    // ------------------------------------------------------------------
    let final_state = state.lock().unwrap().clone();

    match final_state {
        SetupState::Done => {
            log!("Setup done — handing off to Python.");
            hand_off_to_python(&venv_python(&venv));
        }
        SetupState::Failed(e) => {
            log!("Setup failed, cannot start Python: {e}");
            std::process::exit(1);
        }
        SetupState::Running => {
            // stdin was closed before setup finished (user closed Zed).
            log!("stdin closed before setup finished — exiting.");
            std::process::exit(0);
        }
    }
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

/// Slow-path hand-off: after bootstrap proxy, transfer control to Python.
///
/// On Unix: re-exec this stub (which will find the now-valid venv and hit
/// the fast path with fully inherited stdio — no proxy overhead).
///
/// On Windows / fallback: use a bidirectional pipe proxy.
fn hand_off_to_python(venv_py: &Path) -> ! {
    #[cfg(unix)]
    {
        let _ = venv_py;
        try_reexec();
    }

    #[cfg(not(unix))]
    pipe_proxy(venv_py);
}
