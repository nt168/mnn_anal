#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML报告格式化器

提供HTML格式的分析报告生成功能
"""

from typing import Dict, Any, Optional
from .base import BaseFormatter, MetadataBuilder, VarianceExplainer
from ..utils import transform_variable_name, transform_english_name, format_analysis_title, extract_result_units


class HTMLFormatter(BaseFormatter):
    """HTML报告格式化器"""

    def build_report(self, analysis_data: Dict[str, Any],
                    regression_results: Dict[str, Dict[str, Any]],
                    suite_info: Dict[str, Any],
                    **kwargs) -> str:
        """
        构建HTML报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            **kwargs: 其他参数

        Returns:
            HTML格式的报告内容
        """
        # 根据参数决定报告类型
        x_variable = kwargs.get('x_variable')
        y_variable = kwargs.get('y_variable')
        target_variable = kwargs.get('target_variable')
        fixed_params = kwargs.get('fixed_params')

        if target_variable:
            return self.build_single_variable_html(
                analysis_data, regression_results, suite_info,
                target_variable, fixed_params, kwargs.get('images_info', {})
            )
        else:
            return self.build_complete_html(
                analysis_data, regression_results, suite_info,
                x_variable, y_variable, kwargs.get('images_info', {})
            )

    def build_complete_html(self, analysis_data: Dict[str, Any],
                           regression_results: Dict[str, Dict[str, Any]],
                           suite_info: Dict[str, Any],
                           x_variable: Optional[str], y_variable: Optional[str],
                           images_info: Dict[str, str]) -> str:
        """
        构建完整的HTML报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            x_variable: X变量名
            y_variable: Y变量名
            images_info: 图像信息

        Returns:
            完整的HTML报告内容
        """
        # 构建HTML各部分
        html_parts = []

        # HTML头部和样式
        html_parts.append(self._build_html_head())

        # 报告头部信息
        html_parts.append(self._build_html_header(suite_info, None, x_variable, y_variable))

        # 元数据部分
        metadata = MetadataBuilder.build_general_metadata(
            suite_info, analysis_data, x_variable, y_variable
        )
        html_parts.append(self._build_html_metadata_section(metadata))

        # 方差说明部分
        html_parts.append(self._build_html_variance_section(analysis_data))

        # 结果表格和图表
        html_parts.append(self._build_html_results_section(
            analysis_data, regression_results, images_info
        ))

        # 回归分析详情
        html_parts.append(self._build_html_regression_details(
            regression_results, transform_english_name(x_variable) if x_variable else "X"
        ))

        # HTML结尾
        html_parts.append(self._build_html_footer())

        return "\n".join(html_parts)

    def build_single_variable_html(self, analysis_data: Dict[str, Any],
                                  regression_results: Dict[str, Dict[str, Any]],
                                  suite_info: Dict[str, Any],
                                  target_variable: str, fixed_params: Optional[Dict[str, Any]],
                                  images_info: Dict[str, str]) -> str:
        """
        构建单变量分析HTML报告

        Args:
            analysis_data: 分析数据
            regression_results: 回归结果
            suite_info: Suite信息
            target_variable: 目标变量名
            fixed_params: 固定参数
            images_info: 图像信息

        Returns:
            单变量分析的HTML报告内容
        """
        # 构建HTML各部分
        html_parts = []

        # HTML头部和样式
        html_parts.append(self._build_html_head())

        # 报告头部信息
        html_parts.append(self._build_html_header(suite_info, target_variable, None, None))

        # 元数据部分
        metadata = MetadataBuilder.build_single_variable_metadata(
            suite_info, analysis_data, target_variable, fixed_params
        )
        html_parts.append(self._build_html_single_variable_metadata_section(metadata))

        # 方差说明部分
        html_parts.append(self._build_html_variance_section(analysis_data))

        # 结果表格和图表
        html_parts.append(self._build_html_single_variable_results_section(
            analysis_data, regression_results, images_info, target_variable
        ))

        # 回归分析详情
        html_parts.append(self._build_html_single_variable_regression_details(
            regression_results, transform_english_name(target_variable)
        ))

        # HTML结尾
        html_parts.append(self._build_html_footer())

        return "\n".join(html_parts)

    def _build_html_head(self) -> str:
        """构建HTML头部"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MNN LLM 基准测试分析报告</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }
        .metadata-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: #f8f9fa;
        }
        .metadata-table th, .metadata-table td {
            border: 1px solid #dee2e6;
            padding: 12px;
            text-align: left;
        }
        .metadata-table th {
            background-color: #3498db;
            color: white;
        }
        .result-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .result-table th, .result-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }
        .result-table th {
            background-color: #e74c3c;
            color: white;
        }
        .image-container {
            text-align: center;
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ecf0f1;
            border-radius: 5px;
            background-color: #fafafa;
        }
        .image-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
        }
        .variance-box {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .regression-box {
            background-color: #d1f2eb;
            border: 1px solid #a3e4d7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-family: monospace;
        }
        .stats-table th, .stats-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
    </style>
</head>
<body>"""

    def _build_html_header(self, suite_info: Dict[str, Any],
                          target_variable: Optional[str],
                          x_variable: Optional[str],
                          y_variable: Optional[str]) -> str:
        """构建HTML报告头部"""
        suite_name = suite_info['name']
        model_name = suite_info['model_name']
        timestamp = suite_info.get('timestamp', '')

        if target_variable:
            title = f"{suite_name} 单变量分析报告 - {transform_variable_name(target_variable)}"
            intro = f"<p>本报告对<strong>{suite_name}</strong>套件中变量<strong>{transform_variable_name(target_variable)}</strong>的性能影响进行了详细分析。</p>"
        elif x_variable and y_variable:
            title = f"{suite_name} 相关性分析报告 - {transform_variable_name(x_variable)} vs {transform_variable_name(y_variable)}"
            intro = f"<p>本报告分析了<strong>{suite_name}</strong>套件中变量<strong>{transform_variable_name(x_variable)}</strong>和<strong>{transform_variable_name(y_variable)}</strong>之间的相关性。</p>"
        elif x_variable:
            title = f"{suite_name} 分析报告 - {transform_variable_name(x_variable)}"
            intro = f"<p>本报告对<strong>{suite_name}</strong>套件中变量<strong>{transform_variable_name(x_variable)}</strong>的性能影响进行了分析。</p>"
        else:
            title = f"{suite_name} 性能分析报告"
            intro = f"<p>本报告对<strong>{suite_name}</strong>套件进行了全面的性能分析。</p>"

        return f"""
    <div class="container">
        <h1>{title}</h1>
        <div class="header-info">
            <p><strong>模型:</strong> {model_name}</p>
            <p><strong>分析时间:</strong> {timestamp}</p>
            {intro}
        </div>"""

    def _build_html_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """构建元数据部分"""
        return f"""
        <h2>分析元数据</h2>
        <table class="metadata-table">
            <tr><th>属性</th><th>值</th></tr>
            <tr><td>Suite名称</td><td>{metadata['suite_name']}</td></tr>
            <tr><td>模型名称</td><td>{metadata['model_name']}</td></tr>
            <tr><td>分析模式</td><td>{metadata['analysis_mode']}</td></tr>
            <tr><td>X变量</td><td>{metadata['x_variable'] or '无'}</td></tr>
            <tr><td>Y变量</td><td>{metadata['y_variable'] or '无'}</td></tr>
            <tr><td>结果类型</td><td>{', '.join(metadata['result_types'])}</td></tr>
            <tr><td>案例总数</td><td>{metadata['total_cases']}</td></tr>
        </table>"""

    def _build_html_single_variable_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """构建单变量元数据部分"""
        return f"""
        <h2>分析元数据</h2>
        <table class="metadata-table">
            <tr><th>属性</th><th>值</th></tr>
            <tr><td>Suite名称</td><td>{metadata['suite_name']}</td></tr>
            <tr><td>模型名称</td><td>{metadata['model_name']}</td></tr>
            <tr><td>分析模式</td><td>单变量分析</td></tr>
            <tr><td>目标变量</td><td>{metadata['target_variable']}</td></tr>
            <tr><td>固定参数</td><td>{metadata['fixed_params_summary']}</td></tr>
            <tr><td>筛选案例数</td><td>{metadata['filtered_cases']}</td></tr>
            <tr><td>总案例数</td><td>{metadata['total_cases']}</td></tr>
            <tr><td>结果类型</td><td>{', '.join(metadata['result_types'])}</td></tr>
        </table>"""

    def _build_html_variance_section(self, analysis_data: Dict[str, Any]) -> str:
        """构建方差说明部分"""
        variance_explanation = VarianceExplainer.explain_variance_significance(analysis_data)
        variance_table = VarianceExplainer.build_variance_table(analysis_data)

        return f"""
        <h2>方差分析</h2>
        <div class="variance-box">
            <h3>方差意义说明</h3>
            <p>{variance_explanation}</p>
        </div>
        <div class="variance-box">
            <h3>方差统计表</h3>
            <table class="stats-table">
                {variance_table}
            </table>
        </div>"""

    def _build_html_results_section(self, analysis_data: Dict[str, Any],
                                   regression_results: Dict[str, Dict[str, Any]],
                                   images_info: Dict[str, str]) -> str:
        """构建结果部分"""
        return self._build_html_results_common(analysis_data, regression_results, images_info)

    def _build_html_single_variable_results_section(self, analysis_data: Dict[str, Any],
                                                  regression_results: Dict[str, Dict[str, Any]],
                                                  images_info: Dict[str, str],
                                                  target_variable: str) -> str:
        """构建单变量结果部分"""
        return self._build_html_results_common(analysis_data, regression_results, images_info)

    def _build_html_results_common(self, analysis_data: Dict[str, Any],
                                  regression_results: Dict[str, Dict[str, Any]],
                                  images_info: Dict[str, str]) -> str:
        """构建通用结果部分"""
        result_html = ["<h2>分析结果</h2>"]

        # 构建结果表格
        result_html.append(self._build_html_results_table(analysis_data))

        # 添加图表
        for result_type in analysis_data.get('data', {}):
            result_html.append(f"<h3>{result_type.upper()} 结果</h3>")

            # 散点图
            if f'{result_type}_scatter' in images_info:
                result_html.append(f"""
            <div class="image-container">
                <h4>散点图</h4>
                <img src="{images_info[f'{result_type}_scatter']}" alt="{result_type} Scatter Plot">
            </div>""")

            # 回归图
            if f'{result_type}_regression' in images_info:
                result_html.append(f"""
            <div class="image-container">
                <h4>回归分析图</h4>
                <img src="{images_info[f'{result_type}_regression']}" alt="{result_type} Regression Plot">
            </div>""")

        return "\n".join(result_html)

    def _build_html_results_table(self, analysis_data: Dict[str, Any]) -> str:
        """构建结果表格"""
        html = """
        <div class="result-summary">
            <h3>数据汇总</h3>
            <table class="result-table">
                <thead>
                    <tr>
                        <th>结果类型</th>
                        <th>案例数</th>
                        <th>平均性能</th>
                        <th>标准差</th>
                        <th>单位</th>
                    </tr>
                </thead>
                <tbody>"""

        for result_type, data in analysis_data.get('data', {}).items():
            if not data.get('mean_values'):
                continue

            mean_values = [v for v in data.get('mean_values', []) if v is not None]
            std_values = [v for v in data.get('std_values', []) if v is not None]

            avg_performance = sum(mean_values) / len(mean_values) if mean_values else 0
            avg_std = sum(std_values) / len(std_values) if std_values else 0
            unit = data.get('units', [])[0] if data.get('units') else "tokens/sec"

            html += f"""
                    <tr>
                        <td>{result_type.upper()}</td>
                        <td>{len(mean_values)}</td>
                        <td>{avg_performance:.4f}</td>
                        <td>{avg_std:.4f}</td>
                        <td>{unit}</td>
                    </tr>"""

        html += """
                </tbody>
            </table>
        </div>"""

        return html

    def _build_html_regression_details(self, regression_results: Dict[str, Dict[str, Any]],
                                      x_label: str) -> str:
        """构建回归分析详情"""
        html = ["<h2>回归分析详情</h2>"]

        for result_type, reg_result in regression_results.items():
            html.append(f"<h3>{result_type.upper()} 回归分析</h3>")
            html.append("<div class='regression-box'>")
            html.append("<table class='stats-table'>")
            html.append(f"<tr><th>回归方程</th><td>{reg_result.get('equation', 'N/A')}</td></tr>")
            html.append(f"<tr><th>R² 值</th><td>{reg_result.get('regression', {}).get('r2', 'N/A')}</td></tr>")
            html.append(f"<tr><th>回归方法</th><td>{reg_result.get('regression', {}).get('method', 'N/A')}</td></tr>")
            html.append("</table>")
            html.append("</div>")

        return "\n".join(html)

    def _build_html_single_variable_regression_details(self, regression_results: Dict[str, Dict[str, Any]],
                                                      x_label: str) -> str:
        """构建单变量回归分析详情"""
        return self._build_html_regression_details(regression_results, x_label)

    def _build_html_footer(self) -> str:
        """构建HTML结尾"""
        return """
        <div class="footer">
            <p>本报告由 MNN LLM 基准测试系统生成</p>
        </div>
    </div>
</body>
</html>"""

    def _build_header(self, suite_info: Dict[str, Any],
                     analysis_title: str,
                     **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_html_header(suite_info, kwargs.get('target_variable'),
                                      kwargs.get('x_variable'), kwargs.get('y_variable'))

    def _build_metadata_section(self, suite_info: Dict[str, Any],
                               analysis_data: Dict[str, Any],
                               **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_html_metadata_section(
            MetadataBuilder.build_general_metadata(
                suite_info, analysis_data,
                kwargs.get('x_variable'),
                kwargs.get('y_variable')
            )
        )

    def _build_variance_section(self, analysis_data: Dict[str, Any]) -> str:
        """实现基类方法（供兼容性）"""
        return self._build_html_variance_section(analysis_data)

    def _build_results_section(self, analysis_data: Dict[str, Any],
                              regression_results: Dict[str, Dict[str, Any]],
                              images_info: Dict[str, str],
                              **kwargs) -> str:
        """实现基类方法（供兼容性）"""
        if kwargs.get('target_variable'):
            return self._build_html_single_variable_results_section(
                analysis_data, regression_results, images_info, kwargs['target_variable']
            )
        else:
            return self._build_html_results_section(
                analysis_data, regression_results, images_info
            )