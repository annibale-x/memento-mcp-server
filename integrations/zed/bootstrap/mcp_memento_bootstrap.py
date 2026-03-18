#!/usr/bin/env python3
"""
mcp_memento_bootstrap.py
------------------------
Bootstrap launcher for the mcp-memento MCP server.

This script is downloaded by the Zed extension and placed in the extension's
working directory. On first run it installs mcp-memento (and its deps) via pip
into the user's site-packages, then hands off to the real server process.

KEY DESIGN CONSTRAINT
---------------------
Zed expects the MCP handshake (initialize request/response) to complete within
~60 seconds from process start.  Installation via pip can exceed that easily.

Solution: answer the initialize request IMMEDIATELY with a stub response that
advertises zero tools, then install in the background.  Once installation is
done, replace the stub response loop with the real mcp-memento process by
exec()-ing into it (Unix) or launching it as a sub-process and proxying
stdin/stdout (Windows/all platforms).

Protocol: JSON-RPC 2.0, one message per line, UTF-8, no Content-Length header
(stdio transport as used by Zed's context servers).
"""

import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKAGE_NAME = "mcp-memento"
LOG_PREFIX = "[MEMENTO-BOOTSTRAP]"

# Log file written to user home so it survives across Zed restarts.
_LOG_FILE = Path.home() / ".mcp-memento" / "bootstrap.log"

# Minimum stub capabilities – zero tools, but the schema is correct.
_STUB_SERVER_INFO = {
    "name": "memento-bootstrap",
    "version": "0.0.0",
}

_STUB_CAPABILITIES = {
    "tools": {"listChanged": False},
    "experimental": {},
}


# ---------------------------------------------------------------------------
# Logging helpers (all to stderr so stdout stays clean for JSON-RPC)
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = f"{ts} {LOG_PREFIX} {msg}\n"

    sys.stderr.write(line)
    sys.stderr.flush()

    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)

    except Exception:
        pass


# ---------------------------------------------------------------------------
# JSON-RPC I/O helpers
# ---------------------------------------------------------------------------


def _send(obj: dict) -> None:

    line = json.dumps(obj, separators=(",", ":"))
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _send_error(request_id, code: int, message: str) -> None:

    _send(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


def _read_line() -> str | None:
    """Read one line from stdin.  Returns None on EOF."""

    try:
        line = sys.stdin.readline()

        if not line:
            return None

        return line.strip()

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pip installation helpers
# ---------------------------------------------------------------------------


def _is_installed() -> bool:

    try:
        import importlib.util

        return importlib.util.find_spec("memento") is not None

    except Exception:
        return False


def _install_package() -> tuple[bool, str]:
    """Install mcp-memento via pip --user.  Returns (success, error_message)."""

    _log(f"Installing {PACKAGE_NAME} via pip …")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            _log(f"{PACKAGE_NAME} installed successfully.")
            return True, ""

        error = result.stderr.strip() or result.stdout.strip()
        _log(f"pip failed (rc={result.returncode}): {error}")
        return False, error

    except subprocess.TimeoutExpired:
        msg = "pip install timed out after 5 minutes."
        _log(msg)
        return False, msg

    except Exception as exc:
        msg = f"Unexpected error during pip install: {exc}"
        _log(msg)
        return False, msg


# ---------------------------------------------------------------------------
# Real-server proxy (used after installation completes)
# ---------------------------------------------------------------------------


def _launch_real_server() -> subprocess.Popen:
    """Start the real mcp-memento process and return the Popen object."""

    env = os.environ.copy()

    cmd = [sys.executable, "-u", "-m", "memento"]
    _log(f"Launching real server: {' '.join(cmd)}")

    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        env=env,
    )


def _proxy_loop(
    real_proc: subprocess.Popen,
    pending_requests: list[str],
) -> None:
    """
    Forward stdin → real_proc.stdin and real_proc.stdout → stdout.
    Also drains any requests that arrived during installation.
    """

    def _forward_stdout() -> None:

        try:
            assert real_proc.stdout is not None

            for raw_line in real_proc.stdout:
                # Normalize CRLF → LF: on Windows the subprocess stdout may
                # emit \r\n which confuses Zed's JSON-RPC line reader.
                normalized = raw_line.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                sys.stdout.buffer.write(normalized)
                sys.stdout.buffer.flush()

        except Exception as exc:
            _log(f"stdout-forwarder error: {exc}")

    # Start background thread that copies real server output to Zed.
    t = threading.Thread(target=_forward_stdout, daemon=True)
    t.start()

    # Replay buffered requests that arrived while installing.
    assert real_proc.stdin is not None

    for buffered in pending_requests:
        _log(f"Replaying buffered request: {buffered[:120]}")
        real_proc.stdin.write((buffered + "\n").encode())

    real_proc.stdin.flush()

    # Forward new stdin lines to real server.
    try:
        for raw_line in sys.stdin:
            real_proc.stdin.write(
                raw_line.encode() if isinstance(raw_line, str) else raw_line
            )
            real_proc.stdin.flush()

    except Exception as exc:
        _log(f"stdin-forwarder error: {exc}")

    finally:
        real_proc.stdin.close()

    real_proc.wait()
    _log(f"Real server exited with code {real_proc.returncode}.")


