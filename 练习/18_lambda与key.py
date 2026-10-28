"""18：lambda + key —— max/sorted 怎么按某个字段比大小。"""

items = [
    {"title": "T恤", "price": 55},
    {"title": "卫衣", "price": 10},
    {"title": "外套", "price": 299},
]

prices = [item["price"] for item in items]
print("最贵:", max(prices))
print("最便宜:", min(prices))


# 想要"最贵的那个商品"（整个字典），用 key=
best = max(items, key=lambda x: x["price"])
print("最贵的商品:", best["title"], best["price"])

worst = min(items, key=lambda x: x["price"])
print("最便宜的商品:", worst["title"], worst["price"])

# sorted 同理，返回排好序的新列表
ordered = sorted(items, key=lambda x: x["price"])
print("按价格排序:", [i["title"] for i in ordered])

# lambda 就是"一句话的小函数"，等价于：
def get_price(x):
    return x["price"]


print("用普通函数也一样:", max(items, key=get_price)["title"])
