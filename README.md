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

# 出 Allure 报告
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
```

> 说明：本机的 `D:\python\python.exe` 已经装好了全部依赖，
> PyCharm 里把解释器选成它就能直接跑，不用新建虚拟环境。

## 目录说明

```
api_auto/
├─ config/
│  ├─ config.yaml      # base_url、超时、账号 —— 改环境只动这里
│  └─ settings.py      # 把 yaml 读成常量供代码使用
├─ common/
│  ├─ client.py        # HttpClient：requests.Session 封装（拼地址、超时、日志）
│  ├─ yaml_util.py     # 读 data/ 下的用例数据
│  ├─ json_util.py     # jsonpath 取值工具
│  └─ logger.py        # 日志（控制台 + logs/api.log）
├─ data/               # 用例数据（yaml）
├─ testcases/          # 用例
├─ conftest.py         # fixture：client / token / auth_client
├─ pytest.ini
└─ requirements.txt
```

## 三个 fixture 的区别（conftest.py）

| fixture | 作用域 | 用途 |
|---|---|---|
| `client` | session | 未登录的客户端，查公开接口用 |
| `token` | session | 只登录一次，所有用例共用 |
| `auth_client` | function | 带 `Authorization` 头的客户端，测需要登录的接口 |

用例里要哪个就把名字写进参数，pytest 自动注入 —— 不用手动创建。

## 练习站点的已知"坑"（都是实测出来的）

- `GET /products?limit=1` **必须同时传 offset**才生效，否则返回全部数据
- `PUT /products/{id}`（更新）目前返回 **500**，接口本身有问题 —— 所以用例里没写更新场景
- 查询不存在的商品返回 **400**（正常应该是 404），测试用例里按 `in (400, 404)` 断言
- 创建商品必须带 token，不带会返回 400

这些"坑"本身就是接口测试的价值所在：文档写的和实际的往往不一样。
