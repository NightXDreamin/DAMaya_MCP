import os
import importlib

# 兼容 mcp 1.x (FastMCP) 与 mcp 2.x (MCPServer)：
# mcp 2.0.0 起 FastMCP 更名为 MCPServer 并从 mcp.server 导出，旧路径 mcp.server.fastmcp 已移除。
try:
    from mcp.server import MCPServer as _MCPServer  # mcp 2.x
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _MCPServer

from src.core.connection import MayaConnection
from src.core import config


class MayaOrchestrator:
    """
    统一的 Orchestrator，负责构建 MCP 服务并注册各功能模块。

    用途：对外暴露一组生产就绪的工具集合（perception），并管理与 Maya 的连接。
    """
    def __init__(self, name="Maya-Orchestrator-Pro", port=None):
        # 创建 MCP 服务实例（兼容 FastMCP 1.x / MCPServer 2.x）
        self.mcp = _MCPServer(name)
        # 配置与 Maya 的网络连接（commandPort），端口默认取 config.json
        self.conn = MayaConnection(port=port)

        # 自动完成模块工具注册与核心功能注册
        self._register_core_tools()
        self._register_all_modules()

    def _register_core_tools(self):
        """
        注册核心系统层面的通用工具（如规范化执行 Python 代码）。
        """
        @self.mcp.tool()
        def execute_python_code(code: str = None, python_code: str = None) -> str:
            """
            在 Maya 会话中执行任意 Python 代码块（规范化工具通道）。

            该工具在 Maya 中以安全事务（undo chunk）包裹运行，支持撤销操作。
            It can capture stdout, stderr and tracebacks into a structured JSON.

            参数说明：
            - `code`: 要在 Maya 中运行的 Python 代码。
            - `python_code`: 备用参数名（兼容 legacy 命名），与 `code` 作用完全相同。
            """
            actual_code = code if code is not None else python_code
            if not actual_code:
                return "Error: No Python code provided in 'code' or 'python_code' parameter."
            return self.conn.execute(actual_code)

    def _register_all_modules(self):
        """
        自动发现并注册 src/modules/ 下的所有工具模块。

        约定：每个模块文件顶层定义一个或多个 `register_*_tools(mcp, conn)` 函数。
        新增工具模块只需在 src/modules/ 下新建文件，无需修改本文件。
        """
        modules_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules"
        )
        if not os.path.isdir(modules_dir):
            return

        for fname in sorted(os.listdir(modules_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            mod_name = "src.modules." + fname[:-3]
            try:
                module = importlib.import_module(mod_name)
            except Exception as e:
                print(f"[DAMaya MCP] Failed to import module {mod_name}: {e}")
                continue

            registered = False
            for attr_name in dir(module):
                if attr_name.startswith("register_") and callable(getattr(module, attr_name)):
                    getattr(module, attr_name)(self.mcp, self.conn)
                    registered = True
            if not registered:
                print(f"[DAMaya MCP] Warning: no register_*_tools() found in {mod_name}")

    def run(self):
        """
        启动 MCP 服务主循环。

        该调用会阻塞当前线程直至服务停止。适用于生产环境的长期驻留进程。
        """
        self.mcp.run()
