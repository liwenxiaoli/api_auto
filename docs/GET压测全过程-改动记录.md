# GET 接口压测全过程（含每一处改动）

> 这份文档按**时间顺序**记录从"第一次压测"到"能对外报数"的全过程。
> 每个阶段统一四段：**现象 → 判断 → 改了哪儿 → 结果**。
> 概念和原理看《性能测试第一课》，这里只讲"当时看到什么、动了哪行"。

---

## 阶段 0：准备（压测工具和靶子）

**靶子**：`mock/app.py`（Flask + SQLite，`GET /products` 返回全表）

**压测脚本**：`perf/locustfile.py`（新建）

```python
from locust import HttpUser, task, between


class ProductUser(HttpUser):
    # 压测靶子：只压本地 mock（waitress）。故意写死，不要换成公网地址
    host = "http://127.0.0.1:5000"

    wait_time = between(0.1, 0.2)

    @task
    def list_products(self):
        self.client.get("/products")
```

三个参数的含义：

| 写法 | 含义 |
|---|---|
| `host` | 靶子地址。写死是有意的：防止哪天误压公网 |
| `wait_time = between(0.1, 0.2)` | 每个用户跑完一次，随机歇 0.1~0.2 秒（均值 0.15） |
| `@task` | 被压的行为，一个用户循环执行它 |

**装依赖**（必须装进项目 venv，不是系统 python）：

```
pip install waitress locust
```

装完记进 `requirements.txt`：

```
waitress==3.0.2
locust==2.47.0
```

---

## 阶段 1：Flask 自带服务器 → waitress

### 现象

10 个用户压上去，响应时间就以"秒"计。

### 判断

Flask 自带的 `app.run()` 是 **Werkzeug 开发服务器**，单进程单线程，一次只能处理一个请求。它是给人调试用的，不是给人压的。

### 改了哪儿

`mock/app.py` 最后一行。

**改前**：

```python
if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000)
```

**改后**：

```python
from waitress import serve

if __name__ == "__main__":
    init_db()
    serve(app, host="127.0.0.1", port=5000, threads=8, connection_limit=100)
```

### 结果

`64.6 → 315 → 600.8 RPS`。换对了。

---

## 阶段 2：connection_limit 100 → 1000

### 现象

压力继续加，RPS 卡在 **616.5** 不动，但 **Med（中位数）只有 6ms**。

### 判断（这是全篇最重要的一次判断）

```
RPS 卡住 + Med 不涨  →  请求根本没进来，服务端很闲
RPS 卡住 + Med 暴涨  →  进来了但排队
```

我们的 Med 是 6ms —— 请求进去就出来了。**说明不是服务端处理不过来，是连接进不来。**

waitress 的默认值：`threads=4`、`connection_limit=100`、`backlog=1024`。100 个连接名额一满，新连接就在内核队列里干等。

### 改了哪儿

同一个 `serve(...)` 调用：

```python
# 改前
serve(app, host="127.0.0.1", port=5000, threads=8, connection_limit=100)

# 改后
serve(app, host="127.0.0.1", port=5000, threads=8, connection_limit=1000)
```

### 结果

`616.5 → 1222 RPS`，**×1.98**。第一次真正的翻倍。

---

## 阶段 3：threads 扫描（撞上 GIL）

### 现象

想着"线程加到 8 了还不够，再加"。扫了 2 / 4 / 8 / 16 / 32：

| threads | RPS | Med |
|---|---|---|
| 2 | 783 | 90ms |
| 4 | 1026 | 29ms |
| 32 | 1087 / 1176 | 14ms |

**2 加到 32（16 倍），RPS 只涨了 50%。**

### 判断

`threads` 到 2 之后就不是决定因素了。真正的天花板是 **GIL**：

> 一个 Python 进程里，任何时刻只有一个线程能执行 Python 代码。
> 8 个线程 ≠ 8 份算力，而是 8 个人抢 1 支笔。

验证：压测时看任务管理器，整机 CPU 只有 **11%**（≈3.5 核 / 32 核）——而 mock 那 1 个核已经 100%。

**整机 11% 和"跑不快"完全不矛盾：堵的是那一条车道，不是整条高速。**

### 改了哪儿

代码没改。**改的是认知**：停止在 `threads` 上继续调参。

### 结果

确认"加线程无用"，把嫌疑从"线程不够"划掉。

---

## 阶段 4：先排除压测机（关键方法论）

### 现象

单客户端 200 用户时，RPS 卡在 1050 左右，Med 只有 24ms。

