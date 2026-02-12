def register_rigging_tools(mcp, conn):
    @mcp.tool()
    def trace_rig_logic(node_name: str):
        """
        专门用于 Rigging 调试。
        查询一个节点的所有约束关系（Constraints）和 Message 属性连接。
        """
        code = f"""
        import maya.cmds as cmds
        _mcp_results = {{
            "constraints": cmds.listConnections('{node_name}', type='constraint') or [],
            "message_links": cmds.listConnections('{node_name}.message', destination=True, source=False, plugs=True) or [],
            "driven_keys": cmds.setDrivenKeyframe('{node_name}', query=True, cd=True) or []
        }}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_influence_joints(mesh_name: str):
        """
        获取选中 Mesh 的影响骨骼列表及其权重范围。
        """
        code = f"""
        skin_clusters = cmds.ls(cmds.listHistory('{mesh_name}'), type='skinCluster')
        if skin_clusters:
            _mcp_results = cmds.skinCluster(skin_clusters[0], q=True, influence=True)
        else:
            _mcp_results = "No skinCluster found on this mesh."
        """
        return conn.execute(code)