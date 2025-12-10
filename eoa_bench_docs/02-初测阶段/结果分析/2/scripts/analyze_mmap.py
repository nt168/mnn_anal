#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mmap参数影响分析工具
功能：分析mmap参数对MNN LLM推理性能的影响
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

class MmapAnalyzer:
    def __init__(self):
        """初始化mmap分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "mmap_analysis")
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

    def get_mmap_data(self):
        """获取mmap测试数据"""
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
            WHERE s.name = 'mmap_effect_t1'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)

            # 解析base_parameters中的mmap值
            df['mmap_value'] = df['base_parameters'].apply(
                lambda x: eval(x).get('mmap', 'unknown')
            )

            return df
        except Exception as e:
            print(f"获取mmap数据失败: {e}")
            return pd.DataFrame()

    def analyze_by_model_and_type(self, df):
        """按模型和结果类型分别分析"""
        results = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]
            model_results = {}

            for result_type in model_data['result_type'].unique():
                type_data = model_data[model_data['result_type'] == result_type]

                if len(type_data) >= 2:  # 确保有mmap=0和mmap=1的数据
                    # 分组统计
                    mm0_data = type_data[type_data['mmap_value'] == '0']
                    mm1_data = type_data[type_data['mmap_value'] == '1']

                    if not mm0_data.empty and not mm1_data.empty:
                        # 计算性能差异
                        perf_diff = mm1_data['mean_value'].mean() - mm0_data['mean_value'].mean()
                        perf_percent_change = (perf_diff / mm0_data['mean_value'].mean()) * 100

                        stats = {
                            'mmap_0_performance': mm0_data['mean_value'].mean(),
                            'mmap_0_std': mm0_data['mean_value'].std(),
                            'mmap_1_performance': mm1_data['mean_value'].mean(),
                            'mmap_1_std': mm1_data['mean_value'].std(),
                            'performance_diff': perf_diff,
                            'performance_percent_change': perf_percent_change,
                            'mmap_0_avg_cv': mm0_data['cv_value'].mean(),
                            'mmap_1_avg_cv': mm1_data['cv_value'].mean()
                        }

                        model_results[result_type] = {
                            'statistics': stats,
                            'raw_data': type_data
                        }

            results[model] = model_results

        return results

    def create_comparison_plot(self, df, save_path=None):
        """创建mmap对比散点图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}
            markers = {'0': 'o', '1': 's'}

            # 按结果类型分别绘制
            for idx, result_type in enumerate(df['result_type'].unique()):
                ax = axes[idx]
                type_data = df[df['result_type'] == result_type]

                for model in df['model_name'].unique():
                    model_data = type_data[type_data['model_name'] == model]

                    for mmap_val in ['0', '1']:
                        mmap_data = model_data[model_data['mmap_value'] == mmap_val]
                        if not mmap_data.empty:
                            ax.scatter([int(mmap_val)] * len(mmap_data),
                                     mmap_data['mean_value'],
                                     c=colors[model],
                                     marker=markers[mmap_val],
                                     s=100,
                                     alpha=0.7,
                                     label=f'{model} mmap={mmap_val}')

                            # 添加误差棒
                            ax.errorbar([int(mmap_val)] * len(mmap_data),
                                       mmap_data['mean_value'],
                                       yerr=mmap_data['std_value'],
                                       fmt='none',
                                       ecolor=colors[model],
                                       alpha=0.5,
                                       capsize=3)

                ax.set_xlabel('mmap Parameter')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title(f'{result_type.upper()} Performance by mmap Setting')
                ax.set_xticks([0, 1])
                ax.set_xticklabels(['mmap=0', 'mmap=1'])
                ax.grid(True, alpha=0.3)

                # 只在第一个子图显示图例
                if idx == 0:
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建对比图表失败: {e}")
            plt.close()

    def create_performance_diff_plot(self, analysis_results, save_path=None):
        """创建性能差异对比图"""
        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            models = list(analysis_results.keys())
            result_types = ['pp', 'tg']  # 两种结果类型
            x = np.arange(len(models))
            width = 0.35

            colors_pp = '#1f77b4'
            colors_tg = '#ff7f0e'

            for idx, result_type in enumerate(result_types):
                diffs = []
                errors = []
                labels = []

                for model in models:
                    if result_type in analysis_results[model]:
                        stats = analysis_results[model][result_type]['statistics']
                        diffs.append(stats['performance_percent_change'])
                        errors.append(0.5)  # 简单误差估计
                        labels.append(f'{model}')
                    else:
                        diffs.append(0)
                        errors.append(0)

                color = colors_pp if result_type == 'pp' else colors_tg
                offset = -width/2 if result_type == 'pp' else width/2

                bars = ax.bar(x + offset, diffs, width, alpha=0.7, color=color,
                            label=f'{result_type.upper()} Performance Change (%)')

                # 在柱状图上添加数值标签
                for bar, diff in zip(bars, diffs):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{diff:.2f}%',
                           ha='center', va='bottom' if height >= 0 else 'top')

            ax.set_xlabel('Models')
            ax.set_ylabel('Performance Change (%)')
            ax.set_title('mmap=1 vs mmap=0 Performance Impact\n(Positive = mmap=1 faster, Negative = mmap=0 faster)')
            ax.set_xticks(x)
            ax.set_xticklabels(models)
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建性能差异图表失败: {e}")
            plt.close()

    def generate_report(self, analysis_results):
        """生成mmap分析报告"""
        report = f"""# mmap参数影响分析报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: benchmark_results.db
分析范围: mmap_effect_t1 test suite
参数对比: mmap="0" vs mmap="1"

---

## 分析结果

"""

        for model_name, model_data in analysis_results.items():
            report += f"### {model_name}\n\n"

            for result_type, type_data in model_data.items():
                stats = type_data['statistics']

                report += f"#### {result_type.upper()} 结果\n"
                report += f"- mmap=0 性能: {stats['mmap_0_performance']:.2f} ± {stats['mmap_0_std']:.2f} tokens/sec\n"
                report += f"- mmap=1 性能: {stats['mmap_1_performance']:.2f} ± {stats['mmap_1_std']:.2f} tokens/sec\n"
                report += f"- 性能差异: {stats['performance_diff']:.2f} tokens/sec\n"
                report += f"- 相对变化: {stats['performance_percent_change']:.2f}%\n"
                report += f"- mmap=0 平均CV: {stats['mmap_0_avg_cv']:.3f}%\n"
                report += f"- mmap=1 平均CV: {stats['mmap_1_avg_cv']:.3f}%\n\n"

            report += "---\n\n"

        # 数据对比表
        report += "## 性能影响汇总表\n\n"
        report += "| 模型 | PP变化 | TG变化 | PP mmap=0 | PP mmap=1 | TG mmap=0 | TG mmap=1 |\n"
        report += "|------|--------|--------|-----------|-----------|-----------|-----------|\n"

        for model_name, model_data in analysis_results.items():
            pp_change = "N/A"
            tg_change = "N/A"
            pp_0 = pp_1 = tg_0 = tg_1 = "N/A"

            if 'pp' in model_data:
                pp_change = f"{model_data['pp']['statistics']['performance_percent_change']:.2f}%"
                pp_0 = f"{model_data['pp']['statistics']['mmap_0_performance']:.2f}"
                pp_1 = f"{model_data['pp']['statistics']['mmap_1_performance']:.2f}"

            if 'tg' in model_data:
                tg_change = f"{model_data['tg']['statistics']['performance_percent_change']:.2f}%"
                tg_0 = f"{model_data['tg']['statistics']['mmap_0_performance']:.2f}"
                tg_1 = f"{model_data['tg']['statistics']['mmap_1_performance']:.2f}"

            report += f"| {model_name} | {pp_change} | {tg_change} | {pp_0} | {pp_1} | {tg_0} | {tg_1} |\n"

        report += "\n![性能对比](mmap_comparison.png)\n\n"
        report += "![性能差异](mmap_performance_diff.png)\n\n"

        return report

    def run_analysis(self):
        """执行完整的mmap分析流程"""
        print("开始mmap参数分析...")

        # 获取数据
        df = self.get_mmap_data()
        if df.empty:
            print("未找到mmap测试数据")
            return

        print(f"找到 {len(df)} 条mmap测试数据")

        # 按模型分析
        print("进行统计分析...")
        analysis_results = self.analyze_by_model_and_type(df)

        # 生成图表
        print("生成图表...")
        self.create_comparison_plot(df, f'{self.output_dir}/mmap_comparison.png')
        self.create_performance_diff_plot(analysis_results, f'{self.output_dir}/mmap_performance_diff.png')

        # 导出数据
        df.to_csv(f'{self.output_dir}/mmap_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        report = self.generate_report(analysis_results)

        with open(f'{self.output_dir}/mmap_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("mmap分析完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = MmapAnalyzer()
    analyzer.run_analysis()