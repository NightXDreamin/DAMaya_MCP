import os
import sys
import json
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
REQ_TXT = os.path.join(PROJECT_ROOT, "requirements.txt")


def ensure_venv():
    """
    Ensure a local virtual environment exists and dependencies are installed.

    - If .venv/Scripts/python.exe is missing, create the venv via `python -m venv`.
    - Then pip-install requirements.txt into it.

    Returns the actual Python interpreter path to use for running the MCP server
    (venv python when available, otherwise falls back to the current sys.executable).
    """
    print("[*] Checking virtual environment python...")

    if not os.path.exists(VENV_PYTHON):
        print(f"[!] Virtual environment not found at: {VENV_PYTHON}")
        print("[*] Creating virtual environment (.venv) ...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", VENV_DIR],
                check=True
            )
            print(f"[+] Created virtual environment at: {VENV_DIR}")
        except subprocess.CalledProcessError as err:
            print(f"[!] Error: Failed to create virtual environment: {err}")
            print(f"[!] Falling back to system Python: {sys.executable}")
            return sys.executable.replace('\\', '/')
        except Exception as err:
            print(f"[!] Error: Failed to create virtual environment: {err}")
            print(f"[!] Falling back to system Python: {sys.executable}")
            return sys.executable.replace('\\', '/')

    # At this point the venv interpreter should exist; double-check before using it
    if not os.path.exists(VENV_PYTHON):
        print(f"[!] Virtual environment python still missing, falling back to: {sys.executable}")
        return sys.executable.replace('\\', '/')

    if os.path.exists(REQ_TXT):
        print("[*] Installing requirements into virtual environment ...")
        try:
            subprocess.run(
                [VENV_PYTHON, "-m", "pip", "install", "-r", REQ_TXT],
                capture_output=True, text=True, check=True
            )
            print("[+] Pip packages successfully installed/verified!")
        except subprocess.CalledProcessError as err:
            print("[!] Warning: Pip installation failed:")
            print(err.stderr)
    else:
        print(f"[!] Warning: requirements.txt not found at: {REQ_TXT}")

    return VENV_PYTHON.replace('\\', '/')


def display_configuration(python_cmd):
    """
    Generates and prints the standard JSON block for Claude Desktop/other clients,
    giving the user full visibility and control to manual paste.
    """
    # Define our server settings using standardized forward slashes
    server_script = os.path.join(PROJECT_ROOT, "main.py").replace('\\', '/')

    server_settings = {
        "damaya": {
            "command": python_cmd,
            "args": [server_script]
        }
    }

    # Resolve typical AppData path for reference
    appdata = os.environ.get("APPDATA", "C:/Users/<Username>/AppData/Roaming")
    typical_config_path = os.path.join(appdata, "Claude", "claude_desktop_config.json").replace('\\', '/')

    print()
    print("=" * 60)
    print("              MANUAL CONFIGURATION GUIDE (手动配置指南)")
    print("=" * 60)
    print("Please copy the JSON block below (请复制并粘贴下方 JSON 块到您的客户端配置中):")
    print()
    print(json.dumps(server_settings, indent=4))
    print()
    print("=" * 60)
    print("Typical Configuration Files Locations (常用配置存放路径):")
    print(f"- Claude Desktop (Windows):")
    print(f"  {typical_config_path}")
    print("- Cursor/VS Code:")
    print("  Paste directly into your custom MCP servers setup in settings.")
    print("=" * 60)
    return True


def main():
    print("=" * 60)
    print("      DAMaya MCP Client Configuration Helper")
    print("=" * 60)

    # Step 1: Ensure venv exists + dependencies installed, get the python to use
    python_cmd = ensure_venv()

    # Step 2: Display paths and JSON manual block
    display_configuration(python_cmd)

    print("Next steps:")
    print("1. Copy the JSON block printed above.")
    print("2. Paste it into your preferred MCP client's configuration file.")
    print("3. Restart your MCP client and enjoy AI-guided Maya automation!")
    print("=" * 60)

    # Keep the console window open on Windows double-clicks so the user can easily copy
    print()
    input(">>> Press [Enter] to exit and close this window (按回车键关闭该窗口)...")


if __name__ == "__main__":
    main()
