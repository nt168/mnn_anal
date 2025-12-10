#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown报告格式化器

提供Markdown格式的分析报告生成功能
"""

from typing import Dict, Any, Optional
from .base import BaseFormatter, MetadataBuilder, VarianceExplainer
from ..utils import transform_variable_name, transform_english_name, format_analysis_title


class MarkdownFormatter(BaseFormatter):
    """Markdown报告格式化器"""

    def build_report(self, analysis_data: Dict[str, Any],
                    regression_results: Dict[str, Dict[str, Any]],
                    suite_info: Dict[str, Any],
                    **kwargs) -> str:
        """
        构建Markdown报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            **kwargs: 其他参数

        Returns:
            Markdown格式的报告内容
        """
        # 根据参数决定报告类型
        x_variable = kwargs.get('x_variable')
        y_variable = kwargs.get('y_variable')
        target_variable = kwargs.get('target_variable')
        fixed_params = kwargs.get('fixed_params')

        if target_variable:
            return self.build_single_variable_markdown(
                analysis_data, regression_results, suite_info,
                target_variable, fixed_params, kwargs.get('images_info', {})
            )
        else:
            return self.build_complete_markdown(
                analysis_data, regression_results, suite_info,
                x_variable, y_variable, kwargs.get('images_info', {})
            )

    def build_complete_markdown(self, analysis_data: Dict[str, Any],
                               regression_results: Dict[str, Dict[str, Any]],
                               suite_info: Dict[str, Any],
                               x_variable: Optional[str], y_variable: Optional[str],
                               images_info: Dict[str, str]) -> str:
        """
        构建完整的Markdown报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            x_variable: X变量名
            y_variable: Y变量名
            images_info: 图像信息

        Returns:
            完整的Markdown报告内容
        """
        # 构建Markdown各部分
        md_parts = []

        # 报告标题和简介
        md_parts.append(self._build_md_header(suite_info, None, x_variable, y_variable))

        # 元数据部分
        metadata = MetadataBuilder.build_general_metadata(
            suite_info, analysis_data, x_variable, y_variable
        )
        md_parts.append(self._build_md_metadata_section(metadata))

        # 方差说明部分
        md_parts.append(self._build_md_variance_section(analysis_data))

        # 结果表格和图表
        md_parts.append(self._build_md_results_section(
            analysis_data, regression_results, images_info
        ))

        # 回归分析详情
        md_parts.append(self._build_md_regression_details(
            regression_results, transform_english_name(x_variable) if x_variable else "X"
        ))

        return "\n\n".join(md_parts)

    def build_single_variable_markdown(self, analysis_data: Dict[str, Any],
                                      regression_results: Dict[str, Dict[str, Any]],
                                      suite_info: Dict[str, Any],
                                      target_variable: str, fixed_params: Optional[Dict[str, Any]],
                                      images_info: Dict[str, str]) -> str:
        """
        构建单变量分析Markdown报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            target_variable: 目标变量名
            fixed_params: 固定参数
            images_info: 图像信息

        Returns:
            单变量分析的Markdown报告内容
        """
        # 构建Markdown各部分
        md_parts = []

        # 报告标题和简介
        md_parts.append(self._build_md_header(suite_info, target_variable, None, None))

        # 元数据部分
        metadata = MetadataBuilder.build_single_variable_metadata(
            suite_info, analysis_data, target_variable, fixed_params
        )
        md_parts.append(self._build_md_single_variable_metadata_section(metadata))

        # 方差说明部分
        md_parts.append(self._build_md_variance_section(analysis_data))

        # 结果表格和图表
        md_parts.append(self._build_md_single_variable_results_section(
            analysis_data, regression_results, images_info, target_variable
        ))

        # 回归分析详情
        md_parts.append(self._build_md_single_variable_regression_details(
            regression_results, transform_english_name(target_variable)
        ))

        return "\n\n".join(md_parts)

    def _build_md_header(self, suite_info: Dict[str, Any],
                        target_variable: Optional[str],
                        x_variable: Optional[str],
                        y_variable: Optional[str]) -> str:
        """构建Markdown报告头部"""
        suite_name = suite_info['name']
        model_name = suite_info['model_name']
        timestamp = suite_info.get('timestamp', '')

        if target_variable:
            title = f"# {suite_name} 单变量分析报告 - {transform_variable_name(target_variable)}"
            intro = f"本报告对**{suite_name}**套件中变量**{transform_variable_name(target_variable)}**的性能影响进行了详细分析。"
        elif x_variable and y_variable:
            title = f"# {suite_name} 相关性分析报告 - {transform_variable_name(x_variable)} vs {transform_variable_name(y_variable)}"
            intro = f"本报告分析了**{suite_name}**套件中变量**{transform_variable_name(x_variable)}**和**{transform_variable_name(y_variable)}**之间的相关性。"
        elif x_variable:
            title = f"# {suite_name} 分析报告 - {transform_variable_name(x_variable)}"
            intro = f"本报告对**{suite_name}**套件中变量**{transform_variable_name(x_variable)}**的性能影响进行了分析。"
        else:
            title = f"# {suite_name} 性能分析报告"
            intro = f"本报告对**{suite_name}**套件进行了全面的性能分析。"

        return f"""{title}

## 基本信息

- **模型**: {model_name}
- **分析时间**: {timestamp}
- **说明**: {intro}"""

    def _build_md_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """构建元数据部分"""
        return f"""## 分析元数据

