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
        
        # 为每个约束附加类型信息并去重过滤目标
        constraint_info = []
        for c in unique_constraints:
            raw_targets = cmds.listConnections(c + '.target', source=True, destination=False) or []
            unique_targets = list(dict.fromkeys([t for t in raw_targets if t != c]))
            constraint_info.append({{
                "name": c,
                "type": cmds.objectType(c),
                "targets": unique_targets
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
                # 逐顶点查询权重
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

    @mcp.tool()
    def check_nan_weights(mesh_name: str = "*"):
        """
        检查 Mesh 蒙皮中是否存在 NaN (非数) 或 Infinite (无限大) 权重。
        
        这些异常权重会导致骨骼动画播放时模型产生顶点爆炸或拉伸异常。
        参数说明：
        - `mesh_name`: 指定 Mesh 名字或通配符，默认为全场景 Mesh。
        """
        code = f"""
        import maya.cmds as cmds
        import math
        
        meshes = cmds.ls('{mesh_name}', type='mesh', long=True) or []
        transforms = cmds.ls('{mesh_name}', type='transform', long=True) or []
        for t in transforms:
            shapes = cmds.listRelatives(t, shapes=True, type='mesh', fullPath=True) or []
            meshes.extend(shapes)
        
        meshes = list(set(meshes))
        _mcp_results = []
        
        for m in meshes:
            skin_clusters = cmds.ls(cmds.listHistory(m), type='skinCluster')
            if not skin_clusters:
                continue
            sc = skin_clusters[0]
            
            parent_transform = cmds.listRelatives(m, parent=True, fullPath=True)[0]
            vtx_count = cmds.polyEvaluate(m, vertex=True)
            influences = cmds.skinCluster(sc, q=True, influence=True) or []
            
            nan_vertices = []
            # We sample a max of 2000 vertices to prevent socket timeouts on dense meshes
            step = max(1, vtx_count // 2000)
            for i in range(0, vtx_count, step):
                vtx_name = f"{{parent_transform}}.vtx[{{i}}]"
                for inf in influences:
                    try:
                        w = cmds.skinPercent(sc, vtx_name, transform=inf, q=True)
                        if math.isnan(w) or math.isinf(w):
                            nan_vertices.append({{
                                "vertex": vtx_name,
                                "influence": inf,
                                "weight": w
                            }})
                            break # Go to next vertex
                    except Exception:
                        pass
            if nan_vertices:
                _mcp_results.append({{
                    "mesh": parent_transform,
                    "skinCluster": sc,
                    "corrupted_vertices": nan_vertices[:30],
                    "total_errors": len(nan_vertices)
                }})
        """
        return conn.execute(code)

    @mcp.tool()
    def zero_out_transforms(node_name: str):
        """
        安全零点化指定节点的 Transform 属性。
        
        如果是 Translate/Rotate 则设为 0，Scale 设为 1。
        如果节点拥有锁定的通道，会提供友好提示，仅零点化未锁定的通道。
        """
        code = f"""
        import maya.cmds as cmds
        node = '{node_name}'
        if not cmds.objExists(node):
            _mcp_results = {{"error": f"Node not found: {{node}}"}}
        else:
            results = {{}}
            for attr, default in [('tx', 0), ('ty', 0), ('tz', 0), ('rx', 0), ('ry', 0), ('rz', 0), ('sx', 1), ('sy', 1), ('sz', 1)]:
                full_attr = f"{{node}}.{{attr}}"
                if cmds.getAttr(full_attr, settable=True):
                    try:
                        cmds.setAttr(full_attr, default)
                        results[attr] = "reset_to_one" if attr.startswith('s') else "zeroed"
                    except Exception as e:
                        results[attr] = f"error: {{e}}"
                else:
                    results[attr] = "locked/unsettable"
            _mcp_results = results
        """
        return conn.execute(code)