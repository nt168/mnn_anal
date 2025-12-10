#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型基准测试3D散点图动画生成工具（单线程版）

为PP和TG性能3D散点图生成左右旋转的慢速动画
确保质量和稳定性，支持进度显示
"""

import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import pandas as pd
from pathlib import Path
import json
import time
import sys
from tqdm import tqdm

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

        return df

    except Exception as e:
        print(f"数据提取失败: {e}")
        return None
    finally:
        conn.close()

def create_animation_frame(args):
    """
    创建单个动画帧

    Args:
        args: (df, result_type, angle, frame_num, output_dir, colors, performance_name, config)

    Returns:
        frame_info: 帧信息
    """
    df, result_type, angle, frame_num, output_dir, colors, performance_name, config = args

    # 创建临时图形 - 严格固定尺寸，确保所有帧尺寸一致
    figsize = (12, 9)  # 固定图形尺寸
    fig = plt.figure(figsize=figsize, dpi=config['frame_dpi'])
    ax = fig.add_subplot(111, projection='3d')

    # 严格设置图形参数，确保一致性
    fig.set_size_inches(figsize[0], figsize[1])
    fig.set_dpi(config['frame_dpi'])
    ax.set_position([0.1, 0.1, 0.8, 0.8])  # 固定axes位置

    models = df['model_name'].unique()

    # 绘制散点
    for model in models:
        model_data = df[df['model_name'] == model]
        model_color = colors.get(model, 'gray')

        ax.scatter(
            model_data['n_gen'],
            model_data['n_prompt'],
            model_data['performance'],
            c=model_color,
            s=50 + model_data['std_value']*10,
            alpha=0.8,
            label=model,
            edgecolors='black',
            linewidth=0.5
        )

    # 设置轴标签
    ax.set_xlabel('Generation Length (n_gen)', fontsize=10)
    ax.set_ylabel('Prompt Length (n_prompt)', fontsize=10)
    ax.set_zlabel(f'{performance_name} (tokens/sec)', fontsize=10)
    ax.set_title(f'{performance_name} 3D Analysis - Frame {frame_num}', fontsize=12)

    # 设置图例
    ax.legend(loc='upper left', fontsize=8)

    # 设置视角
    ax.view_init(elev=20, azim=angle)

    # 设置网格
    ax.grid(True, alpha=0.3)

    # 保存单帧
    frame_filename = f"{result_type}_frame_{frame_num:03d}.png"
    frame_filepath = Path(output_dir) / f"{result_type}_frames" / frame_filename

    # 确保帧目录存在
    frame_dir = Path(output_dir) / f"{result_type}_frames"
    frame_dir.mkdir(exist_ok=True, parents=True)

    # 使用固定布局，不使用tight_layout避免尺寸变化
    # 仅调用subplots_adjust来确保边距一致
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

    # 保存时不使用bbox_inches，确保尺寸完全一致
    plt.savefig(frame_filepath, dpi=config['frame_dpi'], bbox_inches=None,
                pad_inches=0, format='png')
    plt.close()

    return frame_num, frame_filepath

# 可配置参数 - 用户直接修改这里调整性能和质量
# 单线程模式，保证质量和稳定性
CONFIG = {
    'total_frames': 90,        # 总帧数(建议90-180, 越少越快但动画越短)
    'angle_step': 2,           # 每帧旋转角度(建议1-4度, 角度越小旋转越平滑)
    'frame_dpi': 120,           # 帧图片DPI(80-300, 越低越快但质量越差)
    'gif_duration': 0.1        # GIF每帧持续时间(秒, 0.05-0.2, 越小动画越快)
}

def create_3d_animation(df, result_type, output_dir, config=None):
    """
    创建3D散点图旋转动画（单线程模式）

    Args:
        df: 性能数据DataFrame
        result_type: 性能类型 ('pp' 或 'tg')
        output_dir: 输出目录
        config: 配置参数字典，可选
    """
    # 使用传入配置或默认配置
    cfg = CONFIG.copy()
    if config:
        cfg.update(config)

    if df is None or df.empty:
        print("没有数据可供绘制动画")
        return

    print(f"🎬 开始创建{result_type.upper()} 3D动画...")
    print(f"⚙️  配置参数: 帧数={cfg['total_frames']}, DPI={cfg['frame_dpi']}")

    # 颜色配置
    colors = {
        'qwen2_5_0_5b': 'mediumseagreen',
        'smolvlm2_256m': 'mediumpurple',
        'llama_3_2_1b': 'tomato'
    }

    performance_name = 'PP Performance' if result_type == 'pp' else 'TG Performance'

    # 动画参数
    total_frames = cfg['total_frames']
    angles = [i * cfg['angle_step'] for i in range(total_frames)]  # 0到360度

    # 准备帧生成参数
    frame_args = []
    for i, angle in enumerate(angles):
        frame_args.append((df, result_type, angle, i, output_dir, colors, performance_name, cfg))

    print(f"📊 总共需要生成 {total_frames} 帧")
    print(f"🔄 使用单线程顺序生成确保质量...")
    print(f"⚙️  配置参数: 帧数={total_frames}, DPI={cfg['frame_dpi']}")

    # 单线程顺序生成所有帧
    start_time = time.time()

    with tqdm(total=total_frames, desc=f"🎨 {result_type.upper()} 帧生成进度", unit="frame") as pbar:
        for args in frame_args:
            frame_num, frame_path = create_animation_frame(args)
            pbar.update(1)

    generation_time = time.time() - start_time
    print(f"✅ {result_type.upper()} 帧生成完成, 用时: {generation_time:.1f}秒")

    # 创建GIF动画 - 直接使用imageio
    print(f"🎬 合成GIF动画中...")

    frame_dir = Path(output_dir) / f"{result_type}_frames"
    gif_filename = f"{result_type}_3d_animation.gif"
    gif_filepath = Path(output_dir) / gif_filename

    import imageio.v2 as imageio
    images = []

    print(f"📖 读取{total_frames}帧图像...")
    for frame_num in tqdm(range(total_frames), desc="🎞️ GIF合成进度"):
        frame_filename = f"{result_type}_frame_{frame_num:03d}.png"
        frame_path = frame_dir / frame_filename
        if frame_path.exists():
            img = imageio.imread(str(frame_path))
            images.append(img)

    # 保存GIF
    imageio.mimsave(str(gif_filepath), images, duration=cfg['gif_duration'], loop=0)
    print(f"✅ GIF动画已保存: {gif_filepath}")

    # 清理临时帧文件
    try:
        import shutil
        frame_dir = Path(output_dir) / f"{result_type}_frames"
        if frame_dir.exists():
            shutil.rmtree(frame_dir)
            print(f"🗑️  已清理临时帧文件")
    except:
        pass

def main():
    """Main函数"""
    print("🚀 多模型3D散点图动画生成器（并发优化版）")
    print("=" * 60)

    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "analysis_output" / "multimodel_3d_animation"

    print(f"📁 输出目录: {output_dir}")

    tasks = [
        ('pp', 'PP性能'),
        ('tg', 'TG性能')
    ]

    for task_type, task_name in tasks:
        print(f"\n📊 开始处理{task_name}数据...")

        # 提取数据
        df = extract_multimodel_data(task_type)
        if df is not None:
            print(f"✅ 数据提取成功: {len(df)} 条记录")
            print(f"📈 n_gen: {df['n_gen'].min()}-{df['n_gen'].max()}")
            print(f"📈 n_prompt: {df['n_prompt'].min()}-{df['n_prompt'].max()}")
            print(f"📈 性能: {df['performance'].min():.2f}-{df['performance'].max():.2f} tokens/sec")

            # 创建动画 - 使用默认配置
            create_3d_animation(df, task_type, output_dir)
        else:
            print(f"❌ {task_name}数据提取失败")

    print(f"\n🎉 动画生成完成！")
    print(f"💾 保存位置: {output_dir}")
    print(f"📁 文件包括:")
    print(f"   • pp_3d_animation.gif")
    print(f"   • tg_3d_animation.gif")

if __name__ == "__main__":
    # 检查依赖
    try:
        from tqdm import tqdm
    except ImportError:
        print("正在安装进度条库...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        from tqdm import tqdm

    main()