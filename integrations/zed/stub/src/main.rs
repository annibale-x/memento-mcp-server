//! memento-stub
//!
//! Native MCP stub launcher for the mcp-memento Zed extension.
//!
//! Responsibilities:
//!   1. Read JSON-RPC lines from stdin immediately.
//!   2. Respond to `initialize` with stub capabilities (0 tools, listChanged=true)
//!      so Zed's 60-second timeout is never triggered.
//!   3. Discover a working Python executable on the host system.
//!   4. Launch `python -u -m memento` as a subprocess.
//!   5. Proxy all subsequent stdin/stdout between Zed and the real server.
//!   6. Send a `notifications/tools/list_changed` notification once the real
//!      server has completed its own `initialize` exchange, so Zed refreshes
//!      the tool list.
//!
//! Protocol: JSON-RPC 2.0, one message per line, UTF-8, no Content-Length
//! framing (stdio transport as used by Zed context servers).

use std::env;
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;

// ---------------------------------------------------------------------------
// Logging (stderr only — stdout is reserved for JSON-RPC)
// ---------------------------------------------------------------------------

macro_rules! log {
    ($($arg:tt)*) => {{
        use std::io::Write as _;
        let msg = format!($($arg)*);
        let _ = writeln!(std::io::stderr(), "[MEMENTO-STUB] {}", msg);

        // Always append to a file — stderr is not visible inside Zed's sandbox.
        if let Ok(mut f) = std::fs::OpenOptions::new()
            .create(true).append(true)
            .open(std::env::temp_dir().join("memento_stub_debug.log"))
        {
            let _ = writeln!(f, "{}", msg);
        }
    }};
}

// ---------------------------------------------------------------------------
// JSON-RPC helpers  (tiny, allocation-friendly, no external deps)
// ---------------------------------------------------------------------------

fn send(obj: &str) {
    let stdout = io::stdout();
    let mut out = stdout.lock();
    let _ = out.write_all(obj.as_bytes());
    let _ = out.write_all(b"\n");
    let _ = out.flush();
}

/// Extract a string field value from a raw JSON object.
/// Returns the value without surrounding quotes.
/// Only handles simple string values — sufficient for our use.
fn json_str_field<'a>(json: &'a str, field: &str) -> Option<&'a str> {
    let needle = format!("\"{}\"", field);
    let pos = json.find(needle.as_str())?;
    let after = json[pos + needle.len()..].trim_start();
    let after = after.strip_prefix(':')?.trim_start();

    if after.starts_with('"') {
        let inner = &after[1..];
        let end = inner.find('"')?;
        Some(&inner[..end])
    } else {
        None
    }
}

/// Check whether a JSON line is a notification (no "id" field at top level,
/// or "id" is null).
fn is_notification(json: &str) -> bool {
    // Notifications must not have an "id" field (or have null).
    !json.contains("\"id\"")
        || json
            .find("\"id\"")
            .map(|pos| {
                let rest = json[pos + 4..].trim_start();
                let rest = rest.strip_prefix(':').unwrap_or(rest).trim_start();
                rest.starts_with("null")
            })
            .unwrap_or(false)
}

// ---------------------------------------------------------------------------
// Stub responses
// ---------------------------------------------------------------------------

fn respond_initialize(id: &str) {
    let resp = format!(
        r#"{{"jsonrpc":"2.0","id":{id},"result":{{"protocolVersion":"2024-11-05","capabilities":{{"tools":{{"listChanged":true}},"experimental":{{}}}},"serverInfo":{{"name":"memento-stub","version":"0.1.0"}}}}}}"#,
        id = id
    );
    send(&resp);
    log!("Sent stub initialize response (id={})", id);
}

fn respond_tools_list(id: &str) {
    let resp = format!(
        r#"{{"jsonrpc":"2.0","id":{id},"result":{{"tools":[]}}}}"#,
        id = id
    );
    send(&resp);
    log!("Sent empty tools/list (id={})", id);
}

fn respond_not_found(id: &str, method: &str) {
    let resp = format!(
        r#"{{"jsonrpc":"2.0","id":{id},"error":{{"code":-32601,"message":"Method not found: {method}"}}}}"#,
        id = id,
        method = method
    );
    send(&resp);
}

