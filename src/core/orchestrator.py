from mcp.server.fastmcp import FastMCP
from src.core.connection import MayaConnection
from src.modules.perception import register_perception_tools
from src.modules.rigging import register_rigging_tools
from src.modules.ue_pipeline import register_ue_tools

class MayaOrchestrator:
    def __init__(self, name="Maya-Orchestrator-Pro", port=7022):
        # 初始化 FastMCP
        self.mcp = FastMCP(name)
        # 初始化 Maya 连接
        self.conn = MayaConnection(port=port)
        
        # 自动执行注册
        self._register_all_modules()

    def _register_all_modules(self):
        """将分散在各文件的工具注册到统一的 mcp 实例中"""
        register_perception_tools(self.mcp, self.conn)
        register_rigging_tools(self.mcp, self.conn)
        register_ue_tools(self.mcp, self.conn)

    def run(self):
        """启动服务"""
        self.mcp.run()