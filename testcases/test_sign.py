"""签名工具的单元测试（不联网，纯 Python 逻辑）。

为什么给工具函数单独写测试？
    签名算错了，接口会全量 401，几十条用例一起红 —— 根本看不出是签名的问题。
    把签名逻辑单独测明白，接口用例失败时就只需怀疑"参数/环境"，排查范围小一大半。

跑：pytest testcases/test_sign.py -v
"""
import pytest

from common.sign import add_sign, build_sign_str, md5, md5_sign

SECRET = "my_secret"


def test_基本签名结果固定():
    """同样的输入必须永远得到同样的输出 —— 这是签名能用的前提。"""
    assert md5_sign({"a": 1, "b": 2}, SECRET) == "65b2b9d691d331991f8d989a7eb1026b"


def test_参数顺序不影响结果():
    """字典顺序不同，签名必须一样 —— 靠 build_sign_str 里的 sorted 保证。"""
    assert md5_sign({"a": 1, "b": 2}, SECRET) == md5_sign({"b": 2, "a": 1}, SECRET)


def test_空值和sign字段不参与签名():
    """None / 空串 / sign 本身都要被跳过。"""
    skip_empty = md5_sign({"a": 1, "b": None, "c": "", "sign": "旧签名"}, SECRET)
    only_a = md5_sign({"a": 1}, SECRET)
    assert skip_empty == only_a == "c62176dc58c560525d789a66f8d44abd"


def test_中文参数也能签():
    """md5 只认字节，所以必须 encode('utf-8') —— 这一条就是验证它没被写漏。"""
    assert md5_sign({"name": "张三"}, SECRET) == "c816b3aca9f1d9472bf769dd21e03fbb"


def test_密钥为空必须报错():
    """密钥为空却还能算出签名，是最危险的 bug —— 等于没签名。"""
    with pytest.raises(ValueError) as e:
        md5_sign({"a": 1}, "")
    assert "不能为空" in str(e.value)


def test_add_sign_不修改原字典():
    """加签名要返回新字典，避免"签了一遍又签一遍"。"""
    params = {"a": 1}
    signed = add_sign(params, SECRET)

    assert signed["sign"] == "c62176dc58c560525d789a66f8d44abd"
    assert "sign" not in params, "原字典被改了，重复签名时会出错"


def test_原始串的拼接规则():
    """把拼接结果直接断言出来：签名对不上时，第一步就是比这个串。"""
    assert build_sign_str({"b": 2, "a": 1}, SECRET) == "a=1&b=2&key=my_secret"
    assert md5("abc") == "900150983cd24fb0d6963f7d28e17f72"   # md5 的标准值，验证函数没写错
