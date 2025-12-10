# MNN LLM Stdio Backend Demo 包

这是一个模块化的 Python 演示程序包，用于展示如何与 MNN LLM Stdio Backend 进行交互。

## 目录结构

```
python_demo/
├── __init__.py              # 包初始化文件
├── config.toml              # 配置文件
├── config_manager.py        # 配置管理模块
├── logger.py                # 日志记录模块
├── client.py                # 核心客户端模块（重构优化版）
├── color_output.py          # 彩色输出模块
├── context_manager.py       # 上下文管理模块
├── demo.py                  # 统一演示入口
├── example_commands.txt     # 示例命令文件
├── test_newlines.py         # 换行符处理测试
├── README.md                # 本文档
├── tests/                   # 测试套件
│   ├── test_client.py       # 客户端单元测试
│   └── smoke_test.py        # 冒烟测试
└── demos/                   # 各种演示程序
    ├── single_chat.py       # 单次对话演示
    ├── batch_chat.py        # 批量对话演示
    ├── interactive_chat.py  # 交互式对话演示
    └── system_prompt_demo.py # 系统提示词演示
```

## 模块说明

### 核心模块
- **`config_manager.py`**: 配置管理模块，提供统一的配置加载和管理功能
- **`logger.py`**: 提供统一的日志记录功能，支持文件和控制台输出
- **`client.py`**: LlmStdioClient 核心客户端实现，处理与 backend 的通信

**配置文件**
- **`config.toml`**: 主配置文件，包含所有演示程序的默认参数和设置

### 演示程序架构
每个演示程序都是独立的可执行文件，具有完整的参数解析和错误处理功能：

- **`demo.py`**: 统一的演示入口程序，可以调用所有演示模式
- **`demos/single_chat.py`**: 单次对话演示，执行一次对话后退出，支持系统提示词设置
- **`demos/batch_chat.py`**: 批量对话演示，从文件读取多个提示依次处理，支持批量执行
- **`demos/interactive_chat.py`**: 交互式对话演示，支持多轮对话和上下文管理
- **`demos/system_prompt_demo.py`**: 系统提示词专用演示，展示角色定制和提示词切换功能

## 快速开始

前提条件：
1. 编译生成 `mnn_llm_stdio_backend` 可执行文件
2. 准备好模型配置文件（如 `~/models/Qwen3-0.6B-MNN/config.json`）

### 使用统一入口

```bash
# 单次对话演示
python demo.py single --model ~/models/Qwen3-0.6B-MNN/config.json --prompt "你好，请介绍一下MNN框架"

# 批量对话演示
python demo.py batch --model ~/models/Qwen3-0.6B-MNN/config.json --file example_commands.txt

# 交互式对话演示
python demo.py chat --model ~/models/Qwen3-0.6B-MNN/config.json

# 查看帮助
python demo.py help
```

### 直接调用演示程序

```bash
# 单次对话
python demos/single_chat.py --backend ./mnn_llm_stdio_backend --model ~/models/Qwen3-0.6B-MNN/config.json --prompt "你好"

# 批量对话
python demos/batch_chat.py --backend ./mnn_llm_stdio_backend --model ~/models/Qwen3-0.6B-MNN/config.json --file example_commands.txt

# 交互式对话
python demos/interactive_chat.py --backend ./mnn_llm_stdio_backend --model ~/models/Qwen3-0.6B-MNN/config.json
```

### 作为模块使用

```python
from client import LlmStdioClient
import time

# 创建客户端
client = LlmStdioClient(backend_path="./mnn_llm_stdio_backend", model="~/models/Qwen3-0.6B-MNN/config.json")

# 启动客户端
if client.start():
    # 执行单次对话
    print("\n用户: 你好，请介绍一下你自己")
    print("AI: ", end="", flush=True)

    start_time = time.time()
    success = client.chat("你好，请介绍一下你自己")

    if success:
        elapsed = time.time() - start_time
        print(f"\n\n对话完成 (耗时: {elapsed:.2f}秒)")
        print(f"响应长度: {len(client.assistant_response)} 字符")

    # 停止客户端
    client.stop_backend()
```

## 配置文件

⚠️ **重要：本系统有两种配置文件，请区分清楚！**

### 1. 模型配置文件（Backend使用）
- **作用**: 配置 MNN LLM Backend 的运行参数
- **格式**: JSON（由 MNN 框架定义）
- **路径**: 通过 `--model` 参数指定
- **示例**: `~/models/Qwen3-0.6B-MNN/config.json`
- **内容**: 模型路径、精度配置、线程数、采样器等

