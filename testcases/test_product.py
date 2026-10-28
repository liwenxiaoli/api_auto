"""商品模块用例。

分两类：
    查询类：不需要登录，用 client
    管理类：需要登录，用 auth_client（请求头自动带 token）
"""
import allure
import pytest

from common.json_util import json_get
from common.yaml_util import load_yaml

CASES = load_yaml("product_cases.yaml")

# 新建商品的数据（独立于 yaml 是故意的：这条用例要拿 id 做后续操作，写在代码里更好读）
NEW_PRODUCT = {
    "title": "自动化练习商品",
    "price": 99,
    "description": "由接口自动化用例创建，跑完自动删除",
    "categoryId": 1,
    "images": ["https://placeimg.com/640/480/any"],
}


@allure.feature("商品查询")
class TestProductQuery:

    @allure.story("列表查询：分页与关键字")
    @pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
    def test_query(self, client, case):
        resp = client.get("/products", params=case["params"])

        assert resp.status_code == case["expect_status"], f"实际响应: {resp.text}"
        data = resp.json()

        # 断言：返回条数符合预期
        if "expect_count" in case:
            assert len(data) == case["expect_count"], f"实际返回 {len(data)} 条"

        # 断言：每条结果的标题都包含关键字
        if "expect_contain" in case:
            assert len(data) > 0, "查到了 0 条，断言没意义"
            for item in data:
                assert case["expect_contain"] in item["title"], f"不符合的结果: {item['title']}"

    @allure.story("查询商品详情")
    def test_detail(self, client):
        """详情用例不写死 id —— 公共测试站的数据随时可能被别人删掉。

        正确做法：先从列表里取一个真实存在的 id，再拿它去查详情。
        这也是第 6 周 extract 想法的雏形：用前一条响应的值，驱动下一条请求。
        """
        list_resp = client.get("/products", params={"limit": 1})
        assert list_resp.status_code == 200, f"列表查询失败: {list_resp.text}"
        first_id = json_get(list_resp.json(), "$[0].id")
        assert first_id, "列表返回为空，没法测详情"

        resp = client.get(f"/products/{first_id}")

        assert resp.status_code == 200, f"实际响应: {resp.text}"
        assert json_get(resp.json(), "id") == first_id
        # 用 jsonpath 取嵌套字段：分类名在 data["category"]["name"]
        assert json_get(resp.json(), "category.name"), "分类信息不应为空"

    @allure.story("查询不存在的商品")
    def test_query_not_exist(self, client):
        """异常场景：查一个不存在的 id，应当报错而不是返回空数据。"""
        resp = client.get("/products/999999999")

        # 注意：这个站返回 400（EntityNotFoundError），换成 404 更合理
        assert resp.status_code in (400, 404), f"实际状态码 {resp.status_code}，响应 {resp.text}"


@allure.feature("商品管理（需登录）")
class TestProductManage:

    @allure.story("创建 → 查询 → 删除 的完整闭环")
    def test_create_and_delete(self, auth_client):
        """接口自动化的核心习惯：自己造的数据，自己清掉。

        否则跑几次之后，测试环境里全是垃圾数据，
        不仅污染别人的用例，还可能让"查询列表"这类断言莫名其妙失败。
        """
        product_id = None
        try:
            with allure.step("创建商品"):
                resp = auth_client.post("/products/", json=NEW_PRODUCT)
                assert resp.status_code == 201, f"创建失败: {resp.text}"
                product_id = json_get(resp.json(), "id")
                assert product_id, "创建成功却没返回 id"

                # 断言：创建出来的字段和提交的一致
                assert json_get(resp.json(), "title") == NEW_PRODUCT["title"]
                assert json_get(resp.json(), "price") == NEW_PRODUCT["price"]

            with allure.step("查询刚创建的商品，确认真的写进去了"):
                resp = auth_client.get(f"/products/{product_id}")
                assert resp.status_code == 200
                assert json_get(resp.json(), "title") == NEW_PRODUCT["title"]

        finally:
            # finally 里的代码不管成功失败都会执行 —— 保证一定清理
            with allure.step("删除商品，清理测试数据"):
                if product_id:
                    resp = auth_client.delete(f"/products/{product_id}")
                    assert resp.status_code == 200, f"清理失败: {resp.text}"
