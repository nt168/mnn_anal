# LLM Chat Tool - 流式对话与token分析工具

## 概述

`llm_chat_tool` 是一个专为大语言模型设计的流式对话和token分析工具。它提供了实时流式输出、详细的token分析、性能统计和多种输入模式，是开发和调试LLM应用的强大工具。

## 核心功能

### 1. 流式对话输出
- **实时生成**：逐token流式输出，实时显示模型思考过程
- **自然交互**：模拟真实对话体验，无需等待完整响应
- **中断控制**：支持随时中断生成过程

### 2. 详细token分析
- **编码分析**：显示输入文本的token化过程
- **解码显示**：展示每个token对应的文本内容
- **统计信息**：提供字符数、token数等详细统计

### 3. 多种输入模式
- **交互模式**：命令行交互式对话
- **直接输入**：命令行直接提供文本
- **文件输入**：从文件读取长文本内容

### 4. 性能分析
- **预填充统计**：prompt处理时间和速度
- **解码统计**：token生成时间和速度
- **综合性能**：完整的推理性能报告

## 使用方法

### 基本命令格式
```bash
./llm_chat_tool <config.json> [options] [text]
```

### 启动模式

#### 1. 交互模式（默认）
```bash
# 启动交互式对话
./llm_chat_tool ~/models/Qwen3-0.6B-MNN/config.json
```

#### 2. 直接文本模式
```bash
# 直接提供问题
./llm_chat_tool ~/models/Qwen3-0.6B-MNN/config.json "你好，请介绍一下自己"
```

#### 3. 文件输入模式
```bash
# 从文件读取内容
./llm_chat_tool ~/models/Qwen3-0.6B-MNN/config.json -f prompt.txt
```

### 功能选项

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `--token-only` | `-t` | 仅分析token，不进行LLM推理 | false |
| `--verbose` | `-v` | 显示详细的token分析信息 | false |
| `--file <path>` | `-f` | 从文件读取输入内容 | 无 |
| `--max-tokens <num>` | `-m` | 最大生成token数量 | 100 |
| `--help` | `-h` | 显示帮助信息 | 无 |

## 详细功能说明

### Token分析模式（`-t`/--token-only）

仅进行token分析，跳过LLM推理，适用于：
- Tokenizer调试
- 文本编码分析
- 性能对比测试

```bash
./llm_chat_tool config.json -t -v "Hello, 世界"
```

输出示例：
```
--- Token Analysis (Verbose) ---
Prompt: "Hello, 世界"
Token count: 7
Token array: [31373, 11, 19462, 71491, 13, 254, 12]

--- Detailed Token Breakdown ---
Index   Token           Decoded Text             UTF-8 Chars
-----   -----           -----------             -----------
0       31373           "Hello"                      5
1       11              ","                          1
2       19462           " "                          1
3       71491           "世"                         3
4       13              "界"                         3
5       254             " "                          1
6       12              ""                           0
```

### 详细输出模式（`-v`/--verbose）

提供完整的token信息和生成过程分析：

```bash
./llm_chat_tool config.json -v "什么是人工智能？"
```

包含信息：
- Token编码详情
- 生成的token序列
- 解码后的文本内容

### 文件输入模式（`-f/--file`）

支持长文本文件的内容分析和对话：

```bash
# 创建文本文件
echo "请详细解释机器学习的基本概念" > question.txt

# 使用文件输入
./llm_chat_tool config.json -f question.txt -v -m 200
```

### 控制生成长度（`-m/--max-tokens`）

精确控制生成内容的长度：

```bash
# 生成简短回答
./llm_chat_tool config.json "简单介绍一下MNN" -m 50

# 生成详细回答
./llm_chat_tool config.json "详细解释深度学习" -m 500
```

## 输出详解

### 标准输出
```
Loading LLM with config: /path/to/config.json
LLM loaded successfully!
Text from command line: 你的问题

--- LLM Streaming Response ---
====================
生成的回答内容...
====================

--- Inference Statistics ---
Prompt tokens: 15
Generated tokens: 42
Total tokens processed: 67
Prefill time: 124.5 ms
Prefill speed: 120.5 tokens/sec
Decode time: 2156.3 ms
Decode speed: 19.5 tokens/sec
```

### Verbose模式附加信息
```
--- Token Analysis (Verbose) ---
Prompt: "你的问题"
Token count: 8
Token array: [9931, 345, 1234, ...]

--- Generated Tokens ---
[0] Token 31373 → "我"
[1] Token 11 → "，"
[2] Token 19462 → "是"
[3] Token 71491 → "一"
...
```

## 性能指标说明

### 预填充阶段（Prefill）
- **Prefill tokens**: 输入prompt的token数量
- **Prefill time**: 处理prompt的时间（毫秒）
- **Prefill speed**: prompt处理速度（tokens/秒）

