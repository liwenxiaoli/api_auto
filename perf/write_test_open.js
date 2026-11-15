// k6 压测脚本（开放模型 / 定速灌入）：POST /products 写操作
//
// 为什么要有这个文件：
//   write_test.js 用的是固定用户数（closed model），吞吐恒等于 用户数 ÷ 延迟，
//   延迟一涨吞吐自动下跌，永远看不到服务端天花板。
//   本文件改用 constant-arrival-rate：k6 每秒固定灌 N 个请求，
//   服务端扛不住时表现为「延迟暴涨 / 失败增加」，而灌入速率不变 —— 天花板就露出来了。
//
// 运行（在项目根目录，RATE 是每秒请求数）：
//   tools/k6-v2.4.0-windows-amd64/k6.exe run -e RATE=250 perf/write_test_open.js
//
// 可选环境变量：
//   RATE      每秒请求数（默认 300）
//   DURATION  持续时长（默认 40s）
//   BASE_URL  靶子地址（默认 http://127.0.0.1:5000）

import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:5000";
const RATE = Number(__ENV.RATE || 300);
const DURATION = __ENV.DURATION || "40s";

export const options = {
  // 关闭响应体解析，减少压测机自身开销（我们只关心状态码）
  discardResponseBodies: true,
  scenarios: {
    write: {
      executor: "constant-arrival-rate",
      rate: RATE,
      timeUnit: "1s",
      duration: DURATION,
      // 预分配 100 个 VU 起步，最多允许扩到 maxVUs
      // maxVUs 不能设太高：每个在途请求占一条连接，waitress 单进程在 Windows 上
      // 受 select() 512 句柄限制，超过会直接抛 ValueError 崩掉
      preAllocatedVUs: 100,
      maxVUs: 480,
    },
  },
};

export default function () {
  const payload = JSON.stringify({
    name: `perf-${Math.floor(Math.random() * 1e9)}`,
    price: Math.floor(Math.random() * 100) + 1,
  });

  const resp = http.post(`${BASE}/products`, payload, {
    headers: { "Content-Type": "application/json" },
  });

  // 判据与 write_test.js / locustfile_write.py 保持一致：只有 201 算成功
  check(resp, {
    "status is 201": (r) => r.status === 201,
  });
}
