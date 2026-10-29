# api_auto —— 接口自动化练习项目

![接口自动化测试](https://github.com/liwenxiaoli/api_auto/actions/workflows/api-test.yml/badge.svg)

用 `requests + pytest + yaml` 搭的接口自动化框架，练手站点是
[escuelajs](https://api.escuelajs.co)（一个公开的 REST 示例 API，支持登录、商品增删改查）。

**29 条用例，接口用例全部数据驱动**：用例只描述"调什么、期望什么"，执行逻辑写在框架里。

| 用例文件 | 数据文件 | 条数 |
|---|---|---|
| `test_auth.py` | `data/auth_cases.yaml` | 4（登录成功/失败、带 token、不带 token） |
| `test_product.py` | `data/product_cases.yaml` | 8（分页、关键字、详情、异常、创建+查询） |
| `test_extract.py` | `data/extract_cases.yaml` | 6（extract 关联 + 热加载 + 清理） |
| `test_sign.py` | — | 7（签名工具单测，不联网） |
| `test_my_first.py` | — | 4（第 1 课手写用例，保留作对比） |

## 怎么跑

```bash
# 装依赖（系统 Python 已装全的话可跳过）
pip install -r requirements.txt

# 跑全部用例
pytest

# 只跑登录模块
pytest testcases/test_auth.py

# 切环境跑（dev / test，配置在 config/config.yaml）
pytest --env=test

# 一键跑 + 出 Allure 报告（推荐：会先清掉上一轮的旧结果）
python run.py
python run.py --env=test
python run.py --case testcases/test_extract.py
```

> 说明：本机的 `D:\python\python.exe` 已经装好了全部依赖，
> PyCharm 里把解释器选成它就能直接跑，不用新建虚拟环境。

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
```

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

## CI：GitHub Actions 自动跑

`.github/workflows/api-test.yml` 配置了三种触发：推代码到 main、提 PR、**每天定时（北京时间 10:00）**，
也可以在 GitHub 网页上手动点 Run workflow。

跑完会把 html 报告和 allure 原始数据打包成 artifact 上传（`if: always()` 保证失败也上传）。
README 顶部的徽章就是它的运行状态。

## 目录说明

```
api_auto/
├─ config/
│  ├─ config.yaml      # environments：dev / test 两套环境（地址、超时、账号）
│  └─ settings.py      # Config 对象：读 yaml + 按 --env 切换环境
├─ common/
│  ├─ client.py        # HttpClient：requests.Session 封装（拼地址、超时、日志、渲染占位符）
│  ├─ context.py       # 变量池：存/取变量，把 ${token} 换成真实值
│  ├─ functions.py     # 热加载函数：yaml 里写 ${gen_phone()} 时现调现算
│  ├─ sign.py          # 签名工具：参数排序 + 拼密钥 + md5（有独立单元测试）
│  ├─ extractor.py     # extract：按 jsonpath 规则把响应里的值存进变量池
│  ├─ runner.py        # 通用用例执行器：一份 yaml 数据 → 一次完整调用
│  ├─ asserter.py      # 统一断言：相等 / contains / not_empty / gt / lt / 整体断言
│  ├─ yaml_util.py     # 读 data/ 下的用例数据
│  ├─ json_util.py     # jsonpath 取值工具
│  └─ logger.py        # 日志（logs/api.log）
├─ data/               # 用例数据（yaml）
├─ testcases/          # 用例
├─ .github/workflows/  # GitHub Actions：推代码/每天定时自动跑
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

执行一条用例的固定 5 步（见 `common/runner.py`）：
`渲染占位符 → 发请求 → 断言状态码 → extract 提取 → 断言 expect 字段`。
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

## 练习站点的已知"坑"（都是实测出来的）

- `GET /products?limit=1` **必须同时传 offset**才生效，否则返回全部数据
- `PUT /products/{id}`（更新）目前返回 **500**，接口本身有问题 —— 所以用例里没写更新场景
- 查询不存在的商品返回 **400**（正常应该是 404），测试用例里按 `in (400, 404)` 断言
- 创建商品必须带 token，不带会返回 400
- **公共数据会被别人删**：`GET /products/1` 这类写死 id 的用例随时可能变 400，
  正确做法是先查列表拿一个真实存在的 id 再用（见 `testcases/test_product.py::test_detail`）
- 请求头里**不能写中文**（会报 `UnicodeEncodeError`）

这些"坑"本身就是接口测试的价值所在：文档写的和实际的往往不一样。
