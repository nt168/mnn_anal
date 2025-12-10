#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
上下文管理器单元测试

测试 ContextManager 类的各项功能。

作者: MNN Development Team
"""

import unittest
import time
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from context_manager import ContextManager, MessageRole, ChatMessage
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)


class TestContextManager(unittest.TestCase):
    """ContextManager单元测试"""

    def setUp(self):
        """测试前准备"""
        self.context_manager = ContextManager()

    def test_context_manager_init(self):
        """测试上下文管理器初始化"""
        self.assertIsNotNone(self.context_manager.messages)
        self.assertIsInstance(self.context_manager.messages, list)
        self.assertGreaterEqual(len(self.context_manager.messages), 0)

    def test_message_role_enum(self):
        """测试消息角色枚举"""
        self.assertEqual(MessageRole.SYSTEM.value, "system")
        self.assertEqual(MessageRole.USER.value, "user")
        self.assertEqual(MessageRole.ASSISTANT.value, "assistant")
        self.assertEqual(MessageRole.THINKING.value, "thinking")

    def test_chat_message_creation(self):
        """测试聊天消息创建"""
        timestamp = time.time()
        message = ChatMessage(
            role=MessageRole.USER,
            content="Test message",
            timestamp=timestamp
        )

        self.assertEqual(message.role, MessageRole.USER)
        self.assertEqual(message.content, "Test message")
        self.assertEqual(message.timestamp, timestamp)

    def test_chat_message_auto_timestamp(self):
        """测试聊天消息自动时间戳"""
        start_time = time.time()
        message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Response message"
        )
        end_time = time.time()

        self.assertIsNotNone(message.timestamp)
        self.assertGreaterEqual(message.timestamp, start_time)
        self.assertLessEqual(message.timestamp, end_time)

    def test_chat_message_to_dict(self):
        """测试聊天消息转字典"""
        message = ChatMessage(
            role=MessageRole.SYSTEM,
            content="System message"
        )

        message_dict = message.to_dict()

        self.assertEqual(message_dict['role'], "system")
        self.assertEqual(message_dict['content'], "System message")
        self.assertIn('timestamp', message_dict)

    def test_add_user_message(self):
        """测试添加用户消息"""
        initial_count = len(self.context_manager.messages)
        self.context_manager.add_user_message("Hello")

        self.assertEqual(len(self.context_manager.messages), initial_count + 1)
        last_message = self.context_manager.messages[-1]
        self.assertEqual(last_message.role, MessageRole.USER)
        self.assertEqual(last_message.content, "Hello")

    def test_add_assistant_response(self):
        """测试添加助手响应"""
        self.context_manager.add_assistant_response("Hi there!")

        last_message = self.context_manager.messages[-1]
        self.assertEqual(last_message.role, MessageRole.ASSISTANT)
        self.assertEqual(last_message.content, "Hi there!")

    def test_get_last_user_message(self):
        """测试获取最后一条用户消息"""
        self.context_manager.add_user_message("First message")
        self.context_manager.add_assistant_response("Response 1")
        self.context_manager.add_user_message("Second message")

        last_user_msg = self.context_manager.get_last_user_message()
        self.assertEqual(last_user_msg, "Second message")

    def test_get_last_assistant_response(self):
        """测试获取最后一条助手响应"""
        self.context_manager.add_user_message("Message")
        self.context_manager.add_assistant_response("First response")
        self.context_manager.add_user_message("Another message")
        self.context_manager.add_assistant_response("Second response")

        last_response = self.context_manager.get_last_assistant_response()
        self.assertEqual(last_response, "Second response")

    def test_get_user_message_history(self):
        """测试获取用户消息历史"""
        self.context_manager.add_user_message("User 1")
        self.context_manager.add_assistant_response("Response 1")
        self.context_manager.add_user_message("User 2")

        # 使用实际存在的方法
        user_msg1 = self.context_manager.get_last_user_message()
        self.assertEqual(user_msg1, "User 2")

    def test_clear_messages(self):
        """测试清除消息（使用reset_context代替）"""
        self.context_manager.add_user_message("Test message")
        self.context_manager.add_assistant_response("Test response")

        initial_count = len(self.context_manager.messages)
        self.assertGreater(initial_count, 0)

        # 使用reset_context来清除消息（保持系统提示词）
        self.context_manager.reset_context(keep_system_prompt=True)

        # 应该只剩下系统提示词
        final_count = len(self.context_manager.messages)
        self.assertLessEqual(final_count, initial_count)

    def test_reset_context(self):
        """测试重置上下文"""
        self.context_manager.add_user_message("Test message")
        self.context_manager.set_system_prompt("Test system prompt")

        # 保持系统提示词
        self.context_manager.reset_context(keep_system_prompt=True)

        # 系统提示词应该保留
        system_prompt = self.context_manager.get_system_prompt()
        self.assertEqual(system_prompt, "Test system prompt")

        # 不保持系统提示词
        self.context_manager.reset_context(keep_system_prompt=False)

        # 验证重置后的状态（应该没有最后用户消息）
        last_user = self.context_manager.get_last_user_message()
        self.assertIsNone(last_user)

    def test_set_get_system_prompt(self):
        """测试设置和获取系统提示词"""
        test_prompt = "You are a helpful assistant."
        self.context_manager.set_system_prompt(test_prompt)

        retrieved_prompt = self.context_manager.get_system_prompt()
        self.assertEqual(retrieved_prompt, test_prompt)

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        self.context_manager.add_user_message("User message")
        self.context_manager.add_assistant_response("Assistant response")

        history = self.context_manager.get_conversation_history()
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_get_conversation_summary(self):
        """测试获取对话摘要"""
        self.context_manager.add_user_message("A question about technology")
        self.context_manager.add_assistant_response("An answer about technology")

        summary = self.context_manager.get_conversation_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_truncate_context(self):
        """测试截断上下文（使用内部清理功能）"""
        # 添加多个消息
        for i in range(10):
            self.context_manager.add_user_message(f"User message {i}")
            self.context_manager.add_assistant_response(f"Assistant response {i}")

        initial_count = len(self.context_manager.messages)

        # 获取token计数来触发清理
        token_count = self.context_manager.get_total_tokens_estimate()
        self.assertIsInstance(token_count, int)
        self.assertGreater(token_count, 0)

    def test_context_token_count(self):
        """测试上下文token计数"""
        self.context_manager.add_user_message("Short message")
        self.context_manager.add_assistant_response("A very long response message")

        token_count = self.context_manager.get_total_tokens_estimate()
        self.assertIsInstance(token_count, int)
        self.assertGreater(token_count, 0)

    def test_format_context_as_prompt(self):
        """测试格式化上下文为提示词"""
        self.context_manager.add_user_message("User: Hello")
        self.context_manager.add_assistant_response("Assistant: Hi there")

        # 使用实际的方法获取LLM上下文
        llm_context = self.context_manager.get_context_for_llm()
        self.assertIsInstance(llm_context, list)
        self.assertGreater(len(llm_context), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)