#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repeat参数影响分析工具 - 基于正确结果的修正版本
功能：分析repeat参数对MNN LLM推理测试重复性的影响
专注于单测试点的CV分析，避免聚合不同测试参数
参考：基于正确分析报告的数据结构

作者：EAO项目团队
日期：2025年11月30日
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
from datetime import datetime

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class RepeatAnalyzer:
    def __init__(self):
        """初始化repeat分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "repeat_analysis")
        os.makedirs(self.output_dir, exist_ok=True)
        self.connect_db()

    def connect_db(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if self.conn:
            self.conn.close()

    def get_repeat_data(self):
        """获取repeat测试数据"""
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
            WHERE s.name = 'rep_p_grid_t1'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)

            # 解析repeat值
            df['repeat'] = df['base_parameters'].apply(lambda x: eval(x).get('repeat', None) if isinstance(x, str) else None)
            df = df.dropna(subset=['repeat'])
            df['repeat'] = df['repeat'].astype(int)

            return df
        except Exception as e:
            print(f"获取repeat数据失败: {e}")
            return pd.DataFrame()

    def analyze_single_point_stability(self, df):
        """分析单测试点的重复性"""
        results = {}

        for result_type in ['pp', 'tg']:
            type_data = df[df['result_type'] == result_type]
            stats = []

            for repeat in sorted(type_data['repeat'].unique()):
                repeat_data = type_data[type_data['repeat'] == repeat]

                if not repeat_data.empty:
                    cv_values = repeat_data['cv_value'].values
                    mean_cv = cv_values.mean()
                    cv_std = cv_values.std(ddof=1) if len(cv_values) > 1 else 0

                    stats.append({
                        'repeat': repeat,
                        'data_count': len(repeat_data),
                        'mean_cv': mean_cv,
                        'cv_std': cv_std,
                        'min_cv': cv_values.min(),
                        'max_cv': cv_values.max(),
                        'cv_range': cv_values.max() - cv_values.min(),
                        'mean_performance': repeat_data['mean_value'].mean(),
                        'performance_range': repeat_data['mean_value'].max() - repeat_data['mean_value'].min(),
                        'std_performance': repeat_data['std_value'].mean(),
                        'std_performance_range': repeat_data['std_value'].max() - repeat_data['std_value'].min()
                    })

            if stats:
                results[result_type] = pd.DataFrame(stats)

        return results

    def save_stability_data(self, stability_data):
        """保存稳定性数据到CSV文件"""
        for result_type, stats_df in stability_data.items():
            csv_path = f'{self.output_dir}/stability_{result_type}.csv'
            stats_df.to_csv(csv_path, index=False, encoding='utf-8')

    def create_stability_plots(self, df, save_path=None):
        """创建稳定性图表"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Repeat Parameter Impact on Test Repeatability', fontsize=16, fontweight='bold')

            # 定义颜色和标签
            colors = {'pp': '#1f77b4', 'tg': '#ff7f0e'}
            markers = {'pp': 'o-', 'tg': 's-'}

            # 1. CV值随repeat次数变化 + 误差棒 (左上)
            stability_data = self.analyze_single_point_stability(df)
            for result_type, stats_df in stability_data.items():
                if not stats_df.empty:
                    axes[0,0].plot(stats_df['repeat'], stats_df['mean_cv'],
                                  markers[result_type], color=colors[result_type],
                                  markersize=8, linewidth=2, label=f'{result_type.upper()} CV')

                    # 添加误差棒
                    axes[0,0].errorbar(stats_df['repeat'], stats_df['mean_cv'],
                                       yerr=stats_df['cv_std'], fmt='none',
                                       color=colors[result_type], alpha=0.5, capsize=5)

            axes[0,0].set_title('Single-Point CV vs Repeat Count (with Error Bars)')
            axes[0,0].set_xlabel('Repeat Count')
            axes[0,0].set_ylabel('CV Value (%)')
            axes[0,0].legend()
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].set_xticks([2, 3, 4, 5])

            # 2. 稳定性改善率 (右上)
            for result_type, stats_df in stability_data.items():
                if len(stats_df) > 1:
                    improvement_rates = []
                    for i in range(1, len(stats_df)):
                        prev_repeat = stats_df.iloc[i-1]['repeat']
                        curr_repeat = stats_df.iloc[i]['repeat']
                        prev_cv = stats_df.iloc[i-1]['mean_cv']
                        curr_cv = stats_df.iloc[i]['mean_cv']

                        if prev_cv > 0:
                            improvement = (prev_cv - curr_cv) / prev_cv * 100
                            improvement_rates.append(improvement)

                    repeat_transitions = [f"{stats_df.iloc[i-1]['repeat']}→{stats_df.iloc[i]['repeat']}" for i in range(1, len(stats_df))]

                    if improvement_rates:
                        axes[0,1].bar(range(len(improvement_rates)), improvement_rates,
                                      color=colors[result_type], alpha=0.7, label=f'{result_type.upper()}')

            axes[0,1].set_title('Repeat Number vs Stability Improvement Rate')
            axes[0,1].set_xlabel('Transition')
            axes[0,1].set_ylabel('CV Improvement Rate (%)')
            axes[0,1].set_xticks(range(len(repeat_transitions)))
            axes[0,1].set_xticklabels(repeat_transitions)
            axes[0,1].legend()
            axes[0,1].grid(True, alpha=0.3)

            # 添加参考线
            axes[0,1].axhline(y=0, color='gray', linestyle='-', alpha=0.5, label='No Improvement')
            axes[0,1].axhline(y=10, color='green', linestyle='--', alpha=0.5, label='Good Improvement (+10%)')

            # 3. PP单测试点CV分布箱线图 (左下)
            try:
                pp_data = df[df['result_type'] == 'pp']
                pp_box_data = [pp_data[pp_data['repeat'] == r]['cv_value'].values for r in sorted(pp_data['repeat'].unique())]
                if pp_box_data and all(len(data) > 0 for data in pp_box_data):
                    axes[1,0].boxplot(pp_box_data, tick_labels=[f'Repeat {r}' for r in sorted(pp_data['repeat'].unique())],
                                     patch_artist=True, boxprops=dict(facecolor=colors['pp'], alpha=0.7))
                    axes[1,0].set_title('PP Single-Test CV Distribution')
                    axes[1,0].set_xlabel('Repeat Count')
                    axes[1,0].set_ylabel('CV Value (%)')
                    axes[1,0].grid(True, alpha=0.3)
            except Exception as e:
                print(f"Warning: Could not create PP box plot: {e}")
                axes[1,0].text(0.5, 0.5, "PP data unavailable", ha='center', va='center', transform=axes[1,0].transAxes)

            # 4. TG单测试点CV分布箱线图 (右下)
            try:
                tg_data = df[df['result_type'] == 'tg']
                tg_box_data = [tg_data[tg_data['repeat'] == r]['cv_value'].values for r in sorted(tg_data['repeat'].unique())]
                if tg_box_data and all(len(data) > 0 for data in tg_box_data):
                    axes[1,1].boxplot(tg_box_data, tick_labels=[f'Repeat {r}' for r in sorted(tg_data['repeat'].unique())],
                                     patch_artist=True, boxprops=dict(facecolor=colors['tg'], alpha=0.7))
                    axes[1,1].set_title('TG Single-Test CV Distribution')
                    axes[1,1].set_xlabel('Repeat Count')
                    axes[1,1].set_ylabel('CV Value (%)')
                    axes[1,1].grid(True, alpha=0.3)
            except Exception as e:
                print(f"Warning: Could not create TG box plot: {e}")
                axes[1,1].text(0.5, 0.5, "TG data unavailable", ha='center', va='center', transform=axes[1,1].transAxes)

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建图表失败: {e}")
            plt.close()

    def generate_report(self, df, stability_data):
        """生成分析报告"""
        report_lines = []
        report_lines.append("# Repeat参数对测试重复性影响分析报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        report_lines.append("## 测试设计概览")
        report_lines.append("- **测试目标**: 确定合理的测试重复次数，在保证结果可信度的前提下最大化测试效率")
        report_lines.append("- **涉及Suite**: rep_p_grid_t1 (任务8)")
        report_lines.append("- **测试参数**: repeat [2,3,4,5] × n_prompt [192,384,512] × n_gen [64,128]")
        report_lines.append("- **分析方法**: 聚焦单测试点重复性，避免参数性能聚合")
        report_lines.append("")
        report_lines.append("## 数据概览")
        report_lines.append(f"- 测试记录数: {len(df)}")
        report_lines.append(f"- 涉及模型: {', '.join(df['model_name'].unique())}")
        report_lines.append(f"- 性能指标类型: {', '.join(df['result_type'].unique())}")
        report_lines.append(f"- Repeat次数范围: {df['repeat'].min()} - {df['repeat'].max()}")
        report_lines.append("")

        # 单测试点稳定性分析
        report_lines.append("## 单测试点重复性分析")

        for result_type, stats_df in stability_data.items():
            report_lines.append(f"### {result_type.upper()} 重复性分析")

            for _, row in stats_df.iterrows():
                repeat = row['repeat']
                mean_cv = row['mean_cv']
                cv_range = row['cv_range']

                # 稳定性评价
                if mean_cv < 0.5:
                    level = " (优秀)"
                    desc = "高精度基准测试适用"
                elif mean_cv < 1.0:
                    level = " (良好)"
                    desc = "标准基准测试适用"
                elif mean_cv < 2.0:
                    level = " (一般)"
                    desc = "快速评估适用"
                else:
                    level = " (需改进)"
                    desc = "需要检查测试条件"

                report_lines.append(f"- **Repeat {repeat}**: 平均CV = {mean_cv:.3f}% ±{row['cv_std']:.3f}%{level}")
                report_lines.append(f"  - CV范围: {row['min_cv']:.3f}% - {row['max_cv']:.3f}%")
                report_lines.append(f"  - 测试点数: {row['data_count']}")
                report_lines.append(f"  - 适用场景: {desc}")
                report_lines.append(f"  - 性能均值: {row['mean_performance']:.2f} tokens/sec")

        report_lines.append("")
        report_lines.append("## 重复次数效果量化评估")

        for result_type, stats_df in stability_data.items():
            if len(stats_df) > 1:
                report_lines.append(f"### {result_type.upper()} 重复效果")

                for i in range(1, len(stats_df)):
                    prev_row = stats_df.iloc[i-1]
                    curr_row = stats_df.iloc[i]

                    prev_repeat = prev_row['repeat']
                    curr_repeat = curr_row['repeat']

                    prev_cv = prev_row['mean_cv']
                    curr_cv = curr_row['mean_cv']

                    if prev_cv > 0:
                        improvement = (prev_cv - curr_cv) / prev_cv * 100
                        time_cost = curr_repeat / prev_repeat

                        report_lines.append(f"- 从 {prev_repeat}→{curr_repeat}: CV改善 {improvement:.1f}% (时间成本: {time_cost:.1f}x)")

                
        # 添加图片引用
        report_lines.append("")
        report_lines.append("## 可视化分析")
        report_lines.append("![重复性对比分析](repeat_stability_comparison.png)")

        # 保存报告
        final_report = "\n".join(report_lines)
        with open(f'{self.output_dir}/repeat_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(final_report)

        return final_report

    def run_analysis(self):
        """运行完整分析"""
        print("开始repeat参数分析...")

        df = self.get_repeat_data()
        if df.empty:
            print("未找到repeat测试数据")
            return

        print(f"找到 {len(df)} 条repeat测试数据")
        print(f"测试模型: {df['model_name'].iloc[0]}")

        # 单测试点重复性分析
        stability_data = self.analyze_single_point_stability(df)

        # 保存数据文件
        print("保存数据文件...")
        self.save_stability_data(stability_data)

        # 生成图表
        print("生成图表...")
        self.create_stability_plots(df, f'{self.output_dir}/repeat_stability_comparison.png')

        # 生成报告
        print("生成报告...")
        self.generate_report(df, stability_data)

        print("repeat参数分析完成")
        print(f"文件位置: {self.output_dir}")

if __name__ == "__main__":
    analyzer = RepeatAnalyzer()
    analyzer.run_analysis()