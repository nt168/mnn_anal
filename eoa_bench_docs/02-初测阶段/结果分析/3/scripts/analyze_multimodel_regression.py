#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型对比回归分析工具
功能：分析qwen2_5_0_5b, smolvlm2_256m, llama_3_2_1b三个模型的基准测试回归关系
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
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class MultiModelRegressionAnalyzer:
    def __init__(self):
        """初始化多模型对比回归分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "multimodel_regression")
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

    def get_multimodel_data(self, result_type):
        """获取三模型基准测试数据"""
        try:
            # 从result_parameter获取n_prompt，针对三个模型的基准测试
            query = """
            SELECT
                br.result_parameter as prompt_length,
                br.mean_value,
                br.std_value,
                (br.std_value/br.mean_value*100) as cv_value,
                s.model_name
            FROM benchmark_results br
            JOIN case_definitions cd ON br.case_id = cd.id
            JOIN suites s ON cd.suite_id = s.id
            WHERE br.result_type = ?
            AND s.model_name IN ('qwen2_5_0_5b', 'smolvlm2_256m', 'llama_3_2_1b')
            AND s.task_id = 4
            ORDER BY br.result_parameter, s.model_name
            """
            df = pd.read_sql_query(query, self.conn, params=(result_type,))
            df['prompt_length'] = pd.to_numeric(df['prompt_length'], errors='coerce')

            # 去除无效数据
            df = df.dropna(subset=['prompt_length'])

            return df
        except Exception as e:
            print(f"获取{result_type}数据失败: {e}")
            return pd.DataFrame()

    def analyze_by_model(self, df, result_type):
        """按模型分别分析"""
        results = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]

            # 基础统计
            stats = {
                'data_points': len(model_data),
                'min_length': model_data['prompt_length'].min(),
                'max_length': model_data['prompt_length'].max(),
                'min_performance': model_data['mean_value'].min(),
                'max_performance': model_data['mean_value'].max(),
                'avg_cv': model_data['cv_value'].mean(),
                'min_cv': model_data['cv_value'].min(),
                'max_cv': model_data['cv_value'].max()
            }

            # 回归分析
            X = model_data['prompt_length'].values.reshape(-1, 1)
            y = model_data['mean_value'].values

            # 线性回归
            linear_model = LinearRegression()
            linear_model.fit(X, y)
            y_pred = linear_model.predict(X)
            r2_linear = r2_score(y, y_pred)

            # 二次回归
            X_poly = np.column_stack([X, X**2])
            quad_model = LinearRegression()
            quad_model.fit(X_poly, y)
            y_pred_quad = quad_model.predict(X_poly)
            r2_quad = r2_score(y, y_pred_quad)

            regression = {
                'linear': {
                    'equation': f'y = {linear_model.coef_[0]:.4f}x + {linear_model.intercept_:.4f}',
                    'r2': r2_linear,
                    'slope': float(linear_model.coef_[0]),
                    'intercept': float(linear_model.intercept_),
                    'coef': float(linear_model.coef_[0])
                },
                'quadratic': {
                    'equation': f'y = {quad_model.coef_[1]:.6f}x² + {quad_model.coef_[0]:.4f}x + {quad_model.intercept_:.4f}',
                    'r2': r2_quad,
                    'coef_a': float(quad_model.coef_[1]),  # x²的系数
                    'coef_b': float(quad_model.coef_[0]),  # x的系数
                    'intercept': float(quad_model.intercept_)
                },
                'best': {
                    'type': 'quadratic' if r2_quad > r2_linear else 'linear',
                    'r2': max(r2_linear, r2_quad)
                }
            }

            results[model] = {
                'statistics': stats,
                'regression': regression,
                'raw_data': model_data
            }

        return results

    def create_cv_plot(self, df, result_type, save_path=None):
        """创建CV稳定性图"""
        try:
            plt.figure(figsize=(12, 6))

            colors = {
                'qwen2_5_0_5b': '#1f77b4',
                'smolvlm2_256m': '#ff7f0e',
                'llama_3_2_1b': '#2ca02c'
            }
            prompt_lengths = sorted(df['prompt_length'].unique())
            models = df['model_name'].unique()

            bar_width = 0.25
            x_pos = np.arange(len(prompt_lengths))

            for i, model in enumerate(models):
                model_data = df[df['model_name'] == model]
                cv_values = []
                for length in prompt_lengths:
                    length_data = model_data[model_data['prompt_length'] == length]
                    if not length_data.empty:
                        cv_median = length_data['cv_value'].median()
                        cv_values.append(cv_median)
                    else:
                        cv_values.append(0)

                offset = (i - 1) * bar_width
                plt.bar(x_pos + offset, cv_values, width=bar_width, alpha=0.7,
                       color=colors.get(model, '#333333'), label=model)

            plt.xlabel('n_prompt (tokens)')
            plt.ylabel('Coefficient of Variation CV (%)')
            plt.title(f'{result_type.upper()} Stability Analysis (CV values)')
            plt.legend()
            plt.xticks(x_pos, [str(length) for length in prompt_lengths], rotation=45)
            plt.grid(True, axis='y', alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建CV图表失败: {e}")
            plt.close()

    def create_performance_plot(self, df, result_type, analysis_results, save_path=None):
        """创建性能散点图"""
        try:
            plt.figure(figsize=(14, 10))

            colors = {
                'qwen2_5_0_5b': {'point': '#1f77b4', 'error': '#2E8B57', 'line': '#1f77b4'},
                'smolvlm2_256m': {'point': '#ff7f0e', 'error': '#D2691E', 'line': '#ff7f0e'},
                'llama_3_2_1b': {'point': '#2ca02c', 'error': '#228B22', 'line': '#2ca02c'}
            }

            # 绘制每个模型的数据点（带误差棒）
            for model in df['model_name'].unique():
                model_data = df[df['model_name'] == model]

                plt.errorbar(model_data['prompt_length'], model_data['mean_value'],
                            yerr=model_data['std_value'],
                            fmt='o', capsize=4,
                            markerfacecolor=colors[model]['point'],
                            markeredgecolor='white',
                            ecolor=colors[model]['error'],
                            elinewidth=2,
                            alpha=0.7,
                            label=f'{model} (data)')

            # 为每个模型绘制回归线
            for model in df['model_name'].unique():
                model_data = df[df['model_name'] == model]
                analysis = analysis_results[model]['regression']

                X_range = np.linspace(model_data['prompt_length'].min(),
                                    model_data['prompt_length'].max(), 100)

                # 计算线性拟合
                a_linear = analysis['linear']['coef']
                b_linear = analysis['linear']['intercept']
                y_linear = a_linear * X_range + b_linear
                r2_linear = analysis['linear']['r2']
                label_linear = f'{model} (Linear R²={r2_linear:.3f})'

                if analysis['best']['type'] == 'linear':
                    plt.plot(X_range, y_linear, '-', color=colors[model]['line'],
                            linewidth=2, alpha=0.8, label=label_linear)
                else:
                    a_quad = analysis['quadratic']['coef_a']
                    b_quad = analysis['quadratic']['coef_b']
                    c_quad = analysis['quadratic']['intercept']
                    y_quad = a_quad * X_range**2 + b_quad * X_range + c_quad
                    r2_quad = analysis['quadratic']['r2']
                    label_quad = f'{model} (Quadratic R²={r2_quad:.3f})'

                    plt.plot(X_range, y_quad, '-', color=colors[model]['line'],
                            linewidth=2.5, alpha=0.9, label=label_quad)
                    plt.plot(X_range, y_linear, '--', color=colors[model]['line'],
                            linewidth=1.5, alpha=0.7, label=label_linear)

            plt.xlabel('n_prompt (tokens)')
            plt.ylabel(f'{result_type.upper()} Performance (tokens/sec)')
            plt.title(f'{result_type.upper()} Performance vs n_prompt')
            plt.legend()
            plt.grid(True, alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建性能图表失败: {e}")
            plt.close()

    def generate_md_report(self, pp_results, tg_results):
        """生成MD报告"""
        report = f"""# 多模型对比回归分析数据报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: benchmark_results.db
