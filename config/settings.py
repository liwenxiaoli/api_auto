"""读取 config/config.yaml，按"环境"暴露配置。

为什么单独弄这个文件？
    代码里到处写 BASE_URL = "https://..." 是坏习惯 —— 换环境要改 N 处。

两种用法：
    1. 简单脚本 / 练习：``from config.settings import BASE_URL``  → 默认环境的值
    2. 正式用例（支持 --env 切换）：``from config import settings`` → ``settings.BASE_URL``

为什么要分两种？
    模块级常量（BASE_URL）是在 import 那一刻就定死的，切换环境后不会变；
    settings 对象里的值是活的，pytest_configure 里调 configure() 就能换。
"""
from pathlib import Path

import yaml

# __file__ 是当前文件，parent 是 config/，再 parent 是项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
DATA_DIR = BASE_DIR / "data"


def _load_raw():
    """把 yaml 原样读进来，不做任何加工。"""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    """一份环境的配置。切换环境 = 把里面的值换掉。"""

    def __init__(self, raw, env):
        self.raw = raw                      # 完整配置，留着查可用环境
        self.configure(env)

    def configure(self, env):
        """切到指定环境。环境不存在就直接报错，绝不静默用默认值。"""
        environments = self.raw.get("environments") or {}
        if env not in environments:
            raise KeyError(
                f"环境 [{env}] 不存在。可用环境：{list(environments.keys())}"
            )

        conf = environments[env]
        self.env = env
        self.base_url = conf["base_url"].rstrip("/")   # rstrip 去掉结尾多余的 /
        self.timeout = conf["timeout"]
        self.user = conf["user"]

    @property
    def available_envs(self):
        """yaml 里配了哪些环境。"""
        return list((self.raw.get("environments") or {}).keys())

    def __repr__(self):
        return f"<Config env={self.env} base_url={self.base_url} timeout={self.timeout}>"


_raw = _load_raw()
DEFAULT_ENV = _raw.get("default_env") or "dev"

# 全局唯一的配置对象。conftest.py 里会根据 --env 调 settings.configure(环境名)
settings = Config(_raw, DEFAULT_ENV)

# 默认环境的常量（给练习脚本、临时脚本用，不支持切换）
BASE_URL = settings.base_url
TIMEOUT = settings.timeout
USER = settings.user
