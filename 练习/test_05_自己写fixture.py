import pytest


@pytest.fixture
def numbers():
    print("\n[准备] 造一组数字")
    return [1, 2, 3]


def test_求和(numbers):
    assert sum(numbers) == 6


def test_个数(numbers):
    assert len(numbers) == 3

@pytest.fixture
def cart():
    items = []
    print("\n[开场] 空购物车")
    yield items
    items.clear()
    print("[收尾] 清空购物车")


def test_加购(cart):
    cart.append("手机")
    print(f"购物车: {cart}")
    assert len(cart) == 1


def test_再加一件(cart):
    cart.append("耳机")
    print(f"购物车: {cart}")
    assert len(cart) == 1        # 如果被污染，这里是 2