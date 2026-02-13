def register_rigging_tools(mcp, conn):
    @mcp.tool()
    def trace_rig_logic(node_name: str):
        """
        针对骨骼绑定与约束问题的诊断工具。

        返回结构化信息包括：去重后的约束列表、每个约束的类型与目标、相关的 message 连接，以及驱动关键帧信息。
        该工具用于生产级排查 Rig 逻辑错误并生成可序列化的诊断结果。
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
        收集指定 Mesh 的绑定影响信息（skinCluster 的影响关节及其权重统计）。

        返回每个关节的最小/最大权重、受影响顶点数量以及使用的 skinCluster。适合用于导出前的质量分析与自动化校验。
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