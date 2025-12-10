#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
threads参数影响分析工具 - 重写版本
功能：分析threads参数对MNN LLM推理性能的影响
正确理解：同一模型(hunyuan_05b)在1、2、6线程下的性能测试
- PP性能主要与n_prompt相关
- TG性能主要与n_gen相关
- 将3种线程的图绘制在一张图中进行对比

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

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

class ThreadsAnalyzer:
    def __init__(self):
        """初始化threads分析工具"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "benchmark_results.db")
        self.conn = None
        self.output_dir = os.path.join(script_dir, "..", "analysis_output", "threads_analysis")
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

    def get_threads_data(self):
        """获取线程测试数据，整合所有suite"""
        try:
            query = """
            SELECT
                s.model_name,
                cd.base_parameters,
                br.result_type,
                br.result_parameter,
                br.mean_value,
                br.std_value,
                (br.std_value/br.mean_value*100) as cv_value,
                s.name as suite_name
            FROM benchmark_results br
            JOIN case_definitions cd ON br.case_id = cd.id
            JOIN suites s ON cd.suite_id = s.id
            WHERE s.name IN ('pn_grid_t1', 'pn_grid_t2', 'pn_grid_t6')
            ORDER BY s.name, br.result_type, br.result_parameter
            """
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"获取threads数据失败: {e}")
            return pd.DataFrame()

    def extract_parameters(self, df):
        """解析参数并标准化数据结构"""
        if df.empty:
            return df

        # 解析base_parameters
        def parse_params(param_str):
            try:
                params = eval(param_str)
                return {
                    'threads': int(params.get('threads', 0)),
                    'n_prompt': int(params.get('n_prompt', 0)),
                    'n_gen': int(params.get('n_gen', 0))
                }
            except:
                return {'threads': 0, 'n_prompt': 0, 'n_gen': 0}

        # 解析参数
        param_data = df['base_parameters'].apply(parse_params)
        param_df = pd.DataFrame(param_data.tolist())

        # 合并数据
        df = pd.concat([df.reset_index(drop=True), param_df], axis=1)

        # 根据suite名称验证线程数（额外检查）
        def validate_threads(row):
            if 't1' in row['suite_name']:
                return 1
            elif 't2' in row['suite_name']:
                return 2
            elif 't6' in row['suite_name']:
                return 6
            return row['threads']

        df['threads'] = df.apply(validate_threads, axis=1)

        # 过滤无效数据
        df = df[(df['threads'] > 0) & (df['n_prompt'] > 0) & (df['n_gen'] > 0)]

        return df

    def analyze_pp_performance(self, df):
        """分析PP性能（基于n_prompt）- 使用正确的合并标准差"""
        pp_data = df[df['result_type'] == 'pp'].copy()

        if pp_data.empty:
            return None

        results = {}

        for thread in [1, 2, 6]:
            thread_data = pp_data[pp_data['threads'] == thread]
            if not thread_data.empty:
                stats_list = []

                for n_prompt, group in thread_data.groupby('n_prompt'):
                    # 计算合并标准差 (Propagation of uncertainty)
                    # 总方差 = 组间方差 + 平均组内方差

                    # 组间方差 (均值之间)
                    between_var = group['mean_value'].var()

                    # 平均组内方差 (每个测试点的内部方差)
                    within_var = (group['std_value']**2).mean()

                    # 合并标准差
                    merged_std = np.sqrt(between_var + within_var)

                    # 合并CV = 合并标准差 / 均值 * 100
                    merged_cv = (merged_std / group['mean_value'].mean()) * 100

                    stats = {
                        'n_prompt': n_prompt,
                        'avg_performance': group['mean_value'].mean(),
                        'std_performance': merged_std,  # 使用合并标准差
                        'min_performance': group['mean_value'].min(),
                        'max_performance': group['mean_value'].max(),
                        'avg_cv': merged_cv  # 使用合并CV
                    }
                    stats_list.append(stats)

                results[thread] = pd.DataFrame(stats_list)

        return results

    def analyze_tg_performance(self, df):
        """分析TG性能（基于n_gen）- 使用正确的合并标准差"""
        tg_data = df[df['result_type'] == 'tg'].copy()

        if tg_data.empty:
            return None

        results = {}

        for thread in [1, 2, 6]:
            thread_data = tg_data[tg_data['threads'] == thread]
            if not thread_data.empty:
                stats_list = []

                for n_gen, group in thread_data.groupby('n_gen'):
                    # 计算合并标准差
                    between_var = group['mean_value'].var()
                    within_var = (group['std_value']**2).mean()
                    merged_std = np.sqrt(between_var + within_var)
                    merged_cv = (merged_std / group['mean_value'].mean()) * 100

                    stats = {
                        'n_gen': n_gen,
                        'avg_performance': group['mean_value'].mean(),
                        'std_performance': merged_std,  # 使用合并标准差
                        'min_performance': group['mean_value'].min(),
                        'max_performance': group['mean_value'].max(),
                        'avg_cv': merged_cv  # 使用合并CV
                    }
                    stats_list.append(stats)

                results[thread] = pd.DataFrame(stats_list)

        return results

    def calculate_scaling_efficiency(self, pp_results, tg_results):
        """计算线程扩展效率"""
        efficiency = {}

        # PP扩展效率
        if pp_results:
            pp_eff = {}
            baseline_1t = pp_results.get(1)  # 单线程性能

            if baseline_1t is not None:
                # 2线程相对1线程效率
                if 2 in pp_results:
                    performance_2t = pp_results[2]['avg_performance'].mean()
                    performance_1t = baseline_1t['avg_performance'].mean()
                    pp_eff['2_vs_1'] = performance_2t / performance_1t

                # 6线程相对1线程效率
                if 6 in pp_results:
                    performance_6t = pp_results[6]['avg_performance'].mean()
                    performance_1t = baseline_1t['avg_performance'].mean()
                    pp_eff['6_vs_1'] = performance_6t / performance_1t
                # 6线程相对2线程效率
                if 2 in pp_results and 6 in pp_results:
                    performance_6t = pp_results[6]['avg_performance'].mean()
                    performance_2t = pp_results[2]['avg_performance'].mean()
                    pp_eff['6_vs_2'] = performance_6t / performance_2t

            efficiency['pp'] = pp_eff

        # TG扩展效率
        if tg_results:
            tg_eff = {}
            baseline_1t = tg_results.get(1)  # 单线程性能

            if baseline_1t is not None:
                if 2 in tg_results:
                    performance_2t = tg_results[2]['avg_performance'].mean()
                    performance_1t = baseline_1t['avg_performance'].mean()
                    tg_eff['2_vs_1'] = performance_2t / performance_1t

                if 6 in tg_results:
                    performance_6t = tg_results[6]['avg_performance'].mean()
                    performance_1t = baseline_1t['avg_performance'].mean()
                    tg_eff['6_vs_1'] = performance_6t / performance_1t

                if 2 in tg_results and 6 in tg_results:
                    performance_6t = tg_results[6]['avg_performance'].mean()
                    performance_2t = tg_results[2]['avg_performance'].mean()
                    tg_eff['6_vs_2'] = performance_6t / performance_2t

            efficiency['tg'] = tg_eff

        return efficiency

    def create_performance_plots(self, pp_results, tg_results, efficiency):
        """创建性能对比图"""
        try:
            # 创建2个子图：PP和TG
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            fig.suptitle('Threads Performance Analysis - hunyuan_05b', fontsize=16, fontweight='bold')

            colors = {1: '#1f77b4', 2: '#ff7f0e', 6: '#2ca02c'}
            markers = {1: 'o-', 2: 's-', 6: '^-'}
            labels = {1: '1 Thread', 2: '2 Threads', 6: '6 Threads'}

            # PP性能图 (X: n_prompt, Y: performance)
            if pp_results:
                ax_pp = axes[0]

                for thread in sorted(pp_results.keys()):
                    data = pp_results[thread]
                    if not data.empty:
                        ax_pp.plot(data['n_prompt'], data['avg_performance'],
                                  markers[thread], color=colors[thread],
                                  label=labels[thread], markersize=8, linewidth=2, alpha=0.8)

                        # 添加误差棒
                        ax_pp.errorbar(data['n_prompt'], data['avg_performance'],
                                       yerr=data['std_performance'],
                                       fmt='none', color=colors[thread], alpha=0.5, capsize=3)

                ax_pp.set_title('Prefill Performance vs n_prompt Length')
                ax_pp.set_xlabel('n_prompt (tokens)')
                ax_pp.set_ylabel('Performance (tokens/sec)')
                ax_pp.set_xticks([192, 384, 512])
                ax_pp.legend()
                ax_pp.grid(True, alpha=0.3)

            # TG性能图 (X: n_gen, Y: performance)
            if tg_results:
                ax_tg = axes[1]

                for thread in sorted(tg_results.keys()):
                    data = tg_results[thread]
                    if not data.empty:
                        ax_tg.plot(data['n_gen'], data['avg_performance'],
                                  markers[thread], color=colors[thread],
                                  label=labels[thread], markersize=8, linewidth=2, alpha=0.8)

                        # 添加误差棒
                        ax_tg.errorbar(data['n_gen'], data['avg_performance'],
                                       yerr=data['std_performance'],
                                       fmt='none', color=colors[thread], alpha=0.5, capsize=3)

                ax_tg.set_title('Decode Performance vs n_generate Length')
                ax_tg.set_xlabel('n_generation (tokens)')
                ax_tg.set_ylabel('Performance (tokens/sec)')
                ax_tg.set_xticks([64, 128])
                ax_tg.legend()
                ax_tg.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(f'{self.output_dir}/threads_performance_comparison.png',
                       dpi=300, bbox_inches='tight')
            plt.close()

            # 创建CV稳定性图
            self.create_cv_stability_plot(pp_results, tg_results)

            # 创建扩展效率图
            self.create_efficiency_plot(efficiency)

        except Exception as e:
            print(f"创建性能图失败: {e}")
            plt.close()

    def create_cv_stability_plot(self, pp_results, tg_results):
        """创建CV稳定性对比图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            fig.suptitle('Thread Count Impact on Test Stability (CV Analysis)', fontsize=16, fontweight='bold')

            colors = {1: '#1f77b4', 2: '#ff7f0e', 6: '#2ca02c'}
            markers = {1: 'o-', 2: 's-', 6: '^-'}
            labels = {1: '1 Thread', 2: '2 Threads', 6: '6 Threads'}

            # PP CV稳定性图 (X: n_prompt, Y: CV值)
            if pp_results:
                ax_pp = axes[0]

                for thread in sorted(pp_results.keys()):
                    data = pp_results[thread]
                    if not data.empty:
                        ax_pp.plot(data['n_prompt'], data['avg_cv'],
                                  markers[thread], color=colors[thread],
                                  label=labels[thread], markersize=8, linewidth=2, alpha=0.8)

                ax_pp.set_title('Prefill CV vs n_prompt Length')
                ax_pp.set_xlabel('n_prompt (tokens)')
                ax_pp.set_ylabel('CV Value (%)')
                ax_pp.set_xticks([192, 384, 512])
                ax_pp.legend()
                ax_pp.grid(True, alpha=0.3)

                # 添加稳定性参考线
                ax_pp.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='1% CV Threshold')
                ax_pp.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='0.5% CV Threshold')

            # TG CV稳定性图 (X: n_gen, Y: CV值)
            if tg_results:
                ax_tg = axes[1]

                for thread in sorted(tg_results.keys()):
                    data = tg_results[thread]
                    if not data.empty:
                        ax_tg.plot(data['n_gen'], data['avg_cv'],
                                  markers[thread], color=colors[thread],
                                  label=labels[thread], markersize=8, linewidth=2, alpha=0.8)

                ax_tg.set_title('Decode CV vs n_generation Length')
                ax_tg.set_xlabel('n_generation (tokens)')
                ax_tg.set_ylabel('CV Value (%)')
                ax_tg.set_xticks([64, 128])
                ax_tg.legend()
                ax_tg.grid(True, alpha=0.3)

                # 添加稳定性参考线
                ax_tg.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='1% CV Threshold')
                ax_tg.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='0.5% CV Threshold')

            plt.tight_layout()
            plt.savefig(f'{self.output_dir}/threads_cv_stability.png',
                       dpi=300, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"创建CV稳定性图失败: {e}")
            plt.close()

    def create_efficiency_plot(self, efficiency):
        """创建扩展效率对比图"""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle('Threads Scaling Efficiency Analysis', fontsize=14, fontweight='bold')

            categories = ['2 vs 1', '6 vs 1', '6 vs 2']

            # PP扩展效率
            if 'pp' in efficiency:
                pp_eff = efficiency['pp']
                pp_values = [pp_eff.get(f'{k}_vs_{v}', 0) for k, v in [(2,1), (6,1), (6,2)]]

                bars1 = axes[0].bar(categories, pp_values, color='blue', alpha=0.7)
                axes[0].set_title('Prefill Scaling Efficiency')
                axes[0].set_ylabel('Performance Ratio (Higher is Better)')
                axes[0].set_ylim(0, max(pp_values) * 1.2 if pp_values else 1)
                axes[0].grid(True, axis='y', alpha=0.3)
                axes[0].axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Baseline (1x)')

                # 添加数值标签
                for bar, val in zip(bars1, pp_values):
                    axes[0].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
                               f'{val:.2f}x', ha='center', va='bottom')

            # TG扩展效率
            if 'tg' in efficiency:
                tg_eff = efficiency['tg']
                tg_values = [tg_eff.get(f'{k}_vs_{v}', 0) for k, v in [(2,1), (6,1), (6,2)]]

                bars2 = axes[1].bar(categories, tg_values, color='orange', alpha=0.7)
                axes[1].set_title('Decode Scaling Efficiency')
                axes[1].set_ylabel('Performance Ratio (Higher is Better)')
                axes[1].set_ylim(0, max(tg_values) * 1.2 if tg_values else 1)
                axes[1].grid(True, axis='y', alpha=0.3)
                axes[1].axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Baseline (1x)')

                # 添加数值标签
                for bar, val in zip(bars2, tg_values):
                    axes[1].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
                               f'{val:.2f}x', ha='center', va='bottom')

            plt.tight_layout()
            plt.savefig(f'{self.output_dir}/threads_scaling_efficiency.png',
                       dpi=300, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"创建效率图失败: {e}")
            plt.close()

    def generate_report(self, pp_results, tg_results, efficiency):
        """生成分析报告"""
        report_lines = []
        report_lines.append("# Threads参数影响分析报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        report_lines.append("## 测试设计概览")
        report_lines.append("- **测试模型**: hunyuan_05b (固定模型)")
        report_lines.append("- **线程配置**: 1, 2, 6 线程对比测试")
        report_lines.append("- **测试 Suite**: pn_grid_t1 (1线程), pn_grid_t2 (2线程), pn_grid_t6 (6线程)")
        report_lines.append("- **变量设置**: n_prompt [192,384,512], n_gen [64,128]")
        report_lines.append("- **分析维度**: PP性能(与n_prompt相关), TG性能(与n_gen相关)")
        report_lines.append("")

        # PP性能分析
        if pp_results:
            report_lines.append("## Prefill (PP) 性能分析")

            for thread in sorted(pp_results.keys()):
                data = pp_results[thread]
                report_lines.append(f"### {thread} 线程 PP 性能")

                avg_performance = data['avg_performance'].mean()
                performance_range = f"{data['avg_performance'].min():.1f} - {data['avg_performance'].max():.1f}"
                avg_cv = data['avg_cv'].mean()

                report_lines.append(f"- **平均性能**: {avg_performance:.2f} tokens/sec")
                report_lines.append(f"- **性能范围**: {performance_range} tokens/sec")
                report_lines.append(f"- **平均CV**: {avg_cv:.3f}%")

                # 各n_prompt下的性能
                report_lines.append("- **各n_prompt性能**:")
                for _, row in data.iterrows():
                    report_lines.append(f"  - n_prompt {row['n_prompt']}: {row['avg_performance']:.2f} ± {row['std_performance']:.2f} tokens/sec")
            report_lines.append("")

        # TG性能分析
        if tg_results:
            report_lines.append("## Decode (TG) 性能分析")

            for thread in sorted(tg_results.keys()):
                data = tg_results[thread]
                report_lines.append(f"### {thread} 线程 TG 性能")

                avg_performance = data['avg_performance'].mean()
                performance_range = f"{data['avg_performance'].min():.1f} - {data['avg_performance'].max():.1f}"
                avg_cv = data['avg_cv'].mean()

                report_lines.append(f"- **平均性能**: {avg_performance:.2f} tokens/sec")
                report_lines.append(f"- **性能范围**: {performance_range} tokens/sec")
                report_lines.append(f"- **平均CV**: {avg_cv:.3f}%")

                # 各n_gen下的性能
                report_lines.append("- **各n_gen性能**:")
                for _, row in data.iterrows():
                    report_lines.append(f"  - n_gen {row['n_gen']}: {row['avg_performance']:.2f} ± {row['std_performance']:.2f} tokens/sec")
            report_lines.append("")

        # 扩展效率分析
        report_lines.append("## 线程扩展效率分析")
        if efficiency:
            for result_type in ['pp', 'tg']:
                if result_type in efficiency:
                    report_lines.append(f"### {result_type.upper()} 扩展效率")
                    eff = efficiency[result_type]
                    report_lines.append(f"- **2线程 vs 1线程**: {eff.get('2_vs_1', 'N/A'):.2f}x")
                    report_lines.append(f"- **6线程 vs 1线程**: {eff.get('6_vs_1', 'N/A'):.2f}x")
                    report_lines.append(f"- **6线程 vs 2线程**: {eff.get('6_vs_2', 'N/A'):.2f}x")
            report_lines.append("")

        # CV稳定性分析
        report_lines.append("## CV稳定性分析 (测试可信度)")
        report_lines.append("### 稳定性评价标准")
        report_lines.append("- **优**: CV < 0.5% (高精度测试)")
        report_lines.append("- **良**: CV < 1.0% (标准测试)")
        report_lines.append("- **中**: CV < 2.0% (一般测试)")
        report_lines.append("- **不稳定**: CV ≥ 2.0% (需改进)")

        if pp_results:
            report_lines.append("### PP稳定性分析")
            cv_trend_pp = {}
            for thread in sorted(pp_results.keys()):
                data = pp_results[thread]
                avg_cv = data['avg_cv'].mean()
                cv_status = "优" if avg_cv < 0.5 else ("良" if avg_cv < 1.0 else ("中" if avg_cv < 2.0 else "不稳定"))
                report_lines.append(f"- **{thread}线程**: CV = {avg_cv:.3f}% ({cv_status})")
                cv_trend_pp[thread] = avg_cv

            # CV变化趋势
            if len(cv_trend_pp) >= 2:
                report_lines.append("- **CV变化趋势**:")
                sorted_threads = sorted(cv_trend_pp.keys())
                for i in range(1, len(sorted_threads)):
                    prev_cv = cv_trend_pp[sorted_threads[i-1]]
                    curr_cv = cv_trend_pp[sorted_threads[i]]
                    change = ((curr_cv - prev_cv) / prev_cv * 100) if prev_cv != 0 else 0
                    status = "改善" if change < 0 else ("恶" if change > 5 else "稳定")
                    report_lines.append(f"  - {sorted_threads[i-1]}→{sorted_threads[i]}线程: CV变化{change:+.1f}% ({status})")

        if tg_results:
            report_lines.append("### TG稳定性分析")
            cv_trend_tg = {}
            for thread in sorted(tg_results.keys()):
                data = tg_results[thread]
                avg_cv = data['avg_cv'].mean()
                cv_status = "优" if avg_cv < 0.5 else ("良" if avg_cv < 1.0 else ("中" if avg_cv < 2.0 else "不稳定"))
                report_lines.append(f"- **{thread}线程**: CV = {avg_cv:.3f}% ({cv_status})")
                cv_trend_tg[thread] = avg_cv

            # CV变化趋势
            if len(cv_trend_tg) >= 2:
                report_lines.append("- **CV变化趋势**:")
                sorted_threads = sorted(cv_trend_tg.keys())
                for i in range(1, len(sorted_threads)):
                    prev_cv = cv_trend_tg[sorted_threads[i-1]]
                    curr_cv = cv_trend_tg[sorted_threads[i]]
                    change = ((curr_cv - prev_cv) / prev_cv * 100) if prev_cv != 0 else 0
                    status = "改善" if change < 0 else ("恶" if change > 5 else "稳定")
                    report_lines.append(f"  - {sorted_threads[i-1]}→{sorted_threads[i]}线程: CV变化{change:+.1f}% ({status})")

        report_lines.append("")

        # 优化建议
        report_lines.append("## 优化建议")

        # 性能最优选择
        pp_best_thread = None
        tg_best_thread = None

        if pp_results and efficiency.get('pp'):
            best_eff = max(efficiency['pp'].items(), key=lambda x: x[1])
            pp_best_thread = best_eff[0].split('_vs_')[0]

        if tg_results and efficiency.get('tg'):
            best_eff = max(efficiency['tg'].items(), key=lambda x: x[1])
            tg_best_thread = best_eff[0].split('_vs_')[0]

        # 稳定性最优选择
        pp_stable_thread = None
        tg_stable_thread = None

        if pp_results:
            cv_pp = {thread: data['avg_cv'].mean() for thread, data in pp_results.items()}
            pp_stable_thread = min(cv_pp.keys(), key=lambda x: cv_pp[x])

        if tg_results:
            cv_tg = {thread: data['avg_cv'].mean() for thread, data in tg_results.items()}
            tg_stable_thread = min(cv_tg.keys(), key=lambda x: cv_tg[x])

        # 综合建议
        if pp_best_thread and tg_best_thread:
            if pp_best_thread == tg_best_thread:
                report_lines.append(f"### 性能导向推荐")
                report_lines.append(f"1. **最优性能线程数**: {pp_best_thread}")
                report_lines.append(f"2. **PP性能提升**: {efficiency['pp'][f'{pp_best_thread}_vs_1']:.2f}x")
                report_lines.append(f"3. **TG性能提升**: {efficiency['tg'][f'{pp_best_thread}_vs_1']:.2f}x")
            else:
                report_lines.append("### 性能导向推荐")
                report_lines.append(f"1. **PP最优**: {pp_best_thread} 线程")
                report_lines.append(f"2. **TG最优**: {tg_best_thread} 线程")
                report_lines.append(f"3. **建议**: PP/TG需求不同时可差异化配置")

        if pp_stable_thread and tg_stable_thread:
            if pp_stable_thread == tg_stable_thread:
                report_lines.append(f"### 稳定性导向推荐")
                report_lines.append(f"1. **最稳定线程数**: {pp_stable_thread}")
                if pp_stable_thread != pp_best_thread:
                    report_lines.append(f"2. **注意**: 稳定性最优配置({pp_stable_thread})与性能最优({pp_best_thread})不同")
                    report_lines.append(f"3. **权衡**: 需在性能和稳定性间平衡")
            else:
                report_lines.append(f"### 稳定性导向推荐")
                report_lines.append(f"1. **PP最稳定**: {pp_stable_thread} 线程")
                report_lines.append(f"2. **TG最稳定**: {tg_stable_thread} 线程")

        report_lines.append("")
        report_lines.append("## 可视化分析")
        report_lines.append("![性能对比分析](threads_performance_comparison.png)")
        report_lines.append("")
        report_lines.append("![CV稳定性分析](threads_cv_stability.png)")
        report_lines.append("")
        report_lines.append("![扩展效率分析](threads_scaling_efficiency.png)")

        # 保存报告
        report_content = "\n".join(report_lines)
        with open(f'{self.output_dir}/threads_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_content

    def run_analysis(self):
        """运行完整分析"""
        print("开始threads参数分析...")

        # 获取数据
        df = self.get_threads_data()
        if df.empty:
            print("未找到threads测试数据")
            return

        print(f"找到 {len(df)} 条threads测试数据")

        # 解析参数
        df = self.extract_parameters(df)
        print(f"数据解析完成，包含线程数: {sorted(df['threads'].unique())}")

        # PP性能分析
        print("进行PP性能分析...")
        pp_results = self.analyze_pp_performance(df)

        # TG性能分析
        print("进行TG性能分析...")
        tg_results = self.analyze_tg_performance(df)

        # 计算扩展效率
        print("计算扩展效率...")
        efficiency = self.calculate_scaling_efficiency(pp_results, tg_results)

        # 生成图表
        print("生成图表...")
        self.create_performance_plots(pp_results, tg_results, efficiency)

        # 导出数据
        df.to_csv(f'{self.output_dir}/threads_data.csv', index=False)

        # 生成报告
        print("生成报告...")
        self.generate_report(pp_results, tg_results, efficiency)

        print("Threads分析完成")
        print(f"文件位置: {self.output_dir}")

if __name__ == "__main__":
    analyzer = ThreadsAnalyzer()
    analyzer.run_analysis()