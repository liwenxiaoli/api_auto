"""13：元组与解包 —— saucedemo 里 (By.ID, "user-name") 那种写法。"""

point = (3, 5)
x, y = point          # 解包：一次拿两个
print(x, y)


def get_user():
    return "张三", 18     # 看着像返回两个，其实是一个元组


name, age = get_user()
print(name, age)

a, b = 1, 2
a, b = b, a           # 交换，不用临时变量
print(a, b)

locator = ("id", "user-name")
how, value = locator
print("定位方式:", how, "| 定位值:", value)
