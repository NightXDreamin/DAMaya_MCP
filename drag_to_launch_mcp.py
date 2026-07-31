# -*- coding: utf-8 -*-
"""
DAMaya MCP - Quick Viewport Drag-and-Drop Launcher
--------------------------------------------------
兼容 Python 2.7 (Maya 2018及以下) 与 Python 3 (Maya 2022及以上)。
使用方法：直接将此文件拖入 Maya 3D 视图（Viewport）即可瞬间开启端口并拉起后台服务。
"""

import os
import subprocess
import maya.cmds as cmds


try:
    basestring
except NameError:
    basestring = str


def find_dragged_path(args, kwargs):
    for arg in args:
        if isinstance(arg, basestring) and (arg.endswith('.py') or arg.endswith('.pyc')):
            if os.path.exists(arg):
                return arg
    for k, v in kwargs.items():
        if isinstance(v, basestring) and (v.endswith('.py') or v.endswith('.pyc')):
            if os.path.exists(v):
                return v
    return None


def _read_port(project_root):
    """
    从 config.json 读取 commandPort 端口（Py2/Py3 兼容，默认 7022）。
    """
    try:
        import json as _json
        cfg_path = os.path.join(project_root, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as _f:
                cfg = _json.load(_f)
            port = cfg.get("commandport_port")
            if port is None:
                port = cfg.get("server_port")
            if port:
                return int(port)
    except Exception:
        pass
    return 7022


def run_launch(dragged_path=None):
    # 0. 先解析项目根目录（用于读 config.json 与启动后台 server）
    if dragged_path:
        project_root = os.path.dirname(os.path.abspath(dragged_path)).replace('\\', '/')
    else:
        try:
            project_root = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
        except Exception:
            project_root = os.getcwd().replace('\\', '/')

    # 1. 开启 CommandPort（端口从 config.json 读取）
    port_str = ":{0}".format(_read_port(project_root))
    if cmds.commandPort(port_str, q=True):
        try:
            cmds.commandPort(n=port_str, cl=True)
            print("DAMaya MCP: Closed existing port " + port_str)
        except Exception as e:
            print("DAMaya MCP Warning: Error closing port: " + str(e))

    try:
        # 打开 Python 协议 of CommandPort，关闭 echoOutput 避免回传数据类型错误
        cmds.commandPort(n=port_str, sourceType="python", echoOutput=False)
        port_msg = "Successfully opened CommandPort " + port_str + " (Python protocol)"
        print("DAMaya MCP: " + port_msg)
    except Exception as e:
        port_msg = "Failed to open CommandPort: " + str(e)
        cmds.confirmDialog(title="DAMaya MCP Error", message=port_msg, button=["OK"])
        return

    # 2. 寻找本地的 .venv 虚拟环境并静默启动后台 MCP Server

    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    
    # 兼容入口文件名为 main.py 或 server.py
    server_py = os.path.join(project_root, "main.py")
    if not os.path.exists(server_py):
        server_py = os.path.join(project_root, "server.py")
    
    server_msg = ""
    if os.path.exists(venv_python) and os.path.exists(server_py):
        try:
            # 兼容 Windows 的后台无弹窗运行
            creationflags = 0
            if os.name == 'nt':
                creationflags = 0x08000000  # CREATE_NO_WINDOW
                
            subprocess.Popen(
                [venv_python, server_py],
                cwd=project_root,
                creationflags=creationflags
            )
            server_msg = "\n\nBackground Python MCP server process launched successfully."
        except Exception as e:
            server_msg = "\n\nFailed to start background process: " + str(e)
    else:
        server_msg = "\n\nCould not find .venv virtual environment or main.py/server.py in:\n" + project_root + "\nPlease verify that this script is placed in the project root directory."

    # 3. 弹窗提示用户
    cmds.confirmDialog(
        title="DAMaya MCP Launcher",
        message=port_msg + server_msg,
        button=["OK"]
    )


def onMayaDroppedPython(*args, **kwargs):
    """
    拖入 Maya 视口时自动触发的特殊函数。
    """
    path = find_dragged_path(args, kwargs)
    run_launch(path)


def onMayaDroppedPythonFile(*args, **kwargs):
    """
    部分 Maya 版本中拖入视口时触发的特殊函数名称。
    """
    path = find_dragged_path(args, kwargs)
    run_launch(path)


if __name__ == "__main__":
    # 如果用户在 Maya 脚本编辑器中手动运行此脚本，直接执行 launch
    run_launch()
