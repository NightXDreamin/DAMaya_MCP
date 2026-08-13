import os
import sys
import subprocess
import signal

from src.core.config import PROJECT_ROOT, CONFIG_FILE, get_config, save_config

VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
SERVER_PY = os.path.join(PROJECT_ROOT, "main.py")
PID_FILE = os.path.join(PROJECT_ROOT, ".mcp_server.pid")

# Ensure Windows compatibility
if not VENV_PYTHON.endswith(".exe") and os.name == "nt":
    VENV_PYTHON += ".exe"


def should_autostart():
    """
    Check if MCP background server should start automatically on Maya launch.
    """
    return get_config().get("autostart", True)


def set_autostart(enabled: bool):
    """
    Toggle autostart preference.
    """
    cfg = get_config()
    cfg["autostart"] = enabled
    save_config(cfg)


def get_python_executable():
    """
    Find the virtual environment's Python interpreter.
    Falls back to sys.executable if .venv interpreter is missing.
    """
    if os.path.exists(VENV_PYTHON):
        return VENV_PYTHON
    return sys.executable


def is_process_running(pid: int) -> bool:
    """
    Checks if a process with a given PID is currently active.
    """
    if pid <= 0:
        return False
    try:
        # Works on Windows (Python 3+) and Unix to check process existence
        os.kill(pid, 0)
        return True
    except OSError as err:
        import errno
        # EPERM means process exists but we lack permissions; ESRCH means process does not exist
        return err.errno == errno.EPERM
    except Exception:
        # Fallback in case os.kill is restricted or throws unexpected errors
        try:
            if os.name == "nt":
                out = subprocess.check_output(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                ).decode("utf-8", errors="ignore")
                return str(pid) in out
            return False
        except Exception:
            return False


def get_running_server_pid():
    """
    Reads the background server PID from the tracker file.
    Returns 0 if no server or process is dead.
    """
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                return pid
            else:
                # Process is dead, clean up obsolete PID file
                os.remove(PID_FILE)
        except Exception:
            pass
    return 0


def is_server_running() -> bool:
    """
    Public API to check if background server is active.
    """
    return get_running_server_pid() > 0


def start_server():
    """
    Launches the external MCP server (main.py) in the background.
    Returns a tuple: (success: bool, message: str)
    """
    pid = get_running_server_pid()
    if pid > 0:
        return True, f"Server is already running with PID {pid}."

    python_bin = get_python_executable()
    if not os.path.exists(SERVER_PY):
        return False, f"Server entry point file not found at: {SERVER_PY}"

    try:
        # Start the MCP server entry point (main.py) in the background
        # CREATE_NO_WINDOW ensures no empty command prompt window pops up on Windows
        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            [python_bin, SERVER_PY],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo
        )

        # Record PID
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))

        return True, f"Server successfully started in background (PID {proc.pid})."
    except Exception as e:
        return False, f"Failed to launch background server: {str(e)}"


def stop_server():
    """
    Terminates the running background server process.
    Returns a tuple: (success: bool, message: str)
    """
    pid = get_running_server_pid()
    if pid == 0:
        return True, "Server is not running."

    try:
        if os.name == "nt":
            # Graceful terminate via taskkill
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            os.kill(pid, signal.SIGTERM)

        # Double check cleanup
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        return True, f"Server process {pid} successfully stopped."
    except Exception as e:
        # Force remove the tracker file anyway to allow restart
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return False, f"Error terminating process {pid}: {str(e)}"


def restart_server():
    """
    Restarts the background server process.
    """
    stop_success, stop_msg = stop_server()
    start_success, start_msg = start_server()
    return start_success, f"{stop_msg} -> {start_msg}"
