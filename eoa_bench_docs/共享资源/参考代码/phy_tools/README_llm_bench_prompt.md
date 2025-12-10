# LLM Bench Prompt - 增强版LLM性能测试工具

## 概述

`llm_bench_prompt` 是基于原始 `llm_bench` 的增强版本，专为大语言模型（LLM）提供精确的性能基准测试。

## 核心功能

### 解决VL模型段错误问题
- **问题**: VL模型（如Qwen3-VL-2B）在使用固定token时出现段错误
- **解决**: 强制使用文件输入 + MNN官方tokenizer
- **效果**: VL模型100%稳定运行，无段错误

### 智能Token调整
支持根据参数动态调整文件token长度：
- **截断**: 文件10tokens → 调整到p=4 → 保留前4个
- **填充**: 文件4tokens → 调整到p=15 → 循环重复填充
- **独立**: p测试和pg测试各自调整，互不干扰

### 精确性能测试
- 支持精确控制prompt长度（pp8, pp16, pp32等）
- 提供.statistics和性能指标
- 支持重复测试和标准差计算

## 使用方法

### 基本命令
```bash
# 传统方式（原版功能）
./llm_bench_prompt -m model_config.json

# 文件输入方式（推荐用于VL模型）
./llm_bench_prompt -m model_config.json -pf prompt.txt
```

### 最小化命令
```bash
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_prompt.txt -p 8 -n 32
```

## 文件输入模式

### 准备测试文件
```bash
# VL模型标准prompt
echo -e "<|im_start|>user\n请介绍一下人工智能的基本概念<|im_end|>" > vl_prompt.txt

# 普通文本测试
echo "What is artificial intelligence?" > en_prompt.txt
```

### 测试示例
```bash
# VL模型测试
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_prompt.txt -p 8

# 普通模型测试
./llm_bench_prompt -m /data/models/Qwen3-0.6B-MNN/config.json -pf en_prompt.txt -p 4
```

## 智能调整演示

### 截断测试（文件tokens > 目标长度）
```bash
# 文件10个tokens，但只测试4个
echo "这是一个包含多个token的长文本内容" > long.txt
./llm_bench_prompt -m model.json -pf long.txt -p 4 -v 1
# 结果：显示使用前4个tokens
```

### 填充测试（文件tokens < 目标长度）
```bash
# 文件4个tokens，但要测试15个
echo "短文本" > short.txt
./llm_bench_prompt -m model.json -pf short.txt -p 15 -v 1
# 结果：显示循环重复达到15个tokens
```

## 参数说明

### 核心参数
| 参数 | 说明 | 示例 |
|------|------|------|
| `-m, --model` | 模型配置文件 | `/data/models/Qwen3-VL-2B-Instruct-MNN/config.json` |
| `-pf, --prompt-file` | 提示词文件路径 | `prompt.txt` |
| `-p, --n-prompt` | Prompt token数量 | `8` |
| `-n, --n-gen` | 生成token数量 | `32` |
| `-rep, --n-repeat` | 重复测试次数 | `3` |
| `-v, --verbose` | 详细输出模式 | `1` |
| `-vp, --variable-prompt` | 可变提示词模式 | `1`（默认为0） |
| `-fp, --file-print` | 输出文件路径 | `results.txt`（默认为stdout） |

### 原有参数保持不变
所有原始 `llm_bench` 参数都保持不变，完全向后兼容。

## 输出表格字段说明

### 表格结构
输出采用 markdown 表格格式，包含以下字段：

| 字段 | 说明 | 示例值 |
|------|------|--------|
| `model` | 模型名称 | `Qwen3-0.6B-MNN` |
| `modelSize` | 模型文件大小 | `429.93 MiB` |
| `backend` | 后端类型 | `CPU` / `METAL` / `OPENCL` |
| `threads` | 线程数 | `4` |
| `precision` | 精度级别 | `Low` / `Normal` / `High` |
| `pType` | 提示词类型 | `fix` / `variable` / `file` |
| `test` | 测试类型 | `pp8` / `tg4` / `pp8+tg4` |
| `t/s` | 生成速度 | `260.99 ± 0.00` |
| `speed(tok/s)` | 分项速度 | `prefill ± std<br>decode ± std` |

### pType 字段详解
`pType` 字段显示了提示词的实际类型，优先级如下：

1. **file**：当指定 `--prompt-file` 参数时，使用文件内容作为提示词
2. **variable**：当使用 `--variable-prompt 1` 且未指定文件时，使用可变序列填充（20-39范围循环）
3. **fix**：默认行为，使用全16 token填充

#### 示例
```bash
# file 模式（优先级最高）
./llm_bench_prompt -pf prompt.txt -p 8
# 输出：pType = file

# variable 模式
./llm_bench_prompt --variable-prompt 1 -p 8
# 输出：pType = variable

# fix 模式（默认）
./llm_bench_prompt -p 8
# 输出：pType = fix
```

## 文件输出说明

### 追加模式
- **默认行为**：多次运行时会向文件末尾追加结果，不会覆盖原有内容
- **设计意图**：避免意外丢失之前的测试数据，支持累积对比
- **适用场景**：需要对比多次测试结果或记录测试历史

### 输出示例
```bash
# 第一次运行
./llm_bench_prompt -fp test_results.txt -p 8
# 文件内容：包含第一次的测试结果

# 第二次运行（相同参数）
./llm_bench_prompt -fp test_results.txt -p 8
# 文件内容：第一次结果 + 第二次结果（追加在末尾）
```

### 输出格式保持一致性
- **控制台输出**：和文件输出使用完全相同的表格格式
- **字段一致**：两种输出方式包含相同的字段和pType列
- **无格式差异**：便于结果的重现和对比

