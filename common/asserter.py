"""统一断言工具：把"怎么断言"集中在一个地方。

为什么要单独拆一个模块？
    断言散落在各个用例里，格式五花八门，失败信息也各不相同，排查很累。
    集中之后：yaml 只写"期望什么"，断言方式和报错格式全项目统一。

yaml 里能写的三种写法：

    expect:
      $.email: john@mail.com        # ① 普通：取出来等于这个值
      $.price: {gt: 0}              # ② 高级：contains / not_empty / gt / lt
      @length: 1                    # ③ 整体：对整份响应做断言（@ 开头）

⚠️ 为什么整体断言要用 `@length` 而不是 jsonpath 的 `$`？
    这个 jsonpath 库对单独一个 `$` 返回 False（实测），根本取不到东西，
    所以长度为 0 —— 用 `@` 前缀明确区分"这不是 jsonpath 表达式"。
"""
from common.json_util import json_get
from common.logger import logger


def assert_status(resp, expected):
    """断言状态码。

    expected 可以是：
        201                 必须是 201
        [400, 404]          400 或 404 都算过（同一个错误不同站返回的不一样）
    """
    if isinstance(expected, list):
        assert resp.status_code in expected, (
            f"状态码期望 {expected} 之一，实际 {resp.status_code}，响应: {resp.text}"
        )
    else:
        assert resp.status_code == expected, (
            f"状态码期望 {expected}，实际 {resp.status_code}，响应: {resp.text}"
        )
    logger.info("状态码断言通过: %s", resp.status_code)


def assert_expect(data, expects, ctx):
    """按 yaml 的 expect 逐条断言。"""
    for expr, expected in (expects or {}).items():
        expected = ctx.render(expected)          # 期望值也支持 ${...}

        if expr.startswith("@"):
            _assert_whole(data, expr, expected)
        else:
            actual = json_get(data, expr)
            _assert_field(expr, actual, expected, data)


def _assert_whole(data, expr, expected):
    """对整份响应做断言。"""
    if expr == "@length":
        assert len(data) == expected, (
            f"响应条数期望 {expected}，实际 {len(data)}，响应: {data}"
        )
    elif expr == "@not_empty":
        assert bool(data) is expected, (
            f"响应非空期望 {expected}，实际 {bool(data)}，响应: {data}"
        )
    else:
        raise ValueError(f"不支持的整体断言 {expr}。目前支持：@length / @not_empty")
    logger.info("整体断言通过: %s = %s", expr, expected)


def _assert_field(expr, actual, expected, data):
    """对某个字段做断言。expected 是字典就走高级断言，否则就是相等。"""
    if isinstance(expected, dict):
        for op, want in expected.items():
            _assert_advanced(expr, actual, op, want, data)
    else:
        assert actual == expected, (
            f"字段 {expr} 期望 {expected}，实际 {actual}，完整响应: {data}"
        )
        logger.info("字段断言通过: %s = %s", expr, expected)


def _assert_advanced(expr, actual, op, want, data):
    if op == "contains":
        # jsonpath 取出来的可能是列表，逐个检查
        targets = actual if isinstance(actual, list) else [actual]
        assert targets, f"字段 {expr} 取到空值，没法做包含断言，响应: {data}"
        for item in targets:
            assert want in str(item), (
                f"字段 {expr} 的值「{item}」不包含「{want}」，响应: {data}"
            )
    elif op == "not_empty":
        assert bool(actual), f"字段 {expr} 不应为空，实际 {actual}，响应: {data}"
    elif op == "gt":
        assert actual > want, f"字段 {expr} 应大于 {want}，实际 {actual}，响应: {data}"
    elif op == "lt":
        assert actual < want, f"字段 {expr} 应小于 {want}，实际 {actual}，响应: {data}"
    else:
        raise ValueError(
            f"不支持的断言方式 {op}。目前支持：contains / not_empty / gt / lt"
        )
    logger.info("高级断言通过: %s %s %s", expr, op, want)
