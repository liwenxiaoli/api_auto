import statistics

# 100 个请求：99 个 100ms，1 个 10000ms（10 秒）
data = [100] * 99 + [10000]

print("请求数:", len(data))
print("平均值:", statistics.mean(data))
print("最大值:", max(data))
s = sorted(data)          # 排好序，从慢到快响应时间
print("P50:", s[49])      # 第 50% 位置
print("P95:", s[94])      # 第 95% 位置
print("P99:", s[98])      # 第 99% 位置
print("P100:", s[99])     # 最后一个 = 最大值

