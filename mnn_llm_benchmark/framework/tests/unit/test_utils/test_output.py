#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ColorOutput 单元测试
测试彩色输出工具的各种功能
"""

import sys
from pathlib import Path

# 使用标准包导入方式
try:
    from framework.utils.output import ColorOutput
except ImportError:
    # 如果直接作为脚本运行，使用绝对导入
    framework_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(framework_dir))
    from utils.output import ColorOutput


class TestColorOutput:
    """ColorOutput测试类"""

    def test_color_constants_coverage(self):
        """测试颜色常量覆盖"""
        # 验证所有预定义颜色都存在
        required_colors = [
            'HEADER', 'BLUE', 'CYAN', 'GREEN', 'WARNING', 'FAIL', 'BOLD', 'UNDERLINE', 'ENDC',
            'GRAY', 'WHITE', 'BLACK', 'RED', 'YELLOW'
        ]

        for color_name in required_colors:
            assert color_name in ColorOutput.COLORS, f"缺少颜色常量: {color_name}"

    def test_colored_method(self):
        """测试基础彩色方法"""
        text = "测试文本"

        # 测试已知颜色
        green_text = ColorOutput.colored(text, 'GREEN')
        assert "\033[" in green_text  # 包含ANSI转义序列
        assert "测试文本" in green_text

        # 测试无效颜色（返回带结束符的原文本）
        invalid_text = ColorOutput.colored(text, 'INVALID_COLOR')
        assert "测试文本" in invalid_text and invalid_text.endswith("\033[0m")

    def test_preset_color_methods(self):
        """测试预定义颜色方法"""
        text = "状态文本"

        # 测试所有预定义颜色方法
        header = ColorOutput.header(text)
        assert "状态文本" in header

        blue = ColorOutput.blue(text)
        assert "状态文本" in blue

        cyan = ColorOutput.cyan(text)
        assert "状态文本" in cyan

        green = ColorOutput.green(text)
        assert "状态文本" in green

        yellow = ColorOutput.yellow(text)
        assert "状态文本" in yellow

        red = ColorOutput.red(text)
        assert "状态文本" in red

        gray = ColorOutput.gray(text)
        assert "状态文本" in gray

        white = ColorOutput.white(text)
        assert "状态文本" in white

    def test_bold_formatting(self):
        """测试粗体格式"""
        text = "粗体文本"

        # 普通彩色
        normal_colored = ColorOutput.colored(text, 'BLUE')

        # 粗体彩色（当前实现中bold参数没有实际效果）
        bold_colored = ColorOutput.colored(text, 'BLUE', bold=True)

        # 当前的实现中bold参数不会改变格式，两者应该相等
        assert normal_colored == bold_colored

        # 测试其他粗体方法
        bold_text = ColorOutput.bold(text)
        assert "粗体文本" in bold_text
        assert "\033[" in bold_text  # 应该包含BOLD颜色码

    def test_status_coloring(self):
        """测试状态着色"""
        text = "结果文本"

        # 测试所有状态方法
        success_text = ColorOutput.success(text)
        assert "结果文本" in success_text

        error_text = ColorOutput.error(text)
        assert "结果文本" in error_text

        warning_text = ColorOutput.warning(text)
        assert "结果文本" in warning_text

        info_text = ColorOutput.info(text)
        assert "结果文本" in info_text

    def test_styled_methods(self):
        """测试样式方法"""
        text = "样式文本"

        # 高亮文本（青色粗体）
        highlight = ColorOutput.highlight(text)
        assert "样式文本" in highlight

        # 次要信息（灰色）
        subtle = ColorOutput.subtle(text)
        assert "样式文本" in subtle

    def test_status_automatic_coloring(self):
        """测试状态自动着色"""
        text = "测试状态"

        # 各种状态类型
        success_result = ColorOutput.status(text, "success")
        error_result = ColorOutput.status(text, "error")
        warning_result = ColorOutput.status(text, "warning")
        info_result = ColorOutput.status(text, "default")

        # 验证返回类型
        assert isinstance(success_result, str)
        assert isinstance(error_result, str)
        assert isinstance(warning_result, str)
        assert isinstance(info_result, str)

        # 验证文本内容
        assert "测试状态" in success_result
        assert "测试状态" in error_result

    def test_strip_color_functionality(self):
        """测试移除颜色的功能"""
        # 原始带颜色的文本
        colored_text = ColorOutput.green("成功状态")

        # 移除颜色后应该返回纯文本
        stripped_text = ColorOutput.strip_colors(colored_text)

        # 验证所有ANSI码都被移除
        assert "\033[" not in stripped_text
        assert "成功状态" in stripped_text

    def test_is_color_supported_method(self):
        """测试彩色支持检测"""
        # 这个方法依赖于环境，只验证能正常调用
        result = ColorOutput.is_color_supported()
        assert isinstance(result, bool)

    def test_rainbow_functionality(self):
        """测试彩虹色功能"""
        text = "彩虹测试"

        # 彩虹文本应该逐字符着色
        rainbow_text = ColorOutput.rainbow(text)
        # 应该包含ANSI转义序列
        assert "\033[" in rainbow_text
        # 彩虹文本应该比原文本长（因为添加了颜色代码）
        assert len(rainbow_text) > len(text)
        # 验证所有原文字符都包含在结果中（分散在各处）
        for char in text:
            assert char in rainbow_text

    def test_unicode_handling(self):
        """测试Unicode和中文支持"""
        # 中文字符
        chinese_text = "测试中文"
        chinese_colored = ColorOutput.green(chinese_text)
        assert "测试" in chinese_colored and "中文" in chinese_colored

        # 英文字符
        english_text = "Test English"
        english_colored = ColorOutput.green(english_text)
        assert "Test" in english_colored and "English" in english_colored

        # 混合文本
        mixed_text = "测试Mixed混合Text"
        mixed_colored = ColorOutput.success(mixed_text)
        assert "测试" in mixed_colored and "Mixed" in mixed_colored and "Text" in mixed_colored


