"""15：嵌套字典取值 + get —— resp.json()["category"]["name"] 怎么来的。"""

resp = {
    "id": 1,
    "title": "T-Shirt",
    "category": {"id": 2, "name": "衣服"},
}

print(resp["category"]["name"])          # 一层一层往里走
print(resp.get("price"))                 # 没有这个字段 → None，不报错
print(resp.get("price", 0))              # 没有就用默认值 0
print(resp["category"].get("id", 0))     # 嵌套也能用 get


# 对比：直接取不存在的字段会崩（KeyError）
def demo():
    try:
        print(resp["price"])
    except KeyError as e:
        print("KeyError:", e)


demo()
