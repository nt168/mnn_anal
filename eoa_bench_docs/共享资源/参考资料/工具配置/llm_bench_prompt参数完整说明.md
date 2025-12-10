# llm_bench_prompt 参数完整说明

## 概述

本文档详细说明MNN LLM Bench工具 `llm_bench_prompt` 的所有参数配置，分为**核心参数**（用于测试和基准）和**辅助参数**（调试、开发、特定用途）两部分。核心参数基于EAO基准测试项目需求提供详细使用指南，辅助参数仅作简单说明。

---

## 🔧 参数体系概览

### 🎯 核心参数（11个）

| 参数 | 简写 | 类型 | 默认值 | 说明 | 说明 |
|------|------|------|--------|------|------|
| **threads** | `-t` | int | 4 | 线程数配置 |
| **n-prompt** | `-p` | int | 512 | 提示词长度（输入） |
| **n-gen** | `-n` | int | 128 | 生成长度（输出） |
| **prompt-gen** | `-pg` | string | "512,128" | 预填充+生成格式 |
| **n-repeat** | `-rep` | int | 5 | 重复测试次数 |
| **precision** | `-c` | int | 2 | 精度模式 |
| **kv-cache** | `-kv` | string | "true" | KV缓存开关 |
| **mmap** | `-mmp` | int | 0 | 内存映射开关 |
| **dynamicOption** | `-dyo` | int | 0 | 动态优化选项 |
| **variable-prompt** | `-vp` | int | 0 | 可变提示词模式 |
| **prompt-file** | `-pf` | string | - | 提示词文件路径 |

### 🔧 非核心参数（6个）

| 参数 | 简写 | 类型 | 默认值 | 说明 | 适用场景 |
|------|------|------|--------|------|------|
| **backend** | `-a` | string | "cpu" | 计算后端 | 开发调试 |
| **loadingTime** | `-load` | bool | true | 模型加载测试 | 性能分析 |
| **verbose** | `-v` | bool | false | 详细输出模式 | 调试诊断 |
| **file-print** | `-fp` | string | "stdout" | 输出重定向 | 结果管理 |
| **help** | `-h` | - | - | 帮助信息 | 工具说明 |

> ⚠️ **注意**：非核心参数主要用于开发调试、性能分析等特殊场景，EAO基准测试项目中**不使用**这些参数。

---

## 📋 参数详细说明

### 🔧 `threads` / `-t` - 线程配置

#### 基本用法
```bash
./llm_bench_prompt -m model.json -t 8    # 8线程
./llm_bench_prompt -m model.json -t 1,4,8  # 多线程测试
```

#### 参数意义
- **类型**: 整数，1-16范围
- **默认值**: 4
- **作用**: 控制LLM推理时的并行线程数

#### 使用指南

##### 1. 性能优化测试
```yaml
# EAO基准测试设置
variables:
- name: threads
  values: [1, 2, 4, 6, 8]  # 递增测试
fixed_params:
  other_param: value
```

##### 2. 实际应用配置
```yaml
# 生产环境推荐
fixed_params:
  threads: 4  # 平衡性能和资源占用
```

##### 3. 性能分析场景
```yaml
# 完整扩展性测试
variables:
- name: threads
  start: 1
  end: 16
  step: 2  # 1, 3, 5, ..., 15 (建议2的幂次)
```

#### 注意事项
- **硬件上限**: 不超过CPU物理核心数
- **性能阈值**: 通常4-8线程达到最佳性能
- **资源争用**: 线程过多可能因资源争用降低性能

---

### 📝 `n-prompt` / `-p` - 提示词长度

#### 基本用法
```bash
./llm_bench_prompt -m model.json -p 64      # 64个token提示词
./llm_bench_prompt -m model.json -p 32,64,128
```

#### 参数意义
- **类型**: 正整数，建议范围4-512
- **默认值**: 512
- **作用**: 预填充阶段的输入token数量

#### 使用指南

##### 1. 收敛性测试（EAO 3号报告）
```yaml
# 基于科学搜索理论
variables:
- name: n_prompt
  values: [4, 8, 16, 32, 48, 64, 96, 128, 192, 256]  # 对数采样
```

##### 2. 标准基准测试
```yaml
# 常用长度测试
variables:
- name: n_prompt
  values: [32, 64, 96, 128]  # 覆盖典型应用
```

##### 3. 边界条件测试
```yaml
# 极端条件验证
variables:
- name: n_prompt
  values: [4, 8, 256, 512]  # 最小和最大边界
```

