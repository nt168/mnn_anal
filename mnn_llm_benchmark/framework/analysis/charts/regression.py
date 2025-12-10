#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归图构建器模块

提供各种类型的回归分析图构建功能
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

from .components import create_regression_plot, save_figure, create_errorbar_plot
from ..utils import transform_english_name, format_analysis_title


class RegressionChartBuilder:
    """回归图构建器"""

    def __init__(self):
        """初始化回归图构建器"""
        pass

    def build_general_regression(self, regression_result: Dict[str, Any], result_type: str,
                               x_variable: Optional[str] = None,
                               report_dir: Optional[Path] = None) -> Path:
        """
        构建通用回归图

        Args:
            regression_result: 回归结果
            result_type: 结果类型
            x_variable: X变量名
            report_dir: 报告目录

        Returns:
            图像文件路径
        """
        # 准备数据
        x_data = np.array(regression_result['x_data'])
        y_data = np.array(regression_result['y_data'])
        y_pred = np.array(regression_result['y_predicted'])

        # 创建图表
        x_label = transform_english_name(x_variable) if x_variable else "X"
        y_label = f"{result_type.upper()} Performance"
        title = f"{result_type.upper()} Regression Analysis"

        fig = create_regression_plot(x_data, y_data, y_pred, regression_result,
                                    title, x_label, y_label)

        # 保存图表
        if report_dir:
            image_path = report_dir / f"{result_type}_regression.png"
        else:
            image_path = Path(f"{result_type}_regression.png")

        save_figure(fig, str(image_path))
        return image_path

    def build_single_variable_regression(self, regression_result: Dict[str, Any],
                                       result_type: str, target_variable: str,
                                       report_dir: Optional[Path] = None) -> Path:
        """
        构建单变量回归图（带方差标注）

        Args:
            regression_result: 回归结果
            result_type: 结果类型
            target_variable: 目标变量名
            report_dir: 报告目录

        Returns:
            图像文件路径
        """
        # 获取方差数据
        variance_data = regression_result.get('variance_data', {})
        x_data = variance_data.get('x_values', [])
        y_data = variance_data.get('y_values', [])
        std_data = variance_data.get('std_values', [])
        y_pred = regression_result['y_predicted']

        if not x_data:
            raise ValueError("没有有效的数据点绘制回归图")

        # 确保数据长度一致
        min_length = min(len(x_data), len(y_data), len(std_data))
        x_data = x_data[:min_length]
        y_data = y_data[:min_length]
        std_data = std_data[:min_length]

        # 创建带误差条的回归图
        x_label = transform_english_name(target_variable)
        y_label = f"{result_type.upper()} Performance"
        title = f"{result_type.upper()} Regression Analysis vs {x_label}"

        fig = self._create_composite_regression_plot(x_data, y_data, std_data, y_pred,
                                                    regression_result, title, x_label, y_label)

        # 保存图表
        if report_dir:
            image_path = report_dir / f"{result_type}_regression.png"
        else:
            image_path = Path(f"{result_type}_regression.png")

        save_figure(fig, str(image_path))
        return image_path

    def _create_composite_regression_plot(self, x_data: List[float], y_data: List[float],
                                        std_data: List[float], y_pred: List[float],
                                        regression_result: Dict[str, Any],
                                        title: str, x_label: str, y_label: str):
        """
        创建复合回归图（带误差条）

        Args:
            x_data: X数据
            y_data: Y数据
            std_data: 标准差数据
            y_pred: 预测Y数据
            regression_result: 回归结果
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签

        Returns:
            matplotlib图表对象
        """
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 8))

        # 绘制带误差条的数据点
        plt.errorbar(x_data, y_data, yerr=std_data, fmt='o',
                    alpha=0.7, capsize=5, capthick=2,
                    markersize=8, color='steelblue', ecolor='red',
                    label='Data Points with Variance')

        # 绘制回归曲线
        x_smooth = np.linspace(min(x_data), max(x_data), 100)
        if regression_result['regression']['method'] == 'linear':
            slope = regression_result['regression']['slope']
            intercept = regression_result['regression']['intercept']
            y_smooth = slope * x_smooth + intercept
        else:
            func = regression_result['regression']['function']
            params = regression_result['regression']['parameters']
            y_smooth = func(x_smooth, *params)

        plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, label='回归曲线')

        # 添加统计信息
        equation = regression_result['equation']
        r2 = regression_result['regression']['r2']
        textstr = f'Equation: {equation}\\n$R^2$ = {r2:.4f}'
        plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 设置标签和标题
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')

        # 添加图例和网格
        plt.legend()
        plt.grid(True, alpha=0.3, linestyle='--', which='both')

        # 添加方差说明
        variance_info = "Error bars represent standard deviation across multiple runs"
        plt.figtext(0.5, 0.02, variance_info, ha='center', fontsize=9, style='italic')

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)

        return plt.gcf()