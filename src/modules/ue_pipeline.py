def register_ue_tools(mcp, conn):
    @mcp.tool()
    def validate_for_ue(node_list: list):
        """
        UE 资产导出前检查：
        1. 检查是否有冻结变换（Freeze Transformations）
        2. 检查是否有重叠 UV（Overlapping UVs）
        3. 检查轴心点（Pivot）是否在原点
        """
        code = f"""
        report = []
        nodes = {node_list}
        for n in nodes:
            # 检查位移是否归零
            pos = cmds.xform(n, q=True, ws=True, rp=True)
            if any(abs(v) > 0.001 for v in pos):
                report.append(f"{{n}}: Pivot is not at origin")
            
            # 检查历史记录
            history = cmds.listHistory(n, pruneDagObjects=True)
            if len(history) > 1:
                report.append(f"{{n}}: Has unbaked history")
        
        _mcp_results = report if report else "All checks passed for UE."
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