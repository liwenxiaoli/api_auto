# api_auto —— 接口自动化练习项目

![冒烟测试](https://github.com/liwenxiaoli/api_auto/actions/workflows/smoke.yml/badge.svg)
![全量回归](https://github.com/liwenxiaoli/api_auto/actions/workflows/api-test.yml/badge.svg)

用 `requests + pytest + yaml` 搭的接口自动化框架，练手站点是
[escuelajs](https://api.escuelajs.co)（一个公开的 REST 示例 API，支持登录、商品增删改查）。

**35 条用例，接口用例全部数据驱动**：用例只描述"调什么、期望什么"，执行逻辑写在框架里。

其中 3 条是**数据库校验用例**（`test_db.py`）：除了断言接口响应，还会绕过接口直连数据库，
确认数据真的落库了 —— 跑这部分需要先启动本地 mock 服务（见文末"数据库校验"章节）。

| 用例文件 | 数据文件 | 条数 |
|---|---|---|
| `test_auth.py` | `data/auth_cases.yaml` | 4（登录成功/失败、带 token、不带 token） |
| `test_product.py` | `data/product_cases.yaml` | 8（分页、关键字、详情、异常、创建+查询） |
| `test_extract.py` | `data/extract_cases.yaml` | 6（extract 关联 + 热加载 + 清理） |
| `test_db.py` | `data/db_cases.yaml` | 3（**数据库校验**：创建查得到、删除查不到、删不存在的返 404） |
| `test_sign.py` | — | 7（签名工具单测，不联网） |
| `test_my_first.py` | — | 4（第 1 课手写用例，保留作对比） |
| `test_practice.py` | `data/practice.yaml` | 2（闭卷重建练习，保留作对比） |

## 怎么跑

```bash
# 装依赖（系统 Python 已装全的话可跳过）
pip install -r requirements.txt

# 跑全部用例
pytest

# 只跑登录模块
pytest testcases/test_auth.py

# 只跑冒烟（5 条核心正向链路，提代码时跑这个）
pytest -m smoke

# 跑回归（冒烟以外的全部）
pytest -m "not smoke"

# 切环境跑（dev / test，配置在 config/config.yaml）
pytest --env=test

# 并发跑（4 个进程；实测 12.7s → 6.5s。默认 load 分发即可，不依赖用例顺序）
pytest -n 4

# 一键跑 + 出 Allure 报告（推荐：会先清掉上一轮的旧结果）
python run.py
python run.py --env=test
python run.py --case testcases/test_extract.py

# 数据库校验用例只能跑本地 mock，所以要单独一条命令跑：
# 先另开一个终端启动本地 mock 服务并保持运行
python mock/app.py                    # 看到 Running on http://127.0.0.1:5000
pytest -m mock --env=mock             # 3 条数据库校验用例
pytest -m "not mock"                  # 其余 32 条（公网，不需要 mock）
```

> ⚠️ 两套环境**不能合成一条命令**：`--env` 一次只能选一个 base_url，
> 而 db 三条的表结构是 mock 私有的（`name/price/stock`），打到公网必然 500。
> 所以用 marker 把用例拆开、分两次跑。

> ⚠️ mock 服务**只开一个**：多个进程同时读写同一个 `shop.db` 会撞 SQLite 写锁，
> 报 `database is locked` / `unable to open database file`。

> 说明：本机的 `D:\python\python.exe` 已经装好了全部依赖，
> PyCharm 里把解释器选成它就能直接跑，不用新建虚拟环境。

## 用例分级（marker）

真实团队里不会每次都跑全量：开发提 PR 只跑**冒烟**（几分钟出结果），
每天定时跑**全量回归**。做法是用标记把用例分层：

```yaml
# data/auth_cases.yaml
- case: 正确账号登录成功
  marks: [smoke]        # 加一行就是冒烟用例
  request: ...
```

```bash
pytest -m smoke          # 只跑标了 smoke 的（当前 5 条）
pytest -m "not smoke"    # 跑其余的（29 条）
pytest                   # 全量 35 条

# 同一套机制还用来隔离"环境专用用例"：
pytest -m mock --env=mock   # db 三条（只能跑本地 mock）
pytest -m "not mock"        # 其余 32 条（公网）
```

> `mock` 这个标记名和 `--env=mock` 撞名纯属巧合，两者无关：
> `-m` 是**筛选用例**，`--env` 是**选 base_url**。

**数据驱动下有个坑**：一个测试函数要吃一整份 yaml，标记写在函数头上会让
**整份 yaml 全部变成 smoke**，等于没分级。所以标记写在 yaml 的每一条数据里，
由 `common/yaml_util.py::load_cases` 转成 `pytest.param(case, marks=..., id=...)`
挂到单条数据上。

标记必须在 `pytest.ini` 里注册（`addopts` 里有 `--strict-markers`，
不注册就报 `'smoke' not found in markers configuration option`）：

```ini
markers =
    smoke: 冒烟用例，每次提代码都要跑
    regression: 回归用例，全量跑
    mock: 只能跑本地 mock 环境（--env=mock），公网跑必然失败
```

> 注册的另一个作用是**防"假绿"**：没有 `--strict-markers` 时，
> yaml 里把 `smoke` 拼成 `somke`，pytest 会静默新建一个标记，
> 结果 `pytest -m smoke` 一条都选不中却**全绿通过** —— 你以为冒烟过了，其实一条没跑。
> 开了严格模式会当场报 `'somke' not found in markers configuration option`，收集阶段就中断。

## 并发执行（pytest-xdist）

多进程并行，把"干等 HTTP 响应"的时间重叠掉：

```bash
pytest -n 4                # 日常全量（固定 4 个进程，默认 --dist load）
pytest -n auto             # 按 CPU 核数自动开工
pytest -n 4 -m "not mock"  # 并发也能和 -m 叠加
pytest -n 0                # 退回串行（调试单条 / 打断点 / 看 print 时用）
```

日常命令就这么记：**`-n 数字` 当成一个开关**，`-n 0` 关掉。

> 为什么**不写进 `pytest.ini` 的 `addopts`**：写死后每次跑单条、打断点都要先起 4 个进程，
> 子进程里断点不可靠、日志也乱。调试时用 `-n 0` 手动退回即可。
> 已经写死在 CI 的回归层命令里（CI 不需要调试，只求快）；**冒烟层故意不加**——
> 只有 5 条，4 个进程各登录一次的开销比省下的时间还多（实测串行 5.1s vs 并发 6.7s）。

### 为什么现在不需要 `--dist loadfile` 了

xdist 是**多进程**，每个 worker 一份内存，**变量池不共享**。早期这套用例靠"上一条用例
第 ④ 步 extract 塞值 → 下一条用例第 ① 步取用"串联，一旦两个用例被拆到不同进程，
下游就会 `KeyError: 占位符 ${xxx} 没有值`。当时靠 `--dist loadfile`（同文件→同 worker）
强行把链条按文件绑住，是一种**绕过去**的做法。

根治办法是**取消"用例之间的隐式依赖"**，两条规则：

1. **公共数据由 session 级 fixture 提供**，不由某条用例顺手塞。
   `conftest.py` 的 `existing_product` 会造一个商品并写入 `product_id / product_title /
   product_price`。session fixture 在**每个 worker 各执行一次**，所以无论用例分到哪个进程，
   池里都有料。
2. **私有的中间变量加文件前缀**，避免跨文件撞键。
   变量池是**全局命名空间**，键名唯一。曾出现 `extract_cases.yaml` 和 `product_cases.yaml`
   都往 `product_id` 写、且两边数据不同（88 元 / 99 元），并发时后写者覆盖先写者 →
   偶发 `期望 99，实际 88`。现在改为 `extract_product_*` / `created_product_*` /
   `db_product_*` 各写各的。

改完的验收（不加 `loadfile`，连跑 5 次）：

| 命令 | 结果 |
|---|---|
| `pytest -q`（串行） | 31 passed |
| `pytest -n 4 -q`（默认 load，连跑 5 次） | **5/5 全绿，31 passed** |
| `pytest testcases/test_extract.py -n 4 -q`（只跑一个文件、强行拆散） | 6 passed |

**遗留约束（仍然成立）**：一条用例如果需要"上一条用例刚造的那条数据"，本质上还是有顺序依赖。
本项目的做法是让这类用例改读 fixture 提供的公共数据，而不是读上一条用例的结果 ——
代价是语义从"查刚创建的那个"变成"查一个已知存在的商品"，用例名已同步改掉。
真需要"创建后立刻查"的闭环，正确做法是把它做成**一条用例**（或用 fixture 里造+清理），
而不是靠两条用例的执行顺序。

> 只快约 2 倍而不是 4 倍，是因为 session fixture **每个 worker 各跑一遍**
> （4 次登录，每次约 2.7s），这部分省不掉。

## 多环境配置

一套代码跑多个环境，切换只靠命令行参数，**不改代码、不改 yaml**：

```bash
pytest --env=test          # 不传则用 config.yaml 里的 default_env
```

```yaml
# config/config.yaml
default_env: dev

environments:
  dev:  {base_url: https://api.escuelajs.co/api/v1, timeout: 15, user: {...}}
  test: {base_url: https://api.escuelajs.co/api/v1, timeout: 30, user: {...}}
  mock: {base_url: http://127.0.0.1:5000, timeout: 10, db_path: mock/shop.db, user: {...}}
```

`mock` 是本地自建服务（见文末"数据库校验"），多出来的 `db_path` 只有它有 ——
`settings.py` 用 `conf.get("db_path")` 读取，没配的环境数据库断言会自动跳过，**不影响原有用例**。

实现在 `config/settings.py` 的 `Config.configure()`：环境不存在直接报
`环境 [xxx] 不存在。可用环境：['dev', 'test']`，绝不静默用默认值。
`conftest.py` 里用 `pytest_addoption` 注册 `--env`、`pytest_configure` 里切换。

跑起来输出第一行就能看到环境：

```
运行环境: test | base_url: https://api.escuelajs.co/api/v1 | timeout: 30
```

## Allure 报告

`run.py` 做了四件事：清掉上轮结果 → 跑 pytest（`--alluredir`）→ 写环境信息 → `allure generate` 出网页报告。
报告在 `reports/allure-report/index.html`。

```bash
python run.py --open      # 出完自动起本地服务并打开浏览器（推荐）
```

> ⚠️ **别直接双击 index.html**：Allure 报告用 fetch 加载 json，
> `file://` 协议会被浏览器拦下 → 打开是白屏。要走 http（`--open` 或 `allure open`）。

报告首页的 ENVIRONMENT 区块会显示这轮跑的环境（run.py 写的 `environment.properties`）。

## 请求签名（sign）

签名规则：去掉空值和 `sign` 本身 → 参数名排序 → 拼 `k1=v1&k2=v2` → 尾部拼密钥 → md5。
实现在 `common/sign.py`（不依赖网络，所以有独立的单元测试 `testcases/test_sign.py`，7 条）。

框架里怎么用？yaml 用例加一个 `sign` 字段，框架自动算好再发：

```yaml
- case: 带签名查询商品列表
  request:
    method: GET
    path: /products
    params: {limit: 2}
  sign:
    secret: my_secret     # 真实项目应从配置/环境变量读，不要写死在 yaml
    on: params            # 对谁签名：params / json（默认 params）
    in: params            # 签名值放哪：params / headers（默认跟 on 一样）
  expect_status: 200
```

日志能看到签名确实被算出来并发出去：

```
签名原始串: limit=2&key=my_secret
签名结果 sign = aa62e28daa4bd9eb1c4222eb7629521d
```

> 签名算错会导致接口全量 401、几十条用例一起红，根本看不出是签名的问题 ——
> 所以签名逻辑单独写单测，接口用例失败时就只需怀疑"参数/环境"，排查范围小一大半。

## CI：GitHub Actions（分层跑）

CI 不是"把用例全跑一遍"。**高频的检查必须便宜，否则没人等它，红了也就没人看。**
所以同一批 35 条用例按 marker 切两层，用两条命令跑：

| 层 | 文件 | 触发时机 | 跑哪些 | 耗时 | 红了怎么办 |
|---|---|---|---|---|---|
| 冒烟 | `.github/workflows/smoke.yml` | 每次 push / 提 PR | `-m "smoke and not mock"` → 5 条 | ~15 秒 | **拦住合并** |
| 回归 | `.github/workflows/api-test.yml` | 每天 10:00 + 网页手动点 | `-m "not mock" -n 4 --reruns 2` → 32 条 | ~1 分钟 | 发通知，不拦合 |

设计要点：

- **不是两套用例**：只有一批用例，yaml 里打 marker，用两个 `-m` 表达式筛出两个子集。
  真写两套文件，三个月后两边必然不一致。
- **冒烟必须能单独切出来跑**：所以冒烟层里不能有"依赖前面用例造的数据"的用例。
  `pytest -m smoke` 只收集 5 条，那条造数据的用例根本没被选中，一跑就红。
  需要公共数据就声明 `existing_product` 这类 fixture——写在参数里，pytest 保证先建好。
- **回归必须重试，冒烟不重试**：回归连公网，超时/限流/5xx 是常态（`--reruns 2 --reruns-delay 1`
  只治外部抖动，断言失败重试也白搭）；冒烟只跑主干，它红了就是真红了，重试只会掩盖问题。
- **`not mock` 不能省**：CI 上没有 `127.0.0.1:5000`，那 3 条数据库校验用例必然连不上。
  显式写出来，别依赖"目前没人给 mock 用例打 smoke 标"这种巧合。
- 失败也上传报告：`if: always()` 保证 artifact 里能看到挂在哪一条。
- Python 版本跟本地 `.venv` 对齐（3.13），避免"本地绿、CI 红"这种最难查的问题。

## 目录说明

```
api_auto/
├─ config/
│  ├─ config.yaml      # environments：dev / test / mock 三套环境（地址、超时、账号、db_path）
│  └─ settings.py      # Config 对象：读 yaml + 按 --env 切换环境
├─ common/
│  ├─ client.py        # HttpClient：requests.Session 封装（拼地址、超时、日志、渲染占位符）
│  ├─ context.py       # 变量池：存/取变量，把 ${token} 换成真实值
│  ├─ functions.py     # 热加载函数：yaml 里写 ${gen_phone()} 时现调现算
│  ├─ sign.py          # 签名工具：参数排序 + 拼密钥 + md5（有独立单元测试）
│  ├─ extractor.py     # extract：按 jsonpath 规则把响应里的值存进变量池
│  ├─ runner.py        # 通用用例执行器：一份 yaml 数据 → 一次完整调用
│  ├─ asserter.py      # 统一断言：相等 / contains / not_empty / gt / lt / 整体断言 / 数据库
│  ├─ db.py            # 数据库直连：query_one / execute（绕过接口查库，通道 B）
│  ├─ yaml_util.py     # 读 data/ 下的用例数据
│  ├─ json_util.py     # jsonpath 取值工具
│  └─ logger.py        # 日志（logs/api.log）
├─ data/               # 用例数据（yaml）
├─ testcases/          # 用例
├─ mock/               # 本地 mock 服务：Flask + SQLite，给数据库校验提供可碰库的被测对象
│  └─ app.py           # /auth/login、GET|POST /products、DELETE /products/<id>、/reset
├─ .github/workflows/  # GitHub Actions：smoke.yml(每次 push) + api-test.yml(每天定时全量)
├─ docs/               # 学习指南、练习说明
├─ conftest.py         # fixture：ctx / client / token / auth_client + --env 参数
├─ run.py              # 一键跑：清结果 → pytest → allure generate
├─ pytest.ini
└─ requirements.txt
```

## 五个 fixture 的区别（conftest.py）

| fixture | 作用域 | 用途 |
|---|---|---|
| `ctx` | session | 变量池，配合 extract 与 `${}` 占位符使用 |
| `init_context` | session（autouse） | 自动把登录 token 放进变量池，yaml 里可直接写 `${token}` |
| `cleanup_test_data` | session（autouse） | 收尾统一删除本轮创建的数据 |
| `client` | session | 未登录的客户端，查公开接口用 |
| `token` | session | 只登录一次，所有用例共用 |
| `auth_client` | function | 带 `Authorization` 头的客户端（改造后暂无用例使用，保留演示 `remove_header` 的坑） |

用例里要哪个就把名字写进参数，pytest 自动注入 —— 不用手动创建。
（`autouse=True` 的两个不用写名字，自动生效。）

## yaml 用例字段速查

所有 `data/*.yaml` 结构完全一致，加场景只改这里：

```yaml
- case: 用例名                      # 显示在 pytest 输出和报告里
  story: 报告里的二级分组
  request:
    method: GET
    path: /products/${product_id}   # 支持 ${} 占位符
    params: {limit: 1}
    json: {title: "auto-${random_str(8)}"}
    headers: {Authorization: "Bearer ${token}"}
  expect_status: 200                # 也可写 [400, 404] 多个都算对
  extract: {product_id: $.id}       # 取响应里的值存进变量池
  expect:
    $.email: john@mail.com          # ① 相等
    $.price: {gt: 0}                # ② 高级：contains / not_empty / gt / lt
    "@length": 1                    # ③ 对整份响应断言（@ 必须加引号）
  cleanup:                          # 兜底清理，测试结束统一执行
    method: DELETE
    path: /products/${product_id}
    headers: {Authorization: "Bearer ${token}"}
  db_assert:                        # 可选：数据库断言（需环境配了 db_path）
    sql: SELECT name, price FROM products WHERE id = ${product_id}
    expect: [小米15, 4999]           # 按列顺序比对；写 null 表示期望查不到
  sign: {secret: my_secret}         # 可选：自动算签名
```

## 接口关联：extract + 占位符

yaml 里声明"提取什么"，后面用例用 `${变量名}` 引用，发送前自动替换：

```yaml
extract:
  token: $.access_token        # 从登录响应里取出 token 存进变量池
  product_id: $.id             # 从创建响应里取出商品 id
```

```yaml
path: /products/${product_id}                 # 路径里引用
headers: {Authorization: "Bearer ${token}"}   # 请求头里引用
```

执行一条用例的固定 6 步（见 `common/runner.py`）：
`渲染占位符 → 发请求 → 断言状态码 → extract 提取 → 断言 expect 字段 → 断言数据库`。
所以 `testcases/test_extract.py` 里几乎没有代码 —— **加场景只改 yaml**。

### 热加载函数

yaml 里写函数调用，执行到那一刻才现算，解决"数据每次跑必须不一样"：

```yaml
title: "auto-${random_str(8)}"     # 随机标题，避免重复
phone: "${gen_phone()}"            # 随机手机号
order_no: "${timestamp()}"         # 时间戳
```

可用函数见 `common/functions.py`；**只能调用该模块里定义的函数**（`context.py` 做了限制）。

### 测试数据自动清理

用例加 `cleanup` 字段，框架登记下来，全部跑完后统一删除：

```yaml
  cleanup:
    method: DELETE
    path: /products/${product_id}
    headers: {Authorization: "Bearer ${token}"}
```

登记发生在 expect 断言**之前**，所以中间断言失败也会清干净（见 `conftest.py::cleanup_test_data`）。

## 数据库校验：接口断言 + 数据库断言双通道

### 为什么需要它

接口说"创建成功了"**不等于**数据真的存进去了。实测过一次：把服务端的 `conn.commit()`
注释掉，接口照样返回 `201` 并给了一个 id，但数据库里一条记录都没有 ——
**接口断言全部通过，数据库断言一查就红。**

> 接口断言 = 听服务员说"菜做好了"；数据库断言 = 亲自去厨房看盘子。

练手站 escuelajs 的数据库在人家服务器上，碰不到，所以做不了这层校验。
解决办法是**自建一个 mock 服务**（`mock/app.py`，Flask + SQLite），让被测对象变成白盒：
HTTP 调接口（通道 A）+ sqlite3 直连查库（通道 B）两条路都有。

### 跑起来

```bash
python mock/app.py                           # 终端 1：保持运行，看到 Running on http://127.0.0.1:5000
pytest testcases/test_db.py --env=mock -v    # 终端 2
```

| 用例 | 接口断言 | 数据库断言 |
|---|---|---|
| 创建商品后数据库里应有该记录 | 201 | `SELECT ... WHERE id=1` → `['小米15', 4999.0, 30]` |
| 删除商品后数据库里应查不到 | 200 | 同一条 SQL → 查不到（`expect: null`） |
| 删除不存在的商品应返回 404 | 404 | `WHERE id=99999` → 查不到 |

三条用例顺序依赖：第一条 `extract` 出 `product_id`，第二条、第三条引用它。

### yaml 怎么写

```yaml
- case: 创建商品后数据库里应有该记录
  request:
    method: POST
    path: /products
    json: {name: 小米15, price: 4999, stock: 30}
  expect_status: 201
  extract:
    product_id: $.id                     # 存进变量池，后面用例用
  expect:
    $.name: 小米15                        # 通道 A：验响应
  db_assert:                             # 通道 B：验数据库
    sql: SELECT name, price, stock FROM products WHERE id = ${product_id}
    expect: [小米15, 4999, 30]            # 按 SELECT 的列顺序比对
    # expect: null                        # 写 null 表示"期望这一行查不到"
```

要点：

- `sql` 会先过 `ctx.render()`，`${product_id}` 才换成真实 id
- `expect` 是列表，和查询结果的元组**按列顺序**比对（`SELECT` 出来是元组，没有字段名）
- `expect: null` → Python 读到 `None` → 断言 `fetchone() is None`，正合"删除后应该查不到"
- 没配 `db_path` 的环境（dev / test）**自动跳过并记一条 warning**，老用例不受影响

### 踩过的坑

| 现象 | 原因 |
|---|---|
| `database is locked` / `unable to open database file` | 同时开了多个 mock 服务进程抢同一个 `shop.db`，只留一个 |
| 请求打到 escuelajs 公网、POST /products 返回 500 | 忘了加 `--env=mock`（看日志第一行"环境 = ?"） |
| `405 Method Not Allowed` | 路径对但方法没注册（`/products/<int:pid>` 只登记了 DELETE） |
| 数据库断言不执行、日志一条没有 | 环境没配 `db_path`，属预期行为（向后兼容设计） |
| teardown 出现 `DELETE /products/1 -> 404` | 第一条的 `cleanup` 重复删已被第二条删掉的数据，**保留**它更稳妥（单独跑第一条时不脏库） |

`mock/shop.db` 是运行生成的，已加进 `.gitignore`，不进仓库。

## 练习站点的已知"坑"（都是实测出来的）

- `GET /products?limit=1` **必须同时传 offset**才生效，否则返回全部数据
- `PUT /products/{id}`（更新）目前返回 **500**，接口本身有问题 —— 所以用例里没写更新场景
- 查询不存在的商品返回 **400**（正常应该是 404），测试用例里按 `in (400, 404)` 断言
- 创建商品必须带 token，不带会返回 400
- **公共数据会被别人删**：`GET /products/1` 这类写死 id 的用例随时可能变 400，
  正确做法是先查列表拿一个真实存在的 id 再用（见 `testcases/test_product.py::test_detail`）
- 请求头里**不能写中文**（会报 `UnicodeEncodeError`）

这些"坑"本身就是接口测试的价值所在：文档写的和实际的往往不一样。
