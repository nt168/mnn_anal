#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
散点图构建器模块

提供各种类型的散点图构建功能
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .components import create_errorbar_plot, create_scatter_plot, save_figure
from ..utils import transform_english_name, format_analysis_title, format_analysis_axis_label


class ScatterChartBuilder:
    """散点图构建器"""

    def __init__(self):
        """初始化散点图构建器"""
        pass

    def build_general_scatter(self, data: Dict[str, Any], result_type: str,
                             x_variable: Optional[str] = None,
                             report_dir: Optional[Path] = None) -> Path:
        """
        构建通用散点图

        Args:
            data: 数据字典
            result_type: 结果类型
            x_variable: X变量名
            report_dir: 报告目录

        Returns:
            图像文件路径
        """
        # 准备数据
        x_data, y_data, x_label = self._prepare_scatter_data(data, x_variable)

        # 创建图表
        y_label = format_analysis_axis_label("", result_type,
                                           data.get('units', [''])[0] if data.get('units') else "tokens/sec")
        title = format_analysis_title(result_type, x_variable, "general")

        fig = create_scatter_plot(x_data, y_data, title, x_label, y_label)

        # 保存图表
        if report_dir:
            image_path = report_dir / f"{result_type}_scatter.png"
        else:
            image_path = Path(f"{result_type}_scatter.png")

        save_figure(fig, str(image_path))
        return image_path

    def build_single_variable_scatter(self, data: Dict[str, Any], result_type: str,
                                    target_variable: str,
                                    report_dir: Optional[Path] = None) -> Path:
        """
        构建单变量散点图（带方差标注）

        Args:
            data: 数据字典
            result_type: 结果类型
            target_variable: 目标变量名
            report_dir: 报告目录

        Returns:
            图像文件路径
        """
        # 准备数据
        x_data, y_data, std_data = self._prepare_single_variable_data(data, target_variable)

        if not x_data:
            raise ValueError("没有有效的数据点绘制散点图")

        # 创建图表
        x_label = transform_english_name(target_variable)
        y_label = f"{result_type.upper()} Performance"
        title = f"{result_type.upper()} Single-Variable Analysis vs {x_label}"

        fig = create_errorbar_plot(x_data, y_data, std_data, title, x_label, y_label)

        # 保存图表
        if report_dir:
            image_path = report_dir / f"{result_type}_scatter.png"
        else:
            image_path = Path(f"{result_type}_scatter.png")

        save_figure(fig, str(image_path))
        return image_path

    def _prepare_scatter_data(self, data: Dict[str, Any],
                             x_variable: Optional[str]) -> Tuple[List[float], List[float], str]:
        """
        准备散点图数据

        Args:
            data: 数据字典
            x_variable: X变量名

        Returns:
            (x_data, y_data, x_label)
        """
        mean_values = data.get('mean_values', [])
        x_values = data.get('x_values', [])

        if x_variable and x_values and any(v is not None for v in x_values):
            # 使用X变量作为X轴
            x_data = [float(v) for v in x_values if v is not None]
            y_data = [mean_values[i] for i, v in enumerate(x_values) if v is not None]
            x_label = transform_english_name(x_variable)
        else:
            # 使用案例编号作为X轴
            x_data = list(range(1, len(mean_values) + 1))
            y_data = mean_values
            x_label = "Case Number"

        return x_data, y_data, x_label

    def _prepare_single_variable_data(self, data: Dict[str, Any],
                                    target_variable: str) -> Tuple[List[float], List[float], List[float]]:
        """
        准备单变量分析数据

        Args:
            data: 数据字典
            target_variable: 目标变量名

        Returns:
            (x_data, y_data, std_data)
        """
        x_data = []
        y_data = []
        std_data = []

        x_values = data.get('x_values', [])
        mean_values = data.get('mean_values', [])
        std_values = data.get('std_values', [])

        # 过滤有效数据
        for x_val, y_val, std_val in zip(x_values, mean_values, std_values):
            if x_val is not None and y_val is not None:
                x_data.append(float(x_val))
                y_data.append(float(y_val))
                std_data.append(float(std_val) if std_val else 0.0)

        return x_data, y_data, std_data