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

        # 自动完成模块工具注册与核心功能注册
        self._register_core_tools()
        self._register_all_modules()

    def _register_core_tools(self):
        """
        注册核心系统层面的通用工具（如规范化执行 Python 代码）。
        """
        @self.mcp.tool()
        def execute_python_code(code: str) -> str:
            """
            在 Maya 会话中执行任意 Python 代码块（规范化工具通道）。

            该工具在 Maya 中以安全事务（undo chunk）包裹运行，支持撤销操作。
            它能完整捕获 stdout、stderr 和执行期发生的 Traceback 异常，并以结构化 JSON 格式回传。
            """
            return self.conn.execute(code)

    def _register_all_modules(self):
        """
        将各功能模块注册到同一 MCP 实例。

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