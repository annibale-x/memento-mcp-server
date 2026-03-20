//! memento-stub
//!
//! Native launcher for the mcp-memento Zed extension.
//!
//! Responsibilities:
//!   1. Discover a working Python executable on the host system.
//!   2. Create/validate an isolated venv inside the Zed extension work dir.
//!   3. Ensure mcp-memento is installed in that venv (auto-install via pip).
//!   4. Spawn `python -u -m memento` with inherited stdin/stdout/stderr.
//!
//! FAST PATH (venv already valid):
//!   exec() Python directly — zero overhead, no proxy, no buffering.
//!
//! SLOW PATH (first install / upgrade):
//!   - Acquire an atomic lockfile (O_CREAT|O_EXCL) to be the setup owner.
//!   - Spawn setup thread: python -m venv + pip install mcp-memento.
//!   - Serve a REAL, minimal MCP server on stdio so Zed never times out:
//!       * initialize      → respond with valid ServerInfo + capabilities
//!       * initialized     → ignore (no response)
//!       * tools/list      → return single `memento_status` tool
//!       * tools/call      → return human-readable "still installing…" text
//!       * ping            → respond with empty result {}
//!       * anything else   → respond with method-not-found (-32601)
//!   - When setup finishes → exit(0).
//!   - Zed detects exit(0) and RELAUNCHES the stub automatically.
//!   - Relaunch hits fast path → exec() Python → real server starts.
//!
//! CONCURRENT LAUNCH (second click while setup is running):
//!   - Fails to acquire lockfile → enters bootstrap server loop.
//!   - Polls venv validity every 500ms inside the message-handling loop.
//!   - When venv becomes valid → exit(0) → Zed relaunches → fast path.
//!
//! This approach eliminates ALL race conditions:
//!   - No stdin buffering / replay (those bytes are gone forever).
//!   - No proxy threads competing for stdin ownership.
//!   - Zed always talks to a valid MCP server; never sees silence.
//!   - Python starts with a pristine stdin — no pre-consumed bytes.

use std::env;
use std::fs;
use std::io::{self, BufRead, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

// ---------------------------------------------------------------------------
// Version marker — must match STUB_EXT_RELEASE in lib.rs.
// ---------------------------------------------------------------------------

const STUB_VERSION: &str = "v0.2.22";

// ---------------------------------------------------------------------------
// Logging — stderr + /tmp/memento_stub_debug.log
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

fn lock_path(venv: &Path) -> PathBuf {
    venv.parent()
        .unwrap_or(venv)
        .join("memento_setup.lock")
}

fn release_setup_lock(venv: &Path) {
    let _ = fs::remove_file(lock_path(venv));
    log!("Setup lock released (pid={}).", std::process::id());
}

fn venv_is_valid(venv: &Path) -> bool {
    if !venv_python(venv).exists() {
        return false;
    }

    match fs::read_to_string(marker_path(venv)) {
        Ok(content) if content.trim() == STUB_VERSION => true,
        Ok(content) => {
            log!(
                "Venv version mismatch: marker='{}' expected='{}'.",
                content.trim(),
                STUB_VERSION
            );
            false
        }
        Err(_) => false,
    }
}

fn setup_venv(system_python: &Path, venv: &Path) -> Result<(), String> {
    if venv.exists() {
        log!("Removing stale venv at: {}", venv.display());
        fs::remove_dir_all(venv)
            .map_err(|e| format!("Failed to remove stale venv: {e}"))?;
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

fn install_memento(python: &Path) -> Result<(), String> {
    log!("pip install --upgrade mcp-memento (standard)");

    let status = Command::new(python)
        .args(["-m", "pip", "install", "--upgrade", "--timeout", "120", "mcp-memento"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("Failed to launch pip: {e}"))?;

    if status.success() {
        log!("mcp-memento installed (standard pip).");
        return Ok(());
    }

    log!("Standard pip failed ({status}), trying --break-system-packages...");

    let status = Command::new(python)
        .args([
            "-m", "pip", "install", "--upgrade",
            "--timeout", "120",
            "--break-system-packages",
            "mcp-memento",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("Failed to launch pip --break-system-packages: {e}"))?;

    if status.success() {
        log!("mcp-memento installed (--break-system-packages).");
        return Ok(());
    }

    Err(
        "All install strategies failed. \
         Run: pip install mcp-memento  (or pip install --break-system-packages mcp-memento)"
            .to_string(),
    )
}

// ---------------------------------------------------------------------------
// Fast-path exec — venv is ready, replace stub process with Python.
// ---------------------------------------------------------------------------

fn launch_python(venv_py: &Path) -> ! {
    log!("Fast path: exec {} -u -m memento", venv_py.display());

    let mut cmd = Command::new(venv_py);
    cmd.args(["-u", "-m", "memento"]);
    cmd.env("PYTHONUNBUFFERED", "1");

    for var in &["MEMENTO_DB_PATH", "MEMENTO_PROFILE", "PYTHON_COMMAND"] {
        if let Ok(val) = env::var(var) {
            cmd.env(var, val);
        }
    }

    // Inherited stdin/stdout/stderr — Python talks directly to Zed.
    match cmd.status() {
        Ok(s) => {
            log!("Python exited: {s}");
            std::process::exit(s.code().unwrap_or(1));
        }
        Err(e) => {
            log!("Failed to exec Python: {e}");
            std::process::exit(1);
        }
    }
}

// ---------------------------------------------------------------------------
// Minimal JSON-RPC / MCP helpers
// ---------------------------------------------------------------------------

/// Send one newline-delimited JSON-RPC response to stdout.
fn send(obj: serde_json_lite::Value) {
    let s = obj.to_string();
    log!("→ Zed: {}", &s[..s.len().min(300)]);

    let mut out = io::stdout();
    let _ = writeln!(out, "{}", s);
    let _ = out.flush();
}

/// Build a JSON-RPC success response.
fn ok_response(id: &serde_json_lite::Value, result: serde_json_lite::Value) -> serde_json_lite::Value {
    serde_json_lite::json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    })
}

/// Build a JSON-RPC error response.
fn err_response(
    id: &serde_json_lite::Value,
    code: i64,
    message: &str,
) -> serde_json_lite::Value {
    serde_json_lite::json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message
        }
    })
}