fn notify_tools_list_changed() {
    send(r#"{"jsonrpc":"2.0","method":"notifications/tools/list_changed","params":{}}"#);
    log!("Sent notifications/tools/list_changed");
}

// ---------------------------------------------------------------------------
// Python discovery
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
fn python_candidates() -> Vec<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // 1. Explicit override from environment (set by the WASM extension via settings).
    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "auto" {
            candidates.push(PathBuf::from(&cmd));
        }
    }

    // 2. Python Launcher (py.exe) — most reliable on Windows.
    candidates.push(PathBuf::from("py.exe"));
    candidates.push(PathBuf::from("python.exe"));
    candidates.push(PathBuf::from("python3.exe"));

    // 3. Well-known install locations under %LOCALAPPDATA%.
    if let Ok(local) = env::var("LOCALAPPDATA") {
        let base = Path::new(&local).join("Programs").join("Python");
        if let Ok(rd) = std::fs::read_dir(&base) {
            let mut dirs: Vec<_> = rd.flatten().collect();
            dirs.sort_by(|a, b| b.file_name().cmp(&a.file_name())); // newest first
            for entry in dirs {
                let exe = entry.path().join("python.exe");
                if exe.exists() {
                    candidates.push(exe);
                }
            }
        }
    }

    // 4. Well-known location under %APPDATA%\Python (pip --user installs).
    if let Ok(appdata) = env::var("APPDATA") {
        let base = Path::new(&appdata).join("Python");
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
        if !cmd.is_empty() && cmd != "auto" {
            candidates.push(PathBuf::from(&cmd));
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

/// Try each candidate; return the first one that can run `--version` successfully.
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

/// Check whether `python -m memento --version` succeeds.
/// Returns true if the package is importable.
fn memento_is_installed(python: &Path) -> bool {
    Command::new(python)
        .args(["-m", "memento", "--version"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Install mcp-memento via `python -m pip install --upgrade mcp-memento`.
/// Returns Ok(()) on success, Err(message) on failure.
fn install_memento(python: &Path) -> Result<(), String> {
    log!("mcp-memento not found — installing via pip...");

    let status = Command::new(python)
        .args(["-m", "pip", "install", "--upgrade", "mcp-memento"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("pip install failed to launch: {e}"))?;

    if status.success() {
        log!("mcp-memento installed successfully.");
        Ok(())
    } else {
        Err(format!(
            "pip install mcp-memento exited with status: {}",
            status
        ))
    }
}

// ---------------------------------------------------------------------------
// Real server proxy
// ---------------------------------------------------------------------------

/// Launch `python -u -m memento` and proxy stdin/stdout.
///
/// `buffered` contains lines received during the stub phase (including
/// `initialize`).  We replay them all to Python so it can complete its own
/// internal initialisation — but we suppress Python's `initialize` response
/// (Zed already got one from the stub) and only forward subsequent output.
///
/// `stdin_rx` is the channel receiver from the stub-phase stdin reader thread.
fn run_proxy(python: &Path, buffered: Vec<String>, stdin_rx: mpsc::Receiver<String>) {
    log!("Launching real server: {} -u -m memento", python.display());

    let mut child = match Command::new(python)
        .args(["-u", "-m", "memento"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .env("PYTHONUNBUFFERED", "1")
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            log!("Failed to launch real server: {}", e);
            send(&format!(
                r#"{{"jsonrpc":"2.0","method":"$/logMessage","params":{{"type":1,"message":"mcp-memento: failed to launch Python server: {}"}}}}"#,
                e
            ));
            return;
        }
    };

    let mut child_stdin = child.stdin.take().expect("child stdin");
    let child_stdout = child.stdout.take().expect("child stdout");

    // --- Replay buffered lines to Python ---
    for line in &buffered {
        if !line.is_empty() {
            log!("Replaying: {}", &line[..line.len().min(120)]);
            let _ = writeln!(child_stdin, "{}", line);
        }
    }
    let _ = child_stdin.flush();

    // --- Thread: child stdout → our stdout ---
    // Skip Python's initialize response (id matching buffered initialize id):
    // the stub already sent one to Zed; forwarding a second would confuse it.
    let init_id: Option<String> = buffered
        .iter()
        .find(|l| l.contains("\"initialize\""))
        .and_then(|l| json_str_field(l, "id").map(|s| s.to_owned()));

    thread::spawn(move || {
        let reader = BufReader::new(child_stdout);
        let mut init_response_skipped = init_id.is_none();

        for line in reader.lines() {
            match line {
                Ok(l) => {
                    // Skip the initialize response from Python — Zed already
                    // received one from the stub.
                    if !init_response_skipped {
                        if let Some(ref id) = init_id {
                            if l.contains(&format!("\"id\":{}", id))
                                || l.contains(&format!("\"id\": {}", id))
                            {
                                if l.contains("protocolVersion") || l.contains("serverInfo") {
                                    log!("Suppressing Python initialize response (id={}).", id);
                                    init_response_skipped = true;
                                    continue;
                                }
                            }
                        }
                    }

                    send(&l);
                }
                Err(_) => break,
            }
        }
    });

    // Send tools/list_changed so Zed fetches the real tool list from Python.
    notify_tools_list_changed();

    // --- Forward new stdin lines → child stdin ---
    // We reuse the receiver from the stub phase thread to avoid double-locking
    // stdin. The thread is still running and will forward all new messages.
    loop {
        match stdin_rx.recv() {
            Ok(l) => {
                if writeln!(child_stdin, "{}", l).is_err() {
                    break;
                }
                let _ = child_stdin.flush();
            }
            Err(_) => break,
        }
    }

    let _ = child_stdin; // drop closes the pipe
    let _ = child.wait();
    log!("Real server exited.");
}

// ---------------------------------------------------------------------------
// Stub phase: read stdin until initialize is handled, buffer everything else
// ---------------------------------------------------------------------------

fn stub_phase() -> (Vec<String>, mpsc::Receiver<String>) {
    // Read stdin on a dedicated thread so the main thread can remain responsive.
    let (tx, rx) = mpsc::channel::<String>();

    thread::spawn(move || {
        let stdin = io::stdin();

        for line in stdin.lock().lines() {
            match line {
                Ok(l) => {
                    if tx.send(l).is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    });

    let mut buffered: Vec<String> = Vec::new();
    let mut initialized = false;

    // Wait indefinitely for messages from Zed — it always sends initialize first.
    // We use a long per-message timeout only to detect a broken pipe.
    let line_timeout = std::time::Duration::from_secs(55);

    loop {
        let line = match rx.recv_timeout(line_timeout) {
            Ok(l) => l,
            Err(mpsc::RecvTimeoutError::Timeout) => {
                log!("Stub phase timed out waiting for initialize from Zed.");
                return (buffered, rx);
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                if !initialized {
                    // Stdin closed before initialize arrived — nothing to do.
                    log!("Stdin closed before initialize. Exiting.");
                    std::process::exit(0);
                }
                log!("Stdin closed after initialize.");
                break;
            }
        };

        if line.trim().is_empty() {
            continue;
        }

        log!("Stub recv: {}", &line[..line.len().min(200)]);

        buffered.push(line.clone());

        let method = json_str_field(&line, "method").unwrap_or("").to_owned();
        let id = json_str_field(&line, "id").map(|s| s.to_owned());

        match method.as_str() {
            "initialize" => {
                if let Some(ref id) = id {
                    respond_initialize(id);
                }
                initialized = true;
                // Exit stub phase immediately after responding to initialize.
                // Zed may not send "initialized" before forwarding further
                // messages, and the proxy must be up to receive them.
                log!("Stub phase complete (initialize handled).");
                return (buffered, rx);
            }

            "initialized" => {
                // Notification — no response needed.
                if initialized {
                    log!("Stub phase complete (initialized notification).");
                    return (buffered, rx);
                }
            }

            "tools/list" => {
                if let Some(ref id) = id {
                    respond_tools_list(id);
                }

                if initialized {
                    log!("Stub phase complete (tools/list handled).");
                    return (buffered, rx);
                }
            }

            "ping" => {
                if let Some(ref id) = id {
                    send(&format!(
                        r#"{{"jsonrpc":"2.0","id":{id},"result":{{}}}}"#,
                        id = id
                    ));
                }
            }

            _ => {
                if !is_notification(&line) {
                    if let Some(ref id) = id {
                        respond_not_found(id, &method);
                    }
                }

                if initialized {
                    log!("Stub phase complete (post-init message: {}).", method);
                    return (buffered, rx);
                }
            }
        }
    }

    (buffered, rx)
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    log!(
        "Starting. version=0.1.0 pid={} os={}",
        std::process::id(),
        std::env::consts::OS
    );

    // Phase 1: find Python.
    log!("Searching for Python...");
    let python = match find_python() {
        Some(p) => p,
        None => {
            log!("Python not found!");
            // Can't send MCP yet — Zed hasn't sent initialize.
            // Just exit; Zed will show "server stopped running".
            // TODO: show a notification once we have a way to do it pre-handshake.
            std::process::exit(1);
        }
    };
    log!("Python found: {}", python.display());

    // Phase 2: ensure mcp-memento is installed; auto-install if missing.
    log!("Checking if mcp-memento is installed...");

    if !memento_is_installed(&python) {
        log!("Running pip install mcp-memento...");

        match install_memento(&python) {
            Ok(()) => log!("pip install succeeded."),
            Err(e) => {
                log!("Auto-install failed: {}", e);
                std::process::exit(1);
            }
        }
    }

    log!("mcp-memento ready. Replacing process with Python server...");

    // Phase 3: replace this process with `python -m memento`.
    //
    // We spawn Python with inherited stdin/stdout/stderr (no explicit
    // Stdio redirection = inherit by default) and immediately exit the
    // stub process.  From Zed's perspective the pipe never closes —
    // Python takes over the exact same file descriptors.
    //
    // On Unix this would be exec(). On Windows there is no true exec(),
    // but spawn-with-inherited-stdio + exit() is functionally identical:
    // Zed holds the write end of stdin and the read end of stdout open,
    // and Python inherits both.
    let mut cmd = Command::new(&python);
    cmd.args(["-u", "-m", "memento"]);

    // Forward any env vars set by the WASM extension settings.
    if let Ok(db) = env::var("MEMENTO_DB_PATH") {
        cmd.env("MEMENTO_DB_PATH", db);
    }

    if let Ok(profile) = env::var("MEMENTO_PROFILE") {
        cmd.env("MEMENTO_PROFILE", profile);
    }

    cmd.env("PYTHONUNBUFFERED", "1");

    match cmd.status() {
        Ok(s) => {
            log!("Python server exited: {}", s);
            std::process::exit(s.code().unwrap_or(1));
        }
        Err(e) => {
            log!("Failed to spawn Python server: {}", e);
            std::process::exit(1);
        }
    }
}
