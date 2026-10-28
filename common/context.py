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

# 匹配 ${xxx} 的正则：
#   \$   匹配美元符号（前面加 \ 是因为 $ 在正则里有特殊含义）
#   \{ \} 匹配左右花括号
#   ([^}]+)  括号里的内容就是变量名，[^}] 表示"不是右括号的任何字符"
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


class Context:
    """全局共享的变量池（一个测试会话一个实例）。"""

    def __init__(self):
        self.data = {}          # 真正存东西的字典

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
        """按名字取变量，取不到就抛一个能看懂的错。"""
        if key not in self.data:
            raise KeyError(
                f"占位符 ${{{key}}} 没有值。变量池里现在只有：{list(self.data.keys())}"
            )
        return self.data[key]

    def __str__(self):
        return f"Context({self.data})"
