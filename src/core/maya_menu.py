import maya.cmds as cmds
import maya.mel as mel

from src.core import config

MENU_NAME = "DAMayaMCPMenu"


def create_menu():
    """
    Creates the DAMaya MCP top-level menu in Maya's main window.
    """
    port_str = ":{0}".format(config.get_port())
    # Safeguard for batch/command-line mode
    if cmds.about(batch=True):
        return

    # Delete existing menu to avoid duplicates
    delete_menu()

    # Get Maya's main window menu bar
    # 'gMainWindow' is the global Maya MEL variable for the main window menu bar
    gMainWindow = mel.eval("$tmp = $gMainWindow;")
    if not gMainWindow:
        return

    # Create the menu
    main_menu = cmds.menu(MENU_NAME, label="DAMaya MCP", parent=gMainWindow, tearOff=True)

    # 1. Main UI Window Action
    cmds.menuItem(
        label="Control Panel (控制面板)",
        command=lambda *args: _show_control_panel()
    )
    cmds.menuItem(divider=True)

    # 2. Server Management Submenu
    server_menu = cmds.menuItem(label="Server Management (服务管理)", subMenu=True, tearOff=True)
    
    cmds.menuItem(label="Start Background Server (启动服务)", command=lambda *args: _start_server())
    cmds.menuItem(label="Stop Background Server (停止服务)", command=lambda *args: _stop_server())
    cmds.menuItem(label="Restart Background Server (重启服务)", command=lambda *args: _restart_server())
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Open CommandPort " + port_str + " (开启端口)", command=lambda *args: _open_port())
    cmds.menuItem(label="Close CommandPort " + port_str + " (关闭端口)", command=lambda *args: _close_port())
    
    cmds.setParent(main_menu, menu=True)
    cmds.menuItem(divider=True)

    # 3. Quick Diagnostics
    cmds.menuItem(label="Get Selection Context (获取选择上下文)", command=lambda *args: _run_selection_context())
    cmds.menuItem(divider=True)
    
    # 4. Help / Readme
    cmds.menuItem(label="Help & Readme (帮助文档)", command=lambda *args: _show_help())


def delete_menu():
    """
    Cleans up the menu if it exists.
    """
    if cmds.menu(MENU_NAME, q=True, exists=True):
        cmds.deleteUI(MENU_NAME)


# --- Helper Callbacks to Avoid Circular Imports or Startup Issues ---

def _show_control_panel():
    from src.core import maya_ui
    maya_ui.show_window()


def _start_server():
    from src.core import server_manager
    success, msg = server_manager.start_server()
    cmds.confirmDialog(title="DAMaya MCP", message=msg, button=["OK"])


def _stop_server():
    from src.core import server_manager
    success, msg = server_manager.stop_server()
    cmds.confirmDialog(title="DAMaya MCP", message=msg, button=["OK"])


def _restart_server():
    from src.core import server_manager
    success, msg = server_manager.restart_server()
    cmds.confirmDialog(title="DAMaya MCP", message=msg, button=["OK"])


def _open_port():
    port_str = ":{0}".format(config.get_port())
    if cmds.commandPort(port_str, q=True):
        cmds.warning("DAMaya MCP: Command port {0} is already open.".format(port_str))
    else:
        try:
            cmds.commandPort(n=port_str, sourceType="python", echoOutput=False)
            print("DAMaya MCP: Opened commandPort {0} (sourceType=python)".format(port_str))
        except Exception as e:
            cmds.error(f"DAMaya MCP: Failed to open port: {e}")


def _close_port():
    port_str = ":{0}".format(config.get_port())
    if cmds.commandPort(port_str, q=True):
        try:
            cmds.commandPort(n=port_str, cl=True)
            print("DAMaya MCP: Closed commandPort {0}".format(port_str))
        except Exception as e:
            cmds.error(f"DAMaya MCP: Failed to close port: {e}")
    else:
        cmds.warning("DAMaya MCP: Command port {0} is not open.".format(port_str))


def _run_selection_context():
    import maya.cmds as cmds
    sel = cmds.ls(sl=True)
    print(f"\n--- DAMaya Selection Context ---")
    print(f"Total Selected: {len(sel)}")
    print(f"Selection: {sel}")
    if sel:
        print(f"Primary Node Type: {cmds.objectType(sel[0])}")


def _show_help():
    import webbrowser
    webbrowser.open("https://github.com/NightXDreamin/DAMaya_MCP")
