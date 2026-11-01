# 数据库校验 · 第 3 课：把数据库断言接进 api_auto

> 项目：`C:\Users\A\PycharmProjects\api_auto`
> 前置：第 1 课（sqlite3 基础）、第 2 课（Flask 迷你服务）已学完
> 本课成果：**接口断言 + 数据库断言双通道闭环**，`2 passed`

---

## 一、为什么要自己搭一个 mock 服务

完整闭环长这样：

```
接口说"我创建成功了"  →  绕过接口代码，直接翻数据库看有没有这条
```

escuelajs（你之前测的公网站）的数据库在人家机房里，**你根本没有"第二条通道"**，只能做接口断言。

所以把服务内置进项目：`mock/app.py`。理由很实际：

> 这是要给面试官看的作品集仓库。如果数据库校验依赖你电脑上另一个项目，
> 别人 clone 下来跑不起来，等于没有。内置之后 **clone → pip install → 启动 → 跑**，全流程自包含。

简历上可以写：**"自建 mock 服务支撑数据库校验"** —— 比"连了个本地服务"硬得多。

---

## 二、本机两条通道（本课的核心模型）

| 通道 | 怎么走 | 经过接口代码吗 | 它回答的问题 |
|---|---|---|---|
| **A：HTTP** | `client.post(...)` → Flask | ✅ 经过 | 接口**说**了什么 |
| **B：sqlite3 直连** | `query_one(sql)` | ❌ 绕过 | 库里**实际**有什么 |

通道 A 的回答者是你的 Flask 代码 —— **代码可以撒谎**（第 2 课注释掉 `commit()` 那次，接口照样返回 201）。

通道 B 绕开所有接口代码直接翻文件 —— **两条交叉验证，谎言藏不住。**

---

## 三、改动清单（5 处）

| 文件 | 改动 |
|---|---|
| `mock/app.py`（新建） | 5 个接口：`/auth/login`、`GET/POST /products`、`DELETE /products/<int:pid>`、`/reset` |
| `common/db.py`（新建） | `query_one(sql, args=())` / `execute(sql, args=())` |
| `common/asserter.py` | 新增 `assert_db(conf, ctx)` |
| `common/runner.py` | import + 在 `assert_expect` 后加一行 `assert_db(...)` |
| `data/db_cases.yaml` + `testcases/test_db.py`（新建） | 两条闭环用例 |
| `config/config.yaml` / `settings.py` / `requirements.txt` | 加 `mock` 环境、`db_path`、flask 依赖 |

### 3.1 `common/db.py`

```python
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
        return cur.fetchone()
    finally:
        conn.close()          # 不管中间报不报错，一定关门


def execute(sql, args=()):
    """执行改数据的语句（INSERT/UPDATE/DELETE），自带 commit，返回影响行数。"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        conn.commit()         # 改数据必须落笔，否则又变幽灵数据
        return cur.rowcount
    finally:
        conn.close()
```

三个要点：
- **路径从 `settings.db_path` 读**，不写死
- **`?` 占位符**，`args` 给占位符传值（对应 yaml 的 `${}`）
- **`try/finally` 保证 close** —— 比"最后一行 close"更稳，中间炸了也能关

### 3.2 `common/asserter.py` 的 `assert_db`

```python
def assert_db(conf, ctx):
    if not conf:                                   # ① 没写 db_assert 的用例跳过
        return
    if settings.db_path is None:                   # ② 没配 db_path 的环境跳过
        logger.warning("环境 [%s] 没配 db_path，跳过数据库断言", settings.env)
        return

    sql = ctx.render(conf["sql"])                  # ③ ${product_id} → 1
    expected = ctx.render(conf.get("expect"))      # ④ None 原样返回（yaml 写 null）
    row = query_one(sql)                           # ⑤ 通道 B：直接翻库

    if expected is None:                           # ⑥-A 期望"查不到"
        assert row is None, f"期望数据库里查不到这条记录，实际查到了：{row}\nSQL: {sql}"
        return

    assert row is not None, f"期望数据库里查得到记录，实际一条都没查到\nSQL: {sql}"
    assert list(row) == list(expected), (
        f"数据库记录不符\n期望: {list(expected)}\n实际: {list(row)}\nSQL: {sql}"
    )
```

**四条设计取舍：**

| 规则 | 为什么 |
|---|---|
| `sql` 必须过 `ctx.render()` | 不渲染就是一句带 `${...}` 的废话，SQLite 直接语法错 |
| `expect` 用**列表**，按列顺序比 | SELECT 出来是元组、没字段名，只能按顺序对 |
| `expect: null` → 断言 `row is None` | "期望查不到"正好对上 `fetchone()` 返回 None，删除类用例的核心断言 |
| `db_path` 为 None 时**跳过不报错** | 加新功能不能破坏 dev/test 环境（原来 31 条用例照跑） |

**为什么分成两步断言？** 不能一步写 `list(row) == list(expected)` —— `row` 是 None 时 `list(None)` 抛 `TypeError: 'NoneType' object is not iterable`，看不出是"没查到"还是"代码错"。分开后报错直接告诉你原因。

### 3.3 `runner.py` 接线（只加两处）

```python
from common.asserter import assert_db, assert_expect, assert_status   # import
...
    assert_db(case.get("db_assert"), ctx)     # 放在 assert_expect 之后
```

**注意没写 `if`** —— 直接把可能是 None 的值传进去，让 `assert_db` 自己判断。

> 职责分离：runner 只管"按顺序调谁"，"要不要做"是 `assert_db` 自己的事。

### 3.4 用例 yaml

