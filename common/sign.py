"""请求签名工具。

签名是什么？
    客户端和服务端事先约定一个"密钥"（secret，只有两边知道）。
    发请求前，把所有参数按约定规则拼成一个字符串，加上密钥，算一个 md5，
    一起发给服务端。服务端用**同样的规则**再算一遍，对得上才放行。

    两个作用：
        1. 防篡改 —— 参数被改了，签名就对不上
        2. 防乱调 —— 不知道密钥就算不出正确的 sign

    想再防"重放"（别人把请求原样再发一次），就在参数里加时间戳：
        params["timestamp"] = "${timestamp()}"      # 见 common/functions.py

常见的签名规则（各公司不完全一样，这里是通用的一种）：
    1. 去掉 sign 字段本身，去掉空值
    2. 按参数名排序（a-z）—— 这样字典顺序不同也能算出一样的值
    3. 拼成 "k1=v1&k2=v2"
    4. 尾部拼密钥："k1=v1&k2=v2&key=SECRET"
    5. 算 md5，转 32 位小写十六进制

这个模块不依赖网络，所以可以脱离接口单独写单元测试（见 testcases/test_sign.py）。
"""
import hashlib

from common.logger import logger

SIGN_FIELD = "sign"        # 签名值放在哪个字段里
SECRET_KEY = "key"         # 拼接密钥时用的键名


def md5(text):
    """算 md5，返回 32 位小写十六进制字符串。

    text 必须先 encode 成 bytes —— md5 只认字节，不认字符串。
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def build_sign_str(params, secret, exclude=(SIGN_FIELD,)):
    """把参数拼成待签名的原始串（规则见文件顶部 1-4 步）。

    拼出来的串会打进日志 —— 签名对不上时，第一件事就是比对这个串。
    """
    if not secret:
        raise ValueError("签名密钥 secret 不能为空")

    parts = []
    for key in sorted(params.keys()):          # sorted 保证顺序稳定
        if key in exclude:                     # sign 字段不参与自己的计算
            continue
        value = params[key]
        if value is None or value == "":       # 空值不参与
            continue
        parts.append(f"{key}={value}")

    raw = "&".join(parts) + f"&{SECRET_KEY}={secret}"
    logger.info("签名原始串: %s", raw)
    return raw


def md5_sign(params, secret, exclude=(SIGN_FIELD,)):
    """给参数算签名，返回 32 位小写签名值。"""
    return md5(build_sign_str(params, secret, exclude))


def add_sign(params, secret, sign_field=SIGN_FIELD):
    """返回一份**新的**带签名的参数字典（不改原来的字典）。

    为什么返回新的？
        原字典可能还要复用/断言，就地改容易造成"签了一遍又签一遍"的 bug。
    """
    signed = dict(params)
    signed[sign_field] = md5_sign(params, secret)
    logger.info("签名结果 %s = %s", sign_field, signed[sign_field])
    return signed
