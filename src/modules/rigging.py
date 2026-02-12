def register_rigging_tools(mcp, conn):
    @mcp.tool()
    def trace_rig_logic(node_name: str):
        """
        专门用于 Rigging 调试。
        查询一个节点的所有约束关系（Constraints）和 Message 属性连接。
        返回去重后的约束列表、message 连接和 driven key 信息。
        """
        code = f"""
        import maya.cmds as cmds
        # 约束去重
        raw_constraints = cmds.listConnections('{node_name}', type='constraint') or []
        unique_constraints = list(dict.fromkeys(raw_constraints))
        
        # 为每个约束附加类型信息
        constraint_info = []
        for c in unique_constraints:
            constraint_info.append({{
                "name": c,
                "type": cmds.objectType(c),
                "targets": cmds.listConnections(c + '.target', source=True, destination=False) or []
            }})
        
        _mcp_results = {{
            "constraints": constraint_info,
            "message_links": cmds.listConnections('{node_name}.message', destination=True, source=False, plugs=True) or [],
            "driven_keys": cmds.setDrivenKeyframe('{node_name}', query=True, cd=True) or []
        }}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_influence_joints(mesh_name: str):
        """
        获取 Mesh 的影响骨骼列表及其权重范围（min/max）。
        """
        code = f"""
        import maya.cmds as cmds
        skin_clusters = cmds.ls(cmds.listHistory('{mesh_name}'), type='skinCluster')
        if skin_clusters:
            sc = skin_clusters[0]
            joints = cmds.skinCluster(sc, q=True, influence=True) or []
            vtx_count = cmds.polyEvaluate('{mesh_name}', vertex=True)
            result = []
            for jnt in joints:
                # 逐顶点查询权重（skinPercent 传 list 返回平均值，必须逐个查）
                weights = []
                for i in range(vtx_count):
                    w = cmds.skinPercent(sc, '{mesh_name}.vtx[{{}}]'.format(i), transform=jnt, q=True)
                    weights.append(w)
                result.append({{
                    "joint": jnt,
                    "min_weight": round(min(weights), 4),
                    "max_weight": round(max(weights), 4),
                    "num_affected_verts": sum(1 for w in weights if w > 0.001)
                }})
            _mcp_results = {{"skinCluster": sc, "influences": result}}
        else:
            _mcp_results = {{"error": "No skinCluster found on '{mesh_name}'"}}
        """
        return conn.execute(code)