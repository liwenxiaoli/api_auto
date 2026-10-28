"""变量池：extract 机制的地基。

它只干两件事：
    1. 存：上一条接口取出来的值（token、商品 id...）放进一个公共字典
    2. 换：把用例里写的 ${token} 换成字典里的真实值

为什么需要它？
    以前关联接口是这么写的（写在 Python 里）：
        token = resp.json()["access_token"]
        client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})
    这种写法的 token 只活在这一个函数里。

    一旦用例数据搬到 yaml 里，就没人给你写上面那行 Python 了 ——
    所以需要一个"公共存钱罐"：谁都能往里存，谁都能从里取。
"""
import re

from common import functions
from common.logger import logger

# 匹配 ${xxx} 的正则：
#   \$   匹配美元符号（前面加 \ 是因为 $ 在正则里有特殊含义）
#   \{ \} 匹配左右花括号
#   ([^}]+)  括号里的内容就是变量名，[^}] 表示"不是右括号的任何字符"
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")

# 匹配"函数调用"的写法：gen_phone()、random_str(8)
FUNC_CALL = re.compile(r"^([a-zA-Z_]\w*)\((.*)\)$")


class Context:
    """全局共享的变量池（一个测试会话一个实例）。"""

    def __init__(self):
        self.data = {}               # 真正存变量的字典
        self.pending_cleanups = []   # 待清理的数据（测试结束时统一删掉）

    def set(self, key, value):
        """往池子里存一个变量。"""
        self.data[key] = value

    def get(self, key, default=None):
        """从池子里取一个变量；取不到就返回 default，不报错。"""
        return self.data.get(key, default)

    def render(self, obj):
        """把 obj 里面所有 ${xxx} 换成真实值。

        支持三种结构：
            str   "Bearer ${token}"  -> "Bearer eyJhbGci..."
            dict  {"id": "${pid}"}   -> {"id": 123}
            list  ["${a}", "${b}"]   -> ["x", "y"]
        其它类型（数字、布尔、None）原样返回。
        """
        if isinstance(obj, str):
            return self._render_str(obj)
        if isinstance(obj, dict):
            return {key: self.render(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self.render(item) for item in obj]
        return obj

    def _render_str(self, text):
        """替换一个字符串里的占位符。"""
        # 情况一：整个字符串就只是一个占位符（比如 "${product_id}"）
        # 这时保留变量原来的类型 —— id 在池子里是数字 123，就别变成 "123"
        matched = PLACEHOLDER.fullmatch(text)
        if matched:
            return self._lookup(matched.group(1))

        # 情况二：占位符只是字符串的一部分（比如 "Bearer ${token}"）
        # 这种情况结果一定是字符串，所以统一转成 str 再拼
        def replace_one(match):
            return str(self._lookup(match.group(1)))

        return PLACEHOLDER.sub(replace_one, text)

    def _lookup(self, key):
        """按名字取值；如果名字带括号，就当成热加载函数去调用。"""
        key = key.strip()

        # ${gen_phone()}、${random_str(8)} —— 热加载：执行到这一刻才现算
        func_match = FUNC_CALL.match(key)
        if func_match:
            return self._call_func(func_match.group(1), func_match.group(2))

        if key not in self.data:
            raise KeyError(
                f"占位符 ${{{key}}} 没有值。变量池里现在只有：{list(self.data.keys())}"
            )
        return self.data[key]

    def _call_func(self, name, args_str):
        """调用 common/functions.py 里的函数（只能调这个模块里定义的）。"""
        func = getattr(functions, name, None)
        if func is None or not callable(func):
            available = [
                n for n in dir(functions)
                if not n.startswith("_") and callable(getattr(functions, n))
            ]
            raise AttributeError(f"热加载函数 {name} 不存在。可用的有：{available}")

        args = [self._parse_arg(a) for a in args_str.split(",")] if args_str.strip() else []
        value = func(*args)
        logger.info("热加载 %s(%s) -> %s", name, args_str, value)
        return value

    def _parse_arg(self, raw):
        """把参数字符串转成 Python 值：'8' -> 8，'abc' -> 'abc'。"""
        s = raw.strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
            return s[1:-1]
        try:
            return int(s)
        except ValueError:
            return s

    def add_cleanup(self, item):
        """登记一条清理任务：测试全部结束后统一执行，保证数据不残留。"""
        self.pending_cleanups.append(item)

    def __str__(self):
        return f"Context({self.data})"
