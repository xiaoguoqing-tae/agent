import hashlib
import os

def get_project_root()->str:
    """
    获取项目根目录
    :return:
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_project_dir()->str:
    """
    获取项目根目录,与 get_project_root 一样
    :return:
    """
    return get_project_root()

def get_abs_path(relative_path:str)->str:
    """
    根据相对路径，获取绝对路径
    :param relative_path:
    :return:
    """
    return os.path.join(get_project_dir(), relative_path)


def get_file_md5(file_path: str) -> str:
    """获取文件MD5值"""

    md5_obj = hashlib.md5()
    chunk_size = 1024 #分片读取文件大小
    try:
        with open(file_path, 'rb') as f:
            while chunk:= f.read(chunk_size):
                md5_obj.update(chunk)
            return md5_obj.hexdigest()
    except Exception as e:
        return ""

def load_text(file_path:str)->str:
    file_path = get_abs_path(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


from pathlib import Path


def safe_delete(filepath):
    """安全删除文件或目录"""
    path = Path(filepath)

    if not path.exists():
        #print(f"不存在: {filepath}")
        return False

    if path.is_file():
        path.unlink()
    return True
        #print(f"已删除文件: {filepath}")
    # elif path.is_dir():
    #     # 确认后再删除目录
    #     confirm = input(f"确认删除目录 {filepath} 及其所有内容? (y/n): ")
    #     if confirm.lower() == 'y':
    #         import shutil
    #         shutil.rmtree(path)
    #         print(f"已删除目录: {filepath}")