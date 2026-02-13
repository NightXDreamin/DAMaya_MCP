import maya.cmds as cmds

port_str = ":7022"


if cmds.commandPort(port_str, q=True):
    try:

        cmds.commandPort(n=port_str, cl=True)
        print(f"已关闭现有的端口 {port_str}")
    except Exception as e:
        print(f"关闭端口时遇到错误: {e}")

try:
    cmds.commandPort(n=port_str, sourceType="python", echoOutput=True)
    print(f"成功开启端口 {port_str}，协议类型：Python")
except RuntimeError:
    print(f"致命错误：端口 {port_str} 仍被占用。请检查是否有另一个 Maya 在运行，或尝试更换端口。")