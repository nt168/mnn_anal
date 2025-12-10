#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词模式协方差分析(ANCOVA)工具
功能：使用协变量控制的方法分析VP0、VP1、PF_FILE三种模式对PP和TG性能的影响
- PP分析：使用n_prompt作为协变量
- TG分析：使用n_gen作为协变量
- 假设检验：VP0、VP1、PF_FILE三种模式对结果没有影响
作者：EAO项目团队
日期：2025年11月30日
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
import json
from datetime import datetime
from pathlib import Path
import scipy.stats as stats
from scipy.stats import levene, bartlett, shapiro
from statsmodels.graphics.gofplots import ProbPlot
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
warnings.filterwarnings('ignore')

# 设置安全字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class PromptModeANCOVA:
    def __init__(self):
        """初始化提示词模式协方差分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "prompt_mode_ancova")
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

    def get_ancova_data(self):
        """获取协方差分析的数据"""
        try:
            query = """
            SELECT
                s.name as suite_name,
                s.model_name,
                cd.base_parameters,
                br.result_type,
                br.result_parameter,
                br.mean_value,
                br.std_value
            FROM benchmark_results br
            JOIN case_definitions cd ON br.case_id = cd.id
            JOIN suites s ON cd.suite_id = s.id
            WHERE s.name IN ('pn_grid_vp0', 'pn_grid_vp1', 'pn_grid_pf_file')
            AND br.mean_value IS NOT NULL
            ORDER BY s.model_name, s.name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"获取数据失败: {e}")
            return pd.DataFrame()

    def extract_mode_from_suite(self, suite_name):
        """从suite名称提取提示词模式"""
        mapping = {
            'pn_grid_vp0': 'VP0',
            'pn_grid_vp1': 'VP1',
            'pn_grid_pf_file': 'PF_FILE'
        }
        return mapping.get(suite_name, 'UNKNOWN')

    def extract_parameter(self, params_str, param_name):
        """从参数字符串中提取参数值"""
        try:
            params = json.loads(params_str)
            return params.get(param_name)
        except:
            return None

    def process_data(self, df):
        """处理数据，提取模式和参数"""
        if df.empty:
            return None

        # 提取模式信息
        df['prompt_mode'] = df['suite_name'].apply(self.extract_mode_from_suite)

        # 提取参数
        df['n_prompt'] = df['base_parameters'].apply(lambda x: self.extract_parameter(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: self.extract_parameter(x, 'n_gen'))

        # 转换为数值类型
        numerics = ['mean_value', 'std_value']
        for col in numerics:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 单独处理参数
        df['n_prompt'] = df['base_parameters'].apply(lambda x: self.extract_parameter(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: self.extract_parameter(x, 'n_gen'))
        df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')

        # 数据清洗
        df = df.dropna(subset=['prompt_mode', 'n_prompt', 'n_gen', 'mean_value'])
        df = df[df['mean_value'] > 0]

        return df

    def check_ancova_assumptions(self, data, dv, factor, covariate):
        """检查ANCOVA各项假设"""
        assumptions = {}

        groups = data[factor].unique()
        valid_groups = []

        for group in groups:
            group_data = data[data[factor] == group]
            if len(group_data) >= 3:  # 至少需要3个数据点
                valid_groups.append(group)

        if len(valid_groups) < 2:
            return {"error": "数据不足，无法进行假设检验"}

        try:
            # 1. 线性关系假设（各组内协变量与因变量的线性关系）
            linearity_results = {}
            for group in valid_groups:
                group_data = data[data[factor] == group]
                if len(group_data) >= 3:
                    pearson_r, pearson_p = stats.pearsonr(group_data[covariate], group_data[dv])
                    linearity_results[group] = {
                        'correlation': pearson_r,
                        'p_value': pearson_p,
                        'is_linear': abs(pearson_r) > 0.1,  # 简单判断
                        'sample_size': len(group_data)
                    }
            assumptions['linearity'] = linearity_results

            # 2. 回归斜率齐性检验（协变量与因子的交互作用）
            try:
                formula_with_interaction = f"{dv} ~ {covariate} * {factor}"
                model_interaction = ols(formula_with_interaction, data=data).fit()
                interaction_p = None

                # 找到交互项的p值
                for term in model_interaction.pvalues.index:
                    if f'{covariate}:{factor}' in term:
                        interaction_p = model_interaction.pvalues[term]
                        break

                assumptions['slope_homogeneity'] = {
                    'interaction_p_value': interaction_p,
                    'homogeneous_slopes': interaction_p is not None and interaction_p > 0.05 if interaction_p else None,
                    'test_performed': True
                }
            except Exception as e:
                assumptions['slope_homogeneity'] = {'test_performed': False, 'error': str(e)}

            # 3. 残差正态性检验
            try:
                formula_main = f"{dv} ~ {covariate} + {factor}"
                model_main = ols(formula_main, data=data).fit()
                residuals = model_main.resid

                # Shapiro-Wilk检验（限制样本量）
                sample_for_test = residuals[-1000:] if len(residuals) > 1000 else residuals
                sw_stat, sw_p = shapiro(sample_for_test)

                assumptions['normality'] = {
                    'shapiro_wilk_stat': sw_stat,
                    'shapiro_wilk_p': sw_p,
                    'normal_residuates': sw_p > 0.05,
                    'total_residuates': len(residuals),
                    'test_sample': len(sample_for_test)
                }

                # Q-Q图数据保存
                assumptions['qqplot_data'] = {
                    'residuals': residuals[-500:].tolist() if len(residuals) > 500 else residuals.tolist(),
                    'fitted_values': model_main.fitted_values[-500:].tolist() if len(model_main.fitted_values) > 500 else model_main.fitted_values.tolist()
                }

            except Exception as e:
                assumptions['normality'] = {'test_performed': False, 'error': str(e)}

            # 4. 残差方差齐性检验
            try:
                if 'normality' in assumptions and 'residuals' in locals():
                    residuals = model_main.resid
                    group_residuals = []
                    for group in valid_groups:
                        group_mask = data[factor] == group
                        group_residuals.append(residuals[group_mask])

                    if len(group_residuals) >= 2:
                        levene_stat, levene_p = levene(*group_residuals)

                        assumptions['variance_homogeneity'] = {
                            'levene_stat': levene_stat,
                            'levene_p': levene_p,
                            'equal_variances': levene_p > 0.05,
                            'groups_tested': len(group_residuals)
                        }

            except Exception as e:
                assumptions['variance_homogeneity'] = {'test_performed': False, 'error': str(e)}

        except Exception as e:
            assumptions['overall_error'] = str(e)

        return assumptions

    def perform_ancova(self, data, dv, factor, covariate):
        """执行协方差分析"""
        results = {}

        # 检查假设
        results['assumptions'] = self.check_ancova_assumptions(data, dv, factor, covariate)

        try:
            # 构建ANCOVA模型
            formula = f"{dv} ~ {covariate} + {factor}"
            model = ols(formula, data=data).fit()

            # ANOVA表
            anova_table = anova_lm(model)

            results['model'] = {
                'summary': {
                    'r_squared': model.rsquared,
                    'adj_r_squared': model.rsquared_adj,
                    'f_statistic': model.fvalue,
                    'f_p_value': model.f_pvalue,
                    'aic': model.aic,
                    'bic': model.bic,
                    'log_likelihood': model.llf
                },
                'parameters': model.params.to_dict(),
                'anova_table': anova_table.to_dict(),
                'formula': formula
            }

            # 计算调整均值（控制协变量效应后的各组均值）
            covariate_mean = data[covariate].mean()
            adjusted_means = {}

            for group in data[factor].unique():
                group_mask = data[factor] == group
                if group_mask.sum() > 0:
                    # 使用模型系数计算调整均值
                    intercept = model.params['Intercept']
                    covar_coef = model.params[covariate]
                    group_coef = model.params.get(f'prompt_mode[T.{group}]', 0)

                    adj_mean = intercept + covar_coef * covariate_mean + group_coef
                    adjusted_means[group] = adj_mean

            results['adjusted_means'] = adjusted_means

            # 效应大小计算
            ss_total = anova_table['sum_sq'].sum()
            if factor in anova_table.index:
                ss_factor = anova_table.loc[factor, 'sum_sq']
                eta_squared = ss_factor / ss_total if ss_total > 0 else 0

                ss_error = anova_table.loc['Residual', 'sum_sq'] if 'Residual' in anova_table.index else ss_total - ss_factor
                partial_eta_sq = ss_factor / (ss_factor + ss_error) if (ss_factor + ss_error) > 0 else 0

                results['effect_size'] = {
                    'eta_squared': eta_squared,
                    'partial_eta_squared': partial_eta_sq,
                    'interpretation': self.interpret_eta_squared(eta_squared)
                }
            else:
                results['effect_size'] = {'eta_squared': 0, 'partial_eta_squared': 0, 'interpretation': 'Not applicable'}

            # 事后检验（如果主效应显著）
            if factor in anova_table.index and anova_table.loc[factor, 'PR(>F)'] < 0.05:
                try:
                    # 使用调整均值进行Tukey检验
                    adj_data = []
                    adj_labels = []

                    for group, adj_mean in adjusted_means.items():
                        n_group = sum(data[factor] == group)
                        adj_data.extend([adj_mean] * n_group)
                        adj_labels.extend([group] * n_group)

                    tukey_result = pairwise_tukeyhsd(adj_data, adj_labels)

                    results['post_hoc'] = {
                        'tukey_results': tukey_result._results_table.data,
                        'significant_pairs': []
                    }

                    # 提取显著差异的对
                    for i in range(1, len(tukey_result._results_table.data) - 1):
                        row = tukey_result._results_table.data[i]
                        if len(row) >= 4 and row[3]:  # reject列
                            results['post_hoc']['significant_pairs'].append({
                                'group1': row[0],
                                'group2': row[1],
                                'mean_diff': row[2],
                                'p_adj': row[3],
                                'reject': row[3]
                            })

                except Exception as e:
                    results['post_hoc'] = {'error': str(e)}
            else:
                results['post_hoc'] = {'not_performed': 'Main effect not significant'}

        except Exception as e:
            results['analysis_error'] = str(e)

        return results

    def interpret_eta_squared(self, eta_sq):
        """解释eta-squared效应大小"""
        if eta_sq < 0.01:
            return f"极小效应 (η² = {eta_sq:.6f})"
        elif eta_sq < 0.06:
            return f"小效应 (η² = {eta_sq:.6f})"
        elif eta_sq < 0.14:
            return f"中等效应 (η² = {eta_sq:.6f})"
        else:
            return f"大效应 (η² = {eta_sq:.6f})"

    def create_visualizations(self, data, dv, factor, covariate, results, model_name, result_type):
        """创建可视化图表"""

        # 3列布局：散点图、均值图、残差图
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(f'{model_name} - {result_type.upper()} ANCOVA Analysis\n(Covariate: {covariate})',
                     fontsize=14, fontweight='bold')

        colors = {'VP0': '#1f77b4', 'VP1': '#ff7f0e', 'PF_FILE': '#2ca02c'}

        # 1. 散点图 + 回归线
        ax1 = axes[0]
        for group in data[factor].unique():
            group_data = data[data[factor] == group]
            if len(group_data) > 1:
                ax1.scatter(group_data[covariate], group_data[dv],
                           alpha=0.6, label=group, color=colors.get(group, 'gray'), s=40)
                # 回归线
                z = np.polyfit(group_data[covariate], group_data[dv], 1)
                p = np.poly1d(z)
                x_line = np.linspace(group_data[covariate].min(), group_data[covariate].max(), 100)
                ax1.plot(x_line, p(x_line), color=colors.get(group, 'gray'), alpha=0.8)

        ax1.set_xlabel(covariate)
        ax1.set_ylabel(dv)
        ax1.set_title(f'{dv} vs {covariate}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 调整均值对比
        ax2 = axes[1]
        if 'adjusted_means' in results:
            means = list(results['adjusted_means'].values())
            labels = list(results['adjusted_means'].keys())
            bars = ax2.bar(labels, means, color=[colors.get(label, 'gray') for label in labels], alpha=0.7)
            ax2.set_ylabel(f'Adjusted {dv}')
            ax2.set_title('Adjusted Group Means')
            ax2.grid(True, alpha=0.3)

            # 添加数值标签
            for bar, mean in zip(bars, means):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01*abs(height),
                        f'{height:.4f}', ha='center', va='bottom', fontsize=10)

        # 3. 残差图
        ax3 = axes[2]
        try:
            if 'model' in results:
                formula = results['model']['formula']
                model_fit = ols(formula, data=data).fit()
                residuals = model_fit.resid
                fitted = model_fit.fittedvalues

                ax3.scatter(fitted, residuals, alpha=0.5, s=30)
                ax3.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                ax3.set_xlabel('Fitted Values')
                ax3.set_ylabel('Residuals')
                ax3.set_title('Residual Analysis')
                ax3.grid(True, alpha=0.3)
        except:
            ax3.text(0.5, 0.5, 'Residual Plot\nNot Available',
                    ha='center', va='center', transform=ax3.transAxes)

        plt.tight_layout()
        filename = f"{model_name}_{result_type}_{covariate}_ancova_analysis.png"
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300, bbox_inches='tight')
        plt.close()

        # Q-Q图
        if 'assumptions' in results and 'qqplot_data' in results['assumptions']:
            try:
                fig2 = plt.figure(figsize=(8, 6))
                qq_data = results['assumptions']['qqplot_data']
                if 'residuals' in qq_data and 'fitted_values' in qq_data:
                    residuals = qq_data['residuals']
                    fitted = qq_data['fitted_values']

                    # 标准化残差
                    standardized_resid = (np.array(residuals) - np.mean(residuals)) / np.std(residuals)

                    ProbPlot(standardized_resid).qqplot(line='45', ax=plt.gca())
                    plt.title(f'{model_name} - {result_type.upper()} Normal Q-Q Plot')
                    plt.grid(True, alpha=0.3)

                    filename_qq = f"{model_name}_{result_type}_{covariate}_qq_plot.png"
                    plt.savefig(os.path.join(self.output_dir, filename_qq), dpi=300, bbox_inches='tight')
                    plt.close()
            except Exception as e:
                print(f"Q-Q图生成失败: {e}")

    def save_csv_results(self, all_results):
        """保存结果到CSV"""
        results_data = []

        for model_result in all_results:
            model_name = model_result['model']

            # PP结果
            pp_result = model_result['pp_result']
            if 'model' in pp_result and 'summary' in pp_result['model']:
                summary = pp_result['model']['summary']
                row = {
                    'model': model_name,
                    'analysis_type': 'pp',
                    'dependent_variable': 'mean_value',
                    'covariate': 'n_prompt',
                    'factor': 'prompt_mode',
                    'r_squared': summary['r_squared'],
                    'adj_r_squared': summary['adj_r_squared'],
                    'f_statistic': summary['f_statistic'],
                    'f_p_value': summary['f_p_value'],
                    'aic': summary['aic'],
                    'bic': summary['bic']
                }

                # 效应大小
                if 'effect_size' in pp_result:
                    row.update({
                        'eta_squared': pp_result['effect_size']['eta_squared'],
                        'partial_eta_squared': pp_result['effect_size']['partial_eta_squared'],
                        'effect_interpretation': pp_result['effect_size']['interpretation']
                    })

                # 假设检验结果
                if 'assumptions' in pp_result:
                    assump = pp_result['assumptions']
                    row.update({
                        'normality_p': assump.get('normality', {}).get('shapiro_wilk_p'),
                        'normality_passed': assump.get('normality', {}).get('normal_residuates'),
                        'homogeneity_p': assump.get('variance_homogeneity', {}).get('levene_p'),
                        'homogeneity_passed': assump.get('variance_homogeneity', {}).get('equal_variances'),
                        'slopes_homogeneity_p': assump.get('slope_homogeneity', {}).get('interaction_p_value'),
                        'slopes_homogeneity_passed': assump.get('slope_homogeneity', {}).get('homogeneous_slopes')
                    })

                # 主效应检验
                if 'anova_table' in pp_result['model'] and 'prompt_mode' in pp_result['model']['anova_table']:
                    anova_prompt_mode = pp_result['model']['anova_table']['prompt_mode']
                    row.update({
                        'factor_f_statistic': anova_prompt_mode.get('F'),
                        'factor_p_value': anova_prompt_mode.get('PR(>F)')
                    })

                # 调整均值
                if 'adjusted_means' in pp_result:
                    for mode, mean in pp_result['adjusted_means'].items():
                        row[f'adjusted_mean_{mode.replace("_", "").lower()}'] = mean

                results_data.append(row)

            # TG结果
            tg_result = model_result['tg_result']
            if 'model' in tg_result and 'summary' in tg_result['model']:
                summary = tg_result['model']['summary']
                row = {
                    'model': model_name,
                    'analysis_type': 'tg',
                    'dependent_variable': 'mean_value',
                    'covariate': 'n_gen',
                    'factor': 'prompt_mode',
                    'r_squared': summary['r_squared'],
                    'adj_r_squared': summary['adj_r_squared'],
                    'f_statistic': summary['f_statistic'],
                    'f_p_value': summary['f_p_value'],
                    'aic': summary['aic'],
                    'bic': summary['bic']
                }

                # 效应大小
                if 'effect_size' in tg_result:
                    row.update({
                        'eta_squared': tg_result['effect_size']['eta_squared'],
                        'partial_eta_squared': tg_result['effect_size']['partial_eta_squared'],
                        'effect_interpretation': tg_result['effect_size']['interpretation']
                    })

                # 假设检验结果
                if 'assumptions' in tg_result:
                    assump = tg_result['assumptions']
                    row.update({
                        'normality_p': assump.get('normality', {}).get('shapiro_wilk_p'),
                        'normality_passed': assump.get('normality', {}).get('normal_residuates'),
                        'homogeneity_p': assump.get('variance_homogeneity', {}).get('levene_p'),
                        'homogeneity_passed': assump.get('variance_homogeneity', {}).get('equal_variances'),
                        'slopes_homogeneity_p': assump.get('slope_homogeneity', {}).get('interaction_p_value'),
                        'slopes_homogeneity_passed': assump.get('slope_homogeneity', {}).get('homogeneous_slopes')
                    })

                # 主效应检验
                if 'anova_table' in tg_result['model'] and 'prompt_mode' in tg_result['model']['anova_table']:
                    anova_prompt_mode = tg_result['model']['anova_table']['prompt_mode']
                    row.update({
                        'factor_f_statistic': anova_prompt_mode.get('F'),
                        'factor_p_value': anova_prompt_mode.get('PR(>F)')
                    })

                # 调整均值
                if 'adjusted_means' in tg_result:
                    for mode, mean in tg_result['adjusted_means'].items():
                        row[f'adjusted_mean_{mode.replace("_", "").lower()}'] = mean

                results_data.append(row)

        # 保存DataFrame
        df = pd.DataFrame(results_data)
        csv_path = os.path.join(self.output_dir, 'ancova_analysis_results.csv')
        df.to_csv(csv_path, index=False)

        print(f"分析结果已保存到: {csv_path}")
        return csv_path

    def generate_report(self, all_results):
        """生成分析报告"""
        report_path = os.path.join(self.output_dir, 'ancova_analysis_report.md')

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 提示词模式协方差分析报告\n\n")

            f.write("## 1. 分析概览\n\n")
            f.write("### 1.1 分析目标\n")
            f.write("分析提示词模式（VP0、VP1、PF_FILE）对大模型性能的影响\n")
            f.write("同时控制token长度作为协变量。\n\n")

            f.write("### 1.2 统计假设\n")
            f.write("零假设（H₀）：控制token长度后，提示词模式对性能无显著影响\n")
            f.write("备择假设（H₁）：控制token长度后，至少一种提示词模式与其他模式有差异\n\n")

            f.write("### 1.3 分析设计\n")
            f.write("- **PP性能**：协方差分析，以n_prompt为协变量\n")
            f.write("- **TG性能**：协方差分析，以n_gen为协变量\n")
            f.write("- **分析因子**：提示词模式（VP0、VP1、PF_FILE）\n")
            f.write("- **因变量**：性能均值\n\n")

            f.write("### 1.4 统计假设检验\n\n")
            f.write("| 假设项目 | 描述 | 检验方法 |\n")
            f.write("|---------|-----|---------|\n")
            f.write("| 线性关系 | 各组内协变量与因变量呈线性关系 | Pearson相关系数 |\n")
            f.write("| 斜率齐性 | 协变量与因子无显著交互作用 | 交互项检验 |\n")
            f.write("| 残差正态性 | 残差服从正态分布 | Shapiro-Wilk检验 |\n")
            f.write("| 方差齐性 | 各组残差方差相等 | Levene检验 |\n\n")

            # 各模型详细结果
            for model_result in all_results:
                model_name = model_result['model']
                pp_result = model_result['pp_result']
                tg_result = model_result['tg_result']

                f.write(f"## 2. {model_name.upper()} 分析结果\n\n")

                # PP分析
                f.write("### 2.1 PP性能分析（协变量：n_prompt）\n\n")

                if 'model' in pp_result and 'summary' in pp_result['model']:
                    summary = pp_result['model']['summary']
                    f.write("#### 模型摘要\n\n")
                    f.write(f"- **R²**: {summary['r_squared']:.6f}\n")
                    f.write(f"- **调整R²**: {summary['adj_r_squared']:.6f}\n")
                    f.write(f"- **F统计量**: {summary['f_statistic']:.6f}\n")
                    f.write(f"- **p值**: {summary['f_p_value']:.6f}\n")
                    f.write(f"- **AIC**: {summary['aic']:.2f}\n")
                    f.write(f"- **BIC**: {summary['bic']:.2f}\n\n")

                    # ANOVA关键统计量
                    f.write("#### 方差分析关键统计\n\n")
                    summary = pp_result['model']['summary']
                    f.write(f"- **总体F统计量**: {summary['f_statistic']:.6f}\n")
                    f.write(f"- **总体p值**: {summary['f_p_value']:.6f}\n")
                    f.write("- **显著性**: " + ("显著" if summary['f_p_value'] < 0.05 else "不显著") + "\n\n")

                    # 调整均值
                    if 'adjusted_means' in pp_result:
                        f.write("#### 调整组均值\n\n")
                        f.write("| 提示词模式 | 调整均值 |\n")
                        f.write("|-----------|---------|\n")
                        for mode, adj_mean in pp_result['adjusted_means'].items():
                            f.write(f"| {mode} | {adj_mean:.6f} |\n")
                        f.write("\n")

                    # 效应大小
                    if 'effect_size' in pp_result:
                        effect = pp_result['effect_size']
                        f.write("#### 效应大小\n\n")
                        f.write(f"- **η²**: {effect['eta_squared']:.6f}\n")
                        f.write(f"- **偏η²**: {effect['partial_eta_squared']:.6f}\n")
                        f.write(f"- **效应解释**: {effect['interpretation']}\n\n")

                    # 假设检验结果
                    if 'assumptions' in pp_result:
                        f.write("#### 假设验证\n\n")
                        assump = pp_result['assumptions']

                        f.write("##### 线性关系评估\n")
                        if 'linearity' in assump:
                            for group, linear_assump in assump['linearity'].items():
                                f.write(f"- {group}: r = {linear_assump['correlation']:.3f}, p = {linear_assump['p_value']:.6f}, 符合线性: {linear_assump['is_linear']}\n")
                        f.write("\n")

                        f.write("##### 统计检验\n")
                        normality_p = assump.get('normality', {}).get('shapiro_wilk_p', 'N/A')
                        normality_passed = assump.get('normality', {}).get('normal_residuates', False)
                        f.write(f"- **正态性检验(Shapiro-Wilk)**: p = {normality_p if isinstance(normality_p, str) else f'{normality_p:.6f}'} - {'通过' if normality_passed else '未通过'}\n")

                        homo_p = assump.get('variance_homogeneity', {}).get('levene_p', 'N/A')
                        homo_passed = assump.get('variance_homogeneity', {}).get('equal_variances', False)
                        f.write(f"- **方差齐性(Levene)**: p = {homo_p if isinstance(homo_p, str) else f'{homo_p:.6f}'} - {'通过' if homo_passed else '未通过'}\n")

                        slope_p = assump.get('slope_homogeneity', {}).get('interaction_p_value', 'N/A')
                        slope_passed = assump.get('slope_homogeneity', {}).get('homogeneous_slopes', False)
                        f.write(f"- **斜率齐性**: p = {slope_p if isinstance(slope_p, str) else f'{slope_p:.6f}'} - {'通过' if slope_passed else '未通过'}\n\n")

                    # 事后检验
                    if 'post_hoc' in pp_result and 'significant_pairs' in pp_result['post_hoc']:
                        f.write("#### 事后多重比较\n\n")
                        f.write("| 比较组合 | 均值差 | 调整p值 | 显著 |\n")
                        f.write("|---------|-------|--------|-----|\n")
                        for pair in pp_result['post_hoc']['significant_pairs']:
                            sig_mark = "✓" if pair['reject'] else "✗"
                            mean_diff = pair['mean_diff']
                            p_adj = pair['p_adj']
                            f.write(f"| {pair['group1']} vs {pair['group2']} | {mean_diff if isinstance(mean_diff, str) else f'{mean_diff:.6f}'} | {p_adj if isinstance(p_adj, str) else f'{p_adj:.6f}'} | {sig_mark} |\n")
                        f.write("\n")

                # TG分析
                f.write("### 2.2 TG性能分析（协变量：n_gen）\n\n")

                if 'model' in tg_result and 'summary' in tg_result['model']:
                    summary = tg_result['model']['summary']
                    f.write("#### 模型摘要\n\n")
                    f.write(f"- **R²**: {summary['r_squared']:.6f}\n")
                    f.write(f"- **调整R²**: {summary['adj_r_squared']:.6f}\n")
                    f.write(f"- **F统计量**: {summary['f_statistic']:.6f}\n")
                    f.write(f"- **p值**: {summary['f_p_value']:.6f}\n")
                    f.write(f"- **AIC**: {summary['aic']:.2f}\n")
                    f.write(f"- **BIC**: {summary['bic']:.2f}\n\n")

                    # ANOVA关键统计量
                    f.write("#### 方差分析关键统计\n\n")
                    summary = tg_result['model']['summary']
                    f.write(f"- **总体F统计量**: {summary['f_statistic']:.6f}\n")
                    f.write(f"- **总体p值**: {summary['f_p_value']:.6f}\n")
                    f.write("- **显著性**: " + ("显著" if summary['f_p_value'] < 0.05 else "不显著") + "\n\n")

                    # 调整均值
                    if 'adjusted_means' in tg_result:
                        f.write("#### 调整组均值\n\n")
                        f.write("| 提示词模式 | 调整均值 |\n")
                        f.write("|-----------|---------|\n")
                        for mode, adj_mean in tg_result['adjusted_means'].items():
                            f.write(f"| {mode} | {adj_mean:.6f} |\n")
                        f.write("\n")

                    # 效应大小
                    if 'effect_size' in tg_result:
                        effect = tg_result['effect_size']
                        f.write("#### 效应大小\n\n")
                        f.write(f"- **η²**: {effect['eta_squared']:.6f}\n")
                        f.write(f"- **偏η²**: {effect['partial_eta_squared']:.6f}\n")
                        f.write(f"- **效应解释**: {effect['interpretation']}\n\n")

                    # 假设检验结果
                    if 'assumptions' in tg_result:
                        f.write("#### 假设验证\n\n")
                        assump = tg_result['assumptions']

                        f.write("##### 线性关系评估\n")
                        if 'linearity' in assump:
                            for group, linear_assump in assump['linearity'].items():
                                f.write(f"- {group}: r = {linear_assump['correlation']:.3f}, p = {linear_assump['p_value']:.6f}, 符合线性: {linear_assump['is_linear']}\n")
                        f.write("\n")

                        f.write("##### 统计检验\n")
                        normality_p = assump.get('normality', {}).get('shapiro_wilk_p', 'N/A')
                        normality_passed = assump.get('normality', {}).get('normal_residuates', False)
                        f.write(f"- **正态性检验(Shapiro-Wilk)**: p = {normality_p if isinstance(normality_p, str) else f'{normality_p:.6f}'} - {'通过' if normality_passed else '未通过'}\n")

                        homo_p = assump.get('variance_homogeneity', {}).get('levene_p', 'N/A')
                        homo_passed = assump.get('variance_homogeneity', {}).get('equal_variances', False)
                        f.write(f"- **方差齐性(Levene)**: p = {homo_p if isinstance(homo_p, str) else f'{homo_p:.6f}'} - {'通过' if homo_passed else '未通过'}\n")

                        slope_p = assump.get('slope_homogeneity', {}).get('interaction_p_value', 'N/A')
                        slope_passed = assump.get('slope_homogeneity', {}).get('homogeneous_slopes', False)
                        f.write(f"- **斜率齐性**: p = {slope_p if isinstance(slope_p, str) else f'{slope_p:.6f}'} - {'通过' if slope_passed else '未通过'}\n\n")

            # 综合比较
            f.write("## 3. 跨模型比较\n\n")
            f.write("### 3.1 PP性能汇总\n\n")
            f.write("| 模型 | R² | F统计量 | p值 | η² | 效应解释 |\n")
            f.write("|-----|----|---------|----|----|--------|\n")
            for model_result in all_results:
                model = model_result['model']
                pp = model_result['pp_result']
                if 'model' in pp and 'summary' in pp['model'] and 'effect_size' in pp:
                    summary = pp['model']['summary']
                    effect = pp['effect_size']
                    f.write(f"| {model} | {summary['r_squared']:.4f} | {summary['f_statistic']:.4f} | {summary['f_p_value']:.6f} | {effect['eta_squared']:.6f} | {effect['interpretation']} |\n")
            f.write("\n")

            f.write("### 3.2 TG性能汇总\n\n")
            f.write("| 模型 | R² | F统计量 | p值 | η² | 效应解释 |\n")
            f.write("|-----|----|---------|----|----|--------|\n")
            for model_result in all_results:
                model = model_result['model']
                tg = model_result['tg_result']
                if 'model' in tg and 'summary' in tg['model'] and 'effect_size' in tg:
                    summary = tg['model']['summary']
                    effect = tg['effect_size']
                    f.write(f"| {model} | {summary['r_squared']:.4f} | {summary['f_statistic']:.4f} | {summary['f_p_value']:.6f} | {effect['eta_squared']:.6f} | {effect['interpretation']} |\n")
            f.write("\n")

            f.write("## 4. 技术说明\n\n")
            f.write("### 4.1 分析方法\n")
            f.write("- **分析类型**: 协方差分析（ANCOVA）\n")
            f.write("- **统计软件**: Python (statsmodels, scipy)\n")
            f.write("- **协变量控制**: Token长度（PP用n_prompt，TG用n_gen）\n")
            f.write("- **置信水平**: 95% (α = 0.05)\n")
            f.write("- **效应大小指标**: η²和偏η²\n\n")

            f.write("### 4.2 数据处理\n")
            f.write("- **数据源**: SQLite数据库 benchmark_results.db\n")
            f.write("- **分析模型**: hunyuan_05b, qwen3_06b\n")
            f.write("- **提示词模式**: VP0, VP1, PF_FILE\n")
            f.write("- **性能指标**: PP和TG的均值\n")
            f.write("- **缺失数据**: 完全病例删除\n\n")

            f.write("### 4.3 输出文件\n")
            f.write("- **CSV结果**: ancova_analysis_results.csv\n")
            f.write("- **可视化图表**: (详见下方图表引用)\n")
            f.write("- **分析报告**: ancova_analysis_report.md\n\n")

            # 添加图表展示
            f.write("### 4.4 分析图表\n\n")

            f.write("#### Hunyuan_05b 模型 - PP性能分析（协变量：n_prompt）\n\n")
            f.write("![Hunyuan_05b PP ANCOVA](hunyuan_05b_pp_n_prompt_ancova_analysis.png)\n\n")
            f.write("*图1：左图展示PP性能与提示词长度的线性关系及回归线，中图为控制n_prompt后的各组调整均值，右图为残差分析*\n\n")

            f.write("#### Hunyuan_05b 模型 - TG性能分析（协变量：n_gen）\n\n")
            f.write("![Hunyuan_05b TG ANCOVA](hunyuan_05b_tg_n_gen_ancova_analysis.png)\n\n")
            f.write("*图2：左图展示TG性能与生成长度的线性关系及回归线，中图为控制n_gen后的各组调整均值，右图为残差分析*\n\n")

            f.write("#### Qwen3_06b 模型 - PP性能分析（协变量：n_prompt）\n\n")
            f.write("![Qwen3_06b PP ANCOVA](qwen3_06b_pp_n_prompt_ancova_analysis.png)\n\n")
            f.write("*图3：左图展示PP性能与提示词长度的线性关系及回归线，中图为控制n_prompt后的各组调整均值，右图为残差分析*\n\n")

            f.write("#### Qwen3_06b 模型 - TG性能分析（协变量：n_gen）\n\n")
            f.write("![Qwen3_06b TG ANCOVA](qwen3_06b_tg_n_gen_ancova_analysis.png)\n\n")
            f.write("*图4：左图展示TG性能与生成长度的线性关系及回归线，中图为控制n_gen后的各组调整均值，右图为残差分析*\n\n")

            f.write("**图表说明**：所有图表采用英文标签，使用安全字体(DejaVu Sans)渲染，采用1×3横向布局展示散点图、调整均值和残差分析。\n\n")

            f.write(f"---\n\n")
            f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            f.write(f"*生成工具: 协方差分析脚本*\n")

        print(f"分析报告已生成: {report_path}")
        return report_path

    def run_analysis(self):
        """运行完整的协方差分析"""
        print("开始提示词模式协方差分析(ANCOVA)...")

        # 获取数据
        df = self.get_ancova_data()
        if df.empty:
            print("未找到数据，分析终止")
            return

        # 处理数据
        data = self.process_data(df)
        if data is None or data.empty:
            print("数据处理失败，分析终止")
            return

        print(f"数据加载完成: {len(data)} 条记录")
        print(f"模型: {', '.join(data['model_name'].unique())}")
        print(f"提示词模式: {', '.join(data['prompt_mode'].unique())}")

        # 分析结果存储
        all_results = []

        # 按模型分别分析
        for model in data['model_name'].unique():
            print(f"\n分析模型: {model}")
            model_data = data[data['model_name'] == model]

            # PP分析
            pp_data = model_data[model_data['result_type'] == 'pp']
            pp_result = self.perform_ancova(pp_data, 'mean_value', 'prompt_mode', 'n_prompt')

            # TG分析
            tg_data = model_data[model_data['result_type'] == 'tg']
            tg_result = self.perform_ancova(tg_data, 'mean_value', 'prompt_mode', 'n_gen')

            # 生成可视化
            self.create_visualizations(pp_data, 'mean_value', 'prompt_mode', 'n_prompt', pp_result, model, 'pp')
            self.create_visualizations(tg_data, 'mean_value', 'prompt_mode', 'n_gen', tg_result, model, 'tg')

            all_results.append({
                'model': model,
                'pp_result': pp_result,
                'tg_result': tg_result
            })

        # 保存结果
        self.save_csv_results(all_results)
        self.generate_report(all_results)

        print(f"\n协方差分析完成，结果保存在: {self.output_dir}")

if __name__ == "__main__":
    analyzer = PromptModeANCOVA()
    analyzer.run_analysis()