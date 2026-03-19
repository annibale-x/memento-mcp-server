//! memento-stub
//!
//! Native launcher for the mcp-memento Zed extension.
//!
//! Responsibilities:
//!   1. Discover a working Python executable on the host system.
//!   2. Ensure mcp-memento is installed (auto-install via pip if missing).
//!   3. Spawn `python -u -m memento` with inherited stdin/stdout/stderr,
//!      then exit immediately.
//!
//! On Windows, Zed's ShellBuilder keeps the pipe open for the lifetime of
//! the process it launched.  By spawning Python with inherited file
//! descriptors and exiting the stub, Python takes over those descriptors
//! transparently — no proxy, no buffering, no pipe issues.

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------------------
// Logging — stderr + persistent file (stderr not visible inside Zed sandbox)
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

    // 1. Explicit override from the WASM extension settings.
    if let Ok(cmd) = env::var("PYTHON_COMMAND") {
        if !cmd.is_empty() && cmd != "default" {
            candidates.push(PathBuf::from(cmd));
        }
    }

    // 2. Standard Windows launchers / executables.
    candidates.push(PathBuf::from("py.exe"));
    candidates.push(PathBuf::from("python.exe"));
    candidates.push(PathBuf::from("python3.exe"));

    // 3. Well-known install locations under %LOCALAPPDATA%\Programs\Python.
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
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
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
// mcp-memento installation
// ---------------------------------------------------------------------------

fn memento_is_installed(python: &Path) -> bool {
    Command::new(python)
        .args(["-m", "memento", "--version"])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn install_memento(python: &Path) -> Result<(), String> {
    // Strategy 1: standard pip install
    // Works on: Windows, macOS, Linux systems without PEP 668
    log!("Trying: pip install --upgrade mcp-memento");
    let status = Command::new(python)
        .args(["-m", "pip", "install", "--upgrade", "mcp-memento"])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map_err(|e| format!("Failed to launch pip: {e}"))?;

    if status.success() {
        log!("mcp-memento installed successfully (standard pip).");
        return Ok(());
    }
    log!("Standard pip failed (status: {status}), trying --break-system-packages...");

    // Strategy 2: --break-system-packages (PEP 668 override for Debian/Ubuntu/Fedora)
    // IMPORTANT: This installs globally (not --user), so updates work correctly.
    // PEP 668 blocks this on distros that apply it, but it's the right choice
    // when it succeeds — it makes mcp-memento available system-wide and future
    // updates (via PyPI, other tools, etc.) will find and update it.
    let status = Command::new(python)
        .args([
            "-m", "pip", "install", "--upgrade",
            "--break-system-packages",
            "mcp-memento",
        ])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map_err(|e| format!("Failed to launch pip --break-system-packages: {e}"))?;

    if status.success() {
        log!("mcp-memento installed successfully (--break-system-packages).");
        return Ok(());
    }
    log!("--break-system-packages failed (status: {status}), trying pipx...");

    // Strategy 3: pipx (virtual environment manager for CLI tools)
    // Installs into an isolated venv but makes binary available on PATH.
    // Ensures updates work and doesn't pollute system Python.
    let pipx_status = Command::new("pipx")
        .args(["install", "--upgrade", "mcp-memento"])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status();

    match pipx_status {
        Ok(s) if s.success() => {
            log!("mcp-memento installed successfully via pipx.");
            return Ok(());
        }
        Ok(s) => log!("pipx failed (status: {s})"),
        Err(e) => log!("pipx not available: {e}"),
    }

    Err("All install strategies failed. Please install mcp-memento manually:\n  pip install mcp-memento          (try first)\n  pip install --break-system-packages mcp-memento (if PEP 668 blocks)\n  pipx install mcp-memento         (isolated venv)".to_string())
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
    let python = match find_python() {
        Some(p) => p,
        None => {
            log!("No Python found. Exiting.");
            std::process::exit(1);
        }
    };

    // Phase 2: ensure mcp-memento is installed.
    if !memento_is_installed(&python) {
        if let Err(e) = install_memento(&python) {
            log!("Auto-install failed: {e}");
            std::process::exit(1);
        }
    }

    // Phase 3: spawn `python -u -m memento` with inherited stdio, then exit.
    //
    // Zed holds the write end of stdin and the read end of stdout open for
    // the lifetime of the process it launched (the stub).  By NOT redirecting
    // stdio on the child, Python inherits those file descriptors directly.
    // The stub then exits — Python is now the sole owner of the pipe.
    log!("Spawning: {} -u -m memento", python.display());

    let mut cmd = Command::new(&python);
    cmd.args(["-u", "-m", "memento"]);
    cmd.env("PYTHONUNBUFFERED", "1");

    // Forward settings passed by the WASM extension via environment variables.
    for var in &["MEMENTO_DB_PATH", "MEMENTO_PROFILE", "PYTHON_COMMAND"] {
        if let Ok(val) = env::var(var) {
            cmd.env(var, val);
        }
    }

    // No .stdin() / .stdout() / .stderr() → inherited from this process.
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
