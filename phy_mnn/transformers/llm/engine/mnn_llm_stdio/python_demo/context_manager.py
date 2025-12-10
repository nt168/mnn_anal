#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 上下文管理模块

提供多轮对话的上下文管理功能，包括系统提示词、对话历史、
指令支持等。参考MNN系统的llm_demo实现。

作者: MNN Development Team
"""

import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .logger import logger
    from .color_output import print_system, print_user, print_assistant, print_error
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logger import logger
    from color_output import print_system, print_user, print_assistant, print_error


class MessageRole(Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    THINKING = "thinking"  # 用于标记思考内容


@dataclass
class ChatMessage:
    """聊天消息数据结构"""
    role: MessageRole
    content: str
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """从字典创建消息"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data.get("timestamp")
        )


class ContextManager:
    """多轮对话上下文管理器"""

    def __init__(self,
                 system_prompt: Optional[str] = None,
                 max_history: int = 20,
                 max_token_total: int = 8000,
                 enable_thinking: bool = True):
        """
        初始化上下文管理器

        Args:
            system_prompt: 系统提示词
            max_history: 最大保留的历史消息数
            max_token_total: 最大token总数限制
            enable_thinking: 是否启用思考模式
        """
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.max_history = max_history
        self.max_token_total = max_token_total
        self.enable_thinking = enable_thinking

        # 对话历史
        self.messages: List[ChatMessage] = []

        # 如果有系统提示词，初始化时添加
        if self.system_prompt:
            self.messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content=self.system_prompt
            ))

        # 当前对话状态
        self._current_thinking = ""
        self._in_thinking = False

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return ("你是一个智能助手，请根据用户的问题提供准确、有用的回答。"
                "回答要简洁明了，避免使用过于复杂的术语。如果遇到不确定的内容，"
                "请诚实地说明。")

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        logger.info("添加用户消息")
        self.messages.append(ChatMessage(
            role=MessageRole.USER,
            content=content
        ))
        self._cleanup_old_messages()

    def add_assistant_response(self, content: str, thinking_content: Optional[str] = None) -> None:
        """
        添加助手回复

        Args:
            content: 助手的实际回复内容
            thinking_content: 助手的思考过程内容（如果有）
        """
        # 如果有思考内容且启用思考模式，先添加思考消息
        if thinking_content and self.enable_thinking:
            self.messages.append(ChatMessage(
                role=MessageRole.THINKING,
                content=thinking_content
            ))
            logger.info("添加思考内容")

        # 添加实际回复
        logger.info("添加助手回复")
        self.messages.append(ChatMessage(
            role=MessageRole.ASSISTANT,
            content=content
        ))

        self._cleanup_old_messages()

    def get_conversation_history(self, include_thinking: bool = False) -> List[ChatMessage]:
        """
        获取对话历史

        Args:
            include_thinking: 是否包含思考内容

        Returns:
            消息列表
        """
        if include_thinking:
            return self.messages.copy()

        # 过滤掉思考内容
        return [msg for msg in self.messages if msg.role != MessageRole.THINKING]

    def get_context_for_llm(self, include_system: bool = True, include_thinking: bool = False) -> List[Dict[str, str]]:
        """
        获取适合发送给LLM的上下文格式

        Args:
            include_system: 是否包含系统提示词
            include_thinking: 是否包含思考内容

        Returns:
            LLM格式的上下文列表
        """
        context = []

        for message in self.messages:
            # 过滤思考内容（如果不需要）
            if not include_thinking and message.role == MessageRole.THINKING:
                continue

            # 过滤系统提示词（如果不需要）
            if not include_system and message.role == MessageRole.SYSTEM:
                continue

            context.append({
                "role": message.role.value,
                "content": message.content
            })

        return context

    def start_thinking(self) -> None:
        """开始思考模式"""
        self._in_thinking = True
        self._current_thinking = ""

    def add_thinking_content(self, content: str) -> None:
        """添加思考内容"""
        if self._in_thinking:
            self._current_thinking += content

    def end_thinking(self) -> str:
        """结束思考模式，返回思考内容"""
        thinking = self._current_thinking
        self._current_thinking = ""
        self._in_thinking = False
        return thinking

    def is_thinking(self) -> bool:
        """是否正在进行思考"""
        return self._in_thinking

    def reset_context(self, keep_system_prompt: bool = True) -> None:
        """
        重置上下文

        Args:
            keep_system_prompt: 是否保留系统提示词
        """
        logger.info("重置对话上下文")

        if keep_system_prompt and self.system_prompt:
            # 保留系统提示词
            self.messages = [ChatMessage(
                role=MessageRole.SYSTEM,
                content=self.system_prompt
            )]
        else:
            self.messages = []

        # 重置思考状态
        self._current_thinking = ""
        self._in_thinking = False

    def get_total_tokens_estimate(self) -> int:
        """
        估算当前上下文的token总数（简单估算）

        Returns:
            预估的token数量
        """
        total = 0
        for message in self.messages:
            # 简单估算：英文按1.3个字符/token，中文按1.5个字符/token
            content = message.content
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            other_chars = len(content) - chinese_chars
            tokens = chinese_chars * 1.5 + other_chars * 0.75
            total += int(tokens)

        return total

    def _cleanup_old_messages(self) -> None:
        """清理旧消息以保持上下文大小在限制内"""
        # 检查消息数量限制
        while len(self.messages) > self.max_history:
            # 保留系统提示词，删除最旧的非系统消息
            for i, msg in enumerate(self.messages):
                if msg.role != MessageRole.SYSTEM:
                    removed = self.messages.pop(i)
                    logger.info("删除旧消息")
                    break

        # 检查token总数限制
        if self.max_token_total > 0:
            while self.get_total_tokens_estimate() > self.max_token_total:
                # 删除最旧的消息（保留系统提示词）
                for i, msg in enumerate(self.messages):
                    if msg.role != MessageRole.SYSTEM:
                        removed = self.messages.pop(i)
                        logger.info("因token限制删除消息")
                        break

                # 如果只剩系统提示词还不够小，停止删除
                if len(self.messages) <= 1:
                    break

    def set_system_prompt(self, prompt: str) -> None:
        """
        设置系统提示词

        Args:
            prompt: 新的系统提示词
        """
        self.system_prompt = prompt

        # 如果已有消息，更新系统提示词
        if self.messages and self.messages[0].role == MessageRole.SYSTEM:
            self.messages[0].content = prompt
        else:
            # 在开头添加系统提示词
            self.messages.insert(0, ChatMessage(
                role=MessageRole.SYSTEM,
                content=prompt
            ))

        logger.info(f"系统提示词已更新: {prompt[:50]}...")

    def get_system_prompt(self) -> str:
        """
        获取当前系统提示词

        Returns:
            当前系统提示词
        """
        return self.system_prompt

    def get_last_user_message(self) -> Optional[str]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == MessageRole.USER:
                return msg.content
        return None

    def get_last_assistant_response(self) -> Optional[str]:
        """获取最后一条助手回复"""
        for msg in reversed(self.messages):
            if msg.role == MessageRole.ASSISTANT:
                return msg.content
        return None

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        user_count = sum(1 for msg in self.messages if msg.role == MessageRole.USER)
        assistant_count = sum(1 for msg in self.messages if msg.role == MessageRole.ASSISTANT)
        thinking_count = sum(1 for msg in self.messages if msg.role == MessageRole.THINKING)

        summary = f"对话摘要: {user_count}条用户消息, {assistant_count}条助手回复"
        if thinking_count > 0:
            summary += f", {thinking_count}条思考内容"

        return summary

    def print_conversation_history(self, include_thinking: bool = False) -> None:
        """
        打印对话历史

        Args:
            include_thinking: 是否包含思考内容
        """
        print("=== 对话历史 ===")

        for message in self.messages:
            if not include_thinking and message.role == MessageRole.THINKING:
                continue

            if message.role == MessageRole.SYSTEM:
                print_system(f"系统: {message.content}")
            elif message.role == MessageRole.USER:
                print_user(f"用户: {message.content}")
            elif message.role == MessageRole.ASSISTANT:
                print_assistant(f"助手: {message.content}")
            elif message.role == MessageRole.THINKING:
                # 思考内容用特殊格式展示
                print(f"[思考] {message.content}")
            else:
                print(f"[{message.role.value}] {message.content}")

        print("=== 历史结束 ===")

    def export_context(self, file_path: str, include_thinking: bool = False) -> None:
        """
        导出上下文到文件

        Args:
            file_path: 导出文件路径
            include_thinking: 是否包含思考内容
        """
        data = {
            "messages": [msg.to_dict() for msg in self.messages
                        if include_thinking or msg.role != MessageRole.THINKING],
            "system_prompt": self.system_prompt,
            "timestamp": time.time()
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"上下文已导出到: {file_path}")

    def import_context(self, file_path: str, merge_mode: str = "replace") -> None:
        """
        从文件导入上下文

        Args:
            file_path: 导入文件路径
            merge_mode: 合并模式 ('replace', 'append', 'prepend')
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            imported_messages = [ChatMessage.from_dict(msg) for msg in data["messages"]]

            if merge_mode == "replace":
                self.messages = imported_messages
            elif merge_mode == "append":
                self.messages.extend(imported_messages)
            elif merge_mode == "prepend":
                # 保留系统提示词在开头
                system_msgs = [msg for msg in self.messages if msg.role == MessageRole.SYSTEM]
                other_msgs = [msg for msg in self.messages if msg.role != MessageRole.SYSTEM]
                self.messages = system_msgs + imported_messages + other_msgs
            else:
                raise ValueError(f"不支持的合并模式: {merge_mode}")

            if "system_prompt" in data:
                self.system_prompt = data["system_prompt"]

            self._cleanup_old_messages()
            logger.info(f"上下文已从 {file_path} 导入，模式: {merge_mode}")

        except Exception as e:
            print_error(f"导入上下文失败: {e}")
            raise


# 全局上下文管理器实例
_context_manager = None


def get_context_manager(
    system_prompt: Optional[str] = None,
    max_history: int = 20,
    max_token_total: int = 8000,
    enable_thinking: bool = True,
    reset: bool = False
) -> ContextManager:
    """
    获取全局上下文管理器实例

    Args:
        system_prompt: 系统提示词
        max_history: 最大历史消息数
        max_token_total: 最大token总数
        enable_thinking: 是否启用思考模式
        reset: 是否重置现有实例

    Returns:
        上下文管理器实例
    """
    global _context_manager

    if _context_manager is None or reset:
        _context_manager = ContextManager(
            system_prompt=system_prompt,
            max_history=max_history,
            max_token_total=max_token_total,
            enable_thinking=enable_thinking
        )

    return _context_manager


def reset_context(keep_system_prompt: bool = True) -> None:
    """重置全局上下文"""
    if _context_manager:
        _context_manager.reset_context(keep_system_prompt)