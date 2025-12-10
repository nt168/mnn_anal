# MNN LLM Bench 基准测试工具总结

## 概述

MNN框架提供了两个主要的LLM基准测试工具：
- **llm_bench**: 原版基准测试工具
- **llm_bench_prompt**: 增强版基准测试工具（推荐）

本文档为EAO基准测试项目提供工具使用指南和最佳实践。

---

## 工具对比

### 工具基本信息

| 工具 | 路径 | 大小 | 特点 |
|------|------|------|------|
| `llm_bench` | `~/mnn/build/llm_bench` | 128KB | 原版工具，功能基础 |
| `llm_bench_prompt` | `~/mnn/build/llm_bench_prompt` | 142KB | 增强版，解决VL模型问题 |

### 功能对比

| 功能 | llm_bench | llm_bench_prompt |
|------|-----------|-----------------|
| 基础性能测试 | 支持 | 支持 |
| VL模型支持 | 不支持 (段错误) | 支持 (稳定运行) |
| 文件输入 | 不支持 | 支持 |
| 可变提示词 | 不支持 | 支持 |
| 详细调试模式 | 不支持 | 支持 |
| 向后兼容 | N/A | 支持 (100%兼容) |

---

## 核心功能详解

### 1. 基础性能测试

**测试指标**:
- **Prefill速度**: 首次提示处理速度 (tokens/s)
- **Decode速度**: 令牌生成速度 (tokens/s)  
- **总体速度**: 综合推理速度 (tokens/s)
- **加载时间**: 模型初始化时间 (s)
- **内存使用**: 模型内存占用 (MiB/GiB)

**测试模式**:
```bash
# llama.cpp标准测试
./llm_bench_prompt -m model.json -kv false -p 512    # 纯prompt测试
./llm_bench_prompt -m model.json -kv false -n 128    # 纯generate测试  
./llm_bench_prompt -m model.json -kv false -pg 512,128 # 组合测试

# MNN llm_demo标准测试
./llm_bench_prompt -m model.json -kv true -p 512 -n 128
```

### 2. VL模型专项支持

**问题解决**:
- **段错误修复**: VL模型(如Qwen3-VL-2B)100%稳定运行
- **Token精确控制**: 支持任意长度prompt测试
- **文件化输入**: 使用标准提示词文件避免编码问题

**推荐配置**:
```bash
# VL模型标准测试
echo -e "<|im_start|>user\n请介绍一下人工智能<|im_end|>" > vl_prompt.txt
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_prompt.txt -p 8 -n 32
```

### 3. 智能Token调整

**调整策略**:
- **截断**: 文件tokens > 目标长度 → 保留前N个
- **填充**: 文件tokens < 目标长度 → 循环重复填充
- **独立**: 不同测试使用独立调整，互不干扰

**示例**:
```bash
# 文件10tokens → 测试4tokens (截断)
echo "这是一个包含多个token的长文本内容" > long.txt
./llm_bench_prompt -m model.json -pf long.txt -p 4

# 文件4tokens → 测试15tokens (填充)  
echo "短文本" > short.txt
./llm_bench_prompt -m model.json -pf short.txt -p 15
```

---

## 参数详解

### 核心参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `-m, --model` | 模型配置文件路径 | `./Qwen2.5-1.5B-Instruct/config.json` | `/data/models/Qwen3-0.6B-MNN/config.json` |
| `-p, --n-prompt` | Prompt token数量 | 512 | `8, 16, 32, 64, 128, 256, 512` |
| `-n, --n-gen` | 生成token数量 | 128 | `32, 64, 128, 256, 512` |
| `-pg <pp,tg>` | 组合测试参数 | `0,0` | `512,128` |
| `-rep, --n-repeat` | 重复测试次数 | 5 | `3, 5, 10` |

### 新增参数（增强版）

| 参数 | 说明 | 默认值 | 用途 |
|------|------|--------|------|
| `-pf, --prompt-file` | 提示词文件路径 | none | VL模型、精确控制 |
| `-vp, --variable-prompt` | 可变提示词模式 | 0 | 多样化测试 |
| `-v, --verbose` | 详细输出模式 | 0 | 调试、验证 |

### 运行时参数

| 参数 | 说明 | 选项 | 影响 |
|------|------|------|------|
| `-a, --backends` | 计算后端 | cpu,metal,opencl | 性能、兼容性 |
| `-t, --threads` | 线程数 | 1,2,4,8 | 并行性能 |
| `-c, --precision` | 精度级别 | 0(High),1(Normal),2(Low) | 精度vs速度 |
| `-dyo, --dynamicOption` | 动态优化 | 0,8 | 内存vs性能 |
| `-mmp, --mmap` | 内存映射 | 0,1 | 加载速度 |
| `-kv, --kv-cache` | KV缓存模式 | true,false | 测试标准 |

---

## 输出格式

### 表格字段说明

