#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
precision参数影响分析工具
功能：分析precision参数对MNN LLM推理性能的影响
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

class PrecisionAnalyzer:
    def __init__(self, db_path="benchmark_results.db"):
        """初始化precision分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "precision_analysis")
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

    def get_precision_data(self):
        """获取precision测试数据"""
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
            WHERE s.name = 'precision_effect_t1'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)

            # 解析base_parameters中的precision值
            df['precision_value'] = df['base_parameters'].apply(
                lambda x: eval(x).get('precision', -1)
            )

            # 转换为中文描述
            precision_map = {0: 'Normal', 1: 'High', 2: 'Low'}
            df['precision_desc'] = df['precision_value'].map(precision_map)

            return df
        except Exception as e:
            print(f"获取precision数据失败: {e}")
            return pd.DataFrame()

    def analyze_by_model_and_type(self, df):
        """按模型和结果类型分别分析"""
        results = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]
            model_results = {}

            for result_type in model_data['result_type'].unique():
                type_data = model_data[model_data['result_type'] == result_type]

                if len(type_data) >= 2:  # 确保至少有两个精度级别的数据
                    # 基础统计分析
                    stats = {
                        'data_points': len(type_data),
                        'min_precision': type_data['precision_value'].min(),
                        'max_precision': type_data['precision_value'].max(),
                        'min_performance': type_data['mean_value'].min(),
                        'max_performance': type_data['mean_value'].max(),
                        'avg_performance': type_data['mean_value'].mean(),
                        'performance_std': type_data['mean_value'].std(),
                        'min_cv': type_data['cv_value'].min(),
                        'max_cv': type_data['cv_value'].max(),
                        'avg_cv': type_data['cv_value'].mean()
                    }

                    # 计算性能变化的范围
                    if len(type_data) > 1:
                        performance_range = stats['max_performance'] - stats['min_performance']
                        performance_coefficient_of_variation = (stats['performance_std'] / stats['avg_performance']) * 100

                        stats.update({
                            'performance_range': performance_range,
                            'performance_cv_percent': performance_coefficient_of_variation,
                            'max_performance_percent_change': (performance_range / stats['avg_performance']) * 100
                        })

                    # 按精度级别分离分析
                    precision_stats = {}
                    for precision_val in sorted(type_data['precision_value'].unique()):
                        prec_data = type_data[type_data['precision_value'] == precision_val]
                        if not prec_data.empty:
                            precision_map = {0: 'Normal', 1: 'High', 2: 'Low'}
                            prec_desc = precision_map[precision_val]
                            precision_stats[prec_desc] = {
                                'performance': prec_data['mean_value'].mean(),
                                'std': prec_data['mean_value'].std() if len(prec_data) > 1 else 0,
                                'cv': prec_data['cv_value'].mean()
                            }

                    # 寻找最佳和最差性能的精度级别
                    best_perf_idx = type_data['mean_value'].idxmax()
                    worst_perf_idx = type_data['mean_value'].idxmin()

                    best_row = type_data.loc[best_perf_idx]
                    worst_row = type_data.loc[worst_perf_idx]

                    precision_map = {0: 'Normal', 1: 'High', 2: 'Low'}
                    stats.update({
                        'precision_levels': precision_stats,
                        'best_precision': precision_map[best_row['precision_value']],
                        'best_performance': best_row['mean_value'],
                        'best_cv': best_row['cv_value'],
                        'worst_precision': precision_map[worst_row['precision_value']],
                        'worst_performance': worst_row['mean_value'],
                        'worst_cv': worst_row['cv_value']
                    })

                    # Normal vs High vs Low的具体比较
                    if 'Normal' in precision_stats and 'High' in precision_stats:
                        stats['normal_vs_high'] = {
                            'diff': precision_stats['Normal']['performance'] - precision_stats['High']['performance'],
                            'percent_change': ((precision_stats['Normal']['performance'] - precision_stats['High']['performance']) / precision_stats['High']['performance']) * 100
                        }

                    if 'Normal' in precision_stats and 'Low' in precision_stats:
                        stats['normal_vs_low'] = {
                            'diff': precision_stats['Normal']['performance'] - precision_stats['Low']['performance'],
                            'percent_change': ((precision_stats['Normal']['performance'] - precision_stats['Low']['performance']) / precision_stats['Low']['performance']) * 100
                        }

                    model_results[result_type] = {
                        'statistics': stats,
                        'raw_data': type_data
                    }

            results[model] = model_results

        return results

    def create_performance_scatter_plot(self, df, save_path=None):
        """创建precision性能散点图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}
            markers = {0: 'o', 1: 's', 2: '^'}  # Normal, High, Low

            # 按结果类型分别绘制
            for idx, result_type in enumerate(df['result_type'].unique()):
                ax = axes[idx]
                type_data = df[df['result_type'] == result_type]

                for model in df['model_name'].unique():
                    model_data = type_data[type_data['model_name'] == model]

                    if not model_data.empty:
                        # 散点图，按精度级别用不同标记
                        unique_precisions = sorted(model_data['precision_value'].unique())
                        for precision_val in unique_precisions:
                            prec_data = model_data[model_data['precision_value'] == precision_val]
                            label = f'{model} precision={precision_val}'

                            ax.scatter(prec_data['precision_value'], prec_data['mean_value'],
                                      c=colors[model], s=120, alpha=0.7, label=label,
                                      marker=markers[precision_val], edgecolors='white', linewidth=1)

                        # 误差棒
                        ax.errorbar(model_data['precision_value'], model_data['mean_value'],
                                   yerr=model_data['std_value'],
                                   fmt='none', ecolor=colors[model], alpha=0.5, capsize=3)

                ax.set_xlabel('Precision Level\n(0=Normal, 1=High, 2=Low)')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title(f'{result_type.upper()} Performance vs Precision Level')
                ax.set_xticks([0, 1, 2])
                ax.set_xticklabels(['Normal\n(0)', 'High\n(1)', 'Low\n(2)'])
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

    def create_precision_comparison_plot(self, analysis_results, save_path=None):
        """创建精度级别对比图"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Precision Performance Comparison', fontsize=16)

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}
            precision_names = ['Normal', 'High', 'Low']
            precision_values = [0, 1, 2]
            result_types = ['pp', 'tg']
            models = list(analysis_results.keys())

            # 遍历结果类型和模型
            for type_idx, result_type in enumerate(result_types):
                for model_idx, model in enumerate(models):
                    ax = axes[type_idx, model_idx]

                    if result_type in analysis_results[model]:
                        precision_stats = analysis_results[model][result_type]['statistics']['precision_levels']
                        performances = []
                        precisions = []
                        labels = []

                        for prec_name, prec_val in zip(precision_names, precision_values):
                            if prec_name in precision_stats:
                                performances.append(precision_stats[prec_name]['performance'])
                                precisions.append(prec_val)
                                labels.append(f'{prec_name}')
                            else:
                                performances.append(np.nan)
                                precisions.append(prec_val)
                                labels.append(f'{prec_name}\n(N/A)')

                        # 绘制柱状图
                        bars = ax.bar(precisions, performances, color=colors[model], alpha=0.7, width=0.6)

                        # 添加数值标签
                        for bar, perf, label in zip(bars, performances, labels):
                            height = bar.get_height()
                            if not np.isnan(height):
                                ax.text(bar.get_x() + bar.get_width()/2., height,
                                       f'{perf:.1f}',
                                       ha='center', va='bottom', fontsize=8)

                        ax.set_xlabel('Precision Level')
                        ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                        ax.set_title(f'{model} - {result_type.upper()}')
                        ax.set_xticks(precision_values)
                        ax.set_xticklabels(labels)
                        ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建精度对比图失败: {e}")
            plt.close()

    
    def generate_report(self, analysis_results):
        """生成precision分析报告"""
        report = f"""# precision参数影响分析报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: benchmark_results.db