### 判断

Med 24ms 说明服务端很闲。那卡在哪儿？**可能是压测机自己发不出更多。**

Locust 单进程用 gevent 协程，**只能用 1 个 CPU 核**。一个核要做三件事：发请求、收响应、算统计。

### 怎么验证

开**两个 Locust 进程**同时压，总用户 400。

### 改了哪儿

`mock/app.py` 增加端口参数（为了能起第二个服务），`perf/locustfile.py` 的 `host` 可以用 `--host` 覆盖：

```python
# mock/app.py 末尾
if __name__ == "__main__":
    import sys

    # 端口从命令行读，不传就用 5000：python mock/app.py 5001
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

    init_db()
    serve(app, host="127.0.0.1", port=port, threads=4, connection_limit=1000)
```

> ⚠️ 这里踩过一个坑，见「附录 A 第 3 条」：变量算出来了但没传给 `serve`，
> 两个进程都监听 5000，而 Windows 的 `SO_REUSEADDR` 不报错。

### 结果

`644.37 + 644.45 = 1288.8 RPS`。

**结论：原来的 1050 是压测机的顶，不是服务端的。** 同时 Med 从 24ms 涨到 140ms —— 服务端终于开始排队了。

---

## 阶段 5：加进程（第一次尝试，失败）

### 现象

| 配置（800 用户） | RPS | Med |
|---|---|---|
| 2 个服务进程 | 1217 | 490 / 170ms |
| 1 个服务进程 | 1249 | 490ms |

**两个进程加起来还不如一个。** 加人没用、加进程也没用。

### 判断

不是"能力不够"，是**在抢东西**。两个进程之间唯一共享的就是同一个 `shop.db` 文件。

### 改了哪儿

这一轮**没改代码**，只记录了现象——因为下一步要先搞清楚"钱花在哪儿"。

### 结果

把嫌疑锁到"每个请求自己的开销"上。

---

## 阶段 6：微基准，把单请求成本拆开

### 现象

服务端 `4 线程 ÷ 1289 RPS ≈ 3.1ms`（单请求墙钟时间），但对一个只查几十行的小表来说太贵了。

### 判断

贵在三个环节之一：建连接 / 查询 / JSON 序列化。**不猜，先量。**

### 改了哪儿

新建 `练习/perf_db.py`（微基准脚本），各跑 1000 次：

```python
import sqlite3
import time
from pathlib import Path

DB = str(Path(__file__).resolve().parent.parent / "mock" / "shop.db")
N = 1000

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
    rows = conn.execute("SELECT id, name, price, stock FROM products").fetchall()
    conn.close()
full_cost = time.perf_counter() - start

# 两个总耗时相减 = 查询本身
query_cost = full_cost - connect_cost

print(f"只建连接     单次 {connect_cost / N * 1000:.3f} ms")
print(f"建连接+查询  单次 {full_cost / N * 1000:.3f} ms")
print(f"查询本身     单次 {query_cost / N * 1000:.3f} ms")
```

### 结果

| 环节 | 单次耗时 | 占比 |
|---|---|---|
| 建连接 | **0.307ms** | 51% |
| 查询 | 0.291ms | 49% |
| 合计 | 0.598ms | 100% |

**开一条数据库连接，和真的查一遍数据，一样贵。**

换算成压测口径：

```
1 个核跑 1289 RPS  →  每个请求占用 CPU = 1 ÷ 1289 = 0.78ms
建连接占 0.31ms    →  占 40%
省掉它 → 0.47ms    →  1 ÷ 0.00047 ≈ 2100 RPS（预测值）
```

---

## 阶段 7：连接复用（全程唯一的大胜）

### 改了哪儿（两处，缺一不可）

**① `mock/app.py` 顶部 + `get_conn()`**

**改前**：

```python
def get_conn():
    return sqlite3.connect(DB, timeout=10)
```

**改后**：

```python
import threading
_local = threading.local()

def get_conn():
    """每个线程复用自己的连接，不再每次新建"""
    if not hasattr(_local, "conn"):
        conn = sqlite3.connect(DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")   # 阶段 10 加的
        _local.conn = conn
    return _local.conn
```

`threading.local()` = **每个线程一个自己的储物柜**。普通全局变量是所有线程共用一个柜子（要抢、要锁），`threading.local()` 是各用各的。

**② 删掉所有 `conn.close()`**

`grep -n "conn.close()" mock/app.py` → 4 处，全部删除。
`conn.commit()` 保留（写操作必须提交）。

