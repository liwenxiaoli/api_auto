# perf/wal_lab.py
# 目的：亲眼看见 WAL 文件和 checkpoint 到底在干什么
# 只用 Python 标准库；操作的是独立库 lab.db，不碰压测用的 mock/shop.db
import sqlite3
from pathlib import Path

DIR = Path(__file__).resolve().parent
DB = DIR / "lab.db"

# 每次从零开始，保证看到的是"这一次"实验的结果
for f in DIR.glob("lab.db*"):
    f.unlink()


def show(tag):
    """打印主库文件和 WAL 文件此刻各有多大"""
    wal = DIR / "lab.db-wal"
    main = DIR / "lab.db"
    w = wal.stat().st_size if wal.exists() else 0
    m = main.stat().st_size if main.exists() else 0
    print(f"{tag}  ->  主库 {m} 字节 / WAL {w} 字节")


con = sqlite3.connect(DB)

# 旋钮 1：选记账方式。WAL = 走便签路
# 【破坏性实验】把下面的 WAL 改成 DELETE 再跑一遍，会看到 lab.db-wal 根本不生成、
# 主库在写入后直接变大、wal_checkpoint 返回 (0,-1,-1)（不适用）。看完记得改回 WAL。
mode = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
print("journal_mode       =", mode)
# 旋钮 3：便签攒多少页就自动誊一次
print("wal_autocheckpoint =", con.execute("PRAGMA wal_autocheckpoint").fetchone()[0], "页（默认 1000）")
# 旋钮 2：commit 等多严。2=FULL（每单都等），1=NORMAL（不等）
print("synchronous        =", con.execute("PRAGMA synchronous").fetchone()[0], "（2=FULL, 1=NORMAL）")
print("-" * 52)

con.execute("CREATE TABLE t(x TEXT)")
con.commit()
show("① 刚建完表")

# 写 3000 行，让便签变厚
con.executemany("INSERT INTO t VALUES(?)", [("x" * 200,)] * 3000)
con.commit()
show("② 写入 3000 行后")

# 手动触发一次 checkpoint：把 WAL 里的改动搬回主库，并清空便签
r = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
# 三列含义：(是否被阻塞, WAL 里的总帧数, 已 checkpoint 的帧数)
# ⚠️ TRUNCATE 会把 WAL 文件整个清空，所以后两列常返回 0 —— 这不代表"没搬"。
#    搬没搬要看 ③ 的文件大小：主库变大 + WAL 归零才是硬证据。
print("checkpoint 返回    =", r, " (busy, WAL总帧数, 已搬帧数)")
show("③ checkpoint 之后")

con.close()
