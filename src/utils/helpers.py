import os

def format_maya_path(path: str):
    """
    将 Windows 风格路径（反斜杠）规范化为 Maya/Unix 风格的正斜杠路径。

    该函数用于保证在跨平台导出或传递给 Maya API 时路径格式的一致性。
    """
    return path.replace('\\', '/')

def get_project_root():
    """
    返回当前 Maya 项目的根路径（占位实现）。

    注意：此处保留占位符实现，调用方可根据实际部署环境实现基于 `cmds.workspace` 或环境变量的解析逻辑，以确定导出与缓存目录。
    """
    pass