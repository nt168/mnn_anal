# EAO详测阶段结果分析环境

## 环境概述

本目录为EAO详测阶段的结果分析工作环境，基于uv构建Python环境，提供端侧LLM推理性能数学建模所需的分析工具。

## 环境依赖

核心依赖包：
- pandas (数据处理和分析)
- numpy (数值计算)
- matplotlib (基础绘图)
- seaborn (统计可视化)
- scipy (科学计算)
- scikit-learn (机器学习和建模)
- tqdm (进度条)
- imageio (图像处理)
- statsmodels (统计建模)

## 快速使用

### 激活环境
```bash
# 进入目录
cd 03-详测阶段/结果分析

# 环境已通过uv配置，直接使用即可
```

### 运行分析脚本
```bash
# 使用模板脚本分析数据
uv run python scripts/template_analysis.py --data-path path/to/your/data.csv

# 或者直接运行Python进行交互式分析
uv run python
```

## 目录结构

```
03-详测阶段/结果分析/
├── .venv/                    # uv管理的Python虚拟环境
├── scripts/                  # 分析脚本目录
│   └── template_analysis.py  # 模板分析脚本
├── pyproject.toml           # 项目配置文件
├── uv.lock                  # uv锁定文件
└── README.md                # 本文件
```

## 功能模块

### 1. 数据加载与预处理
- 支持CSV、JSON等格式数据
- 自动数据质量检查
- 缺失值处理

### 2. 多元回归分析
- 参数相关性分析
- 回归模型建立
- 交互效应分析

### 3. 可视化
- 相关性矩阵热图
- 性能趋势图表
- 模型诊断图表

### 4. 模型验证
- 交叉验证
- 残差分析
- 预测精度评估

## 使用指南

### 安装/更新环境
```bash
# 初次设置或更新依赖
uv sync
```

### 添加新分析脚本
1. 在`scripts/`目录下创建新的Python文件
2. 导入所需依赖库
3. 使用`uv run python scripts/your_script.py`运行

### 注意事项
- 所有分析脚本应优先使用已安装的依赖包
- 输出文件建议保存至专门的`output/`目录
- 重要图表保存为高分辨率PNG格式便于报告使用

## 与阶段02的差异

本环境相对于阶段02（初测阶段）结果分析：
- 重点关注数学建模和回归分析
- 强调多参数交互效应分析
- 支持更复杂的数据模型验证

## 技术支持

如有问题请参考：
- 项目主文档：`../README.md`
- 详测阶段工作逻辑：`../README.md`