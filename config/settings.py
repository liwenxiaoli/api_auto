"""读取 config/config.yaml，把配置暴露成常量。

为什么单独弄这个文件？
    代码里到处写 BASE_URL = "https://..." 是坏习惯 —— 换环境要改 N 处。
    统一从这里读，改 yaml 就够。
"""
from pathlib import Path

import yaml

# __file__ 是当前文件，parent 是 config/，再 parent 是项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
DATA_DIR = BASE_DIR / "data"


def _load():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


_cfg = _load()

BASE_URL = _cfg["base_url"].rstrip("/")
TIMEOUT = _cfg["timeout"]
USER = _cfg["user"]
