#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主数据分析器

协调数据提取、回归分析和报告生成
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

from .data_extractor import DataExtractor
from .regression import RegressionAnalyzer
from .report_generator import ReportGenerator
from utils.logger import LoggerManager
from .utils import transform_variable_name


class DataAnalyzer:
    """主数据分析器"""

    def __init__(self):
        """初始化数据分析器"""
        self.logger = LoggerManager.get_logger("DataAnalyzer")
        self.extractor = DataExtractor()
        self.regression_analyzer = RegressionAnalyzer()
        self.report_generator = ReportGenerator()

    
    def list_available_suites(self) -> List[Dict[str, Any]]:
        """
        列出可用的suite列表

        Returns:
            suite信息列表
        """
        try:
            return self.extractor.get_suite_list()
        except Exception as e:
            self.logger.error(f"获取suite列表失败: {e}")
            raise

    def get_suite_variables(self, suite_id: int) -> List[str]:
        """
        获取suite的变量列表

        Args:
            suite_id: suite ID

        Returns:
            变量名列表
        """
        try:
            return self.extractor.get_suite_variables(suite_id)
        except Exception as e:
            self.logger.error(f"获取suite变量失败: {e}")
            raise

    def get_suite_result_types(self, suite_id: int) -> List[str]:
        """
        获取suite的结果类型列表

        Args:
            suite_id: suite ID

        Returns:
            结果类型列表
        """
        try:
            return self.extractor.get_suite_result_types(suite_id)
        except Exception as e:
            self.logger.error(f"获取结果类型失败: {e}")
            raise

    def analyze_single_variable(self, suite_id: int,
                               target_variable: str,
                               fixed_params: Optional[Dict[str, Any]] = None,
                               result_types: Optional[List[str]] = None) -> str:
        """
        单变量分析 - 正式分析模式

        Args:
            suite_id: suite ID
            target_variable: 要分析的目标变量
            fixed_params: 其他变量的固定值字典
            result_types: 要分析的结果类型列表

        Returns:
            分析报告目录路径
        """
        try:
            # 检查是否已存在相同分析
            analysis_key = self._generate_single_var_analysis_key(suite_id, target_variable, fixed_params, result_types)
            existing_report = self._check_existing_analysis(analysis_key)
            if existing_report:
                self.logger.info(f"发现已有分析报告: {existing_report}")
                return existing_report

            # 验证参数
            valid, error_msg = self.extractor.validate_analysis_parameters(
                suite_id, target_variable, None
            )
            if not valid:
                raise ValueError(error_msg)

            # 提取单变量分析数据
            self.logger.info(f"开始单变量分析 - 目标变量: {target_variable}")
            if fixed_params:
                self.logger.info(f"固定参数: {fixed_params}")

            analysis_data = self.extractor.extract_single_variable_data(
                suite_id, target_variable, fixed_params, result_types
            )

            if not analysis_data['data']:
                raise ValueError("未找到符合条件的分析数据")

            # 执行回归分析
            self.logger.info("开始执行回归分析...")
            regression_results = self._perform_single_variable_regression(
                analysis_data, target_variable
            )

            # 生成报告
            self.logger.info("开始生成分析报告...")
            report_path = self.report_generator.generate_single_variable_report(
                analysis_data, regression_results,
                analysis_data['suite_info'], target_variable, fixed_params
            )

            # 记录分析历史
            self._record_analysis_history(analysis_key, str(report_path))

            self.logger.info(f"单变量分析完成，报告保存在: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"单变量分析Suite {suite_id} 失败: {e}")
            raise

    
    def _perform_single_variable_regression(self, analysis_data: Dict[str, Any],
                                          target_variable: str) -> Dict[str, Dict[str, Any]]:
        """
        执行单变量回归分析

        Args:
            analysis_data: 分析数据
            target_variable: 目标变量

        Returns:
            回归分析结果字典
        """
        regression_results = {}

        for result_type, data in analysis_data['data'].items():
            try:
                if not data['mean_values']:
                    continue

                # 准备数据
                x_data = []
                y_data = []
                std_data = []

                # 使用目标变量作为X轴
                for i, (x_val, y_val, std_val) in enumerate(zip(data['x_values'], data['mean_values'], data['std_values'])):
                    if x_val is not None and y_val is not None:
                        x_data.append(float(x_val))
                        y_data.append(float(y_val))
                        std_data.append(float(std_val) if std_val else 0.0)

                if len(x_data) < 3:
                    self.logger.warning(f"结果类型 {result_type} 数据点太少，跳过回归分析")
                    continue

                # 执行回归分析
                x_name = transform_variable_name(target_variable)
                y_name = f"{result_type.upper()} 性能"

                result = self.regression_analyzer.analyze_regression(
                    np.array(x_data), np.array(y_data), x_name, y_name
                )

                # 添加方差信息
                result['variance_data'] = {
                    'x_values': x_data,
                    'y_values': y_data,
                    'std_values': std_data
                }

                regression_results[result_type] = result

            except Exception as e:
                self.logger.error(f"分析结果类型 {result_type} 失败: {e}")
                continue

        return regression_results

    def _generate_single_var_analysis_key(self, suite_id: int,
                                         target_variable: str,
                                         fixed_params: Optional[Dict[str, Any]],
                                         result_types: Optional[List[str]]) -> str:
        """
        生成单变量分析的唯一标识

        Args:
            suite_id: suite ID
            target_variable: 目标变量
            fixed_params: 固定参数
            result_types: 结果类型列表

        Returns:
            分析标识字符串
        """
        key_parts = [str(suite_id), "singlevar", target_variable]
        if fixed_params:
            # 将固定参数排序后加入key
            param_items = sorted(fixed_params.items())
            for param, value in param_items:
                key_parts.append(f"{param}_{value}")
        if result_types:
            key_parts.extend(sorted(result_types))

        key_string = "_".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()[:8]

    
    def _check_existing_analysis(self, analysis_key: str) -> Optional[str]:
        """
        检查是否已存在相同分析

        Args:
            analysis_key: 分析标识

        Returns:
            已存在的报告路径或None
        """
        try:
            analysis_dir = self.report_generator.output_dir

            # 搜索包含该标识的目录
            for existing_dir in analysis_dir.iterdir():
                if existing_dir.is_dir() and analysis_key in existing_dir.name:
                    # 检查是否包含必要的文件
                    html_file = existing_dir / "analysis_report.html"
                    if html_file.exists():
                        return str(existing_dir)

            return None

        except Exception as e:
            self.logger.warning(f"检查已有分析失败: {e}")
            return None

    def _record_analysis_history(self, analysis_key: str, report_path: str):
        """
        记录分析历史

        Args:
            analysis_key: 分析标识
            report_path: 报告路径
        """
        try:
            history_file = self.report_generator.output_dir / "analysis_history.json"
            history = {}

            # 读取现有历史
            if history_file.exists():
                import json
                with open(history_file, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                    except:
                        history = {}

            # 添加新记录
            from datetime import datetime
            history[analysis_key] = {
                "report_path": report_path,
                "timestamp": datetime.now().isoformat()
            }

            # 保存历史
            import json
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.warning(f"记录分析历史失败: {e}")


