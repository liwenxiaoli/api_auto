from locust import HttpUser, task, between


class ProductUser(HttpUser):
    # 压测靶子：只压本地 mock（waitress）。故意写死，不要换成公网地址
    host = "http://127.0.0.1:5000"

    wait_time = between(0.1, 0.2)

    @task
    def list_products(self):
        self.client.get("/products")
