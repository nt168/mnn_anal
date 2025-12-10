# 提示词文件目录

本目录包含用于MNN LLM基准测试的多样化提示词文件，支持llm_bench_prompt的文件输入模式。

## 📁 目录说明

### 文件命名规范
- `en_xx.txt` - 英文提示词（xx表示token数量估计）
- `zh_xx.txt` - 中文提示词
- `code_xx.txt` - 代码相关提示词
- `special_*.txt` - 特殊用途提示词

### 使用方法

#### 基本用法
```bash
# 使用英文短提示词
~/mnn/build/llm_bench_prompt -m model.json -pf prompts/en_short.txt -p 8 -n 32

# 使用中文长提示词
~/mnn/build/llm_bench_prompt -m model.json -pf prompts/zh_long.txt -p 128 -n 64

# 使用代码提示词
~/mnn/build/llm_bench_prompt -m model.json -pf prompts/code_medium.txt -p 32 -n 128
```

#### 在YAML配置中使用
```yaml
fixed_params:
  prompt_file: prompts/en_short.txt
  n_prompt: 32
  n_gen: 64
```

## 📚 提示词类型

### 1. 基础提示词
- **en_short.txt**: 英文短句（约4-8 tokens）
- **en_medium.txt`: 英文段落（约16-32 tokens）
- **en_long.txt`: 英文长文本（约64-128 tokens）

### 2. 多语言支持
- **zh_short.txt`: 中文短句
- **zh_medium.txt`: 中文段落
- **es_medium.txt`: 西班牙语段落
- **fr_medium.txt`: 法语段落

### 3. 专业领域
- **code_python.txt`: Python代码提示词
- **code_js.txt`: JavaScript代码提示词
- **tech_ai.txt`: AI技术专业提示词
- **legal_simple.txt`: 法律简述提示词

### 4. 特殊格式
- **vl_standard.txt`: 视觉语言模型标准格式
- **conversation.txt`: 对话格式提示词
- **list_items.txt`: 列表格式提示词

## 🎯 最佳实践

### 选择合适的长度
- **测试性能**: 使用短提示词（4-16 tokens）
- **测负载能力**: 使用中等长度（32-64 tokens）
- **测准确性**: 使用长提示词（128+ tokens）

### 适配目标模型
- **小模型（<1B参数）**: 建议使用短到中等长度
- **中等模型（1-7B参数）**: 支持各种长度
- **大模型（>7B参数）**: 可处理复杂长文本

### 特殊用途
- **VL模型**: 使用vl_standard.txt格式
- **代码生成**: 使用合适的code_*.txt文件
- **多语言测试**: 选择对应语言的文件

## ⚙️ 自定义提示词

你可以在这里添加自己的提示词文件：

```bash
# 创建自定义提示词
echo "Your custom prompt text here." > prompts/custom.txt

# 在测试中使用
~/mnn/build/llm_bench_prompt -m model.json -pf prompts/custom.txt -p 16 -n 32
```

## 🔧 技术说明

- 所有文件默认使用UTF-8编码
- llm_bench_prompt会自动调整token长度以匹配指定参数
- 支持相对路径和绝对路径引用
- 文件内容会被token化处理，实际token数可能与文本字符数不同

---

💡 **提示**: 根据测试需求选择合适的提示词长度和语言，这样可以更准确地评估模型在各种场景下的表现。