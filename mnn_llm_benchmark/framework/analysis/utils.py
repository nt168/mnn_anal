#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析模块通用工具函数

提供所有分析模块共用的工具函数，避免代码重复
"""

from typing import Dict, Any, Optional


def transform_variable_name(name: str) -> str:
    """
    转换变量名为更友好的显示名称

    Args:
        name: 变量名

    Returns:
        转换后的显示名称
    """
    name_mapping = {
        'n_prompt': '输入序列长度',
        'n_gen': '生成长度',
        'threads': '线程数',
        'precision': '精度',
        'n_repeat': '重复次数'
    }
    return name_mapping.get(name, name)


def transform_english_name(name: str) -> str:
    """
    转换变量名为英文显示名称（用于图表标签）

    Args:
        name: 变量名

    Returns:
        英文显示名称
    """
    english_mapping = {
        'n_prompt': 'Input Sequence Length',
        'n_gen': 'Generation Length',
        'threads': 'Thread Count',
        'precision': 'Precision',
        'n_repeat': 'Repeat Count'
    }
    return english_mapping.get(name, name.title())


def format_analysis_title(result_type: str, x_variable: Optional[str] = None,
                         analysis_type: str = "general") -> str:
    """
    格式化分析标题

    Args:
        result_type: 结果类型
        x_variable: X变量名
        analysis_type: 分析类型 (general, single_variable, simple)

    Returns:
        格式化的标题
    """
    base_title = f"{result_type.upper()} Performance Analysis"

    if analysis_type == "single_variable" and x_variable:
        return f"{result_type.upper()} Single-Variable Analysis vs {transform_english_name(x_variable)}"
    elif x_variable:
        return f"{base_title} vs {transform_english_name(x_variable)}"

    return base_title


def format_analysis_axis_label(variable_name: str, result_type: str = "",
                             unit: str = "", language: str = "english") -> str:
    """
    格式化分析坐标轴标签

    Args:
        variable_name: 变量名
        result_type: 结果类型
        unit: 单位
        language: 语言 (english/chinese)

    Returns:
        格式化的标签
    """
    if variable_name:
        if language == "chinese":
            label = transform_variable_name(variable_name)
        else:
            label = transform_english_name(variable_name)
    else:
        label = "Case Number"

    # 添加结果类型和单位
    if result_type:
        if language == "chinese":
            suffix = f"{result_type.upper()}性能"
        else:
            suffix = f"{result_type.upper()} Performance"

        if unit:
            suffix += f" ({unit})"

        label = f"{label} vs {suffix}" if variable_name else suffix

    return label


def validate_analysis_parameters(suite_id: int, x_variable: Optional[str] = None,
                                y_variable: Optional[str] = None,
                                available_variables: Optional[list] = None) -> tuple[bool, str]:
    """
    验证分析参数的有效性

    Args:
        suite_id: 套件ID
        x_variable: X变量名
        y_variable: Y变量名
        available_variables: 可用变量列表

    Returns:
        (是否有效, 错误信息)
    """
    if not isinstance(suite_id, int) or suite_id <= 0:
        return False, f"Suite ID必须为正整数，当前值: {suite_id}"

    if available_variables and x_variable and x_variable not in available_variables:
        return False, f"变量 '{x_variable}' 不存在，可用变量: {', '.join(available_variables)}"

    if available_variables and y_variable and y_variable not in available_variables:
        return False, f"变量 '{y_variable}' 不存在，可用变量: {', '.join(available_variables)}"

    return True, ""


def format_fixed_params_summary(fixed_params: Dict[str, Any]) -> str:
    """
    格式化固定参数摘要信息

    Args:
        fixed_params: 固定参数字典

    Returns:
        格式化的参数摘要字符串
    """
    if not fixed_params:
        return "无固定参数"

    param_list = [f"{transform_variable_name(k)} = {v}" for k, v in fixed_params.items()]
    return "固定参数: " + ", ".join(param_list)


def extract_result_units(analysis_data: Dict[str, Any]) -> Dict[str, str]:
    """
    从分析数据中提取结果单位

    Args:
        analysis_data: 分析数据字典

    Returns:
        结果类型到单位的映射字典
    """
    units = {}
    for result_type, data in analysis_data.get('data', {}).items():
        if data.get('units') and data['units']:
            units[result_type] = data['units'][0] if isinstance(data['units'], list) else data['units']
        else:
            units[result_type] = "tokens/sec"

    return units


def generate_analysis_key(result_type: str, *args) -> str:
    """
    生成分析键名

    Args:
        result_type: 结果类型
        *args: 其他参数

    Returns:
        分析键名
    """
    if args:
        suffix = "_".join(str(arg) for arg in args)
        return f"{result_type}_{suffix}"
    return result_type