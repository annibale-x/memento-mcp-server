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
launching it as a sub-process and proxying stdin/stdout.

Protocol: JSON-RPC 2.0, one message per line, UTF-8, no Content-Length header
(stdio transport as used by Zed's context servers).

WINDOWS NOTES
-------------
- stdout must be in binary mode or line-buffered mode to avoid buffering issues.
- sys.stdin.readline() can block indefinitely; we use a reader thread + queue.
- The process may be launched through a shell wrapper by Zed (PowerShell/cmd),
  which can affect stdin/stdout encoding — we force UTF-8 everywhere.
"""

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKAGE_NAME = "mcp-memento"
MODULE_NAME = "memento"  # importable name: PyPI package installs as `memento`
LOG_PREFIX = "[MEMENTO-BOOTSTRAP]"

_STUB_SERVER_INFO = {
    "name": "memento-bootstrap",
    "version": "0.0.0",
}

_STUB_CAPABILITIES = {
    "tools": {"listChanged": True},
    "experimental": {},
}

# ---------------------------------------------------------------------------
# stdout / stderr setup  (must happen before any I/O)
# ---------------------------------------------------------------------------


def _setup_streams() -> None:
    """
    Force stdout to binary-passthrough mode and stderr to line-buffered UTF-8.
    On Windows the default mode is text with CRLF translation and a large
    buffer — both of which break the MCP newline protocol.
    """

    # stderr: always UTF-8, line-buffered for real-time log visibility
    try:
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

    except Exception:
        pass

    # stdout: we will write exclusively via _raw_stdout (bytes) so that we
    # never lose data to codec errors or buffering.  Wrap the underlying
    # binary buffer in an explicit UTF-8 writer only as a fallback.
    global _raw_stdout

    try:
        # Python 3.x: sys.stdout.buffer is the raw binary stream
        _raw_stdout = sys.stdout.buffer

    except AttributeError:
        # Fallback (should not happen in CPython)
        _raw_stdout = sys.stdout  # type: ignore[assignment]


_raw_stdout: io.RawIOBase  # set by _setup_streams()


# ---------------------------------------------------------------------------
# Logging helpers (all to stderr so stdout stays clean for JSON-RPC)
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:

    try:
        sys.stderr.write(f"{LOG_PREFIX} {msg}\n")
        sys.stderr.flush()

    except Exception:
        pass

    # Also write to a temp file so we can debug even when Zed captures stderr.
    try:
        import tempfile

        log_path = os.path.join(tempfile.gettempdir(), "memento_bootstrap.log")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{LOG_PREFIX} {msg}\n")

    except Exception:
        pass


# ---------------------------------------------------------------------------
# JSON-RPC I/O helpers
# ---------------------------------------------------------------------------


def _send(obj: dict) -> None:
    """Serialise *obj* as a single JSON line and write it to stdout."""

    try:
        line = json.dumps(obj, separators=(",", ":")) + "\n"
        _raw_stdout.write(line.encode("utf-8"))
        _raw_stdout.flush()

    except Exception as exc:
        _log(f"_send error: {exc}")


def _send_error(request_id, code: int, message: str) -> None:

    _send(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


# ---------------------------------------------------------------------------
# Non-blocking stdin reader (thread + queue)
# ---------------------------------------------------------------------------
#
# On Windows, sys.stdin.readline() can block forever even when the peer has
# closed the connection.  Running the read in a daemon thread + draining via
# a queue allows the main thread to poll both stdin and the install_done
# event without getting stuck.

_stdin_queue: "queue.Queue[str | None]" = queue.Queue()


def _stdin_reader_thread() -> None:
    """
    Daemon thread: reads lines from stdin and pushes them onto _stdin_queue.
    A None sentinel is pushed on EOF or error.
    """

    try:
        # Force binary reads then decode manually so we control the codec.
        raw_in = getattr(sys.stdin, "buffer", sys.stdin)

        while True:
            try:
                raw_line = raw_in.readline()

            except Exception as exc:
                _log(f"stdin read error: {exc}")
                break

            if not raw_line:
                break

            try:
                line = raw_line.decode("utf-8").rstrip("\r\n")

            except Exception:
                line = raw_line.decode("latin-1").rstrip("\r\n")

            _stdin_queue.put(line)

    finally:
        _stdin_queue.put(None)  # EOF sentinel


def _read_line_nonblocking(timeout: float = 0.1) -> "str | None | object":
    """
    Try to get one line from the stdin queue.

    Returns:
        str   — a line of text (stripped)
        None  — EOF / stdin closed
        _TIMEOUT  — no data within *timeout* seconds (caller should retry)
    """

    try:
        return _stdin_queue.get(timeout=timeout)

    except queue.Empty:
        return _TIMEOUT


_TIMEOUT = object()  # sentinel for "no data yet"


# ---------------------------------------------------------------------------
# Pip installation helpers
# ---------------------------------------------------------------------------


def _is_installed() -> bool:
    """Return True if the memento module is importable from the current Python."""

    try:
        import importlib.util

        spec = importlib.util.find_spec(MODULE_NAME)
        result = spec is not None
        _log(f"_is_installed check: {result} (spec={spec})")
        return result

    except Exception as exc:
        _log(f"_is_installed error: {exc}")
        return False


def _install_package() -> "tuple[bool, str]":
    """Install mcp-memento via pip --user.  Returns (success, error_message)."""

    _log(f"Installing {PACKAGE_NAME} via pip …")
    _log(f"Using Python: {sys.executable}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )

        stdout_snippet = (result.stdout or "").strip()[-500:]
        stderr_snippet = (result.stderr or "").strip()[-500:]

        _log(f"pip stdout: {stdout_snippet}")
        _log(f"pip stderr: {stderr_snippet}")

        if result.returncode == 0:
            _log(f"{PACKAGE_NAME} installed successfully.")
            return True, ""

        error = stderr_snippet or stdout_snippet or f"rc={result.returncode}"
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
# Real-server proxy
# ---------------------------------------------------------------------------


def _launch_real_server() -> subprocess.Popen:
    """Start the real mcp-memento process and return the Popen object."""

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [sys.executable, "-u", "-m", MODULE_NAME]
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
    pending_requests: "list[str]",
) -> None:
    """
    Forward stdin → real_proc.stdin and real_proc.stdout → stdout.
    Also drains any requests that arrived during installation.
    """

    _log(f"Entering proxy loop. Buffered requests to replay: {len(pending_requests)}")

    def _forward_real_stdout() -> None:

        try:
            assert real_proc.stdout is not None

            while True:
                chunk = real_proc.stdout.read(4096)

                if not chunk:
                    break

                _raw_stdout.write(chunk)
                _raw_stdout.flush()

        except Exception as exc:
            _log(f"stdout-forwarder error: {exc}")

    fwd_thread = threading.Thread(target=_forward_real_stdout, daemon=True)
    fwd_thread.start()

    assert real_proc.stdin is not None

    # Replay buffered requests from the stub phase.
    for buffered in pending_requests:
        if buffered:
            _log(f"Replaying: {buffered[:120]}")

            try:
                real_proc.stdin.write((buffered + "\n").encode("utf-8"))

            except Exception as exc:
                _log(f"Replay write error: {exc}")

    try:
        real_proc.stdin.flush()

    except Exception:
        pass

    # Forward new stdin lines to real server via the queue.
    try:
        while True:
            item = _stdin_queue.get(timeout=1.0)

            if item is None:
                _log("stdin EOF — closing real server stdin.")
                break

            try:
                real_proc.stdin.write((item + "\n").encode("utf-8"))
                real_proc.stdin.flush()

            except Exception as exc:
                _log(f"Forward write error: {exc}")
                break

    except queue.Empty:
        pass

    except Exception as exc:
        _log(f"stdin-forwarder error: {exc}")

    finally:
        try:
            real_proc.stdin.close()

        except Exception:
            pass

    real_proc.wait()
    _log(f"Real server exited with code {real_proc.returncode}.")


# ---------------------------------------------------------------------------
# Stub MCP loop
# ---------------------------------------------------------------------------


def _handle_stub_request(request: dict) -> None:
    """Respond to a single JSON-RPC request with stub responses."""

    request_id = request.get("id")
    method = request.get("method", "")

    _log(f"Stub handling method={method!r} id={request_id!r}")

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
        return

    if method == "initialized":
        # Notification — no response needed.
        return

    if method == "tools/list":
        _send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": []},
            }
        )
        _log("Stub: sent empty tools/list (installation in progress).")
        return

    if method == "tools/call":
        _send_error(
            request_id,
            -32603,
            "mcp-memento is being installed, please retry in a moment.",
        )
        return

    if method == "ping":
        if request_id is not None:
            _send({"jsonrpc": "2.0", "id": request_id, "result": {}})
        return

    # Unknown method — respond with method-not-found (only if it has an id).
    if request_id is not None:
        _send_error(request_id, -32601, f"Method not found: {method}")


def _stub_loop(
    install_done: threading.Event,
    buffered: "list[str]",
) -> None:
    """
    Read JSON-RPC requests from the stdin queue, answer with stub responses,
    and buffer lines so they can be replayed to the real server.
    Exits when installation completes.
    """

    _log("Stub loop started — waiting for MCP requests while installing …")

    while not install_done.is_set():
        item = _read_line_nonblocking(timeout=0.05)

        if item is _TIMEOUT:
            # No data yet — keep polling the install_done flag.
            continue

        if item is None:
            _log("stdin closed during stub loop.")
            sys.exit(0)

        line: str = item  # type: ignore[assignment]

        if not line:
            continue

        buffered.append(line)

        try:
            request = json.loads(line)

        except json.JSONDecodeError:
            _log(f"Invalid JSON received: {line[:200]}")
            continue

        _handle_stub_request(request)

    # Drain any lines that arrived in the last poll window.
    while True:
        try:
            item = _stdin_queue.get_nowait()

        except queue.Empty:
            break

        if item is None:
            break

        if item:
            buffered.append(item)

            try:
                _handle_stub_request(json.loads(item))

            except Exception:
                pass

    _log("Stub loop exiting — installation complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:

    _setup_streams()

    _log(
        f"Bootstrap starting. "
        f"Python {sys.version.split()[0]} @ {sys.executable} | "
        f"platform={sys.platform} | "
        f"cwd={os.getcwd()}"
    )

    # Start the stdin reader thread immediately so no bytes are lost.
    reader_thread = threading.Thread(
        target=_stdin_reader_thread, daemon=True, name="stdin-reader"
    )
    reader_thread.start()
    _log("stdin reader thread started.")

    # --- Fast path: already installed ---
    already_installed = _is_installed()

    if already_installed:
        _log(f"{PACKAGE_NAME} already installed — launching directly.")
        real_proc = _launch_real_server()
        _proxy_loop(real_proc, [])
        rc = real_proc.returncode

        if rc is None:
            rc = 0

        sys.exit(rc)

    # --- Slow path: install in background, stub in foreground ---
    install_done = threading.Event()
    install_result: "list[tuple[bool, str]]" = []

    def _install_thread_fn() -> None:

        success, error = _install_package()
        install_result.append((success, error))
        install_done.set()

    install_thread = threading.Thread(
        target=_install_thread_fn,
        daemon=True,
        name="pip-install",
    )
    install_thread.start()
    _log("pip install thread started.")

    buffered_requests: "list[str]" = []
    _stub_loop(install_done, buffered_requests)

    install_thread.join(timeout=10)

    if not install_result:
        _log("Installation result missing — aborting.")
        sys.exit(1)

    success, error = install_result[0]

    if not success:
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

    # Refresh sys.path so the freshly-installed package is importable.
    import importlib
    import site

    importlib.invalidate_caches()

    user_site = site.getusersitepackages()

    if user_site not in sys.path:
        sys.path.insert(0, user_site)
        _log(f"Added user site-packages to sys.path: {user_site}")

    real_proc = _launch_real_server()
    _proxy_loop(real_proc, buffered_requests)
    rc = real_proc.returncode

    if rc is None:
        rc = 0

    sys.exit(rc)


if __name__ == "__main__":
    main()
