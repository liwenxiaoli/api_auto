"""读取 data/ 目录下的 yaml 用例数据。"""
from config.settings import DATA_DIR
from common.logger import logger
import yaml


def load_yaml(filename):
    """把 data/xxx.yaml 读成 Python 的 dict 或 list。"""
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("读取用例数据: %s", path.name)
    return data
