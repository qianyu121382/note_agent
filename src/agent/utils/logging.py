"""
配置项目专用的日志记录器。
"""
import logging
import os
import sys

# 1. 从环境变量获取日志级别，默认为 INFO
#    可以通过设置 LOG_LEVEL=DEBUG 来显示更详细的日志
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

# 2. 创建一个全局的 Logger 实例
logger = logging.getLogger("NoteAgent")
logger.setLevel(log_level)

# 3. 如果 logger 还没有 handlers，则为其添加一个
#    这可以防止在多次导入时重复添加 handler
if not logger.handlers:
    # 创建一个流处理器 (StreamHandler)，将日志输出到标准错误 (stderr)
    # 输出到 stderr 是日志记录的最佳实践，可以将日志与程序的标准输出分开
    handler = logging.StreamHandler(sys.stderr)
    
    # 4. 定义日志格式
    # 格式: [LEVEL] [file:line] message
    formatter = logging.Formatter(
        "[%(levelname)s] [%(module)s.py:%(lineno)d] %(message)s"
    )
    handler.setFormatter(formatter)
    
    # 5. 将处理器添加到 logger
    logger.addHandler(handler)

# 确保日志级别设置成功
logger.info(f"Logger initialized with level {log_level_name}")

__all__ = ["logger"]
