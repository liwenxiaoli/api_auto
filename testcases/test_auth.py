"""登录鉴权用例。

演示两件事：
1. 数据驱动：用例数据写在 data/auth_cases.yaml，加场景只改 yaml
2. 同一个函数覆盖成功与失败：靠数据里的字段决定走哪套断言
"""
import allure
import pytest

from common.yaml_util import load_yaml

CASES = load_yaml("auth_cases.yaml")


@allure.feature("登录鉴权")
class TestAuth:

    @allure.story("不同账号密码的登录结果")
    @pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
    def test_login(self, client, case):
        # 发请求：path 只写 "/auth/login"，base_url 由 HttpClient 自动拼
        resp = client.post("/auth/login", json=case["body"])

        # 断言 1：状态码。断言消息里带上真实响应，失败时一眼能看出问题
        assert resp.status_code == case["expect_status"], f"实际响应: {resp.text}"

        data = resp.json()

        # 断言 2：成功场景要拿到 token，而且不能是空字符串
        if case.get("expect_token"):
            assert data.get("access_token"), "登录成功却没有返回 token"

        # 断言 3：失败场景要给出明确的错误信息
        if case.get("expect_message"):
            assert data.get("message") == case["expect_message"], f"实际提示: {data}"

    @allure.story("用 token 访问需要登录的接口")
    def test_profile_with_token(self, auth_client):
        resp = auth_client.get("/auth/profile")

        assert resp.status_code == 200, f"实际响应: {resp.text}"
        # 断言返回的是"我"的信息，而不是随便一个人的
        assert resp.json()["email"] == "john@mail.com"
        assert "id" in resp.json()

    @allure.story("不带 token 访问受保护接口")
    def test_profile_without_token(self, client):
        """反向用例：没登录就该被拦住。这条比正向用例更有价值 —— 权限校验漏了是真事故。"""
        resp = client.get("/auth/profile")

        assert resp.status_code == 401, f"没登录却访问成功了，权限校验有问题: {resp.text}"


