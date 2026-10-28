"""14：文件读写 + json —— 第6周 extract 机制要用的基础。"""
import json
from pathlib import Path

p = Path("练习/output.json")

# 写：把 Python 字典变成 JSON 文本存到文件
data = {"token": "abc123", "user": "张三"}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# 读：把文件里的 JSON 文本变回 Python 字典
back = json.loads(p.read_text(encoding="utf-8"))
print("读回来:", back)
print("取字段:", back["token"])

# 这两句的区别
print(type(json.dumps(data)))   # str   —— 要写进文件/发请求用这个
print(type(back))               # dict  —— 要在代码里取值用这个
