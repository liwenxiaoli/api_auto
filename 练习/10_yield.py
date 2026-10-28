def make_numbers():
    print("[1] 开始准备")
    yield 1
    print("[2] 交出第 1 个，回来继续")
    yield 2
    print("[3] 交出第 2 个，收工")


for n in make_numbers():
    print(f"    拿到: {n}")