> ⚠️ 漏删一处会报 `sqlite3.ProgrammingError: Cannot operate on a closed database`，
> 而且**第一次调用完全正常，第二次才炸**——因为柜子里存的是一条已经关闭的连接。

### 先回归，再压

```
python -m pytest -q --env=mock testcases/test_db.py
# 3 passed in 0.16s
```

**顺序不能反。** 性能优化把功能改坏是最常见的翻车方式。

### 结果

| 指标 | 优化前 | 优化后 |
|---|---|---|
| RPS | 1289 | **2491** |
| Med | 140ms | **5ms** |
| 变化 | | **×1.93** |

预测 2100，实测 2491 —— **打过了预测**，因为省下的不止建连接，还有跟着它消失的文件 I/O 和锁开销。

---

## 阶段 8：压 800 用户把服务打崩

### 现象

```
ValueError: too many file descriptors in select()
```

### 判断

Windows 的 `select()` 最多只能监控 **512 个句柄**（`FD_SETSIZE`）。800 个并发 socket 直接越界。

**为什么偏偏优化后才崩**：服务端变快了 → 连接周转更快 → 同时挂着的连接数冲高 → 顶破 512。

> **优化不会解决问题，它只会把墙推到下一层。**

### 改了哪儿

代码不改。**压测用户数 800 → 400**（400 个 socket 在 512 以内）。

---

## 阶段 9：基线复现失败 → 修测量方法

### 现象

```text
16:12  同一份代码、400 用户  →  2491 / 2491 / 2112
16:41  完全相同的配置        →  1877 / 1735
```

**25% 的抖动，比要测的效应还大。** 之前那些"差 17%""差 2.6%"的结论全部作废。

### 判断：三个噪声来源

| 来源 | 说明 |
|---|---|
| **爬坡占了 1/3** | `-u 400 -r 40` 要 10 秒爬满，而总时长只有 30 秒 |
| **客户端 CPU 饱和** | 一出现 `CPU usage above 90%`，压测机就变成运气游戏 |
| **多次压测同时跑** | 三个 Locust 一起压 = 1200 用户，测的是混合体 |

### 改了哪儿（改的是命令，不是代码）

| 项 | 改前 | 改后 |
|---|---|---|
| 爬坡 | `-r 40`（10 秒） | **`-r 200`（2 秒）** |
| 时长 | `-t 30s` | **`-t 50s`** |
| 次数 | 1 次 | **3 次取中位数** |
| 数据 | 手抄终端 | **`--csv perf/x1`** 落盘 |
| 执行 | 多个终端同时跑 | **串行**（一条命令用 `;` 串联） |
| 环境 | 随便 | **插电源 + 高性能模式** |

### 结果

| | 修之前 | 修之后 |
|---|---|---|
| 三次方差 | 25% | **2.7%** |
| 中位数 | — | **2281** |
| 三次原始值 | — | 2318.8 / 2281.0 / 2252.6 |

### 判读规则也跟着升级

> **不看百分比大小，看两组数据的区间有没有重叠。**

```
journal：2253 ──── 2319
WAL    ：                2356 ──── 2377
                          ↑ 空出 37，六次测量一次都没交叉 → 差异是真的
```

---

## 阶段 10：SQLite 切 WAL（A/B 实验）

### 假设

> 两个服务进程共享同一个 `shop.db`，每次 `SELECT` 都要在文件上加共享锁 →
> 切到 WAL（读不加文件锁，读 `-shm` 共享内存）后吞吐应该上升。

### 改了哪儿（三处）

**① `get_conn()` 里加一行**：

```python
conn = sqlite3.connect(DB, timeout=10)
conn.execute("PRAGMA journal_mode=WAL")   # 读不加文件锁
_local.conn = conn
```

**② 新建 `练习/journal_mode.py`**（A/B 切换工具，切换前必须先停服务）：

```python
conn = sqlite3.connect(DB, timeout=10)
result = conn.execute(f"PRAGMA journal_mode={mode}").fetchone()[0]
```

**③ `.gitignore` 补 WAL 的伴生文件**：

```
mock/*.db-wal
mock/*.db-shm
```

### 结果

| 配置 | 三次 RPS | 中位数 | P50 | P95 |
|---|---|---|---|---|
| rollback journal | 2252.6 / 2281.0 / 2318.8 | 2281 | 13ms | 40ms |
| **WAL** | 2355.6 / 2375.5 / 2377.0 | **2376** | **8ms** | 30ms |

