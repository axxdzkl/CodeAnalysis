import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """日志管理器"""

    _loggers = {}
    _log_dir = None

    @classmethod
    def setup(cls, log_dir="logs", log_level=logging.INFO, console_output=True):
        """
        初始化日志系统

        Args:
            log_dir: 日志文件存储目录
            log_level: 日志级别
            console_output: 是否输出到控制台
        """
        cls._log_dir = Path(log_dir)
        cls._log_dir.mkdir(exist_ok=True)

        # 创建按日期分类的日志文件
        today = datetime.now().strftime("%Y%m%d")
        log_file = cls._log_dir / f"semantic_deriver_{today}.log"

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 清除已有的处理器
        root_logger.handlers.clear()

        # 日志格式
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 文件处理器 - 详细日志
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 控制台处理器 - INFO及以上级别
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # 创建错误日志文件
        error_file = cls._log_dir / f"semantic_deriver_error_{today}.log"
        error_handler = logging.FileHandler(
            error_file,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

        logging.info("=" * 60)
        logging.info("日志系统初始化完成")
        logging.info(f"日志目录: {cls._log_dir.absolute()}")
        logging.info("=" * 60)

    @classmethod
    def get_logger(cls, name):
        """
        获取指定名称的日志记录器

        Args:
            name: 日志记录器名称，通常使用 __name__

        Returns:
            logging.Logger: 日志记录器实例
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


# 便捷函数
def get_logger(name):
    """获取日志记录器的便捷函数"""
    return Logger.get_logger(name)
