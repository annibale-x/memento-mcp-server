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
    ($($arg:tt)*) => {
        let msg = format!($($arg)*);
        let _ = writeln!(std::io::stderr(), "[MEMENTO-STUB] {}", msg);
    };
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

// ---------------------------------------------------------------------------
// Real server proxy
// ---------------------------------------------------------------------------

/// Launch `python -u -m memento` and proxy stdin/stdout.
/// `buffered` contains lines received during the stub phase that must be
/// replayed to the real server before forwarding new stdin.
/// `stdin_rx` is the channel receiver from the stub-phase stdin reader thread,
/// which must be reused to avoid double-locking stdin.
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
            // Notify Zed so the user sees something.
            send(&format!(
                r#"{{"jsonrpc":"2.0","method":"$/logMessage","params":{{"type":1,"message":"mcp-memento: failed to launch Python server: {}"}}}}"#,
                e
            ));
            return;
        }
    };

    let mut child_stdin = child.stdin.take().expect("child stdin");
    let child_stdout = child.stdout.take().expect("child stdout");

    // --- Replay buffered lines ---
    for line in &buffered {
        if !line.is_empty() {
            log!("Replaying: {}", &line[..line.len().min(120)]);
            let _ = writeln!(child_stdin, "{}", line);
        }
    }
    let _ = child_stdin.flush();

    // --- Thread: child stdout → our stdout ---
    let (tools_tx, tools_rx) = mpsc::channel::<()>();

    thread::spawn(move || {
        let reader = BufReader::new(child_stdout);
        let mut notified = false;

        for line in reader.lines() {
            match line {
                Ok(l) => {
                    // Forward to Zed.
                    send(&l);

                    // If the real server sent its initialize response,
                    // signal the main thread to send tools/list_changed.
                    if !notified && l.contains("\"result\"") && l.contains("protocolVersion") {
                        let _ = tools_tx.send(());
                        notified = true;
                    }
                }
                Err(_) => break,
            }
        }
    });

    // Wait for the real server's initialize response, then notify Zed.
    if tools_rx
        .recv_timeout(std::time::Duration::from_secs(30))
        .is_ok()
    {
        notify_tools_list_changed();
    }

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
    // We read stdin on a dedicated thread so we can apply a timeout.
    // If Zed's ShellBuilder pipes stdin but the messages are delayed (or
    // if the pipe is set up after the process has already started), we still
    // want to respond within the 60-second window.
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

    // Wait up to 2 seconds for the first message from Zed.
    // If nothing arrives, respond proactively with a synthetic initialize
    // response so that Zed's 60-second timeout is never triggered.
    let first_timeout = std::time::Duration::from_millis(2000);
    let line_timeout = std::time::Duration::from_millis(500);

    let recv_first = rx.recv_timeout(first_timeout);

    let first_line = match recv_first {
        Ok(l) => {
            log!("First stdin line received within timeout.");
            Some(l)
        }
        Err(_) => {
            // Timeout — Zed never sent anything (ShellBuilder buffering issue).
            // Respond proactively: Zed always sends id=1 for initialize.
            log!("Stdin timeout — sending proactive initialize response (id=1).");
            respond_initialize("1");
            initialized = true;
            None
        }
    };

    // Process the first line if we got one, then continue reading.
    let mut lines_to_process: Vec<String> = Vec::new();

    if let Some(l) = first_line {
        lines_to_process.push(l);
    }

    // Now drain remaining messages with a shorter per-line timeout.
    // We keep reading until the stub phase is complete.
    loop {
        // Pull any already-queued lines first.
        let line = if !lines_to_process.is_empty() {
            lines_to_process.remove(0)
        } else {
            match rx.recv_timeout(line_timeout) {
                Ok(l) => l,
                Err(mpsc::RecvTimeoutError::Timeout) => {
                    // No more messages for now.
                    if initialized {
                        // Hand off to proxy — Zed will send more after initialize.
                        log!("Stub phase complete (timeout after init).");
                        return (buffered, rx);
                    }

                    // Still waiting for initialize.
                    continue;
                }
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }
        };

        if line.trim().is_empty() {
            continue;
        }

        log!("Stub recv: {}", &line[..line.len().min(200)]);

        // Always buffer so we can replay to the real server.
        buffered.push(line.clone());

        let method = json_str_field(&line, "method").unwrap_or("").to_owned();
        let id = json_str_field(&line, "id").map(|s| s.to_owned());

        match method.as_str() {
            "initialize" => {
                // Always respond to initialize, even if we already sent a
                // proactive response: Zed may have missed it (ShellBuilder
                // buffering) and will send its own initialize with a real id.
                if let Some(ref id) = id {
                    respond_initialize(id);
                }
                initialized = true;
            }

            "initialized" => {
                // Notification — no response needed.
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
                    let resp =
                        format!(r#"{{"jsonrpc":"2.0","id":{id},"result":{{}}}}"#, id = id);
                    send(&resp);
                }
            }

            _ => {
                if !is_notification(&line) {
                    if let Some(ref id) = id {
                        respond_not_found(id, &method);
                    }
                }

                // Any message after initialize means handshake is done.
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

    // Write a marker file so we can verify the stub is running.
    #[cfg(target_os = "windows")]
    {
        if let Ok(tmp) = env::var("TEMP").or_else(|_| env::var("TMP")) {
            let marker = Path::new(&tmp).join("memento_stub.log");
            let _ = std::fs::write(
                &marker,
                format!(
                    "stub started pid={} python_command={:?}\n",
                    std::process::id(),
                    env::var("PYTHON_COMMAND").unwrap_or_default()
                ),
            );
        }
    }

    // Phase 1: stub — answer Zed's handshake immediately.
    // Returns buffered lines AND the stdin receiver thread to reuse in proxy.
    let (buffered, stdin_rx) = stub_phase();
    log!("Stub phase complete. Buffered {} lines.", buffered.len());

    // Phase 2: find Python.
    let python = match find_python() {
        Some(p) => p,
        None => {
            log!("Python not found! Sending error notification.");
            send(concat!(
                r#"{"jsonrpc":"2.0","method":"$/logMessage","params":{"#,
                r#""type":1,"message":"mcp-memento: Python not found. "#,
                r#"Set PYTHON_COMMAND in extension settings."}}"#
            ));
            return;
        }
    };

    // Phase 3: proxy — reuse the stdin receiver from stub phase.
    run_proxy(&python, buffered, stdin_rx);
}