| 属性 | 值 |
|------|-----|
| Suite名称 | {metadata['suite_name']} |
| 模型名称 | {metadata['model_name']} |
| 分析模式 | {metadata['analysis_mode']} |
| X变量 | {metadata['x_variable'] or '无'} |
| Y变量 | {metadata['y_variable'] or '无'} |
| 结果类型 | {', '.join(metadata['result_types'])} |
| 案例总数 | {metadata['total_cases']} |"""

    def _build_md_single_variable_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """构建单变量元数据部分"""
        return f"""## 分析元数据

| 属性 | 值 |
|------|-----|
| Suite名称 | {metadata['suite_name']} |
| 模型名称 | {metadata['model_name']} |
| 分析模式 | 单变量分析 |
| 目标变量 | {metadata['target_variable']} |
| 固定参数 | {metadata['fixed_params_summary']} |
| 筛选案例数 | {metadata['filtered_cases']} |
| 总案例数 | {metadata['total_cases']} |
| 结果类型 | {', '.join(metadata['result_types'])} |"""

    def _build_md_variance_section(self, analysis_data: Dict[str, Any]) -> str:
        """构建方差说明部分"""
        variance_explanation = VarianceExplainer.explain_variance_significance(analysis_data)
        variance_table = VarianceExplainer.build_variance_table(analysis_data)

        return f"""## 方差分析

### 方差意义说明

{variance_explanation}

### 方差统计表

{variance_table}"""

    def _build_md_results_section(self, analysis_data: Dict[str, Any],
                                 regression_results: Dict[str, Dict[str, Any]],
                                 images_info: Dict[str, str]) -> str:
        """构建结果部分"""
        return self._build_md_results_common(analysis_data, regression_results, images_info)

    def _build_md_single_variable_results_section(self, analysis_data: Dict[str, Any],
                                                 regression_results: Dict[str, Dict[str, Any]],
                                                 images_info: Dict[str, str],
                                                 target_variable: str) -> str:
        """构建单变量结果部分"""
        return self._build_md_results_common(analysis_data, regression_results, images_info)

    def _build_md_results_common(self, analysis_data: Dict[str, Any],
                                regression_results: Dict[str, Dict[str, Any]],
                                images_info: Dict[str, str]) -> str:
        """构建通用结果部分"""
        result_md = ["## 分析结果"]

        # 构建结果表格
        result_md.append(self._build_md_results_table(analysis_data))

        # 添加图表
        for result_type in analysis_data.get('data', {}):
            result_md.append(f"\n### {result_type.upper()} 结果")

            # 散点图
            if f'{result_type}_scatter' in images_info:
                result_md.append(f"""
![{result_type}散点图]({images_info[f'{result_type}_scatter']})""")

            # 回归图
            if f'{result_type}_regression' in images_info:
                result_md.append(f"""
![{result_type}回归分析图]({images_info[f'{result_type}_regression']})""")

        return "\n".join(result_md)

    def _build_md_results_table(self, analysis_data: Dict[str, Any]) -> str:
        " ""构建结果表格"""
        table_md = ["### 数据汇总\n"]
        table_md.append("| 结果类型 | 案例数 | 平均性能 | 标准差 | 单位 |")
        table_md.append("|----------|--------|----------|--------|------|")

        for result_type, data in analysis_data.get('data', {}).items():
            if not data.get('mean_values'):
                continue

            mean_values = [v for v in data.get('mean_values', []) if v is not None]
            std_values = [v for v in data.get('std_values', []) if v is not None]

            avg_performance = sum(mean_values) / len(mean_values) if mean_values else 0
            avg_std = sum(std_values) / len(std_values) if std_values else 0
            unit = data.get('units', [])[0] if data.get('units') else "tokens/sec"

            table_md.append(f"| {result_type.upper()} | {len(mean_values)} | {avg_performance:.4f} | {avg_std:.4f} | {unit} |")

        return "\n".join(table_md)

    def _build_md_regression_details(self, regression_results: Dict[str, Dict[str, Any]],
                                   x_label: str) -> str:
        """构建回归分析详情"""
        md = ["## 回归分析详情\n"]

        for result_type, reg_result in regression_results.items():
            md.append(f"### {result_type.upper()} 回归分析\n")
            md.append("```")
            md.append(f"回归方程: {reg_result.get('equation', 'N/A')}")
            md.append(f"R² 值: {reg_result.get('regression', {}).get('r2', 'N/A')}")
            md.append(f"回归方法: {reg_result.get('regression', {}).get('method', 'N/A')}")
            md.append("```\n")

        return "\n".join(md)

    def _build_md_single_variable_regression_details(self, regression_results: Dict[str, Dict[str, Any]],
                                                    x_label: str) -> str:
        """构建单变量回归分析详情"""
        return self._build_md_regression_details(regression_results, x_label)

    def _build_header(self, suite_info: Dict[str, Any],
                     analysis_title: str,
                     **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_md_header(suite_info, kwargs.get('target_variable'),
                                    kwargs.get('x_variable'), kwargs.get('y_variable'))

    def _build_metadata_section(self, suite_info: Dict[str, Any],
                               analysis_data: Dict[str, Any],
                               **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_md_metadata_section(
            MetadataBuilder.build_general_metadata(
                suite_info, analysis_data,
                kwargs.get('x_variable'),
                kwargs.get('y_variable')
            )
        )

    def _build_variance_section(self, analysis_data: Dict[str, Any]) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_md_variance_section(analysis_data)

    def _build_results_section(self, analysis_data: Dict[str, Any],
                              regression_results: Dict[str, Dict[str, Any]],
                              images_info: Dict[str, str],
                              **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        if kwargs.get('target_variable'):
            return self._build_md_single_variable_results_section(
                analysis_data, regression_results, images_info, kwargs['target_variable']
            )
        else:
            return self._build_md_results_section(
                analysis_data, regression_results, images_info
            )