"""extract：从响应里取值存进变量池 —— 接口关联的"取"这一半。

配合 common/context.py 一起看：
    extractor 负责"存"，Context.render 负责"取"。
"""
from common.json_util import json_get
from common.logger import logger


def extract(resp_json, rules, ctx):
    """按规则集从响应里提取变量。

    rules 长这样（写在 yaml 的 extract 下面）：
        extract:
          token: $.access_token
          product_id: $.id

    左边是你自己起的名字，右边是 jsonpath 表达式。
    提取完之后，后面的用例就能用 ${token}、${product_id} 了。

    返回：本次提取到的 {变量名: 值}，方便调用方打印或断言。
    """
    if not rules:
        return {}

    saved = {}
    for name, expr in rules.items():
        value = json_get(resp_json, expr)

        # 取不到必须报错。如果这里静默跳过，后面用到 ${token} 的用例
        # 会以"看起来莫名其妙"的方式失败，排查成本高十倍。
        if value is None:
            raise AssertionError(
                f"提取失败：表达式 {expr} 在这份响应里没取到值，实际响应是：{resp_json}"
            )

        ctx.set(name, value)
        saved[name] = value
        logger.info("提取变量 %s = %s（来自表达式 %s）", name, value, expr)

    return saved
