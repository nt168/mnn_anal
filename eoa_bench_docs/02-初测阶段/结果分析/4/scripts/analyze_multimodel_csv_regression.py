#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型CSV数据回归分析工具
功能：分析Qwen3_0.6B、hunyuan_05B、SmolVLM2-256M三个模型的CSV回归关系
作者：EAO项目团队
日期：2025年12月11日
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
import re
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class MultiModelCSVRegressionAnalyzer:
    def __init__(self):
        """初始化多模型CSV回归分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = os.path.join(script_dir, "..", "data", "D3000Mstep-p64n16.csv")
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "csv_regression")
        os.makedirs(self.output_dir, exist_ok=True)
        self.raw_data = None
        self.processed_data = None

    def load_csv_data(self):
        """加载并解析CSV数据"""
        try:
            print(f"正在加载CSV文件: {self.csv_path}")
            df = pd.read_csv(self.csv_path, header=None)

            # 解析CSV数据结构
            parsed_data = []
            current_model = None

            for idx, row in df.iterrows():
                row_values = row.values.tolist()
                row_str = ' '.join([str(v) for v in row_values if pd.notna(v)])

                # 提取模型名
                if any(model in row_str for model in ['Qwen3_0.6B', 'hunyuan_05B', 'SmolVLM2-256M']):
                    for model in ['Qwen3_0.6B', 'hunyuan_05B', 'SmolVLM2-256M']:
                        if model in row_str:
                            current_model = model
                            break
                    continue

                # 提取测试参数行
                if 't=' in row_str and 'p=' in row_str and 'n=' in row_str:
                    # 解析参数
                    t_match = re.search(r't=(\d+)', row_str)
                    p_match = re.search(r'p=(\d+)', row_str)
                    n_match = re.search(r'n=(\d+)', row_str)

                    if t_match and p_match and n_match:
                        t = int(t_match.group(1))
                        p = int(p_match.group(1))
                        n = int(n_match.group(1))

                        # 查找对应的性能数据行（通常在下一行）
                        if idx + 1 < len(df):
                            next_row = df.iloc[idx + 1].values.tolist()
                            # 提取数值数据
                            numeric_values = []
                            for val in next_row:
                                if pd.notna(val) and isinstance(val, (int, float)):
                                    numeric_values.append(val)
                                elif pd.notna(val) and str(val).replace('.', '').isdigit():
                                    numeric_values.append(float(str(val)))

                            # 确保有足够的数值列：预填tps, 预填方差, 解码tps, 解码方差, 加载时间, 加载方差
                            if len(numeric_values) >= 6:
                                parsed_data.append({
                                    'model': current_model,
                                    'threads': t,
                                    'n_prompt': p,
                                    'n_gen': n,
                                    'prefill_tps': numeric_values[0],
                                    'prefill_var': numeric_values[1],
                                    'decode_tps': numeric_values[2],
                                    'decode_var': numeric_values[3],
                                    'load_time': numeric_values[4],
                                    'load_var': numeric_values[5]
                                })

            self.processed_data = pd.DataFrame(parsed_data)
            print(f"成功解析CSV数据，共{len(self.processed_data)}条记录")

            # 计算变异系数
            self.processed_data['prefill_cv'] = (self.processed_data['prefill_var']**0.5 /
                                                 self.processed_data['prefill_tps'] * 100)
            self.processed_data['decode_cv'] = (self.processed_data['decode_var']**0.5 /
                                              self.processed_data['decode_tps'] * 100)

            return True

        except Exception as e:
            print(f"加载CSV文件失败: {e}")
            return False

    def get_model_data(self, model, result_type):
        """获取指定模型的数据"""
        if self.processed_data is None:
            return pd.DataFrame()

        model_data = self.processed_data[self.processed_data['model'] == model]

        if result_type == 'prefill':
            result_df = model_data[['n_prompt', 'prefill_tps', 'prefill_var', 'prefill_cv']].copy()
            result_df.columns = ['prompt_length', 'mean_value', 'std_value', 'cv_value']
        elif result_type == 'decode':
            result_df = model_data[['n_gen', 'decode_tps', 'decode_var', 'decode_cv']].copy()
            result_df.columns = ['prompt_length', 'mean_value', 'std_value', 'cv_value']
        else:
            return pd.DataFrame()

        return result_df

    def analyze_by_model(self, data, result_type):
        """按模型分别分析"""
        results = {}

        if result_type == 'prefill':
            X_col = 'n_prompt'
            y_col = 'prefill_tps'
            cv_col = 'prefill_cv'
            length_name = 'n_prompt'
        elif result_type == 'decode':
            X_col = 'n_gen'
            y_col = 'decode_tps'
            cv_col = 'decode_cv'
            length_name = 'n_gen'
        else:
            return results

        for model in data['model'].unique():
            model_data = data[data['model'] == model]

            # 基础统计
            stats = {
                'data_points': len(model_data),
                'min_length': model_data[X_col].min(),
                'max_length': model_data[X_col].max(),
                'min_performance': model_data[y_col].min(),
                'max_performance': model_data[y_col].max(),
                'avg_cv': model_data[cv_col].mean(),
                'min_cv': model_data[cv_col].min(),
                'max_cv': model_data[cv_col].max()
            }

            # 回归分析
            X = model_data[X_col].values.reshape(-1, 1)
            y = model_data[y_col].values

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

    def create_cv_plot(self, data, result_type, save_path=None):
        """创建CV稳定性图"""
        try:
            plt.figure(figsize=(12, 6))

            colors = {
                'Qwen3_0.6B': '#1f77b4',
                'hunyuan_05B': '#ff7f0e',
                'SmolVLM2-256M': '#2ca02c'
            }

            if result_type == 'prefill':
                X_col = 'n_prompt'
                cv_col = 'prefill_cv'
                title_prefix = 'n_prompt'
            else:
                X_col = 'n_gen'
                cv_col = 'decode_cv'
                title_prefix = 'n_gen'

            lengths = sorted(data[X_col].unique())
            models = data['model'].unique()

            bar_width = 0.25
            x_pos = np.arange(len(lengths))

            for i, model in enumerate(models):
                model_data = data[data['model'] == model]
                cv_values = []
                for length in lengths:
                    length_data = model_data[model_data[X_col] == length]
                    if not length_data.empty:
                        cv_median = length_data[cv_col].median()
                        cv_values.append(cv_median)
                    else:
                        cv_values.append(0)

                offset = (i - 1) * bar_width
                plt.bar(x_pos + offset, cv_values, width=bar_width, alpha=0.7,
                       color=colors.get(model, '#333333'), label=model)

            plt.xlabel(f'{result_type.title()} length (tokens)')
            plt.ylabel('Coefficient of Variation CV (%)')
            plt.title(f'{result_type.title()} Stability Analysis (CV values)')
            plt.legend()
            plt.xticks(x_pos, [str(length) for length in lengths], rotation=45)
            plt.grid(True, axis='y', alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"创建CV图表失败: {e}")
            plt.close()

    def create_performance_plot(self, data, result_type, analysis_results, save_path=None):
        """创建性能散点图"""
        try:
            plt.figure(figsize=(14, 10))

            colors = {
                'Qwen3_0.6B': {'point': '#1f77b4', 'error': '#2E8B57', 'line': '#1f77b4'},
                'hunyuan_05B': {'point': '#ff7f0e', 'error': '#D2691E', 'line': '#ff7f0e'},
                'SmolVLM2-256M': {'point': '#2ca02c', 'error': '#228B22', 'line': '#2ca02c'}
            }

            if result_type == 'prefill':
                X_col = 'n_prompt'
                y_col = 'prefill_tps'
                var_col = 'prefill_var'
            else:
                X_col = 'n_gen'
                y_col = 'decode_tps'
                var_col = 'decode_var'

            # 绘制每个模型的数据点（带误差棒）
            for model in data['model'].unique():
                model_data = data[data['model'] == model]

                plt.errorbar(model_data[X_col], model_data[y_col],
                            yerr=np.sqrt(model_data[var_col]),
                            fmt='o', capsize=4,
                            markerfacecolor=colors[model]['point'],
                            markeredgecolor='white',
                            ecolor=colors[model]['error'],
                            elinewidth=2,
                            alpha=0.7,
                            label=f'{model} (data)')

            # 为每个模型绘制回归线
            for model in data['model'].unique():
                model_data = data[data['model'] == model]
                analysis = analysis_results[model]['regression']

                X_range = np.linspace(model_data[X_col].min(),
                                    model_data[X_col].max(), 100)

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

            len_label = 'n_prompt' if result_type == 'prefill' else 'n_gen'
            plt.xlabel(f'{len_label} (tokens)')
            plt.ylabel(f'{result_type.title()} Performance (tokens/sec)')
            plt.title(f'{result_type.title()} Performance vs {len_label}')
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
        report = f"""# 多模型CSV数据回归分析报告

