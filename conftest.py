"""pytest 全局 fixture：管理 HTTP 客户端和登录 token。

这个文件是接口自动化的"枢纽"，重点看三个东西：
    1. pytest_addoption / pytest_configure —— 注册 --env 参数并切换环境
    2. fixture 的作用域（scope）
    3. 收尾清理（autouse + yield）
"""
import pytest

from common.client import HttpClient
from common.context import Context
from common.logger import logger
from config.settings import settings   # settings 是 Config 对象（不是模块名，别写成 from config import settings）


def pytest_addoption(parser):
    """注册自定义命令行参数。写在这里，pytest 启动时才认识 --env。"""
    parser.addoption(
        "--env",
        action="store",
        default=settings.env,          # 不传就用 config.yaml 里的 default_env
        help=f"运行环境，可选：{settings.available_envs}",
    )


def pytest_configure(config):
    """所有用例跑之前的钩子：在这里把配置切到指定环境。

    为什么放这里？
        它在任何 fixture 之前执行，保证 client 创建时读到的已经是新环境的地址。
    """
    env = config.getoption("--env")
    try:
        settings.configure(env)
    except KeyError as e:
        # UsageError 会让 pytest 输出友好的提示并退出，而不是抛一堆红字堆栈
        raise pytest.UsageError(str(e))


def pytest_report_header(config):
    """在 pytest 输出的最开头加一行 —— 一眼看清这轮跑的是哪个环境。"""
    return (f"运行环境: {settings.env} | "
            f"base_url: {settings.base_url} | "
            f"timeout: {settings.timeout}")


@pytest.fixture(scope="session")
def ctx():
    """变量池：整个测试过程共用一份。

    为什么必须是 session 级？
        变量池的价值就是"上一条用例存进去、下一条用例取出来"。
        如果每条用例都新建一个空池子，谁也取不到别人存的值，extract 就白做了。
    """
    return Context()


@pytest.fixture(scope="session", autouse=True)
def init_context(ctx, token):
    """把登录 token 提前放进变量池，yaml 里就能直接写 ${token}。

    autouse=True：不用在用例里写它的名字，自动生效。
    有了它，yaml 用例就不用先登录一次才能拿到 token 了 ——
    "登录拿 token" 这种公共前置，交给框架做，用例只管自己的业务。
    """
    ctx.set("token", token)
    return ctx


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(client, ctx):
    """收尾清理：所有用例跑完后，删掉本轮创建的数据。

    autouse=True 表示不用在用例里写名字，自动生效。

    为什么需要它？
        yaml 里的用例是"顺序依赖"的：创建 → 查询 → 删除。
        如果中间某条失败导致后面的"删除"没跑到，商品就残留在测试站了。
        有了这个兜底，不管中间发生什么，结束时都会清干净。
    """
    yield

    if not ctx.pending_cleanups:
        return
    for item in ctx.pending_cleanups:
        resp = client.request(
            item["method"], item["path"], headers=item.get("headers") or {}
        )
        logger.info("清理测试数据 %s %s -> %s", item["method"], item["path"], resp.status_code)


@pytest.fixture(scope="session")
def client(ctx):
    """整个测试过程共用一个 HTTP 客户端。

    scope="session" 表示：所有用例加起来只创建一次，而不是每条用例都新建。
    好处：Session 复用了 TCP 连接和 Cookie，跑得更快，也更接近真实用户行为。
    """
    logger.info("=== 测试开始，环境 = %s，base_url = %s ===", settings.env, settings.base_url)
    http = HttpClient(settings.base_url, settings.timeout)
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
    resp = client.post("/auth/login", json={
        "email": settings.user["email"],
        "password": settings.user["password"],
    })
    assert resp.status_code == 201, f"登录失败，状态码 {resp.status_code}，响应 {resp.text}"
    access_token = resp.json()["access_token"]
    logger.info("登录成功，拿到 token: %s...", access_token[:20])
    return access_token


@pytest.fixture
def auth_client(client, token):
    """带登录态的客户端：请求头里自动带上 Authorization。

    注意这里是 function 级 —— 每条用例用完都把 header 摘掉，
    保证下一条用例是干净的（否则"不需要登录"的用例也会被带上 token，测不准）。

    【现状】用例全部改成 yaml 驱动后，这个 fixture 暂时没人用了 ——
    因为 yaml 里写 `headers: {Authorization: "Bearer ${token}"}` 是一次性的，
    天然不会污染别的用例，比它更省事。保留在这里是为了演示"用完记得摘掉"这个坑
    （把下面 remove_header 注释掉，再跑"不带 token"的用例就会变绿不起来）。
    """
    client.set_header("Authorization", f"Bearer {token}")
    yield client
    client.remove_header("Authorization")
