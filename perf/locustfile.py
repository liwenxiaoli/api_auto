from locust import HttpUser, task, between


class ProductUser(HttpUser):
    wait_time = between(0.1, 0.2)

    @task
    def list_products(self):
        self.client.get("/products")
