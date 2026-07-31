import os
import time

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        # Fallback if PySide is not found (should not happen inside modern Maya)
        raise ImportError("PySide2 or PySide6 is required to run the DAMaya MCP UI.")

import maya.cmds as cmds
import maya.OpenMayaUI as omui

from src.core import server_manager
from src.core import config
from src import __version__

PORT_STR = ":{0}".format(config.get_port())

WINDOW_TITLE = "DAMaya MCP"
WINDOW_OBJECT_NAME = "DAMayaMCPWindow"


def get_maya_main_window():
    """
    Get Maya's main window widget to use as parent.
    This keeps the UI docked or grouped inside Maya properly.
    """
    try:
        try:
            import shiboken6 as shiboken
        except ImportError:
            import shiboken

        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return shiboken.wrapInstance(int(ptr), QtWidgets.QMainWindow)
    except Exception:
        pass
    return None


class DAMayaMCPPanel(QtWidgets.QMainWindow):
    """
    Main PySide Control Panel for DAMaya MCP.
    """
    def __init__(self, parent=None):
        # Parent to Maya window if possible
        parent_win = parent or get_maya_main_window()
        super(DAMayaMCPPanel, self).__init__(parent_win)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(560, 440)

        # Minimal dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #262626;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #9a9a9a;
                border: 1px solid #3a3a3a;
                border-bottom: none;
                padding: 6px 18px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #262626;
                color: #ffffff;
            }
            QLabel {
                color: #d4d4d4;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QCheckBox {
                color: #d4d4d4;
                spacing: 6px;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #b5b5b5;
                border: 1px solid #3a3a3a;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)

        # Main Widget & Setup
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # --- HEADER ---
        header_layout = QtWidgets.QHBoxLayout()
        header_title = QtWidgets.QLabel("DAMaya MCP")
        header_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_ver = QtWidgets.QLabel("v{0}".format(__version__))
        header_ver.setStyleSheet("color: #808080; font-size: 11px;")
        header_layout.addWidget(header_title)
        header_layout.addWidget(header_ver)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)
        main_layout.addSpacing(8)

        # --- TAB WIDGET ---
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_dashboard_tab()
        self._build_logs_tab()

        # Timer to poll status of server and commandPort
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.setInterval(2000)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start()

        self.log("Control panel initialized (v{0}).".format(__version__))
        self.update_status()

    # ==================== TAB BUILDERS ====================

    def _build_dashboard_tab(self):
        """
        Creates the status & settings tab.
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- Status rows ---
        grid = QtWidgets.QGridLayout()
        grid.setVerticalSpacing(10)

        # CommandPort row
        grid.addWidget(QtWidgets.QLabel("CommandPort " + PORT_STR), 0, 0)
        self.port_indicator = QtWidgets.QLabel("● CLOSED")
        self.port_indicator.setStyleSheet("color: #e05252; font-weight: bold;")
        grid.addWidget(self.port_indicator, 0, 1)
        self.port_btn = QtWidgets.QPushButton("Open Port")
        self.port_btn.clicked.connect(self.toggle_commandport)
        self.port_btn.setFixedWidth(90)
        grid.addWidget(self.port_btn, 0, 2)

        # MCP Server row
        grid.addWidget(QtWidgets.QLabel("MCP Server"), 1, 0)
        self.server_indicator = QtWidgets.QLabel("● INACTIVE")
        self.server_indicator.setStyleSheet("color: #e05252; font-weight: bold;")
        grid.addWidget(self.server_indicator, 1, 1)
        self.server_btn = QtWidgets.QPushButton("Start Server")
        self.server_btn.clicked.connect(self.toggle_server)
        self.server_btn.setFixedWidth(90)
        grid.addWidget(self.server_btn, 1, 2)

        layout.addLayout(grid)

        # --- Divider ---
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setStyleSheet("color: #3a3a3a;")
        layout.addWidget(divider)
        layout.addSpacing(4)

        # --- Auto-start ---
        self.autostart_cb = QtWidgets.QCheckBox("Start MCP server automatically when Maya opens")
        self.autostart_cb.setChecked(server_manager.should_autostart())
        self.autostart_cb.stateChanged.connect(self.on_autostart_changed)
        layout.addWidget(self.autostart_cb)

        # --- Project path (read-only hint) ---
        path_lbl = QtWidgets.QLabel(server_manager.PROJECT_ROOT)
        path_lbl.setStyleSheet("color: #707070; font-size: 10px;")
        path_lbl.setWordWrap(True)
        layout.addWidget(path_lbl)

        layout.addStretch()
        self.tabs.addTab(tab, "Dashboard")

    def _build_logs_tab(self):
        """
        Creates the log console tab.
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        self.console = QtWidgets.QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        btn_layout = QtWidgets.QHBoxLayout()
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self.console.clear)
        save_btn = QtWidgets.QPushButton("Export")
        save_btn.clicked.connect(self.export_logs)

        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Logs")

    # ==================== STATE MANAGEMENT ====================

    def log(self, text):
        """
        Append timestamps and print to log tab.
        """
        t = time.strftime("[%H:%M:%S]")
        self.console.append(f"{t} {text}")
        print(f"DAMaya MCP: {text}")

    def update_status(self):
        """
        Periodically checks commandPort and server process.
        """
        # 1. CommandPort Check
        is_port_open = cmds.commandPort(PORT_STR, q=True)
        if is_port_open:
            self.port_indicator.setText("● LISTENING")
            self.port_indicator.setStyleSheet("color: #57a957; font-weight: bold;")
            self.port_btn.setText("Close")
        else:
            self.port_indicator.setText("● CLOSED")
            self.port_indicator.setStyleSheet("color: #e05252; font-weight: bold;")
            self.port_btn.setText("Open")

        # 2. Server Process Check
        is_running = server_manager.is_server_running()
        if is_running:
            pid = server_manager.get_running_server_pid()
            self.server_indicator.setText(f"● ACTIVE (PID {pid})")
            self.server_indicator.setStyleSheet("color: #57a957; font-weight: bold;")
            self.server_btn.setText("Stop")
        else:
            self.server_indicator.setText("● INACTIVE")
            self.server_indicator.setStyleSheet("color: #e05252; font-weight: bold;")
            self.server_btn.setText("Start")

    def toggle_commandport(self):
        """
        Open/Close commandPort port.
        """
        is_open = cmds.commandPort(PORT_STR, q=True)
        if is_open:
            try:
                cmds.commandPort(n=PORT_STR, cl=True)
                self.log("CommandPort " + PORT_STR + " closed.")
            except Exception as e:
                self.log(f"Error closing CommandPort: {e}")
        else:
            try:
                cmds.commandPort(n=PORT_STR, sourceType="python", echoOutput=False)
                self.log("CommandPort " + PORT_STR + " opened successfully.")
            except Exception as e:
                self.log(f"Error opening CommandPort: {e}")
        self.update_status()

    def toggle_server(self):
        """
        Start/Stop background server process.
        """
        is_running = server_manager.is_server_running()
        if is_running:
            success, msg = server_manager.stop_server()
            self.log(msg)
        else:
            success, msg = server_manager.start_server()
            self.log(msg)
        self.update_status()

    def on_autostart_changed(self, state):
        """
        Set auto-start configurations.
        """
        enabled = state == QtCore.Qt.Checked
        server_manager.set_autostart(enabled)
        self.log(f"Auto-start set to: {enabled}")

    def export_logs(self):
        """
        Save console log to disk.
        """
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        log_file = os.path.join(desktop, f"damaya_mcp_log_{int(time.time())}.txt")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(self.console.toPlainText())
            self.log(f"Logs exported to: {log_file}")
            QtWidgets.QMessageBox.information(self, "Export Successful", f"Logs exported to:\n{log_file}")
        except Exception as e:
            self.log(f"Failed to export logs: {e}")


# --- GLOBAL SINGLETON WINDOW INSTANCE CONTROL ---
_instance = None

def show_window():
    """
    Exposes a safe, single-instance runner to show the control panel in Maya.
    """
    global _instance
    # If window is already open, raise it to top focus
    if _instance is not None:
        try:
            _instance.show()
            _instance.raise_()
            _instance.activateWindow()
            return _instance
        except RuntimeError:
            # Window was deleted behind our back, clean up and recreate
            _instance = None

    # Instantiate new window
    _instance = DAMayaMCPPanel()
    _instance.show()
    return _instance
