"""商品模块用例（数据驱动版）。

改造前这个文件有 100 多行：查询、详情、异常、创建删除闭环，各自写一遍请求和断言。
改造后全部搬进 data/product_cases.yaml，这里只剩 parametrize + 一行 run_case。

用例数量反而变多了（原来 4 条 → 现在 7 条），因为加场景的成本变低了。
"""
import allure
import pytest

from common.runner import run_case
from common.yaml_util import load_yaml

CASES = load_yaml("product_cases.yaml")


@allure.feature("商品模块")
class TestProduct:

    @pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
    def test_product(self, client, ctx, case):
        run_case(client, case, ctx)