#### 理论依据
- **EAO 3号报告**: 通过CV收敛性确定最优长度
- **实际应用**: 与典型prompt长度匹配
- **性能影响**: 长度增加会导致prefill时间线性增长

#### 数据参考
| 应用场景 | 推荐长度 | 说明 |
|----------|----------|------|
| **实时对话** | 32-64 | 简短交互 |
| **文档处理** | 96-192 | 中等文档 |
| **长文生成** | 256-512 | 长文档创作 |

---

### 🔤 `n-gen` / `-n` - 生成长度

#### 基本用法
```bash
./llm_bench_prompt -m model.json -n 32      # 生成32个token
./llm_bench_prompt -m model.json -n 16,32,64
```

#### 参数意义
- **类型**: 正整数，建议范围8-256
- **默认值**: 128
- **作用**: 设置解码（生成）阶段的输出token数量

#### 使用指南

##### 1. 平衡测试
```yaml
# 保持prompt和gen长度比例合理
variables:
- name: n_gen
  values: [32, 64, 96]  # 测试不同生成长度
fixed_params:
  n_prompt: 64          # 固定提示词长度
```

##### 2. 应用场景测试
```yaml
# 不同生成长度要求
variables:
- name: n_gen
  values: [16]  # 短回答
# ---
variables:
- name: n_gen
  values: [64, 128]  # 中等回答
# ---
variables:
- name: n_gen
  values: [256]  # 长篇生成
```

#### 理论依据
- **时间复杂度**: decode时间与生成长度线性相关
- **质量权衡**: 更长生成长度可能需要更高质量评估
- **实用范围**: 大多数应用场景不超过128 tokens

---

### 🔄 `prompt-gen` / `-pg` - 组合模式

#### 基本用法
```bash
./llm_bench_prompt -m model.json -pg "64,32"    # 64提示+32生成
./llm_bench_prompt -m model.json -pg "256,256"  # 预填充+生成模式
```

#### 参数意义
- **类型**: "prefill,generate"格式字符串
- **覆盖规则**: 覆盖`-p`和`-n`的独立设置
- **默认值**: "512,128"

#### 使用指南

##### 1. PP+TG组合测试
```yaml
# Prefill+Generate性能测试
variables:
- name: prompt_gen
  values:
  - "32,16"   # 轻负载
  - "64,32"   # 标准负载
  - "128,64"  # 重负载
```

##### 2. 纯模式测试
```yaml
# 纯Prefill测试
fixed_params:
  prompt_gen: "256,8"  # 大prefill，小generate

# 纯Generate测试
fixed_params:
  prompt_gen: "8,256"   # 小prefill，大generate
```

##### 3. 比例分析
```yaml
# 1:1比例测试
variables:
- name: prompt_gen
  values: ["16,16", "32,32", "64,64", "128,128"]
```

#### 应用价值
- **综合性评估**: 避免单独测试pp/tg的偏差
- **实际场景**: 真实应用通常包含输入+输出
- **性能预测**: 更准确反映端到端性能

---

### 🔄 `n-repeat` / `-rep` - 重复测试

#### 基本用法
```bash
./llm_bench_prompt -m model.json -rep 10    # 重复10次
```

#### 参数意义
- **类型**: 正整数，建议范围1-20
- **默认值**: 5
- **作用**: 每个测试配置的重复执行次数

#### 统计输出
每次重复测试后自动输出：
- **平均值**: μ ± std
- **标准差**: σ
- **变异系数**: CV = σ/μ

#### 使用指南

##### 1. 质量优先（EAO基准测试）
```yaml
fixed_params:
  n_repeat: 10  # 确保统计可靠性
```

##### 2. 快速验证
```yaml
fixed_params:
  n_repeat: 3   # 初步筛选
```

##### 3. 精确测量
```yaml
fixed_params:
  n_repeat: 15  # 高精度分析
```

##### 4. 统计学建议
| 目的 | 重复次数 | 置信度 | 应用场景 |
|------|----------|--------|----------|
| **筛选测试** | 3-5 | 80% | 快速验证 |
| **常规测试** | 10 | 95% | 标准基准 |
| **精确分析** | 15-20 | 99% | 科学测量 |

---

### ⚙️ `precision` / `-c` - 精度模式

#### 基本用法
```bash
./llm_bench_prompt -m model.json -c 0    # Normal精度
./llm_bench_prompt -m model.json -c 2    # Low精度
```

