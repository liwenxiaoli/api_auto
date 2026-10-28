# api_auto —— 接口自动化练习项目

用 `requests + pytest + yaml` 搭的接口自动化框架，练手站点是
[escuelajs](https://api.escuelajs.co)（一个公开的 REST 示例 API，支持登录、商品增删改查）。

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
│  ├─ extractor.py     # extract：按 jsonpath 规则把响应里的值存进变量池
│  ├─ runner.py        # 通用用例执行器：一份 yaml 数据 → 一次完整调用
│  ├─ yaml_util.py     # 读 data/ 下的用例数据
│  ├─ json_util.py     # jsonpath 取值工具
│  └─ logger.py        # 日志（logs/api.log）
├─ data/               # 用例数据（yaml）
├─ testcases/          # 用例
├─ docs/               # 学习指南、练习说明
├─ conftest.py         # fixture：ctx / client / token / auth_client + --env 参数
├─ run.py              # 一键跑：清结果 → pytest → allure generate
├─ pytest.ini
└─ requirements.txt
```

## 四个 fixture 的区别（conftest.py）

| fixture | 作用域 | 用途 |
|---|---|---|
| `ctx` | session | 变量池，配合 extract 与 `${}` 占位符使用 |
| `client` | session | 未登录的客户端，查公开接口用 |
| `token` | session | 只登录一次，所有用例共用 |
| `auth_client` | function | 带 `Authorization` 头的客户端，测需要登录的接口 |

用例里要哪个就把名字写进参数，pytest 自动注入 —— 不用手动创建。

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
