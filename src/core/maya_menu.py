import maya.cmds as cmds
import maya.mel as mel

MENU_NAME = "DAMayaMCPMenu"

def create_menu():
    """
    Creates the DAMaya MCP top-level menu in Maya's main window.
    """
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
    cmds.menuItem(label="Open CommandPort :7022 (开启端口)", command=lambda *args: _open_port())
    cmds.menuItem(label="Close CommandPort :7022 (关闭端口)", command=lambda *args: _close_port())
    
    cmds.setParent(main_menu, menu=True)
    cmds.menuItem(divider=True)

    # 3. Quick TA Diagnostic Actions
    tools_menu = cmds.menuItem(label="Quick TA Diagnostics (快捷诊断)", subMenu=True, tearOff=True)
    
    cmds.menuItem(label="Get Selection Context (获取选择上下文)", command=lambda *args: _run_selection_context())
    cmds.menuItem(label="Validate Selected for UE (UE导出校验)", command=lambda *args: _run_ue_validation())
    cmds.menuItem(label="Scan NaN Weights (坏权重扫描)", command=lambda *args: _run_nan_scan())
    cmds.menuItem(label="Audit Texture Resolutions (贴图尺寸审计)", command=lambda *args: _run_texture_audit())
    cmds.menuItem(label="Auto-Rename for UE (命名规范化)", command=lambda *args: _run_auto_rename())
    
    cmds.setParent(main_menu, menu=True)
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
    port_str = ":7022"
    if cmds.commandPort(port_str, q=True):
        cmds.warning("DAMaya MCP: Command port :7022 is already open.")
    else:
        try:
            cmds.commandPort(n=port_str, sourceType="python", echoOutput=False)
            print("DAMaya MCP: Opened commandPort :7022 (sourceType=python)")
        except Exception as e:
            cmds.error(f"DAMaya MCP: Failed to open port: {e}")


def _close_port():
    port_str = ":7022"
    if cmds.commandPort(port_str, q=True):
        try:
            cmds.commandPort(n=port_str, cl=True)
            print("DAMaya MCP: Closed commandPort :7022")
        except Exception as e:
            cmds.error(f"DAMaya MCP: Failed to close port: {e}")
    else:
        cmds.warning("DAMaya MCP: Command port :7022 is not open.")


def _run_selection_context():
    import maya.cmds as cmds
    sel = cmds.ls(sl=True)
    print(f"\n--- DAMaya Selection Context ---")
    print(f"Total Selected: {len(sel)}")
    print(f"Selection: {sel}")
    if sel:
        print(f"Primary Node Type: {cmds.objectType(sel[0])}")


def _run_ue_validation():
    import maya.cmds as cmds
    sel = cmds.ls(sl=True)
    if not sel:
        cmds.confirmDialog(title="DAMaya MCP", message="Please select at least one node to validate.", button=["OK"])
        return
        
    print(f"\n--- DAMaya UE Pipeline Audit ---")
    for n in sel:
        # Check Freeze Transform
        t = cmds.getAttr(n + '.translate')[0]
        r = cmds.getAttr(n + '.rotate')[0]
        s = cmds.getAttr(n + '.scale')[0]
        frozen = all(abs(v) < 0.001 for v in t) and all(abs(v) < 0.001 for v in r) and all(abs(v - 1.0) < 0.001 for v in s)
        
        # Check Pivot
        pivot = cmds.xform(n, q=True, ws=True, rp=True)
        pivot_origin = all(abs(v) < 0.001 for v in pivot)
        
        # Check History
        history = cmds.listHistory(n, pruneDagObjects=True) or []
        clean_history = len(history) <= 1
        
        status = "PASSED" if (frozen and pivot_origin and clean_history) else "FAILED"
        print(f"Node: {n} -> [{status}]")
        print(f"  - Freeze Transforms: {'OK' if frozen else 'FROZEN CHECK FAILED'} (t={t}, r={r}, s={s})")
        print(f"  - Pivot at Origin: {'OK' if pivot_origin else 'PIVOT NOT AT ORIGIN'} ({pivot})")
        print(f"  - History Count: {'OK (Clean)' if clean_history else f'UNBAKED HISTORY ({len(history)} items)'}")


