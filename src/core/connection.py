import socket
import textwrap
import json
import tempfile
import os
import time

from src.core import config


class MayaConnection:
    def __init__(self, host='127.0.0.1', port=None):
        self.host = host
        self.port = port if port is not None else config.get_port()
        # 用于存放临时 Python 脚本文件的目录
        self._tmp_dir = tempfile.gettempdir()
        # 调用计数器：临时文件名唯一化（PID + 计数），避免多实例/并发互踩
        self._call_counter = 0

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
        log_file = config.get_log_file_path("mcp_connection_debug.log")
        def debug_log(msg):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except Exception:
                pass

        debug_log("=" * 50)
        debug_log("execute() called!")
        debug_log(f"py_code: {py_code[:200]}...")

        clean_user_code = textwrap.dedent(py_code).strip()

        # 为本次执行准备唯一临时文件路径（PID + 计数），避免多实例/并发互踩
        self._call_counter += 1
        file_tag = "_mcp_{0}_{1}".format(os.getpid(), self._call_counter)
        result_file = os.path.join(self._tmp_dir, file_tag + "_result.json").replace('\\', '/')
        script_file = os.path.join(self._tmp_dir, file_tag + "_exec.py").replace('\\', '/')

        # 构造待发送的 Python 执行体
        # 注意：这段代码会被注入到目标 Maya 进程中执行，必须同时兼容
        # Python 2.7 (Maya 2018 及以下) 与 Python 3 (Maya 2022+)。
        # 因此严禁使用 f-string / contextlib.redirect_stdout / io.StringIO /
        # open(encoding=) 等 Py3-only 写法，否则 Maya 2018 会直接 SyntaxError。
        python_lines = [
            "import maya.cmds as cmds",
            "import json, sys, traceback, os",
            # StringIO 选择：Py2 用 StringIO.StringIO（同时接受 str/unicode），
            # Py3 回退到 io.StringIO。
            "try:",
            "    from StringIO import StringIO as _MCP_SIO",
            "except ImportError:",
            "    from io import StringIO as _MCP_SIO",
            "_mcp_output = _MCP_SIO()",
            "_mcp_results = None",
        ]
        if not no_undo:
            python_lines.append("cmds.undoInfo(openChunk=True)")

        # 用手动替换 sys.stdout 代替 contextlib.redirect_stdout（Py2.7 无该 API）
        python_lines += [
            "_mcp_old_stdout = sys.stdout",
            "sys.stdout = _mcp_output",
            "try:",
            textwrap.indent(clean_user_code, '    '),
            "except Exception as _mcp_e:",
            "    _mcp_output.write('MAYA_ERROR: {0}\\n{1}'.format(_mcp_e, traceback.format_exc()))",
            "finally:",
            "    sys.stdout = _mcp_old_stdout",
        ]
        if not no_undo:
            python_lines.append("    cmds.undoInfo(closeChunk=True)")

        # 将结果写入临时 JSON 文件而非 print 到 stdout。
        # ensure_ascii=True -> 输出纯 ASCII，普通 open('w') 在 Py2/Py3 都安全，
        # 彻底规避 Py2 下 unicode/str 写入文本流的编码错误。
        python_lines += [
            "_mcp_captured = _mcp_output.getvalue()",
            "try:",
            "    if isinstance(_mcp_captured, bytes):",
            "        _mcp_captured = _mcp_captured.decode('utf-8', 'replace')",
            "except Exception:",
            "    pass",
            "_mcp_final = {'stdout': _mcp_captured, 'result': _mcp_results}",
            "_mcp_text = json.dumps(_mcp_final, default=str, ensure_ascii=True)",
            "_mcp_f = open(r'{0}', 'w')".format(result_file),
            "try:",
            "    _mcp_f.write(_mcp_text)",
            "finally:",
            "    _mcp_f.close()",
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
            debug_log(f"Connecting to Maya at {self.host}:{self.port}...")
            with socket.create_connection((self.host, self.port), timeout=timeout) as s:
                debug_log("Connected! Sending code...")
                s.sendall(full_py_code.encode('utf-8'))
                # 关闭写端，通知 Maya 代码发送完毕
                try:
                    s.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                debug_log("Reading socket response...")
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
                debug_log(f"Socket closed. Response: {repr(full_res)}")

            debug_log(f"Waiting for result file: {result_file}...")
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
                debug_log("Result file found!")
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    json.loads(content)  # validate
                    debug_log("Successfully parsed result JSON.")
                    # 清理本次调用的临时文件
                    for tmp_path in (result_file, script_file):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                    return content
                except Exception as parse_err:
                    debug_log(f"Failed to parse result JSON: {parse_err}")
                    return json.dumps({
                        "error": "Failed to parse result JSON",
                        "raw": content[:4000] if 'content' in dir() else "",
                        "mel_echo": full_res[:2000]
                    })
            else:
                debug_log("Result file NOT generated!")
                return json.dumps({
                    "error": "Result file not generated - Maya may not have executed the script",
                    "mel_echo": full_res[:2000]
                })

        except Exception as e:
            debug_log(f"Socket connection exception: {e}")
            return json.dumps({"error": f"Socket connection failed: {str(e)}"})