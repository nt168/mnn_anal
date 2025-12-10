#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表生成模块

负责协调各种图表的生成，使用组件化架构
"""

from pathlib import Path
from typing import Dict, Any, Optional
from config.system import SystemConfig
from utils.logger import LoggerManager

from .charts import ScatterChartBuilder, RegressionChartBuilder


class ChartGenerator:
    """图表生成器 - 使用组件化架构"""

    def __init__(self):
        """初始化图表生成器"""
        self.logger = LoggerManager.get_logger("ChartGenerator")
        self.system_config = SystemConfig()

        # 初始化图表构建器
        self.scatter_builder = ScatterChartBuilder()
        self.regression_builder = RegressionChartBuilder()

    def generate_all_charts(self, report_dir: Path,
                           analysis_data: Dict[str, Any],
                           regression_results: Dict[str, Dict[str, Any]],
                           x_variable: Optional[str],
                           y_variable: Optional[str] = None) -> Dict[str, str]:
        """
        生成所有图表

        Args:
            report_dir: 报告目录
            analysis_data: 分析数据
            regression_results: 回归结果
            x_variable: X变量
            y_variable: Y变量

        Returns:
            图像信息字典 {image_key: filename}
        """
        images_info = {}

        try:
            # 为每个结果类型生成图表
            for result_type, data in analysis_data['data'].items():
                if not data.get('mean_values'):
                    continue

                # 生成散点图
                try:
                    scatter_path = self.scatter_builder.build_general_scatter(
                        data, result_type, x_variable, report_dir
                    )
                    images_info[f'{result_type}_scatter'] = scatter_path.name
                except Exception as e:
                    self.logger.warning(f"创建{result_type}散点图失败: {e}")
                    continue

                # 生成回归分析图
                if result_type in regression_results:
                    try:
                        regression_path = self.regression_builder.build_general_regression(
                            regression_results[result_type], result_type, x_variable, report_dir
                        )
                        images_info[f'{result_type}_regression'] = regression_path.name
                    except Exception as e:
                        self.logger.warning(f"创建{result_type}回归图失败: {e}")
                        continue

            self.logger.info(f"生成了 {len(images_info)} 个通用图表")
            return images_info

        except Exception as e:
            self.logger.error(f"生成图表失败: {e}")
            raise

    def generate_single_variable_charts(self, report_dir: Path,
                                       analysis_data: Dict[str, Any],
                                       regression_results: Dict[str, Dict[str, Any]],
                                       target_variable: str) -> Dict[str, str]:
        """
        生成单变量分析图表

        Args:
            report_dir: 报告目录
            analysis_data: 分析数据
            regression_results: 回归结果
            target_variable: 目标变量

        Returns:
            图像信息字典 {image_key: filename}
        """
        images_info = {}

        try:
            # 为每个结果类型生成图表
            for result_type, data in analysis_data['data'].items():
                if not data.get('mean_values'):
                    continue

                # 生成带方差标注的散点图
                try:
                    scatter_path = self.scatter_builder.build_single_variable_scatter(
                        data, result_type, target_variable, report_dir
                    )
                    images_info[f'{result_type}_scatter'] = scatter_path.name
                except Exception as e:
                    self.logger.warning(f"创建{result_type}单变量散点图失败: {e}")
                    continue

                # 生成带回归线的方差标注图
                if result_type in regression_results:
                    try:
                        regression_path = self.regression_builder.build_single_variable_regression(
                            regression_results[result_type], result_type, target_variable, report_dir
                        )
                        images_info[f'{result_type}_regression'] = regression_path.name
                    except Exception as e:
                        self.logger.warning(f"创建{result_type}单变量回归图失败: {e}")
                        continue

            self.logger.info(f"生成了 {len(images_info)} 个单变量分析图表")
            return images_info

        except Exception as e:
            self.logger.error(f"生成单变量图表失败: {e}")
            raise