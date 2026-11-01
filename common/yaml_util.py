"""读取 data/ 目录下的 yaml 用例数据。"""
import pytest

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


def load_cases(filename):
    """读 yaml 用例，转成带标记的参数列表（供 parametrize 直接用）。

    yaml 里这样写：
        - case: 查询商品列表
          marks: [smoke]        # 可选；不写就是不带标记

    为什么要转成 pytest.param？
        数据驱动下一个函数跑 N 条用例，标记必须挂在「每一条数据」上，
        挂在函数头上会让整份 yaml 全被打上同一个标记。
    """
    params = []
    for case in load_yaml(filename):
        marks = [getattr(pytest.mark, m) for m in case.get("marks", [])]
        params.append(
            pytest.param(case, marks=marks, id=case.get("case"))
        )
    return params
