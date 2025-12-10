#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
彩带输出模块单元测试

测试 color_output 模块的各项功能。

作者: MNN Development Team
"""

import unittest
import io
import os
import sys
from unittest.mock import patch

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from color_output import MessageColor, get_color_manager, print_system, print_user, print_assistant, print_error, print_timing
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)


class TestMessageColor(unittest.TestCase):
    """MessageColor单元测试"""

    def setUp(self):
        """测试前准备"""
        self.color_manager = MessageColor()

    def test_color_manager_init(self):
        """测试颜色管理器初始化"""
        self.assertIsNotNone(self.color_manager)

    def test_get_color_manager_singleton(self):
        """测试颜色管理器单例"""
        manager1 = get_color_manager()
        manager2 = get_color_manager()
        self.assertIs(manager1, manager2)

    def test_print_functions(self):
        """测试打印函数"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            # 测试系统消息打印
            print_system("System message")
            output = mock_stdout.getvalue()
            self.assertIn("System message", output)

    def test_print_user_assistant_functions(self):
        """测试用户和助手消息打印"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            # 测试用户消息打印
            print_user("User message")
            output = mock_stdout.getvalue()
            self.assertIn("User message", output)

            # 清空缓冲区
            mock_stdout.seek(0)
            mock_stdout.truncate(0)

            # 测试助手消息打印
            print_assistant("Assistant response")
            output = mock_stdout.getvalue()
            self.assertIn("Assistant response", output)

    def test_print_error_function(self):
        """测试错误消息打印"""
        # 直接测试函数调用不抛出异常
        try:
            print_error("Error message")
            # 如果没有异常发生则测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"print_error抛出异常: {e}")

    def test_print_timing_function(self):
        """测试计时信息打印"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_timing(15.3)  # 修正参数类型
            output = mock_stdout.getvalue()
            self.assertIn("15.3", output)

    def test_manager_methods(self):
        """测试MessageColor的方法"""
        # 测试各种打印方法不抛出异常
        try:
            self.color_manager.print_user_message("User test")
            self.color_manager.print_assistant_message("Assistant test")
            self.color_manager.print_error("Error test")
            # 如果没有异常则测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"MessageColor方法抛出异常: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)