### 解码阶段（Decode）
- **Generated tokens**: 生成的新token数量
- **Decode time**: 生成token的总时间（毫秒）
- **Decode speed**: token生成速度（tokens/秒）

## 常见使用场景

### 1. Tokenizer调试
```bash
# 分析不同语言的token化效果
./llm_chat_tool config.json -t -v "Hello worlds"
./llm_chat_tool config.json -t -v "你好世界"
./llm_chat_tool config.json -t -v "こんにちは世界"
```

### 2. 性能基准测试
```bash
# 测试不同prompt长度的影响
./llm_chat_tool config.json -v -m 100 "短问题"
./llm_chat_tool config.json -v -m 100 "这是一个很长的prompt，包含了很多详细的信息和上下文背景..."
```

### 3. 应用开发调试
```bash
# 测试特定功能
./llm_chat_tool config.json -f user_query.txt -v -m 300

# 交互式开发
./llm_chat_tool config.json
```

### 4. 教学演示
```bash
# 展示LLM工作原理
./llm_chat_tool config.json -v "请用简单的语言解释什么是token"
```

## 示例脚本

### 批量性能测试
```bash
#!/bin/bash
MODEL="~/models/Qwen3-0.6B-MNN/config.json"

echo "=== 不同长度prompt性能对比 ==="

prompts=("短" "中等长度的prompt" "这是一个相当长的prompt，包含了大量的描述性内容和详细的背景信息")
for prompt in "${prompts[@]}"; do
    echo "测试: $prompt"
    ./llm_chat_tool $MODEL "$prompt" -m 50 -v | grep -E "(Prefill|Decode)"
    echo "---"
done
```

### 多语言token分析
```bash
#!/bin/bash
MODEL="~/models/Qwen3-0.6B-MNN/config.json"

echo "=== 多语言Token分析 ==="

texts=("English text" "中文文本" "日本語テキスト" "Русский текст")
for text in "${texts[@]}"; do
    echo "分析: $text"
    ./llm_chat_tool $MODEL -t -v "$text" | head -10
    echo "---"
done
```

### VL模型专项测试
```bash
#!/bin/bash
VL_MODEL="/data/models/Qwen3-VL-2B-Instruct-MNN/config.json"

echo "=== VL模型功能验证 ==="

# 1. 基础对话测试
echo "1. 基础对话:"
./llm_chat_tool $VL_MODEL "请介绍一下人工智能的基本概念" -v -m 50

# 2. 复杂问题测试
echo "2. 复杂问题:"
./llm_chat_tool $VL_MODEL "详细解释量子计算的工作原理和应用前景" -v -m 100

# 3. 输出质量验证
echo "3. 输出质量:"
python3 -c "
import subprocess, sys
result = subprocess.run(['./llm_chat_tool', '$VL_MODEL', '写一首关于春天的诗', '-m', '60'], capture_output=True, text=True)
output = result.stdout
chinese_chars = sum(1 for c in output if '\u4e00' <= c <= '\u9fff')
print(f'中文字符数: {chinese_chars}')
print(f'输出完整性: {"良好" if chinese_chars > 20 else "需要改进"}')
"
```

## 故障排除

### 常见问题

1. **模型加载失败**
   - 检查config.json路径是否正确
   - 确认模型文件完整性和权限

2. **编译错误**
   - 检查MNN依赖是否正确安装
   - 确认编译参数配置正确

3. **输出乱码**
   - 确认终端支持UTF-8编码
   - 检查模型tokenizer配置
   - VL模型：本工具通常输出正常，如遇乱码检查模型文件完整性

4. **性能缓慢**
   - 检查CPU线程数配置
   - 考虑使用不同的precision设置

### 调试建议

1. **逐步调试**：从token-only模式开始，逐步启用功能
2. **性能分析**：使用verbose模式获取详细统计
3. **对比测试**：使用相同输入对比不同配置

## 技术特性

### 实现特点
- **零拷贝设计**：高效的token处理
- **内存优化**：适合移动端和嵌入式环境
- **线程安全**：支持并发操作
- **错误处理**：完善的异常处理机制

### 兼容性
- **模型支持**：兼容所有MNN LLM格式模型，包括VL视觉语言模型
- **平台支持**：Linux/macOS/Windows
- **VL模型支持**：正确处理Qwen3-VL-2B等视觉语言模型
- **语言支持**：多语言Unicode支持

## 构建和安装

### 编译要求
- CMake 3.10+
- C++17编译器
- MNN框架依赖

### 编译命令
```bash
cd /home/xphi/mnn/build
make -j12 llm_chat_tool
```

### 验证安装
```bash
./llm_chat_tool --help
```

## API参考

虽然这是CLI工具，但其调用模式可以直接转换为API调用：

```cpp
// 示例API调用模式
Llm* llm = Llm::createLLM(config_path);
llm->load();
llm->response(prompt, &output_stream, nullptr, max_tokens);
```