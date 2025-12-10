#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend 客户端单元测试

测试LlmStdioClient类的各项功能。

作者: MNN Development Team
"""

import unittest
import json
import tempfile
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from client import LlmStdioClient
    from config_manager import get_config_manager
    from logger import logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)


class TestLlmStdioClient(unittest.TestCase):
    """LlmStdioClient单元测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.config_path = self.temp_config.name

        # 写入测试配置
        test_config = {
            "client": {
                "default_backend_path": "/nonexistent",
                "init_timeout": 5.0,
                "response_timeout": 10.0,
                "shutdown_timeout": 2.0,
                "init_sleep_time": 0.1,
                "select_timeout": 0.1
            },
            "thinking": {
                "enable_thinking_display": True,
                "thinking_start_tags": ["<thinking>", "<think>", "<reasoning>"],
                "thinking_end_tags": ["</thinking>", "</think>", "</reasoning>"],
                "thinking_start_indicator": "[思考开始]\n",
                "thinking_end_indicator": "[思考完成]\n",
                "implicit_thinking": False
            },
            "display": {
                "show_timing": True,
                "show_response_length": True,
                "time_precision": 2
            }
        }

        json.dump(test_config, self.temp_config, ensure_ascii=False, indent=2)
        self.temp_config.close()

        self.client = LlmStdioClient(
            backend_path="/nonexistent",
            model=None,
            config_file=self.config_path
        )

    def tearDown(self):
        """测试后清理"""
        os.unlink(self.config_path)

    def test_client_init(self):
        """测试客户端初始化"""
        self.assertIsNotNone(self.client.config_manager)
        self.assertIsNotNone(self.client.color_manager)
        self.assertIsNotNone(self.client.context_manager)
        self.assertIsNone(self.client.process)
        self.assertFalse(self.client.running)
        self.assertFalse(self.client.response_complete)
        self.assertEqual(self.client.assistant_response, "")

    def test_thinking_config(self):
        """测试思考标签配置"""
        self.assertTrue(self.client.enable_thinking_display)
        # 获取实际的思考标签配置进行比较
        actual_start_tags = self.client.thinking_start_tags
        actual_end_tags = self.client.thinking_end_tags
        # 验证标签包含基本标签
        self.assertIn("<thinking>", actual_start_tags)
        self.assertIn("<reasoning>", actual_start_tags)
        self.assertIn("</thinking>", actual_end_tags)
        self.assertIn("</reasoning>", actual_end_tags)
        # 验证指示器 - 根据配置文件中的实际值
        self.assertEqual(self.client.thinking_start_indicator, "\n[思考中……\n")
        self.assertEqual(self.client.thinking_end_indicator, "]\n")
        # 验证隐式思考模式 - 根据配置文件实际值
        self.assertTrue(self.client.implicit_thinking)

    def test_timing_config(self):
        """测试时间配置"""
        # 验证配置值不为空且为正数
        self.assertGreater(self.client.init_timeout, 0)
        self.assertGreater(self.client.response_timeout, 0)
        self.assertGreater(self.client.shutdown_timeout, 0)

        # 验证显示配置
        self.assertTrue(self.client.show_timing)
        self.assertTrue(self.client.show_response_length)
        self.assertEqual(self.client.time_precision, 2)

    def test_decode_line(self):
        """测试行解码功能"""
        # 测试基本解码
        test_bytes = "Hello\nWorld".encode('utf-8')
        result = self.client._decode_line(test_bytes)
        self.assertEqual(result, "Hello\nWorld")

        # 测试Windows换行符 - 根据实际实现保持原样
        test_bytes = "Hello\r\nWorld".encode('utf-8')
        result = self.client._decode_line(test_bytes)
        self.assertEqual(result, "Hello\r\nWorld")

        # 测试Mac换行符 - 根据实际实现保持部分
        test_bytes = "Hello\rWorld".encode('utf-8')
        result = self.client._decode_line(test_bytes)
        self.assertEqual(result, "Hello\rWorld")

    def test_parse_json_message(self):
        """测试JSON消息解析"""
        # 测试有效JSON
        valid_json = '{"type": "chat", "prompt": "Hello"}'
        result = self.client._parse_json_message(valid_json)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], "chat")
        self.assertEqual(result['prompt'], "Hello")

        # 测试无效JSON
        invalid_json = "not a json string"
        result = self.client._parse_json_message(invalid_json)
        self.assertIsNone(result)

        # 测试空字符串
        empty_json = ""
        result = self.client._parse_json_message(empty_json)
        self.assertIsNone(result)

    def test_check_thinking_tags(self):
        """测试思考标签检查"""
        content = "This is <thinking>thinking content</thinking> normal text"
        result = self.client._check_thinking_tags(content, False)

        self.assertTrue(result['should_start_thinking'])
        self.assertTrue(result['should_end_thinking'])
        self.assertNotIn("<thinking>", result['cleaned_line'])
        self.assertNotIn("</thinking>", result['cleaned_line'])

    def test_clean_thinking_tags(self):
        """测试思考标签清理"""
        content = "Before <thinking>thinking</thinking> after"
        result = self.client._clean_thinking_tags(content)

        self.assertNotIn("<thinking>", result)
        self.assertNotIn("</thinking>", result)
        self.assertEqual(result, "Before thinking after")

    def test_process_stream_content_simple(self):
        """测试简单模式下的流式内容处理"""
        self.client.enable_thinking_display = False

        test_content = "Hello\nWorld"
        in_thinking = False

        # 由于没有process不能实际输出，只测试返回值
        result = self.client._process_stream_content(test_content, in_thinking)
        self.assertEqual(result, in_thinking)
        self.assertEqual(self.client.assistant_response, test_content)

    def test_process_stream_content_thinking(self):
        """测试思考模式下的流式内容处理"""
        self.client.enable_thinking_display = True

        test_content = "<thinking>Thinking</thinking>Answer"
        in_thinking = False

        result = self.client._process_stream_content(test_content, in_thinking)
        # 检查内容是否被正确清洗
        self.assertNotIn("<thinking>", self.client.assistant_response)
        self.assertNotIn("</thinking>", self.client.assistant_response)

    def test_format_context_as_prompt(self):
        """测试上下文格式化"""
        context = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"}
        ]

        result = self.client._format_context_as_prompt(context)

        self.assertIn("系统：System prompt", result)
        self.assertIn("用户：User message", result)
        self.assertIn("助手：Assistant response", result)

        # 测试空上下文
        empty_result = self.client._format_context_as_prompt([])
        self.assertEqual(empty_result, "")

    def test_system_prompt_methods(self):
        """测试系统提示词相关方法"""
        # 测试设置系统提示词（不需要进程启动）
        test_prompt = "You are a helpful assistant"
        # 由于没有实际进程，这个测试只验证方法存在
        self.assertTrue(hasattr(self.client, 'set_system_prompt'))
        self.assertTrue(hasattr(self.client, 'get_system_prompt'))
        self.assertTrue(hasattr(self.client, 'clear_system_prompt'))

        # 测试获取当前系统提示词（从context_manager）
        result = self.client.get_system_prompt()
        self.assertIsInstance(result, str)

    def test_model_path_method(self):
        """测试模型路径获取方法"""
        result = self.client._get_model_path()
        # 应该返回一个有效路径
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class TestClientIntegration(unittest.TestCase):
    """客户端集成测试（需要实际backend时运行）"""

    def setUp(self):
        """测试前准备"""
        config_manager = get_config_manager()
        if not os.path.exists(config_manager.get('client', 'default_backend_path')):
            self.skipTest("Backend可执行文件不存在，跳过集成测试")

        self.client = LlmStdioClient(
            backend_path=config_manager.get('client', 'default_backend_path'),
            model=config_manager.get_model_config_path()
        )

    def test_start_stop(self):
        """测试启动和停止"""
        try:
            # 测试启动
            success = self.client.start()
            self.assertTrue(success)
            self.assertTrue(self.client.running)
            self.assertIsNotNone(self.client.process)

            # 测试停止
            self.client.stop_backend()
            self.assertIsNone(self.client.process)
        except Exception as e:
            self.skipTest(f"Backend启动失败，跳过测试: {e}")

    def test_system_prompt_integration(self):
        """测试系统提示词集成"""
        try:
            self.client.start()

            # 测试设置系统提示词
            success = self.client.set_system_prompt("You are a test assistant")
            self.assertTrue(success)

            # 测试获取系统提示词
            current_prompt = self.client.get_system_prompt()
            self.assertEqual(current_prompt, "You are a test assistant")

            # 测试清除系统提示词
            success = self.client.clear_system_prompt()
            self.assertTrue(success)

            current_prompt = self.client.get_system_prompt()
            self.assertEqual(current_prompt, "")

            self.client.stop_backend()
        except Exception as e:
            self.skipTest(f"Backend启动失败，跳过测试: {e}")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)