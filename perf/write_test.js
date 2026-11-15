// k6 压测脚本：POST /products 写操作
// 目的：用 Go 的多核能力突破 Locust 客户端 0.92 核的天花板，测服务端真实上限
//
// 与 perf/locustfile_write.py 对齐：
//   - 同样的 payload（name 带随机数，price 1~100）
//   - 同样的成功判据：只有 201 才算成功
//   - 目标都是打满 mock 服务端
//
// 运行（在项目根目录）：
//   tools/k6-v2.4.0-windows-amd64/k6.exe run -u 400 -d 50s perf/write_test.js
//
// 参数说明：
//   -u = 并发虚拟用户数（vus）
//   -d = 持续时间（k6 用 --duration 或 -d）
//   注意：k6 默认会一直跑，必须给 -d 或 -i 指定停止条件

import http from "k6/http";
import { check } from "k6";

// 靶子写死：只压本地 mock（waitress）。和 locustfile 一样，不碰公网
const BASE = "http://127.0.0.1:5000";

// 每个虚拟用户反复执行这个函数
export default function () {
  const payload = JSON.stringify({
    name: `perf-${Math.floor(Math.random() * 1e9)}`,
    price: Math.floor(Math.random() * 100) + 1,
  });

  const params = {
    headers: { "Content-Type": "application/json" },
  };

  const resp = http.post(`${BASE}/products`, payload, params);

  // 只有 201 算成功，和 locustfile_write.py 里 catch_response 判 201 完全一致
  check(resp, {
    "status is 201": (r) => r.status === 201,
  });
}
