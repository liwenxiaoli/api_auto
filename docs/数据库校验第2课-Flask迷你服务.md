# 数据库校验 · 第 2 课：Flask 迷你接口服务

> 代码都在 `C:\Users\A\PycharmProjects\db_practice`（沙盒）
> 环境：db_practice 的 `.venv`，已装 flask 3.1.3

---

## 一、为什么要有这一课

数据库校验的完整闭环是：

```
接口说"我创建成功了"  →  去数据库里看一眼，到底有没有这条
```

第 1 课你会了"看库"，但**没有能写库的接口** —— escuelajs 是别人的站，你摸不到它的数据库。

所以自己搭一个：Flask 30 行服务 + SQLite，POST 创建商品写进库，GET 查列表从库里读。

学完这个，第 3 课就能做真正的闭环：**POST 创建 → 查库有记录 → DELETE → 查库没记录**。

---

## 二、Flask 是什么

一句话：**把 Python 函数变成网址。**

```python
@app.route("/products", methods=["POST"])
def create_product():
    ...
```

写完这个，访问 `POST http://127.0.0.1:5000/products` 就会执行 `create_product()` 这个函数。

`@app.route(...)` 是**装饰器** —— 跟你用过的 `@pytest.mark.parametrize` 完全同一类东西：不改函数内部，给它加个功能（这里的功能是"绑定到一个网址上"）。

---

## 三、完整代码（`app.py`，约 40 行）

```python
from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
DB = "shop.db"


def init_db():
    """启动时建表（已存在就跳过）。"""
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS products "
                 "(id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER)")
    conn.commit()
    conn.close()


@app.route("/products", methods=["GET"])
def list_products():
    """查所有商品。"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock FROM products")
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "price": r[2], "stock": r[3]} for r in rows])


@app.route("/products", methods=["POST"])
def create_product():
    """创建商品：写进数据库，返回 201。"""
    data = request.get_json()                       # 拿请求体（JSON → 字典）
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                (data["name"], data["price"], data.get("stock", 0)))
    conn.commit()                                   # 落笔！不写这行数据进不了库
    new_id = cur.lastrowid                          # 拿到刚插入那行的 id
    conn.close()
    return jsonify({"id": new_id, "name": data["name"],
                    "price": data["price"], "stock": data.get("stock", 0)}), 201


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)
```

---

## 四、逐块拆解

| 代码 | 干什么 | 对应你熟悉的东西 |
|---|---|---|
| `app = Flask(__name__)` | 造一个服务对象 | 类似 `Context()` 造对象 |
| `@app.route(路径, methods=[...])` | 把网址绑到函数上 | 类似 `@pytest.mark.parametrize` |
| `request.get_json()` | 拿请求体，转成字典 | 类似 `resp.json()` |
| `jsonify(字典)` | 把字典转成 JSON 响应 | 服务端版的 "返回 JSON" |
| `return jsonify(...), 201` | 返回内容 **+ 状态码** | 状态码就是 `expect_status` 验的那个 |
| `cur.lastrowid` | 刚插入那行的 id | 后面接口关联要用 |
| `sqlite3.connect(DB)` 每个请求一次 | 用完了就 `close()` | 简单，不用管并发 |
| `app.run(port=5000)` | 起服务，占 5000 端口 | 服务一直跑着，等你来调 |

**注意：两个函数路径都是 `/products`，靠 `methods` 区分** —— GET 走上面那个，POST 走下面那个。

---

## 五、怎么跑

**1. 启动服务**（Terminal 里，或 PyCharm 右键 Run）：

```bash
python app.py
```

看到 `Running on http://127.0.0.1:5000` 就成了。**这个窗口别关**，它就是你的服务器。

**2. 用浏览器验证 GET**：

打开 `http://127.0.0.1:5000/products` → 看到 `[]`（现在是空的）。

**3. 用 requests 脚本调 POST**（新建 `call_api.py`）：

```python
import requests

BASE = "http://127.0.0.1:5000"

r = requests.post(BASE + "/products", json={"name": "测试商品", "price": 9.9, "stock": 5})
print("创建:", r.status_code, r.json())

r2 = requests.get(BASE + "/products")
print("列表:", r2.status_code, r2.json())
```

应该看到 `201` + 一条数据，然后 `200` + 列表里有一条。

---

## 六、自测题（闭卷答，答对 4 题以上算过）

1. `@app.route("/products", methods=["POST"])` 这行在干什么？`@` 是什么东西？
2. POST 那个函数里为什么要 `conn.commit()`？不写会怎样（接口会报什么错）？
3. `request.get_json()` 拿到的是什么？`jsonify(...)` 又是在干什么？
4. `return jsonify(...), 201` 里的 `201` 是什么？不写默认返回多少？
5. 两个函数路径都是 `/products`，Flask 怎么知道该走哪个？

<details>
<summary>点开看答案</summary>

1. 把这个函数绑定到"POST /products"这个网址上。`@` 是**装饰器**（和 `@pytest.mark.parametrize` 一类），给函数加功能，不改函数内部。
2. INSERT 是改数据，不 commit 就只在草稿上，程序结束就丢。**接口不会报错**，照样返回 201 —— 但库里其实没有这条，这就是最阴的 bug。
3. `request.get_json()` = 拿客户端发来的请求体，转成字典（对应你熟悉的 `resp.json()`，只是方向相反）。`jsonify(字典)` = 把字典转成 JSON 作为响应返回。
4. HTTP 状态码，201 = 创建成功。不写默认 **200**。
5. 靠 `methods` 区分：GET 请求走 `list_products`，POST 请求走 `create_product`。

</details>

---

## 七、动手练习

### 练习 1：跑通并加断言（必做）

在 `call_api.py` 里把打印改成**断言**：

```python
r = requests.post(BASE + "/products", json={"name": "练习商品", "price": 19.9, "stock": 3})
assert r.status_code == 201, f"创建应该返回 201，实际 {r.status_code}"
pid = r.json()["id"]

r2 = requests.get(BASE + "/products")
names = [p["name"] for p in r2.json()]
assert "练习商品" in names, f"列表里应该有练习商品，实际是 {names}"
```

### 练习 2：破坏实验（必做，最有价值）

把 `create_product()` 里的 `conn.commit()` **注释掉**，重启服务，再跑 `call_api.py`：

- POST 依然返回 **201**（接口说自己成功了）
- 但 GET 列表里**没有这条**（库里其实没写进去）

**这就是"接口断言过不了的事，数据库断言能抓到"** —— 整个第 2、3 课存在的理由。看完把 commit 改回来。

### 练习 3（加分）：加一个删除接口

```python
@app.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": pid}), 200
```

`<int:pid>` 是路径参数：访问 `DELETE /products/3`，`pid` 就等于 3。
然后用 requests 删一条，再 GET 验证它没了。

---

## 八、坑表

| 现象 | 原因 |
|---|---|
| 端口被占用 `Address already in use` | 上一次的服务没关，或者换了 `app.run(port=5001)` |
| 改了代码没生效 | 服务要**重启**（debug=True 会自动重启，但不是每次都能捕捉到） |
| `jsonify` 报 TypeError | 传了不能转成 JSON 的东西（比如元组、数据库行对象），先转成字典 |
| POST 返回 500 | 请求体没写 `json=`，或字段名拼错（`data["name"]` KeyError） |

---

## 九、下一课预告

第 3 课：把数据库校验接进 api_auto 框架 —— 新建 `common/db.py`，conftest 加 fixture，
用例闭环：POST 创建 → 查库有记录 → DELETE → 查库没记录。
