# DAMaya MCP (Technical Artist Suite)

基于 Model Context Protocol (MCP) 协议的 Autodesk Maya TA 联动控制台与自动化工具集，支持外部 AI 客户端（如 Claude、Cursor、VS Code）与 Maya 本地会话的深度交互。

---

## 🌟 核心特性

- **图形化控制面板 (PySide)**：内置独立的控制面板窗口，兼容 PySide2 与 PySide6，具备双状态灯心跳监控（CommandPort 端口及外部 Server 进程）、可视化 TA 工具箱、以及带有日志导出功能的控制台。
- **Maya 顶栏菜单集成**：自动在 Maya 主窗口菜单栏中注册 `DAMaya MCP` 原生菜单，支持一键打开面板、管理服务生命周期、或直接运行高频诊断。
- **智能化自动启动**：自带注册表感知安装器，支持开机自动打开 Maya 通信端口并智能托管 MCP 守护进程，可一键撤回安装，无损保留用户其他 `userSetup.py` 配置。
- **标准化代码执行器**：提供核心级工具 `execute_python_code`。执行代码自动包裹于 Maya 的事务块（Undo Chunk）中，支持撤销（Ctrl+Z），完全兼容 `code` 与 `python_code` 参数别名，完美规避 AI 客户端的调用校验崩溃。
- **智能选择降级容错**：关键诊断工具全部支持缺省参数调用。当外部未指定目标节点时，自动默认降级应用 Maya 场景中的当前选择，实现极高的人机协同流畅度。

---

## 🚀 快速开始

### 0. 前置要求
- **Python 3.10+**：独立安装的 Python（后台 MCP 服务由其驱动，与 Maya 内置 Python 无关），推荐 3.11+。
- **Autodesk Maya**：任意带有 PySide 的现代版本。
- **一个 MCP 客户端**：Claude Desktop、Cursor 或 VS Code 等。

### 1. 创建虚拟环境并安装依赖
在项目根目录下，创建 `.venv` 虚拟环境并安装 `requirements.txt` 中的依赖：

**Windows（PowerShell / CMD）：**
```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux：**
```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

> 💡 说明：`mcp`、`pydantic` 等后台服务依赖都隔离安装在这个 `.venv` 中，避免污染系统 Python。步骤 3 的 `generate_mcp_config.py` 在检测到 `.venv` 缺失时也会自动创建并安装依赖，因此即便跳过本步骤也能兜底；但手动先完成一遍能更早暴露环境问题。

### 2. 自动挂载至 Maya 启动链
在项目根目录下，使用 Python 运行安装器：
```bash
python install_maya_mcp.py
```
*注：安装程序会自动定位您的 Maya 脚本目录，并安全、幂等地修改 `userSetup.py`，无损保留您原有的配置。*

### 3. 生成 MCP 客户端配置
在项目根目录下运行配置辅助程序：
```bash
python generate_mcp_config.py
```
*注：该脚本会复用（或自动创建）`.venv` 并确保依赖已安装，然后在终端打印标准的 JSON 配置块及常用存放路径，并保持窗口开启以便复制粘贴。*

### 4. 重启 Maya
重启 Maya 后，系统会自动：
1. 开启 TCP 通信端口（默认 `:7022`，可通过项目根 `config.json` 的 `commandport_port` 修改）；
2. 启动顶栏主菜单 `DAMaya MCP`；
3. 根据配置自动引导外部后台 MCP 守护进程。

> ⚙️ 补充：`install_maya_mcp.py` 与 `generate_mcp_config.py` 本身只用 Python 标准库，用系统 `python` 运行即可；真正需要依赖的是后台 MCP 服务 `main.py`，它由 `.venv` 中的 Python 驱动。

---

## 🛠️ TA 工具箱列表

### Perception (场景感知)
- `execute_python_code(code=None, python_code=None)`：核心标准化通道，用于在事务块内安全执行任意 Python 代码。同时支持 `code` 与遗留命名 `python_code` 参数。
- `get_scene_summary()`：快速扫描大纲节点，统计真实 Mesh、Joint、Camera、Constraint、Material 数量（已过滤 Intermediate 中间体节点）。
- `get_selection_context()`：查询当前选择对象的数量、列表及首选节点类型。
- `get_node_attributes(node_name=None)`：检索指定节点的属性集（可键控/自定义属性及类型）。**若未指定参数，默认应用 Maya 当前选择。**
- `query_scene_topology(pattern="*", node_type="transform")`：深度查询节点拓扑、连接细节及 DAG 父子层级（自动跳过非 DAG 节点）。
- `search_nodes_by_attribute(attr_name, value_pattern=None)`：精准/模糊搜索场景中带有特定自定义属性的节点。
- `capture_viewport(output_name="ai_capture.jpg")`：后台生成当前视口的 playblast 截图。
