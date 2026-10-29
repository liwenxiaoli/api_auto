"""通用用例执行器：把一份 yaml 用例数据变成一次真实的接口调用。

它把流程固化成 5 步，以后加场景只改 yaml，代码一行不动：
    渲染占位符 -> 发请求 -> 断言状态码 -> 提取变量 -> 断言响应字段

这就是"框架"和"一堆脚本"的分界线：
    脚本里，每加一个接口就要再写一遍 requests 调用 + 断言；
    框架里，这些都写一次，数据只负责描述"这次要调什么、期望什么"。
"""
import allure

from common.asserter import assert_expect, assert_status
from common.extractor import extract
from common.logger import logger
from common.sign import add_sign


def _apply_sign(kwargs, conf, ctx):
    """按 yaml 里的 sign 配置给请求签名（第 8 周）。

    yaml 写法：
        sign:
          secret: my_secret     # 密钥（真实项目里应从配置/环境变量读，不要写死在 yaml）
          on: params            # 对谁签名：params / json（默认 params）
          in: params            # 签名值放哪：params / headers（默认跟 on 一样）
          field: sign           # 签名字段名（默认 sign）
    """
    secret = ctx.render(conf["secret"])        # 密钥也支持 ${...}，方便从配置读
    field = conf.get("field", "sign")
    source_name = conf.get("on", "params")     # 参与签名的参数
    target_name = conf.get("in", source_name)  # 签名值放哪儿

    source = kwargs.get(source_name) or {}
    signed = add_sign(source, secret, field)

    if target_name == source_name:
        kwargs[target_name] = signed
    else:
        kwargs.setdefault(target_name, {})[field] = signed[field]
    return kwargs


def run_case(client, case, ctx):
    """执行 yaml 里的一条用例数据，返回响应对象。

    case 的结构（对应 data/extract_cases.yaml）：
        case: 用例名
        request:
          method: POST
          path: /auth/login
          json: {email: ..., password: ...}
          headers: {Authorization: "Bearer ${token}"}
        expect_status: 201
        extract:
          token: $.access_token
        expect:
          $.email: john@mail.com
    """
    # 报告分层：yaml 里写了 feature / story，报告里就能按模块折叠
    if case.get("feature"):
        allure.dynamic.feature(case["feature"])
    if case.get("story"):
        allure.dynamic.story(case["story"])

    req = case["request"]

    # 只把 yaml 里写了的字段传给 requests，没写的不要传 None（会污染请求）
    kwargs = {}
    if req.get("params"):
        kwargs["params"] = ctx.render(req["params"])
    if req.get("json"):
        kwargs["json"] = ctx.render(req["json"])
    if req.get("headers"):
        # headers 走 kwargs 是"一次性"的，只在这一条请求生效，不会污染后面的用例
        kwargs["headers"] = ctx.render(req["headers"])

    # 可选：请求签名（第 8 周）—— 算完把 sign 塞进参数/请求头
    if case.get("sign"):
        kwargs = _apply_sign(kwargs, case["sign"], ctx)

    # path 里的 ${product_id} 由 client 自动渲染（见 client.request）
    resp = client.request(req["method"], req["path"], **kwargs)

    # 断言 1：状态码（支持 [400, 404] 这种"多个都算对"的写法）
    assert_status(resp, case["expect_status"])

    data = resp.json() if resp.text else None

    # 断言 2：先提取变量（给后面的用例用）
    extract(data, case.get("extract"), ctx)

    # 登记清理任务：写在 expect 断言之前是有意的 ——
    # 万一后面的断言失败（抛异常），这条数据也已经被记下来，测试结束时照样会被删掉
    if case.get("cleanup"):
        ctx.add_cleanup(ctx.render(case["cleanup"]))

    # 断言 3：逐个校验响应字段（三种写法见 common/asserter.py 顶部）
    assert_expect(data, case.get("expect"), ctx)

    logger.info("用例执行完成: %s", case["case"])
    return resp