**吞吐 +4.1%，P50 −38%。区间不重叠，差异为真。**

### 为什么只有 4%

单进程时锁争用本来就小（4 条连接在同一个进程里，锁大部分在内存里解决）。WAL 真正救的是**跨进程**场景，而那个场景我们测不了——客户端先到顶。

**但延迟降了 38%**，这个比吞吐更能说明机制：每个请求少了一次文件锁的系统调用。

---

# 附录 A：所有报错与处理

| # | 报错 / 现象 | 真正原因 | 怎么处理 |
|---|---|---|---|
| 1 | `pip install locust` 报 `OSError: No such file or directory 'pip-unpack-...whl'` | Windows 临时目录被占用 / 权限 | `pip install --no-cache-dir locust`；或改 `TMP`/`TEMP`；或换清华源 |
| 2 | `locust --version` 提示找不到命令 | 脚本目录不在 PATH | 用 `python -m locust` 代替 |
| 3 | 起了两个服务，`--host 5001` 全部 ConnectionRefused | **`port` 变量算出来了，但 `serve(port=5000)` 没用它**；而 Windows 的 `SO_REUSEADDR` 让两个进程绑同一端口都不报错 | 改成 `serve(..., port=port, ...)`；用 `netstat -ano \| findstr :5000` 看到两个 PID 才发现 |
| 4 | 压 800 用户 `ValueError: too many file descriptors in select()` | Windows `select()` 上限 512 句柄 | 降到 400 用户（或用 Linux/epoll） |
| 5 | `--processes 4` 报 "not supported in Windows" | Locust 的 `--processes` 不支持 Windows | 手动开多个终端，各自 `--host` 指向不同端口 |
| 6 | 改了 `get_conn()` 后 pytest 全绿，但压测报 closed database | 漏删某个 `conn.close()`，第二次调用才炸 | 全局搜 `conn.close()` 清零 |
| 7 | 跑 `pytest --env=mock` 一片红（8 failed / 14 error） | mock 只实现了 5 个路由，其余接口返回 HTML 404；且 mock 的 `/auth/login` 不校验密码 | 只跑 `testcases/test_db.py` 那 3 条；`test_db.py` 加 `@pytest.mark.mock`，用 `-m mock` 筛选 |
| 8 | 三条数据库用例在外网环境失败（创建 500、删除期望 404 实得 400、`${db_product_id}` 无值） | 对方服务器把创建接口搞挂了，删除的错误码也改了；第三条是前两条的连锁反应 | 不是自己的问题；对外网依赖要么打 marker 隔离，要么改成前置失败就 skip |
| 9 | 三个终端同时压，x3 出现 738 次 ConnectionRefused | 1200 用户打一个服务，超过 512 句柄，**服务进程直接崩了** | 压测必须串行；一条命令用 `;` 串联 |

---

# 附录 B：最终在用的命令

**起服务**（`mock/app.py` 支持传端口）：

```
python mock/app.py          # 5000
python mock/app.py 5001     # 5001
```

**单次压测**（固定协议）：

```
python -m locust -f perf/locustfile.py --headless -u 400 -r 200 -t 50s --host http://127.0.0.1:5000 --only-summary --csv perf/x1
```

**连续三轮（串行，取中位数）**：

```
for i in 1 2 3; do python -m locust -f perf/locustfile.py --headless -u 400 -r 200 -t 50s --host http://127.0.0.1:5000 --only-summary --csv perf/x$i; sleep 3; done
```

**清库**：

```
curl -X POST http://127.0.0.1:5000/reset
```

**回归**：

```
python -m pytest -q --env=mock testcases/test_db.py
```

---

# 附录 C：遗留问题（下次必须处理）

1. **GET 的绝对值是在空表下测的。** 数据库被 `/reset` 清空后一直是 0 行，返回空数组比返回 50 行 JSON 便宜。所以 2281 / 2376 偏乐观，**对外报数前必须在有数据的前提下重测一次**（已塞 50 行，待重测）。
2. **横向扩展 ×2 无法在本机验证。** 单进程 waitress ≈2380，单客户端 Locust ≈2500，两个天花板只差 5%。要么上分布式压测，要么换 `wrk` / `hey`。
3. **`pytest.ini` 里的 `mock` marker 至今没有用例真的使用**，`-m mock` 筛不出东西。
4. **GET 之外的接口没压过**：`POST /products`（写锁）、`DELETE`、`/reset`（全表删除，会锁表）。