// ---------------------------------------------------------------------------
// Minimal JSON implementation (no external crates needed for this small use)
// ---------------------------------------------------------------------------

mod serde_json_lite {
    use std::collections::BTreeMap;
    use std::fmt;

    #[derive(Clone, Debug)]
    pub enum Value {
        Null,
        Bool(bool),
        Number(f64),
        Str(String),
        Array(Vec<Value>),
        Object(BTreeMap<String, Value>),
    }

    impl fmt::Display for Value {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            match self {
                Value::Null => write!(f, "null"),
                Value::Bool(b) => write!(f, "{}", b),
                Value::Number(n) => {
                    if *n == n.floor() && n.abs() < 1e15 {
                        write!(f, "{}", *n as i64)
                    } else {
                        write!(f, "{}", n)
                    }
                }
                Value::Str(s) => {
                    write!(f, "\"")?;
                    for c in s.chars() {
                        match c {
                            '"' => write!(f, "\\\"")?,
                            '\\' => write!(f, "\\\\")?,
                            '\n' => write!(f, "\\n")?,
                            '\r' => write!(f, "\\r")?,
                            '\t' => write!(f, "\\t")?,
                            c => write!(f, "{}", c)?,
                        }
                    }
                    write!(f, "\"")
                }
                Value::Array(arr) => {
                    write!(f, "[")?;
                    for (i, v) in arr.iter().enumerate() {
                        if i > 0 {
                            write!(f, ",")?;
                        }
                        write!(f, "{}", v)?;
                    }
                    write!(f, "]")
                }
                Value::Object(map) => {
                    write!(f, "{{")?;
                    for (i, (k, v)) in map.iter().enumerate() {
                        if i > 0 {
                            write!(f, ",")?;
                        }
                        write!(f, "\"{}\":{}", k, v)?;
                    }
                    write!(f, "}}")
                }
            }
        }
    }

    /// Extremely small recursive-descent JSON parser.
    pub fn parse(s: &str) -> Option<Value> {
        let s = s.trim();
        let (v, _) = parse_value(s)?;
        Some(v)
    }

    fn skip_ws(s: &str) -> &str {
        s.trim_start_matches([' ', '\t', '\r', '\n'])
    }

    fn parse_value(s: &str) -> Option<(Value, &str)> {
        let s = skip_ws(s);

        if s.is_empty() {
            return None;
        }

        match s.as_bytes()[0] {
            b'"' => parse_string(s),
            b'{' => parse_object(s),
            b'[' => parse_array(s),
            b't' => s.strip_prefix("true").map(|r| (Value::Bool(true), r)),
            b'f' => s.strip_prefix("false").map(|r| (Value::Bool(false), r)),
            b'n' => s.strip_prefix("null").map(|r| (Value::Null, r)),
            b'0'..=b'9' | b'-' => parse_number(s),
            _ => None,
        }
    }

    fn parse_string(s: &str) -> Option<(Value, &str)> {
        let s = s.strip_prefix('"')?;
        let mut result = String::new();
        let mut chars = s.char_indices();

        loop {
            let (i, c) = chars.next()?;

            if c == '"' {
                return Some((Value::Str(result), &s[i + 1..]));
            }

            if c == '\\' {
                let (_, esc) = chars.next()?;
                match esc {
                    '"' => result.push('"'),
                    '\\' => result.push('\\'),
                    '/' => result.push('/'),
                    'n' => result.push('\n'),
                    'r' => result.push('\r'),
                    't' => result.push('\t'),
                    'b' => result.push('\x08'),
                    'f' => result.push('\x0C'),
                    'u' => {
                        // consume 4 hex digits — simplified: push replacement char
                        for _ in 0..4 {
                            chars.next()?;
                        }
                        result.push('\u{FFFD}');
                    }
                    other => result.push(other),
                }
            } else {
                result.push(c);
            }
        }
    }

    fn parse_number(s: &str) -> Option<(Value, &str)> {
        let end = s
            .find(|c: char| !matches!(c, '0'..='9' | '-' | '+' | '.' | 'e' | 'E'))
            .unwrap_or(s.len());
        let n: f64 = s[..end].parse().ok()?;
        Some((Value::Number(n), &s[end..]))
    }

    fn parse_object(s: &str) -> Option<(Value, &str)> {
        let s = skip_ws(s.strip_prefix('{')?);
        let mut map = BTreeMap::new();

        if let Some(rest) = s.strip_prefix('}') {
            return Some((Value::Object(map), rest));
        }

        let mut cur = s;

        loop {
            let cur_ws = skip_ws(cur);
            let (key, after_key) = parse_string(cur_ws)?;
            let key_str = match key {
                Value::Str(k) => k,
                _ => return None,
            };
            let after_colon = skip_ws(after_key).strip_prefix(':')?;
            let (val, after_val) = parse_value(after_colon)?;
            map.insert(key_str, val);
            let after_ws = skip_ws(after_val);

            if let Some(rest) = after_ws.strip_prefix('}') {
                return Some((Value::Object(map), rest));
            }

            cur = after_ws.strip_prefix(',')?;
        }
    }

    fn parse_array(s: &str) -> Option<(Value, &str)> {
        let s = skip_ws(s.strip_prefix('[')?);
        let mut arr = Vec::new();

        if let Some(rest) = s.strip_prefix(']') {
            return Some((Value::Array(arr), rest));
        }

        let mut cur = s;

        loop {
            let (val, after_val) = parse_value(cur)?;
            arr.push(val);
            let after_ws = skip_ws(after_val);

            if let Some(rest) = after_ws.strip_prefix(']') {
                return Some((Value::Array(arr), rest));
            }

            cur = after_ws.strip_prefix(',')?;
        }
    }

    impl Value {
        pub fn get(&self, key: &str) -> Option<&Value> {
            match self {
                Value::Object(m) => m.get(key),
                _ => None,
            }
        }

        pub fn as_str(&self) -> Option<&str> {
            match self {
                Value::Str(s) => Some(s.as_str()),
                _ => None,
            }
        }

        pub fn is_null(&self) -> bool {
            matches!(self, Value::Null)
        }
    }

    /// Minimal json! macro — supports string literals and nested json!{} calls.
    macro_rules! json {
        (null) => { $crate::serde_json_lite::Value::Null };

        (true) => { $crate::serde_json_lite::Value::Bool(true) };
        (false) => { $crate::serde_json_lite::Value::Bool(false) };

        ([ $($elem:tt),* $(,)? ]) => {{
            let mut arr = Vec::new();
            $( arr.push(json!($elem)); )*
            $crate::serde_json_lite::Value::Array(arr)
        }};

        ({ $($key:literal : $val:tt),* $(,)? }) => {{
            let mut map = std::collections::BTreeMap::new();
            $( map.insert($key.to_string(), json!($val)); )*
            $crate::serde_json_lite::Value::Object(map)
        }};

        ($e:expr) => {
            $crate::serde_json_lite::Value::from($e)
        };
    }

    pub(crate) use json;

    impl From<&str> for Value {
        fn from(s: &str) -> Self {
            Value::Str(s.to_string())
        }
    }

    impl From<String> for Value {
        fn from(s: String) -> Self {
            Value::Str(s)
        }
    }

    impl From<i64> for Value {
        fn from(n: i64) -> Self {
            Value::Number(n as f64)
        }
    }

    impl From<f64> for Value {
        fn from(n: f64) -> Self {
            Value::Number(n)
        }
    }

    impl From<bool> for Value {
        fn from(b: bool) -> Self {
            Value::Bool(b)
        }
    }

    impl From<&Value> for Value {
        fn from(v: &Value) -> Self {
            v.clone()
        }
    }
}

