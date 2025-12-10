#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG性能趋势数学分析工具
验证模型在不同n_prompt和n_gen下的性能变化模式
"""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from scipy import stats
from scipy.stats import linregress
from sklearn.metrics import r2_score
from pathlib import Path

# 设置字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

def extract_tg_data():
    """提取TG性能数据"""
    script_dir = Path(__file__).parent
    db_path = script_dir / ".." / "data" / "benchmark_results.db"
    conn = sqlite3.connect(str(db_path))

    query = """
    SELECT
        s.model_name,
        cv_n_prompt.variable_value as n_prompt,
        cv_n_gen.variable_value as n_gen,
        br.mean_value as tg_performance,
        br.std_value as std_value
    FROM benchmark_results br
    JOIN case_definitions cd ON br.case_id = cd.id
    JOIN suites s ON cd.suite_id = s.id
    JOIN case_variable_values cv_n_prompt ON cd.id = cv_n_prompt.case_id
        AND cv_n_prompt.variable_name = 'n_prompt'
    JOIN case_variable_values cv_n_gen ON cd.id = cv_n_gen.case_id
        AND cv_n_gen.variable_name = 'n_gen'
    WHERE br.result_type = 'tg'
    ORDER BY s.model_name, CAST(cv_n_prompt.variable_value as INTEGER), CAST(cv_n_gen.variable_value as INTEGER)
    """

    df = pd.read_sql_query(query, conn)
    df['n_prompt'] = df['n_prompt'].astype(int)
    df['n_gen'] = df['n_gen'].astype(int)
    df['tg_performance'] = df['tg_performance'].astype(float)
    df['std_value'] = df['std_value'].astype(float)

    conn.close()
    return df

def analyze_trend_with_n_gen(df, model_name):
    """分析TG性能随n_gen的变化趋势"""
    model_data = df[df['model_name'] == model_name]

    print(f"\n=== {model_name} - TG vs n_gen 趋势分析 ===")

    # 分析每个n_gen下的性能变化
    n_gen_values = sorted(model_data['n_gen'].unique())
    performance_by_n_gen = []

    for n_gen in n_gen_values:
        n_gen_data = model_data[model_data['n_gen'] == n_gen]
        mean_perf = n_gen_data['tg_performance'].mean()
        std_perf = n_gen_data['tg_performance'].std()

        performance_by_n_gen.append({
            'n_gen': n_gen,
            'mean_performance': mean_perf,
            'std_performance': std_perf,
            'count': len(n_gen_data)
        })

    trend_df = pd.DataFrame(performance_by_n_gen)

    # 线性回归分析
    slope, intercept, r_value, p_value, std_err = linregress(trend_df['n_gen'], trend_df['mean_performance'])

    print(f"线性回归结果:")
    print(f"  斜率: {slope:.4f} (负值表示下降趋势)")
    print(f"  R²: {r_value**2:.4f}")
    print(f"  p值: {p_value:.4f}")

    # 性能下降率计算
    if slope < 0:
        first_perf = trend_df['mean_performance'].iloc[0]
        last_perf = trend_df['mean_performance'].iloc[-1]
        decline_rate = (first_perf - last_perf) / first_perf * 100
        print(f"  性能下降率: {decline_rate:.2f}%")

    return trend_df, slope, r_value**2

def analyze_stability_by_n_prompt_fixed_n_gen(df, model_name):
    """分析在固定n_gen条件下，TG性能随n_prompt的稳定性变化"""
    model_data = df[df['model_name'] == model_name]

    n_gen_values = sorted(model_data['n_gen'].unique())
    n_gen_stability_results = []

    for n_gen in n_gen_values:
        gen_data = model_data[model_data['n_gen'] == n_gen]

        # 在固定n_gen条件下，分析不同n_prompt的性能
        n_prompt_values = sorted(gen_data['n_prompt'].unique())
        cv_by_n_prompt = []

        for n_prompt in n_prompt_values:
            prompt_data = gen_data[gen_data['n_prompt'] == n_prompt]

            n_gen_all = model_data[model_data['n_gen'] == n_gen]
            n_gen_mean = n_gen_all['tg_performance'].mean()

            current_perf = prompt_data['tg_performance'].iloc[0]
            relative_deviation = abs(current_perf - n_gen_mean) / n_gen_mean

            cv_by_n_prompt.append({
                'n_prompt': n_prompt,
                'performance': current_perf,
                'relative_deviation': relative_deviation
            })

        # 分析这个n_gen条件下的稳定性随n_prompt的变化
        stability_df = pd.DataFrame(cv_by_n_prompt)

        # 计算离散度随n_prompt的变化趋势
        if len(stability_df) > 1:
            slope, _, r_value, p_value, _ = linregress(stability_df['n_prompt'], stability_df['relative_deviation'])

            n_gen_stability_results.append({
                'n_gen': n_gen,
                'slope': slope,
                'r2': r_value**2,
                'cv_start': stability_df['relative_deviation'].iloc[0],
                'cv_end': stability_df['relative_deviation'].iloc[-1]
            })

    return pd.DataFrame(n_gen_stability_results)

def visualize_stability_per_n_gen(df):
    """为每个n_gen条件生成独立的稳定性分析图表"""
    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "analysis_output" / "tg_trend_analysis" / "stability_by_n_gen"
    output_dir.mkdir(parents=True, exist_ok=True)

    models = df['model_name'].unique()
    colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}

    n_gen_values = sorted(df['n_gen'].unique())

    for n_gen in n_gen_values:
        # 为当前n_gen创建图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(f'TG Performance Stability Analysis - n_gen={n_gen}', fontsize=14, fontweight='bold')

        # 准备数据
        for i, model in enumerate(models):
            model_data = df[df['model_name'] == model]
            gen_data = model_data[model_data['n_gen'] == n_gen]

            # 获取n_gen下的所有性能值用于计算基准
            n_gen_data = model_data[model_data['n_gen'] == n_gen]
            n_gen_mean = n_gen_data['tg_performance'].mean()

            # 计算每个n_prompt的性能和相对偏离度
            n_prompt_values = sorted(gen_data['n_prompt'].unique())
            performances = []
            relative_deviations = []

            for n_prompt in n_prompt_values:
                prompt_data = gen_data[gen_data['n_prompt'] == n_prompt]
                perf = prompt_data['tg_performance'].iloc[0]
                rel_dev = abs(perf - n_gen_mean) / n_gen_mean

                performances.append(perf)
                relative_deviations.append(rel_dev)

            # 左图: 性能 vs n_prompt
            ax1.plot(n_prompt_values, performances, 'o-',
                    color=colors[model], label=f'{model} performance',
                    linewidth=2, markersize=6)

            # 添加水平线表示n_gen的平均性能
            ax1.axhline(y=n_gen_mean, color=colors[model], linestyle='--', alpha=0.5, linewidth=1)

            # 右图: 相对偏离度 vs n_prompt
            ax2.plot(n_prompt_values, relative_deviations, 'o-',
                    color=colors[model], label=f'{model} stability',
                    linewidth=2, markersize=6)

            # 添加趋势线
            if len(n_prompt_values) > 1:
                z = np.polyfit(n_prompt_values, relative_deviations, 1)
                p = np.poly1d(z)
                trend_line = p(n_prompt_values)
                ax2.plot(n_prompt_values, trend_line, '--',
                        color=colors[model], alpha=0.7, linewidth=1)

                # 计算趋势斜率
                slope = z[0]
                ax2.text(0.98, 0.02 + (i * 0.05), f'{model}: slope={slope:.6f}',
                        transform=ax2.transAxes, ha='right', fontsize=10,
                        color=colors[model], fontweight='bold')

        # 设置左图
        ax1.set_xlabel('Prompt Length (n_prompt)')
        ax1.set_ylabel('TG Performance (tokens/sec)')
        ax1.set_title(f'TG Performance vs n_prompt (n_gen={n_gen})')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 设置右图
        ax2.set_xlabel('Prompt Length (n_prompt)')
        ax2.set_ylabel('Relative Deviation')
        ax2.set_title(f'Performance Stability vs n_prompt (n_gen={n_gen})')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # 保存当前n_gen的图表
        filename = f'stability_n_gen_{n_gen}.png'
        filepath = output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()  # 关闭当前图形，避免内存泄漏

    # 生成汇总图
    create_summary_stability_chart(df, output_dir, colors)

def create_summary_stability_chart(df, output_dir, colors):
    """创建汇总稳定性图表"""
    fig, ax = plt.subplots(figsize=(12, 8))

    models = df['model_name'].unique()
    n_gen_values = sorted(df['n_gen'].unique())

    for model in models:
        slopes = []
        n_gen_nums = []
        colors_list = []

        model_data = df[df['model_name'] == model]

        for n_gen in n_gen_values:
            gen_data = model_data[model_data['n_gen'] == n_gen]
            n_gen_data = model_data[model_data['n_gen'] == n_gen]
            n_gen_mean = n_gen_data['tg_performance'].mean()

            n_prompt_values = sorted(gen_data['n_prompt'].unique())
            relative_deviations = []

            for n_prompt in n_prompt_values:
                prompt_data = gen_data[gen_data['n_prompt'] == n_prompt]
                perf = prompt_data['tg_performance'].iloc[0]
                rel_dev = abs(perf - n_gen_mean) / n_gen_mean
                relative_deviations.append(rel_dev)

            if len(n_prompt_values) > 1:
                slope = np.polyfit(n_prompt_values, relative_deviations, 1)[0]
                slopes.append(slope)
                n_gen_nums.append(n_gen)
                colors_list.append(colors[model])

        # 绘制随n_gen变化的斜率图
        ax.bar(np.array(n_gen_nums) - 0.12 if model == 'hunyuan_05b' else np.array(n_gen_nums) + 0.12,
               slopes, width=0.25, color=colors[model], alpha=0.8, label=f'{model} stability slope')

    ax.set_xlabel('Generation Length (n_gen)')
    ax.set_ylabel('Stability Slope')
    ax.set_title('Stability Trend vs n_gen (Negative = More Stable, Positive = More Variable)')
    ax.set_xticks(n_gen_values)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    # 确保保存路径正确
    save_dir = output_dir.parent
    plt.savefig(save_dir / 'stability_summary.png', dpi=300, bbox_inches='tight')

    plt.close()

def generate_md_report(stability_results, df):
    """生成中文MD格式稳定性分析报告"""
    script_dir = Path(__file__).parent
    output_path = script_dir / ".." / "analysis_output" / "tg_trend_analysis" / "stability_report.md"

    md_content = []

    # 标题
    md_content.append("# TG性能稳定性分析报告")
    md_content.append("")
    md_content.append("## 总览")
    md_content.append("")
    md_content.append(f"- **总记录数**: {len(df)}")
    md_content.append(f"- **测试模型**: {', '.join(df['model_name'].unique())}")
    md_content.append(f"- **提示词长度范围**: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
    md_content.append(f"- **生成长度范围**: {df['n_gen'].min()} - {df['n_gen'].max()}")
    md_content.append("")

    # 每个模型的详细数据
    for model_name, model_results in stability_results.items():
        md_content.append(f"## {model_name} - 稳定性分析")
        md_content.append("")

        # 汇总表格
        md_content.append("### 汇总表格")
        md_content.append("")
        md_content.append("| 生成长度 | 稳定性斜率 | R²值 | 起始偏离度 | 结束偏离度 |")
        md_content.append("|---------|--------------|-----|------------|------------|")

        for _, row in model_results.iterrows():
            n_gen_val = int(row['n_gen']) if isinstance(row['n_gen'], (int, float)) else row['n_gen']
            md_content.append(f"| {n_gen_val} | {row['slope']:+.6f} | {row['r2']:.4f} | {row['cv_start']:.4f} | {row['cv_end']:.4f} |")

        md_content.append("")

        # 插入图表
        md_content.append("### 分析图表")
        md_content.append("")

        # 每个n_gen的子章节
        n_gen_values = sorted(df['n_gen'].unique())
        for n_gen in n_gen_values:
            md_content.append(f"#### 生成长度 = {n_gen}")
            md_content.append("")
            md_content.append(f"![稳定性分析-生成长度{n_gen}](stability_by_n_gen/stability_n_gen_{n_gen}.png)")
            md_content.append("")

    # 汇总图表
    md_content.append("## 汇总图表")
    md_content.append("")
    md_content.append("![汇总分析](stability_by_n_gen/stability_summary.png)")
    md_content.append("")

    # 原始数据概览
    md_content.append("## 原始数据概览")
    md_content.append("")
    md_content.append("### 数据样本 (前20条记录)")
    md_content.append("")

    # 生成数据表格
    sample_df = df.head(20)
    md_content.append("| 模型名称 | 提示词长度 | 生成长度 | TG性能(tokens/sec) | 标准差 |")
    md_content.append("|---------|----------|-------|------------------|---------|")

    for _, row in sample_df.iterrows():
        md_content.append(f"| {row['model_name']} | {row['n_prompt']} | {row['n_gen']} | {row['tg_performance']:.4f} | {row['std_value']:.4f} |")

    md_content.append("")

    # 统计信息
    md_content.append("### 性能统计")
    md_content.append("")

    for model in df['model_name'].unique():
        model_df = df[df['model_name'] == model]
        md_content.append(f"#### {model}")
        md_content.append("")
        md_content.append(f"- **记录数**: {len(model_df)} 条")
        md_content.append(f"- **性能范围**: {model_df['tg_performance'].min():.4f} - {model_df['tg_performance'].max():.4f} tokens/sec")
        md_content.append(f"- **平均性能**: {model_df['tg_performance'].mean():.4f} tokens/sec")
        md_content.append(f"- **标准差**: {model_df['tg_performance'].std():.4f}")
        md_content.append("")

    # 保存文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_content))

    return output_path

def main():
    """主分析函数 - 专注离散度分析"""
    print("开始TG稳定性分析 (固定n_gen条件)...")

    # 提取数据
    df = extract_tg_data()
    print(f"数据提取完成: {len(df)} 条记录")

    # 分析每个模型的稳定性
    models = df['model_name'].unique()
    stability_results = {}

    for model in models:
        # 专注离散度分析 (固定n_gen)
        stability_df = analyze_stability_by_n_prompt_fixed_n_gen(df, model)
        stability_results[model] = stability_df

    print("稳定性指标计算完成")

    # 生成专门的稳定性可视化
    print("生成稳定性分析图表...")
    visualize_stability_per_n_gen(df)

    # 生成MD报告
    print("生成MD格式报告...")
    report_path = generate_md_report(stability_results, df)

    print(f"\n分析完成!")
    script_dir = Path(__file__).parent
    output_path = script_dir / ".." / "analysis_output" / "tg_trend_analysis"
    print(f"图表输出目录: {output_path}/stability_by_n_gen/")
    print(f"MD报告文件: {report_path}")

if __name__ == "__main__":
    main()