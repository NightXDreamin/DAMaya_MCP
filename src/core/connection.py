import socket
import textwrap
import json

class MayaConnection:
    def __init__(self, host='127.0.0.1', port=7022):
        self.host = host
        self.port = port

    def execute(self, py_code: str):
        """
        在远程 Maya 会话中通过 commandPort 执行 Python 代码并返回结构化输出。

        功能说明：
        - 使用 textwrap.dedent 清理传入代码；在 Maya 端以受控上下文执行。
        - 在执行期间使用 undo chunk 包裹以保证操作可回退。
        - 捕获 stdout 与 _mcp_results 并通过固定的 JSON 边界文本返回。

        前置条件：Maya 端需要开启 Python 类型的 commandPort，例如：
            cmds.commandPort(n=':7022', sourceType='python', echoOutput=True)
        """
        clean_user_code = textwrap.dedent(py_code).strip()
        
        # 构造待发送的 Python 执行体（无需 MEL 包裹）
        python_lines = [
            "import maya.cmds as cmds",
            "import json, io, contextlib, traceback",
            "cmds.undoInfo(openChunk=True)",
            "_mcp_output = io.StringIO()",
            "_mcp_results = None",
            "try:",
            "    with contextlib.redirect_stdout(_mcp_output):",
            textwrap.indent(clean_user_code, '        '),
            "except Exception as _mcp_e:",
            "    _mcp_output.write(f'MAYA_ERROR: {_mcp_e}\\n{traceback.format_exc()}')",
            "finally:",
            "    cmds.undoInfo(closeChunk=True)",
            "_mcp_final = {'stdout': _mcp_output.getvalue(), 'result': _mcp_results}",
            "print(f'MCP_JSON_START:{json.dumps(_mcp_final, default=str)}:MCP_JSON_END')",
        ]
        
        full_py_code = "\n".join(python_lines) + "\n"
        
        try:
            with socket.create_connection((self.host, self.port), timeout=15) as s:
                s.sendall(full_py_code.encode('utf-8'))
                
                full_res = ""
                while True:
                    data = s.recv(16384).decode('utf-8')
                    if not data:
                        break
                    full_res += data
                    if "MCP_JSON_END" in full_res:
                        break
                
                full_res = full_res.strip('\x00').strip()
                
                # 如果返回中包含 MCP 标记则解析 JSON 负载
                if "MCP_JSON_START:" in full_res:
                    try:
                        content = full_res.split("MCP_JSON_START:")[1].split(":MCP_JSON_END")[0].strip()
                        json.loads(content)  # validate
                        return content
                    except Exception:
                        return json.dumps({"error": "Failed to parse JSON from Maya", "raw": full_res})
                
                return json.dumps({"stdout": full_res, "result": None})
                
        except Exception as e:
            return json.dumps({"error": f"Socket connection failed: {str(e)}"})