#### 参数映射
| 值 | 字符串标识 | 精度类型 | 浮点格式 | 性能影响 |
|----|------------|----------|----------|---------|
| **0** | "normal" | **全精度** | FP32 | 基准性能 |
| **1** | "high" | **全精度** | FP32 | 基准性能 |
| **2** | "low" | **低精度** | FP16* | 速度提升 |

*仅在硬件支持FP16时启用

#### 使用指南

##### 1. 基准测试（EAO推荐）
```yaml
fixed_params:
  precision: 0  # FP32确保准确性
```

##### 2. 性能优化
```yaml
# 仅在fp16硬件支持时
fixed_params:
  precision: 2  # FP16加速测试
```

##### 3. 对比测试
```yaml
variables:
- name: precision
  values: [0, 2]  # FP32 vs FP16对比
```

#### 硬件兼容性
```bash
# 检查FP16支持
./llm_bench_prompt -m model.json  # 查看输出: fp16:1
# 如果fp16: 0，则precision: 2无加速效果
```

---

### 🗄️ `kv-cache` / `-kv` - KV缓存

#### 基本用法
```bash
./llm_bench_prompt -m model.json -kv true   # 启用KV缓存
./llm_bench_prompt -m model.json -kv false  # 禁用KV缓存
```

#### 参数意义
- **类型**: 布尔值 true/false
- **默认值**: "true"
- **作用**: 控制是否保存和重用键值缓存

#### 影响分析
| 模式 | 首次生成 | 后续生成 | 内存占用 | 适用场景 |
|------|----------|----------|----------|----------|
| **true** | 慢（保存） | 快（重用） | 高 | 连续对话 |
| **false** | 快（无保存） | 慢（重新计算） | 低 | 独立测试 |

#### 使用指南

##### 1. 基准测试一致性
```yaml
# 确保测试条件一致
fixed_params:
  kv_cache: "false"  # 避免缓存影响独立性
```

##### 2. 实际应用测试
```yaml
# 模拟真实使用场景
fixed_params:
  kv_cache: "true"   # 启用缓存加速
```

##### 3. 性能差异分析
```yaml
variables:
- name: kv_cache
  values: ["true", "false"]
```

---

### 📦 `mmap` / `-mmp` - 内存映射

#### 基本用法
```bash
./llm_bench_prompt -m model.json -mmp 1    # 启用内存映射
./llm_bench_prompt -m model.json -mmp 0    # 禁用内存映射
```

#### 参数意义
- **类型**: 整数 0/1
- **默认值**: 0
- **作用**: 模型文件加载方式选择

#### 影响分析
| 模式 | 加载速度 | 内存使用 | 适用场景 |
|------|----------|----------|----------|
| **1** | 快（直接映射） | 高内存 | 系统资源充足 |
| **0** | 慢（拷贝加载） | 低内存 | 内存受限设备 |

#### 使用指南

##### 1. 性能测试
```yaml
# 优先考虑性能
fixed_params:
  mmap: 1
```

##### 2. 资源受限设备
```yaml
# 端侧设备考虑
fixed_params:
  mmap: 0
```

##### 3. 兼容性测试
```yaml
variables:
- name: mmap
  values: [0, 1]
```

---

### ⚡ `dynamicOption` / `-dyo` - 动态优化

#### 基本用法
```bash
./llm_bench_prompt -m model.json -dyo 4   # 动态优化级别4
```

#### 参数范围
- **类型**: 整数 0-8
- **默认值**: 0
- **含义**: MNN动态优化选项

#### 优化级别
| 级别 | 优化程度 | 适用情况 | 风险 |
|------|----------|----------|------|
| **0-2** | 低 | 兼容性优先 | 低 |
| **3-5** | 中 | 平衡优化 | 中 |
| **6-8** | 高 | 性能优先 | 高 |

#### 使用指南

##### 1. 稳定性测试
```yaml
# 确保结果稳定
fixed_params:
  dynamicOption: 0
```

##### 2. 性能探索
```yaml
# 渐进式优化
variables:
- name: dynamicOption
  values: [0, 2, 4, 6]
```

##### 3. 生产配置
```yaml
# 保守优化
fixed_params:
  dynamicOption: 2
```

---

### 🎭 `variable-prompt` / `-vp` - 可变提示词

#### 基本用法
```bash
./llm_bench_prompt -m model.json -vp 1    # 启用可变模式
./llm_bench_prompt -m model.json -vp 0    # 固定模式
```

#### 参数意义
| 值 | 模式 | Token行为 | 应用场景 |
|----|------|-----------|----------|
| **0** | **固定** | 固定重复16值 | 基准测试 |
| **1** | **可变** | 20-39循环 | 多样性测试 |

