"""本地 mock 服务：给接口自动化提供"能碰数据库"的被测对象。

为什么要有它？
    escuelajs 的数据库在人家服务器上，我们碰不到，只能做接口断言。
    自己搭一个，就同时有了两条通道：HTTP 调接口 + sqlite3 直连查库。

启动：python mock/app.py
"""
from pathlib import Path
import sqlite3
from waitress import serve
from flask import Flask, jsonify, request

app = Flask(__name__)

# 用绝对路径：不管从哪个目录启动，库文件都固定在本文件旁边
# （写相对路径 "shop.db" 会建在"当前工作目录"，换目录跑就找不到 —— 今天踩过的坑）
DB = str(Path(__file__).resolve().parent / "shop.db")


def get_conn():
    """每次请求新建一条连接，用完就关。简单、不会互相干扰。"""
    # timeout=10：测试脚本会同时直连同一个库文件，撞上时排队等，别直接抛锁错误
    return sqlite3.connect(DB, timeout=10)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id    INTEGER PRIMARY KEY,
            name  TEXT,
            price REAL,
            stock INTEGER
        )
    """)
    conn.commit()
    conn.close()


@app.route("/auth/login", methods=["POST"])
def login():
    """框架 conftest 的 token fixture 会调它。返回假 token 即可，不校验账号。"""
    return jsonify({"access_token": "mock-token-for-test"}), 201


@app.route("/products", methods=["GET"])
def list_products():
    conn = get_conn()
    rows = conn.execute("SELECT id, name, price, stock FROM products").fetchall()
    conn.close()
    products = [{"id": r[0], "name": r[1], "price": r[2], "stock": r[3]} for r in rows]
    return jsonify(products), 200


@app.route("/products", methods=["POST"])
def create_product():
    data = request.get_json()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (name, price, stock) VALUES (?,?,?)",
        (data["name"], data["price"], data.get("stock", 0)),
    )
    conn.commit()                 # 落笔！不写就变"幽灵商品"
    new_id = cur.lastrowid
    conn.close()
    return jsonify({
        "id": new_id,
        "name": data["name"],
        "price": data["price"],
        "stock": data.get("stock", 0),
    }), 201


@app.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (pid,))   # WHERE 不能漏
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": pid}), 200


@app.route("/reset", methods=["POST"])
def reset():
    """测试专用：清空表，保证用例从干净状态开始。"""
    conn = get_conn()
    conn.execute("DELETE FROM products")
    conn.commit()
    conn.close()
    return jsonify({"reset": True}), 200


if __name__ == "__main__":
    init_db()
    serve(app, host="127.0.0.1", port=5000, threads=32, connection_limit=1000)
