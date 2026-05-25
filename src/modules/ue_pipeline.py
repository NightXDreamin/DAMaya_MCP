def register_ue_tools(mcp, conn):
    @mcp.tool()
    def validate_for_ue(node_list: list):
        """
        在导出至 Unreal Engine 之前执行一系列自动化检查。

        包含检查项：
        1. Freeze Transforms（平移/旋转/缩放是否在期望值）
        2. Pivot 是否位于原点
        3. 是否存在未烘焙的历史记录

        返回针对每个节点的结构化报告（每项检查的通过状态与相关数据），便于流水线自动化或人工复核。
        """
        code = f"""
        import maya.cmds as cmds
        nodes = {node_list}
        report = []
        for n in nodes:
            checks = {{}}
            
            # 1. Freeze Transforms: translate/rotate 应为 0, scale 应为 1
            t = cmds.getAttr(n + '.translate')[0]
            r = cmds.getAttr(n + '.rotate')[0]
            s = cmds.getAttr(n + '.scale')[0]
            has_non_frozen_t = any(abs(v) > 0.001 for v in t)
            has_non_frozen_r = any(abs(v) > 0.001 for v in r)
            has_non_frozen_s = any(abs(v - 1.0) > 0.001 for v in s)
            checks['freeze_transforms'] = {{
                'passed': not (has_non_frozen_t or has_non_frozen_r or has_non_frozen_s),
                'translate': [round(v, 4) for v in t],
                'rotate': [round(v, 4) for v in r],
                'scale': [round(v, 4) for v in s]
            }}
            
            # 2. Pivot at origin
            pivot = cmds.xform(n, q=True, ws=True, rp=True)
            checks['pivot_at_origin'] = {{
                'passed': all(abs(v) < 0.001 for v in pivot),
                'pivot': [round(v, 4) for v in pivot]
            }}
            
            # 3. History check
            history = cmds.listHistory(n, pruneDagObjects=True) or []
            checks['clean_history'] = {{
                'passed': len(history) <= 1,
                'history_count': len(history)
            }}
            
            all_passed = all(c['passed'] for c in checks.values())
            report.append({{
                'node': n,
                'all_passed': all_passed,
                'checks': checks
            }})
        
        _mcp_results = report
        """
        return conn.execute(code)

    @mcp.tool()
    def quick_export_fbx(export_path: str, selection_only: bool = True):
        """
        使用 Maya 的 FBX 导出流程将场景或选定对象导出为 FBX 文件。

        实现细节：在需要时自动加载 `fbxmaya` 插件，并使用 `cmds.file(..., es=...)` 执行导出。
        返回导出路径字符串以便后续上传或归档。
        """
        code = f"""
        import maya.cmds as cmds
        # 确保 FBX 插件已加载
        if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
            cmds.loadPlugin('fbxmaya')
            
        path_str = r'{export_path}'
        cmds.file(path_str, force=True, options='v=0;', type='FBX export', pr=True, es={selection_only})
        _mcp_results = f"Exported to {{path_str}}"
        """
        return conn.execute(code)

    @mcp.tool()
    def validate_texture_resolutions():
        """
        扫描当前场景中所有文件贴图（file texture），并审计其长宽分辨率是否为2的幂次方（Power of Two）。
        
        这是 Unreal 导出的关键校验，非2的幂次方贴图在 UE 中无法进行 Mipmap 生成或纹理流送（Texture Streaming）。
        """
        code = """
        import maya.cmds as cmds
        import os
        
        file_nodes = cmds.ls(type="file") or []
        issues = []
        
        def is_power_of_two(n):
            return (n & (n - 1) == 0) and n > 0
            
        for fn in file_nodes:
            path = cmds.getAttr(fn + ".fileTextureName")
            
            try:
                w_val = cmds.getAttr(fn + ".outSizeX")
                h_val = cmds.getAttr(fn + ".outSizeY")
                w = int(w_val) if w_val is not None else 0
                h = int(h_val) if h_val is not None else 0
            except Exception:
                w, h = 0, 0
            
            is_w_po2 = is_power_of_two(w)
            is_h_po2 = is_power_of_two(h)
            
            if w == 0 or h == 0 or not (is_w_po2 and is_h_po2):
                issues.append({
                    "node": fn,
                    "path": path or "empty/virtual",
                    "resolution": f"{w}x{h}",
                    "error": "Non-power-of-two resolution or invalid/missing dimensions"
                })
                
        _mcp_results = {
            "total_scanned": len(file_nodes),
            "passed": len(file_nodes) - len(issues),
            "failed_textures": issues
        }
        """
        return conn.execute(code)

    @mcp.tool()
    def auto_rename_for_ue(node_list: list = None):
        """
        根据 Unreal Engine 行业标准规范命名，自动给所选或指定的节点重命名并加上标准前缀。
        
        规范如下：
        - Mesh: 前缀 `SM_` (e.g. SM_Sword)
        - Joint: 前缀 `joint_` (e.g. joint_Pelvis)
        - Material (shadingEngine): 前缀 `M_` (e.g. M_Iron)
        - Texture (file): 前缀 `T_` (e.g. T_Wood_D)
        
        参数说明：
        - `node_list`: 指定重命名节点列表。若未指定，自动使用当前 Maya 选中项。
        """
        nodes_repr = f"{node_list}" if node_list is not None else "cmds.ls(sl=True, long=True)"
        code = f"""
        import maya.cmds as cmds
        
        nodes = {nodes_repr} or []
        renamed_map = {{}}
        
        for n in nodes:
            if not cmds.objExists(n):
                continue
            
            base_name = n.split('|')[-1]
            obj_type = cmds.objectType(n)
            
            prefix = ""
            clean_name = base_name
            
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
                
            if not prefix:
                continue
                
            if clean_name.startswith(prefix):
                continue
                
            for p in ["SM_", "M_", "T_", "Grp_", "joint_"]:
                if clean_name.startswith(p):
                    clean_name = clean_name[len(p):]
                    break
                    
            new_name = prefix + clean_name
            try:
                actual_new_name = cmds.rename(n, new_name)
                renamed_map[n] = actual_new_name
            except Exception as e:
                renamed_map[n] = f"error: {{e}}"
                
        _mcp_results = renamed_map
        """
        return conn.execute(code)