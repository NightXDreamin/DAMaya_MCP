# Changelog

## [1.2.2] - 2026-08-13

### 安装体验修复
- 兼容 `mcp 2.0.0`：`orchestrator.py` 用 `try/except` 同时导入 `MCPServer`（mcp 2.x）与 `FastMCP`（mcp 1.x），`requirements.txt` 放宽为 `mcp>=1.26,<3`，避免装到 2.x 时启动即 `No module named 'mcp.server.fastmcp'`
- `generate_mcp_config.py` 在缺失 `.venv` 时自动创建虚拟环境并安装 `requirements.txt` 依赖，生成的 MCP 配置 `command` 回退到系统 Python，不再硬编码指向不存在的 `.venv/Scripts/python.exe`
- `start_mcp_server.bat` 移除硬编码的绝对路径，改用 `%~dp0` 定位项目目录，入口指向 `main.py`
- 修正 `server_manager.py` 中陈旧的 `server.py` 注释（实际入口为 `main.py`）
- README 更正配置脚本文件名 `generate_mcp_config.py`，补充虚拟环境创建说明

## [1.2.1] - 2025-07-31

### 轻量化（Breaking）
- 移除 Rigging 诊断工具（`check_nan_weights` / `zero_out_transforms` / `trace_rig_logic` / `get_influence_joints`）
- 移除 UE Pipeline 工具（`validate_for_ue` / `validate_texture_resolutions` / `auto_rename_for_ue` / `quick_export_fbx`）
- 移除 UI 的 Toolbox 页卡，控制面板仅保留 Dashboard 与 Logs
- 移除 Maya 菜单中的 Quick TA Diagnostics 子菜单（保留 Get Selection Context）

### 架构优化
- 新增 `src/core/config.py` 集中配置：端口、项目根、日志路径统一管理，换端口只需改 `config.json`
- 移除 `connection.py` 中硬编码的用户绝对日志路径
- `orchestrator.py` 改为自动发现注册 `src/modules/*.py` 中的 `register_*_tools(mcp, conn)`，新增工具模块无需改 orchestrator
- 工具注入参数改用 `repr()` 安全转义，修复参数含引号/换行导致注入 SyntaxError 的问题
- MCP 临时结果/脚本文件唯一化（PID + 计数），避免多实例并发互踩
- `server_manager.py` 配置读写统一走 `config.py`

### 仓库卫生
- 测试脚本移入 `tests/`，删除运行残留（`test_run.txt`、`stderr*.log`）
- `.gitignore` 排除 `.mcp_server.pid`
- 文档同步：移除 README 中已删除工具的章节

### UI 简约化
- 控制面板改为极简深色风格：移除紫色 accent 与 GroupBox 边框装饰
- 头部版本号不再硬编码，统一从 `src.__version__` 读取（当前 v1.2.1）
- 窗口尺寸缩小，按钮文案精简为 Open/Close、Start/Stop

## [1.x] - 初始版本

- FastMCP + Maya commandPort 双进程架构
- Perception / Rigging / UE Pipeline 三组共 15 个工具
- Maya 顶栏菜单、PySide 控制面板、一键安装器
