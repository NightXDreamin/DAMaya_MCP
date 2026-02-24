# DAMaya_MCP

专为Autodesk Maya设计的MCP工具，它为AI提供了深度感知、诊断及自动化操作 Maya 场景以及运行Python的能力。是专为Maya使用者设计的下一代生产力工具。

## 快速开始
1. 在 Maya 的 Python 脚本编辑器中执行以下代码开启监听端口
   ```
   import maya.cmds as cmds
   cmds.commandPort(n=':7022', sourceType='python', echoOutput=True)
   ```
   (注：项目中也提供了 RUNMEINMAYA.py 自动化配置脚本)
   
3. 安装依赖：
   ```
   pip install -r requirements.txt
   python server.py
   ```
4. 接入 AI IDE
   在支持 MCP 的客户端中添加以下配置：
   ```
   {
     "mcpServers": {
       "DAMaya_MCP": {
         "command": "path/to/your/folder/DAMaya_MCP/.venv/Scripts/python.exe",
         "args": ["path/to/your/folder/DAMaya_MCP/server.py"]
       }
     }
   }
   ```
