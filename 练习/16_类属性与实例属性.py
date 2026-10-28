"""16：类属性 vs 实例属性 —— LoginPage.USERNAME 那种写法。"""


class LoginPage:
    USERNAME = ("id", "user-name")     # 类属性：写在类里，所有对象共享一份

    def __init__(self, name):
        self.name = name               # 实例属性：每个对象各一份


a = LoginPage("页面A")
b = LoginPage("页面B")

print(a.USERNAME, b.USERNAME)      # 都一样，共享
print(a.name, b.name)              # 各自不同

LoginPage.USERNAME = ("id", "changed")   # 改类属性，所有对象跟着变
print(a.USERNAME, b.USERNAME)

a.name = "改名了"                    # 改实例属性，只影响这一个
print(a.name, b.name)
