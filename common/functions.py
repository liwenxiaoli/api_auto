"""热加载函数库：yaml 里写 ${函数名()} ，执行到那一刻才现算。

为什么需要它？
    有些数据每次跑必须不一样：手机号、订单号、随机标题。
    写死在 yaml 里，第二次跑就会被服务端拒绝（"已存在"）。

用法（写在 yaml 里）：
    phone: "${gen_phone()}"          -> 1 开头的 11 位手机号
    order_no: "${timestamp()}"       -> 当前秒级时间戳
    title: "auto-${random_str(8)}"   -> auto-a3f9k2m1

安全提醒：
    只有本文件里定义的函数能被调用（common/context.py 里做了限制），
    yaml 里写 ${os.system(...)} 之类的不会被执行。
"""
import random
import string
import time
import uuid


def timestamp():
    """当前秒级时间戳（10 位整数）。"""
    return int(time.time())


def timestamp_ms():
    """当前毫秒级时间戳（13 位整数）。"""
    return int(time.time() * 1000)


def gen_phone():
    """随机生成一个 1 开头的 11 位手机号（练习用，不是真号段）。"""
    return "1" + "".join(random.choices(string.digits, k=10))


def random_str(n=6):
    """随机小写字母 + 数字组成的字符串，默认 6 位。"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=int(n)))


def uuid_hex():
    """32 位无横线的 uuid。"""
    return uuid.uuid4().hex
