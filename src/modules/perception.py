import json

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
        code = f"""
        import maya.cmds as cmds
        type_str = '{node_type}'
        types = [t.strip() for t in type_str.split(',')]
        
        all_nodes = []
        for t in types:
            found = cmds.ls('{pattern}', type=t, long=True) or []
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
    def run_custom_diagnostic(python_code: str):
        """
        执行传入的 Python 代码字符串并返回执行结果。

        设计用于在受控环境下运行自定义诊断或分析脚本。调用方应负责保证代码来源可信并进行必要的安全与错误处理。
        """
        return conn.execute(python_code)
    @mcp.tool()
    def capture_viewport(output_name: str = "ai_capture.jpg"):
        """
        在当前 Maya 会话中对活动视口生成截图并返回文件路径与操作信息。

        截图文件写入用户临时目录，返回值包含操作消息与写入路径，便于后续上传或归档。
        """
        code = f"""
        import maya.cmds as cmds
        import os
        # 获取用户临时目录
        tmp_dir = cmds.internalVar(userTmpDir=True)
        full_path = os.path.join(tmp_dir, '{output_name}')
        
        # 生成视口截图（playblast），以当前帧为基准并写入指定文件
        cmds.viewFit(all=True)
        cmds.playblast(frame=cmds.currentTime(q=True), format='image', 
                       viewer=False, compression='jpg', completeFilename=full_path)
        
        _mcp_results = {{"message": "Screenshot saved", "path": full_path}}
        """
        return conn.execute(code)

    @mcp.tool()
    def get_node_attributes(node_name: str):
        """
        检索指定节点的属性集，包括可键控属性（keyable）、用户自定义属性以及节点类型。

        如果节点不存在，返回带错误标识的结构。该信息用于节点级别的精确诊断、同步与序列化流程。
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
    