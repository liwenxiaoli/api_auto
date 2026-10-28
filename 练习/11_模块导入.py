"""11：模块导入 —— from common.client import HttpClient 到底怎么找着的。"""
import json
import sys
from pathlib import Path

print(json.dumps({"a": 1}, ensure_ascii=False))
print(Path("api_auto") / "data" / "x.yaml")
print("搜索起点(第1条):", sys.path[0])
print("搜索起点(第2条):", sys.path[1])

# 三种写法，效果一样，只是名字不同
import json as j                      # 起别名
from json import dumps                # 只拿其中一个
print(j.dumps({"b": 2}), dumps({"c": 3}))
