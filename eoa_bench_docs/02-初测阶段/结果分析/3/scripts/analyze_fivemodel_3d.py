#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五模型基准测试3D散点图绘制工具

XY坐标：n_gen和n_prompt，Z坐标：PP/TG性能
五个模型同图显示：qwen2_5_0_5b, smolvlm2_256m, llama_3_2_1b, hunyuan_05b, qwen3_06b
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

def extract_fivemodel_data(result_type):
    """
    从数据库提取五模型性能数据
    返回DataFrame包含: model_name, n_prompt, n_gen, performance, std_value
    包含来自不同数据库的模型：
    - 目录3数据库: task4模型 qwen2_5_0_5b, smolvlm2_256m, llama_3_2_1b
    - 目录1数据库: hunyuan_05b, qwen3_06b
    """
    # 连接当前目录(目录3)的数据库获取task4数据
    conn3 = get_database_connection()

    # 连接目录1数据库获取task1数据
    db1_path = Path(__file__).resolve().parent.parent.parent / "1" / "data" / "benchmark_results.db"

    if not db1_path.exists():
        print(f"错误：找不到目录1数据库: {db1_path}")
        return None

    conn1 = sqlite3.connect(str(db1_path))

    # 查询各自的数据库
    try:
        all_data = []

        # 从目录3数据库获取task4数据
        query3 = """
        SELECT
            s.model_name,
            cd.base_parameters,
            br.mean_value as performance,
            br.std_value as std_value
        FROM benchmark_results br
        JOIN case_definitions cd ON br.case_id = cd.id
        JOIN suites s ON cd.suite_id = s.id
        WHERE br.result_type = ?
        AND s.task_id = 4
        AND s.model_name IN ('qwen2_5_0_5b', 'smolvlm2_256m', 'llama_3_2_1b')
        ORDER BY s.model_name, CAST(br.result_parameter as INTEGER)
        """
        df3 = pd.read_sql_query(query3, conn3, params=(result_type,))
        all_data.append(df3)

        # 从目录1数据库获取task1数据（只保留与task4相同的n_gen值）
        query1 = """
        SELECT
            s.model_name,
            cd.base_parameters,
            br.mean_value as performance,
            br.std_value as std_value
        FROM benchmark_results br
        JOIN case_definitions cd ON br.case_id = cd.id
        JOIN suites s ON cd.suite_id = s.id
        WHERE br.result_type = ?
        AND s.model_name IN ('hunyuan_05b', 'qwen3_06b')
        AND json_extract(cd.base_parameters, '$.n_gen') IN (32, 64, 96, 128)
        ORDER BY s.model_name, CAST(br.result_parameter as INTEGER)
        """
        df1 = pd.read_sql_query(query1, conn1, params=(result_type,))
        all_data.append(df1)

        # 合并两个数据源
        df = pd.concat(all_data, ignore_index=True)

        # 所有参数都从base_parameters提取
        def extract_from_base(params_str, param_name):
            try:
                params = json.loads(params_str)
                return params.get(param_name)
            except:
                return None

        # 从base_parameters提取n_prompt和n_gen
        df['n_prompt'] = df['base_parameters'].apply(lambda x: extract_from_base(x, 'n_prompt'))
        df['n_gen'] = df['base_parameters'].apply(lambda x: extract_from_base(x, 'n_gen'))

        # 转换为数值
        df['n_prompt'] = pd.to_numeric(df['n_prompt'], errors='coerce')
        df['n_gen'] = pd.to_numeric(df['n_gen'], errors='coerce')

        # 转换其他列为数值
        df['performance'] = pd.to_numeric(df['performance'], errors='coerce')
        df['std_value'] = pd.to_numeric(df['std_value'], errors='coerce')

        # 删除无效数据
        df = df.dropna(subset=['n_gen', 'n_prompt', 'performance'])

        print(f"成功提取{result_type.upper()}五模型性能数据: {len(df)} 条记录")
        print(f"模型数量: {df['model_name'].nunique()}")
        print(f"模型列表: {sorted(df['model_name'].unique())}")
        print(f"n_prompt范围: {df['n_prompt'].min()} - {df['n_prompt'].max()}")
        print(f"n_gen范围: {df['n_gen'].min()} - {df['n_gen'].max()}")
        print(f"{result_type.upper()}性能范围: {df['performance'].min():.2f} - {df['performance'].max():.2f} tokens/sec")

        return df

    except Exception as e:
        print(f"数据提取失败: {e}")
        return None
    finally:
        conn3.close()
        conn1.close()

def plot_performance_3d_scatter(df, result_type, output_dir):
    """
    绘制五模型性能立体散点图 - n_gen和n_prompt为XY，性能为Z

    Args:
        df: 性能数据DataFrame
        result_type: 性能类型 ('pp' 或 'tg')
        output_dir: 输出目录
    """
    if df is None or df.empty:
        print("没有数据可供绘制")
        return

    # 创建图形
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection='3d')

    # 获取模型列表和颜色配置（五个模型的不同颜色）
    models = df['model_name'].unique()
    # 五模型配色，避免与现有配色重复
    colors = {
        'qwen2_5_0_5b': 'mediumseagreen',   # 海绿色
        'smolvlm2_256m': 'mediumpurple',     # 中紫色
        'llama_3_2_1b': 'crimson',           # 深红色（与橙色更好分离）
        'hunyuan_05b': 'dodgerblue',        # 道奇蓝
        'qwen3_06b': 'darkorange'           # 深橙色
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
            s=60 + model_data['std_value']*8, # 点大小基于标准差，稍大以适应5个模型
            alpha=0.7,
            label=model,
            edgecolors='black',
            linewidth=0.5
        )

    # 设置轴标签和标题
    ax.set_xlabel('Generation Length (n_gen)', fontsize=12)
    ax.set_ylabel('Prompt Length (n_prompt)', fontsize=12)
    ax.set_zlabel(f'{performance_name} (tokens/sec)', fontsize=12)
    ax.set_title(f'{performance_name} 3D Analysis - Five Models (n_gen vs n_prompt)', fontsize=14, pad=20)

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
        filename = f"fivemodel_{result_type}_3d_scatter_{view_name}.png"
        filepath = output_path / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"保存图像: {filepath}")

def main():
    """Main function"""
    print("开始五模型3D散点图绘制分析...")
    print("包含模型: qwen2_5_0_5b, smolvlm2_256m, llama_3_2_1b, hunyuan_05b, qwen3_06b")

    # 确定目录路径
    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "analysis_output" / "fivemodel_3d"

    # 处理PP数据
    print("\n1. 处理PP性能数据...")
    pp_df = extract_fivemodel_data('pp')

    if pp_df is not None:
        print("\nPP数据概览:")
        print("=" * 50)
        print(pp_df[['model_name', 'n_gen', 'n_prompt', 'performance']].head(10))
        print("=" * 50)

        print("\n2. 绘制PP 3D散点图...")
        plot_performance_3d_scatter(pp_df, 'pp', output_dir)

    # 处理TG数据
    print("\n3. 处理TG性能数据...")
    tg_df = extract_fivemodel_data('tg')

    if tg_df is not None:
        print("\nTG数据概览:")
        print("=" * 50)
        print(tg_df[['model_name', 'n_gen', 'n_prompt', 'performance']].head(10))
        print("=" * 50)

        print("\n4. 绘制TG 3D散点图...")
        plot_performance_3d_scatter(tg_df, 'tg', output_dir)

    print("\n✓ 五模型3D散点图绘制完成!")
    print(f"输出目录: {output_dir}")

if __name__ == "__main__":
    main()