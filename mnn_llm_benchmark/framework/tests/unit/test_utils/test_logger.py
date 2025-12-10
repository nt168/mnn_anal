#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoggerManager单元测试
测试日志管理器的功能
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

# 使用标准包导入方式
from framework.utils.logger import LoggerManager
from framework.utils.exceptions import ConfigError


class TestLoggerManager:
    """LoggerManager测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_logger_basic(self):
        """测试基本logger获取功能"""
        logger = LoggerManager.get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.handlers  # 至少应该有一个handler
        assert len(logger.handlers) >= 1  # 至少应该有一个file handler

    def test_get_logger_with_system_config(self):
        """测试使用系统配置获取logger"""
        logger = LoggerManager.get_logger("test_config")

        assert isinstance(logger, logging.Logger)
        # 应该使用系统配置的默认级别
        assert logger.handlers  # 至少应该有一个handler
        assert len(logger.handlers) >= 1  # 至少应该有一个file handler

    def test_logger_singleton_behavior(self):
        """测试logger缓存行为"""
        logger1 = LoggerManager.get_logger("singleton_test")
        logger2 = LoggerManager.get_logger("singleton_test")

        # 相同名称应该返回相同的logger实例
        assert logger1 is logger2

    def test_get_different_loggers(self):
        """测试获取不同的logger"""
        logger1 = LoggerManager.get_logger("module1")
        logger2 = LoggerManager.get_logger("module2")

        # 不同名称应该返回不同的logger实例
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    
    def test_console_handler_creation(self):
        """测试控制台handler创建"""
        logger = LoggerManager.get_logger("console_test")

        # 应该有控制台handler（如果系统配置启用了控制台输出）
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1

    @patch('framework.config.system.SystemConfig')
    def test_system_config_error_handling(self, mock_system_config):
        """测试系统配置异常处理"""
        mock_system_config.side_effect = Exception("System config error")

        with pytest.raises(ConfigError):
            LoggerManager.get_logger("error_test")

    def test_clear_logger_cache(self):
        """测试清除logger缓存"""
        # 创建logger
        logger1 = LoggerManager.get_logger("cache_test")

        # 检查缓存不为空
        assert len(LoggerManager._loggers) > 0

        # 清除缓存
        LoggerManager.clear_logger_cache()
        assert len(LoggerManager._loggers) == 0

        # 再次获取应该创建新的实例（使用不同名称确保创建新实例）
        logger2 = LoggerManager.get_logger("cache_test_new")
        # 不同的名称应该创建不同的logger
        assert logger1 is not logger2
        assert len(LoggerManager._loggers) == 1

    def test_logger_output_format(self):
        """测试日志输出格式"""
        logger = LoggerManager.get_logger("format_test")

        # 检查handler的格式应该使用系统配置的默认格式
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        for handler in file_handlers:
            formatter = handler.formatter
            # 应该使用系统配置的默认格式
            assert formatter._fmt is not None
            assert "%(asctime)s" in formatter._fmt or "%(levelname)s" in formatter._fmt

    def test_concurrent_logging(self):
        """测试并发日志记录的线程安全性"""
        import threading

        results = []

        def log_task(module_name):
            try:
                logger = LoggerManager.get_logger(module_name)
                logger.info(f"Message from {module_name}")
                results.append(1)
            except Exception:
                pass

        # 创建多个线程同时访问logger
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_task, args=(f"module_{i}",))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=2)

        # 检查结果
        assert len(results) == 5

    def test_configure_logging_for_module(self):
        """测试静态方法配置模块日志"""
        logger = LoggerManager.configure_logging_for_module("static_test")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "static_test"

    