| 字段 | 说明 | 示例值 |
|------|------|--------|
| `model` | 模型名称 | `Qwen3-0.6B-MNN` |
| `modelSize` | 模型大小 | `429.93 MiB` |
| `backend` | 后端类型 | `CPU`/`METAL`/`OPENCL` |
| `threads` | 线程数 | `4` |
| `precision` | 精度 | `Low`/`Normal`/`High` |
| `pType` | 提示词类型 | `fix`/`variable`/`file` |
| `test` | 测试类型 | `pp8`/`tg4`/`pp8+tg4` |
| `t/s` | 总体速度 | `260.99 ± 0.00` |
| `speed(tok/s)` | 分项速度 | `prefill ± std<br>decode ± std` |
| `loadingTime(s)` | 加载时间 | `1.23 ± 0.05` |

### pType字段详解

**优先级**: file > variable > fix

```bash
# file模式 (优先级最高)
./llm_bench_prompt -pf prompt.txt -p 8
# 输出: pType = file

# variable模式  
./llm_bench_prompt --variable-prompt 1 -p 8
# 输出: pType = variable

# fix模式 (默认)
./llm_bench_prompt -p 8  
# 输出: pType = fix
```

---

## EAO项目应用指南

### 阶段一：预备阶段

**可行性论证测试**:
- 验证基础功能：小规模参数组合测试
- VL模型专项验证：使用文件输入模式确保稳定性
- 参数可行性：确认关键参数的可用范围

**参数筛选测试**:
- 关键参数识别：通过小范围测试确定重要参数
- 参数敏感性：分析各参数对性能的影响程度
- 交互效应：初步发现参数间的相互影响

### 阶段二：初测阶段

**广泛参数测试**:
- 正交测试设计：系统性地覆盖参数空间
- 边界测试：确定参数的有效边界值
- 性能趋势：建立初步的性能变化规律

### 阶段三：详测阶段

**精确性能建模**:
- 精细参数测试：在关键范围内进行密集测试
- 多维度分析：考虑所有相关参数的组合效应
- 模型建立：构建精确的数学预测模型

### 阶段四：硅前阶段

**自动化测试脚本**:
- 标准化流程：建立可重复的测试流程
- 硅后验证：与实际硬件测试结果对比
- 模型校正：根据验证数据调整预测模型

---

## 最佳实践

### 1. 测试环境标准化

**模型路径规范**:
```bash
# 标准模型目录结构
/data/models/
├── Qwen3-0.6B-MNN/
│   ├── config.json
│   └── llm.mnn.weight
├── Qwen3-VL-2B-Instruct-MNN/
│   ├── config.json  
│   └── llm.mnn.weight
```

**测试文件管理**:
```bash
# 测试提示词文件
/prompts/
├── standard_prompt.txt    # 标准LLM提示词
├── vl_prompt.txt          # VL模型提示词
├── short_test.txt         # 短文本测试
└── long_test.txt          # 长文本测试
```

### 2. 测试结果管理

**文件命名规范**:
```bash
# 结果文件命名
results_{model}_{backend}_{precision}_{timestamp}.txt
# 示例: results_Qwen3-0.6B_CPU_Low_20251119_143022.txt
```

**数据收集流程**:
```bash
#!/bin/bash
# 标准测试流程示例
MODEL_PATH="<模型配置文件路径>"
DATE=$(date +%Y%m%d_%H%M%S)
OUTPUT="results/benchmark_${DATE}.txt"

# 创建输出目录
mkdir -p results

# 执行测试（根据实际需求调整参数）
./llm_bench_prompt -m $MODEL_PATH <测试参数> -fp $OUTPUT
```

### 3. 性能监控

**系统资源监控**:
```bash
# CPU和内存监控
htop -p $(pgrep llm_bench_prompt)

# 详细性能分析
perf stat -e cycles,instructions,cache-misses ./llm_bench_prompt -m model.json -p 512 -n 128
```

### 4. 故障排除

**常见问题解决**:

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| VL模型段错误 | 程序崩溃 | 使用 `llm_bench_prompt` + `-pf` 参数 |
| 输出乱码 | 显示问号 | 正常现象，不影响性能数据 |
| 内存不足 | 测试失败 | 降低 `-p`/`-n` 参数或使用 `-c 2` (Low精度) |
| 权限错误 | 无法访问模型 | 检查文件权限：`chmod 644 config.json` |

---

---

## 总结

MNN LLM Bench工具为EAO基准测试项目提供了强大的性能测试能力：

### 核心优势
1. **VL模型支持**: 解决了VL模型的稳定性问题
2. **精确控制**: 支持任意长度的精确token控制
3. **灵活输入**: 支持文件输入和可变提示词
4. **向后兼容**: 完全兼容原有测试流程
5. **丰富输出**: 详细的性能指标和调试信息

### 推荐使用策略
1. **工具选择**: 优先使用 `llm_bench_prompt` 作为主要测试工具
2. **VL模型**: 对于VL模型，必须使用文件输入模式 (`-pf` 参数) 确保稳定性
3. **标准化**: 建立统一的测试流程和文件管理规范
4. **参数优化**: 根据具体测试目标选择合适的参数组合
5. **自动化**: 结合脚本实现批量测试和系统化结果收集

通过合理使用这些工具，EAO项目能够建立准确、可重现的端侧AI推理性能基准模型。

---

**文档版本**: v1.0  
**更新时间**: 2025-11-19  
**适用项目**: EAO基准测试项目  
**维护者**: Gemini AI助手