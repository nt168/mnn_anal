# MNN LLM Stdio Backend

## 概述

MNN LLM Stdio Backend 是专为 MNN Transformer 框架设计的轻量级大语言模型后端服务，采用**三管道通信模型**提供高效的结构化交互。

## 核心特色

### 三管道通信架构

| 管道 | 方向 | 用途 | 数据格式 |
|------|------|------|----------|
| **stdin** | 输入 | JSON 请求 | `{"type":"chat","prompt":"..."}` |
| **stdout** | 输出 | LLM Token 流式输出 | `[LLM_STREAM_START]content[LLM_STREAM_END]` |
| **stderr** | 输出 | 状态控制消息 | OpenAI API 风格 JSON |

### 支持的请求类型

- **chat**: 聊天对话 `{"type":"chat","prompt":"问题内容"}`
- **system_prompt**: 系统提示词 `{"type":"system_prompt","content":"提示内容"}`
- **status**: 状态查询 `{"type":"status","id":"请求ID"}`
- **reset**: 重置对话 `{"type":"reset","id":"请求ID"}`
- **exit**: 退出程序 `{"type":"exit"}`

## 项目结构

```
mnn_llm_stdio/
├── include/llm_stdio_core.hpp    # 核心服务接口
├── src/llm_stdio_core.cpp        # 核心服务实现
├── backend/main.cpp              # 后端入口程序
├── python_demo/                  # Python客户端演示
│   ├── client.py                 # 核心客户端（重构优化版）
│   ├── demo.py                   # 统一演示入口
│   ├── demos/                    # 各种演示程序
│   │   ├── single_chat.py        # 单次对话演示
│   │   ├── batch_chat.py         # 批量对话演示
│   │   ├── interactive_chat.py   # 交互式对话演示
│   │   └── system_prompt_demo.py # 系统提示词演示
│   ├── tests/                    # 前端测试套件
│   │   ├── test_client.py        # 客户端单元测试
│   │   └── smoke_test.py         # 冒烟测试
│   └── test_newlines.py          # 换行处理测试
├── tests/                        # 后端测试
│   └── test_backend_simple.py    # 后端简单测试
├── run_tests.py                  # 统一测试运行器
├── CMakeLists.txt                # 编译配置
└── README.md                     # 项目说明
```

## 编译

在 MNN 根目录下执行：

```bash
mkdir build && cd build
cmake .. \
  -DMNN_LOW_MEMORY=true \
  -DMNN_BUILD_LLM=true \
  -DMNN_SUPPORT_TRANSFORMER_FUSE=true \
  -DMNN_OPENMP=true \
  -DMNN_USE_THREAD_POOL=true \
  -DMNN_BUILD_TOOLS=ON \
  -DBUILD_MLS=true

make mnn_llm_stdio_backend -j12
```

## 使用方法

### 基本使用

```bash
# 直接调用backend
./mnn_llm_stdio_backend /path/to/model/config.json

# 发送单个请求
echo '{"type":"chat","prompt":"你好"}' | ./mnn_llm_stdio_backend /path/to/model/config.json

# 运行Python演示
cd python_demo
python3 demo.py single --backend ../../mnn/build/mnn_llm_stdio_backend
```

### Python演示程序

Python演示程序提供了完整的功能演示和详细配置选项：

#### 快速开始
```bash
cd python_demo

# 基本演示（使用默认配置）
python3 demo.py single    # 单次对话
python3 demo.py batch     # 批量对话
python3 demo.py chat      # 交互式对话
```

#### 详细说明
完整的参数说明、配置选项和用法示例请参考：**`python_demo/README.md`**

该文档包含：
- 详细的命令行参数说明
- 配置文件使用方法
- 作为模块使用的示例
- 故障排除指南

#### 自定义参数示例
```bash
# 指定模型和后端路径
python3 demo.py single --model /path/to/model/config.json --backend /path/to/backend

# 使用自定义配置
python3 demo.py single --config custom_config.toml
```

### 系统提示词功能

支持设置系统提示词来定制AI角色的行为和风格：

```bash
# 方法1：在演示程序中设置
python3 demo.py single --system-prompt "你是一个专业的技术顾问，请用专业的语气回答。"

# 方法2：使用专门的系统提示词演示
python3 demos/system_prompt_demo.py --demo basic    # 基础演示
python3 demos/system_prompt_demo.py --demo complex  # 复杂演示
python3 demos/system_prompt_demo.py --demo all      # 所有演示
```

### 测试指南

项目提供了完整的测试套件来确保系统稳定性：

#### 快速测试
```bash
# 运行所有测试推荐使用统一测试运行器
python3 run_tests.py

# 只检查环境
python3 run_tests.py --check-only
```

#### 单独测试
```bash
# 前端测试
python3 python_demo/tests/smoke_test.py      # 冒烟测试
python3 python_demo/tests/test_client.py     # 单元测试

# 后端测试
python3 tests/test_backend_simple.py        # 后端简单测试

# 换行处理测试
python3 test_newlines.py                    # 换行符处理测试
```

#### 测试覆盖范围
- ✅ 基础功能：连接、对话、响应处理
- ✅ 高级功能：系统提示词、上下文管理、思考标签
- ✅ 格式处理：换行符保留、思考标签处理
- ✅ 性能和稳定性：多轮对话、超时处理
- ✅ 集成测试：frontend-backend完整交互

## 故障排除

1. **编译问题**: 检查MNN版本和依赖
2. **模型加载**: 验证模型路径和文件格式
3. **通信问题**: 检查JSON格式和管道连接
4. **权限问题**: 确保backend文件有执行权限
5. **测试失败**: 运行 `python3 run_tests.py --check-only` 检查环境
6. **换行问题**: 确保使用更新后的演示程序和客户端代码

## 优势

- **职责分离**: 三个独立管道各司其职，避免消息混淆
- **实时响应**: 流式输出支持实时显示
- **状态监控**: 结构化状态消息便于调试和监控
- **易于集成**: 标准JSON格式，支持多种客户端语言

---

**MNN LLM Stdio Backend** - 基于stdio的三管道通信架构，为 LLM 服务提供更清晰、更实时的交互体验。