


def test_查询商品列表(client):
    resp=client.get("/products",params={"limit":3,"offset":0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["title"]


def test_价格都是正数(client):
    resp=client.get("/products",params={"limit":5,"offset":0})
    assert resp.status_code == 200, f"实际状态码 {resp.status_code}"

    data = resp.json()
    for item in data:
            assert item["price"] > 0,f"价格异常:{item["title"]}={item["price"]}"


def test_价格区间过滤(client):
    # 只传 price_min 时，后端会忽略这个参数（接口缺陷）
    resp = client.get("/products", params={"price_min": 100})
    assert resp.status_code == 200
    prices = [item["price"] for item in resp.json()]
    assert min(prices) < 100, "说明 price_min 没生效，这是接口缺陷"

    # price_min 和 price_max 一起传才生效
    resp = client.get("/products", params={"price_min": 100, "price_max": 1000})
    assert resp.status_code == 200
    prices = [item["price"] for item in resp.json()]
    assert prices, "查到 0 条，断言没意义"
    for price in prices:
        assert 100 <= price <= 1000, f"超出区间的价格: {price}"

def test_假token访问会被拒绝(client):
    client.set_header("Authorization", "Bearer token")
    resp = client.get("/auth/profile")
    assert resp.status_code == 401
    client.remove_header("Authorization")
