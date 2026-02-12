import socket
import textwrap
import json

class MayaConnection:
    def __init__(self, host='127.0.0.1', port=7022):
        self.host = host
        self.port = port

    def execute(self, py_code: str):
        """
        核心执行逻辑：
        1. 包装代码以支持捕获 print 和变量 _mcp_results
        2. 自动开启/关闭 Undo Chunk
        """
        # 使用 textwrap.dedent 确保缩进正确
        safe_code = textwrap.dedent(f"""
            import maya.cmds as cmds
            import json, io, contextlib
            
            cmds.undoInfo(openChunk=True)
            _mcp_output = io.StringIO()
            _mcp_results = None
            
            try:
                with contextlib.redirect_stdout(_mcp_output):
                    # --- AI Code Start ---
                    {textwrap.indent(py_code.strip(), '                    ')}
                    # --- AI Code End ---
            except Exception as e:
                print(f"MAYA_ERROR: {{e}}")
            finally:
                cmds.undoInfo(closeChunk=True)
            
            # 构造统一的返回格式
            final_response = {{
                "stdout": _mcp_output.getvalue(),
                "result": _mcp_results
            }}
            print(f"MCP_JSON_START:{{json.dumps(final_response)}}:MCP_JSON_END")
        """)
        
        try:
            with socket.create_connection((self.host, self.port), timeout=15) as s:
                s.sendall(safe_code.encode('utf-8'))
                
                # 循环接收数据直到结束
                full_res = ""
                while True:
                    data = s.recv(8192).decode('utf-8')
                    if not data: break
                    full_res += data
                    if "MCP_JSON_END" in full_res: break
                
                # 从原始输出中提取我们的 JSON 报文
                if "MCP_JSON_START:" in full_res:
                    json_str = full_res.split("MCP_JSON_START:")[1].split(":MCP_JSON_END")[0]
                    return json_str
                return full_res
        except Exception as e:
            return json.dumps({"error": f"Connection failed: {str(e)}"})