```yaml
- case: 创建商品后数据库里应有该记录
  request:
    method: POST
    path: /products
    json: {name: 小米15, price: 4999, stock: 30}
  expect_status: 201
  extract:
    product_id: $.id
  expect:
    $.name: 小米15
  db_assert:
    sql: SELECT name, price, stock FROM products WHERE id = ${product_id}
    expect: [小米15, 4999, 30]
  cleanup:
    method: DELETE
    path: /products/${product_id}

- case: 删除商品后数据库里应查不到
  request:
    method: DELETE
    path: /products/${product_id}
  expect_status: 200
  db_assert:
    sql: SELECT id, name FROM products WHERE id = ${product_id}
    expect: null
```

第二条**依赖第一条 extract 出来的 `product_id`** —— parametrize 严格按 yaml 列表顺序执行，所以顺序依赖成立。

---

## 四、怎么跑（记住这个顺序）

```
1. PyCharm 里 Run mock/app.py        ← 先开店，窗口别关（只开一个！）
2. .venv\Scripts\python.exe -m pytest testcases/test_db.py --env=mock -v
```

**认准日志第一行**：`环境 = mock，base_url = http://127.0.0.1:5000`

---

## 五、本课踩过的坑（都是真踩的）

| 现象 | 原因 | 修法 |
|---|---|---|
| `环境 = dev`，打到 escuelajs 返回 500 | 没传 `--env=mock` | 运行配置加参数，或直接用 Terminal 敲命令 |
| `database is locked` / `unable to open database file` | **同时跑了多个 mock 服务**抢同一个 shop.db | 只留一个服务；删掉 `shop.db` 让它重建；连接加 `timeout=10` |
| 请求打到 `/products/1` 返回 **405** | yaml 里 `method` 写成了 POST，该路径只注册了 DELETE | 405 = 路径存在但方法不允许；404 才是路径不存在 |
| `requests.ConnectionError ... 10061` | 服务没启动 | 先 Run `mock/app.py` |
| `ModuleNotFoundError: No module named 'flask'` | 装包装到了系统 Python，PyCharm 用的是 `.venv` | 装包一律用 `.venv\Scripts\python.exe -m pip install` |
| PyCharm 跑起来没带 `--env` | 点的是右键生成的**临时配置**，不是自己建的那个 | 认右上角下拉框显示的是 `mock-db`；或改用 Terminal |

---

## 六、自测题（10 题，闭卷答）

1. 为什么要自己搭 mock 服务，而不直接测 escuelajs？
2. 通道 A 和通道 B 分别是什么？为什么"接口返回 201"不能替代通道 B？
3. `assert_db` 里为什么必须先 `ctx.render(sql)`？
4. `expect: null` 在 yaml 里不加引号，Python 读进来是什么？它对应哪条断言？
5. 为什么 `assert_db` 里 `db_path` 为 None 时选择"记日志跳过"而不是报错？
6. runner 里调用 `assert_db` 为什么没写 `if`？
7. 为什么不能一步写 `assert list(row) == list(expected)`？
8. `query_one` 里为什么用 `try/finally` 而不是在最后一行 `conn.close()`？
9. 第二条用例为什么必须写在第一条后面？它依赖什么？
10. `sqlite3.connect(path, timeout=10)` 这个 `timeout` 解决什么问题？

<details>
<summary>答案（先自己答完再看）</summary>

1. escuelajs 的数据库在人家机房，**没有通道 B**，只能做接口断言；且内置 mock 让仓库自包含，clone 就能跑。
2. A = HTTP 调接口（经过 Flask 代码，代码可以撒谎）；B = sqlite3 直连查库（绕过接口代码）。201 只证明"代码执行到了 return 那一行"，不证明数据落盘。
3. sql 里有 `${product_id}`，不渲染就是字面 `${...}`，SQLite 会语法错。
4. `None`；对应 `assert row is None`（期望查不到）。
5. 向后兼容：dev/test 没配 db_path，报错会让原有 31 条用例全崩。加新功能不能破坏既有环境。
6. 职责分离：runner 只管"按顺序调谁"，"要不要做"的判断属于 `assert_db` 自己，将来别处调用也不会漏。
7. `row` 为 None 时 `list(None)` 抛 `TypeError: 'NoneType' object is not iterable`，看不出是"没查到数据"还是"代码写错"。分开写报错信息能直接定位。
8. `finally` 保证**中间抛异常也能关门**；写在最后一行，一旦 execute 报错就永远关不掉，连接越攒越多。
9. parametrize 按 yaml 列表顺序执行，第二条要用第一条 `extract` 存进变量池的 `product_id`。
10. SQLite 同一时刻只允许一个连接写；测试脚本直连 + mock 服务在写，撞上时默认只等 5 秒就抛 `database is locked`，给 10 秒让它排队等。

</details>

---

## 七、练习

**练习 1（必做）：见红验收**
把第二条的 `expect: null` 改成 `expect: [1, 小米15]`，跑一次**必须红**（数据真被删了，查不到）。看到红再改回 `null`。
> 规矩：**每条断言都要见过它红的样子**，否则可能是假绿。

**练习 2（必做）：异常用例 —— 删不存在的商品**
新增第三条：`DELETE /products/99999`，`expect_status: 404`（你的 mock 里 `rowcount == 0` 时返回 404）。
> 这是标准异常用例，简历加分项。

**练习 3（加分）：让登录变"真"**
给 `mock/app.py` 的 `/auth/login` 加校验：密码不对返回 401。然后加一条用例 `expect_status: 401`。

---

## 八、下一步

- 把 `common/db.py` 的 `execute()` 用起来：写一个**前置数据准备** fixture（每条用例前 `DELETE FROM products`），让用例互不影响
- `conn.row_factory = sqlite3.Row` —— 让查询结果能 `row["name"]` 按字段名取，不用记下标
- 把这条线的成果写进 README 和简历
