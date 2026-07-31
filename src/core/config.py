"""
集中配置模块。

所有跨模块共享的配置（端口、路径、日志）统一从这里读取，
避免散落各文件的硬编码（如旧版 connection.py 里的绝对日志路径、
以及散落 5+ 处的 7022 端口）。换机器 / 换端口只需改 config.json。
"""
import os
import json

# 项目根目录：基于本文件位置计算（src/core/config.py -> 项目根）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")

# 默认配置（config.json 不存在时使用）
DEFAULT_CONFIG = {
    "autostart": True,
    # Maya commandPort 端口；server_port 为旧字段，读取时作为兼容回退
    "commandport_port": 7022,
    "server_port": 7022,
}


def get_config():
    """
    读取 config.json。文件不存在或解析失败时返回默认配置。
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config_data):
    """
    将配置写回 config.json。
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_port():
    """
    获取 Maya commandPort 端口。

    优先读 `commandport_port`，兼容旧字段 `server_port`，默认 7022。
    """
    cfg = get_config()
    port = cfg.get("commandport_port")
    if port is None:
        port = cfg.get("server_port")
    if port is None:
        port = DEFAULT_CONFIG["commandport_port"]
    return int(port)


def get_log_file_path(name):
    """
    返回项目根目录下日志文件的绝对路径。

    日志统一放项目根目录（已被 .gitignore 排除），不再硬编码用户绝对路径。
    """
    return os.path.join(PROJECT_ROOT, name)
