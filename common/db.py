
"""数据库直连工具：给断言提供"绕过接口、直接看库"的通道。"""
import sqlite3

from config.settings import settings


def _connect():
    """统一建连接 —— 路径只在 settings 里配一次。

    timeout=10：SQLite 同一时刻只允许一个连接写。测试脚本会直连库、mock 服务
    也在写同一个文件，撞上时默认只等 5 秒就抛 "database is locked"；
    给 10 秒让它排队等着，就能稳定跑过。
    """
    return sqlite3.connect(settings.db_path, timeout=10)


def query_one(sql, args=()):
    """查一行。查到返回元组，查不到返回 None。"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        return cur.fetchone()             # TODO 1：查一行用哪个方法？（第 1 课写过）
    finally:
        conn.close()               # 不管中间报不报错，一定关门


def execute(sql, args=()):
    """执行改数据的语句（INSERT/UPDATE/DELETE），自带 commit，返回影响行数。"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        conn.commit()                    # TODO 2：改数据必须落笔，否则又变幽灵数据
        return cur.rowcount
    finally:
        conn.close()
