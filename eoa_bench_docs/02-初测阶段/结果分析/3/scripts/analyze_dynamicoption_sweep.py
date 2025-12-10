#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dynamicOption深度扫描分析工具
功能：分析dynamicOption 7/8参数在大范围P/N组合下对MNN LLM推理性能的影响
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

class DynamicOptionSweepAnalyzer:
    def __init__(self):
        """初始化dynamicOption深度扫描分析工具"""
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
        """获取dynamicOption深度扫描测试数据"""
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
            WHERE s.name LIKE '%dyo78%'
            ORDER BY s.model_name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"获取dynamicOption深度扫描数据失败: {e}")
            return None

    def extract_dynamicoption_from_params(self, params_str):
        """从参数字符串中提取dynamicOption值"""
        try:
            import json
            params = json.loads(params_str)
            return params.get('dynamicOption')
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

    def process_dynamicoption_data(self, df):
        """处理dynamicOption扫描数据，提取参数和n参数"""
        if df.empty:
            return None

        # 提取dynamicOption值
        df['dynamicoption'] = df['base_parameters'].apply(self.extract_dynamicoption_from_params)

        # 从base_parameters中提取n_prompt和n_gen
        df['n_prompt'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_gen'))

        # 转换为数值类型
        df['dynamicoption'] = pd.to_numeric(df['dynamicoption'], errors='coerce')
        df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')
        df['mean_value'] = pd.to_numeric(df['mean_value'], errors='coerce')
        df['std_value'] = pd.to_numeric(df['std_value'], errors='coerce')
        df['cv_value'] = pd.to_numeric(df['cv_value'], errors='coerce')

        # 去除无效数据
        df = df.dropna(subset=['dynamicoption', 'n_prompt', 'n_gen', 'mean_value'])

        return df

    def create_dynamicoption_comparison_plots(self, df):
        """创建dynamicOption对比散点图"""
        if df.empty:
            return

        # 定义颜色
        do_colors = {7: '#1f77b4', 8: '#ff7f0e'}

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
                fig.suptitle(f'{model} - {result_type.upper()} Performance vs DynamicOption Comparison',
                            fontsize=14, fontweight='bold')

                # 将数据按dynamicOption分成两组
                do7_df = model_df[model_df['dynamicoption'] == 7]
                do8_df = model_df[model_df['dynamicoption'] == 8]

                # 绘制散点图（n_prompt vs performance）
                ax = axes[0]
                if not do7_df.empty:
                    ax.scatter(do7_df['n_prompt'], do7_df['mean_value'],
                             color=do_colors[7], alpha=0.6, label='dynamicOption=7', s=50)
                    ax.errorbar(do7_df['n_prompt'], do7_df['mean_value'],
                              yerr=do7_df['std_value'],
                              fmt='none', color=do_colors[7], alpha=0.3, capsize=3)

                if not do8_df.empty:
                    ax.scatter(do8_df['n_prompt'], do8_df['mean_value'],
                             color=do_colors[8], alpha=0.6, label='dynamicOption=8', s=50)
                    ax.errorbar(do8_df['n_prompt'], do8_df['mean_value'],
                              yerr=do8_df['std_value'],
                              fmt='none', color=do_colors[8], alpha=0.3, capsize=3)

                ax.set_xlabel('n_prompt (tokens)')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title('Performance vs n_prompt')
                ax.legend()
                ax.grid(True, alpha=0.3)

                # 绘制散点图（n_gen vs performance）
                ax = axes[1]
                if not do7_df.empty:
                    ax.scatter(do7_df['n_gen'], do7_df['mean_value'],
                             color=do_colors[7], alpha=0.6, label='dynamicOption=7', s=50)
                    ax.errorbar(do7_df['n_gen'], do7_df['mean_value'],
                              yerr=do7_df['std_value'],
                              fmt='none', color=do_colors[7], alpha=0.3, capsize=3)

                if not do8_df.empty:
                    ax.scatter(do8_df['n_gen'], do8_df['mean_value'],
                             color=do_colors[8], alpha=0.6, label='dynamicOption=8', s=50)
                    ax.errorbar(do8_df['n_gen'], do8_df['mean_value'],
                              yerr=do8_df['std_value'],
                              fmt='none', color=do_colors[8], alpha=0.3, capsize=3)

                ax.set_xlabel('n_gen (tokens)')
                ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                ax.set_title('Performance vs n_gen')
                ax.legend()
                ax.grid(True, alpha=0.3)

                # 直接对比图（do7 vs do8）
                ax = axes[2]
                if not do7_df.empty and not do8_df.empty:
                    # 匹配相同n_prompt和n_gen的数据点进行直接对比
                    merged_df = pd.merge(
                        do7_df[['n_prompt', 'n_gen', 'mean_value']].rename(columns={'mean_value': 'do7_mean'}),
                        do8_df[['n_prompt', 'n_gen', 'mean_value']].rename(columns={'mean_value': 'do8_mean'}),
                        on=['n_prompt', 'n_gen']
                    )

                    ax.scatter(merged_df['do7_mean'], merged_df['do8_mean'],
                             color='purple', alpha=0.6, s=30, label='comparison')
                    # 添加45度参考线
                    min_val = min(merged_df['do7_mean'].min(), merged_df['do8_mean'].min())
                    max_val = max(merged_df['do7_mean'].max(), merged_df['do8_mean'].max())
                    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='equal performance')

                ax.set_xlabel('dynamicOption=7 Performance (tokens/sec)')
                ax.set_ylabel('dynamicOption=8 Performance (tokens/sec)')
                ax.set_title('Direct Comparison dynamicOption 7 vs 8')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_aspect('equal', adjustable='box')

                plt.tight_layout()
                # 保存图表
                plot_filename = f'{model}_{result_type}_dynamicoption_comparison.png'
                plt.savefig(os.path.join(self.output_dir, plot_filename),
                           dpi=300, bbox_inches='tight')
                plt.close()

    def create_aggregate_dynamicoption_plots(self, df):
        """创建dynamicOption聚合对比图"""
        if df.empty:
            return

        # 定义颜色
        do_colors = {7: '#1f77b4', 8: '#ff7f0e'}

        result_types = df['result_type'].unique()  # pp, tg

        for result_type in result_types:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f'DynamicOption Performance Comparison - {result_type.upper()}',
                        fontsize=14, fontweight='bold')

            # 1. 所有模型的均值对比（n_prompt）
            ax1 = axes[0, 0]
            for do_val in [7, 8]:
                do_df = df[df['dynamicoption'] == do_val]
                if not do_df.empty:
                    ax1.scatter(do_df['n_prompt'], do_df['mean_value'],
                              color=do_colors[do_val], alpha=0.6, label=f'do={do_val}', s=30)
            ax1.set_xlabel('n_prompt (tokens)')
            ax1.set_ylabel(f'{result_type.upper()} Mean (tokens/sec)')
            ax1.set_title('Performance vs n_prompt')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. 所有模型的CV值对比（n_prompt）
            ax2 = axes[0, 1]
            for do_val in [7, 8]:
                do_df = df[df['dynamicoption'] == do_val]
                if not do_df.empty:
                    ax2.scatter(do_df['n_prompt'], do_df['cv_value'],
                              color=do_colors[do_val], alpha=0.6, label=f'do={do_val}', s=30)
            ax2.set_xlabel('n_prompt (tokens)')
            ax2.set_ylabel(f'{result_type.upper()} CV (%)')
            ax2.set_title('Stability vs n_prompt')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 3. 所有模型的均值对比（n_gen）
            ax3 = axes[1, 0]
            for do_val in [7, 8]:
                do_df = df[df['dynamicoption'] == do_val]
                if not do_df.empty:
                    ax3.scatter(do_df['n_gen'], do_df['mean_value'],
                              color=do_colors[do_val], alpha=0.6, label=f'do={do_val}', s=30)
            ax3.set_xlabel('n_gen (tokens)')
            ax3.set_ylabel(f'{result_type.upper()} Mean (tokens/sec)')
            ax3.set_title('Performance vs n_gen')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 4. 所有模型的CV值对比（n_gen）
            ax4 = axes[1, 1]
            for do_val in [7, 8]:
                do_df = df[df['dynamicoption'] == do_val]
                if not do_df.empty:
                    ax4.scatter(do_df['n_gen'], do_df['cv_value'],
                              color=do_colors[do_val], alpha=0.6, label=f'do={do_val}', s=30)
            ax4.set_xlabel('n_gen (tokens)')
            ax4.set_ylabel(f'{result_type.upper()} CV (%)')
            ax4.set_title('Stability vs n_gen')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            # 保存聚合图表
            plt.savefig(os.path.join(self.output_dir, f'{result_type}_aggregate_dynamicoption.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

    def generate_dynamicoption_summary(self, df):
        """生成dynamicOption摘要统计"""
        if df.empty:
            return None

        summary_results = []

        for result_type in df['result_type'].unique():
            for model in df['model_name'].unique():
                for do_val in [7, 8]:
                    do_df = df[(df['dynamicoption'] == do_val) &
                                   (df['model_name'] == model) &
                                   (df['result_type'] == result_type)]

                    if do_df.empty:
                        continue

                    # 计算统计指标
                    stats = {
                        'result_type': result_type,
                        'model': model,
                        'dynamicoption_value': do_val,
                        'data_points': len(do_df),
                        'mean_performance': do_df['mean_value'].mean(),
                        'std_performance': do_df['mean_value'].std(),
                        'min_performance': do_df['mean_value'].min(),
                        'max_performance': do_df['mean_value'].max(),
                        'avg_cv': do_df['cv_value'].mean(),
                        'max_cv': do_df['cv_value'].max(),
                        'min_cv': do_df['cv_value'].min(),
                        'n_prompt_range': f"{do_df['n_prompt'].min()} - {do_df['n_prompt'].max()}",
                        'n_gen_range': f"{do_df['n_gen'].min()} - {do_df['n_gen'].max()}"
                    }
                    summary_results.append(stats)

        return pd.DataFrame(summary_results)

    def calculate_dynamicoption_difference(self, df, summary_df):
        """计算dynamicOption=7与dynamicOption=8之间的差异"""
        if summary_df.empty:
            return None

        diff_results = []

        for result_type in df['result_type'].unique():
            for model in df['model_name'].unique():
                # 获取两个dynamicOption值的数据
                do7_row = summary_df[(summary_df['result_type'] == result_type) &
                                       (summary_df['model'] == model) &
                                       (summary_df['dynamicoption_value'] == 7)]
                do8_row = summary_df[(summary_df['result_type'] == result_type) &
                                       (summary_df['model'] == model) &
                                       (summary_df['dynamicoption_value'] == 8)]

                if len(do7_row) == 1 and len(do8_row) == 1:
                    diff_stats = {
                        'result_type': result_type,
                        'model': model,
                        'performance_diff': do8_row.iloc[0]['mean_performance'] - do7_row.iloc[0]['mean_performance'],
                        'performance_diff_pct': (do8_row.iloc[0]['mean_performance'] - do7_row.iloc[0]['mean_performance']) / do7_row.iloc[0]['mean_performance'] * 100,
                        'cv_diff': do8_row.iloc[0]['avg_cv'] - do7_row.iloc[0]['avg_cv'],
                        'data_points_diff': do8_row.iloc[0]['data_points'] - do7_row.iloc[0]['data_points']
                    }
                    diff_results.append(diff_stats)

        return pd.DataFrame(diff_results)

    def save_data_files(self, df, summary_df=None, diff_df=None):
        """保存数据文件"""
        # 保存原始数据
        if df is not None and not df.empty:
            df.to_csv(os.path.join(self.output_dir, 'dynamicoption_raw_data.csv'), index=False)

        # 保存摘要数据
        if summary_df is not None and not summary_df.empty:
            summary_df.to_csv(os.path.join(self.output_dir, 'dynamicoption_summary.csv'), index=False)

        # 保存差异数据
        if diff_df is not None and not diff_df.empty:
            diff_df.to_csv(os.path.join(self.output_dir, 'dynamicoption_difference.csv'), index=False)

    def generate_md_report(self, df, summary_df=None, diff_df=None):
        """生成MD格式报告"""
        if df.empty:
            return "未找到dynamicOption扫描测试数据"

        report_lines = []
        report_lines.append("# dynamicOption深度扫描分析数据报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append("数据来源: benchmark_results.db")
        report_lines.append("")

        # 数据概览
        report_lines.append("## 数据概览")
        report_lines.append(f"- 总测试记录数: {len(df)}")
        report_lines.append(f"- 涉及模型: {', '.join(df['model_name'].unique())}")
        report_lines.append(f"- 性能指标: {', '.join(df['result_type'].unique())}")
        report_lines.append(f"- dynamicOption值: {sorted(df['dynamicoption'].unique())}")
        report_lines.append(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        report_lines.append(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        report_lines.append("")

        # 测试记录详细统计
        report_lines.append("## 测试记录统计")
        dyo_stats = df.groupby(['dynamicoption', 'model_name', 'result_type']).size().reset_index(name='data_points')
        report_lines.append("| dynamicOption值 | 模型 | 性能指标 | 测试记录数 |")
        report_lines.append("|----------------|------|----------|------------|------------|")
        for _, row in dyo_stats.iterrows():
            report_lines.append(f"| {row['dynamicoption']} | {row['model_name']} | {row['result_type']} | {row['data_points']} |")
        report_lines.append("")

        # 性能数据表格
        report_lines.append("## 性能数据表格")

        if summary_df is not None and not summary_df.empty:
            # PP数据
            pp_data = summary_df[summary_df['result_type'] == 'pp'].sort_values(['model', 'dynamicoption_value'])
            if not pp_data.empty:
                report_lines.append("### PP (Prefill阶段) 性能数据")
                report_lines.append("| 模型 | dynamicOption值 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) | n_prompt范围 | n_gen_range |")
                report_lines.append("|------|--------------|----------|-------------------|------------|----------|----------|-----------|----------|-------------|-----------|")
                for _, row in pp_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['dynamicoption_value']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} | {row['n_prompt_range']} | {row['n_gen_range']} |")
                report_lines.append("")

            # TG数据
            tg_data = summary_df[summary_df['result_type'] == 'tg'].sort_values(['model', 'dynamicoption_value'])
            if not tg_data.empty:
                report_lines.append("### TG (Decode阶段) 性能数据")
                report_lines.append("| 模型 | dynamicOption值 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) | n_prompt范围 | n_gen_range |")
                report_lines.append("|------|--------------|----------|-------------------|------------|----------|-----------|----------|-------------|-----------|-------------|")
                for _, row in tg_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['dynamicoption_value']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} | {row['n_prompt_range']} | {row['n_gen_range']} |")
                report_lines.append("")

        # 差异分析
        if diff_df is not None and not diff_df.empty:
            report_lines.append("## dynamicOption差异分析")
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
            report_lines.append(f"![{model} PP对比]({model}_pp_dynamicoption_comparison.png)")
            report_lines.append(f"![{model} TG对比]({model}_tg_dynamicoption_comparison.png)")
            report_lines.append("")
        report_lines.append("*图表说明: 每个图表显示dynamicOption=7和dynamicOption=8条件下的性能散点图，包含误差棒表示标准差。最后一个子图显示直接对比。*")
        report_lines.append("")

        report_lines.append("### 聚合对比图")
        report_lines.append("![PP聚合对比](pp_aggregate_dynamicoption.png)")
        report_lines.append("")
        report_lines.append("[TG聚合对比](tg_aggregate_dynamicoption.png)")
        report_lines.append("")
        report_lines.append("*聚合图表说明: 左上-性能vs n_prompt，右上-稳定性vs n_prompt，左下-性能vs n_gen，右下-稳定性vs n_gen*")
        report_lines.append("")

        # 数据文件说明
        report_lines.append("## 数据文件")
        report_lines.append("- [原始数据](dynamicoption_raw_data.csv): 所有测试记录的详细数据")
        report_lines.append("- [汇总数据](dynamicoption_summary.csv): 按模型和dynamicOption值汇总的统计数据")
        report_lines.append("- [差异数据](dynamicoption_difference.csv): dynamicOption=7与dynamicOption=8的差异对比数据")
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("数据整理完成")

        return "\n".join(report_lines)

    def run_analysis(self):
        """运行完整分析流程"""
        print("开始dynamicOption深度扫描分析...")

        # 获取数据
        df = self.get_dynamicoption_data()
        if df is None or df.empty:
            print("未找到dynamicOption深度扫描测试数据")
            return

        print(f"找到 {len(df)} 条dynamicOption深度扫描测试数据")

        # 处理数据
        df = self.process_dynamicoption_data(df)
        if df is None or df.empty:
            print("dynamicOption深度扫描数据处理失败")
            return

        print(f"处理后有效数据: {len(df)} 条")

        # 数据概览
        print("\n数据概览:")
        print(f"- 模型数: {df['model_name'].nunique()}")
        print(f"- 性能指标类型: {', '.join(df['result_type'].unique())}")
        print(f"- dynamicOption值: {sorted(df['dynamicoption'].unique())}")
        print(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")

        # 生成图表
        print("\n生成图表...")
        self.create_dynamicoption_comparison_plots(df)
        self.create_aggregate_dynamicoption_plots(df)

        # 生成数据摘要
        print("生成数据摘要...")
        summary_df = self.generate_dynamicoption_summary(df)

        # 计算差异
        print("计算差异分析...")
        diff_df = self.calculate_dynamicoption_difference(df, summary_df)

        # 保存数据文件
        self.save_data_files(df, summary_df, diff_df)

        # 生成MD报告
        print("\\n生成报告...")
        report_content = self.generate_md_report(df, summary_df, diff_df)
        with open(os.path.join(self.output_dir, 'dynamicoption_report.md'), 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 显示简要统计
        if summary_df is not None:
            print("\n简要统计结果:")
            print(summary_df.to_string(index=False))

        if diff_df is not None:
            print("\ndynamicOption差异分析:")
            print(diff_df.to_string(index=False))

        print("\ndynamicOption深度扫描分析完成")
        print(f"文件位置: {self.output_dir}")

if __name__ == "__main__":
    analyzer = DynamicOptionSweepAnalyzer()
    analyzer.run_analysis()