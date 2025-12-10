#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理器单元测试

测试 ConfigManager 类的各项功能。

作者: MNN Development Team
"""

import unittest
import tempfile
import os
import sys
import toml
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config_manager import ConfigManager, ClientConfig, DisplayConfig, ChatConfig, LoggingConfig
    from logger import logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)


class TestConfigManager(unittest.TestCase):
    """ConfigManager单元测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.toml")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_default_config_creation(self):
        """测试默认配置创建"""
        # 测试没有配置文件时使用默认配置
        config_manager = ConfigManager(config_file=None)

        self.assertIsNotNone(config_manager._client_config)
        self.assertIsNotNone(config_manager._display_config)
        self.assertIsNotNone(config_manager._chat_config)
        self.assertIsNotNone(config_manager._logging_config)

    def test_config_file_loading(self):
        """测试配置文件加载"""
        # 创建测试配置文件
        test_config = {
            "client": {
                "default_backend_path": "/test/backend",
                "init_timeout": 20.0,
                "response_timeout": 80.0
            },
            "display": {
                "show_timing": False,
                "show_response_length": True,
                "time_precision": 3
            },
            "chat": {
                "default_prompt": "Test prompt",
                "default_batch_file": "test_batch.txt"
            },
            "logging": {
                "log_level": "DEBUG",
                "enable_file_log": False
            }
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            toml.dump(test_config, f)

        config_manager = ConfigManager(config_file=self.config_file)

        # 验证配置已加载
        self.assertEqual(config_manager.get('client', 'default_backend_path'), "/test/backend")
        self.assertEqual(config_manager.get('client', 'init_timeout'), 20.0)
        self.assertEqual(config_manager.get('display', 'show_timing'), False)
        self.assertEqual(config_manager.get('chat', 'default_prompt'), "Test prompt")

    def test_get_methods(self):
        """测试get方法"""
        config_manager = ConfigManager()

        # 测试获取存在的配置
        backend_path = config_manager.get('client', 'default_backend_path')
        self.assertIsInstance(backend_path, str)
        self.assertTrue(len(backend_path) > 0)

        # 测试获取不存在的配置项
        result = config_manager.get('nonexistent', 'key')
        self.assertIsNone(result)

    def test_get_model_config_path(self):
        """测试模型配置路径获取"""
        config_manager = ConfigManager()
        model_path = config_manager.get_model_config_path()

        self.assertIsInstance(model_path, str)
        self.assertTrue(len(model_path) > 0)

    def test_client_config_class(self):
        """测试客户端配置数据类"""
        config = ClientConfig(
            default_backend_path="/test/backend",
            init_timeout=15.0
        )

        self.assertEqual(config.default_backend_path, "/test/backend")
        self.assertEqual(config.init_timeout, 15.0)

    def test_display_config_class(self):
        """测试显示配置数据类"""
        config = DisplayConfig(
            show_timing=False,
            time_precision=1
        )

        self.assertFalse(config.show_timing)
        self.assertEqual(config.time_precision, 1)

    def test_chat_config_class(self):
        """测试聊天配置数据类"""
        config = ChatConfig(
            default_prompt="Custom prompt",
            show_progress=False
        )

        self.assertEqual(config.default_prompt, "Custom prompt")
        self.assertFalse(config.show_progress)

    def test_logging_config_class(self):
        """测试日志配置数据类"""
        config = LoggingConfig(
            log_file="test.log",
            log_level="ERROR"
        )

        self.assertEqual(config.log_file, "test.log")
        self.assertEqual(config.log_level, "ERROR")


if __name__ == '__main__':
    unittest.main(verbosity=2)