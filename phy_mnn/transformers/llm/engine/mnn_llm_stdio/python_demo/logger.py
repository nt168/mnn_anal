#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 日志记录模块

提供统一的日志记录功能，支持文件和控制台输出。

作者: MNN Development Team
"""

import logging
import os
from typing import Optional


class Logger:
    """简单日志记录器"""

    def __init__(self, log_file: str = "mnn_llm_demo.log", name: str = "MNN_LLM_Demo"):
        """
        初始化日志记录器

        Args:
            log_file: 日志文件路径
            name: 日志记录器名称
        """
        # 确保日志目录存在
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 清除现有handlers

        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # 记录所有级别

            # 控制台handler（只显示错误）
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)

            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def debug(self, message: str, source: Optional[str] = None):
        """记录调试信息"""
        if source:
            self.logger.debug(f"[{source}] {message}")
        else:
            self.logger.debug(message)

    def info(self, message: str, source: Optional[str] = None):
        """记录一般信息"""
        if source:
            self.logger.info(f"[{source}] {message}")
        else:
            self.logger.info(message)

    def error(self, message: str, source: Optional[str] = None):
        """记录错误信息"""
        if source:
            self.logger.error(f"[{source}] {message}")
        else:
            self.logger.error(message)

    def warning(self, message: str, source: Optional[str] = None):
        """记录警告信息"""
        if source:
            self.logger.warning(f"[{source}] {message}")
        else:
            self.logger.warning(message)


# 全局日志实例
logger = Logger()