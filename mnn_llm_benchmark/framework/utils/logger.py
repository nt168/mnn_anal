#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的日志配置和管理功能
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any
from utils.project import ProjectPath
from utils.exceptions import ConfigError


class LoggerManager:
    """日志管理器"""

    _loggers = {}  # 缓存已创建的logger

    def __init__(self):
        """
        初始化日志管理器
        从系统配置获取所有日志配置
        """
        # 导入系统配置
        from config.system import SystemConfig

        try:
            self._system_config = SystemConfig()
        except Exception as e:
            raise ConfigError(f"无法初始化系统配置: {e}")

        self.logging_config = self._system_config.get_logging_config()
        self.project_root = ProjectPath.get_project_root()

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取或创建logger实例

        Args:
            name: logger名称

        Returns:
            配置好的logger实例

        Raises:
            ConfigError: 无法初始化系统配置时
        """
        # 创建临时实例以获取系统配置
        temp_manager = cls()  # 这会初始化系统配置

        # 直接使用系统配置
        final_config = temp_manager._system_config.get_logging_config()

        logger_key = f"{name}_{id(final_config)}"

        if logger_key not in cls._loggers:
            logger = cls._create_logger_internal(name, final_config)
            cls._loggers[logger_key] = logger

        return cls._loggers[logger_key]

    @classmethod
    def clear_logger_cache(cls):
        """清除logger缓存，强制重新创建"""
        cls._loggers.clear()

    @classmethod
    def _create_logger_internal(cls, name: str, config: Dict[str, Any]) -> logging.Logger:
        """
        内部方法：创建配置好的logger

        Args:
            name: logger名称
            config: 日志配置

        Returns:
            配置好的logger实例

        Raises:
            ValueError: 日志路径配置无效时
        """
        # 获取日志级别
        log_level_name = config.get('level', 'INFO').upper()
        log_level = getattr(logging, log_level_name, logging.INFO)

        # 使用系统配置获取日志文件的完整绝对路径
        from config.system import SystemConfig
        system_config = SystemConfig()
        log_path = system_config.get_log_path()

        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(log_level)

        # 清除已有的handlers以避免重复
        logger.handlers.clear()

        # 添加文件handler
        cls._add_file_handler(logger, log_path, config)

        # 添加控制台handler（如果启用）
        if config.get('console', True):
            cls._add_console_handler(logger, config)

        return logger

    @classmethod
    def _add_file_handler(cls, logger: logging.Logger, log_path: Path, config: Dict[str, Any]):
        """添加文件handler（强制使用轮换）"""
        # 每日轮换一个日志文件
        # 固定使用每日午夜轮换
        when = 'midnight'
        backup_count = config.get('rotation_backup_count', 7)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_path,
            when=when,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # 文件handler应该继承全局级别，而不是限制级别
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别信息

        file_format = config.get('format',
                                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

    @classmethod
    def _add_console_handler(cls, logger: logging.Logger, config: Dict[str, Any]):
        """添加控制台handler"""
        console_handler = logging.StreamHandler()

        # 控制台日志级别
        console_level_name = config.get('console_level', 'ERROR').upper()
        console_level = getattr(logging, console_level_name, logging.ERROR)
        console_handler.setLevel(console_level)

        # 控制台格式
        console_format = config.get('console_format',
                                   '%(levelname)s: %(message)s')
        console_formatter = logging.Formatter(console_format)
        console_handler.setFormatter(console_formatter)

        logger.addHandler(console_handler)

    @staticmethod
    def configure_logging_for_module(module_name: str) -> logging.Logger:
        """
        为特定模块配置日志

        Args:
            module_name: 模块名称

        Returns:
            配置好的logger
        """
        return LoggerManager.get_logger(module_name)

    def __repr__(self) -> str:
        return f"LoggerManager(log_dir={self.log_dir}, config={self.config})"