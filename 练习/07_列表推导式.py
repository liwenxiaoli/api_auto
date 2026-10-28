nums = [1, 2, 3, 4, 5]

squ = [n * n for n in nums]
print(squ)

prices = [{"price": 10}, {"price": 20}, {"price": 30}]
only_price = [p["price"] for p in prices]
big = [p["price"] for p in prices if p["price"] > 15]
print(big)
print(only_price)
print(min(only_price))
print(max(only_price))