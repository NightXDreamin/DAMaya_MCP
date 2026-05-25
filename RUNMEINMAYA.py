import maya.cmds as cmds

port_str = ":7022"


if cmds.commandPort(port_str, q=True):
    try:
        cmds.commandPort(n=port_str, cl=True)
        print(f"已关闭现有的端口 {port_str}")
    except Exception as e:
        print(f"关闭端口时遇到错误: {e}")

try:
    # 使用 Python 协议，但关闭 echoOutput
    # Maya 2024 Python 3 下 echoOutput=True 会导致 CommandPort 回传结果时
    # str/bytes 类型不匹配的 TypeError，关闭后结果通过临时文件传递
    cmds.commandPort(n=port_str, sourceType="python", echoOutput=False)
    print(f"成功开启端口 {port_str}，协议类型：Python (echoOutput=False)")
except RuntimeError:
    print(f"致命错误：端口 {port_str} 仍被占用。请检查是否有另一个 Maya 在运行，或尝试更换端口。")