@echo off
rem DAMaya MCP background server launcher (Windows)
rem Runs the MCP server entry point (main.py) using the local virtual environment.

rem Change to the directory containing this script (no hardcoded absolute path)
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "main.py"
) else (
    echo [DAMaya MCP] Virtual environment not found.
    echo             Run the following to set it up:
    echo             python -m venv .venv
    echo             .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)
