#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成基础模块

提供报告生成的基础组件和接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..utils import transform_variable_name, transform_english_name, format_analysis_title, format_fixed_params_summary


class BaseFormatter(ABC):
    """报告格式化器的基类"""

    def __init__(self):
        """初始化基础格式化器"""
        pass

    @abstractmethod
    def build_report(self, analysis_data: Dict[str, Any],
                    regression_results: Dict[str, Dict[str, Any]],
                    suite_info: Dict[str, Any],
                    **kwargs) -> str:
        """
        构建完整报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            **kwargs: 其他参数

        Returns:
            格式化的报告内容
        """
        pass

    def _build_header(self, suite_info: Dict[str, Any],
                     analysis_title: str,
                     **kwargs) -> str:
        """
        构建报告头部

        Args:
            suite_info: Suite信息
            analysis_title: 分析标题
            **kwargs: 其他参数

        Returns:
            报告头部内容
        """
        raise NotImplementedError

    def _build_metadata_section(self, suite_info: Dict[str, Any],
                               analysis_data: Dict[str, Any],
                               **kwargs) -> str:
        """
        构建元数据部分

        Args:
            suite_info: Suite信息
            analysis_data: 分析数据
            **kwargs: 其他参数

        Returns:
            元数据部分内容
        """
        raise NotImplementedError

    def _build_variance_section(self, analysis_data: Dict[str, Any]) -> str:
        """
        构建方差说明部分

        Args:
            analysis_data: 分析数据

        Returns:
            方差说明部分内容
        """
        raise NotImplementedError

    def _build_results_section(self, analysis_data: Dict[str, Any],
                              regression_results: Dict[str, Dict[str, Any]],
                              images_info: Dict[str, str],
                              **kwargs) -> str:
        """
        构建结果部分

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            images_info: 图像信息
            **kwargs: 其他参数

        Returns:
            结果部分内容
        """
        raise NotImplementedError


class MetadataBuilder:
    """元数据构建器"""

    @staticmethod
    def build_general_metadata(suite_info: Dict[str, Any],
                             analysis_data: Dict[str, Any],
                             x_variable: Optional[str] = None,
                             y_variable: Optional[str] = None) -> Dict[str, Any]:
        """
        构建通用分析的元数据

        Args:
            suite_info: Suite信息
            analysis_data: 分析数据
            x_variable: X变量名
            y_variable: Y变量名

        Returns:
            元数据字典
        """
        return {
            'suite_name': suite_info['name'],
            'model_name': suite_info['model_name'],
            'analysis_mode': analysis_data.get('analysis_mode', 'general'),
            'x_variable': x_variable,
            'y_variable': y_variable,
            'result_types': analysis_data.get('result_types', []),
            'total_cases': analysis_data.get('total_cases', 0)
        }

    @staticmethod
    def build_single_variable_metadata(suite_info: Dict[str, Any],
                                     analysis_data: Dict[str, Any],
                                     target_variable: str,
                                     fixed_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建单变量分析的元数据

        Args:
            suite_info: Suite信息
            analysis_data: 分析数据
            target_variable: 目标变量名
            fixed_params: 固定参数

        Returns:
            元数据字典
        """
        return {
            'suite_name': suite_info['name'],
            'model_name': suite_info['model_name'],
            'analysis_mode': 'single_variable',
            'target_variable': transform_variable_name(target_variable),
            'fixed_params_summary': format_fixed_params_summary(fixed_params or {}),
            'fixed_params': fixed_params or {},
            'filtered_cases': analysis_data.get('filtered_cases', 0),
            'total_cases': analysis_data.get('total_cases', 0),
            'result_types': analysis_data.get('result_types', [])
        }


class VarianceExplainer:
    """方差解释器"""

    @staticmethod
    def explain_variance_significance(analysis_data: Dict[str, Any]) -> str:
        """
        解释方差的重要性

        Args:
            analysis_data: 分析数据

        Returns:
            方差显著性说明
        """
        significance = """
        方差说明：
        - 每个数据点的误差条表示多次运行结果的标准差
        - 误差条长度反映了结果的一致性：较短表示结果更稳定
        - 在理想情况下，相同参数配置下的多次运行结果应该有较小的方差
        - 较大的方差可能表明系统存在不稳定的因素
        """
        return significance.strip()


    @staticmethod
    def build_variance_table(analysis_data: Dict[str, Any]) -> str:
        """
        构建方差统计表

        Args:
            analysis_data: 分析数据

        Returns:
            方差统计表格内容
        """
        table_content = []
        for result_type, data in analysis_data.get('data', {}).items():
            if not data.get('std_values'):
                continue

            std_values = [v for v in data.get('std_values', []) if v is not None]
            mean_std = sum(std_values) / len(std_values) if std_values else 0

            table_content.append(f"| {result_type} | {len(std_values)} | {mean_std:.4f} | {max(std_values):.4f} | {min(std_values):.4f} |")

        if not table_content:
            return "无有效的方差数据"

        header = "| 结果类型 | 数据点数 | 平均标准差 | 最大标准差 | 最小标准差 |\n|--------|--------|----------|----------|----------|"

        return header + "\n" + "\n".join(table_content)