def _run_nan_scan():
    import maya.cmds as cmds
    import math
    sel = cmds.ls(sl=True, type='transform') or cmds.ls(sl=True, type='mesh')
    if not sel:
        cmds.confirmDialog(title="DAMaya MCP", message="Please select a Mesh to scan.", button=["OK"])
        return
        
    meshes = []
    for s in sel:
        if cmds.objectType(s) == 'mesh':
            meshes.append(s)
        else:
            shapes = cmds.listRelatives(s, shapes=True, type='mesh', fullPath=True) or []
            meshes.extend(shapes)
            
    meshes = list(set(meshes))
    if not meshes:
        cmds.confirmDialog(title="DAMaya MCP", message="No meshes found in selection.", button=["OK"])
        return
        
    print(f"\n--- DAMaya Skin Weights NaN/Inf Scan ---")
    total_corrupted = 0
    for m in meshes:
        skin_clusters = cmds.ls(cmds.listHistory(m), type='skinCluster')
        if not skin_clusters:
            print(f"Mesh: {m} -> [SKIPPED] No SkinCluster found.")
            continue
        sc = skin_clusters[0]
        vtx_count = cmds.polyEvaluate(m, vertex=True)
        influences = cmds.skinCluster(sc, q=True, influence=True) or []
        
        corrupted_vtx = []
        step = max(1, vtx_count // 1000)
        for i in range(0, vtx_count, step):
            vtx = f"{m}.vtx[{i}]"
            for inf in influences:
                try:
                    w = cmds.skinPercent(sc, vtx, transform=inf, q=True)
                    if math.isnan(w) or math.isinf(w):
                        corrupted_vtx.append((i, inf, w))
                        break
                except Exception:
                    pass
        if corrupted_vtx:
            print(f"Mesh: {m} (sc={sc}) -> [ALERT] Found {len(corrupted_vtx)} corrupted weights (sampled)!")
            for idx, inf, w in corrupted_vtx[:5]:
                print(f"  - Vertex index {idx} on Joint {inf}: weight={w}")
            total_corrupted += len(corrupted_vtx)
        else:
            print(f"Mesh: {m} -> [PASSED] Skin weights are clean.")
            
    if total_corrupted > 0:
        cmds.confirmDialog(title="NaN Weights Check", message=f"Scan complete. Found {total_corrupted} weight errors! Please check script editor for details.", button=["OK"])
    else:
        cmds.confirmDialog(title="NaN Weights Check", message="Scan complete. All weights are clean!", button=["OK"])


def _run_texture_audit():
    import maya.cmds as cmds
    file_nodes = cmds.ls(type="file")
    if not file_nodes:
        cmds.confirmDialog(title="DAMaya MCP", message="No file textures found in scene.", button=["OK"])
        return
        
    def po2(n):
        try:
            n_int = int(n)
            return (n_int & (n_int - 1) == 0) and n_int > 0
        except Exception:
            return False

    issues = []
    for fn in file_nodes:
        w = cmds.getAttr(fn + ".outSizeX")
        h = cmds.getAttr(fn + ".outSizeY")
        path = cmds.getAttr(fn + ".fileTextureName")
        if w is None or h is None or not (po2(w) and po2(h)):
            issues.append((fn, f"{w}x{h}", path))
            
    print(f"\n--- DAMaya File Texture Power-of-Two Audit ---")
    print(f"Total Textures Checked: {len(file_nodes)}")
    if issues:
        print(f"[FAILED] Found {len(issues)} texture(s) with non-power-of-two resolutions:")
        for node, res, path in issues:
            print(f"  - Node: {node} ({res}) | Path: {path}")
        cmds.confirmDialog(title="Texture Audit", message=f"Audit complete. Found {len(issues)} non-power-of-two texture(s).", button=["OK"])
    else:
        print(f"[PASSED] All texture resolutions are power-of-two.")
        cmds.confirmDialog(title="Texture Audit", message="Audit complete. All textures conform to power-of-two standards!", button=["OK"])


def _run_auto_rename():
    import maya.cmds as cmds
    sel = cmds.ls(sl=True, long=True)
    if not sel:
        cmds.confirmDialog(title="DAMaya MCP", message="Please select at least one node to rename.", button=["OK"])
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
                cmds.rename(n, new_name)
                renamed += 1
            except Exception:
                pass
    cmds.confirmDialog(title="Auto-Rename", message=f"Naming alignment complete. Renamed {renamed} node(s).", button=["OK"])


def _show_help():
    import webbrowser
    webbrowser.open("https://github.com/NightXDreamin/DAMaya_MCP")
