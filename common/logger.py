"""日志工具：让用例执行过程留下痕迹。

接口自动化里日志特别重要 ——
接口不像浏览器能截图，一旦失败，你唯一的线索就是日志里的请求和响应。
"""
import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# 避免重复添加 handler（pytest 多次导入时会重复，导致日志打印两遍）
if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

    # 输出到文件（失败后回看，接口自动化唯一的"案发现场"）
    file = logging.FileHandler(LOG_DIR / "api.log", encoding="utf-8")
    file.setFormatter(fmt)
    logger.addHandler(file)

    # 注意：这里故意不加控制台 handler。
    # pytest.ini 里开了 log_cli=true，pytest 会自己把日志按用例分组打印出来。
    # 如果这里再加一个控制台 handler，同一条日志就会出现两遍（你刚才看到的就是）。
