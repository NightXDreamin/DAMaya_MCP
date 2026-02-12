def register_ue_tools(mcp, conn):
    @mcp.tool()
    def validate_for_ue(node_list: list):
        """
        UE 资产导出前检查：
        1. 检查是否有冻结变换（Freeze Transformations）
        2. 检查轴心点（Pivot）是否在原点
        3. 检查是否有未烘焙的历史记录
        返回每个节点、每项检查的 pass/fail 结构化结果。
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
        调用 FBX 插件导出资产。
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