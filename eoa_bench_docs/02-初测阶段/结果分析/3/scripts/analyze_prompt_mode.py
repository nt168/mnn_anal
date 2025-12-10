#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词模式对比分析工具
功能：分析vp=0、vp=1、prompt_file三种提示词输入模式对MNN LLM推理性能的影响
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

class PromptModeAnalyzer:
    def __init__(self):
        """初始化提示词模式分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "prompt_mode_analysis")
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

    def get_mode_data(self):
        """获取提示词模式测试数据"""
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
            WHERE s.name IN ('pn_grid_vp0', 'pn_grid_vp1', 'pn_grid_pf_file')
            ORDER BY s.model_name, s.name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"获取提示词模式数据失败: {e}")
            return None

    def extract_mode_from_suite(self, suite_name):
        """从suite名称提取提示词模式"""
        if suite_name == 'pn_grid_vp0':
            return 'vp0'
        elif suite_name == 'pn_grid_vp1':
            return 'vp1'
        elif suite_name == 'pn_grid_pf_file':
            return 'pf_file'
        else:
            return 'unknown'

    def extract_n_from_params(self, params_str, param_name):
        """从参数字符串中提取n_prompt或n_gen值"""
        try:
            import json
            params = json.loads(params_str)
            return params.get(param_name)
        except:
            return None

    def process_mode_data(self, df):
        """处理提示词模式数据，提取模式号和n参数"""
        if df.empty:
            return None

        # 提取模式信息
        df['prompt_mode'] = df['suite_name'].apply(self.extract_mode_from_suite)

        # 从base_parameters中提取n_prompt和n_gen
        df['n_prompt'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: self.extract_n_from_params(x, 'n_gen'))

        # 转换为数值类型
        df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')
        df['mean_value'] = pd.to_numeric(df['mean_value'], errors='coerce')
        df['std_value'] = pd.to_numeric(df['std_value'], errors='coerce')
        df['cv_value'] = pd.to_numeric(df['cv_value'], errors='coerce')

        # 去除无效数据
        df = df.dropna(subset=['prompt_mode', 'n_prompt', 'n_gen', 'mean_value'])

        return df

    def create_comparison_plots(self, df):
        """创建对比散点图"""
        if df.empty:
            return

        # 定义颜色
        mode_colors = {
            'vp0': '#1f77b4',
            'vp1': '#ff7f0e',
            'pf_file': '#2ca02c'
        }

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
                fig.suptitle(f'{model} - {result_type.upper()} Performance vs Prompt Mode Comparison',
                            fontsize=14, fontweight='bold')

                # 按模式分别绘制
                modes = ['vp0', 'vp1', 'pf_file']

                for i, mode in enumerate(modes):
                    mode_df = model_df[model_df['prompt_mode'] == mode]

                    if mode_df.empty:
                        continue

                    ax = axes[i]

                    # 选择X轴变量：PP用n_prompt，TG用n_gen
                    if result_type == 'pp':
                        x_var = mode_df['n_prompt']
                        x_label = 'n_prompt (tokens)'
                    else:  # tg
                        x_var = mode_df['n_gen']
                        x_label = 'n_gen (tokens)'

                    # 绘制散点图（x_var vs performance）
                    ax.scatter(x_var, mode_df['mean_value'],
                             color=mode_colors[mode], alpha=0.6, label=f'{mode.upper()} Mean', s=50)

                    # 添加误差棒（标准差）
                    ax.errorbar(x_var, mode_df['mean_value'],
                              yerr=mode_df['std_value'],
                              fmt='none', color=mode_colors[mode], alpha=0.3, capsize=3)

                    ax.set_xlabel(x_label)
                    ax.set_ylabel(f'{result_type.upper()} Performance (tokens/sec)')
                    ax.set_title(f'Prompt Mode: {mode.upper()}')
                    ax.grid(True, alpha=0.3)
                    ax.legend()

                    # 设置y轴为对数坐标，便于观察差异
                    # ax.set_yscale('log')

                plt.tight_layout()
                # 保存图表
                plot_filename = f'{model}_{result_type}_comparison.png'
                plt.savefig(os.path.join(self.output_dir, plot_filename),
                           dpi=300, bbox_inches='tight')
                plt.close()

    def create_mode_aggregate_plots(self, df):
        """创建模式聚合对比图，PP和TG分别生成独立图表"""
        if df.empty:
            return

        # 定义颜色
        mode_colors = {
            'vp0': '#1f77b4',
            'vp1': '#ff7f0e',
            'pf_file': '#2ca02c'
        }

        # PP分析：主要关注n_prompt
        if 'pp' in df['result_type'].values:
            pp_df = df[df['result_type'] == 'pp']
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('PP (Prefill) Performance vs Prompt Mode Analysis',
                        fontsize=14, fontweight='bold')

            # 定义颜色和形状
            mode_colors = {
                'vp0': '#1f77b4',
                'vp1': '#ff7f0e',
                'pf_file': '#2ca02c'
            }

            # 定义不同模型的散点形状
            model_markers = {
                'hunyuan_05b': 'o',    # 圆形
                'qwen3_06b': 's'       # 方形
            }

            # 左上：PP性能 vs n_prompt (主要)
            ax1 = axes[0, 0]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = pp_df[pp_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax1.scatter(model_data['n_prompt'], model_data['mean_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax1.set_xlabel('n_prompt (tokens)')
            ax1.set_ylabel('PP Performance (tokens/sec)')
            ax1.set_title('PP Performance vs n_prompt')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 右上：PP稳定性 vs n_prompt (主要)
            ax2 = axes[0, 1]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = pp_df[pp_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax2.scatter(model_data['n_prompt'], model_data['cv_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax2.set_xlabel('n_prompt (tokens)')
            ax2.set_ylabel('PP CV (%)')
            ax2.set_title('PP Stability vs n_prompt')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 左下：PP性能 vs n_gen (次要)
            ax3 = axes[1, 0]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = pp_df[pp_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax3.scatter(model_data['n_gen'], model_data['mean_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax3.set_xlabel('n_gen (tokens)')
            ax3.set_ylabel('PP Performance (tokens/sec)')
            ax3.set_title('PP Performance vs n_gen (secondary)')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 右下：PP稳定性 vs n_gen (次要)
            ax4 = axes[1, 1]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = pp_df[pp_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax4.scatter(model_data['n_gen'], model_data['cv_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax4.set_xlabel('n_gen (tokens)')
            ax4.set_ylabel('PP CV (%)')
            ax4.set_title('PP Stability vs n_gen (secondary)')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'pp_aggregate_comparison.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

        # TG分析：主要关注n_gen
        if 'tg' in df['result_type'].values:
            tg_df = df[df['result_type'] == 'tg']
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('TG (Decode) Performance vs Prompt Mode Analysis',
                        fontsize=14, fontweight='bold')

            # 定义颜色和形状（重新定义避免变量作用域问题）
            mode_colors = {
                'vp0': '#1f77b4',
                'vp1': '#ff7f0e',
                'pf_file': '#2ca02c'
            }

            # 定义不同模型的散点形状
            model_markers = {
                'hunyuan_05b': 'o',    # 圆形
                'qwen3_06b': 's'       # 方形
            }

            # 左上：TG性能 vs n_gen (主要)
            ax1 = axes[0, 0]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = tg_df[tg_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax1.scatter(model_data['n_gen'], model_data['mean_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax1.set_xlabel('n_gen (tokens)')
            ax1.set_ylabel('TG Performance (tokens/sec)')
            ax1.set_title('TG Performance vs n_gen')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 右上：TG稳定性 vs n_gen (主要)
            ax2 = axes[0, 1]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = tg_df[tg_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax2.scatter(model_data['n_gen'], model_data['cv_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax2.set_xlabel('n_gen (tokens)')
            ax2.set_ylabel('TG CV (%)')
            ax2.set_title('TG Stability vs n_gen')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 左下：TG性能 vs n_prompt (次要)
            ax3 = axes[1, 0]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = tg_df[tg_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax3.scatter(model_data['n_prompt'], model_data['mean_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax3.set_xlabel('n_prompt (tokens)')
            ax3.set_ylabel('TG Performance (tokens/sec)')
            ax3.set_title('TG Performance vs n_prompt (secondary)')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 右下：TG稳定性 vs n_prompt (次要)
            ax4 = axes[1, 1]
            for mode in ['vp0', 'vp1', 'pf_file']:
                mode_df = tg_df[tg_df['prompt_mode'] == mode]
                if not mode_df.empty:
                    for model in mode_df['model_name'].unique():
                        model_data = mode_df[mode_df['model_name'] == model]
                        ax4.scatter(model_data['n_prompt'], model_data['cv_value'],
                                  color=mode_colors[mode], marker=model_markers[model],
                                  alpha=0.6, label=f'{mode.upper()} - {model}', s=30)
            ax4.set_xlabel('n_prompt (tokens)')
            ax4.set_ylabel('TG CV (%)')
            ax4.set_title('TG Stability vs n_prompt (secondary)')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'tg_aggregate_comparison.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

    def generate_data_summary(self, df):
        """生成数据摘要统计"""
        if df.empty:
            return None

        summary_results = []

        for result_type in df['result_type'].unique():
            for model in df['model_name'].unique():
                for mode in ['vp0', 'vp1', 'pf_file']:
                    mode_df = df[(df['prompt_mode'] == mode) &
                                 (df['model_name'] == model) &
                                 (df['result_type'] == result_type)]

                    if mode_df.empty:
                        continue

                    # 计算统计指标
                    stats = {
                        'result_type': result_type,
                        'model': model,
                        'prompt_mode': mode,
                        'data_points': len(mode_df),
                        'mean_performance': mode_df['mean_value'].mean(),
                        'std_performance': mode_df['mean_value'].std(),
                        'min_performance': mode_df['mean_value'].min(),
                        'max_performance': mode_df['mean_value'].max(),
                        'avg_cv': mode_df['cv_value'].mean(),
                        'max_cv': mode_df['cv_value'].max(),
                        'min_cv': mode_df['cv_value'].min()
                    }
                    summary_results.append(stats)

        return pd.DataFrame(summary_results)

    def save_data_files(self, df, summary_df=None):
        """保存数据文件"""
        # 保存原始数据
        if df is not None and not df.empty:
            df.to_csv(os.path.join(self.output_dir, 'prompt_mode_raw_data.csv'), index=False)

        # 保存摘要数据
        if summary_df is not None and not summary_df.empty:
            summary_df.to_csv(os.path.join(self.output_dir, 'prompt_mode_summary.csv'), index=False)

    def generate_md_report(self, df, summary_df=None):
        """生成MD格式报告"""
        if df.empty:
            return "未找到提示词模式测试数据"

        report_lines = []
        report_lines.append("# 提示词模式对比分析数据报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append("数据来源: benchmark_results.db")
        report_lines.append("")

        # 数据概览
        report_lines.append("## 数据概览")
        report_lines.append(f"- 总测试记录数: {len(df)}")
        report_lines.append(f"- 涉及模型: {', '.join(df['model_name'].unique())}")
        report_lines.append(f"- 性能指标: {', '.join(df['result_type'].unique())}")
        report_lines.append(f"- 提示词模式: {', '.join(df['prompt_mode'].unique())}")
        report_lines.append(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        report_lines.append(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        report_lines.append("")

        # 测试记录详细统计
        report_lines.append("## 测试记录统计")

        # 统计各模式组合
        mode_stats = df.groupby(['prompt_mode', 'model_name', 'result_type']).size().reset_index(name='data_points')

        report_lines.append("| 提示词模式 | 模型 | 性能指标 | 测试记录数 |")
        report_lines.append("|------------|------|----------|------------|")
        for _, row in mode_stats.iterrows():
            report_lines.append(f"| {row['prompt_mode']} | {row['model_name']} | {row['result_type']} | {row['data_points']} |")
        report_lines.append("")

        # 性能数据表格
        report_lines.append("## 性能数据表格")

        if summary_df is not None and not summary_df.empty:
            # PP数据
            pp_data = summary_df[summary_df['result_type'] == 'pp'].sort_values(['model', 'prompt_mode'])
            if not pp_data.empty:
                report_lines.append("### PP (Prefill阶段) 性能数据")
                report_lines.append("| 模型 | 提示词模式 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) |")
                report_lines.append("|------|------------|----------|-------------------|------------|----------|----------|-----------|----------|")
                for _, row in pp_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['prompt_mode']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} |")
                report_lines.append("")

            # TG数据
            tg_data = summary_df[summary_df['result_type'] == 'tg'].sort_values(['model', 'prompt_mode'])
            if not tg_data.empty:
                report_lines.append("### TG (Decode阶段) 性能数据")
                report_lines.append("| 模型 | 提示词模式 | 数据点数 | 平均性能(tokens/sec) | 性能标准差 | 最小性能 | 最大性能 | 平均CV(%) | 最大CV(%) |")
                report_lines.append("|------|------------|----------|-------------------|------------|----------|----------|-----------|----------|")
                for _, row in tg_data.iterrows():
                    report_lines.append(f"| {row['model']} | {row['prompt_mode']} | {row['data_points']} | {row['mean_performance']:.4f} | {row['std_performance']:.4f} | {row['min_performance']:.4f} | {row['max_performance']:.4f} | {row['avg_cv']:.4f} | {row['max_cv']:.4f} |")
                report_lines.append("")

        # 图表说明
        report_lines.append("## 分析图表")
        report_lines.append("### 单模型对比图")
        report_lines.append("![Hunyuan-05B PP对比](hunyuan_05b_pp_comparison.png)")
        report_lines.append("")
        report_lines.append("![Hunyuan-05B TG对比](hunyuan_05b_tg_comparison.png)")
        report_lines.append("")
        report_lines.append("![Qwen3-06B PP对比](qwen3_06b_pp_comparison.png)")
        report_lines.append("")
        report_lines.append("![Qwen3-06B TG对比](qwen3_06b_tg_comparison.png)")
        report_lines.append("")
        report_lines.append("*图表说明: 每个图表显示不同提示词模式(vp0/vp1/pf_file)下的性能散点图，包含误差棒表示标准差。*")
        report_lines.append("")

        report_lines.append("### 聚合对比图")
        report_lines.append("![PP聚合对比](pp_aggregate_comparison.png)")
        report_lines.append("")
        report_lines.append("![TG聚合对比](tg_aggregate_comparison.png)")
        report_lines.append("")
        report_lines.append("*聚合图表说明:")
        report_lines.append("- PP聚合图: 左上-性能vs n_prompt(主要)，右上-稳定性vs n_prompt(主要)，左下-性能vs n_gen(次要)，右下-稳定性vs n_gen(次要)*")
        report_lines.append("- TG聚合图: 左上-性能vs n_gen(主要)，右上-稳定性vs n_gen(主要)，左下-性能vs n_prompt(次要)，右下-稳定性vs n_prompt(次要)*")
        report_lines.append("- 图例说明：hunyuan_05b模型使用圆形(○)，qwen3_06b模型使用方形(□)")
        report_lines.append("- 注意：PP和TG已分两个独立图表展示，便于清晰分析")
        report_lines.append("")

        # 数据文件说明
        report_lines.append("## 数据文件")
        report_lines.append("- [原始数据](prompt_mode_raw_data.csv): 所有测试记录的详细数据")
        report_lines.append("- [汇总数据](prompt_mode_summary.csv): 按模型和模式汇总的统计数据")
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("数据整理完成")

        return "\n".join(report_lines)

    def run_analysis(self):
        """运行完整分析流程"""
        print("开始提示词模式对比分析...")

        # 获取数据
        df = self.get_mode_data()
        if df is None or df.empty:
            print("未找到提示词模式测试数据")
            return

        print(f"找到 {len(df)} 条提示词模式测试数据")

        # 处理数据
        df = self.process_mode_data(df)
        if df is None or df.empty:
            print("提示词模式数据处理失败")
            return

        print(f"处理后有效数据: {len(df)} 条")

        # 数据概览
        print("\n数据概览:")
        print(f"- 模型数: {df['model_name'].nunique()}")
        print(f"- 性能指标类型: {', '.join(df['result_type'].unique())}")
        print(f"- 提示词模式: {', '.join(df['prompt_mode'].unique())}")
        print(f"- n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"- n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")

        # 生成图表
        print("\n生成图表...")
        self.create_comparison_plots(df)
        self.create_mode_aggregate_plots(df)

        # 生成数据摘要
        print("生成数据摘要...")
        summary_df = self.generate_data_summary(df)

        # 保存数据文件
        self.save_data_files(df, summary_df)

        # 生成MD报告
        print("生成报告...")
        report_content = self.generate_md_report(df, summary_df)
        with open(os.path.join(self.output_dir, 'prompt_mode_report.md'), 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 显示简要统计
        if summary_df is not None:
            print("\n简要统计结果:")
            print(summary_df.to_string(index=False))

        print("\n提示词模式分析完成")
        print(f"文件位置: {self.output_dir}")

if __name__ == "__main__":
    analyzer = PromptModeAnalyzer()
    analyzer.run_analysis()