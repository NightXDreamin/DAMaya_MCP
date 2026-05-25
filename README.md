# DAMaya MCP (Technical Artist Suite)

基于 Model Context Protocol (MCP) 协议的 Autodesk Maya TA 联动控制台与自动化工具集，支持外部 AI 客户端（如 Claude Code）与 Maya 本地会话的深度交互。

---

## 核心特性

- **图形化控制面板 (PySide)**：内置独立的控制面板窗口，兼容 PySide2 与 PySide6，具备双状态灯心跳监控（CommandPort 端口及外部 Server 进程）、可视化 TA 工具箱、以及带有日志导出功能的控制台。
- **Maya 顶栏菜单集成**：自动在 Maya 主窗口菜单栏中注册 `DAMaya MCP` 原生菜单，支持一键打开面板、管理服务生命周期、或直接运行高频诊断。
- **智能化自动启动**：自带注册表感知安装器，支持开机自动打开 Maya 通信端口并智能托管 MCP 守护进程，可一键撤回安装，无损保留用户其他 `userSetup.py` 配置。
- **标准化代码执行器**：提供核心级工具 `execute_python_code`。执行代码自动包裹于 Maya 的事务块（Undo Chunk）中，支持撤销（Ctrl+Z），并捕获 `stdout`/`stderr` 与异常 Traceback。

---

## 快速开始

### 1. 自动挂载至 Maya 启动链
在项目根目录下，使用 Python 运行安装器：
```bash
python install_maya_mcp.py
```
*注：安装程序会自动定位您的 Maya 脚本目录，并修改 `userSetup.py`。*

### 2.
运行Generate_MCP_Json.py文件会自动生成MCP配置
在您的IDE的MCP设置中拷贝进配置脚本即可

### 3. 重启 Maya
重启 Maya 后，系统会自动：
1. 开启 TCP 通信端口 `:7022`；
2. 启动顶栏主菜单 `DAMaya MCP`；
3. 根据配置自动引导外部后台 MCP 守护进程。

## TA 工具箱列表

### 1. Perception (场景感知)
- `execute_python_code`：核心标准化通道，用于在事务块内安全执行任意 Python 代码。
- `get_scene_summary`：快速扫描大纲节点，统计真实 Mesh、Joint、Camera、Constraint、Material 数量（已过滤 Intermediate 中间体节点）。
- `get_selection_context`：查询当前选择对象的数量、列表及首选节点类型。
- `query_scene_topology`：深度查询节点拓扑、连接细节及 DAG 父子层级。
- `search_nodes_by_attribute`：精准/模糊搜索场景中带有特定自定义属性的节点。
- `capture_viewport`：后台生成当前视口的 playblast 截图。

### 2. Rigging (绑定诊断)
- `check_nan_weights`：高速扫描网格蒙皮权重，精确定位损坏的 NaN/Inf 权重顶点，防止顶点爆面。
- `zero_out_transforms`：安全零点化 Translate/Rotate，重置 Scale 为 1.0（自动跳过锁定通道并返回状态报告）。
- `trace_rig_logic`：分析目标约束连接、Message 链及 Driven Key 驱动关系（已自动去重并过滤约束自身节点）。
- `get_influence_joints`：详细审计 SkinCluster 的影响骨骼分布、顶点关联计数及权重极值。

### 3. UE Pipeline (虚幻导出流水线)
- `validate_for_ue`：自动化审计 Freeze Transform、Pivot 是否位于原点、以及是否存在未烘焙历史。
- `validate_texture_resolutions`：审计场景贴图分辨率，确保完全符合 2 的幂次方（Power of Two）规范以供虚幻流送。
- `auto_rename_for_ue`：根据行业规范，自动为选择的 Mesh/Joint/Material/File 节点应用 `SM_` / `joint_` / `M_` / `T_` 前缀。
- `quick_export_fbx`：自动化加载 fbx 插件，将场景或选定物体批量安全导出为 FBX 格式。