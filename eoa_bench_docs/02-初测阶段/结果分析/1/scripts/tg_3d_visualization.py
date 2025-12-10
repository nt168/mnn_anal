#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG性能立体散点图绘制工具

绘制Token Generation(TG)性能相对于n_gen和n_prompt的二元立体散点图
"""

import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import pandas as pd
from pathlib import Path
import sys

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

def get_database_connection():
    """获取数据库连接"""
    script_dir = Path(__file__).parent
    db_path = script_dir / ".." / "data" / "benchmark_results.db"
    return sqlite3.connect(str(db_path))

def extract_tg_data():
    """
    从数据库提取TG性能数据
    返回DataFrame包含: model_name, n_prompt, n_gen, tg_performance, std_value
    """
    conn = get_database_connection()

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

    try:
        df = pd.read_sql_query(query, conn)
        # 转换字符串为数值
        df['n_prompt'] = df['n_prompt'].astype(int)
        df['n_gen'] = df['n_gen'].astype(int)
        df['tg_performance'] = df['tg_performance'].astype(float)
        df['std_value'] = df['std_value'].astype(float)

        print(f"成功提取TG性能数据: {len(df)} 条记录")
        print(f"模型数量: {df['model_name'].nunique()}")
        print(f"n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        print(f"TG性能范围: {df['tg_performance'].min():.2f} - {df['tg_performance'].max():.2f} tokens/sec")

        return df

    except Exception as e:
        print(f"数据提取失败: {e}")
        return None
    finally:
        conn.close()

def plot_tg_3d_scatter(df, output_dir):
    """
    绘制TG性能立体散点图

    Args:
        df: TG性能数据DataFrame
        output_dir: 输出目录
    """
    if df is None or df.empty:
        print("没有数据可供绘制")
        return

    # 创建图形
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    # 获取模型列表和颜色配置
    models = df['model_name'].unique()
    colors = {'hunyuan_05b': '#1f77b4', 'qwen3_06b': '#ff7f0e'}

    # 为每个模型绘制散点
    for model in models:
        model_data = df[df['model_name'] == model]
        model_color = colors.get(model, plt.cm.Set1(np.linspace(0, 1, len(models))[0]))

        # 绘制散点，点的大小基于标准差（不确定性）
        scatter = ax.scatter(
            model_data['n_prompt'],    # X轴: n_prompt
            model_data['n_gen'],       # Y轴: n_gen
            model_data['tg_performance'], # Z轴: TG性能
            c=[model_color],           # 颜色
            s=50 + model_data['std_value']*10, # 点大小基于标准差
            alpha=0.7,
            label=model,
            edgecolors='black',
            linewidth=0.5
        )

    # 设置轴标签和标题
    ax.set_xlabel('Prompt Length (n_prompt)', fontsize=12)
    ax.set_ylabel('Generation Length (n_gen)', fontsize=12)
    ax.set_zlabel('TG Performance (tokens/sec)', fontsize=12)
    ax.set_title('Token Generation Performance - n_prompt vs n_gen 3D Analysis', fontsize=14, pad=20)

    # 设置图例
    ax.legend(loc='upper left', fontsize=10)

    # 调整视角
    ax.view_init(elev=20, azim=45)

    # 添加网格
    ax.grid(True, alpha=0.3)

    # 保存图片
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 保存多个视角
    view_angles = [
        (20, 45, "default"),
        (30, 60, "tilted_1"),
        (10, 30, "tilted_2"),
        (0, 0, "top_view"),
        (90, 0, "front_view")
    ]

    for elev, azim, view_name in view_angles:
        ax.view_init(elev=elev, azim=azim)
        filename = f"tg_3d_scatter_{view_name}.png"
        filepath = output_path / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Saved image: {filepath}")

def main():
    """Main function"""
    print("Starting TG Performance 3D Scatter Plot Generation...")

    # 确定目录路径
    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "analysis_output" / "tg_3d_visualization"

    # 提取数据
    print("1. Extracting TG performance data from database...")
    df = extract_tg_data()

    if df is not None:
        # 显示数据概览
        print("\nData Overview:")
        print("=" * 50)
        print(df.head(10))
        print("=" * 50)

        # 绘制图形
        print("\n2. Plotting 3D scatter plot...")
        plot_tg_3d_scatter(df, output_dir)

        print("\n✓ TG Performance 3D Scatter Plot Generation Complete!")
        print(f"Output directory: {output_dir}")
    else:
        print("✗ Data extraction failed, unable to generate plots")

if __name__ == "__main__":
    main()