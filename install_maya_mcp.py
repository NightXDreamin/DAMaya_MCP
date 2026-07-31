import os
import sys

# Get project root folder absolute path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')


def get_windows_documents_folder():
    """
    Directly query Windows Registry to locate the official User Documents folder.
    Handles OneDrive and redirected system folders flawlessly.
    """
    if os.name == 'nt':
        try:
            import winreg
            sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                val, type_id = winreg.QueryValueEx(key, "Personal")
                return os.path.expandvars(val)
        except Exception:
            pass
    # Fallback to standard userprofile path
    return os.path.join(os.path.expanduser("~"), "Documents")


def main():
    print("=" * 60)
    print("         DAMaya MCP Native Integration Installer")
    print("=" * 60)

    # 1. Resolve Maya scripts directory
    docs_folder = get_windows_documents_folder()
    maya_scripts_dir = os.path.join(docs_folder, "maya", "scripts")
    user_setup_path = os.path.join(maya_scripts_dir, "userSetup.py")

    print(f"[*] Target Documents Folder: {docs_folder}")
    print(f"[*] Target Maya Scripts Dir: {maya_scripts_dir}")

    # Ensure scripts directory exists
    if not os.path.exists(maya_scripts_dir):
        try:
            os.makedirs(maya_scripts_dir)
            print("[+] Created missing Maya scripts directory.")
        except Exception as e:
            print(f"[!] Error: Failed to create scripts directory: {e}")
            sys.exit(1)

    # 2. Build the startup code block
    hook_start = "# --- DAMaya MCP Startup Hook ---"
    hook_end = "# --- End of DAMaya MCP Startup Hook ---"
    
    hook_code = f"""{hook_start}
import sys
import os

project_path = r"{PROJECT_ROOT}"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

try:
    import maya.utils as mutils
    
    def _damaya_mcp_startup():
        import maya.cmds as cmds
        from src.core import config as _mcp_config
        
        # 1. Open Command Port (端口从 config.json 读取)
        port_str = ":{0}".format(_mcp_config.get_port())
        if not cmds.commandPort(port_str, q=True):
            try:
                # sourceType=python, echoOutput=False
                cmds.commandPort(n=port_str, sourceType="python", echoOutput=False)
                print("DAMaya MCP: CommandPort {0} successfully opened.".format(port_str))
            except Exception as e:
                print("DAMaya MCP Error: Failed to open CommandPort {0}: {1}".format(port_str, e))
        else:
            print("DAMaya MCP: CommandPort {0} is already open.".format(port_str))

        # 2. Register Native Menu
        try:
            from src.core import maya_menu
            maya_menu.create_menu()
            print("DAMaya MCP: Native menus successfully integrated.")
        except Exception as e:
            print(f"DAMaya MCP Error: Failed to build menus: {{e}}")

        # 3. Boot Background Server if configured
        try:
            from src.core import server_manager
            if server_manager.should_autostart():
                success, msg = server_manager.start_server()
                print(f"DAMaya MCP: Auto-start background server -> {{msg}}")
        except Exception as e:
            print(f"DAMaya MCP Error: Failed to run background server: {{e}}")

    # Deferred execution to ensure Maya UI is fully initialized before adding menus
    mutils.executeDeferred(_damaya_mcp_startup)

except Exception as startup_err:
    print(f"DAMaya MCP Startup Hook failed: {{startup_err}}")
{hook_end}"""

    # 3. Read or create userSetup.py
    existing_content = ""
    if os.path.exists(user_setup_path):
        try:
            with open(user_setup_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            print(f"[*] Found existing userSetup.py at: {user_setup_path}")
        except Exception as e:
            print(f"[!] Error: Failed to read existing userSetup.py: {e}")
            sys.exit(1)
    else:
        print(f"[*] Creating new userSetup.py at: {user_setup_path}")

    # 4. Write/Update hook in userSetup.py idempotently
    try:
        new_content = ""
        if hook_start in existing_content and hook_end in existing_content:
            # Replaced existing hook block
            print("[*] DAMaya MCP hook is already present. Updating block contents...")
            start_idx = existing_content.find(hook_start)
            end_idx = existing_content.find(hook_end) + len(hook_end)
            new_content = existing_content[:start_idx] + hook_code + existing_content[end_idx:]
        else:
            # Append hook block
            print("[+] Adding new DAMaya MCP hook to userSetup.py...")
            separator = "\n\n" if existing_content else ""
            new_content = existing_content + separator + hook_code

        with open(user_setup_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("[SUCCESS] userSetup.py successfully updated!")
        print("=" * 60)
        print("Installation complete! Next steps:")
        print("1. Restart Maya if it is already open.")
        print("2. Maya will auto-open the commandPort, boot MCP, and create 'DAMaya MCP' menus.")
        print("3. Open Maya menu 'DAMaya MCP' -> 'Control Panel' to explore the UI.")
        print("=" * 60)

    except Exception as e:
        print(f"[!] Error: Failed to write to userSetup.py: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