use serde_json_lite::{Value, json};

// ---------------------------------------------------------------------------
// Setup state (shared between setup thread and bootstrap server loop)
// ---------------------------------------------------------------------------

#[derive(Clone, PartialEq)]
enum SetupState {
    Running,
    Done,
    Failed(String),
}

// ---------------------------------------------------------------------------
// Bootstrap MCP server
//
// Runs on stdin/stdout while venv setup is in progress.
// Responds to ALL MCP messages so Zed never times out.
// When setup finishes (Done or Failed) → exit(0) so Zed relaunches.
// On relaunch the stub hits the fast path and exec()s Python directly.
// ---------------------------------------------------------------------------

fn run_bootstrap_server(state: Arc<Mutex<SetupState>>) -> ! {
    log!("Bootstrap server started (pid={}).", std::process::id());

    let stdin = io::stdin();
    let mut reader = io::BufReader::new(stdin.lock());
    let mut initialized = false;

    loop {
        // Check setup state before blocking on stdin — if done, exit now
        // so Zed relaunches and hits the fast path immediately.
        {
            let s = state.lock().unwrap();

            if *s != SetupState::Running {
                let msg = match &*s {
                    SetupState::Done => "Setup complete — exiting so Zed relaunches.".to_string(),
                    SetupState::Failed(e) => format!("Setup failed: {e}"),
                    SetupState::Running => unreachable!(),
                };
                log!("{}", msg);
                std::process::exit(0);
            }
        }

        // Non-blocking line read with a short timeout emulated via a
        // separate thread + channel, so we can re-check state periodically.
        let line = read_line_timeout(&mut reader, Duration::from_millis(300));

        let raw = match line {
            None => {
                // Timeout — loop back and re-check state.
                continue;
            }
            Some(Err(_)) => {
                log!("stdin EOF — exiting.");
                std::process::exit(0);
            }
            Some(Ok(s)) => s,
        };

        let trimmed = raw.trim();

        if trimmed.is_empty() {
            continue;
        }

        log!("← Zed: {}", &trimmed[..trimmed.len().min(300)]);

        let msg = match serde_json_lite::parse(trimmed) {
            Some(v) => v,
            None => {
                log!("Failed to parse JSON: {}", trimmed);
                continue;
            }
        };

        let id = msg.get("id").cloned().unwrap_or(Value::Null);
        let method = msg
            .get("method")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        // Notifications have no id — no response needed.
        let is_notification = id.is_null();

        match method.as_str() {
            "initialize" => {
                initialized = true;
                send(ok_response(&id, json!({
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mcp-memento-bootstrap",
                        "version": STUB_VERSION
                    },
                    "capabilities": {
                        "tools": {}
                    }
                })));
            }

            "notifications/initialized" | "initialized" => {
                // No response for notifications.
            }

            "tools/list" => {
                if is_notification { continue; }
                send(ok_response(&id, json!({
                    "tools": [
                        {
                            "name": "memento_status",
                            "description": "Returns the current setup status of mcp-memento.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                })));
            }

            "tools/call" => {
                if is_notification { continue; }

                let elapsed = {
                    // We don't track start time here precisely, so just say "in progress".
                    "mcp-memento is being installed in the background.\n\
                     This usually takes 10–60 seconds on first run.\n\
                     Please wait — the server will restart automatically when ready."
                };

                send(ok_response(&id, json!({
                    "content": [
                        {
                            "type": "text",
                            "text": elapsed
                        }
                    ]
                })));
            }

            "ping" => {
                if is_notification { continue; }
                send(ok_response(&id, json!({})));
            }

            _ => {
                if is_notification {
                    log!("Ignoring notification: {method}");
                    continue;
                }

                if !initialized {
                    // Zed sent something before initialize — ignore.
                    log!("Ignoring pre-init request: {method}");
                    continue;
                }

                send(err_response(&id, -32601, &format!("Method not found: {method}")));
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Non-blocking line read with timeout
//
// Spawns a reader thread once, parks lines in an mpsc channel.
// Returns None on timeout, Some(Ok(line)) on data, Some(Err(_)) on EOF/error.
// ---------------------------------------------------------------------------

use std::sync::OnceLock;
use std::sync::mpsc::{Receiver, SyncSender};

static LINE_RX: OnceLock<Mutex<Receiver<Option<String>>>> = OnceLock::new();
static LINE_TX: OnceLock<SyncSender<Option<String>>> = OnceLock::new();

fn init_reader_thread() {
    let (tx, rx) = std::sync::mpsc::sync_channel::<Option<String>>(16);
    let _ = LINE_TX.set(tx.clone());
    let _ = LINE_RX.set(Mutex::new(rx));

    thread::spawn(move || {
        let stdin = io::stdin();
        let mut reader = io::BufReader::new(stdin.lock());

        loop {
            let mut line = String::new();

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

/// Read one line from the shared reader thread, with a timeout.
/// Returns:
///   None           — timeout (no data yet)
///   Some(Ok(line)) — got a line (may be empty for blank lines)
///   Some(Err(()))  — EOF or read error
fn read_line_timeout(
    _reader: &mut impl BufRead,
    timeout: Duration,
) -> Option<Result<String, ()>> {
    let rx_lock = LINE_RX.get()?;
    let rx = rx_lock.lock().unwrap();

    match rx.recv_timeout(timeout) {
        Ok(Some(line)) => Some(Ok(line)),
        Ok(None) => Some(Err(())),
        Err(std::sync::mpsc::RecvTimeoutError::Timeout) => None,
        Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => Some(Err(())),
    }
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
            log!("No Python found. Exiting.");
            std::process::exit(1);
        }
    };

    let venv = venv_dir();
    log!("Venv directory: {}", venv.display());

    // Fast path — venv already valid, exec Python immediately.
    if venv_is_valid(&venv) {
        log!("Fast path: venv valid.");
        launch_python(&venv_python(&venv));
    }

    // Slow path — setup needed.
    // Initialise the shared stdin reader thread BEFORE acquiring the lock
    // so it starts reading immediately (Zed may send initialize right away).
    init_reader_thread();

    log!("Slow path: venv not valid (pid={}).", std::process::id());

    let lock = lock_path(&venv);

    if let Some(parent) = lock.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let we_own_lock = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&lock)
        .is_ok();

    if we_own_lock {
        log!("Acquired setup lock (pid={}).", std::process::id());
    } else {
        log!("Setup lock busy — another process is installing (pid={}).", std::process::id());
    }

    let state = Arc::new(Mutex::new(SetupState::Running));
    let state_for_thread = Arc::clone(&state);
    let venv_for_thread = venv.clone();
    let python_for_thread = system_python.clone();

    thread::spawn(move || {
        if !we_own_lock {
            // Not the setup owner — just poll until venv is valid.
            loop {
                thread::sleep(Duration::from_millis(500));

                if venv_is_valid(&venv_for_thread) {
                    log!("Other process finished setup — venv valid (pid={}).", std::process::id());
                    *state_for_thread.lock().unwrap() = SetupState::Done;
                    return;
                }

                log!("Still waiting for setup to finish…");
            }
        }

        // We own the lock — run setup.
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
    });

    // Run bootstrap server — responds to Zed while setup runs in background.
    // Exits with code 0 when setup is done so Zed relaunches.
    run_bootstrap_server(state);
}
