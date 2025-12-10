# MNN LLM Benchmark precision参数详细说明

## 概述

本文档详细说明MNN LLM Benchmark工具中precision参数的具体含义，特别是在CPU后端上的物理意义和使用建议。

---

## 🔧 参数映射关系

### 源码映射逻辑

**位置**：`~/mnn/transformers/llm/engine/phy_tools/llm_bench_prompt.cpp` 第802行

```bash
-c, --precision <n> | Note: (0:Normal(for cpu bakend, 'Nornal' is 'High'),1:High,2:Low)
```

**位置**：`~/mnn/include/MNN/MNNForwardType.h` 第86行

```cpp
enum PrecisionMode {
    Precision_Normal = 0,
    Precision_High = 1,
    Precision_Low = 2,
    Precision_Low_BF16 = 3
};
```

### 配置字符串映射

**位置**：`llm_bench_prompt.cpp` 第1042-1047行

```cpp
std::map<int, std::string> lever = {{0,"normal"}, {1, "high"}, {2, "low"}};
setSuccess &= llmPtr->set_config("{\"precision\":\"" + lever[precision] + "\"}");
```

---

## 🎯 数值含义详解

| 参数值 | 字符串标识 | 在CPU后端的具体含义 | 物理意义 | 适用场景 |
|--------|------------|--------------------|----------|----------|
| **0** | `"normal"` | **Precision_Normal** | **最高精度**：FP32全精度计算 | 基准测试、科学研究 |
| **1** | `"high"` | **Precision_High** | **高精度**：FP32全精度计算 | 高质量推理 |
| **2** | `"low"` | **Precision_Low** | **低精度**：FP16半精度计算（硬件支持时） | 性能优化、实时推理 |

---

## 🤔 CPU后端的特殊性

### 关键特性

**注意**：文档中明确提到 `for cpu bakend, 'Normal' is 'High'`

#### 具体含义：
- **CPU后端下**：`precision=0 (normal)` 实际等同于 `High` 精度
- **技术原因**：CPU后端不像GPU专用硬件有低精度加速单元，CPU的"Normal"和"High"都使用FP32全精度计算
- **实际差异**：只有在硬件支持FP16且后端启用时，`precision=2 (low)`才会真正使用FP16进行计算加速

#### 硬件支持检查

**位置**：`~/mnn/source/backend/cpu/CPUBackend.cpp`

```cpp
if (core->supportFp16arith && precision == BackendConfig::Precision_Low) {
    // 启用FP16计算路径
    // 实际使用FP16进行运算
}
```

---

## 💡 实际使用建议

### EAO基准测试推荐配置

```yaml
# 标准基准测试（推荐）
fixed_params:
  precision: 0  # FP32全精度，确保结果准确性和可重复性

# 高质量推理测试
fixed_params:
  precision: 1  # 与0相同，但语义更明确为高精度

# 性能优化测试
fixed_params:
  precision: 2  # FP16半精度，需评估硬件支持情况
```

### 不同使用场景选择

#### 🎯 **科学基准测试**
- **推荐**：`precision: 0`
- **理由**：最高精度，结果可重现性强，符合科学测试标准

#### ⚡ **实时推理优化**
- **选项**：`precision: 2`
- **条件**：硬件支持FP16，可接受轻微精度损失
- **收益**：通常会有20-40%的性能提升

#### 🔬 **模型研发验证**
- **选择**：`precision: 1`
- **用途**：平衡精度和性能的标准选择

---

## 📊 性能与精度权衡

| 配置 | 计算精度 | 内存占用 | 执行速度 | 适用后端 |
|------|----------|----------|----------|----------|
| `precision: 0` | FP32 (32-bit) | 基准 | 基准 | CPU/Metal/OpenCL |
| `precision: 1` | FP32 (32-bit) | 基准 | 基准 | CPU/Metal/OpenCL |
| `precision: 2` | FP16 (16-bit) | ~50% | +20-40% | 支持FP16的后端 |

---

## 🔍 代码验证路径

### 1. 参数解析验证
```bash
# 测试不同precision值实际对应的字符串
./llm_bench_prompt -m config.json -c 0  # 应调用 "normal"
./llm_bench_prompt -m config.json -c 1  # 应调用 "high"
./llm_bench_prompt -m config.json -c 2  # 应调用 "low"
```

### 2. 硬件支持检查
```cpp
// 检查CPU是否支持FP16
bool supportFP16 = MNNGetCoreFunctions()->supportFp16arith;
```

### 3. 输出格式验证
工具输出的表格中，precision列会显示：
- `precision: 0` → 显示 "Normal"
- `precision: 1` → 显示 "High"
- `precision: 2` → 显示 "Low"

---

## 📋 EAO项目特殊说明

### 基准测试标准化
为确保EAO基准测试结果的科学性和可重复性：

1. **主基准测试**：统一使用 `precision: 0`
2. **性能验证测试**：可使用 `precision: 2` 评估性能上限
3. **交叉对比测试**：比较 `precision: 0` vs `precision: 2` 的精度损失

### 配置文件模板

```yaml
# EAO标准基准测试配置
global_config:
  models: ["qwen3_0_6b"]
  timeout: 1200

benchmark_suits:
- suit_name: "standard_baseline"
  description: "EAO标准FP32全精度基准测试"
  variables:
  - name: threads
    values: [4]
  fixed_params:
    precision: 0        # FP32全精度，标准配置
    n_repeat: 10
    n_prompt: 128
    n_gen: 64
    kv_cache: "true"

- suit_name: "performance_optimized"
  description: "FP16优化性能测试（硬件允许时）"
  variables:
  - name: threads
    values: [4]
  fixed_params:
    precision: 2        # FP16半精度，性能优化
    n_repeat: 10
    n_prompt: 128
    n_gen: 64
    kv_cache: "true"
```

---

## 🔗 相关源码位置

- **参数解析**：`~/mnn/transformers/llm/engine/phy_tools/llm_bench_prompt.cpp:802`
- **配置映射**：`~/mnn/transformers/llm/engine/phy_tools/llm_bench_prompt.cpp:1042-1047`
- **枚举定义**：`~/mnn/include/MNN/MNNForwardType.h:86`
- **CPU后端处理**：`~/mnn/source/backend/cpu/CPUBackend.cpp`
- **精度检查**：`~/mnn/source/backend/cpu/CPUBackend.cpp`

---

**文档版本**: v1.0
**最后更新**: 2025年11月19日
**适用版本**: MNN LLM Benchmark
**维护者**: EAO基准测试项目团队