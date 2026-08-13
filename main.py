import sys
import io

class WritableTextIOWrapper(io.TextIOWrapper):
    def __init__(self, original_stream, *args, **kwargs):
        super(WritableTextIOWrapper, self).__init__(original_stream, *args, **kwargs)
        self._buffer = original_stream
    @property
    def buffer(self):
        return self._buffer
    @buffer.setter
    def buffer(self, value):
        self._buffer = value

sys.stdin = WritableTextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding, errors=sys.stdin.errors)
sys.stdout = WritableTextIOWrapper(sys.stdout.buffer, encoding=sys.stdout.encoding, errors=sys.stdout.errors, line_buffering=True)
sys.stderr = WritableTextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding, errors=sys.stderr.errors, line_buffering=True)

import os
import subprocess
import logging
import traceback

# Auto-redirect to virtual environment python if not already running under it
project_root = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")

if os.path.exists(venv_python) and os.path.normpath(sys.executable).lower() != os.path.normpath(venv_python).lower():
    # Force flushing of any outstanding prints
    sys.stdout.flush()
    sys.stderr.flush()
    # Re-spawn using the virtual environment python
    cmd = [venv_python] + sys.argv
    res = subprocess.run(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    sys.exit(res.returncode)

# FORCE all logging to stderr to prevent breaking JSON-RPC over stdout
logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)


project_root = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_root, "mcp_server_debug.log")

def log(msg):
    try:
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass

log("=" * 50)
log("main.py started!")
log(f"sys.executable: {sys.executable}")
log(f"sys.argv: {sys.argv}")
log(f"sys.path: {sys.path}")
log(f"cwd: {os.getcwd()}")

try:
    # Ensure the project root is in the path
    sys.path.insert(0, project_root)
    
    from src import __version__
    log(f"========== DAMaya MCP v{__version__} starting ==========")
    
    log("Importing MayaOrchestrator...")
    from src.core.orchestrator import MayaOrchestrator
    log("MayaOrchestrator imported successfully!")

    if __name__ == "__main__":
        # Write current process PID to tracker file
        pid_file = os.path.join(project_root, ".mcp_server.pid")
        try:
            with open(pid_file, "w") as f:
                f.write(str(os.getpid()))
            log(f"Wrote PID {os.getpid()} to {pid_file}")
        except Exception as pe:
            log(f"Failed to write PID file: {pe}")

        try:
            log("Initializing MayaOrchestrator...")
            orchestrator = MayaOrchestrator()
            log("MayaOrchestrator initialized successfully! Starting MCP server run...")
            orchestrator.mcp.run()
            log("MCP server run finished gracefully.")
        except Exception as e:
            log(f"CRASH during initialization or run: {e}")
            log(traceback.format_exc())
            raise
        finally:
            # Ensure cleanup of the PID tracker file on graceful exit
            try:
                if os.path.exists(pid_file):
                    os.remove(pid_file)
                log("Cleaned up PID file.")
            except Exception as pe:
                log(f"Failed to clean up PID file: {pe}")

except Exception as e:
    log(f"TOP-LEVEL CRASH: {e}")
    log(traceback.format_exc())
    raise
