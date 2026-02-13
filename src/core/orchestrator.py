from mcp.server.fastmcp import FastMCP
from src.core.connection import MayaConnection
from src.modules.perception import register_perception_tools
from src.modules.rigging import register_rigging_tools
from src.modules.ue_pipeline import register_ue_tools

class MayaOrchestrator:
    """
    统一的 Orchestrator，负责构建 MCP 服务并注册各功能模块。

    用途：对外暴露一组生产就绪的工具集合（perception / rigging / ue），并管理与 Maya 的连接。
    """
    def __init__(self, name="Maya-Orchestrator-Pro", port=7022):
        # 创建 FastMCP 服务实例
        self.mcp = FastMCP(name)
        # 配置与 Maya 的网络连接（commandPort）
        self.conn = MayaConnection(port=port)

        # 自动完成模块工具注册
        self._register_all_modules()

    def _register_all_modules(self):
        """
        将各功能模块（perception、rigging、ue_pipeline）注册到同一 MCP 实例。

        该方法负责把模块级工具绑定到 `self.mcp`，使外部客户端通过统一接口调用。
        """
        register_perception_tools(self.mcp, self.conn)
        register_rigging_tools(self.mcp, self.conn)
        register_ue_tools(self.mcp, self.conn)

    def run(self):
        """
        启动 MCP 服务主循环。

        该调用会阻塞当前线程直至服务停止。适用于生产环境的长期驻留进程。
        """
        self.mcp.run()