#### 详细说明

##### 固定模式（vp=0）
```cpp
// 所有token都是16
std::vector<int> tokens(n_prompt, 16);
```

##### 可变模式（vp=1）
```cpp
// 20-39循环
for (int i = 0; i < n_prompt; ++i) {
    tokens.push_back(20 + (i % 20)); // 20,21,...,39,20,21,...
}
```

#### 使用指南

##### 1. 科学基准测试
```yaml
# EAO标准：固定模式确保一致性
fixed_params:
  variable_prompt: 0
```

##### 2. 模型鲁棒性测试
```yaml
# 测试对输入变化的适应能力
variables:
- name: variable_prompt
  values: [0, 1]
```

---

### 📄 `prompt-file` / `-pf` - 提示词文件

#### 基本用法
```bash
./llm_bench_prompt -m model.json -pf test.txt    # 使用文件内容
```

#### 参数要求
- **类型**: 文件路径（仅文件名，无路径）
- **必需性**: 可选，默认不使用
- **文件位置**: MNN标准目录或通过环境变量指定

#### 使用场景

##### 1. VL模型必需
```yaml
# VL模型必须使用文件提示词
fixed_params:
  prompt_file: "vl_standard.txt"
  variable_prompt: 0
```

##### 2. 标准化测试
```yaml
# 统一提示词内容
fixed_params:
  prompt_file: "benchmark_standard.txt"
```

##### 3. 多语言测试
```yaml
variables:
- name: prompt_file
  values:
    - "zh_test.txt"
    - "en_test.txt"
    - "code_test.txt"
```

#### 文件初始化代码参考
```python
# 提示词文件内容示例
test_content = "请介绍一下人工智能的基本概念。"

# 写入文件
with open("test.txt", "w") as f:
    f.write(test_content)
```

---

## 🎯 EAO项目特定建议

### 💡 参数选择策略

#### 1. 科学基准测试
```yaml
fixed_params:
  threads: 4
  n_prompt: 64     # 或通过3号报告确定的最优值
  n_gen: 64
  precision: 0
  kv_cache: "false"
  variable_prompt: 0
  n_repeat: 10
```

#### 2. 性能优化测试
```yaml
variables:
- name: threads
  values: [1, 2, 4, 6, 8]
- name: precision
  values: [0, 2]  # FP32 vs FP16对比
```

#### 3. 模型对比测试
```yaml
variables:
- name: n_prompt
  values: [32, 64, 96, 128]
- name: n_gen
  values: [32, 64]
```

### 📋 配置模板库

#### 标准配置库
```yaml
# 模板1: 基础性能测试
name: "baseline_performance"
fixed_params:
  threads: 4
  precision: 0
  kv_cache: "false"
  variable_prompt: 0
  n_repeat: 10
  n_prompt: 64
  n_gen: 64

# 模板2: 扩展性测试
name: "scalability_test"
variables:
- name: threads
  start: 1
  end: 8
  step: 2

# 模板3: VL模型测试
name: "vl_model_test"
fixed_params:
  threads: 4
  precision: 0
  kv_cache: "false"
  variable_prompt: 0
  prompt_file: "vl_standard.txt"
  n_repeat: 5
  n_gen: 64
```

---

## 🔧 辅助参数详细说明

> ⚠️ **注意**：以下参数主要用于开发调试、性能分析等特殊场景，EAO基准测试项目中**不使用**这些参数。

### 🖥️ `backend` / `-a` - 计算后端

#### 基本用法
```bash
./llm_bench_prompt -m model.json -a cpu      # CPU后端
./llm_bench_prompt -m model.json -a opencl   # OpenCL后端
./llm_bench_prompt -m model.json -a metal     # Metal后端
```

#### 支持的后端
| 后端 | 标识符 | 适用平台 | 说明 |
|------|--------|----------|------|
| **CPU** | cpu | 所有平台 | 通用计算 |
| **OpenCL** | opencl | GPU设备 | 并行加速 |
| **Metal** | metal | Apple平台 | 专用加速 |

#### 用途
- **性能对比**：不同后端性能差异分析
- **兼容性测试**：验证平台兼容性
- **开发调试**：在CPU上开发然后在目标后端测试

---

### ⏱️ `loadingTime` - 模型加载时间测试

#### 基本用法
```bash
./llm_bench_prompt -m model.json --loadingTime true
```

#### 输出内容
- **三次测量**：平均加载时间 ± 标准差
- **时间统计**：加载阶段性能分析

