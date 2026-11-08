"""切换 SQLite 的日志模式，用于 A/B 压测对照

用法：
    python 练习/journal_mode.py           # 查看当前模式
    python 练习/journal_mode.py WAL       # 切成 WAL（读不加文件锁）
    python 练习/journal_mode.py DELETE    # 切回默认（rollback journal）

注意：切换前必须先停掉 mock 服务，否则会 database is locked。
"""
import sqlite3
import sys
from pathlib import Path

DB = str(Path(__file__).resolve().parent.parent / "mock" / "shop.db")

conn = sqlite3.connect(DB, timeout=10)
try:
    if len(sys.argv) > 1:
        mode = sys.argv[1].upper()
        result = conn.execute(f"PRAGMA journal_mode={mode}").fetchone()[0]
        print(f"切换结果: {result}")
    print(f"当前模式: {conn.execute('PRAGMA journal_mode').fetchone()[0]}")
finally:
    conn.close()
