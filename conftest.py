"""pytest 全局 fixture：管理 HTTP 客户端和登录 token。

这个文件是接口自动化的"枢纽"，重点看两个 fixture 的作用域（scope）。
"""
import pytest

from common.client import HttpClient
from common.context import Context
from common.logger import logger
from config.settings import BASE_URL, TIMEOUT, USER


@pytest.fixture(scope="session")
def ctx():
    """变量池：整个测试过程共用一份。

    为什么必须是 session 级？
        变量池的价值就是"上一条用例存进去、下一条用例取出来"。
        如果每条用例都新建一个空池子，谁也取不到别人存的值，extract 就白做了。
    """
    return Context()


@pytest.fixture(scope="session")
def client(ctx):
    """整个测试过程共用一个 HTTP 客户端。

    scope="session" 表示：所有用例加起来只创建一次，而不是每条用例都新建。
    好处：Session 复用了 TCP 连接和 Cookie，跑得更快，也更接近真实用户行为。
    """
    logger.info("=== 测试开始，base_url = %s ===", BASE_URL)
    http = HttpClient(BASE_URL, TIMEOUT)
    http.attach_context(ctx)      # 挂上变量池，请求里的 ${xxx} 才会被替换
    yield http
    http.close()
    logger.info("=== 测试结束 ===")


@pytest.fixture(scope="session")
def token(client):
    """登录一次，拿到 token 给所有用例复用 —— 这就是"接口关联"最简单实用的形态。

    关键点：
    1. scope="session"：只登录一次。如果每条用例都登录一遍，慢且容易被限流
    2. 登录失败要在 fixture 里直接报错，否则后面所有用例都会以奇怪的方式失败
    """
    resp = client.post("/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert resp.status_code == 201, f"登录失败，状态码 {resp.status_code}，响应 {resp.text}"
    access_token = resp.json()["access_token"]
    logger.info("登录成功，拿到 token: %s...", access_token[:20])
    return access_token


@pytest.fixture
def auth_client(client, token):
    """带登录态的客户端：请求头里自动带上 Authorization。

    注意这里是 function 级 —— 每条用例用完都把 header 摘掉，
    保证下一条用例是干净的（否则"不需要登录"的用例也会被带上 token，测不准）。
    """
    client.set_header("Authorization", f"Bearer {token}")
    yield client
    client.remove_header("Authorization")
