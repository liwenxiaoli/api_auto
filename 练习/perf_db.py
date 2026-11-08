"""微基准：把 list_products 里"建连接"和"查询"拆开计时"""
import sqlite3
import time
from pathlib import Path

# 和 mock/app.py 指向同一个库文件
DB = str(Path(__file__).resolve().parent.parent / "mock" / "shop.db")

N = 1000   # 每个实验跑 1000 次

# 实验一：只建连接、立刻关闭
start = time.perf_counter()
for _ in range(N):
    conn = sqlite3.connect(DB, timeout=10)
    conn.close()
connect_cost = time.perf_counter() - start

# 实验二：建连接 + 查询 + 关闭（就是 list_products 干的活）
start = time.perf_counter()
for _ in range(N):
    conn = sqlite3.connect(DB, timeout=10)
    # TODO 1：在这里写查询，结果存到 rows
    #         提示：conn.execute("SELECT id, name, price, stock FROM products").fetchall()
    rows=conn.execute("SELECT id, name, price, stock FROM products").fetchall()

    conn.close()
full_cost = time.perf_counter() - start
query_cost = full_cost - connect_cost

# TODO 2：算出"查询本身"花了多少（两次的差），存到变量 query_cost

print(f"只建连接     总 {connect_cost * 1000:8.1f} ms   单次 {connect_cost / N * 1000:.3f} ms")
print(f"建连接+查询  总 {full_cost * 1000:8.1f} ms   单次 {full_cost / N * 1000:.3f} ms")
print(f"查询本身     单次 {query_cost / N * 1000:.3f} ms")