# ---------------------------------------------------------------------------
# Stub MCP loop (runs while mcp-memento is being installed)
# ---------------------------------------------------------------------------


def _handle_stub_request(request: dict, install_done: threading.Event) -> bool:
    """
    Handle a single JSON-RPC request with stub responses.
    Returns True when the stub loop should exit (installation done + initialize ack sent),
    or False to keep looping.
    """

    request_id = request.get("id")
    method = request.get("method", "")

    if method == "initialize":
        _send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": _STUB_CAPABILITIES,
                    "serverInfo": _STUB_SERVER_INFO,
                },
            }
        )
        _log("Stub: sent initialize response.")
        return False

    if method == "initialized":
        # Notification, no id, no response needed.
        return False

    if method == "tools/list":
        _send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": []},
            }
        )
        _log("Stub: sent empty tools/list (installation in progress).")
        return False

    if method == "tools/call":
        _send_error(
            request_id,
            -32603,
            "mcp-memento is being installed, please retry in a moment.",
        )
        return False

    # Unknown method – respond with method-not-found.
    if request_id is not None:
        _send_error(request_id, -32601, f"Method not found: {method}")

    return False


def _stub_loop(
    install_done: threading.Event,
    install_result: list,
    buffered: list[str],
) -> None:
    """
    Read JSON-RPC requests from stdin, answer them with stub responses,
    and buffer everything so it can be replayed to the real server.
    Runs until installation completes and stdin is transferred to _proxy_loop.
    """

    _log("Stub loop started – waiting for MCP requests while installing …")

    while not install_done.is_set():
        line = _read_line()

        if line is None:
            _log("stdin closed during stub loop.")
            sys.exit(0)

        if not line:
            continue

        buffered.append(line)

        try:
            request = json.loads(line)

        except json.JSONDecodeError:
            _log(f"Invalid JSON received: {line[:200]}")
            continue

        _handle_stub_request(request, install_done)

    _log("Installation complete – exiting stub loop.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:

    _log(f"Bootstrap starting. Python {sys.version.split()[0]} @ {sys.executable}")

    # Make stdout binary-safe on Windows.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True)

        except Exception:
            pass

    # --- Check if already installed ---
    already_installed = _is_installed()

    if already_installed:
        _log(f"{PACKAGE_NAME} is already installed – launching directly.")
        # No need to stub: just exec into the real server immediately.
        real_proc = _launch_real_server()
        _proxy_loop(real_proc, [])
        sys.exit(real_proc.returncode if real_proc.returncode is not None else 0)

    # --- Not installed: start background installation ---
    install_done = threading.Event()
    install_result: list = []  # Will hold (success: bool, error: str)

    def _install_thread_fn() -> None:

        success, error = _install_package()
        install_result.append((success, error))
        install_done.set()

    install_thread = threading.Thread(target=_install_thread_fn, daemon=True)
    install_thread.start()

    # --- Run stub loop in the MAIN THREAD (owns stdin) ---
    buffered_requests: list[str] = []

    _stub_loop(install_done, install_result, buffered_requests)

    # --- Installation finished: check result ---
    install_thread.join(timeout=5)

    if not install_result:
        _log("Installation result missing – aborting.")
        sys.exit(1)

    success, error = install_result[0]

    if not success:
        # Notify Zed via a JSON-RPC error notification so the user sees it.
        _send(
            {
                "jsonrpc": "2.0",
                "method": "$/logMessage",
                "params": {
                    "type": 1,
                    "message": f"mcp-memento installation failed: {error}",
                },
            }
        )
        _log(f"Installation failed: {error}")
        sys.exit(1)

    # --- Hand off to real server ---
    # Reload sys.path so pip's newly installed package is visible.
    import importlib
    import site

    importlib.invalidate_caches()

    # Re-add user site-packages in case it wasn't on the path initially.
    user_site = site.getusersitepackages()

    if user_site not in sys.path:
        sys.path.insert(0, user_site)

    real_proc = _launch_real_server()
    _proxy_loop(real_proc, buffered_requests)
    sys.exit(real_proc.returncode if real_proc.returncode is not None else 0)


if __name__ == "__main__":
    main()
