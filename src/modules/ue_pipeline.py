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
        import maya.mel as mel
        # 确保 FBX 插件已加载
        if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
            cmds.loadPlugin('fbxmaya')
            
        cmds.file('{export_path}', force=True, options='v=0;', type='FBX export', pr=True, es={selection_only})
        _mcp_results = f"Exported to {{export_path}}"
        """
        return conn.execute(code)