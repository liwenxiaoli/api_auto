"""HTTP 请求封装。

核心目的：所有请求都从这一个口子出去，便于统一处理：
    1. 自动拼接 base_url（用例里只写 /products，不写完整地址）
    2. 统一设超时（不设超时 = 接口挂了用例永远卡住，这是新手最常犯的错）
    3. 自动记日志（失败后有据可查）
    4. 复用 Session（同一个 Session 会自动保持 Cookie，并复用 TCP 连接，更快）
"""
import requests

from common.logger import logger


class HttpClient:
    def __init__(self, base_url, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Session 会自动保存服务端返回的 Cookie，并在后续请求带上
        self.session = requests.Session()

    def request(self, method, path, **kwargs):
        """统一的请求入口，get/post/put/delete 最终都调它。"""
        url = path if path.startswith("http") else f"{self.base_url}{path}"

        logger.info("请求: %s %s", method.upper(), url)
        if kwargs.get("json"):
            logger.info("请求体: %s", kwargs["json"])

        # timeout 是强制的 —— 没有它，requests 会无限等待
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)

        logger.info("响应: %s | 耗时 %.2fs", resp.status_code, resp.elapsed.total_seconds())
        logger.debug("响应体: %s", resp.text[:500])
        return resp

    def get(self, path, params=None, **kwargs):
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def set_header(self, key, value):
        """给之后所有请求加一个请求头（比如带上 token）。"""
        self.session.headers[key] = value

    def remove_header(self, key):
        self.session.headers.pop(key, None)

    def close(self):
        self.session.close()