分析范围: precision_effect_t1 test suite
参数对比: precision=0 (Normal) vs 1 (High) vs 2 (Low)
精度说明:
- Normal (0): 基础精度，CPU后端为High精度
- High (1): 高精度模式
- Low (2): 低精度模式，提升性能

---

## 分析结果

"""

        for model_name, model_data in analysis_results.items():
            report += f"### {model_name}\n\n"

            for result_type, type_data in model_data.items():
                stats = type_data['statistics']

                report += f"#### {result_type.upper()} 结果\n"
                report += f"- 数据点数: {stats['data_points']}\n"
                report += f"- 精度级别范围: {stats['min_precision']} - {stats['max_precision']}\n"
                report += f"- 性能范围: {stats['min_performance']:.2f} - {stats['max_performance']:.2f} tokens/sec\n"
                report += f"- 平均性能: {stats['avg_performance']:.2f} ± {stats['performance_std']:.2f} tokens/sec\n"
                report += f"- 性能变化范围: {stats['performance_range']:.2f} tokens/sec\n"
                report += f"- 最大性能变化百分比: {stats['max_performance_percent_change']:.2f}%\n"
                report += f"- CV值范围: {stats['min_cv']:.3f}% - {stats['max_cv']:.3f}% (平均: {stats['avg_cv']:.3f}%)\n"
                report += f"- 最优精度: {stats['best_precision']}, 性能={stats['best_performance']:.2f} tokens/sec\n"
                report += f"- 最差精度: {stats['worst_precision']}, 性能={stats['worst_performance']:.2f} tokens/sec\n\n"

                # 精度级别详细数据
                report += "##### 各精度级别性能:\n"
                for prec_name, prec_stats in stats['precision_levels'].items():
                    report += f"- {prec_name}: {prec_stats['performance']:.2f} ± {prec_stats['std']:.2f} tokens/sec (CV: {prec_stats['cv']:.3f}%)\n"
                report += "\n"

                # 精度对比
                if 'normal_vs_high' in stats:
                    comp = stats['normal_vs_high']
                    report += f"##### Normal vs High 精度对比:\n"
                    report += f"- 性能差异: {comp['diff']:.2f} tokens/sec\n"
                    report += f"- 相对变化: {comp['percent_change']:.2f}%\n\n"

                if 'normal_vs_low' in stats:
                    comp = stats['normal_vs_low']
                    report += f"##### Normal vs Low 精度对比:\n"
                    report += f"- 性能差异: {comp['diff']:.2f} tokens/sec\n"
                    report += f"- 相对变化: {comp['percent_change']:.2f}%\n\n"

            report += "---\n\n"

        # 参数优化建议表
        report += "## 精度模式优化建议表\n\n"
        report += "| 模型 | PP最优精度 | TG最优精度 | PP性能范围 | TG性能范围 | PP Normal vs High | PP Normal vs Low | TG Normal vs High | TG Normal vs Low |\n"
        report += "|------|------------|------------|------------|------------|------------------|------------------|------------------|------------------|\n"

        for model_name, model_data in analysis_results.items():
            pp_best = pp_range = "N/A"
            tg_best = tg_range = "N/A"
            pp_nh = pp_nl = tg_nh = tg_nl = "N/A"

            if 'pp' in model_data:
                pp_stats = model_data['pp']['statistics']
                pp_best = pp_stats['best_precision']
                pp_range = f"{pp_stats['min_performance']:.1f}-{pp_stats['max_performance']:.1f}"
                if 'normal_vs_high' in pp_stats:
                    pp_nh = f"{pp_stats['normal_vs_high']['percent_change']:.2f}%"
                if 'normal_vs_low' in pp_stats:
                    pp_nl = f"{pp_stats['normal_vs_low']['percent_change']:.2f}%"

            if 'tg' in model_data:
                tg_stats = model_data['tg']['statistics']
                tg_best = tg_stats['best_precision']
                tg_range = f"{tg_stats['min_performance']:.1f}-{tg_stats['max_performance']:.1f}"
                if 'normal_vs_high' in tg_stats:
                    tg_nh = f"{tg_stats['normal_vs_high']['percent_change']:.2f}%"
                if 'normal_vs_low' in tg_stats:
                    tg_nl = f"{tg_stats['normal_vs_low']['percent_change']:.2f}%"

            report += f"| {model_name} | {pp_best} | {tg_best} | {pp_range} | {tg_range} | {pp_nh} | {pp_nl} | {tg_nh} | {tg_nl} |\n"

        report += "\n![性能散点图](precision_performance_scatter.png)\n\n"
        report += "![精度对比分析](precision_comparison.png)\n\n"
        
        return report

    def run_analysis(self):
        """执行完整的precision分析流程"""
        print("开始precision参数分析...")

        # 获取数据
        df = self.get_precision_data()
        if df.empty:
            print("未找到precision测试数据")
            return

        print(f"找到 {len(df)} 条precision测试数据")

        # 按模型分析
        print("进行统计分析...")
        analysis_results = self.analyze_by_model_and_type(df)

        # 生成图表
        print("生成图表...")
        self.create_performance_scatter_plot(df, f'{self.output_dir}/precision_performance_scatter.png')
        self.create_precision_comparison_plot(analysis_results, f'{self.output_dir}/precision_comparison.png')
        
        # 导出数据
        df.to_csv(f'{self.output_dir}/precision_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        report = self.generate_report(analysis_results)

        with open(f'{self.output_dir}/precision_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("precision分析完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = PrecisionAnalyzer()
    analyzer.run_analysis()