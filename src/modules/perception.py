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