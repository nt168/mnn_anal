# MNN LLM Benchmark YAML配置实用指南

## 概述

本指南提供MNN LLM Benchmark框架YAML配置文件的实用编写方法，包含核心概念、常用模式、最佳实践和具体示例。

---

## 📖 基础概念

### 文件结构
```yaml
task_name: "测试任务名称"
description: "任务描述"
global_config:
  # 全局配置
benchmark_suits:
  # 测试套件列表
```

### 核心组成

1. **全局配置 (global_config)**：适用于整个测试任务的设置
2. **测试套件 (benchmark_suits)**：具体的测试集合定义
3. **变量参数 (variables)**：需要变化的测试参数
4. **固定参数 (fixed_params)**：在套件内保持不变的参数

---

## 🔧 参数详解

### 全局配置参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `timeout` | int | 否 | 全局超时时间(秒) |
| `models` | array | 是 | 测试模型列表 |
| `output_dir` | string | 否 | 结果输出目录 |
| `parallel_mode` | bool | 否 | 并行执行模式 |

### 测试参数详解

#### 序列长度参数
```yaml
# 输入序列长度
n_prompt: 128          # 固定值
# 或者使用范围模式
n_prompt:
  start: 64
  end: 512
  step: 64

# 生成长度
n_gen: 64

# 组合模式
prompt_gen: "256,128"  # 预填充256，生成128
```

#### 系统参数
```yaml
threads: 4              # 线程数
precision: 1            # 精度：0=High,1=Normal,2=Low
kv_cache: "true"        # KV缓存开关
mmap: 0                 # 内存映射开关
dynamic_option: 0       # 动态优化选项

# 重复测试
n_repeat: 5             # 重复次数
```

#### 提示词参数
```yaml
variable_prompt: 0      # 0=固定，1=可变
prompt_file: "test.txt" # 提示词文件名
```

---

## 🎯 常用测试模式

### 1. 简单单参数测试
```yaml
task_name: "线程数扩展性测试"
global_config:
  models: ["qwen3_0_6b"]
benchmark_suits:
- suit_name: "thread_scaling"
  description: "测试不同线程数下的性能"
  variables:
  - name: threads
    start: 1
    end: 8
    step: 1
  fixed_params:
    n_prompt: 128
    n_gen: 64
    precision: 1
    n_repeat: 3
```

### 2. 多参数组合测试
```yaml
- suit_name: "parameter_combination"
  description: "多参数组合性能测试"
  variables:
  - name: n_prompt
    values: [64, 128, 256]
  - name: precision
    values: [0, 1, 2]
  fixed_params:
    threads: 4
    n_gen: 64
    n_repeat: 3
```

### 3. PG组合测试
```yaml
- suit_name: "pg_combination"
  description: "Prefill+Generate组合测试"
  variables:
  - name: prompt_gen
    values:
    - "32,16"
    - "64,32"
    - "128,64"
    - "256,128"
  fixed_params:
    threads: 4
    precision: 1
   kv_cache: "true"
    n_repeat: 5
```

### 4. VL模型测试
```yaml
- suit_name: "vl_model_test"
  description: "VL模型特殊测试"
  variables:
  - name: prompt_gen
    values: ["96,32", "128,64"]
  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "false"
    variable_prompt: 0
    prompt_file: "vl_standard.txt"
    n_repeat: 3
```

---

## 📋 参数值定义方式

### 1. 范围定义（step模式）
```yaml
- name: threads
  start: 1
  end: 8
  step: 2
  # 生成：1, 3, 5, 7
```

### 2. 枚举定义（值列表）
```yaml
- name: precision
  values: [0, 1, 2]
  # 生成：0, 1, 2
```

### 3. 混合定义
```yaml
variables:
- name: threads
  start: 1
  end: 4
  step: 1
- name: precision
  values: [0, 1]
# 总组合数：4×2=8个测试用例
```

---

## 🛠️ 实用技巧

### 1. 性能vs稳定性权衡
```yaml
# 快速探索模式
n_repeat: 1  # 快速获得结果

# 可靠验证模式
n_repeat: 10  # 统计稳定性

# 生产部署模式
n_repeat: 5   # 平衡效率与可靠性
```

### 2. 内存管理
```yaml
# 大负载测试降低内存使用
fixed_params:
  precision: 2     # 使用Low精度
  kv_cache: "true" # 启用KV缓存减少内存

# 小负载追求最高精度
fixed_params:
  precision: 0     # 使用High精度
  kv_cache: "false"
```

### 3. 测试效率优化
```yaml
# 分阶段测试策略
# 阶段1：快速筛选
n_repeat: 2
variable范围：较大

# 阶段2：精确验证
n_repeat: 10
variable范围：缩小的最优区间
```

