#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析报告生成模块

负责协调图表生成、格式化和打包
"""

import zipfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from config.system import SystemConfig
from utils.logger import LoggerManager
from .chart_generator import ChartGenerator
from .reports.html_formatter import HTMLFormatter
from .reports.markdown_formatter import MarkdownFormatter
try:
    from ..db.analysis_manager import AnalysisManager
except ImportError:
    import sys
    from pathlib import Path
    framework_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(framework_dir))
    from db.analysis_manager import AnalysisManager


class ReportGenerator:
    """分析报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        self.logger = LoggerManager.get_logger("ReportGenerator")
        self.system_config = SystemConfig()

        # 分析结果目录 - 直接使用web静态目录下的analysis文件夹
        web_static_dir = self.system_config.get_web_static_dir()
        self.output_dir = web_static_dir / "analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化子模块
        self.chart_generator = ChartGenerator()
        self.analysis_manager = AnalysisManager()

    
    def generate_single_variable_report(self, analysis_data: Dict[str, Any],
                                       regression_results: Dict[str, Dict[str, Any]],
                                       suite_info: Dict[str, Any],
                                       target_variable: str,
                                       fixed_params: Optional[Dict[str, Any]] = None,
                                       start_time: Optional[datetime] = None) -> str:
        """
        生成单变量分析报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归分析结果
            suite_info: Suite信息
            target_variable: 目标变量名
            fixed_params: 固定参数字典
            start_time: 开始时间（用于统一时间戳）

        Returns:
            报告目录路径
        """
        try:
            # 使用统一时间戳生成报告目录名
            report_name = self._generate_single_var_report_name(suite_info, target_variable, fixed_params, start_time)
            report_dir = self.output_dir / report_name
            report_dir.mkdir(parents=True, exist_ok=True)

            # 生成单变量分析图表
            images_info = self.chart_generator.generate_single_variable_charts(
                report_dir, analysis_data, regression_results, target_variable
            )

            # 生成HTML报告
            html_path = self._generate_single_variable_html_report(
                report_dir, analysis_data, regression_results, suite_info,
                target_variable, fixed_params, images_info
            )

            # 生成Markdown报告
            md_path = self._generate_single_variable_markdown_report(
                report_dir, analysis_data, regression_results, suite_info,
                target_variable, fixed_params, images_info
            )

            # 记录分析历史到数据库
            self._record_analysis_to_database(
                suite_info, target_variable, fixed_params, analysis_data,
                regression_results, report_dir, start_time
            )

            # 打包压缩文件
            archive_path = self._create_archive(report_dir, md_path, images_info)

            self.logger.info(f"单变量分析报告生成完成: {report_dir}")
            return str(report_dir)

        except Exception as e:
            self.logger.error(f"生成单变量报告失败: {e}")
            raise

    def _record_analysis_to_database(self, suite_info: Dict[str, Any],
                                   target_variable: str,
                                   fixed_params: Optional[Dict[str, Any]],
                                   analysis_data: Dict[str, Any],
                                   regression_results: Dict[str, Dict[str, Any]],
                                   report_dir: Path,
                                   completed_at: Optional[datetime] = None):
        """
        记录分析历史到数据库

        Args:
            suite_info: Suite信息
            target_variable: 目标变量
            fixed_params: 固定参数
            analysis_data: 分析数据
            regression_results: 回归分析结果
            report_dir: 报告目录
        """
        try:
            # 统计信息
            total_cases = len(analysis_data.get('data_points', []))
            successful_cases = total_cases  # 假设所有数据点都是成功的

            # 回归分析摘要
            regression_summary = {}
            for result_type, result in regression_results.items():
                regression_summary[result_type] = {
                    'method': result.get('method', 'unknown'),
                    'r_squared': result.get('r_squared', 0),
                    'equation': result.get('equation', ''),
                    'p_value': result.get('p_value', None)
                }

            # 获取Web URL - 需要包含analysis路径
            web_static_dir = self.output_dir.parent.parent  # web_server/static/
            relative_path = report_dir.relative_to(web_static_dir)
            web_url = f"static/{relative_path}/analysis_report.html"

            # 记录到数据库，使用统一的时间戳
            analysis_id = self.analysis_manager.record_analysis(
                suite_id=suite_info['id'],
                analysis_type="single_variable",
                target_variable=target_variable,
                fixed_params=fixed_params,
                result_types=list(regression_results.keys()),
                analysis_dir=str(report_dir),
                web_url=web_url,
                total_cases=total_cases,
                successful_cases=successful_cases,
                regression_summary=regression_summary,
                duration_ms=0,  # 可以后续添加计时功能
                status="completed",
                completed_at=completed_at
            )

            self.logger.info(f"分析历史已记录到数据库，ID: {analysis_id}")

        except Exception as e:
            self.logger.error(f"记录分析历史失败: {e}")
            # 不抛出异常，避免影响主要功能

    def _generate_single_var_report_name(self, suite_info: Dict[str, Any],
                                         target_variable: str,
                                         fixed_params: Optional[Dict[str, Any]],
                                         start_time: Optional[datetime] = None) -> str:
        """
        生成单变量分析报告目录名

        Args:
            suite_info: Suite信息
            target_variable: 目标变量
            fixed_params: 固定参数

        Returns:
            报告目录名
        """
        timestamp = (start_time if start_time else datetime.now()).strftime("%Y%m%d_%H%M%S")
        # 新的简单命名规则: 只返回子目录名(变量名_时间戳)
        # 因为output_dir已经是suite_id目录了
        return f"{target_variable}_{timestamp}"

    
    
    
    def _create_archive(self, report_dir: Path, md_path: Path, images_info: Dict[str, str]) -> Path:
        """
        创建压缩包

        Args:
            report_dir: 报告目录
            md_path: Markdown文件路径
            images_info: 图像信息

        Returns:
            压缩包路径
        """
        archive_path = report_dir / "report_package.zip"

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加Markdown文件
            zf.write(md_path, "analysis_report.md")

            # 添加图像文件
            for image_info in images_info.values():
                image_path = report_dir / image_info
                if image_path.exists():
                    zf.write(image_path, image_path.name)

        return archive_path

    def _generate_single_variable_html_report(self, report_dir: Path,
                                             analysis_data: Dict[str, Any],
                                             regression_results: Dict[str, Dict[str, Any]],
                                             suite_info: Dict[str, Any],
                                             target_variable: str,
                                             fixed_params: Optional[Dict[str, Any]],
                                             images_info: Dict[str, str]) -> Path:
        """
        生成单变量分析HTML报告

        Args:
            report_dir: 报告目录
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            target_variable: 目标变量
            fixed_params: 固定参数
            images_info: 图像信息

        Returns:
            HTML文件路径
        """
        from .reports.html_formatter import HTMLFormatter

        formatter = HTMLFormatter()
        html_content = formatter.build_single_variable_html(
            analysis_data, regression_results, suite_info,
            target_variable, fixed_params, images_info
        )

        html_path = report_dir / "analysis_report.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_path

    def _generate_single_variable_markdown_report(self, report_dir: Path,
                                                 analysis_data: Dict[str, Any],
                                                 regression_results: Dict[str, Dict[str, Any]],
                                                 suite_info: Dict[str, Any],
                                                 target_variable: str,
                                                 fixed_params: Optional[Dict[str, Any]],
                                                 images_info: Dict[str, str]) -> Path:
        """
        生成单变量分析Markdown报告

        Args:
            report_dir: 报告目录
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            target_variable: 目标变量
            fixed_params: 固定参数
            images_info: 图像信息

        Returns:
            Markdown文件路径
        """
        from .reports.markdown_formatter import MarkdownFormatter

        formatter = MarkdownFormatter()
        md_content = formatter.build_single_variable_markdown(
            analysis_data, regression_results, suite_info,
            target_variable, fixed_params, images_info
        )

        md_path = report_dir / "analysis_report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return md_path