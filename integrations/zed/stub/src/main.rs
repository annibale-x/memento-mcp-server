//! memento-stub
//!
//! Native launcher for the mcp-memento Zed extension.
//!
//! Responsibilities:
//!   1. Discover a working Python executable on the host system.
//!   2. Create/validate an isolated venv inside the Zed extension work dir.
//!   3. Ensure mcp-memento is installed in that venv (auto-install via pip).
//!   4. Spawn `python -u -m memento` with inherited stdin/stdout/stderr,
//!      then exit immediately.
//!
//! On Windows, Zed's ShellBuilder keeps the pipe open for the lifetime of
//! the process it launched.  By spawning Python with inherited file
//! descriptors and exiting the stub, Python takes over those descriptors
//! transparently — no proxy, no buffering, no pipe issues.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------------------
// Version marker — must match STUB_EXT_RELEASE in lib.rs.
// The venv is rebuilt whenever this value changes (i.e. on every release).
// ---------------------------------------------------------------------------

/// Injected by scripts/deploy.py during a version bump.  Matches the PyPI
/// package version and the Zed extension marketplace version.
const STUB_VERSION: &str = "v0.2.19";

// ---------------------------------------------------------------------------
// Logging — stderr + persistent file (stderr not visible inside Zed sandbox)
// ---------------------------------------------------------------------------

/// Returns true if debug logging is enabled.
///
/// Checks for a `debug.enable` marker file in (in order):
///   1. MEMENTO_WORK_DIR (the Zed extension work directory, passed by the WASM)
///   2. The directory containing this stub binary
///
/// To enable on Linux/macOS:
///   touch ~/.local/share/zed/extensions/work/mcp-memento/debug.enable
/// To enable on Windows (PowerShell):
///   New-Item "$env:LOCALAPPDATA\Zed\extensions\work\mcp-memento\debug.enable"
fn debug_enabled() -> bool {
    // 1. Zed extension work directory (preferred — same file as WASM checks).
    if let Ok(work) = env::var("MEMENTO_WORK_DIR") {
        if !work.is_empty() {
            return Path::new(&work).join("debug.enable").exists();
        }
    }

    // 2. Fallback: directory containing the stub binary.
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
// Venv management
// ---------------------------------------------------------------------------

/// Returns the path to the venv inside the Zed extension work directory.
/// The work dir is passed by the WASM extension via MEMENTO_WORK_DIR.
/// Falls back to a sibling directory of the stub binary itself.
fn venv_dir() -> PathBuf {
    if let Ok(work) = env::var("MEMENTO_WORK_DIR") {
        if !work.is_empty() {
            return PathBuf::from(work).join("venv");
        }
    }

    // Fallback: place venv next to the stub binary.
    let mut dir = env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("."))
        .parent()
        .unwrap_or(Path::new("."))
        .to_path_buf();
    dir.push("venv");
    dir
}

/// Returns the Python executable inside the venv.
#[cfg(target_os = "windows")]
fn venv_python(venv: &Path) -> PathBuf {
    venv.join("Scripts").join("python.exe")
}

#[cfg(not(target_os = "windows"))]
fn venv_python(venv: &Path) -> PathBuf {
    venv.join("bin").join("python")
}

/// Path to the version marker file inside the venv.
fn marker_path(venv: &Path) -> PathBuf {
    venv.join("memento_version.txt")
}

/// Returns true if the venv exists and its marker matches STUB_VERSION.
fn venv_is_valid(venv: &Path) -> bool {
    let marker = marker_path(venv);

    if !venv_python(venv).exists() {
        log!("Venv missing or incomplete at: {}", venv.display());
        return false;
    }

    match fs::read_to_string(&marker) {
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

/// Removes and recreates the venv, installs mcp-memento, writes the marker.
fn setup_venv(system_python: &Path, venv: &Path) -> Result<(), String> {
    // Remove stale venv if present.
    if venv.exists() {
        log!("Removing stale venv at: {}", venv.display());
        fs::remove_dir_all(venv)
            .map_err(|e| format!("Failed to remove stale venv: {e}"))?;
    }

    // Create fresh venv.
    log!("Creating venv at: {}", venv.display());
    let status = Command::new(system_python)
        .args(["-m", "venv", &venv.to_string_lossy()])
        .status()
        .map_err(|e| format!("Failed to create venv: {e}"))?;

    if !status.success() {
        return Err(format!("python -m venv failed (status: {status})"));
    }

    // Install mcp-memento inside the venv.
    let pip = venv_python(venv);
    install_memento(&pip)?;

    // Write version marker.
    fs::write(marker_path(venv), STUB_VERSION)
        .map_err(|e| format!("Failed to write venv marker: {e}"))?;
    log!("Venv ready. Marker written: {}", STUB_VERSION);

    Ok(())
}

// ---------------------------------------------------------------------------
// mcp-memento installation (runs inside the venv)
// ---------------------------------------------------------------------------

fn install_memento(python: &Path) -> Result<(), String> {
    // Strategy 1: standard pip install
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

    // Strategy 2: PEP 668 override (Debian/Ubuntu/Fedora)
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

    Err(
        "All install strategies failed. Please install mcp-memento manually:\n  \
         pip install mcp-memento\n  \
         pip install --break-system-packages mcp-memento  (if PEP 668 blocks)"
        .to_string(),
    )
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

    // Phase 1: find a system Python to create the venv (if needed).
    let system_python = match find_python() {
        Some(p) => p,
        None => {
            log!("No Python found. Exiting.");
            std::process::exit(1);
        }
    };

    // Phase 2: ensure venv exists and is up to date.
    let venv = venv_dir();
    log!("Venv directory: {}", venv.display());

    if !venv_is_valid(&venv) {
        if let Err(e) = setup_venv(&system_python, &venv) {
            log!("Venv setup failed: {e}");
            std::process::exit(1);
        }
    }

    // Phase 3: spawn `python -u -m memento` from the venv with inherited stdio.
    //
    // Zed holds the write end of stdin and the read end of stdout open for
    // the lifetime of the process it launched (the stub).  By NOT redirecting
    // stdio on the child, Python inherits those file descriptors directly.
    // The stub then exits — Python is now the sole owner of the pipe.
    let venv_python = venv_python(&venv);
    log!("Spawning: {} -u -m memento", venv_python.display());

    let mut cmd = Command::new(&venv_python);
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
