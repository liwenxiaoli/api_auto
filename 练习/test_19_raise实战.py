"""19：raise + pytest.raises 的真实用法
场景：自己写的工具函数，参数不合法就 raise；用例里用 pytest.raises 验证它确实拦住了。
"""
import pytest


# ========== 被测试的工具函数（真实项目里会放在 common/ 目录）==========

def build_login_payload(username, password):
    """造登录请求体：参数不合法直接掐断，不让它污染后面的请求。"""
    if not username:
        raise ValueError("用户名不能为空")
    if not password:
        raise ValueError("密码不能为空")
    return {"username": username, "password": password}


def get_field(resp_json, key):
    """从接口返回里取字段：取不到就报错，并把实际有哪些字段打印出来方便排查。"""
    if key not in resp_json:
        raise KeyError(f"返回里没有 {key} 字段，实际字段是：{list(resp_json.keys())}")
    return resp_json[key]


# ========== 用例 ==========

def test_参数正常时能造出请求体():
    assert build_login_payload("tom", "123456") == {
        "username": "tom",
        "password": "123456",
    }


def test_用户名为空应该报错():
    with pytest.raises(ValueError) as e:
        build_login_payload("", "123456")
    assert "用户名不能为空" in str(e.value)


def test_密码为空应该报错():
    with pytest.raises(ValueError) as e:
        build_login_payload("tom", "")
    assert "密码不能为空" in str(e.value)


def test_字段存在时取得到():
    resp_json = {"code": 200, "data": {"id": 1}}
    assert get_field(resp_json, "code") == 200


def test_字段不存在应该报KeyError():
    resp_json = {"code": 200, "data": {"id": 1}}
    with pytest.raises(KeyError) as e:
        get_field(resp_json, "token")
    assert "token" in str(e.value)
