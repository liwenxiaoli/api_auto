"""一键跑测试 + 生成 Allure 报告。

在终端里敲：
    python run.py                      # 跑全部用例（默认环境 dev）并出报告
    python run.py --env=test           # 切到 test 环境跑
    python run.py --case testcases/test_extract.py
    python run.py --no-report          # 只跑测试，不生成报告
    python run.py --open               # 报告生成后自动打开
    python run.py -k login             # -k 这类 pytest 原生参数会原样透传

为什么要有这个脚本？
    每次都手敲 "pytest --alluredir=... && allure generate ..." 既长又容易敲错，
    而且报告目录不会自动清理 —— 上一轮的失败结果会混进这一轮。
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS = BASE_DIR / "reports" / "allure-results"     # pytest 产生的原始数据
REPORT = BASE_DIR / "reports" / "allure-report"       # allure 生成的网页报告
ALLURE_BAT = Path(r"D:\allure-2.29.0\bin\allure.bat")  # 本机 allure 命令行位置


def find_allure():
    """找 allure 命令：优先用本机安装路径，找不到就赌它在 PATH 里。"""
    if ALLURE_BAT.exists():
        return str(ALLURE_BAT)
    return shutil.which("allure") or "allure"


def main():
    parser = argparse.ArgumentParser(description="一键跑接口自动化并生成 Allure 报告")
    parser.add_argument("--env", default=None, help="运行环境，如 dev / test")
    parser.add_argument("--case", default=None, help="只跑指定文件/用例，如 testcases/test_extract.py")
    parser.add_argument("--no-report", action="store_true", help="只跑测试，不生成报告")
    parser.add_argument("--open", dest="open_report", action="store_true", help="报告生成后自动打开")
    opts, extra = parser.parse_known_args()   # extra = 不认识的 pytest 原生参数，原样透传

    # 第 1 步：清掉上一轮的原始结果 —— 否则旧数据会混进新报告
    if RESULTS.exists():
        shutil.rmtree(RESULTS)
    RESULTS.mkdir(parents=True, exist_ok=True)

    # 第 2 步：跑 pytest，让 allure-pytest 把结果写进 RESULTS
    cmd = [
        sys.executable, "-m", "pytest",
        opts.case or "testcases",
        f"--alluredir={RESULTS}",
    ]
    if opts.env:
        cmd.append(f"--env={opts.env}")
    cmd += extra

    print(">>>", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    # 第 3 步：写环境信息，报告首页能看到这轮跑的是哪个环境
    env_name = opts.env or "dev"
    (RESULTS / "environment.properties").write_text(
        f"env={env_name}\n"
        f"python={sys.version.split()[0]}\n"
        f"command={' '.join(cmd)}\n",
        encoding="utf-8",
    )

    if opts.no_report:
        sys.exit(result.returncode)

    # 第 4 步：把原始数据渲染成网页报告
    allure = find_allure()
    gen = f'"{allure}" generate "{RESULTS}" -o "{REPORT}" --clean'
    print(">>>", gen)
    subprocess.run(gen, shell=True, check=True)

    index = REPORT / "index.html"
    print(f"\n报告已生成：{index}")
    if opts.open_report and index.exists():
        serve_report()


def serve_report():
    """起一个本地服务打开报告。

    为什么不能直接双击 index.html？
        Allure 报告是用 fetch 加载 json 的，file:// 协议会被浏览器拦下 → 白屏。
        所以得起一个 http 服务再用浏览器访问。
    """
    import functools
    import threading
    import webbrowser
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(REPORT))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)     # 端口 0 = 让系统随便给一个空端口
    url = f"http://127.0.0.1:{httpd.server_port}/index.html"

    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"报告地址：{url}")
    webbrowser.open(url)
    input("预览服务已启动，看完按回车结束...")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
