"""第 6 周：通用 extract 机制（接口关联 + 占位符）。

注意看这个文件有多"薄"：
    没有 requests 调用、没有 jsonpath、没有一堆 assert ——
    全部交给 common/runner.py 和 data/extract_cases.yaml。

以后要加新场景：在 yaml 里再加一条，这个文件一行都不用改。
"""
import allure
import pytest

from common.runner import run_case
from common.yaml_util import load_yaml

CASES = load_yaml("extract_cases.yaml")


@allure.feature("extract 机制")
class TestExtract:

    @allure.story("登录取 token → 带 token 查资料 → 建商品取 id → 查询 → 删除清理")
    @pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
    def test_extract_demo(self, client, ctx, case):
        run_case(client, case, ctx)
