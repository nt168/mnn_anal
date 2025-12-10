#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EAO初测结果数据分析工具
功能：从SQLite数据库中抽取数据，提供统计分析和可视化结果，不做解读
作者：EAO项目团队
日期：2025年11月21日
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

class DataAnalyzer:
    def __init__(self, db_path="benchmark_results.db"):
        """初始化分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "data_analysis")
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

    def get_data(self, result_type):
        """获取指定类型的数据"""
        try:
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
            ORDER BY br.result_parameter, s.model_name
            """
            df = pd.read_sql_query(query, self.conn, params=(result_type,))
            df['prompt_length'] = pd.to_numeric(df['prompt_length'])
            return df
        except Exception as e:
            print(f"获取{result_type}数据失败: {e}")
            return pd.DataFrame()  # 返回空DataFrame

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
        """创建CV稳定性图（并列柱状图）"""
        try:
            plt.figure(figsize=(12, 6))

            colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}
            prompt_lengths = sorted(df['prompt_length'].unique())
            models = df['model_name'].unique()

            bar_width = 0.35
            x_pos = np.arange(len(prompt_lengths))

            for i, model in enumerate(models):
                model_data = df[df['model_name'] == model]
                # 修复：对每个prompt_length的所有测试结果进行统计聚合（使用中位数更稳健）
                cv_values = []
                for length in prompt_lengths:
                    length_data = model_data[model_data['prompt_length'] == length]
                    if not length_data.empty:
                        # 使用中位数，避免异常值影响
                        cv_median = length_data['cv_value'].median()
                        cv_values.append(cv_median)
                    else:
                        cv_values.append(0)

                offset = (i - 0.5) * bar_width
                plt.bar(x_pos + offset, cv_values, width=bar_width, alpha=0.7,
                       color=colors[model], label=model)

            plt.xlabel('Prompt Length (tokens)')
            plt.ylabel('Coefficient of Variation CV (%)')
            plt.title(f'{result_type.upper()} Stability Analysis (CV values)')
            plt.legend()
            plt.xticks(x_pos, [str(length) for length in prompt_lengths], rotation=45)
            plt.grid(True, axis='y', alpha=0.3)
            # 移除1%和3%参考线，避免Y轴过度压缩（PP和TG的实际CV值都很低，PP平均0.05%，TG平均0.15%）

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建CV图表失败: {e}")
            plt.close()

    def generate_data_report(self, pp_results, tg_results):
        """生成数据报告（仅提供数据结果）"""

        report = f"""# EAO初测结果数据报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: benchmark_results.db

---

## PP(Prefill阶段)数据结果

"""

        for model_name, model_data in pp_results.items():
            stats = model_data['statistics']
            regression = model_data['regression']

            report += f"""### {model_name}

#### 基础统计数据
- 数据点: {stats['data_points']}
- 提示词长度范围: {stats['min_length']} - {stats['max_length']} tokens
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

        report += "![PP性能分析](pp_performance.png)\n\n"
        report += "![PP稳定性分析](pp_cv.png)\n\n"
        report += "---\n\n"

        report += "## TG(Decode阶段)数据结果\n\n"

        for model_name, model_data in tg_results.items():
            stats = model_data['statistics']
            regression = model_data['regression']

            report += f"""### {model_name}

#### 基础统计数据
- 数据点: {stats['data_points']}
- 提示词长度范围: {stats['min_length']} - {stats['max_length']} tokens
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

        report += "![TG性能分析](tg_performance.png)\n\n"
        report += "![TG稳定性分析](tg_cv.png)\n\n"

        # 综合数据表
        report += "---\n\n## 数据汇总表\n\n"
        report += "| 指标 | PP | TG |\n"
        report += "|------|----|----|\n"

        pp_avg_cv = pp_results[list(pp_results.keys())[0]]['statistics']['avg_cv']
        tg_avg_cv = tg_results[list(tg_results.keys())[0]]['statistics']['avg_cv']

        report += f"| 平均CV | {pp_avg_cv:.3f}% | {tg_avg_cv:.3f}% |\n"

        report += f"\n\n数据处理完成"

        return report

    def create_performance_plot(self, df, result_type, analysis_results, save_path=None):
        """创建性能散点图（按模型分别，含误差棒和回归线）"""
        try:
            plt.figure(figsize=(14, 10))

            colors = {
                'hunyuan_05b': {'point': '#1f77b4', 'error': '#2E8B57', 'line': '#1f77b4'},
                'qwen3_06b': {'point': '#ff7f0e', 'error': '#D2691E', 'line': '#ff7f0e'}
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

                # 绘制线性和二次拟合（根据最佳类型选择线型）
                # 计算线性拟合
                a_linear = analysis['linear']['coef']
                b_linear = analysis['linear']['intercept']
                y_linear = a_linear * X_range + b_linear
                r2_linear = analysis['linear']['r2']
                label_linear = f'{model} (Linear R²={r2_linear:.3f})'

                if analysis['best']['type'] == 'linear':
                    # 最佳是线性：只绘制一条实线（线性）
                    plt.plot(X_range, y_linear, '-', color=colors[model]['line'],
                            linewidth=2, alpha=0.8, label=label_linear)
                else:
                    # 最佳是二次：实线绘制二次，虚线绘制线性
                    # 计算二次拟合
                    a_quad = analysis['quadratic']['coef_a']  # x²系数
                    b_quad = analysis['quadratic']['coef_b']  # x系数
                    c_quad = analysis['quadratic']['intercept']  # 常数项
                    y_quad = a_quad * X_range**2 + b_quad * X_range + c_quad
                    r2_quad = analysis['quadratic']['r2']
                    label_quad = f'{model} (Quadratic R²={r2_quad:.3f})'

                    # 实线绘制最佳拟合一（二次）
                    plt.plot(X_range, y_quad, '-', color=colors[model]['line'],
                            linewidth=2.5, alpha=0.9, label=label_quad)
                    # 虚线绘制线性拟合
                    plt.plot(X_range, y_linear, '--', color=colors[model]['line'],
                            linewidth=1.5, alpha=0.7, label=label_linear)

            plt.xlabel('Prompt Length (tokens)')
            plt.ylabel(f'{result_type.upper()} Performance (tokens/sec)')
            plt.title(f'{result_type.upper()} Performance vs Prompt Length')
            plt.legend()
            plt.grid(True, alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建性能图表失败: {e}")
            plt.close()

    def run_analysis(self):
        """执行完整数据处理流程"""
        print("开始数据处理...")

        # 获取数据
        pp_df = self.get_data('pp')
        tg_df = self.get_data('tg')

        print(f"PP数据: {len(pp_df)} 条, TG数据: {len(tg_df)} 条")

        # 按模型分析（包含所有回归分析）
        print("进行回归分析...")
        pp_results = self.analyze_by_model(pp_df, 'pp')
        tg_results = self.analyze_by_model(tg_df, 'tg')

        # 生成图表（传入分析结果）
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
        report = self.generate_data_report(pp_results, tg_results)

        with open(f'{self.output_dir}/data_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("数据处理完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = DataAnalyzer()
    analyzer.run_analysis()