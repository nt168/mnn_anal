#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 彩色输出模块

提供丰富的彩色输出功能，区分不同类型的消息。
支持终端颜色和格式化输出。

作者: MNN Development Team
"""

import sys
import os
from typing import Optional, Any
from enum import Enum

# 检测终端是否支持颜色
def supports_color() -> bool:
    """
    检测当前终端是否支持颜色输出

    Returns:
        bool: 是否支持颜色
    """
    # 检查是否为真实终端
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # 检查NO_COLOR环境变量
    if os.getenv("NO_COLOR"):
        return False

    # 检查FORCE_COLOR环境变量
    if os.getenv("FORCE_COLOR"):
        return True

    # 检测常见的支持颜色的终端
    term = os.getenv("TERM", "").lower()
    if term in ("xterm", "xterm-256color", "screen", "tmux", "linux", "ansi", "color"):
        return True

    # Windows 10+ 通常也支持ANSI颜色
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # 获取控制台模式
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(mode))
            # 检查是否启用虚拟终端序列
            return (mode.value & 0x0004) != 0
        except:
            return False

    return False


class ColorType(Enum):
    """颜色类型枚举"""
    RESET = 0

    # 颜色
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    # 亮色
    BRIGHT_BLACK = 90
    BRIGHT_RED = 91
    BRIGHT_GREEN = 92
    BRIGHT_YELLOW = 93
    BRIGHT_BLUE = 94
    BRIGHT_MAGENTA = 95
    BRIGHT_CYAN = 96
    BRIGHT_WHITE = 97

    # 背景颜色
    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGENTA = 45
    BG_CYAN = 46
    BG_WHITE = 47

    # 背景亮色
    BG_BRIGHT_BLACK = 100
    BG_BRIGHT_RED = 101
    BG_BRIGHT_GREEN = 102
    BG_BRIGHT_YELLOW = 103
    BG_BRIGHT_BLUE = 104
    BG_BRIGHT_MAGENTA = 105
    BG_BRIGHT_CYAN = 106
    BG_BRIGHT_WHITE = 107


class FormatType(Enum):
    """格式类型枚举"""
    BOLD = 1
    UNDERLINE = 4
    ITALIC = 3
    STRIKETHROUGH = 9
    RESET = 0


class MessageColor:
    """定义各种消息类型的颜色配置"""

    def __init__(self, enable_colors: bool = None):
        """
        初始化颜色配置

        Args:
            enable_colors: 是否启用颜色，None为自动检测
        """
        if enable_colors is None:
            enable_colors = supports_color()

        self.enable_colors = enable_colors

        # 预定义颜色方案
        self.colors = {
            "system": (ColorType.CYAN, FormatType.BOLD),           # 系统消息
            "user": (ColorType.GREEN, None),                      # 用户输入
            "assistant": (ColorType.BRIGHT_GREEN, None),            # 助手一般输出
            "thinking": (ColorType.YELLOW, None),                 # 助手思考内容
            "error": (ColorType.RED, FormatType.BOLD),            # 错误信息
            "warning": (ColorType.YELLOW, FormatType.BOLD),       # 警告信息
            "success": (ColorType.GREEN, FormatType.BOLD),        # 成功信息
            "info": (ColorType.CYAN, None),                       # 信息提示
            "timing": (ColorType.MAGENTA, None),                  # 时间信息
            "prompt": (ColorType.GREEN, FormatType.BOLD),         # 提示符
            "separator": (ColorType.BRIGHT_BLACK, None),          # 分隔线
            "debug": (ColorType.BRIGHT_BLACK, None),              # 调试信息
        }

    def _build_ansi_code(self, color: ColorType, format_type: Optional[FormatType] = None) -> str:
        """
        构建ANSI颜色编码

        Args:
            color: 颜色类型
            format_type: 格式类型

        Returns:
            ANSI编码字符串
        """
        if not self.enable_colors:
            return ""

        codes = [color.value]
        if format_type:
            codes.append(format_type.value)

        return f"\033[{';'.join(map(str, codes))}m"

    def colorize(self, text: str, message_type: str,
                 custom_color: Optional[ColorType] = None,
                 custom_format: Optional[FormatType] = None) -> str:
        """
        为文本添加颜色

        Args:
            text: 原始文本
            message_type: 消息类型（预定义类型）
            custom_color: 自定义颜色（覆盖预定义）
            custom_format: 自定义格式（覆盖预定义）

        Returns:
            彩色文本
        """
        if not self.enable_colors:
            return text

        # 获取颜色配置
        if custom_color is None or custom_format is None:
            if message_type not in self.colors:
                # 未知类型，使用默认颜色
                color, format_type = ColorType.WHITE, None
            else:
                color, format_type = self.colors[message_type]
                custom_color = custom_color or color
                custom_format = custom_format or format_type

        # 构建ANSI编码
        start_code = self._build_ansi_code(custom_color, custom_format)
        end_code = self._build_ansi_code(ColorType.RESET)

        return f"{start_code}{text}{end_code}"

    def print_colored(self, text: str, message_type: str = "info",
                      end: str = "\n", flush: bool = False,
                      stream: Any = None):
        """
        直接打印彩色文本

        Args:
            text: 文本内容
            message_type: 消息类型
            end: 行结束符
            flush: 是否立即刷新
            stream: 输出流，默认为sys.stdout
        """
        if stream is None:
            stream = sys.stdout

        colored_text = self.colorize(text, message_type)
        print(colored_text, end=end, file=stream, flush=flush)

    def print_thinking_start(self):
        """打印思考开始标记"""
        self.print_colored("[思考中...", message_type="thinking", end="", flush=True)

    def print_thinking_end(self):
        """打印思考结束标记"""
        self.print_colored("] [思考完成]", message_type="thinking")

    def print_separator(self, char: str = "=", length: int = 50):
        """
        打印分隔线

        Args:
            char: 分隔符字符
            length: 分隔线长度
        """
        print()  # 确保换行
        self.print_colored(char * length, message_type="separator")

    def print_user_message(self, message: str):
        """打印用户消息"""
        self.print_colored(f"用户: {message}", message_type="user")

    def print_assistant_message(self, message: str):
        """打印助手消息"""
        self.print_colored(f"助手: {message}", message_type="assistant")

    def print_system_message(self, message: str):
        """打印系统消息"""
        self.print_colored(f"系统: {message}", message_type="system")

    def print_stream_start(self):
        """打印流式输出开始"""
        self.print_colored("[开始流式输出]", message_type="info", end="", flush=True)

    def print_stream_end(self):
        """打印流式输出结束"""
        self.print_colored(" [完成]", message_type="success")

    def print_error(self, message: str):
        """打印错误信息"""
        self.print_colored(f"错误: {message}", message_type="error")

    def print_warning(self, message: str):
        """打印警告信息"""
        self.print_colored(f"警告: {message}", message_type="warning")

    def print_success(self, message: str):
        """打印成功信息"""
        self.print_colored(f"成功: {message}", message_type="success")

    def print_timing(self, seconds: float, operation: str = "操作"):
        """打印时间信息"""
        if seconds < 1.0:
            timing_text = f"{operation}耗时: {seconds*1000:.0f}毫秒"
        else:
            timing_text = f"{operation}耗时: {seconds:.2f}秒"
        self.print_colored(timing_text, message_type="timing")

    def print_prompt(self, text: str, end: str = " "):
        """打印提示符"""
        self.print_colored(text, message_type="prompt", end=end, flush=True)

    def disable_colors(self):
        """禁用颜色输出"""
        self.enable_colors = False

    def enable_colors_auto(self):
        """自动检测并启用颜色输出"""
        self.enable_colors = supports_color()


# 全局颜色管理器实例
_color_manager = None


def get_color_manager(enable_colors: bool = None) -> MessageColor:
    """
    获取全局颜色管理器实例

    Args:
        enable_colors: 是否启用颜色，None为自动检测

    Returns:
        颜色管理器实例
    """
    global _color_manager
    if _color_manager is None:
        _color_manager = MessageColor(enable_colors)
    return _color_manager


# 便捷函数
def colorize(text: str, message_type: str,
             custom_color: Optional[ColorType] = None,
             custom_format: Optional[FormatType] = None) -> str:
    """为文本添加颜色的便捷函数"""
    return get_color_manager().colorize(text, message_type, custom_color, custom_format)


def print_colored(text: str, message_type: str = "info", **kwargs):
    """打印彩色文本的便捷函数"""
    return get_color_manager().print_colored(text, message_type, **kwargs)


def print_user(message: str):
    """打印用户消息的便捷函数"""
    return get_color_manager().print_user_message(message)


def print_assistant(message: str):
    """打印助手消息的便捷函数"""
    return get_color_manager().print_assistant_message(message)


def print_system(message: str):
    """打印系统消息的便捷函数"""
    return get_color_manager().print_system_message(message)


def print_error(message: str):
    """打印错误信息的便捷函数"""
    return get_color_manager().print_error(message)


def print_timing(seconds: float, operation: str = "操作"):
    """打印时间信息的便捷函数"""
    return get_color_manager().print_timing(seconds, operation)


def separator(char: str = "=", length: int = 50):
    """打印分隔线的便捷函数"""
    return get_color_manager().print_separator(char, length)