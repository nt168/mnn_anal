#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词模式方差分析工具
功能：使用单因素方差分析(ANOVA)检验VP0、VP1、PF三种模式下PP和TG性能的差异显著性
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
from pathlib import Path
import scipy.stats as stats
from scipy.stats import levene, bartlett
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class PromptModeANOVA:
    def __init__(self):
        """初始化提示词模式方差分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "prompt_mode_anova")
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

    def perform_grouped_anova_test(self, data, metric_name, result_type):
        """执行按长度分组的方差分析"""
        if result_type == 'pp':
            # PP分析：按n_prompt分组
            parameter_name = 'n_prompt'
            parameter_values = sorted(data['n_prompt'].unique())
        else:  # tg
            # TG分析：按n_gen分组
            parameter_name = 'n_gen'
            parameter_values = sorted(data['n_gen'].unique())

        all_results = []

        for param_value in parameter_values:
            # 筛选当前参数值的数据
            if result_type == 'pp':
                param_data = data[data['n_prompt'] == param_value]
            else:
                param_data = data[data['n_gen'] == param_value]

            # 获取三个模式的数据
            vp0_data = param_data[param_data['prompt_mode'] == 'vp0']['mean_value']
            vp1_data = param_data[param_data['prompt_mode'] == 'vp1']['mean_value']
            pf_data = param_data[param_data['prompt_mode'] == 'pf_file']['mean_value']

            # 检查是否每种模式都有足够的数据
            if len(vp0_data) == 0 or len(vp1_data) == 0 or len(pf_data) == 0:
                continue

            # 基础统计
            results = {
                'metric': metric_name,
                'parameter_name': parameter_name,
                'parameter_value': param_value,
                'vp0_n': len(vp0_data),
                'vp1_n': len(vp1_data),
                'pf_n': len(pf_data),
                'vp0_mean': vp0_data.mean(),
                'vp1_mean': vp1_data.mean(),
                'pf_mean': pf_data.mean(),
                'vp0_std': vp0_data.std(),
                'vp1_std': vp1_data.std(),
                'pf_std': pf_data.std(),
                'vp0_median': vp0_data.median(),
                'vp1_median': vp1_data.median(),
                'pf_median': pf_data.median()
            }

            # 执行Levene检验（方差齐性检验）
            try:
                levene_stat, levene_p = levene(vp0_data, vp1_data, pf_data)
                results['levene_stat'] = levene_stat
                results['levene_p'] = levene_p
            except Exception as e:
                results['levene_stat'] = None
                results['levene_p'] = None

            # 执行Bartlett检验（另一种方差齐性检验）
            try:
                bartlett_stat, bartlett_p = bartlett(vp0_data, vp1_data, pf_data)
                results['bartlett_stat'] = bartlett_stat
                results['bartlett_p'] = bartlett_p
            except Exception as e:
                results['bartlett_stat'] = None
                results['bartlett_p'] = None

            # 执行单因素方差分析
            try:
                f_stat, p_value = stats.f_oneway(vp0_data, vp1_data, pf_data)
                results['anova_f_stat'] = f_stat
                results['anova_p_value'] = p_value
            except Exception as e:
                results['anova_f_stat'] = None
                results['anova_p_value'] = None

            # 如果ANOVA显著，进行事后两两比较
            try:
                if results['anova_p_value'] is not None and results['anova_p_value'] < 0.05:
                    # 合并数据和组标签
                    all_values = np.concatenate([vp0_data, vp1_data, pf_data])
                    group_labels = ['vp0'] * len(vp0_data) + ['vp1'] * len(vp1_data) + ['pf_file'] * len(pf_data)

                    # 使用Tukey HSD进行事后检验
                    tukey_result = pairwise_tukeyhsd(endog=all_values, groups=group_labels, alpha=0.05)

                    # 保存Tukey HSD结果
                    results['tukey_results'] = []
                    for i, (group1, group2, mean_diff, p_adj, reject) in enumerate(tukey_result._results_table[1:]):
                        results['tukey_results'].append({
                            'group1': group1,
                            'group2': group2,
                            'mean_diff': mean_diff,
                            'p_adj': p_adj,
                            'reject_h0': reject
                        })
                else:
                    results['tukey_results'] = []
            except Exception as e:
                results['tukey_results'] = []

            all_results.append(results)

        return all_results

    def create_boxplot(self, data, metric_name, filename, param_display=""):
        """创建箱线图"""
        plt.figure(figsize=(10, 6))

        # 按模式分组数据
        box_data = [
            data[data['prompt_mode'] == 'vp0']['mean_value'],
            data[data['prompt_mode'] == 'vp1']['mean_value'],
            data[data['prompt_mode'] == 'pf_file']['mean_value']
        ]

        labels = ['VP0', 'VP1', 'PF_FILE']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

        # 绘制箱线图
        box_plot = plt.boxplot(box_data, tick_labels=labels, patch_artist=True)

        # 设置颜色
        for patch, color in zip(box_plot['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # 根据是否有参数显示来设置标题
        if param_display:
            title = f'{metric_name.upper()} Performance Distribution ({param_display})'
        else:
            title = f'{metric_name.upper()} Performance Distribution by Prompt Mode'

        plt.title(title)
        plt.ylabel(f'{metric_name.upper()} Performance (tokens/sec)')
        plt.xlabel('Prompt Mode')
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300, bbox_inches='tight')
        plt.close()

    def run_analysis(self):
        """运行完整的方差分析"""
        print("开始提示词模式方差分析...")

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

        all_results = []

        # 对每个模型和性能指标组合进行分析
        models = df['model_name'].unique()
        for model in models:
            for result_type in df['result_type'].unique():  # pp, tg
                model_type_data = df[(df['model_name'] == model) & (df['result_type'] == result_type)]

                if model_type_data.empty:
                    continue

                metric_name = f"{model}_{result_type}"
                print(f"\n分析: {metric_name}")

                # 执行按长度分组的方差分析
                grouped_anova_results = self.perform_grouped_anova_test(model_type_data, metric_name, result_type)

                for result in grouped_anova_results:
                    result['model'] = model
                    result['result_type'] = result_type
                    all_results.append(result)

                # 为每个参数值创建箱线图
                for result in grouped_anova_results:
                    param_value = result['parameter_value']
                    param_name = result['parameter_name']

                    # 筛选当前参数值的数据用于绘图
                    if result_type == 'pp':
                        plot_data = model_type_data[model_type_data['n_prompt'] == param_value]
                    else:
                        plot_data = model_type_data[model_type_data['n_gen'] == param_value]

                    boxplot_filename = f"{metric_name}_{param_name}_{param_value}_boxplot.png"
                    param_display = f"{param_name}={param_value}"
                    self.create_boxplot(plot_data, f"{model}_{result_type}", boxplot_filename, param_display)

                    # 打印简要结果
                    print(f"  - {param_name}={param_value}: VP0(n={result['vp0_n']})均值={result['vp0_mean']:.4f}, VP1(n={result['vp1_n']})均值={result['vp1_mean']:.4f}, PF_FILE(n={result['pf_n']})均值={result['pf_mean']:.4f}")
                    print(f"    ANOVA F={result['anova_f_stat']:.4f}, p={result['anova_p_value']:.6f}")

                    if result['anova_p_value'] is not None and result['anova_p_value'] < 0.05:
                        print(f"    - 事后检验结果:")
                        for tukey in result['tukey_results']:
                            print(f"      * {tukey['group1']} vs {tukey['group2']}: 均值差={tukey['mean_diff']:.4f}, p={tukey['p_adj']:.6f}, 拒绝原假设={tukey['reject_h0']}")

        # 保存结果到DataFrame
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(os.path.join(self.output_dir, 'anova_results.csv'), index=False)

        # 生成详细报告
        self.generate_md_report(results_df, df)

        print("\n方差分析完成")
        print(f"文件位置: {self.output_dir}")

        return all_results

    def generate_md_report(self, results_df, data_df):
        """生成Markdown格式报告"""
        report_lines = []
        report_lines.append("# 提示词模式性能方差分析报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append("数据来源: benchmark_results.db")
        report_lines.append("分析方法: 单因素方差分析(One-Way ANOVA)")
        report_lines.append("")

        # 数据概览
        report_lines.append("## 1. 数据概览")
        report_lines.append(f"- 总测试记录数: {len(data_df)}")
        report_lines.append(f"- 涉及模型: {', '.join(data_df['model_name'].unique())}")
        report_lines.append(f"- 性能指标: {', '.join(data_df['result_type'].unique())}")
        report_lines.append(f"- 提示词模式: {', '.join(data_df['prompt_mode'].unique())}")
        report_lines.append(f"- n_prompt范围: {data_df['n_prompt'].min()} - {data_df['n_prompt'].max()}")
        report_lines.append(f"- n_gen范围: {data_df['n_gen'].min()} - {data_df['n_gen'].max()}")
        report_lines.append("")

        # 分析方法说明
        report_lines.append("## 2. 分析方法")
        report_lines.append("### 2.1 单因素方差分析(One-Way ANOVA)")
        report_lines.append("- 原假设H0: 三种提示词模式(VP0, VP1, PF_FILE)的性能均值相等")
        report_lines.append("- 备择假设H1: 至少有一种模式的性能均值与其他模式不同")
        report_lines.append("- 显著性水平α=0.05")
        report_lines.append("")

        report_lines.append("### 2.2 方差齐性检验")
        report_lines.append("- Levene检验: 检验各组方差是否相等")
        report_lines.append("- Bartlett检验: 另一种方差齐性检验方法")
        report_lines.append("")

        report_lines.append("### 2.3 事后检验")
        report_lines.append("- Tukey HSD: 当ANOVA显著时，进行两两比较")
        report_lines.append("- 控制多重比较中的第一类错误率")
        report_lines.append("")

        # 详细结果表格 - 按模型和性能指标分组
        report_lines.append("## 3. 详细分析结果")

        current_model = None
        current_result_type = None
        section_counter = 1

        for _, row in results_df.iterrows():
            model = row['model']
            result_type = row['result_type']

            # 如果是新模型或新性能指标，开始新章节
            if model != current_model or result_type != current_result_type:
                current_model = model
                current_result_type = result_type
                metric_name = f"{model}_{result_type}"
                report_lines.append(f"### 3.{section_counter} {metric_name.upper()} 性能分析")
                report_lines.append("")

                # 分析方法说明
                if result_type == 'pp':
                    param_name = 'n_prompt'
                    param_values = sorted(results_df[results_df['result_type'] == 'pp']['parameter_value'].unique())
                    report_lines.append(f"**分析方法**: 按{param_name}参数值分组进行ANOVA，每组内包含相同{param_name}长度下的5次重复测试")
                else:  # tg
                    param_name = 'n_gen'
                    param_values = sorted(results_df[results_df['result_type'] == 'tg']['parameter_value'].unique())
                    report_lines.append(f"**分析方法**: 按{param_name}参数值分组进行ANOVA，每组内包含相同{param_name}长度下的5次重复测试")

                report_lines.append("")
                report_lines.append(f"**分析范围**: {param_name} ∈ [{', '.join(map(str, param_values))}]")
                report_lines.append("")

                section_counter += 1

            # 添加具体分析结果
            param_value = row['parameter_value']
            param_name = row['parameter_name']

            report_lines.append(f"#### {param_name} = {param_value}")
            report_lines.append("")

            # 基础统计表格
            report_lines.append("##### 基础统计信息")
            report_lines.append("| 模式 | 样本量 | 均值 | 标准差 | 中位数 |")
            report_lines.append("|------|--------|------|--------|--------|")
            report_lines.append(f"| VP0 | {row['vp0_n']} | {row['vp0_mean']:.4f} | {row['vp0_std']:.4f} | {row['vp0_median']:.4f} |")
            report_lines.append(f"| VP1 | {row['vp1_n']} | {row['vp1_mean']:.4f} | {row['vp1_std']:.4f} | {row['vp1_median']:.4f} |")
            report_lines.append(f"| PF_FILE | {row['pf_n']} | {row['pf_mean']:.4f} | {row['pf_std']:.4f} | {row['pf_median']:.4f} |")
            report_lines.append("")

            # 方差齐性检验结果
            report_lines.append("##### 方差齐性检验")
            report_lines.append("| 检验方法 | 统计量 | p值 | 结论(α=0.05) |")
            report_lines.append("|----------|--------|-----|--------------|")

            if pd.notna(row['levene_p']):
                levene_conclusion = "满足方差齐性" if row['levene_p'] >= 0.05 else "不满足方差齐性"
                report_lines.append(f"| Levene检验 | {row['levene_stat']:.6f} | {row['levene_p']:.6f} | {levene_conclusion} |")
            else:
                report_lines.append("| Levene检验 | N/A | N/A | 检验失败 |")

            if pd.notna(row['bartlett_p']):
                bartlett_conclusion = "满足方差齐性" if row['bartlett_p'] >= 0.05 else "不满足方差齐性"
                report_lines.append(f"| Bartlett检验 | {row['bartlett_stat']:.6f} | {row['bartlett_p']:.6f} | {bartlett_conclusion} |")
            else:
                report_lines.append("| Bartlett检验 | N/A | N/A | 检验失败 |")
            report_lines.append("")

            # ANOVA结果
            report_lines.append("##### 单因素方差分析(ANOVA)结果")
            report_lines.append(f"- F统计量: {row['anova_f_stat']:.6f}")
            report_lines.append(f"- p值: {row['anova_p_value']:.8f}")

            if pd.notna(row['anova_p_value']):
                if row['anova_p_value'] < 0.001:
                    significance = "极显著 (p < 0.001)"
                elif row['anova_p_value'] < 0.01:
                    significance = "高度显著 (p < 0.01)"
                elif row['anova_p_value'] < 0.05:
                    significance = "显著 (p < 0.05)"
                elif row['anova_p_value'] < 0.10:
                    significance = "边缘显著 (p < 0.10)"
                else:
                    significance = "不显著 (p >= 0.05)"

                report_lines.append(f"- 显著性水平: {significance}")

                if row['anova_p_value'] < 0.05:
                    report_lines.append("- **结果**: 拒绝原假设，至少有一种模式的性能与其他模式存在显著差异")
                    if row['tukey_results']:
                        report_lines.append("")
                        report_lines.append("##### Tukey HSD事后检验结果")
                        report_lines.append("| 比较组 | 均值差 | 调整后p值 | 是否拒绝原假设 |")
                        report_lines.append("|---------|--------|----------|--------------|")
                        for tukey in row['tukey_results']:
                            reject = "是" if tukey['reject_h0'] else "否"
                            report_lines.append(f"| {tukey['group1']} vs {tukey['group2']} | {tukey['mean_diff']:.4f} | {tukey['p_adj']:.6f} | {reject} |")
                else:
                    report_lines.append("- **结果**: 不能拒绝原假设，三种模式的性能差异不具有统计显著性")
            else:
                report_lines.append("- **结果**: ANOVA检验失败，无法得出结论")

            report_lines.append("")

            # 添加箱线图引用
            report_lines.append("##### 数据分布图")
            boxplot_filename = f"{model}_{result_type}_{param_name}_{param_value}_boxplot.png"
            report_lines.append(f"![{model}_{result_type.upper()} {param_name}={param_value} 箱线图]({boxplot_filename})")
            report_lines.append("")

        # 总体结论
        report_lines.append("## 4. 数据文件")
        report_lines.append("- [详细分析结果](anova_results.csv): 所有统计分析的完整数据")
        report_lines.append("- [箱线图文件]: 各模型和性能指标的分布可视化")
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("分析完成 | 请注意：本报告仅提供统计检验结果，不包含技术和业务结论")

        # 写入文件
        with open(os.path.join(self.output_dir, 'prompt_mode_anova_report.md'), 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))

if __name__ == "__main__":
    analyzer = PromptModeANOVA()
    analyzer.run_analysis()