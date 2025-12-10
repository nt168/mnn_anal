# MNN LLM Benchmark YAML配置完整特性展示

## 概述

本文档展示MNN LLM Benchmark框架中YAML配置文件的完整特性，包括所有参数类型、组合方式、高级功能和最佳实践。

---

## 🚀 超复杂综合样例

该样例涵盖MNN LLM Benchmark的所有核心功能和高级特性：

```yaml
task_name: "MNN LLM Benchmark 完整功能综合测试"
description: "包含所有参数类型、高级特性和复杂组合的综合测试，展示YAML配置的完整能力"
author: "EAO基准测试团队"
version: "2.0"
output_dir: "results/comprehensive_benchmark"

global_config:
  timeout: 1200              # 全局超时时间（20分钟）
  models:                    # 多模型测试
  - qwen3_0_6b              # 标准LLM模型
  - deepseek_r1_1_5b        # 对比模型
  - llama3_2_1b             # 第二对比模型
  parallel_mode: true       # 并行执行多个模型（如果支持）
  max_concurrent: 2         # 最大并发数
  log_level: "debug"        # 日志级别
  auto_cleanup: true        # 自动清理临时文件

# 核心指标基准测试套件
benchmark_suits:

# =========================================================================
# 套件1：Prefill性能专项测试 - 展示step增长和复杂参数组合
# =========================================================================
- suit_name: "prefill_performance_analysis"
  description: "Prefill阶段性能全面分析，包括序列长度、线程、精度等多维度测试"
  category: "prefill"

  variables:
  # 序列长度使用step增长模式
  - name: n_prompt
    start: 32
    end: 512
    step: 32
    description: "输入序列长度阶梯增长，测试Prefill扩展性"

  # 多线程测试
  - name: threads
    values: [1, 2, 4, 6, 8]
    description: "不同线程数下的Prefill性能"

  # 精度模式测试
  - name: precision
    values: [0, 1, 2]  # High, Normal, Low
    description: "精度对Prefill性能的影响"

  # KV缓存模式对比
  - name: kv_cache
    values: ["false"]  # Prefill测试通常禁用KV缓存
    description: "KV缓存模式"

  fixed_params:
    n_repeat: 6
    variable_prompt: 0
    debugging: false

# =========================================================================
# 套件2：Decode性能专项测试 - 展示参数约束和条件测试
# =========================================================================
- suit_name: "decode_performance_analysis"
  description: "Decode阶段性能分析，重点测试生成长度、模式切换和稳定性"
  category: "decode"

  variables:
  # 生成长度步进测试
  - name: n_gen
    start: 16
    end: 256
    step: 16
    constraint: "must_be_multiple_of_8"  # 约束条件示例
    description: "生成长度步进测试，必须为8的倍数"

  # 提示词模式切换测试
  - name: variable_prompt
    values: [0, 1]  # 固定模式 vs 可变模式
    description: "提示词模式对比测试"

  # 多种prompt_gen组合
  - name: prompt_gen
    values:
    - "32,16"   # 小规模
    - "64,32"   # 中等规模
    - "96,48"   # 较大规模
    description: "PG参数组合，测试不同负载模式"

  # 提示词文件测试
  - name: prompt_file
    values:
    - "en_short.txt"
    - "zh_medium.txt"
    - "code_python.txt"
    - "vl_standard.txt"
    description: "多语言和跨领域提示词测试"

  fixed_params:
    threads: 4
    precision: 1
    n_repeat: 8
    kv_cache: "true"

# =========================================================================
# 套件3：混合性能指标测试 - 展示混合负载和模式灵活性
# =========================================================================
- suit_name: "mixed_performance_validation"
  description: "pp+tg混合指标验证，测试端到端综合性能和指标一致性"
  category: "mixed"

  variables:
  # 复杂的prompt_gen矩阵测试
  - name: prompt_gen
    values:
    - "16,8"      # 极小负载
    - "32,16"     # 小负载
    - "64,32"     # 标准负载
    - "128,64"    # 中等负载
    - "256,128"   # 大负载
    - "512,256"   # 重负载
    constraint: "prefill_not_less_than_generate"  # 约束条件
    description: "多级别负载矩阵测试，prefill通常不小于generate"

  # 内存映射对比
  - name: mmap
    values: [0, 1]
    description: "内存映射开关对性能的影响"

  # 动态优化选项
  - name: dynamicOption
    values: [0, 4, 8]
    description: "动态优化级别对比"

  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "true"
    variable_prompt: 0
    n_repeat: 5

# =========================================================================
# 套件4：VL模型专项测试 - 展示特殊模型支持
# =========================================================================
- suit_name: "vl_model_special_validation"
  description: "VL（视觉语言）模型特殊测试，验证文件输入、调试模式等VL特定功能"
  category: "vl_models"

  variables:
  # VL模型的prompt_gen组合
  - name: prompt_gen
    values:
    - "96,32"    # 视觉描述任务
    - "128,64"   # 图像问答任务
    - "160,96"   # 图像理解任务
    description: "VL场景典型负载模式"

  # VL专用提示词文件
  - name: prompt_file
    values:
    - "vl_image_desc.txt"     # 图像描述
    - "vl_qa.txt"             # 图像问答
    - "vl_ocr.txt"            # 文字识别
    - "vl_chart_analysis.txt" # 图表分析
    description: "VL专业提示词文件"

  # VL模型特殊参数测试
  - name: variable_prompt
    values: [0]  # VL模型建议使用固定模式
    description: "VL模型提示词模式"

  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "false"  # VL测试通常禁用KV缓存
    n_repeat: 4
    debugging: true     # 启用调试模式查看详细信息

# =========================================================================
# 套件5：性能压力测试 - 展示边界条件和极限测试
# =========================================================================
- suit_name: "extreme_performance_stress"
  description: "性能压力和边界条件测试，验证工具在极限条件下的稳定性"
  category: "stress_test"

  variables:
  # 大负载压力测试
  - name: prompt_gen
    values:
    - "1024,512"    # 超大负载测试
    - "2048,1024"   # 极限负载测试
    warning: "high_memory_usage"
    description: "极限负载测试，注意内存使用"

  # 极短序列测试
  - name: prompt_gen
    values:
    - "4,2"         # 极小测试
    - "8,4"         # 最小有效测试
    category: "boundary"
    description: "边界条件测试"

  # 并发线程数极限测试
  - name: threads
    values: [1, 4, 8, 12, 16]
    warning: "high_cpu_usage"
    description: "高并发压力测试"

  fixed_params:
    precision: 2      # 低精度减少压力
    kv_cache: "true"
    variable_prompt: 0
    n_repeat: 2

# =========================================================================
# 套件6：算法验证测试 - 展示科学实验设计
# =========================================================================
- suit_name: "algorithmic_validation"
  description: "算法正确性验证，确保不同配置下数学计算的一致性"
  category: "validation"

  variables:
  # 数学一致性验证：相同总token数的不同分解
  - name: prompt_gen
    values:
    - "64,128"   # 偏decode
    - "96,96"    # 平衡
    - "128,64"   # 偏prefill
    validation_type: "mathematical_consistency"
    description: "数学一致性验证：相同总token数不同分解"

  # 统计稳定性验证
  - name: n_repeat
    values: [1, 5, 10, 20]
    validation_type: "stability_analysis"
    description: "统计稳定性分析"

  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "false"
    variable_prompt: 0

# =========================================================================
# 套件7：回归测试套件 - 展示测试管理和版本对比
# =========================================================================
- suit_name: "regression_test_suite"
  description: "回归测试集合，确保新版本不破坏现有功能"
  category: "regression"

  variables:
  # 核心基准组合
  - name: prompt_gen
    values:
    - "64,32"   # 轻负载基准
    - "128,64"  # 标准负载基准
    benchmark_reference: true
    description: "基准性能参考点"

  # 多模型一致性测试
  - name: model_param_override
    values: ["qwen3_0_6b", "deepseek_r1_1_5b", "llama3_2_1b"]
    validation_type: "cross_model_consistency"
    description: "跨模型一致性验证"

  fixed_params:
    threads: 4
    precision: 1
    kv_cache: "true"
    variable_prompt: 0
    n_repeat: 5

# =========================================================================
# 套件8：特殊功能测试 - 展示高级和实验性功能
# =========================================================================
- suit_name: "special_features_test"
  description: "特殊功能实验性测试，包括调试模式、性能剖析等"
  category: "experimental"

  variables:
  # 调试模式深度测试
  - name: debugging
    values: [true]
    experimental: true
    description: "深度调试模式测试"

  # 性能剖析模式
  - name: profiling
    values: ["basic", "detailed"]
    experimental: true
    description: "性能剖析级别"

  # 自定义测试模式（如果支持）
  - name: test_mode
    values: ["standard", "compatibility", "enterprise"]
    experimental: true
    description: "不同测试模式"

  fixed_params:
    threads: 4
    precision: 1
    prompt_gen: "64,32"
    kv_cache: "true"
    variable_prompt: 0
    n_repeat: 3

# =========================================================================
# 全局测试配置和环境变量
# =========================================================================

test_execution_config:
  # 并行执行配置
  parallel_execution:
    enabled: true
    max_processes: 4
    memory_limit: "8GB"

  # 结果处理配置
  result_processing:
    auto_analysis: true
    statistical_summary: true
    visualization: true
    export_formats: ["csv", "json", "html"]

  # 质量控制配置
  quality_control:
    retry_failed_tests: true
    max_retries: 3
    outlier_detection: true
    statistical_significance: true

# 环境依赖和前提条件
environment_setup:
  Required_software:
    - "MNN-Latest"
    - "Python >= 3.8"

  required_models:
    paths:
      qwen3_0_6b: "/models/qwen3-0.6b-mnn"
      deepseek_r1_1_5b: "/models/deepseek-r1-1.5b-mnn"
      llama3_2_1b: "/models/llama3-2-1b-mnn"

  system_resources:
    min_memory: "4GB"
    recommended_memory: "8GB"
    min_cores: 4
    recommended_cores: 8

# 测试目标和验证标准
validation_criteria:
  performance_benchmarks:
    pp_speed_min: 100    # tokens/s
    tg_speed_min: 50     # tokens/s
    mixed_speed_min: 80  # tokens/s

  stability_requirements:
    cv_threshold: 0.05   # 变异系数最大5%
    outlier_ratio: 0.1   # 异常值最大10%

  consistency_checks:
    cross_model_cv: 0.1  # 跨模型CV最大10%
    mathematical_error: 0.001  # 数学计算误差

# 结果分析和报告模板
analysis_templates:
  summary_template: "templates/benchmark_summary.md"
  detailed_template: "templates/benchmark_detailed.md"
  comparison_template: "templates/model_comparison.md"
  regression_template: "templates/regression_analysis.md"

---
## 配置文件说明

### 🎯 核心特性展示

1. **多样化参数类型**：
   - 范围型参数：`start/end/step`
   - 枚举型参数：固定值列表
   - 组合型参数：多变量组合
   - 约束型参数：条件限制

2. **高级功能**：
   - 多模型并行测试
   - 实验性功能测试
   - 回归测试套件
   - 性能压力测试

3. **智能配置**：
   - 环境依赖声明
   - 质量控制配置
   - 验证标准定义
   - 结果处理模板

4. **最佳实践**：
   - 详细的注释和描述
   - 分类和标签化管理
   - 警告和风险提示
   - 性能基准定义

### 📋 参数完整列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `n_prompt` | int/step | 512 | 输入序列长度 |
| `n_gen` | int | 128 | 生成序列长度 |
| `prompt_gen` | string | "512,128" | 预填充和生成参数 |
| `threads` | int/step | [1,4,8] | 线程数设置 |
| `precision` | int | 1 | 精度模式(0/1/2) |
| `kv_cache` | string | "true" | KV缓存开关 |
| `variable_prompt` | int | 0 | 提示词模式 |
| `prompt_file` | string | - | 提示词文件名 |
| `n_repeat` | int | 1 | 重复测试次数 |
| `mmap` | int | 0 | 内存映射开关 |
| `dynamicOption` | int | 0 | 动态优化选项 |

### 🔧 高级特性

1. **约束条件**：
   ```yaml
   constraint: "must_be_multiple_of_8"
   constraint: "prefill_not_less_than_generate"
   ```

2. **实验性标记**：
   ```yaml
   experimental: true
   warning: "high_memory_usage"
   ```

3. **验证类型**：
   ```yaml
   validation_type: "mathematical_consistency"
   benchmark_reference: true
   ```

4. **自定义分类**：
   ```yaml
   category: "stress_test"
   description: "详细的中文描述"
   ```

---

**文档版本**: v1.0
**最后更新**: 2025年11月19日
**适用框架**: MNN LLM Benchmark
**维护者**: EAO基准测试团队