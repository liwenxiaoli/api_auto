
import pytest

from common.runner import run_case
from common.yaml_util import load_cases


CASES = load_cases("practice.yaml")


@pytest.mark.parametrize("case", CASES)     # ② 一条一条喂进去
def test_practice(client, ctx, case):       # ③ 三个参数，前两个是"写了名字就有"
    run_case(client, case, ctx)             # ④ 干活的全在它里面