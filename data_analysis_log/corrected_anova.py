#!/usr/bin/env python3
import numpy as np
from scipy import stats
import pandas as pd

# 读取数据
data = pd.read_csv('anova_data.csv')
complete_data = data[data['Tokens'] < 512].copy()

print("=== 使用scipy.stats的标准双因子ANOVA ===")

# 为模型和环境创建分类编码
complete_data['Model_Code'] = (complete_data['Model'] == 'Hunyuan').astype(int)
complete_data['Env_Code'] = (complete_data['Environment'] == 'Simulated').astype(int)

# 手动计算ANOVA的另一种方法
def two_way_anova(y, factor1, factor2):
    n = len(y)

    # 计算各组合的均值
    overall_mean = np.mean(y)

    # 因子水平
    levels1 = np.unique(factor1)
    levels2 = np.unique(factor2)

    # 主效应
    # 因子1
    means1 = [np.mean(y[factor1 == level]) for level in levels1]
    ns1 = [np.sum(factor1 == level) for level in levels1]
    ss1 = np.sum([n1 * (mean1 - overall_mean)**2 for n1, mean1 in zip(ns1, means1)])
    df1 = len(levels1) - 1

    # 因子2
    means2 = [np.mean(y[factor2 == level]) for level in levels2]
    ns2 = [np.sum(factor2 == level) for level in levels2]
    ss2 = np.sum([n2 * (mean2 - overall_mean)**2 for n2, mean2 in zip(ns2, means2)])
    df2 = len(levels2) - 1

    # 交互效应
    cell_means = []
    cell_ns = []
    for level1 in levels1:
        for level2 in levels2:
            mask = (factor1 == level1) & (factor2 == level2)
            if np.sum(mask) > 0:
                cell_means.append(np.mean(y[mask]))
                cell_ns.append(np.sum(mask))

    # 预测值（无交互）
    predicted = []
    for _, (level1, level2) in enumerate([(0,0), (0,1), (1,0), (1,1)]):
        pred = means1[level1] + means2[level2] - overall_mean
        predicted.append(pred)

    ss_inter = np.sum([cell_ns[i] * (cell_means[i] - predicted[i])**2 for i in range(len(cell_means))])
    df_inter = (len(levels1) - 1) * (len(levels2) - 1)

    # 总平方和
    ss_total = np.sum((y - overall_mean)**2)
    df_total = n - 1

    # 误差平方和
    ss_error = ss_total - ss1 - ss2 - ss_inter
    df_error = df_total - df1 - df2 - df_inter

    # 均方
    ms1 = ss1 / df1
    ms2 = ss2 / df2
    ms_inter = ss_inter / df_inter
    ms_error = ss_error / df_error

    # F值和p值
    f1 = ms1 / ms_error if ms_error > 0 else 0
    f2 = ms2 / ms_error if ms_error > 0 else 0
    f_inter = ms_inter / ms_error if ms_error > 0 else 0

    p1 = 1 - stats.f.cdf(f1, df1, df_error) if ms_error > 0 else 1
    p2 = 1 - stats.f.cdf(f2, df2, df_error) if ms_error > 0 else 1
    p_inter = 1 - stats.f.cdf(f_inter, df_inter, df_error) if ms_error > 0 else 1

    return {
        'SS': [ss1, ss2, ss_inter, ss_error, ss_total],
        'DF': [df1, df2, df_inter, df_error, df_total],
        'MS': [ms1, ms2, ms_inter, ms_error, 0],
        'F': [f1, f2, f_inter, 0, 0],
        'p': [p1, p2, p_inter, 0, 0],
        'Factor': ['Model', 'Environment', 'Interaction', 'Error', 'Total']
    }

# 执行ANOVA
y = complete_data['DecodeSpeed'].values
factor1 = complete_data['Model_Code'].values
factor2 = complete_data['Env_Code'].values

results = two_way_anova(y, factor1, factor2)

# 输出结果
print(f"\n=== 修正的ANOVA结果 ===")
print(f"{'效应':<12} {'平方和':<12} {'自由度':<8} {'均方':<12} {'F值':<8} {'p值':<8}")
print("-" * 70)
for i in range(5):
    print(f"{results['Factor'][i]:<12} {results['SS'][i]:<12.3f} {results['DF'][i]:<8} {results['MS'][i]:<12.3f} {results['F'][i]:<8.3f} {results['p'][i]:<8.3f}")

# 效应量
print(f"\n=== 效应量 (η²) ===")
for i in range(3):  # 只显示主效应和交互效应
    eta2 = results['SS'][i] / results['SS'][4]
    print(f"{results['Factor'][i]}: {eta2:.3f}")

# 计算描述性统计
print(f"\n=== 各组描述统计 ===")
group_stats = complete_data.groupby(['Model', 'Environment'])['DecodeSpeed'].agg(['count', 'mean', 'std']).round(3)
print(group_stats)

# 方差齐性检验
print(f"\n=== 方差齐性检验 (Levene) ===")
groups = []
for model in ['Qwen', 'Hunyuan']:
    for env in ['Physical', 'Simulated']:
        group = complete_data[(complete_data['Model'] == model) &
                            (complete_data['Environment'] == env)]['DecodeSpeed']
        if len(group) > 0:
            groups.append(group)

if len(groups) >= 2:
    levene_stat, levene_p = stats.levene(*groups)
    print(f"Levene检验: W={levene_stat:.3f}, p={levene_p:.3f}")