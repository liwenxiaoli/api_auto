"""12：装饰器原理 —— @pytest.fixture 到底干了什么。"""


def my_decorator(func):
    def wrapper():
        print("--- 前：准备 ---")
        func()
        print("--- 后：收尾 ---")

    return wrapper


@my_decorator
def say_hi():
    print("hi，我是本体")


# 上面那段等价于：say_hi = my_decorator(say_hi)
say_hi()
print("现在 say_hi 的真身:", say_hi.__name__)
