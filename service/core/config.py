"""加载配置文件"""
import yaml
from utils.file import get_abs_path
def load_app_conf(path:str = get_abs_path("config.yaml")):
    with open(path, 'r',encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config

conf = load_app_conf()

if __name__=='__main__':
    print(conf)