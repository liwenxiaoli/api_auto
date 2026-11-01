# 数据库校验 · 第 1 课：sqlite3 基础

> 练习代码放 `C:\Users\A\PycharmProjects\db_practice`（沙盒，不进 api_auto 仓库）
> 第 3 课才会把 `common/db.py` 正式写进 api_auto

---

## 一、学习范围（不用全学）

| 档位 | 内容 |
|---|---|
| **必会** | `CREATE TABLE` 建表、`INSERT` 插入、`SELECT` 查询、`commit()` 落笔 |
| 用到再查 | `UPDATE` 改、`DELETE` 删、`WHERE` 条件 |
| 不用学 | 索引、视图、触发器、事务回滚、用户权限 |

判断诀窍：**大写的英文单词 = 固定语法；你自己起的名字（表名/列名/值）= 自由的。**
类型只有三种可选：`INTEGER` / `TEXT` / `REAL`。

---

## 二、10 行模板（背下来就能开工）

```python
import sqlite3

conn = sqlite3.connect("demo.db")            # 1 连接（没有就自动创建）
cur = conn.cursor()                          # 2 拿操作手（游标）

cur.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, price REAL)")
                                             # 3 建表（已存在就跳过）
cur.execute("INSERT INTO books (title, price) VALUES (?, ?)", ("Python入门", 45.5))
                                             # 4 插入（? 是占位符，防 SQL 注入）

conn.commit()                                # 5 落笔（改数据才需要）

for row in cur.execute("SELECT * FROM books"):
    print(row)                               # 6 查询并打印（row 是元组）

conn.close()                                 # 7 关闭
```

改两行（UPDATE / DELETE）放在 `commit()` **前面**：

```python
cur.execute("UPDATE books SET price = ? WHERE title = ?", (39.9, "Python入门"))
cur.execute("DELETE FROM books WHERE id = ?", (2,))
```

### conn 与 cur 的关系

| 东西 | 类比 | 能力 |
|---|---|---|
| `conn` | 银行的**窗口 / 管道** | `cursor()` / `commit()` / `close()` |
| `cur` | 窗口里的**柜员** | `execute()` / `fetchone()` / `fetchall()` |

### 三个取值方法

| 方法 | 返回 | 查不到时 |
|---|---|---|
| `execute(sql, args)` | 不返回数据（只是执行） | — |
| `fetchone()` | 一行（元组） | **`None`** ← 断言就靠它 |
| `fetchall()` | 所有行（列表套元组） | `[]` |

---

## 三、自测题（闭卷答，答对 5 题以上算过）

1. `conn.commit()` 不写会怎样？哪些语句**必须**写它，哪些**不用**？
2. SQL 里的 `?` 是干什么的？它对应你框架里的哪个东西？为什么不能直接用字符串拼接？
3. `conn` 和 `cur` 分别是什么？`commit()` 是哪个对象的方法？
4. `SELECT` 为什么不需要 `commit()`？
5. `fetchone()` 查不到数据时返回什么？用它怎么做一条"库里必须有这条记录"的断言？
6. 为什么 `UPDATE` / `DELETE` 一定要带 `WHERE`？不带会怎样？
7. （现象解释）表里 id 出现 `1、3、4`，缺 `2`，为什么？这个号以后会被新数据用掉吗？

<details>
<summary>点开看答案</summary>

1. **改动只写在草稿上，程序一关就没了，等于白插。** `INSERT` / `UPDATE` / `DELETE` 必须写；`SELECT` 不用（没改动任何东西）。
2. **占位符，值和语句分开写，执行时才填进去** —— 对应框架里的 `${xxx}`。直接字符串拼接会被 SQL 注入攻击（坏人把 SQL 片段塞进值里）。
3. `conn` 是连接对象（管道），`cur` 是游标对象（操作手）。`commit()` 是 **conn** 的方法。
4. commit 是"把改动写进文件"，SELECT 只是看一眼，没改动，不用落笔。
5. 返回 `None`，不报错。断言写：`assert cur.fetchone() is not None`。
6. 不带 WHERE 会作用于**全表**（所有行都被改/被删）。这是测试工程师最容易出的事故。
7. id=2 被 DELETE 了；3、4 是后来运行时新插的。**自增 id 用掉不回收**，2 永远空着，以后 id 不连续是正常现象。

</details>

---

## 四、动手练习（做完才算学会）

### 练习 1：自己建一张新表（20 分钟）

在 `db_practice` 里新建 `sqlite_practice.py`，要求：

- 建表 `products`，四列：`id INTEGER PRIMARY KEY`、`name TEXT`、`price REAL`、`stock INTEGER`
- 插入三条不同数据（其中至少一条 price > 50，一条 price < 50）
- 查询并打印 **price > 50** 的商品（用 `WHERE price > ?`）
- 把其中一条的 `stock` 改成 0，然后查 `WHERE stock = 0` 验证

**验收**：打印结果只有符合条件的那些行。

### 练习 2：写一个 `query_one()` 函数（这是第 3 课 db.py 的雏形）

```python
def query_one(conn, sql, args=()):
    """查一条，查不到返回 None。"""
    cur = conn.cursor()
    cur.execute(sql, args)
    row = cur.fetchone()
    cur.close()
    return row
```

用它重写练习 1 里的查询，并用 `assert query_one(...) is not None` 做一条断言。

**验收**：查存在的 → 返回元组；查不存在的 → 返回 None，断言亮红。

### 练习 3：两个破坏实验（必做，亲眼见）

| 实验 | 操作 | 应该看到 |
|---|---|---|
| A | 删掉 `demo.db` → 注释掉 `commit()` → 跑两遍 | 永远只有 1 条（改动没落笔） |
| B | `UPDATE books SET price = 9.9`（**故意不带 WHERE**） | 全表所有行价格都变 9.9 |

做完把 `commit()` 改回来。

---

## 五、遇到的坑

| 现象 | 原因 |
|---|---|
| `Can't run program ...venv\Scripts\python.exe` | PyCharm 新项目继承了已删除的旧 venv → 重新配置解释器为 `D:\python\python.exe` |
| 跑第二遍数据变多 | 数据在 `demo.db` 文件里，不会随程序结束消失（和变量不一样） |
| 建表报错 | 少了 `IF NOT EXISTS` |
| 类型只有三种 | SQLite 只认 `INTEGER` / `TEXT` / `REAL` |

---

## 六、下一课预告

第 2 课：Flask 30 行迷你接口服务（POST 写库 / GET 读库），
先装：`D:/python/python.exe -m pip install flask`