---

## 🚨 常见问题与解决

### 1. 内存不足
**症状**：测试中途失败，提示内存不足
**解决**：
```yaml
# 降低测试强度
fixed_params:
  precision: 2     # Low精度

# 减小测试规模
variables:
- name: n_prompt
  end: 128         # 减小最大长度

# 启用KV缓存
kv_cache: "true"
```

### 2. 测试时间过长
**症状**：预期几分钟，实际几小时
**解决**：
```yaml
# 减少重复次数
n_repeat: 3

# 减少参数组合
variables:
  - name: threads
    values: [1, 4, 8]  # 只测关键值

# 设置合理超时
global_config:
  timeout: 300
```

### 3. 结果不稳定
**症状**：相同参数下结果差异很大
**解决**：
```yaml
# 增加重复次数
n_repeat: 10

# 固化环境因素
fixed_params:
  threads: 4         # 固定线程数
  precision: 1       # 固定精度
  kv_cache: "true"   # 启用KV缓存确保一致性
```

---

## 📊 最佳实践

### 1. 文件组织
```
benchmarks/
├── simple_tests/      # 简单快速测试
├── comprehensive/     # 全面测试
├── regression/        # 回归测试
└── experimental/      # 实验性测试
```

### 2. 命名规范
```yaml
task_name: "model_threads_scaling_exp"
# 格式：主题_参数_目的_类型

# 好的命名
- "qwen3_performance_baseline"
- "memory_usage_stress_test"
- "cross_model_comparison"

# 避免的命名
- "test1"
- "temp_yaml"
- "final_test_v2"
```

### 3. 注释规范
```yaml
# 必要的注释说明
- suit_name: "prefill_analysis"
  description: "分析不同输入长度对Prefill性能的影响"
  variables:
  - name: n_prompt
    start: 32        # 最小有效长度
    end: 512         # 实际应用上限
    step: 32         # 常用递增单位
```

---

## 🔄 测试流程建议

### 1. 开发阶段
```yaml
# 快速验证配置正确性
global_config:
  timeout: 60
  models: ["qwen3_0_6b"]  # 单模型
benchmark_suits:
- variables:
  - name: threads
    values: [1, 4]      # 只测关键值
  n_repeat: 1           # 快速测试
```

### 2. 验证阶段
```yaml
# 全面功能验证
global_config:
  timeout: 600
  models:
    - "qwen3_0_6b"
    - "deepseek_r1_1_5b"
n_repeat: 5             # 稳定性测试
```

### 3. 生产阶段
```yaml
# 批量基准测试
global_config:
  timeout: 1200
  parallel_mode: true   # 并行执行
n_repeat: 10            # 统计可靠性
```

---

## 📚 参考模板

### 模板1：基础性能测试
```yaml
task_name: "基础性能基准测试"
description: "测试模型在标准配置下的基准性能"
global_config:
  timeout: 300
  models: ["qwen3_0_6b"]
benchmark_suits:
- suit_name: "baseline_test"
  variables:
  - name: prompt_gen
    values: ["64,32", "128,64", "256,128"]
  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "true"
    n_repeat: 5
```

### 模板2：扩展性测试
```yaml
task_name: "多维度扩展性测试"
description: "测试在不同参数配置下的扩展性表现"
global_config:
  timeout: 600
  models: ["qwen3_0_6b"]
benchmark_suits:
- suit_name: "scaling_analysis"
  variables:
  - name: threads
    start: 1
    end: 8
    step: 2
  - name: n_prompt
    values: [64, 128, 256, 512]
  fixed_params:
    precision: 1
    kv_cache: "true"
    n_repeat: 3
```

### 模板3：对比测试
```yaml
task_name: "模型对比基准测试"
description: "对比不同模型在相同配置下的性能表现"
global_config:
  timeout: 900
  models:
    - "qwen3_0_6b"
    - "deepseek_r1_1_5b"
    - "llama3_2_1b"
benchmark_suits:
- suit_name: "model_comparison"
  variables:
  - name: prompt_gen
    values: ["128,64", "256,128"]
  - name: threads
    values: [1, 4, 8]
  fixed_params:
    precision: 1
    kv_cache: "true"
    n_repeat: 5
```

---

## 🔗 相关资源

- **完整特性展示**：`MNN_LLM_Benchmark_YAML配置完整特性展示.md`
- **官方文档**：`MNN_LLM_Benchmark/tasks/README.md`
- **示例文件**：`MNN_LLM_Benchmark/tasks/*.yaml`
- **EAO项目指导**：`CLAUDE.md` 等

---

**文档版本**: v1.0
**最后更新**: 2025年11月19日
**适用框架**: MNN LLM Benchmark
**维护者**: EAO基准测试团队