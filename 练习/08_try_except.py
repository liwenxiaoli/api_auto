def demo1():
    try:
        result = 10 / 0
        print("这行永远不会执行")
    except ZeroDivisionError as e:
        print("抓到了:", e)
    finally:
        print("无论如何都会执行")


def demo2():
    data = {"a": 1}
    try:
        print(data["b"])
    except KeyError as e:
        print("字段不存在:", e)


demo1()
print("---")
demo2()
