#!/usr/bin/env python3
import numpy as np
from scipy import stats
import pandas as pd

# 读取数据
data = pd.read_csv('anova_data.csv')

# 分离完整数据 vs 被截断的数据（512 tokens）
complete_data = data[data['Tokens'] < 512]
truncated_data = data[data['Tokens'] == 512]

print("=== 数据基本情况 ===")
print(f"总样本数: {len(data)}")
print(f"完整数据样本数: {len(complete_data)}")
print(f"可能被截断的样本数: {len(truncated_data)}")
print(f"截断数据占比: {len(truncated_data)/len(data)*100:.1f}%")

print("\n=== 完整数据的描述性统计 ===")
print(complete_data.groupby(['Model', 'Environment'])['DecodeSpeed'].describe())

# 双因子方差分析（仅使用完整数据）
print("\n=== 双因子方差分析（完整数据）=== ")

# 重新组织数据为矩阵形式
qwen_physical = complete_data[(complete_data['Model'] == 'Qwen') & (complete_data['Environment'] == 'Physical')]['DecodeSpeed']
qwen_simulated = complete_data[(complete_data['Model'] == 'Qwen') & (complete_data['Environment'] == 'Simulated')]['DecodeSpeed']
hunyuan_physical = complete_data[(complete_data['Model'] == 'Hunyuan') & (complete_data['Environment'] == 'Physical')]['DecodeSpeed']
hunyuan_simulated = complete_data[(complete_data['Model'] == 'Hunyuan') & (complete_data['Environment'] == 'Simulated')]['DecodeSpeed']

# 计算各组均值
overall_mean = complete_data['DecodeSpeed'].mean()
model_means = complete_data.groupby('Model')['DecodeSpeed'].mean()
env_means = complete_data.groupby('Environment')['DecodeSpeed'].mean()

print(f"总体均值: {overall_mean:.3f}")
print(f"模型均值: Qwen={model_means['Qwen']:.3f}, Hunyuan={model_means['Hunyuan']:.3f}")
print(f"环境均值: Physical={env_means['Physical']:.3f}, Simulated={env_means['Simulated']:.3f}")

# 方差分析计算
n_total = len(complete_data)
n_groups = 4  # 2模型 × 2环境
k_model = 2
k_env = 2

# 计算平方和
total_ss = ((complete_data['DecodeSpeed'] - overall_mean) ** 2).sum()

# 模型主效应
model_ss = len(complete_data) * ((model_means - overall_mean) ** 2).sum()

# 环境主效应
env_ss = len(complete_data) * ((env_means - overall_mean) ** 2).sum()

# 交互效应 - 需要计算每个 cell 的均值
cell_means = complete_data.groupby(['Model', 'Environment'])['DecodeSpeed'].mean()

# 计算每个单元格的样本数
cell_counts = complete_data.groupby(['Model', 'Environment']).size()

interaction_ss = 0
for model, env in [('Qwen', 'Physical'), ('Qwen', 'Simulated'), ('Hunyuan', 'Physical'), ('Hunyuan', 'Simulated')]:
    predicted = model_means[model] + env_means[env] - overall_mean
    actual = cell_means[(model, env)]
    cell_n = cell_counts[(model, env)]
    interaction_ss += cell_n * (actual - predicted) ** 2

# 残差（误差）
error_ss = total_ss - model_ss - env_ss - interaction_ss

# 自由度
df_total = n_total - 1
df_model = k_model - 1
df_env = k_env - 1
df_interaction = (k_model - 1) * (k_env - 1)
df_error = df_total - df_model - df_env - df_interaction

# 均方
ms_model = model_ss / df_model
ms_env = env_ss / df_env
ms_interaction = interaction_ss / df_interaction
ms_error = error_ss / df_error

# F统计量
f_model = ms_model / ms_error
f_env = ms_env / ms_error
f_interaction = ms_interaction / ms_error

# p值
p_model = 1 - stats.f.cdf(f_model, df_model, df_error)
p_env = 1 - stats.f.cdf(f_env, df_env, df_error)
p_interaction = 1 - stats.f.cdf(f_interaction, df_interaction, df_error)

print(f"\n=== ANOVA 结果表格 ===")
print(f"{'效应':<12} {'平方和':<10} {'自由度':<8} {'均方':<10} {'F值':<8} {'p值':<8}")
print("-" * 60)
print(f"{'模型':<12} {model_ss:<10.3f} {df_model:<8} {ms_model:<10.3f} {f_model:<8.3f} {p_model:<8.3f}")
print(f"{'环境':<12} {env_ss:<10.3f} {df_env:<8} {ms_env:<10.3f} {f_env:<8.3f} {p_env:<8.3f}")
print(f"{'交互':<12} {interaction_ss:<10.3f} {df_interaction:<8} {ms_interaction:<10.3f} {f_interaction:<8.3f} {p_interaction:<8.3f}")
print(f"{'误差':<12} {error_ss:<10.3f} {df_error:<8} {ms_error:<10.3f} {'-':<8} {'-':<8}")
print(f"{'总计':<12} {total_ss:<10.3f} {df_total:<8} {'-':<10} {'-':<8} {'-':<8}")

# 效应量计算
eta2_model = model_ss / total_ss
eta2_env = env_ss / total_ss
eta2_interaction = interaction_ss / total_ss

print(f"\n=== 效应量 (η²) ===")
print(f"模型主效应: {eta2_model:.3f}")
print(f"环境主效应: {eta2_env:.3f}")
print(f"交互效应: {eta2_interaction:.3f}")

# 正态性检验
print(f"\n=== 正态性检验 (Shapiro-Wilk) ===")
for group_name, group_data in [
    ('Qwen_Physical', qwen_physical),
    ('Qwen_Simulated', qwen_simulated),
    ('Hunyuan_Physical', hunyuan_physical),
    ('Hunyuan_Simulated', hunyuan_simulated)
]:
    if len(group_data) >= 3:  # 需要至少3个样本
        shapiro_stat, shapiro_p = stats.shapiro(group_data)
        print(f"{group_name}: W={shapiro_stat:.3f}, p={shapiro_p:.3f}")

# 方差齐性检验
print(f"\n=== 方差齐性检验 (Levene) ===")
groups = [qwen_physical, qwen_simulated, hunyuan_physical, hunyuan_simulated]
levene_stat, levene_p = stats.levene(*groups)
print(f"Levene检验: W={levene_stat:.3f}, p={levene_p:.3f}")