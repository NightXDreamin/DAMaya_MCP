import socket
import textwrap
import json
import tempfile
import os
import time


class MayaConnection:
    def __init__(self, host='127.0.0.1', port=7022):
        self.host = host
        self.port = port
        # 用于存放临时 Python 脚本文件的目录
        self._tmp_dir = tempfile.gettempdir()

    def execute(self, py_code: str, timeout: float = 30, no_undo: bool = False):
        """
        在远程 Maya 会话中通过 commandPort (Python 协议, echoOutput=False) 执行 Python 代码并返回结构化输出。

        功能说明：
        - 直接发送 Python 代码到 Maya 的 commandPort (sourceType=python)。
        - 关闭 echoOutput 避免 Maya 2024 Python 3 下 str/bytes 类型不匹配的 TypeError。
        - 执行结果写入临时 JSON 文件，由本端读取后返回。
        - 在执行期间使用 undo chunk 包裹以保证操作可回退（可通过 no_undo 关闭）。

        参数：
        - timeout: socket 超时秒数，默认30秒。长运行操作（如编译/导出）可设更大值。
        - no_undo: 若为 True 则不包裹 undo chunk（适用于只读查询或外部子进程调用）。

        前置条件：Maya 端需要开启 Python 类型的 commandPort (echoOutput=False)：
            cmds.commandPort(n=':7022', sourceType='python', echoOutput=False)
        """
        clean_user_code = textwrap.dedent(py_code).strip()

        # 为本次执行准备临时文件路径
        result_file = os.path.join(self._tmp_dir, '_mcp_result.json').replace('\\', '/')
        script_file = os.path.join(self._tmp_dir, '_mcp_exec.py').replace('\\', '/')

        # 构造待发送的 Python 执行体
        python_lines = [
            "import maya.cmds as cmds",
            "import json, io, contextlib, traceback, os",
        ]
        if not no_undo:
            python_lines.append("cmds.undoInfo(openChunk=True)")

        python_lines += [
            "_mcp_output = io.StringIO()",
            "_mcp_results = None",
            "try:",
            "    with contextlib.redirect_stdout(_mcp_output):",
            textwrap.indent(clean_user_code, '        '),
            "except Exception as _mcp_e:",
            "    _mcp_output.write(f'MAYA_ERROR: {_mcp_e}\\n{traceback.format_exc()}')",
        ]

        if not no_undo:
            python_lines += [
                "finally:",
                "    cmds.undoInfo(closeChunk=True)",
            ]

        # 将结果写入临时 JSON 文件而非 print 到 stdout
        python_lines += [
            "_mcp_final = {'stdout': _mcp_output.getvalue(), 'result': _mcp_results}",
            f"with open(r'{result_file}', 'w', encoding='utf-8') as _mcp_f:",
            "    json.dump(_mcp_final, _mcp_f, default=str, ensure_ascii=False)",
        ]

        full_py_code = "\n".join(python_lines) + "\n"

        # 清理旧的结果文件
        if os.path.exists(result_file):
            os.remove(result_file)

        # 将 Python 脚本写入临时文件
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(full_py_code)

        # 直接发送 Python 代码（commandPort sourceType=python, echoOutput=False）
        # 由于关闭了 echoOutput，不会有 bytes/str 回传问题
        # 结果通过临时 JSON 文件传递

        try:
            with socket.create_connection((self.host, self.port), timeout=timeout) as s:
                s.sendall(full_py_code.encode('utf-8'))
                # 关闭写端，通知 Maya 代码发送完毕
                try:
                    s.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                # echoOutput=False 时不会回传数据，但仍需读取以正常关闭连接
                full_res = ""
                while True:
                    try:
                        data = s.recv(65536)
                        if not data:
                            break
                        full_res += data.decode('utf-8', errors='replace')
                    except socket.timeout:
                        break

            # 等待结果文件生成（Maya 执行可能有延迟）
            deadline = time.time() + timeout
            while time.time() < deadline:
                if os.path.exists(result_file):
                    try:
                        size = os.path.getsize(result_file)
                        if size > 0:
                            break
                    except OSError:
                        pass
                time.sleep(0.15)

            # 读取结果文件
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    json.loads(content)  # validate
                    return content
                except Exception:
                    return json.dumps({
                        "error": "Failed to parse result JSON",
                        "raw": content[:4000] if 'content' in dir() else "",
                        "mel_echo": full_res[:2000]
                    })
            else:
                return json.dumps({
                    "error": "Result file not generated - Maya may not have executed the script",
                    "mel_echo": full_res[:2000]
                })

        except Exception as e:
            return json.dumps({"error": f"Socket connection failed: {str(e)}"})