### 如需覆盖模式
如果希望每次运行时覆盖文件内容，请：
1. 手动删除现有文件，或
2. 在脚本中使用重定向：`rm test_results.txt && ./llm_bench_prompt -fp test_results.txt`

## Verbose 详细信息模式

### 功能描述
Verbose模式（`-v 1` 或 `--verbose 1`）提供详细的测试调试信息，但**不会影响文件输出**。

### 详细输出内容
启用verbose模式时，控制台会显示额外的调试信息：

```
=== Prompt Test Information ===
Test Mode: Fixed Prompt
Test Token: 16
File Input: Yes
File Length: 8
Original nPrompt: 16
Prompt Tokens Vector [size=8]: [16, 16, 16, 16, 16, 16, 16, 16]
Decode Token Count: 0
Note: Decode tokens are generated dynamically during inference
================================

=== Generated Content (Decode Tokens Decoded) ===
Decode Tokens [size=4]: [28361, 481, 220, 16]
Decoded Text:  Articles - 1
=====================================
```

### 输出分离机制

| 输出方式 | 不使用 `-v 1` | 使用 `-v 1` |
|----------|--------------|------------|
| **控制台输出** | 表格数据 + 设备信息 | 表格数据 + 调试信息 + 设备信息 |
| **文件输出** | 纯表格数据 | 纯表格数据（不变） |

### 调试信息包含

#### 1. Prompt Test Information
- **Test Mode**: 显示是 Fixed Prompt 还是 Variable Prompt
- **Test Token**: 主要测试token值
- **File Input**: 是否使用了文件输入
- **File Length**: 文件token数量（如使用文件）
- **Original nPrompt**: 原始prompt参数
- **Prompt Tokens Vector**: 实际使用的token向量（显示前5个和后5个）

#### 2. Generated Content (Decode Tokens Decoded)
- **Token序列**: 显示生成的token ID列表
- **解码文本**: 生成的实际文本内容
- **统计信息**: token总数和显示限制

### 使用场景

#### 启用 Verbose 模式
```bash
# 显示详细调试信息
./llm_bench_prompt -m model.json -p 8 -n 4 -v 1

# 同时输出到文件和控制台（文件干净无调试信息）
./llm_bench_prompt -m model.json -p 8 -n 4 -v 1 -fp results.txt
```

#### 关闭 Verbose 模式
```bash
# 只显示表格数据
./llm_bench_prompt -m model.json -p 8 -n 4

# 文件输出结果相同（没有调试信息）
./llm_bench_prompt -m model.json -p 8 -n 4 -fp results.txt
```

### 设计优势

#### 目标分离
- **调试输出**：开发者查看详细过程，理解测试行为
- **结果输出**：自动化处理，数据分析，性能对比
- **纯净报告**：便于与其他工具集成，无需额外清理

#### 数据一致性
- **格式稳定**：文件输出始终保持markdown表格格式
- **解析友好**：便于脚本处理，数据分析工具读取
- **版本控制**：减少文件内容变化，便于diff比较

#### 灵活性
- **开发调试**：启用verbose查看内部工作原理
- **生产使用**：关闭verbose获得干净的数据报告
- **自动化**：脚本可以忽略verbose开关，获得一致的文件格式

## VL模型专项指南

### 推荐用法
```bash
# 创建标准VL prompt文件
echo -e "<|im_start|>user\n请介绍一下人工智能<|im_end|>" > vl_standard.txt

# 性能基准测试
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_standard.txt -p 8 -n 32

# 不同长度对比
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_standard.txt -p 16 -n 64
./llm_bench_prompt -m /data/models/Qwen3-VL-2B-Instruct-MNN/config.json -pf vl_standard.txt -p 32 -n 128
```

### 已知限制
- **输出乱码**: VL模型在bench中运行稳定但输出为问号
- **不影响**: 性能测量数据完全准确
- **价值**: 仍可用于精确的性能基准测试

## 普通模型使用

```bash
# 标准LLM测试
./llm_bench_prompt -m /data/models/Qwen3-0.6B-MNN/config.json -p 512 -n 128 -rep 3

# 文件输入测试
echo "Artificial intelligence is..." > ai_prompt.txt
./llm_bench_prompt -m /data/models/Qwen3-0.6B-MNN/config.json -pf ai_prompt.txt -p 32 -n 64
```

## 性能测试示例

```bash
#!/bin/bash
MODEL_VL="/data/models/Qwen3-VL-2B-Instruct-MNN/config.json"
MODEL_STD="/data/models/Qwen3-0.6B-MNN/config.json"
PROMPT="vl_standard.txt"

echo "=== VL模型性能测试 ==="
./llm_bench_prompt -m $MODEL_VL -pf $PROMPT -p 8 -n 32
./llm_bench_prompt -m $MODEL_VL -pf $PROMPT -p 16 -n 64

echo "=== 标准模型对比测试 ==="
./llm_bench_prompt -m $MODEL_STD -p 512 -n 128
./llm_bench_prompt -m $MODEL_STD -p 256 -n 64
```

## 构建和安装

```bash
cd /home/xphi/mnn/build
make -j12 llm_bench_prompt
```

## 向后兼容性

所有原始 `llm_bench` 的功能完全保持：
- 不使用新功能时与原版100%一致
- 所有原有参数和功能都正常工作
- 输出格式与原版完全相同
- 新功能有条件启用

---

**llm_bench_prompt** 为LLM性能评估提供了强大的解决方案，特别是解决了VL模型的稳定运行问题，同时保持了精确的token控制能力。通过智能调整和文件输入，用户可以进行更贴近实际应用的性能测试。