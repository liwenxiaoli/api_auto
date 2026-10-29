"""登录鉴权用例（数据驱动版）。

这个文件的职责只有一件事：把 yaml 里的数据喂给执行器。

改造前后对比：
    改造前：请求怎么发、断言怎么写，全写在 Python 里 → 加场景要改代码
    改造后：数据写在 data/auth_cases.yaml → 加场景只改 yaml，这个文件一行都不用动

这就是"框架"和"一堆脚本"的区别。
"""
import allure
import pytest

from common.runner import run_case
from common.yaml_util import load_yaml

CASES = load_yaml("auth_cases.yaml")


@allure.feature("登录鉴权")
class TestAuth:

    @pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
    def test_auth(self, client, ctx, case):
        run_case(client, case, ctx)
