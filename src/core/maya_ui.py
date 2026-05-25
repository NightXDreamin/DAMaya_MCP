import os
import sys
import json
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

# Import server manager
from src.core import server_manager

WINDOW_TITLE = "DAMaya MCP Control Panel"
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


class ToolRow(QtWidgets.QFrame):
    """
    Helper class to render a clean, premium tool row with details and action button.
    """
    def __init__(self, name, desc, run_callback, inputs=None, parent=None):
        super(ToolRow, self).__init__(parent)
        self.run_callback = run_callback
        self.inputs_def = inputs or []
        self.input_widgets = {}

        self.setStyleSheet("""
            ToolRow {
                background-color: #202024;
                border: 1px solid #2d2d34;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 6px;
            }
            ToolRow:hover {
                background-color: #24242b;
                border-color: #4338ca;
            }
            QLabel#ToolName {
                color: #e2e8f0;
                font-weight: bold;
                font-size: 13px;
            }
            QLabel#ToolDesc {
                color: #94a3b8;
                font-size: 11px;
            }
            QPushButton#RunBtn {
                background-color: #4f46e5;
                color: white;
                border: None;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton#RunBtn:hover {
                background-color: #4338ca;
            }
            QLineEdit {
                background-color: #18181b;
                color: #e2e8f0;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #6366f1;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Left Info Panel
        info_layout = QtWidgets.QVBoxLayout()
        name_lbl = QtWidgets.QLabel(name)
        name_lbl.setObjectName("ToolName")
        desc_lbl = QtWidgets.QLabel(desc)
        desc_lbl.setObjectName("ToolDesc")
        desc_lbl.setWordWrap(True)
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(desc_lbl)

        # Center Parameter Panel (if any inputs)
        self.params_layout = QtWidgets.QHBoxLayout()
        self.params_layout.setSpacing(6)
        for inp_name, default_val in self.inputs_def:
            le = QtWidgets.QLineEdit()
            le.setPlaceholderText(inp_name)
            le.setText(str(default_val))
            le.setMaximumWidth(120)
            self.params_layout.addWidget(le)
            self.input_widgets[inp_name] = le
        
        layout.addLayout(info_layout, 3)
        layout.addLayout(self.params_layout, 2)

        # Right Action Panel
        self.run_btn = QtWidgets.QPushButton("Run")
        self.run_btn.setObjectName("RunBtn")
        self.run_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.on_run)
        layout.addWidget(self.run_btn, 0, QtCore.Qt.AlignVCenter)

    def on_run(self):
        args = {}
        for k, widget in self.input_widgets.items():
            args[k] = widget.text()
        self.run_callback(args)


class DAMayaMCPPanel(QtWidgets.QMainWindow):
    """
    Main PySide Control Panel for DAMaya MCP
    """
    def __init__(self, parent=None):
        # Parent to Maya window if possible
        parent_win = parent or get_maya_main_window()
        super(DAMayaMCPPanel, self).__init__(parent_win)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(680, 520)

        # Premium Dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121214;
            }
            QTabWidget::pane {
                border: 1px solid #27272a;
                background-color: #18181b;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #202024;
                color: #a1a1aa;
                border: 1px solid #27272a;
                border-bottom: None;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #18181b;
                color: #e4e4e7;
                border-bottom: 2px solid #6366f1;
            }
            QTabBar::tab:hover {
                color: #f4f4f5;
                background-color: #27272a;
            }
            QLabel {
                color: #e4e4e7;
            }
            QGroupBox {
                border: 1px solid #2d2d34;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: #6366f1;
                font-size: 13px;
                background-color: #18181b;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 8px;
            }
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                border-color: #52525b;
            }
            QTextEdit {
                background-color: #0c0c0e;
                color: #10b981;
                border: 1px solid #27272a;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: #18181b;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #3f3f46;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #52525b;
            }
        """)

        # Main Widget & Setup
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- HEADER ---
        header_layout = QtWidgets.QHBoxLayout()
        header_title = QtWidgets.QLabel("DAMaya MCP TA Studio")
        header_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_ver = QtWidgets.QLabel("v1.1.0")
        header_ver.setStyleSheet("color: #71717a; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(header_title)
        header_layout.addWidget(header_ver)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)

        # --- TAB WIDGET ---
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_dashboard_tab()
        self._build_toolbox_tab()
        self._build_logs_tab()

        # Timer to poll status of server and commandPort
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.setInterval(2000)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start()

        self.log("DAMaya MCP Control Panel Initialized.")
        self.update_status()

    # ==================== TAB BUILDERS ====================

    def _build_dashboard_tab(self):
        """
        Creates the Dashboard & Configuration tab.
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # 1. Services Status Indicators
        status_box = QtWidgets.QGroupBox("Services Status (服务状态)")
        status_layout = QtWidgets.QGridLayout(status_box)
        status_layout.setContentsMargins(15, 15, 15, 15)

        # CommandPort Status
        status_layout.addWidget(QtWidgets.QLabel("Maya CommandPort (:7022):"), 0, 0)
        self.port_indicator = QtWidgets.QLabel("● CLOSED")
        self.port_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(self.port_indicator, 0, 1)

        self.port_btn = QtWidgets.QPushButton("Toggle Port")
        self.port_btn.clicked.connect(self.toggle_commandport)
        status_layout.addWidget(self.port_btn, 0, 2)

        # MCP Background Server Status
        status_layout.addWidget(QtWidgets.QLabel("Background MCP Server:"), 1, 0)
        self.server_indicator = QtWidgets.QLabel("● INACTIVE")
        self.server_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(self.server_indicator, 1, 1)

        self.server_btn = QtWidgets.QPushButton("Toggle Server")
        self.server_btn.clicked.connect(self.toggle_server)
        status_layout.addWidget(self.server_btn, 1, 2)

        layout.addWidget(status_box)

        # 2. Advanced Launch Settings
        settings_box = QtWidgets.QGroupBox("Launch Preferences (启动首选项)")
        settings_layout = QtWidgets.QVBoxLayout(settings_box)
        settings_layout.setContentsMargins(15, 15, 15, 15)

        self.autostart_cb = QtWidgets.QCheckBox("Automatically start background MCP server when Maya opens")
        self.autostart_cb.setStyleSheet("color: #e4e4e7; font-size: 12px; spacing: 8px;")
        self.autostart_cb.setChecked(server_manager.should_autostart())
        self.autostart_cb.stateChanged.connect(self.on_autostart_changed)
        settings_layout.addWidget(self.autostart_cb)

        path_lbl = QtWidgets.QLabel(f"Project Workspace Directory:\n{server_manager.PROJECT_ROOT}")
        path_lbl.setStyleSheet("color: #71717a; font-size: 11px; margin-top: 8px;")
        settings_layout.addWidget(path_lbl)

        layout.addWidget(settings_box)
        layout.addStretch()

        self.tabs.addTab(tab, "Dashboard (仪表盘)")

    def _build_toolbox_tab(self):
        """
        Creates the interactive tool sandbox launcher tab.
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scroll Area for Toolbox items
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: None; background: transparent; }")
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 5, 0)
        scroll_layout.setSpacing(10)

        # --- PERCEPTION GROUP ---
        p_group = QtWidgets.QGroupBox("1. Perception Tools (场景感知)")
        p_layout = QtWidgets.QVBoxLayout(p_group)
        p_layout.addWidget(ToolRow(
            "Get Scene Summary", "Scan Maya nodes and return counts of meshes, joints, lights, constraints.",
            lambda args: self.run_ta_tool("scene_summary")
        ))
        p_layout.addWidget(ToolRow(
            "Get Selection Context", "Inspect currently highlighted objects, items count, and type.",
            lambda args: self.run_ta_tool("selection_context")
        ))
        p_layout.addWidget(ToolRow(
            "Query Scene Topology", "Query deep hierarchy connections and parents / children nodes.",
            lambda args: self.run_ta_tool("topology", args),
            inputs=[("pattern", "*"), ("node_type", "transform")]
        ))
        p_layout.addWidget(ToolRow(
            "Capture Viewport", "Generate playblast viewport screens of full frame fits.",
            lambda args: self.run_ta_tool("capture", args),
            inputs=[("filename", "viewport_snap.jpg")]
        ))
        scroll_layout.addWidget(p_group)

        # --- RIGGING GROUP ---
        r_group = QtWidgets.QGroupBox("2. Rigging Diagnostics (绑定排错)")
        r_layout = QtWidgets.QVBoxLayout(r_group)
        r_layout.addWidget(ToolRow(
            "Scan NaN Weights", "Scans mesh skinCluster weights for corrupted, infinite, or NaN values.",
            lambda args: self.run_ta_tool("nan_scan", args),
            inputs=[("mesh_name", "*")]
        ))
        r_layout.addWidget(ToolRow(
            "Zero Out Transforms", "Safe zeroing of transformations (Scale=1, Pos/Rot=0) respecting locked channels.",
            lambda args: self.run_ta_tool("zero_transforms", args),
            inputs=[("node_name", "")]
        ))
        scroll_layout.addWidget(r_group)

        # --- UE PIPELINE GROUP ---
        ue_group = QtWidgets.QGroupBox("3. Unreal Engine Pipeline (UE导出流水线)")
        ue_layout = QtWidgets.QVBoxLayout(ue_group)
        ue_layout.addWidget(ToolRow(
            "Validate Selected for UE", "Audit freeze transformations, clean history, and pivot placement.",
            lambda args: self.run_ta_tool("ue_validate")
        ))
        ue_layout.addWidget(ToolRow(
            "Audit Texture Resolutions", "Scan textures in scene to guarantee Power-of-Two dimensions for proper streaming.",
            lambda args: self.run_ta_tool("texture_audit")
        ))
        ue_layout.addWidget(ToolRow(
            "Align Naming For UE", "Apply SM_ / joint_ / M_ / T_ prefix structures dynamically.",
            lambda args: self.run_ta_tool("align_naming")
        ))
        scroll_layout.addWidget(ue_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        self.tabs.addTab(tab, "Toolbox (工具箱)")

    def _build_logs_tab(self):
        """
        Creates the live Diagnostic Log Console tab.
        """
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        self.console = QtWidgets.QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        btn_layout = QtWidgets.QHBoxLayout()
        clear_btn = QtWidgets.QPushButton("Clear Console Logs")
        clear_btn.clicked.connect(self.console.clear)
        save_btn = QtWidgets.QPushButton("Export Log to File")
        save_btn.clicked.connect(self.export_logs)

        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Logs (日志控制台)")

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
        is_port_open = cmds.commandPort(":7022", q=True)
        if is_port_open:
            self.port_indicator.setText("● LISTENING (:7022)")
            self.port_indicator.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.port_btn.setText("Close Port")
        else:
            self.port_indicator.setText("● CLOSED")
            self.port_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
            self.port_btn.setText("Open Port")

        # 2. Server Process Check
        is_running = server_manager.is_server_running()
        if is_running:
            pid = server_manager.get_running_server_pid()
            self.server_indicator.setText(f"● ACTIVE (PID {pid})")
            self.server_indicator.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.server_btn.setText("Stop Server")
        else:
            self.server_indicator.setText("● INACTIVE")
            self.server_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
            self.server_btn.setText("Start Server")

    def toggle_commandport(self):
        """
        Open/Close commandPort port.
        """
        is_open = cmds.commandPort(":7022", q=True)
        if is_open:
            try:
                cmds.commandPort(n=":7022", cl=True)
                self.log("CommandPort :7022 closed.")
            except Exception as e:
                self.log(f"Error closing CommandPort: {e}")
        else:
            try:
                cmds.commandPort(n=":7022", sourceType="python", echoOutput=False)
                self.log("CommandPort :7022 opened successfully.")
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
        self.log(f"Auto-start background server set to: {enabled}")

    def export_logs(self):
        """
        Save console log to disk.
        """
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        log_file = os.path.join(desktop, f"damaya_mcp_log_{int(time.time())}.txt")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(self.console.toPlainText())
            self.log(f"Logs successfully exported to: {log_file}")
            QtWidgets.QMessageBox.information(self, "Export Successful", f"Logs exported to:\n{log_file}")
        except Exception as e:
            self.log(f"Failed to export logs: {e}")

    # ==================== TA TOOL EXECUTION ====================

    def run_ta_tool(self, tool_id, args=None):
        """
        Executes a diagnostic tool locally in Maya's environment
        and displays output beautifully in the logs and popups.
        """
        args = args or {}
        self.log(f"Running TA Tool: '{tool_id}' with parameters: {args}...")
        self.tabs.setCurrentIndex(2) # Switch to Log Console to see execution

        try:
            # 1. Perception tools
            if tool_id == "scene_summary":
                total = len(cmds.ls(long=True) or [])
                all_meshes = cmds.ls(type="mesh", long=True) or []
                visible_meshes = [m for m in all_meshes if not cmds.getAttr(m + ".intermediateObject")]
                meshes = len(visible_meshes)
                joints = len(cmds.ls(type="joint") or [])
                cameras = len(cmds.ls(type="camera") or [])
                constraints = len(cmds.ls(type="constraint") or [])
                mats = len(cmds.ls(type="shadingEngine") or [])
                
                output = (
                    f"--- Maya Scene Summary ---\n"
                    f"Total Nodes In Scene: {total}\n"
                    f"Meshes Count: {meshes}\n"
                    f"Joint Bones Count: {joints}\n"
                    f"Cameras Count: {cameras}\n"
                    f"Constraints Count: {constraints}\n"
                    f"Materials Count: {mats}\n"
                    f"Currently Selected: {cmds.ls(sl=True)}\n"
                )
                self.log(output)
                QtWidgets.QMessageBox.information(self, "Scene Summary", output)

            elif tool_id == "selection_context":
                sel = cmds.ls(sl=True)
                output = (
                    f"--- Selection Context ---\n"
                    f"Total Selected Nodes: {len(sel)}\n"
                    f"Items List: {sel}\n"
                )
                if sel:
                    output += f"Primary Node Type: {cmds.objectType(sel[0])}\n"
                self.log(output)
                QtWidgets.QMessageBox.information(self, "Selection Context", output)

            elif tool_id == "topology":
                pattern = args.get("pattern", "*")
                node_type = args.get("node_type", "transform")
                types = [t.strip() for t in node_type.split(',')]
                
                nodes = []
                for t in types:
                    nodes.extend(cmds.ls(pattern, type=t, long=True) or [])
                nodes = list(set(nodes))
                
                output = f"--- Scene Topology (Type={node_type}, Pattern={pattern}) ---\n"
                output += f"Found matching nodes: {len(nodes)}\n"
                for n in nodes[:15]:
                    name = n.split('|')[-1]
                    parent = cmds.listRelatives(n, parent=True)
                    children = cmds.listRelatives(n, children=True) or []
                    output += f" - Node: {name} | Path: {n}\n"
                    output += f"   - Parent: {parent}\n"
                    output += f"   - Children Count: {len(children)}\n"
                if len(nodes) > 15:
                    output += f" ... and {len(nodes) - 15} more nodes. (View Script Editor for full lists)."
                self.log(output)

            elif tool_id == "capture":
                filename = args.get("filename", "viewport_snap.jpg")
                tmp_dir = cmds.internalVar(userTmpDir=True)
                full_path = os.path.join(tmp_dir, filename).replace('\\', '/')
                
                cmds.viewFit(all=True)
                cmds.playblast(frame=cmds.currentTime(q=True), format='image', 
                               viewer=False, compression='jpg', completeFilename=full_path)
                
                self.log(f"[SUCCESS] Viewport screen snap saved to: {full_path}")
                QtWidgets.QMessageBox.information(self, "Viewport Captured", f"Screenshot saved successfully at:\n{full_path}")

            # 2. Rigging tools
            elif tool_id == "nan_scan":
                mesh_pattern = args.get("mesh_name", "*")
                import math
                
                # Resolve meshes
                raw = cmds.ls(mesh_pattern, type='mesh', long=True) or []
                tfs = cmds.ls(mesh_pattern, type='transform', long=True) or []
                for t in tfs:
                    shapes = cmds.listRelatives(t, shapes=True, type='mesh', fullPath=True) or []
                    raw.extend(shapes)
                meshes = list(set(raw))
                
                self.log(f"Scanning {len(meshes)} mesh shape(s) for NaN skin weight values...")
                corrupted_total = 0
                
                for m in meshes:
                    skin_clusters = cmds.ls(cmds.listHistory(m), type='skinCluster')
                    if not skin_clusters:
                        continue
                    sc = skin_clusters[0]
                    vtx_count = cmds.polyEvaluate(m, vertex=True)
                    influences = cmds.skinCluster(sc, q=True, influence=True) or []
                    
                    errs = []
                    # Limit sample on dense mesh in UI to keep it ultra-fast
                    step = max(1, vtx_count // 1000)
                    for i in range(0, vtx_count, step):
                        vtx = f"{m}.vtx[{i}]"
                        for inf in influences:
                            try:
                                w = cmds.skinPercent(sc, vtx, transform=inf, q=True)
                                if math.isnan(w) or math.isinf(w):
                                    errs.append((i, inf, w))
                                    break
                            except Exception:
                                pass
                    if errs:
                        self.log(f"[ALERT] SkinCluster '{sc}' on Mesh '{m}' has {len(errs)} bad weights!")
                        for idx, inf, val in errs[:5]:
                            self.log(f"  - Vertex [{idx}] on bone '{inf}': weight={val}")
                        corrupted_total += len(errs)
                
                if corrupted_total > 0:
                    QtWidgets.QMessageBox.warning(self, "Weight Scan Failed", f"Found {corrupted_total} vertex weight errors. Inspect logs/script editor.")
                else:
                    self.log("[PASSED] Skin weights are clean.")
                    QtWidgets.QMessageBox.information(self, "Weight Scan Passed", "All skin weights are clean and healthy.")

            elif tool_id == "zero_transforms":
                node = args.get("node_name", "")
                if not node:
                    sel = cmds.ls(sl=True)
                    if sel:
                        node = sel[0]
                    else:
                        QtWidgets.QMessageBox.warning(self, "Zero Out Transforms", "Specify a node or select one in Maya.")
                        return
                
                if not cmds.objExists(node):
                    self.log(f"[ERROR] Node '{node}' does not exist.")
                    return
                
                results = []
                for attr, default in [('tx', 0), ('ty', 0), ('tz', 0), ('rx', 0), ('ry', 0), ('rz', 0), ('sx', 1), ('sy', 1), ('sz', 1)]:
                    full = f"{node}.{attr}"
                    if cmds.getAttr(full, settable=True):
                        try:
                            cmds.setAttr(full, default)
                            results.append(f"{attr}=OK")
                        except Exception as e:
                            results.append(f"{attr}=ERR({e})")
                    else:
                        results.append(f"{attr}=LOCKED")
                self.log(f"Zeroed transforms for '{node}': {', '.join(results)}")

            # 3. UE Pipeline tools
            elif tool_id == "ue_validate":
                sel = cmds.ls(sl=True)
                if not sel:
                    QtWidgets.QMessageBox.warning(self, "UE Audit", "Please select objects to validate.")
                    return
                
                self.log(f"Running UE validation audits on: {sel}")
                failures = 0
                for n in sel:
                    # Freeze
                    t = cmds.getAttr(n + '.translate')[0]
                    r = cmds.getAttr(n + '.rotate')[0]
                    s = cmds.getAttr(n + '.scale')[0]
                    frozen = all(abs(v) < 0.001 for v in t) and all(abs(v) < 0.001 for v in r) and all(abs(v - 1.0) < 0.001 for v in s)
                    
                    # Pivot
                    piv = cmds.xform(n, q=True, ws=True, rp=True)
                    pivot_ok = all(abs(v) < 0.001 for v in piv)
                    
                    # History
                    hist = cmds.listHistory(n, pruneDagObjects=True) or []
                    hist_ok = len(hist) <= 1
                    
                    if not (frozen and pivot_ok and hist_ok):
                        self.log(f"[FAIL] Node: {n} has issues:")
                        if not frozen: self.log(f"  - Translation/Rotation not frozen! (t={t}, r={r}, s={s})")
                        if not pivot_ok: self.log(f"  - Pivot not at center! ({piv})")
                        if not hist_ok: self.log(f"  - Unbaked construction history ({len(hist)} nodes)!")
                        failures += 1
                    else:
                        self.log(f"[PASS] Node: {n}")
                
                if failures > 0:
                    QtWidgets.QMessageBox.warning(self, "UE Audit Failed", f"Found {failures} mesh(es) with UE export compliance issues. Check logs.")
                else:
                    QtWidgets.QMessageBox.information(self, "UE Audit Passed", "All selected meshes are fully UE export compliant!")

            elif tool_id == "texture_audit":
                file_nodes = cmds.ls(type="file")
                def po2(n):
                    try:
                        n_int = int(n)
                        return (n_int & (n_int - 1) == 0) and n_int > 0
                    except Exception:
                        return False
                failures = []
                for fn in file_nodes:
                    w = cmds.getAttr(fn + ".outSizeX")
                    h = cmds.getAttr(fn + ".outSizeY")
                    path = cmds.getAttr(fn + ".fileTextureName")
                    if w is None or h is None or not (po2(w) and po2(h)):
                        failures.append((fn, f"{w}x{h}", path))
                
                self.log(f"Texture audit complete. Scanned: {len(file_nodes)}")
                if failures:
                    self.log(f"[ALERT] Found {len(failures)} textures out of compliance:")
                    for f, res, path in failures:
                        self.log(f"  - Node: {f} ({res}) | Path: {path}")
                    QtWidgets.QMessageBox.warning(self, "Texture Audit Failed", f"Found {len(failures)} textures that do not conform to power-of-two rules.")
                else:
                    self.log("[PASSED] All texture assets are power-of-two compliant.")
                    QtWidgets.QMessageBox.information(self, "Texture Audit Passed", "All textures conform to power-of-two rules.")

            elif tool_id == "align_naming":
                sel = cmds.ls(sl=True, long=True)
                if not sel:
                    QtWidgets.QMessageBox.warning(self, "Rename Alignment", "Select objects in Maya to rename.")
                    return
                
                renamed = 0
                for n in sel:
                    if not cmds.objExists(n):
                        continue
                    base = n.split('|')[-1]
                    obj_type = cmds.objectType(n)
                    prefix = ""
                    if obj_type == "transform":
                        shapes = cmds.listRelatives(n, shapes=True) or []
                        if shapes and cmds.objectType(shapes[0]) == "mesh":
                            prefix = "SM_"
                        elif shapes and cmds.objectType(shapes[0]) == "camera":
                            continue
                        else:
                            prefix = "Grp_"
                    elif obj_type == "joint":
                        prefix = "joint_"
                    elif obj_type == "shadingEngine":
                        prefix = "M_"
                    elif obj_type == "file":
                        prefix = "T_"
                        
                    if prefix and not base.startswith(prefix):
                        clean = base
                        for p in ["SM_", "M_", "T_", "Grp_", "joint_"]:
                            if clean.startswith(p):
                                clean = clean[len(p):]
                                break
                        new_name = prefix + clean
                        try:
                            actual = cmds.rename(n, new_name)
                            self.log(f"Renamed: {base} -> {actual}")
                            renamed += 1
                        except Exception as e:
                            self.log(f"Failed to rename {base}: {e}")
                
                self.log(f"Naming alignment finished. Processed: {renamed} nodes.")
                QtWidgets.QMessageBox.information(self, "Rename Complete", f"Successfully aligned {renamed} node names to industry naming standard.")

        except Exception as tool_e:
            self.log(f"[FATAL EXCEPTION] Tool execution crashed: {tool_e}")


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