分析模型: qwen2_5_0_5b, smolvlm2_256m, llama_3_2_1b
测试类型: 三模型n/p组合扫描基准测试

---

## PP(Prefill阶段)数据结果

"""

        for model_name, model_data in pp_results.items():
            stats = model_data['statistics']
            regression = model_data['regression']

            report += f"""### {model_name}

#### 基础统计数据
- 数据点: {stats['data_points']}
- n_prompt范围: {stats['min_length']} - {stats['max_length']} tokens
- 性能值范围: {stats['min_performance']:.2f} - {stats['max_performance']:.2f} tokens/sec
- CV值:
  - 平均: {stats['avg_cv']:.3f}%
  - 最小: {stats['min_cv']:.3f}%
  - 最大: {stats['max_cv']:.3f}%

#### 回归分析结果
- 线性回归: {regression['linear']['equation']} (R²={regression['linear']['r2']:.4f})
- 二次回归: {regression['quadratic']['equation']} (R²={regression['quadratic']['r2']:.4f})
- 最佳模型: {regression['best']['type']} (R²={regression['best']['r2']:.4f})
- 线性回归斜率: {regression['linear']['slope']:.4f}

"""

        report += "![PP性能分析](pp_performance.png)\\n\\n"
        report += "![PP稳定性分析](pp_cv.png)\\n\\n"
        report += "---\\n\\n"

        report += "## TG(Decode阶段)数据结果\\n\\n"

        for model_name, model_data in tg_results.items():
            stats = model_data['statistics']
            regression = model_data['regression']

            report += f"""### {model_name}

