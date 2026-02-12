import os

def format_maya_path(path: str):
    """将 Windows 路径转换为 Maya 喜欢的正斜杠路径"""
    return path.replace('\\', '/')

def get_project_root():
    """获取当前 Maya 项目的根目录"""
    # 可以在这里写逻辑让 AI 知道导出的默认位置
    pass