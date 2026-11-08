"""POST /products 压测脚本：测写操作（INSERT + commit）

与 locustfile.py（只读）分开：一个文件只放一类任务，
否则测出来的是"读写混合"，既不能和 GET 对比，也说不清是谁的瓶颈。
"""
import random

from locust import HttpUser, task, between


class ProductWriter(HttpUser):
    # 压测靶子：只压本地 mock（waitress）。故意写死，不要换成公网地址
    host = "http://127.0.0.1:5000"
    # 基准协议：每次请求后歇 0.1~0.2 秒（均值 0.15），与 GET 的 locustfile 对齐
    # 加压实验时改成 between(0, 0.1)：用户不停手 = 加压，但连接数不变
    # （500 用户 ≈ 500 条 keep-alive 连接，再加用户会撞 Windows select 512 上限）
    wait_time = between(0.1, 0.2)

    @task
    def create_product(self):
        # name 带随机数：每次都不一样，压完可以直接在库里数出这一轮写了多少条
        payload = {
            "name": f"perf-{random.randint(1, 10**9)}",
            "price": random.randint(1, 100),
        }

        # catch_response=True = 我自己判断成功还是失败，不让 Locust 按默认规则算
        with self.client.post("/products", json=payload, catch_response=True) as resp:
            # 只有 201 才算成功。默认规则是"2xx 全算成功"，
            # 万一接口退化成返回 200，不写这段你完全看不出来
            if resp.status_code != 201:
                resp.failure(f"期望 201，实际 {resp.status_code}，响应 {resp.text[:100]}")
