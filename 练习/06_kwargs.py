def show(**kwargs):
    print(kwargs)
    for key, value in kwargs.items():
        print(f"  {key} = {value}")


show(a=1, b=2)
show()
show(name="张三", age=18)


def wrapper(**kwargs):
    print("收到的:", kwargs)


wrapper(**{"a": 1, "b": 2})