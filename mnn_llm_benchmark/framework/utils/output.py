#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩色输出工具模块

提供统一的彩色文本输出功能，支持多种颜色和样式。
用于终端界面的美观和信息展示。
"""

import re
import sys
import os

class ColorOutput:
    """彩色输出工具类

    提供统一的彩色文本输出功能，支持多种颜色和样式。
    使用ANSI转义序列实现终端彩色显示。
    """

    # ANSI颜色码定义
    COLORS = {
        'HEADER': '\033[95m',       # 紫色 - 标题
        'BLUE': '\033[94m',         # 蓝色 - 链接、路径
        'CYAN': '\033[96m',         # 青色 - 信息
        'GREEN': '\033[92m',        # 绿色 - 成功、完成
        'WARNING': '\033[93m',      # 黄色 - 警告、变量
        'FAIL': '\033[91m',         # 红色 - 失败、错误
        'BOLD': '\033[1m',          # 粗体
        'UNDERLINE': '\033[4m',     # 下划线
        'ENDC': '\033[0m',          # 结束标记
        # 额外的灰色和轻量颜色
        'GRAY': '\033[90m',         # 灰色 - 次要信息
        'WHITE': '\033[97m',        # 白色
        'BLACK': '\033[90m',        # 黑色（与gray相同）
        'RED': '\033[1;91m',        # 亮红色
        'YELLOW': '\033[1;93m',     # 亮黄色
        'GREEN': '\033[1;92m',      # 亮绿色
    }

    @classmethod
    def colored(cls, text: str, color: str, bold: bool = False) -> str:
        """
        返回带颜色的文本

        Args:
            text: 要着色的文本
            color: 颜色名称，从COLORS中选择
            bold: 是否使用粗体

        Returns:
            带ANSI颜色码的文本
        """
        color_code = cls.COLORS.get(color, '')

        if bold:
            return f"{color_code}{text}{cls.COLORS['ENDC']}"
        else:
            return f"{color_code}{text}{cls.COLORS['ENDC']}"

    # 预定义的常用颜色方法
    @classmethod
    def header(cls, text: str) -> str:
        """标题颜色（紫色）"""
        return cls.colored(text, 'HEADER')

    @classmethod
    def blue(cls, text: str) -> str:
        """蓝色 - 用于路径、链接"""
        return cls.colored(text, 'BLUE')

    @classmethod
    def cyan(cls, text: str) -> str:
        """青色 - 用于信息展示"""
        return cls.colored(text, 'CYAN')

    @classmethod
    def green(cls, text: str) -> str:
        """绿色 - 用于成功状态"""
        return cls.colored(text, 'GREEN')

    @classmethod
    def yellow(cls, text: str) -> str:
        """黄色 - 用于警告、变量名"""
        return cls.colored(text, 'WARNING')

    @classmethod
    def red(cls, text: str) -> str:
        """红色 - 用于错误、失败"""
        return cls.colored(text, 'FAIL')

    @classmethod
    def gray(cls, text: str) -> str:
        """灰色 - 用于次要信息"""
        return cls.colored(text, 'GRAY')

    @classmethod
    def white(cls, text: str) -> str:
        """白色"""
        return cls.colored(text, 'WHITE')

    @classmethod
    def bold(cls, text: str) -> str:
        """粗体文本"""
        return cls.colored(text, 'BOLD')

    @classmethod
    def success(cls, text: str) -> str:
        """成功信息（绿色粗体）"""
        return cls.colored(text, 'GREEN', bold=True)

    @classmethod
    def error(cls, text: str) -> str:
        """错误信息（红色粗体）"""
        return cls.colored(text, 'FAIL', bold=True)

    @classmethod
    def warning(cls, text: str) -> str:
        """警告信息（黄色）"""
        return cls.colored(text, 'WARNING')

    @classmethod
    def info(cls, text: str) -> str:
        """信息提示（蓝色）"""
        return cls.colored(text, 'BLUE')

    @classmethod
    def subtle(cls, text: str) -> str:
        """次要信息（灰色）"""
        return cls.colored(text, 'GRAY')

    @classmethod
    def highlight(cls, text: str) -> str:
        """高亮文本（青色粗体）"""
        return cls.colored(text, 'CYAN', bold=True)

    @classmethod
    def status(cls, text: str, status_type: str) -> str:
        """
        根据状态类型返回不同的颜色文本

        Args:
            text: 状态文本
            status_type: 状态类型 (success, error, warning, info, default)

        Returns:
            对应颜色的状态文本
        """
        status_types = {
            'success': cls.success,
            'error': cls.error,
            'warning': cls.warning,
            'info': cls.info,
            'default': lambda x: x
        }

        return status_types.get(status_type, status_types['default'])(text)

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """移除文本中的所有ANSI颜色码"""
        # 匹配ANSI转义序列的正则表达式
        ansi_escape = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @classmethod
    def is_color_supported(cls) -> bool:
        """检查当前终端是否支持彩色输出"""
        try:
            # 检查TERM是否为已知的彩色终端
            term = os.environ.get('TERM', '').lower()
            if 'color' in term or '256' in term or 'xterm' in term:
                return True
            # 检查COLORTERM环境变量
            colorterm = os.environ.get('COLORTERM', '').lower()
            if 'truecolor' in colorterm or '24bit' in colorterm:
                return True
        except:
            pass
        return False

    @classmethod
    def rainbow(cls, text: str) -> str:
        """彩虹色文字（用于特殊展示）"""
        colors = ['RED', 'YELLOW', 'GREEN', 'CYAN', 'BLUE', 'MAGENTA']
        if not hasattr(cls, '_color_cycle_index'):
            cls._color_cycle_index = 0

        chars = []
        for i, char in enumerate(text):
            color = colors[i % len(colors)]
            chars.append(cls.colored(char, color))

        return ''.join(chars)


# 便捷的别名函数
def colored(text, color, bold=False):
    """ColorOutput.colored的简化函数"""
    return ColorOutput.colored(text, color, bold)

def green(text):
    """绿色文本"""
    return ColorOutput.green(text)

def red(text):
    """红色文本"""
    return ColorOutput.red(text)

def yellow(text):
    """黄色文本"""
    return ColorOutput.yellow(text)

def blue(text):
    """蓝色文本"""
    return ColorOutput.blue(text)

def cyan(text):
    """青色文本"""
    return ColorOutput.cyan(text)

def gray(text):
    """灰色文本"""
    return ColorOutput.gray(text)

def bold(text):
    """粗体文本"""
    return ColorOutput.bold(text)

def success(text):
    """成功信息"""
    return ColorOutput.success(text)

def error(text):
    """错误信息"""
    return ColorOutput.error(text)

def warning(text):
    """警告信息"""
    return ColorOutput.warning(text)

def info(text):
    """信息提示"""
    return ColorOutput.info(text)

def subtle(text):
    """次要信息"""
    return ColorOutput.subtle(text)