### 2. 演示程序配置（Python Demo使用）
- **作用**: 配置 Python 演示程序的默认参数
- **格式**: TOML（推荐）或 JSON
- **路径**: 通过 `--config` 参数指定，或自动加载默认配置
- **示例**: `config.toml`、`config_demo.toml`
- **内容**: 默认路径、显示格式、日志设置等

---

## 演示程序配置详解

### [backend] 后端配置
- `default_backend_path`: 默认backend可执行文件路径
- `default_model_config`: 默认模型配置文件路径
- `init_timeout`: 后端初始化超时时间(秒)
- `response_timeout`: 响应超时时间(秒)

### [chat] 对话配置
- `default_prompt`: 默认单次对话提示语
- `default_batch_file`: 默认批量对话文件
- `max_tokens`: 最大生成token数
- `stream_output`: 是否启用流式输出

### [output] 输出配置
- `show_timing`: 是否显示耗时信息
- `show_response_length`: 是否显示响应长度
- `show_progress`: 是否显示进度信息

### [logging] 日志配置
- `log_file`: 日志文件路径
- `log_level`: 日志级别
- `enable_file_log`: 是否启用文件日志
- `enable_console_log`: 是否启用控制台日志

### [display] 显示配置
- `seperator_length`: 分隔线长度
- `time_precision`: 时间显示精度

## 命令行参数

所有演示程序都支持以下基础参数：

- `--backend`: backend 可执行文件路径（从**演示程序配置**读取默认值）
- `--model`: **模型配置**文件路径（从**演示程序配置**读取默认值）
- `--config`: **演示程序配置**文件路径（可选，默认自动加载）

**重要说明**:
- `--model` 参数指定的是**模型配置文件**（backend用的配置）
- `--config` 参数指定的是**演示程序配置**（不指定时自动加载默认配置）
- 命令行参数会覆盖相应配置文件中的对应设置

### 正确用法示例：

```bash
# 使用默认设置
python3 demo.py single

# 使用自定义演示程序配置
python3 demo.py single --config config_demo.toml

# 指定不同的模型配置
python3 demo.py single --model /path/to/other/model/config.json

# 指定自定义backend路径
python3 demo.py single --backend /path/to/custom/backend

# 组合使用多个参数
python3 demo.py single --config config_demo.toml --model /path/to/model.json
```

### 参数语义清晰对比：

| 参数 | 用途 | 示例 |
|------|------|------|
| `--backend` | 指定可执行文件路径 | `--backend ./my_backend` |
| `--model` | 指定模型配置文件 | `--model model.json` |
| `--config` | 指定演示程序配置 | `--config my_config.toml` |
| `--system-prompt` | 设置系统提示词 | `--system-prompt "你是技术顾问"` |

## 测试与验证

项目提供了完整的测试套件来确保系统稳定性：

### 快速测试
```bash
# 运行冒烟测试（验证基本功能）
python3 tests/smoke_test.py

# 运行单元测试
python3 tests/test_client.py
```

### 特定功能测试
```bash
# 测试系统提示词功能
python3 demos/system_prompt_demo.py --demo all

# 测试换行符处理
python3 test_newlines.py
```

### 测试覆盖范围
- ✅ 基础功能测试：连接、对话、响应处理
- ✅ 系统提示词测试：角色定制、提示词切换
- ✅ 上下文管理测试：多轮对话、历史记录
- ✅ 思考标签测试：标签处理、状态切换
- ✅ 格式处理测试：换行符保留、内容清理
- ✅ 性能测试：响应时间、timeout处理

### 模式特定参数

**单次对话模式 (single)**:
- `--prompt`: 对话提示语（默认: "你好，请介绍一下MNN框架"）

**批量对话模式 (batch)**:
- `--file`: 包含提示的文件路径，每行一个提示（默认: `example_commands.txt`）

**交互式对话模式 (chat)**:
- 无额外参数

## 配置文件格式

示例 `example_commands.txt` 文件格式：
```
你好，请介绍一下你自己
请简单介绍一下深度学习
什么是MNN框架？
请解释一下神经网络的工作原理
```

## 日志输出

程序生成 `mnn_llm_demo.log` 日志文件，包含运行信息。

## 故障排除

1. **Backend文件**: 确保 `mnn_llm_stdio_backend` 已编译
2. **配置文件**: 检查模型配置文件路径
3. **权限**: 确保backend文件有执行权限

## 许可证

本项目遵循 MNN 项目的许可证条款。
