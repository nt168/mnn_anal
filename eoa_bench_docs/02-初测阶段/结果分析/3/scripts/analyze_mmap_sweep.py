#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mmap参数深度扫描分析工具
功能：分析mmap=0/1参数在大范围P/N组合下对MNN LLM推理性能的影响
作者：EAO项目团队
日期：2025年11月28日
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
from datetime import datetime
from pathlib import Path

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class MmapSweepAnalyzer:
    def __init__(self):
        """初始化mmap参数深度扫描分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "mmap_sweep_analysis")
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
        """获取mmap深度扫描测试数据"""
        try:
            query = """
            SELECT
                s.name as suite_name,
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
            WHERE s.name = 'pn_sweep_step-p64-n32_mmp01'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"获取mmap深度扫描数据失败: {e}")
            return None

    def extract_mmap_from_params(self, params_str):
        """从参数字符串中提取mmap值"""
        try:
            import json
            params = json.loads(params_str)
            return params.get('mmap')
        except:
            return None

    def extract_n_from_params(self, params_str, param_name):
        """从参数字符串中提取n_prompt或n_gen值"""
        try:
            import json
            params = json.loads(params_str)
            return params.get(param_name)
        except:
            return None

    def process_mmap_data(self, df):
        """处理mmap扫描数据，提取mmap参数和n参数"""
        if df.empty:
            return None

        # 提取mmap值
        df['mmap'] = df['base_parameters'].apply(self.extract_mmap_from_params)

        # 从base_parameters中提取n_prompt和n_gen
        df['n_prompt'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_gen'))

        # 转换为数值类型
        df['mmap'] = pd.to_numeric(df['mmap'], errors='coerce')
        df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')
        df['mean_value'] = pd.to_numeric(df['mean_value'], errors='coerce')
        df['std_value'] = pd.to_numeric(df['std_value'], errors='coerce')
        df['cv_value'] = pd.to_numeric(df['cv_value'], errors='coerce')

        # 去除无效数据
        df = df.dropna(subset=['mmap', 'n_prompt', 'n_gen', 'mean_value'])

        return df

    def create_mmap_comparison_plots(self, df):
        """创建mmap对比散点图"""
        if df.empty:
            return

        # 定义颜色
        mmap_colors = {0: '#1f77b4', 1: '#ff7f0e'}

        # 为每个性能指标和每个模型创建图表
        result_types = df['result_type'].unique()
        models = df['model_name'].unique()

        for result_type in result_types:
            for model in models:
                model_df = df[(df['model_name'] == model) & (df['result_type'] == result_type)]

                if model_df.empty:
                    continue

                # 创建图表
                fig, axes = plt.subplots(1, 3, figsize=(18, 6))
                fig.suptitle(f'{model} - {result_type.upper()} Performance vs Mmap Parameter Comparison',
                            fontsize=14, fontweight='bold')

                # 将数据按mmap分成两组
                mmap0_df = model_df[model_df['mmap'] == 0]
                mmap1_df = model_df[model_df['mmap'] == 1]

                # 绘制散点图（n_prompt vs performance）
                ax = axes[0]
                if not mmap0_df.empty:
                    ax.scatter(mmap0_df['n_prompt'], mmap0_df['mean_value'],
                             color=mmap_colors[0], alpha=0.6, label='mmap=0', s=50)
                    ax.errorbar(mmap0_df['n_prompt'], mmap0_df['mean_value'],
                              yerr=mmap0_df['std_value'],
                              fmt='none', color=mmap_colors[0], alpha=0.3, capsize=3)

                if not mmap1_df.empty:
                    ax.scatter(mmap1_df['n_prompt'], mmap1_df['mean_value'],
                             color=mmap_colors[1], alpha=0.6, label='mmap=1', s=50)
                    ax.errorbar(mmap1_df['n_prompt'], mmap1_df['mean_value'],
                              yerr=mmap1_df['std_value'],
                              fmt='none', color=mmap_colors[1], alpha=0.3, capsize=3)

                ax.set_xlabel('n_prompt (tokens)')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title('Performance vs n_prompt')
                ax.legend()
                ax.grid(True, alpha=0.3)

                # 绘制散点图（n_gen vs performance）
                ax = axes[1]
                if not mmap0_df.empty:
                    ax.scatter(mmap0_df['n_gen'], mmap0_df['mean_value'],
                             color=mmap_colors[0], alpha=0.6, label='mmap=0', s=50)
                    ax.errorbar(mmap0_df['n_gen'], mmap0_df['mean_value'],
                              yerr=mmap0_df['std_value'],
                              fmt='none', color=mmap_colors[0], alpha=0.3, capsize=3)

                if not mmap1_df.empty:
                    ax.scatter(mmap1_df['n_gen'], mmap1_df['mean_value'],
                             color=mmap_colors[1], alpha=0.6, label='mmap=1', s=50)
                    ax.errorbar(mmap1_df['n_gen'], mmap1_df['mean_value'],
                              yerr=mmap1_df['std_value'],
                              fmt='none', color=mmap_colors[1], alpha=0.3, capsize=3)

                ax.set_xlabel('n_gen (tokens)')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title('Performance vs n_gen')
                ax.legend()
                ax.grid(True, alpha=0.3)

                # 直接对比图（mmap0 vs mmap1）
                ax = axes[2]
                if not mmap0_df.empty and not mmap1_df.empty:
                    # 匹配相同n_prompt和n_gen的数据点进行直接对比
                    merged_df = pd.merge(
                        mmap0_df[['n_prompt', 'n_gen', 'mean_value']].rename(columns={'mean_value': 'mmap0_mean'}),
                        mmap1_df[['n_prompt', 'n_gen', 'mean_value']].rename(columns={'mean_value': 'mmap1_mean'}),
                        on=['n_prompt', 'n_gen']
                    )

                    ax.scatter(merged_df['mmap0_mean'], merged_df['mmap1_mean'],
                             color='purple', alpha=0.6, s=30, label='comparison')
                    # 添加45度参考线
                    min_val = min(merged_df['mmap0_mean'].min(), merged_df['mmap1_mean'].min())
                    max_val = max(merged_df['mmap0_mean'].max(), merged_df['mmap1_mean'].max())
                    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='equal performance')

                ax.set_xlabel('mmap=0 Performance (tokens/sec)')
                ax.set_ylabel('mmap=1 Performance (tokens/sec)')
                ax.set_title('Direct Comparison mmap0 vs mmap1')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_aspect('equal', adjustable='box')

                plt.tight_layout()
                # 保存图表
                plot_filename = f'{model}_{result_type}_mmap_comparison.png'
                plt.savefig(os.path.join(self.output_dir, plot_filename),
                           dpi=300, bbox_inches='tight')
                plt.close()

    def create_aggregate_mmap_plots(self, df):
        """创建mmap聚合对比图"""
        if df.empty:
            return

        # 定义颜色
        mmap_colors = {0: '#1f77b4', 1: '#ff7f0e'}

        result_types = df['result_type'].unique()  # pp, tg

        for result_type in result_types:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f'Mmap Parameter Performance Comparison - {result_type.upper()}',
                        fontsize=14, fontweight='bold')

            # 1. 所有模型的均值对比（n_prompt）
            ax1 = axes[0, 0]
            for mmap_val in [0, 1]:
                mmap_df = df[df['mmap'] == mmap_val]
                if not mmap_df.empty:
                    ax1.scatter(mmap_df['n_prompt'], mmap_df['mean_value'],
                              color=mmap_colors[mmap_val], alpha=0.6, label=f'mmap={mmap_val}', s=30)
            ax1.set_xlabel('n_prompt (tokens)')
            ax1.set_ylabel(f'{result_type.upper()} Mean (tokens/sec)')
            ax1.set_title('Performance vs n_prompt')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. 所有模型的CV值对比（n_prompt）
            ax2 = axes[0, 1]
            for mmap_val in [0, 1]:
                mmap_df = df[df['mmap'] == mmap_val]
                if not mmap_df.empty:
                    ax2.scatter(mmap_df['n_prompt'], mmap_df['cv_value'],
                              color=mmap_colors[mmap_val], alpha=0.6, label=f'mmap={mmap_val}', s=30)
            ax2.set_xlabel('n_prompt (tokens)')
            ax2.set_ylabel(f'{result_type.upper()} CV (%)')
            ax2.set_title('Stability vs n_prompt')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 3. 所有模型的均值对比（n_gen）
            ax3 = axes[1, 0]
            for mmap_val in [0, 1]:
                mmap_df = df[df['mmap'] == mmap_val]
                if not mmap_df.empty:
                    ax3.scatter(mmap_df['n_gen'], mmap_df['mean_value'],
                              color=mmap_colors[mmap_val], alpha=0.6, label=f'mmap={mmap_val}', s=30)
            ax3.set_xlabel('n_gen (tokens)')
            ax3.set_ylabel(f'{result_type.upper()} Mean (tokens/sec)')
            ax3.set_title('Performance vs n_gen')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 4. 所有模型的CV值对比（n_gen）
            ax4 = axes[1, 1]
            for mmap_val in [0, 1]:
                mmap_df = df[df['mmap'] == mmap_val]
                if not mmap_df.empty:
                    ax4.scatter(mmap_df['n_gen'], mmap_df['cv_value'],
                              color=mmap_colors[mmap_val], alpha=0.6, label=f'mmap={mmap_val}', s=30)
            ax4.set_xlabel('n_gen (tokens)')
            ax4.set_ylabel(f'{result_type.upper()} CV (%)')
            ax4.set_title('Stability vs n_gen')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            # 保存聚合图表
            plt.savefig(os.path.join(self.output_dir, f'{result_type}_aggregate_mmap.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

    def generate_mmap_summary(self, df):
        """生成mmap摘要统计"""
        if df.empty:
            return None

        summary_results = []

        for result_type in df['result_type'].unique():
            for model in df['model_name'].unique():
                for mmap_val in [0, 1]:
                    mmap_df = df[(df['mmap'] == mmap_val) &
                                   (df['model_name'] == model) &
                                   (df['result_type'] == result_type)]

                    if mmap_df.empty:
                        continue

                    # 计算统计指标
                    stats = {
                        'result_type': result_type,
                        'model': model,
                        'mmap_value': mmap_val,
                        'data_points': len(mmap_df),
                        'mean_performance': mmap_df['mean_value'].mean(),
                        'std_performance': mmap_df['mean_value'].std(),
                        'min_performance': mmap_df['mean_value'].min(),
                        'max_performance': mmap_df['mean_value'].max(),
                        'avg_cv': mmap_df['cv_value'].mean(),
                        'max_cv': mmap_df['cv_value'].max(),
                        'min_cv': mmap_df['cv_value'].min(),
                        'n_prompt_range': f"{mmap_df['n_prompt'].min()}-{mmap_df['n_prompt'].max()}",
                        'n_gen_range': f"{mmap_df['n_gen'].min()}-{mmap_df['n_gen'].max()}"
                    }
                    summary_results.append(stats)

        return pd.DataFrame(summary_results)

    def calculate_mmap_difference(self, df, summary_df):
        """计算mmap=0与mmap=1之间的差异"""
        if summary_df.empty:
            return None

        diff_results = []

        for result_type in df['result_type'].unique():
            for model in df['model_name'].unique():
                # 获取两个mmap值的数据
                mmap0_row = summary_df[(summary_df['result_type'] == result_type) &
                                      (summary_df['model'] == model) &
                                      (summary_df['mmap_value'] == 0)]
                mmap1_row = summary_df[(summary_df['result_type'] == result_type) &
                                      (summary_df['model'] == model) &
                                      (summary_df['mmap_value'] == 1)]

                if len(mmap0_row) == 1 and len(mmap1_row) == 1:
                    diff_stats = {
                        'result_type': result_type,
                        'model': model,
                        'performance_diff': mmap1_row.iloc[0]['mean_performance'] - mmap0_row.iloc[0]['mean_performance'],
                        'performance_diff_pct': (mmap1_row.iloc[0]['mean_performance'] - mmap0_row.iloc[0]['mean_performance']) / mmap0_row.iloc[0]['mean_performance'] * 100,
                        'cv_diff': mmap1_row.iloc[0]['avg_cv'] - mmap0_row.iloc[0]['avg_cv'],
                        'data_points_diff': mmap1_row.iloc[0]['data_points'] - mmap0_row.iloc[0]['data_points']
                    }
                    diff_results.append(diff_stats)

        return pd.DataFrame(diff_results)

    def save_data_files(self, df, summary_df=None, diff_df=None):
        """保存数据文件"""
        # 保存原始数据
        if df is not None and not df.empty:
            df.to_csv(os.path.join(self.output_dir, 'mmap_sweep_raw_data.csv'), index=False)

        # 保存摘要数据
        if summary_df is not None and not summary_df.empty:
            summary_df.to_csv(os.path.join(self.output_dir, 'mmap_sweep_summary.csv'), index=False)

        # 保存差异数据
        if diff_df is not None and not diff_df.empty:
            diff_df.to_csv(os.path.join(self.output_dir, 'mmap_sweep_difference.csv'), index=False)

    def generate_md_report(self, df, summary_df=None, diff_df=None):
        """生成MD格式报告"""
        if df.empty:
            return "未找到mmap扫描测试数据"

        report_lines = []
        report_lines.append("# mmap参数深度扫描分析数据报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append("数据来源: benchmark_results.db")
        report_lines.append("")

        # 数据概览
        report_lines.append("## 数据概览")
        report_lines.append(f"- 总测试记录数: {len(df)}")
        report_lines.append(f"- 涉及模型: {', '.join(df['model_name'].unique())}")
        report_lines.append(f"- 性能指标: {', '.join(df['result_type'].unique())}")
        report_lines.append(f"- mmap参数: 0, 1")
        report_lines.append(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        report_lines.append(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        report_lines.append("")

        # 测试记录详细统计
        report_lines.append("## 测试记录统计")
        mmap_stats = df.groupby(['mmap', 'model_name', 'result_type']).size().reset_index(name='data_points')
        report_lines.append("| mmap值 | 模型 | 性能指标 | 测试记录数 |")
        report_lines.append("|--------|------|----------|------------|")
        for _, row in mmap_stats.iterrows():
            report_lines.append(f"| {row['mmap']} | {row['model_name']} | {row['result_type']} | {row['data_points']} |")
        report_lines.append("")

        # 性能数据表格
        report_lines.append("## 性能数据表格")

        if summary_df is not None and not summary_df.empty:
            # PP数据
            pp_data = summary_df[summary_df['result_type'] == 'pp'].sort_values(['model', 'mmap_value'])
            if not pp_data.empty:
                report_lines.append("### PP (Prefill阶段) 性能数据")
                report_lines.append("| 模型 | mmap值 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) | n_prompt范围 | n_gen范围 |")
                report_lines.append("|------|--------|----------|-------------------|------------|----------|----------|-----------|----------|-------------|-----------|")
                for _, row in pp_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['mmap_value']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} | {row['n_prompt_range']} | {row['n_gen_range']} |")
                report_lines.append("")

            # TG数据
            tg_data = summary_df[summary_df['result_type'] == 'tg'].sort_values(['model', 'mmap_value'])
            if not tg_data.empty:
                report_lines.append("### TG (Decode阶段) 性能数据")
                report_lines.append("| 模型 | mmap值 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) | n_prompt范围 | n_gen范围 |")
                report_lines.append("|------|--------|----------|-------------------|------------|----------|----------|-----------|----------|-------------|-----------|")
                for _, row in tg_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['mmap_value']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} | {row['n_prompt_range']} | {row['n_gen_range']} |")
                report_lines.append("")

        # 差异分析
        if diff_df is not None and not diff_df.empty:
            report_lines.append("## mmap参数差异分析")
            report_lines.append("| 模型 | 性能指标 | 性能差异(tokens/sec) | 差异百分比(%) | CV差异(%) | 数据点数差 |")
            report_lines.append("|------|----------|-------------------|----------------|-----------|-------------|------------|")
            for _, row in diff_df.iterrows():
                report_lines.append(f"| {row['model']} | {row['result_type']} | {row['performance_diff']:.4f} | {row['performance_diff_pct']:.4f} | {row['cv_diff']:.4f} | {row['data_points_diff']} |")
            report_lines.append("")

        # 图表说明
        report_lines.append("## 分析图表")
        report_lines.append("### 单模型对比图")
        models = df['model_name'].unique()
        for model in models:
            report_lines.append(f"![{model} PP对比]({model}_pp_mmap_comparison.png)")
            report_lines.append(f"![{model} TG对比]({model}_tg_mmap_comparison.png)")
            report_lines.append("")
        report_lines.append("*图表说明: 每个图表显示mmap=0和mmap=1条件下的性能散点图，包含误差棒表示标准差。最后一个子图显示直接对比。*")
        report_lines.append("")

        report_lines.append("### 聚合对比图")
        report_lines.append("![PP聚合对比](pp_aggregate_mmap.png)")
        report_lines.append("")
        report_lines.append("![TG聚合对比](tg_aggregate_mmap.png)")
        report_lines.append("")
        report_lines.append("*聚合图表说明: 左上-性能vs n_prompt，右上-稳定性vs n_prompt，左下-性能vs n_gen，右下-稳定性vs n_gen*")
        report_lines.append("")

        # 数据文件说明
        report_lines.append("## 数据文件")
        report_lines.append("- [原始数据](mmap_sweep_raw_data.csv): 所有测试记录的详细数据")
        report_lines.append("- [汇总数据](mmap_sweep_summary.csv): 按模型和mmap值汇总的统计数据")
        report_lines.append("- [差异数据](mmap_sweep_difference.csv): mmap=0与mmap=1的差异对比数据")
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("数据整理完成")

        return "\n".join(report_lines)

    def run_analysis(self):
        """运行完整分析流程"""
        print("开始mmap参数深度扫描分析...")

        # 获取数据
        df = self.get_mmap_data()
        if df is None or df.empty:
            print("未找到mmap深度扫描测试数据")
            return

        print(f"找到 {len(df)} 条mmap深度扫描测试数据")

        # 处理数据
        df = self.process_mmap_data(df)
        if df is None or df.empty:
            print("mmap深度扫描数据处理失败")
            return

        print(f"处理后有效数据: {len(df)} 条")

        # 数据概览
        print("\n数据概览:")
        print(f"- 模型数: {df['model_name'].nunique()}")
        print(f"- 性能指标类型: {', '.join(df['result_type'].unique())}")
        print(f"- mmap值: {sorted(df['mmap'].unique())}")
        print(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")

        # 生成图表
        print("\n生成图表...")
        self.create_mmap_comparison_plots(df)
        self.create_aggregate_mmap_plots(df)

        # 生成数据摘要
        print("生成数据摘要...")
        summary_df = self.generate_mmap_summary(df)

        # 计算差异
        print("计算差异分析...")
        diff_df = self.calculate_mmap_difference(df, summary_df)

        # 保存数据文件
        self.save_data_files(df, summary_df, diff_df)

        # 显示简要统计
        if summary_df is not None:
            print("\n简要统计结果:")
            print(summary_df.to_string(index=False))

        if diff_df is not None:
            print("\nmmap差异分析:")
            print(diff_df.to_string(index=False))

        print("\nmmap深度扫描分析完成")
        print(f"文件位置: {self.output_dir}")

if __name__ == "__main__":
    analyzer = MmapSweepAnalyzer()
    analyzer.run_analysis()