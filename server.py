import os
import sys
from src.core.orchestrator import MayaOrchestrator

if __name__ == "__main__":
    # Write current process PID to tracker file
    # This allows Maya's Control Panel to immediately auto-detect the server status,
    # regardless of whether it was spawned by Maya, Claude Desktop, or manual terminal.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pid_file = os.path.join(current_dir, ".mcp_server.pid")
    
    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    try:
        # Instantiate and start the FastMCP orchestrator
        orchestrator = MayaOrchestrator(port=7022)
        orchestrator.run()
    finally:
        # Ensure cleanup of the PID tracker file on graceful exit
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception:
            pass