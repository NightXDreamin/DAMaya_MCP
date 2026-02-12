import json

def register_perception_tools(mcp, conn):
    @mcp.tool()
    def query_scene_topology(pattern: str = "*", node_type: str = "transform"):
        """
        深度查询场景拓扑。解决 Opus 无法看到层级和连接的问题。
        返回：节点名称、类型、父级、子级、以及输入/输出连接。
        node_type 支持逗号分隔多类型，如 "transform,joint,constraint"。
        """
        code = f"""
        import maya.cmds as cmds
        type_str = '{node_type}'
        types = [t.strip() for t in type_str.split(',')]
        
        all_nodes = []
        for t in types:
            found = cmds.ls('{pattern}', type=t, long=True) or []
            all_nodes.extend(found)
        
        # 去重并保持顺序
        seen = set()
        unique_nodes = []
        for n in all_nodes:
            if n not in seen:
                seen.add(n)
                unique_nodes.append(n)
        
        _mcp_results = []
        for n in unique_nodes[:30]:
            _mcp_results.append({{
                "name": n.split('|')[-1],
                "type": cmds.objectType(n),
                "path": n,
                "parent": cmds.listRelatives(n, parent=True) or None,
                "children": cmds.listRelatives(n, children=True) or [],
                "connections_in": cmds.listConnections(n, destination=False, source=True, plugs=True) or [],
                "connections_out": cmds.listConnections(n, destination=True, source=False, plugs=True) or []
            }})
        """
        return conn.execute(code)

    @mcp.tool()
    def get_selection_context():
        """
        感知用户当前在 Maya 中选了什么。让 AI 瞬间获得上下文。
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
    def run_custom_diagnostic(python_code: str):
        """
        万能执行器。Opus 优先级最高的工具。
        允许 AI 编写复杂的检测逻辑并直接运行。
        """
        return conn.execute(python_code)
    @mcp.tool()
    def capture_viewport(output_name: str = "ai_capture.jpg"):
        """
        截取 Maya 当前活动视口的截图，并尝试将其路径返回。
        """
        code = f"""
        import maya.cmds as cmds
        import os
        # 获取临时目录
        tmp_dir = cmds.internalVar(userTmpDir=True)
        full_path = os.path.join(tmp_dir, '{output_name}')
        
        # 视口截图逻辑
        cmds.viewFit(all=True) # 自动对焦物体
        cmds.playblast(frame=cmds.currentTime(q=True), format='image', 
                       viewer=False, compression='jpg', completeFilename=full_path)
        
        _mcp_results = {{"message": "Screenshot saved", "path": full_path}}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_node_attributes(node_name: str):
        """
        精准获取某个节点的所有可 Key 属性和 Message 连接，弥补通用查询的不足。
        """
        code = f"""
        import maya.cmds as cmds
        if not cmds.objExists('{node_name}'):
            _mcp_results = {{"error": "Node not found"}}
        else:
            _mcp_results = {{
                "keyable": cmds.listAttr('{node_name}', k=True) or [],
                "user_defined": cmds.listAttr('{node_name}', ud=True) or [],
                "type": cmds.objectType('{node_name}')
            }}
        """
    