#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型基准测试3D散点图绘制工具

XY坐标：n_gen和n_prompt，Z坐标：PP/TG性能
三个模型同图显示，避免与1目录配色重复
"""

import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import pandas as pd
from pathlib import Path
import json

# 设置安全的中英文支持字体
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

def get_database_connection():
    """获取数据库连接"""
    script_dir = Path(__file__).parent
    db_path = script_dir / ".." / "data" / "benchmark_results.db"
    return sqlite3.connect(str(db_path))

def extract_multimodel_data(result_type):
    """
    从数据库提取task4多模型性能数据
    返回DataFrame包含: model_name, n_prompt, n_gen, performance, std_value
    """
    conn = get_database_connection()

    if result_type == 'pp':
        # PP: result_parameter是n_prompt
        query = f"""
        SELECT
            s.model_name,
            cd.base_parameters,
            br.result_parameter as n_prompt,
            br.mean_value as performance,
            br.std_value as std_value
        FROM benchmark_results br
        JOIN case_definitions cd ON br.case_id = cd.id
        JOIN suites s ON cd.suite_id = s.id
        WHERE br.result_type = 'pp'
        AND s.task_id = 4
        AND s.model_name IN ('qwen2_5_0_5b', 'smolvlm2_256m', 'llama_3_2_1b')
        ORDER BY s.model_name, CAST(br.result_parameter as INTEGER)
        """
    else:
        # TG: result_parameter是n_gen
        query = f"""
        SELECT
            s.model_name,
            cd.base_parameters,
            br.result_parameter as n_gen,
            br.mean_value as performance,
            br.std_value as std_value
        FROM benchmark_results br
        JOIN case_definitions cd ON br.case_id = cd.id
        JOIN suites s ON cd.suite_id = s.id
        WHERE br.result_type = 'tg'
        AND s.task_id = 4
        AND s.model_name IN ('qwen2_5_0_5b', 'smolvlm2_256m', 'llama_3_2_1b')
        ORDER BY s.model_name, CAST(br.result_parameter as INTEGER)
        """

    try:
        df = pd.read_sql_query(query, conn)

        # 根据数据类型提取相应的参数
        if result_type == 'pp':
            # PP: 从base_parameters提取n_gen, result_parameter是n_prompt
            def extract_n_gen(params_str):
                try:
                    params = json.loads(params_str)
                    return params.get('n_gen')
                except:
                    return None

            df['n_gen'] = df['base_parameters'].apply(extract_n_gen)
            df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')
            df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        else:
            # TG: 从base_parameters提取n_prompt, result_parameter是n_gen
            def extract_n_prompt(params_str):
                try:
                    params = json.loads(params_str)
                    return params.get('n_prompt')
                except:
                    return None

            df['n_prompt'] = df['base_parameters'].apply(extract_n_prompt)
            df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
            df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')

        # 转换其他列为数值
        df['performance'] = pd.to_numeric(df['performance'], errors='coerce')
        df['std_value'] = pd.to_numeric(df['std_value'], errors='coerce')

        # 删除无效数据
        df = df.dropna(subset=['n_gen', 'n_prompt', 'performance'])

        print(f"成功提取{result_type.upper()}性能数据: {len(df)} 条记录")
        print(f"模型数量: {df['model_name'].nunique()}")
        print(f"n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        print(f"{result_type.upper()}性能范围: {df['performance'].min():.2f} - {df['performance'].max():.2f} tokens/sec")

        return df

    except Exception as e:
        print(f"数据提取失败: {e}")
        return None
    finally:
        conn.close()

def plot_performance_3d_scatter(df, result_type, output_dir):
    """
    绘制性能立体散点图 - n_gen和n_prompt为XY，性能为Z

    Args:
        df: 性能数据DataFrame
        result_type: 性能类型 ('pp' 或 'tg')
        output_dir: 输出目录
    """
    if df is None or df.empty:
        print("没有数据可供绘制")
        return

    # 创建图形
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')

    # 获取模型列表和颜色配置（避免与1目录重复）
    models = df['model_name'].unique()
    # 1目录配色：hunyuan_05b: '#1f77b4', qwen3_06b: '#ff7f0e'
    # 这里使用不同的配色
    colors = {
        'qwen2_5_0_5b': 'mediumseagreen',   # 海绿色
        'smolvlm2_256m': 'mediumpurple',     # 中紫色
        'llama_3_2_1b': 'tomato'            # 番茄红
    }

    performance_name = 'PP Performance' if result_type == 'pp' else 'TG Performance'

    # 为每个模型绘制散点
    for model in models:
        model_data = df[df['model_name'] == model]
        model_color = colors.get(model, 'gray')

        # 绘制散点，X: n_gen, Y: n_prompt, Z: performance
        scatter = ax.scatter(
            model_data['n_gen'],              # X轴: n_gen
            model_data['n_prompt'],           # Y轴: n_prompt
            model_data['performance'],       # Z轴: 性能值
            c=model_color,                    # 颜色
            s=50 + model_data['std_value']*10, # 点大小基于标准差
            alpha=0.8,
            label=model,
            edgecolors='black',
            linewidth=0.5
        )

    # 设置轴标签和标题
    ax.set_xlabel('Generation Length (n_gen)', fontsize=12)
    ax.set_ylabel('Prompt Length (n_prompt)', fontsize=12)
    ax.set_zlabel(f'{performance_name} (tokens/sec)', fontsize=12)
    ax.set_title(f'{performance_name} 3D Analysis - n_gen vs n_prompt', fontsize=14, pad=20)

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
        (30, 60, "elevated"),
        (10, 30, "low_angle"),
        (0, 0, "top_view"),
        (90, 0, "front_view")
    ]

    for elev, azim, view_name in view_angles:
        ax.view_init(elev=elev, azim=azim)
        filename = f"{result_type}_3d_scatter_{view_name}.png"
        filepath = output_path / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Saved image: {filepath}")

def main():
    """Main function"""
    print("Starting Multi-Model 3D Scatter Plot Generation for Task4...")

    # 确定目录路径
    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "analysis_output" / "multimodel_3d"

    # 处理PP数据
    print("\n1. Processing PP performance data from database...")
    pp_df = extract_multimodel_data('pp')

    if pp_df is not None:
        print("\nPP Data Overview:")
        print("=" * 50)
        print(pp_df[['model_name', 'n_gen', 'n_prompt', 'performance']].head(10))
        print("=" * 50)

        print("\n2. Plotting PP 3D scatter plot...")
        plot_performance_3d_scatter(pp_df, 'pp', output_dir)

    # 处理TG数据
    print("\n3. Processing TG performance data from database...")
    tg_df = extract_multimodel_data('tg')

    if tg_df is not None:
        print("\nTG Data Overview:")
        print("=" * 50)
        print(tg_df[['model_name', 'n_gen', 'n_prompt', 'performance']].head(10))
        print("=" * 50)

        print("\n4. Plotting TG 3D scatter plot...")
        plot_performance_3d_scatter(tg_df, 'tg', output_dir)

    print("\n✓ Multi-Model 3D Scatter Plot Generation Complete!")
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    main()