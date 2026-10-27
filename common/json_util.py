"""用 jsonpath 从响应里取值。

为什么需要它？
    接口返回的 JSON 经常嵌套很深，比如取商品分类名要写：
        resp.json()["category"]["name"]
    一旦中间某层不存在（比如 category 为 None），就会 KeyError 崩溃。

    用 jsonpath 写成 "category.name"，取不到返回 None，不会崩，还能写进 yaml 配置。
"""
from jsonpath import jsonpath


def json_get(data, expr):
    """按 jsonpath 表达式取值。

    例：
        json_get(resp.json(), "id")             -> 183
        json_get(resp.json(), "category.name")  -> "Updated Category Name"
        json_get(resp.json(), "[0].title")      -> 第一条商品的标题
        json_get(resp.json(), "not.exist")      -> None（不报错）
    """
    result = jsonpath(data, expr)
    if result is False or result is None:   # jsonpath 取不到时返回 False
        return None
    return result[0] if len(result) == 1 else result