## 基本信息
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
数据来源: D3000Mstep-p64n16.csv
分析模型: Qwen3_0.6B, hunyuan_05B, SmolVLM2-256M
测试环境: D3000M CPU 6小核(0,1,2,4,5,6)

## 测试配置信息
- 线程数: 6
- 精度: Low (precision=2)
- KV缓存: true
- 内存映射: true
- 动态优化: dynamicOption=7
- Prompt模式: vp=1

---

## Prefill阶段数据结果

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

        report += "![Prefill性能分析](pp_performance.png)\n\n"
        report += "![Prefill稳定性分析](pp_cv.png)\n\n"
        report += "---\n\n"

        report += "## Decode阶段数据结果\n\n"

        for model_name, model_data in tg_results.items():
            stats = model_data['statistics']
            regression = model_data['regression']

            report += f"""### {model_name}

#### 基础统计数据
- 数据点: {stats['data_points']}
- n_gen范围: {stats['min_length']} - {stats['max_length']} tokens
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

        report += "![Decode性能分析](tg_performance.png)\n\n"
        report += "![Decode稳定性分析](tg_cv.png)\n\n"

        # 综合数据表
        report += "---\n\n## 数据汇总表\n\n"
        report += "| 指标 | Prefill | Decode |\n"
        report += "|------|---------|--------|\n"

        for model_name in pp_results.keys():
            if model_name in tg_results:
                pp_avg_cv = pp_results[model_name]['statistics']['avg_cv']
                tg_avg_cv = tg_results[model_name]['statistics']['avg_cv']
                pp_r2 = pp_results[model_name]['regression']['best']['r2']
                tg_r2 = tg_results[model_name]['regression']['best']['r2']
                report += f"| {model_name} R² | PP:{pp_r2:.4f} | TG:{tg_r2:.4f} |\n"
                report += f"| {model_name} CV | PP:{pp_avg_cv:.3f}% | TG:{tg_avg_cv:.3f}% |\n"

        report += f"\n数据处理完成\n"

        return report

    def run_analysis(self):
        """执行完整数据处理流程"""
        print("开始多模型CSV数据回归分析...")

        # 加载CSV数据
        if not self.load_csv_data():
            print("CSV数据加载失败")
            return

        if self.processed_data.empty:
            print("未找到有效数据")
            return

        print(f"解析到的数据概览:")
        print(f"- 模型数量: {self.processed_data['model'].nunique()}")
        print(f"- 总记录数: {len(self.processed_data)}")
        print(f"- 模型列表: {', '.join(self.processed_data['model'].unique())}")

        # 按模型分析
        print("进行回归分析...")
        pp_results = self.analyze_by_model(self.processed_data, 'prefill')
        tg_results = self.analyze_by_model(self.processed_data, 'decode')

        # 生成图表
        print("生成图表...")
        self.create_performance_plot(self.processed_data, 'prefill', pp_results,
                                   f'{self.output_dir}/pp_performance.png')
        self.create_cv_plot(self.processed_data, 'prefill',
                           f'{self.output_dir}/pp_cv.png')
        self.create_performance_plot(self.processed_data, 'decode', tg_results,
                                   f'{self.output_dir}/tg_performance.png')
        self.create_cv_plot(self.processed_data, 'decode',
                           f'{self.output_dir}/tg_cv.png')

        # 导出处理后的数据
        self.processed_data.to_csv(f'{self.output_dir}/processed_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        report = self.generate_md_report(pp_results, tg_results)

        with open(f'{self.output_dir}/csv_regression_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print("多模型CSV数据回归分析完成")
        print("文件位置:", self.output_dir)

if __name__ == "__main__":
    analyzer = MultiModelCSVRegressionAnalyzer()
    analyzer.run_analysis()