#### 用途
- **性能基准**：模型初始化成本
- **冷启动分析**：首次加载性能
- **系统评估**：存储I/O能力评估

---

### 📊 `v` / `-v` - 详细输出模式

#### 基本用法
```bash
./llm_bench_prompt -m model.json -v
```

#### 输出信息
- **Token详情**：输入/输出token数量和内容
- **执行过程**：每步执行状态和时间
- **错误诊断**：详细的错误信息

#### 用途
- **问题诊断**：测试失败时的详细分析
- **数据验证**：确认输入数据正确性
- **开发调试**：算法验证和优化

---

### 🛠️ `testPath` - 测试数据路径

#### 基本用法
```bash
./llm_bench_prompt -m model.json --testPath /path/to/test
```

#### 用途
- **自定义数据**：使用特定测试数据集
- **路径配置**：指定提示词文件位置
- **开发测试**：测试环境配置

---

### ⏰ `timeLimit` - 时间限制模式

#### 基本用法
```bash
./llm_bench_prompt -m model.json --timeLimit true
```

#### 功能
- **超时保护**：防止测试无限运行
- **性能约束**：强制在时限内完成

#### 用途
- **CI/CD集成**：确保测试及时完成
- **批量测试**：规范测试时间窗口

---

### ℹ️ `help` / `-h` - 帮助信息

#### 基本用法
```bash
./llm_bench_prompt -h
./llm_bench_prompt --help
```

#### 输出内容
- 完整参数列表
- 参数说明和默认值
- 使用示例

---

### 🔢 `version` - 版本信息

#### 基本用法
```bash
./llm_bench_prompt --version
```

#### 输出内容
- 工具版本号
- 构建信息
- 编译器版本

---

### 📈 `profile` - 性能剖析

#### 基本用法
```bash
./llm_bench_prompt -m model.json --profile true
```

#### 输出信息
- **时间分布**：各阶段耗时分析
- **内存使用**：内存占用统计
- **计算性能**：热点函数分析

#### 用途
- **性能优化**：识别性能瓶颈
- **资源分析**：内存和CPU使用评估
- **架构优化**：系统调优指导

---

### 📝 `logLevel` - 日志级别

#### 基本用法
```bash
./llm_bench_prompt -m model.json --logLevel debug
```

#### 日志级别
- **error**：仅错误信息
- **info**：一般信息
- **debug**：详细调试信息
- **trace**：最详细信息

#### 用途
- **开发调试**：详细的执行流程跟踪
- **问题排查**：错误定位和分析

---

### 📄 `configFile` - 配置文件

#### 基本用法
```bash
./llm_bench_prompt -m model.json --configFile config.yaml
```

#### 功能
- 批量参数配置
- 环境变量设置
- 全局参数覆盖

#### 用途
- **批量部署**：统一的参数管理
- **CI配置**：自动化测试配置

---

### 🎨 `outputFormat` - 输出格式

#### 基本用法
```bash
./llm_bench_prompt -m model.json --outputFormat json
```

#### 支持格式
- **markdown**：Markdown表格（默认）
- **json**：JSON结构化数据
- **csv**：CSV表格数据

#### 用途
- **自动化处理**：程序化数据分析
- **系统集成**：与其他工具链集成
- **数据导出**：结果数据处理

---

### 🐛 `debugMode` - 调试模式

#### 基本用法
```bash
./llm_bench_prompt -m model.json --debugMode true
```

#### 调试功能
- **断点设置**：在关键位置暂停
- **状态检查**：中间状态验证
- **异常捕获**：详细错误跟踪

#### 用途
- **算法验证**：确认算法正确性
- **问题排查**：复杂问题诊断
- **功能开发**：新功能测试

---

## 🔧 参考资源

### 相关文档
- **MNN precision参数详细说明**: `MNN_LLM_Benchmark_precision参数详细说明.md`
- **硬件支持信息详解**: `MNN_LLM_Benchmark硬件支持信息详解.md`
- **YAML配置实用指南**: `MNN_LLM_Benchmark_YAML配置实用指南.md`

### 工具链
- **MNN源码**: `~/mnn/transformers/llm/engine/phy_tools/llm_bench_prompt.cpp`
- **MNN LLM Bench**: `~/MNN_LLM_Benchmark/framework/`
- **示例代码**: `~/MNN_LLM_Benchmark/tasks/complex_sample_task.yaml`

---

**文档版本**: v1.0
**最后更新**: 2025年11月19日
**适用版本**: MNN LLM Bench 最新版
**维护者**: EAO基准测试项目团队