//! Minimal test: can we replace the current process with Python on Windows?
//!
//! Tests two approaches:
//!   1. std::os::unix::process::CommandExt::exec() — not available on Windows
//!   2. Windows CreateProcess + exit() — effectively the same result
//!   3. Python via _execvp equivalent using a raw Win32 call
//!
//! Run with:
//!   cargo run --bin test_exec --target x86_64-pc-windows-msvc
//!
//! Expected output: Python starts and reads from stdin normally (no proxy).

use std::process::Command;

fn main() {
    eprintln!("[test_exec] pid={}", std::process::id());
    eprintln!(
        "[test_exec] Attempting to replace process with: py.exe -c \"import sys; print('Python started, reading stdin...'); [print('echo:', l.rstrip()) for l in sys.stdin]\""
    );

    // On Unix this would be exec() — process image replaced, same PID, same stdin/stdout.
    // On Windows there is no true exec(). We test two fallbacks:

    // --- Approach 1: CommandExt::exec() via the unix trait (compile-time gated) ---
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        eprintln!("[test_exec] Unix: using CommandExt::exec()");
        let err = Command::new("python3")
            .args(["-c", "import sys; print('Python started'); [print('echo:', l.rstrip()) for l in sys.stdin]"])
            .exec(); // never returns on success
        eprintln!("[test_exec] exec() failed: {}", err);
        std::process::exit(1);
    }

    // --- Approach 2: Windows — spawn + exit(child.wait()) ---
    // This is NOT a true exec(): two processes exist briefly.
    // BUT stdin/stdout are inherited, so from Zed's perspective it is transparent.
    #[cfg(windows)]
    {
        eprintln!("[test_exec] Windows: spawning py.exe with inherited stdio, then exiting self");

        let status = Command::new("py.exe")
            .args([
                "-c",
                "import sys; print('Python started, reading stdin...', flush=True); [print('echo:', l.rstrip(), flush=True) for l in sys.stdin]",
            ])
            // Inherit stdin/stdout/stderr from the current process.
            // No .stdin()/.stdout()/.stderr() calls = inherit by default.
            .status();

        match status {
            Ok(s) => {
                eprintln!("[test_exec] py.exe exited with: {}", s);
                std::process::exit(s.code().unwrap_or(1));
            }
            Err(e) => {
                eprintln!("[test_exec] Failed to spawn py.exe: {}", e);
                std::process::exit(1);
            }
        }
    }
}