#### 基础统计数据
- 数据点: {stats['data_points']}
- n_prompt范围: {stats['min_length']} - {stats['max_length']} tokens
- 性能值范围: {stats['min_performance']:.2f} - {stats['max_performance']:.2f} tokens/sec
- CV值:
  - 平均: {stats['avg_cv']:.3f}%
  - 最小: {stats['min_cv']:.3f}%
  - 最大: {stats['max_cv']:.3f}%

#### 回归分析结果
- 线性回归: {regression['linear']['equation']} (R²={regression['linear']['r2']:.4f})
- 二次回归: {regression['quadratic']['equation']} (R²={regression['quadratic']['r2']:.4f})
- 最佳模型: {regression['best']['type']} (R²={regression['best']['r2']:.4f})
- 线性回归斜率: {regression['linear']['slope']:.4f}

"""

        report += "![TG性能分析](tg_performance.png)\\n\\n"
        report += "![TG稳定性分析](tg_cv.png)\\n\\n"

        # 综合数据表
        report += "---\\n\\n## 数据汇总表\\n\\n"
        report += "| 指标 | PP | TG |\\n"
        report += "|------|----|----|\\n"

        if pp_results and tg_results:
            pp_avg_cv = pp_results[list(pp_results.keys())[0]]['statistics']['avg_cv']
            tg_avg_cv = tg_results[list(tg_results.keys())[0]]['statistics']['avg_cv']
            report += f"| 平均CV | {pp_avg_cv:.3f}% | {tg_avg_cv:.3f}% |\\n"

        report += f"\\n\\n数据处理完成"

        return report

    def run_analysis(self):
        """执行完整数据处理流程"""
        print("开始多模型对比回归分析...")

        # 获取数据
        pp_df = self.get_multimodel_data('pp')
        tg_df = self.get_multimodel_data('tg')

        print(f"PP数据: {len(pp_df)} 条, TG数据: {len(tg_df)} 条")

        if pp_df.empty or tg_df.empty:
            print("未找到测试数据")
            return

        # 按模型分析
        print("进行回归分析...")
        pp_results = self.analyze_by_model(pp_df, 'pp')
        tg_results = self.analyze_by_model(tg_df, 'tg')

        # 生成图表
        print("生成图表...")
        self.create_performance_plot(pp_df, 'pp', pp_results, f'{self.output_dir}/pp_performance.png')
        self.create_cv_plot(pp_df, 'pp', f'{self.output_dir}/pp_cv.png')
        self.create_performance_plot(tg_df, 'tg', tg_results, f'{self.output_dir}/tg_performance.png')
        self.create_cv_plot(tg_df, 'tg', f'{self.output_dir}/tg_cv.png')

        # 导出原始数据
        pp_df.to_csv(f'{self.output_dir}/pp_data.csv', index=False)
        tg_df.to_csv(f'{self.output_dir}/tg_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        report = self.generate_md_report(pp_results, tg_results)

        with open(f'{self.output_dir}/multimodel_regression_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("多模型对比回归分析完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = MultiModelRegressionAnalyzer()
    analyzer.run_analysis()