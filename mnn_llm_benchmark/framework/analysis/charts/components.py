#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表组件模块

提供基础的图表组件和配置
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import platform
import matplotlib.font_manager as fm
from typing import Dict, Any, Tuple, List

# 设置matplotlib使用非交互式后端
matplotlib.use('Agg')

# 设置字体配置
def setup_chinese_font():
    """设置matplotlib的中文字体支持"""
    system = platform.system()

    try:
        if system == 'Linux':
            # Linux系统，优先使用系统可用中文字体
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            chinese_fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
                           'Noto Sans CJK SC', 'Source Han Sans SC', 'SimHei']

            selected_font = None
            for font in chinese_fonts:
                if font in available_fonts:
                    selected_font = font
                    break

            if selected_font:
                plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans']
                return selected_font
            else:
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
                return None
        elif system == 'Darwin':  # macOS
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'STHeiti', 'SimHei']
        elif system == 'Windows':
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
    except Exception:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

    return None

# 初始化字体设置
_chinese_font_available = setup_chinese_font()

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 10


def create_errorbar_plot(x_data: List[float], y_data: List[float], std_data: List[float],
                        title: str, x_label: str, y_label: str,
                        figsize: Tuple[int, int] = (12, 8),
                        plot_style: str = "default") -> plt.Figure:
    """
    创建带误差条的图表

    Args:
        x_data: X轴数据
        y_data: Y轴数据
        std_data: 标准差数据
        title: 图表标题
        x_label: X轴标签
        y_label: Y轴标签
        figsize: 图表尺寸
        plot_style: 绘图样式

    Returns:
        matplotlib图表对象
    """
    fig = plt.figure(figsize=figsize)

    # 验证数据长度一致
    min_length = min(len(x_data), len(y_data), len(std_data))
    x_data = x_data[:min_length]
    y_data = y_data[:min_length]
    std_data = std_data[:min_length]

    # 绘制误差条形图
    color = 'steelblue' if plot_style == "default" else 'darkblue'

    plt.errorbar(x_data, y_data, yerr=std_data, fmt='o',
                alpha=0.8, capsize=5, capthick=2,
                markersize=8, color=color, ecolor='red',
                label='Data Points with Variance')

    # 设置标签和标题
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')

    # 添加网格和图例
    plt.grid(True, alpha=0.3, linestyle='--', which='both')
    plt.legend()

    # 添加方差说明
    variance_info = "Error bars represent standard deviation across multiple runs"
    plt.figtext(0.5, 0.02, variance_info, ha='center', fontsize=9, style='italic')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    return fig


def create_scatter_plot(x_data: List[float], y_data: List[float],
                       title: str, x_label: str, y_label: str,
                       figsize: Tuple[int, int] = (10, 8),
                       color: str = 'steelblue') -> plt.Figure:
    """
    创建散点图

    Args:
        x_data: X轴数据
        y_data: Y轴数据
        title: 图表标题
        x_label: X轴标签
        y_label: Y轴标签
        figsize: 图表尺寸
        color: 点的颜色

    Returns:
        matplotlib图表对象
    """
    fig = plt.figure(figsize=figsize)

    # 创建散点图
    plt.scatter(x_data, y_data, alpha=0.7, s=60, color=color)

    # 设置标签和标题
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')

    # 添加网格
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    return fig


def create_regression_plot(x_data: np.ndarray, y_data: np.ndarray,
                          y_pred: np.ndarray, regression_result: Dict[str, Any],
                          title: str, x_label: str, y_label: str,
                          figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
    """
    创建回归分析图

    Args:
        x_data: 原始X数据
        y_data: 原始Y数据
        y_pred: 预测Y数据
        regression_result: 回归结果字典
        title: 图表标题
        x_label: X轴标签
        y_label: Y轴标签
        figsize: 图表尺寸

    Returns:
        matplotlib图表对象
    """
    fig = plt.figure(figsize=figsize)

    # 绘制原始数据点
    plt.scatter(x_data, y_data, alpha=0.7, s=60, color='steelblue', label='原始数据')

    # 绘制回归曲线
    if regression_result['regression']['method'] == 'linear':
        plt.plot(x_data, y_pred, 'r-', linewidth=2, label='线性回归')
    else:
        # 生成平滑曲线
        x_smooth = np.linspace(min(x_data), max(x_data), 100)
        y_smooth = _predict_smooth_curve(regression_result, x_smooth)
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
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    return fig


def _predict_smooth_curve(regression_result: Dict[str, Any], x_smooth: np.ndarray) -> np.ndarray:
    """预测平滑曲线值（内部函数）"""
    if regression_result['regression']['method'] == 'linear':
        slope = regression_result['regression']['slope']
        intercept = regression_result['regression']['intercept']
        return slope * x_smooth + intercept
    else:
        func = regression_result['regression']['function']
        params = regression_result['regression']['parameters']
        return func(x_smooth, *params)


def save_figure(fig: plt.Figure, filepath: str, dpi: int = 300) -> None:
    """
    保存图表到文件

    Args:
        fig: matplotlib图表对象
        filepath: 文件路径
        dpi: 图像分辨率
    """
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close(fig)