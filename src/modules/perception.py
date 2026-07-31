def _lit(v, none_as_str="None"):
    """
    将工具参数转为可安全注入 Maya 的 Python 源码字面量。

    使用 repr() 而非手工 f-string 拼接，正确处理引号、换行、反斜杠等特殊字符，
    避免用户输入含引号时注入代码直接 SyntaxError。
    """
    if v is None:
        return repr(none_as_str)
    return repr(v)


def register_perception_tools(mcp, conn):
    @mcp.tool()
    def query_scene_topology(pattern: str = "*", node_type: str = "transform"):
        """
        查询场景拓扑并返回结构化节点信息。

        返回结构包括：节点名称、类型、完整路径、父节点、子节点，以及输入/输出连接。
        该工具用于在自动化与生产流水线中获取明确的层级与连接关系，以支持后续分析、同步或诊断。

        参数说明：
        - `pattern`: Maya 节点匹配模式（默认为全部 `*`）。
        - `node_type`: 支持以逗号分隔的节点类型列表，例如 "transform,joint,constraint"。
        """
        type_lit = _lit(node_type)
        pattern_lit = _lit(pattern)
        code = f"""
        import maya.cmds as cmds
        type_str = {type_lit}
        types = [t.strip() for t in type_str.split(',')]
        
        all_nodes = []
        for t in types:
            found = cmds.ls({pattern_lit}, type=t, long=True) or []
            all_nodes.extend(found)
        
        # 对搜索结果去重以保证顺序一致性
        seen = set()
        unique_nodes = []
        for n in all_nodes:
            if n not in seen:
                seen.add(n)
                unique_nodes.append(n)
        
        _mcp_results = []
        for n in unique_nodes[:30]:
            is_dag = bool(cmds.ls(n, dag=True))
            _mcp_results.append({{
                "name": n.split('|')[-1],
                "type": cmds.objectType(n),
                "path": n,
                "parent": (cmds.listRelatives(n, parent=True) or None) if is_dag else None,
                "children": (cmds.listRelatives(n, children=True) or []) if is_dag else [],
                "connections_in": cmds.listConnections(n, destination=False, source=True, plugs=True) or [],
                "connections_out": cmds.listConnections(n, destination=True, source=False, plugs=True) or []
            }})
        """
        return conn.execute(code)

    @mcp.tool()
    def get_selection_context():
        """
        获取当前 Maya 选择集合的上下文信息。

        返回包含选择数量、对象清单以及首个对象的类型（如存在）。
        该工具仅做只读查询，适用于向 AI 或上游服务提供确定性输入。
        """
        code = """
        sel = cmds.ls(sl=True, long=True)
        _mcp_results = {
            "count": len(sel),
            "items": sel,
            "main_type": cmds.objectType(sel[0]) if sel else None
        }
        """
        return conn.execute(code)

    @mcp.tool()
    def capture_viewport(output_name: str = "ai_capture.jpg"):
        """
        在当前 Maya 会话中对活动视口生成截图并返回文件路径与操作信息。

        截图文件写入用户临时目录，返回值包含操作消息与写入路径，便于后续上传或归档。
        """
        output_lit = _lit(output_name)
        code = f"""
        import maya.cmds as cmds
        import os
        # 获取用户临时目录
        tmp_dir = cmds.internalVar(userTmpDir=True)
        full_path = os.path.join(tmp_dir, {output_lit})
        
        # 生成视口截图（playblast），以当前帧为基准并写入指定文件
        cmds.viewFit(all=True)
        cmds.playblast(frame=cmds.currentTime(q=True), format='image', 
                       viewer=False, compression='jpg', completeFilename=full_path)
        
        _mcp_results = {{"message": "Screenshot saved", "path": full_path}}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_node_attributes(node_name: str = None):
        """
        检索指定节点的属性集，包括可键控属性（keyable）、用户自定义属性以及节点类型。

        如果参数 node_name 未指定，自动默认使用 Maya 当前选择的主选择节点。
        """
        if node_name:
            node_repr = _lit(node_name)
        else:
            node_repr = "cmds.ls(sl=True, long=True)[0] if cmds.ls(sl=True) else ''"
        code = f"""
        import maya.cmds as cmds
        target_node = {node_repr}
        if not target_node or not cmds.objExists(target_node):
            _mcp_results = {{"error": "Node not found or nothing selected"}}
        else:
            _mcp_results = {{
                "keyable": cmds.listAttr(target_node, k=True) or [],
                "user_defined": cmds.listAttr(target_node, ud=True) or [],
                "type": cmds.objectType(target_node),
                "resolved_node": target_node
            }}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_scene_summary():
        """
        获取当前 Maya 场景的大纲概览与统计信息。
        
        返回数据包括：总节点数、Mesh 数量、Joint 骨骼数量、Camera 相机数量、
        Constraint 约束数量、Material 材质球数量以及当前选择的主体。
        该工具极度适合场景健康度分析与场景复杂度审计。
        """
        code = """
        import maya.cmds as cmds
        all_meshes = cmds.ls(type="mesh", long=True) or []
        visible_meshes = [m for m in all_meshes if not cmds.getAttr(m + ".intermediateObject")]
        _mcp_results = {
            "total_nodes": len(cmds.ls(long=True) or []),
            "meshes": len(visible_meshes),
            "joints": len(cmds.ls(type="joint") or []),
            "cameras": len(cmds.ls(type="camera") or []),
            "constraints": len(cmds.ls(type="constraint") or []),
            "materials": len(cmds.ls(type="shadingEngine") or []),
            "selected": cmds.ls(sl=True) or []
        }
        """
        return conn.execute(code)

    @mcp.tool()
    def search_nodes_by_attribute(attr_name: str, value_pattern: str = None):
        """
        在 Maya 场景中搜索具有指定 custom/userDefined 属性或特定属性值的节点。
        
        参数说明：
        - `attr_name`: 属性的精确名称。
        - `value_pattern`: 可选，要匹配的属性值模式（进行模糊或精确匹配）。
        """
        # repr() 生成安全字面量；value_pattern 为 None 时保持旧语义 'None'（不过滤）
        attr_lit = _lit(attr_name)
        value_lit = _lit(value_pattern)
        code = f"""
        import maya.cmds as cmds
        all_nodes = cmds.ls(long=True) or []
        found_nodes = []
        for n in all_nodes:
            if cmds.attributeQuery({attr_lit}, node=n, exists=True):
                val = cmds.getAttr(n + '.' + {attr_lit})
                val_str = str(val)
                patt = {value_lit}
                if patt == 'None' or patt == '' or patt.lower() == 'null':
                    found_nodes.append({{"node": n, "value": val}})
                elif patt in val_str:
                    found_nodes.append({{"node": n, "value": val}})
        _mcp_results = found_nodes[:50]
        """
        return conn.execute(code)
