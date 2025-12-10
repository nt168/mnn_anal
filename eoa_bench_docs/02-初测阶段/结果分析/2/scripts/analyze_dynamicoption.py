#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dynamicOption参数影响分析工具
功能：分析dynamicOption参数对MNN LLM推理性能的影响
作者：EAO项目团队
日期：2025年11月27日
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
from datetime import datetime

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class DynamicOptionAnalyzer:
    def __init__(self, db_path="benchmark_results.db"):
        """初始化dynamicOption分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "dynamicoption_analysis")
        os.makedirs(self.output_dir, exist_ok=True)
        self.connect_db()

    def connect_db(self):
        """连接SQLite数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if self.conn:
            self.conn.close()

    def get_dynamicoption_data(self):
        """获取dynamicOption测试数据"""
        try:
            query = """
            SELECT
                s.model_name,
                cd.base_parameters,
                br.result_type,
                br.result_parameter,
                br.mean_value,
                br.std_value,
                (br.std_value/br.mean_value*100) as cv_value
            FROM benchmark_results br
            JOIN case_definitions cd ON br.case_id = cd.id
            JOIN suites s ON cd.suite_id = s.id
            WHERE s.name = 'dynamic_option_effect_t1'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)

            # 解析base_parameters中的dynamicOption值
            df['dynamic_option'] = df['base_parameters'].apply(
                lambda x: eval(x).get('dynamicOption', 'unknown')
            )

            # 转换为数值
            df['dynamic_option'] = pd.to_numeric(df['dynamic_option'], errors='coerce')
            df = df.dropna(subset=['dynamic_option'])
            df['dynamic_option'] = df['dynamic_option'].astype(int)

            return df
        except Exception as e:
            print(f"获取dynamicOption数据失败: {e}")
            return pd.DataFrame()

    def analyze_by_model_and_type(self, df):
        """按模型和结果类型分别分析"""
        results = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]
            model_results = {}

            for result_type in model_data['result_type'].unique():
                type_data = model_data[model_data['result_type'] == result_type]

                if len(type_data) >= 2:  # 确保有足够的数据点
                    # 基础统计分析
                    stats = {
                        'data_points': len(type_data),
                        'min_dopt': type_data['dynamic_option'].min(),
                        'max_dopt': type_data['dynamic_option'].max(),
                        'min_performance': type_data['mean_value'].min(),
                        'max_performance': type_data['mean_value'].max(),
                        'avg_performance': type_data['mean_value'].mean(),
                        'performance_std': type_data['mean_value'].std(),
                        'min_cv': type_data['cv_value'].min(),
                        'max_cv': type_data['cv_value'].max(),
                        'avg_cv': type_data['cv_value'].mean()
                    }

                    # 计算性能变化的范围和方差
                    if len(type_data) > 1:
                        performance_range = stats['max_performance'] - stats['min_performance']
                        performance_coefficient_of_variation = (stats['performance_std'] / stats['avg_performance']) * 100

                        stats.update({
                            'performance_range': performance_range,
                            'performance_cv_percent': performance_coefficient_of_variation,
                            'max_performance_percent_change': (performance_range / stats['avg_performance']) * 100
                        })

                    # 寻找最佳和最差性能的dynamicOption值
                    best_perf_idx = type_data['mean_value'].idxmax()
                    worst_perf_idx = type_data['mean_value'].idxmin()

                    best_row = type_data.loc[best_perf_idx]
                    worst_row = type_data.loc[worst_perf_idx]

                    stats.update({
                        'best_dynamic_option': best_row['dynamic_option'],
                        'best_performance': best_row['mean_value'],
                        'best_cv': best_row['cv_value'],
                        'worst_dynamic_option': worst_row['dynamic_option'],
                        'worst_performance': worst_row['mean_value'],
                        'worst_cv': worst_row['cv_value']
                    })

                    model_results[result_type] = {
                        'statistics': stats,
                        'raw_data': type_data
                    }

            results[model] = model_results

        return results

    def create_performance_scatter_plot(self, df, save_path=None):
        """创建dynamicOption性能散点图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}

            # 按结果类型分别绘制
            for idx, result_type in enumerate(df['result_type'].unique()):
                ax = axes[idx]
                type_data = df[df['result_type'] == result_type]

                for model in df['model_name'].unique():
                    model_data = type_data[type_data['model_name'] == model]

                    if not model_data.empty:
                        # 散点图
                        ax.scatter(model_data['dynamic_option'], model_data['mean_value'],
                                  c=colors[model], s=100, alpha=0.7, label=f'{model}',
                                  edgecolors='white', linewidth=1)

                        # 误差棒
                        ax.errorbar(model_data['dynamic_option'], model_data['mean_value'],
                                   yerr=model_data['std_value'],
                                   fmt='none', ecolor=colors[model], alpha=0.5, capsize=3)

                ax.set_xlabel('dynamicOption Level')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title(f'{result_type.upper()} Performance vs dynamicOption Level')
                ax.set_xticks(range(0, 9))  # 0-8级别
                ax.grid(True, alpha=0.3)

                # 只在第一个子图显示图例
                if idx == 0:
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建性能散点图失败: {e}")
            plt.close()

    def create_trend_analysis_plot(self, analysis_results, save_path=None):
        """创建趋势分析图"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('dynamicOption Performance Trend Analysis', fontsize=16)

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}
            result_types = ['pp', 'tg']
            models = list(analysis_results.keys())

            # 遍历结果类型和模型
            for type_idx, result_type in enumerate(result_types):
                for model_idx, model in enumerate(models):
                    if result_type in analysis_results[model]:
                        ax = axes[type_idx, model_idx]
                        raw_data = analysis_results[model][result_type]['raw_data']

                        # 排序dynamicOption
                        sorted_data = raw_data.sort_values('dynamic_option')

                        # 绘制性能曲线和散点
                        ax.plot(sorted_data['dynamic_option'], sorted_data['mean_value'],
                               'o-', color=colors[model], markersize=6, linewidth=2, alpha=0.8)

                        # 添加误差棒
                        ax.errorbar(sorted_data['dynamic_option'], sorted_data['mean_value'],
                                   yerr=sorted_data['std_value'],
                                   fmt='none', ecolor=colors[model], alpha=0.5, capsize=3)

                        # 标注最高点
                        best_idx = sorted_data['mean_value'].idxmax()
                        best_point = sorted_data.loc[best_idx]
                        ax.annotate(f"Best: {best_point['dynamic_option']}",
                                   xy=(best_point['dynamic_option'], best_point['mean_value']),
                                   xytext=(10, 10), textcoords='offset points',
                                   fontsize=8, color='red', weight='bold')

                        ax.set_xlabel('dynamicOption Level')
                        ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                        ax.set_title(f'{model} - {result_type.upper()}')
                        ax.set_xticks(range(0, 9))
                        ax.grid(True, alpha=0.3)

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建趋势分析图失败: {e}")
            plt.close()

    def create_stability_plot(self, analysis_results, save_path=None):
        """创建稳定性分析图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

            result_types = ['pp', 'tg']
            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}

            for idx, result_type in enumerate(result_types):
                ax = axes[idx]

                for model in analysis_results.keys():
                    if result_type in analysis_results[model]:
                        raw_data = analysis_results[model][result_type]['raw_data']
                        sorted_data = raw_data.sort_values('dynamic_option')

                        ax.bar(sorted_data['dynamic_option'], sorted_data['cv_value'],
                               alpha=0.7, color=colors[model], label=f'{model}',
                               width=0.8)

                ax.set_xlabel('dynamicOption Level')
                ax.set_ylabel('Coefficient of Variation CV (%)')
                ax.set_title(f'{result_type.upper()} Stability by dynamicOption Level')
                ax.set_xticks(range(0, 9))
                ax.legend()
                ax.grid(True, alpha=0.3)

                # 添加参考线
                ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='1% CV Reference')

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建稳定性分析图失败: {e}")
            plt.close()

    def generate_report(self, analysis_results):
        """生成dynamicOption分析报告"""
        report = f"""# dynamicOption参数影响分析报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: benchmark_results.db
分析范围: dynamic_option_effect_t1 test suite
参数范围: dynamicOption 0-8 (共9个级别)

---

## 分析结果

"""

        for model_name, model_data in analysis_results.items():
            report += f"### {model_name}\n\n"

            for result_type, type_data in model_data.items():
                stats = type_data['statistics']

                report += f"#### {result_type.upper()} 结果\n"
                report += f"- 数据点数: {stats['data_points']}\n"
                report += f"- dynamicOption范围: {stats['min_dopt']} - {stats['max_dopt']}\n"
                report += f"- 性能范围: {stats['min_performance']:.2f} - {stats['max_performance']:.2f} tokens/sec\n"
                report += f"- 平均性能: {stats['avg_performance']:.2f} ± {stats['performance_std']:.2f} tokens/sec\n"
                report += f"- 性能变化范围: {stats['performance_range']:.2f} tokens/sec\n"
                report += f"- 最大性能变化百分比: {stats['max_performance_percent_change']:.2f}%\n"
                report += f"- CV值范围: {stats['min_cv']:.3f}% - {stats['max_cv']:.3f}% (平均: {stats['avg_cv']:.3f}%)\n"
                report += f"- 最优设置: dynamicOption={stats['best_dynamic_option']}, 性能={stats['best_performance']:.2f} tokens/sec\n"
                report += f"- 最差设置: dynamicOption={stats['worst_dynamic_option']}, 性能={stats['worst_performance']:.2f} tokens/sec\n"
                report += f"- 性能提升潜在: {(stats['best_performance'] - stats['worst_performance']):.2f} tokens/sec\n\n"

            report += "---\n\n"

        # 参数优化建议表
        report += "## dynamicOption优化建议\n\n"
        report += "| 模型 | PP最优设置 | TG最优设置 | PP性能范围 | TG性能范围 |\n"
        report += "|------|------------|------------|------------|------------|\n"

        for model_name, model_data in analysis_results.items():
            pp_best = pp_range = "N/A"
            tg_best = tg_range = "N/A"

            if 'pp' in model_data:
                pp_stats = model_data['pp']['statistics']
                pp_best = f"Level {pp_stats['best_dynamic_option']}"
                pp_range = f"{pp_stats['min_performance']:.1f}-{pp_stats['max_performance']:.1f}"

            if 'tg' in model_data:
                tg_stats = model_data['tg']['statistics']
                tg_best = f"Level {tg_stats['best_dynamic_option']}"
                tg_range = f"{tg_stats['min_performance']:.1f}-{tg_stats['max_performance']:.1f}"

            report += f"| {model_name} | {pp_best} | {tg_best} | {pp_range} | {tg_range} |\n"

        report += "\n![性能散点图](do_performance_scatter.png)\n\n"
        report += "![趋势分析](do_trend_analysis.png)\n\n"
        report += "![稳定性分析](do_stability_analysis.png)\n\n"

        return report

    def run_analysis(self):
        """执行完整的dynamicOption分析流程"""
        print("开始dynamicOption参数分析...")

        # 获取数据
        df = self.get_dynamicoption_data()
        if df.empty:
            print("未找到dynamicOption测试数据")
            return

        print(f"找到 {len(df)} 条dynamicOption测试数据")

        # 按模型分析
        print("进行统计分析...")
        analysis_results = self.analyze_by_model_and_type(df)

        # 生成图表
        print("生成图表...")
        self.create_performance_scatter_plot(df, f'{self.output_dir}/do_performance_scatter.png')
        self.create_trend_analysis_plot(analysis_results, f'{self.output_dir}/do_trend_analysis.png')
        self.create_stability_plot(analysis_results, f'{self.output_dir}/do_stability_analysis.png')

        # 导出数据
        df.to_csv(f'{self.output_dir}/dynamicoption_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        report = self.generate_report(analysis_results)

        with open(f'{self.output_dir}/dynamicoption_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("dynamicOption分析完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = DynamicOptionAnalyzer()
    analyzer.run_analysis()