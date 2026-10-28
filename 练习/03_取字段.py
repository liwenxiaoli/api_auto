data = [
    {"title": "T-Shirt", "price": 55},
    {"title": "Hoodie", "price": 10},
]


def first_title(items):
    return items[0]["title"]


def total_price(items):
    total = 0
    for item in items:
        total = total + item["price"]
    return total

def zuiguins(items):
    best=items[0]
    for item in items:
        if item["price"] > best["price"]:  # 发现更贵的
            best = item  # 就换成它
        return best["title"]  # 最后手上剩下的就是最贵


def test_总价正确():
    assert total_price(data) == 65


def test_第一条标题():
    assert first_title(data) == "T-Shirt"




print(first_title(data))
print(total_price(data))
print(zuiguins(data))
