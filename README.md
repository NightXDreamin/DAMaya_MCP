# Maya Orchestrator

基于 MCP 协议的 Maya AI 联动助手，专为 TA (Technical Artist) 调试设计。

## 快速开始
1. 在 Maya 中开启端口：
   `import maya.cmds as cmds; cmds.commandPort(n=':7022')`
2. 安装依赖：
   `pip install -r requirements.txt`
3. 运行：
   `python server.py`

## 核心功能
- **Perception**: 深度场景拓扑查询
- **Rigging**: 骨骼权重与约束追踪
- **UE Pipeline**: 导出前自动化审计与 FBX 联动