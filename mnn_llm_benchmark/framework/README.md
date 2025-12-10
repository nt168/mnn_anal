# Framework 目录核心框架说明

本目录包含MNN LLM基准测试框架的核心Python实现代码，提供完整的测试自动化和数据收集功能。

## 📁 目录结构

```
framework/
├── benchmark.py            # 主入口程序，CLI工具
├── core/                   # 核心业务逻辑
│   ├── executor.py         # 基准测试执行器
│   └── orchestrator.py     # 批量测试编排器（待重新启用）
├── config/                 # 配置管理模块
│   ├── system.py           # 系统配置管理
│   └── models.py            # 模型配置管理
├── utils/                  # 工具函数
│   ├── logger.py           # 日志管理器（支持每日轮换）
│   ├── project.py          # 项目路径工具
│   ├── exceptions.py       # 异常定义
│   └── output.py           # 彩色输出工具
├── data/                   # 数据处理模块
│   └── processor.py        # 数据处理器实现
├── tests/                  # 测试套件
│   └── unit/               # 单元测试
└── __init__.py            # 包初始化文件
```

## 🔧 核心模块说明

### 主入口程序

#### `benchmark.py`
框架的主入口程序，提供命令行接口。

**主要功能：**
- 单次基准测试执行
- 批量测试编排和执行
- 示例配置文件生成
- 参数解析和验证

**使用方式：**
```bash
# 单次测试
python benchmark.py qwen3_06b -t 4 -c 2

# 批量测试
python benchmark.py -b ../tasks/thread_test.yaml
python benchmark.py --preview -b ../tasks/thread_test.yaml

# 创建示例
python benchmark.py --create-sample
```

### 核心模块

#### `config/system.py`
**系统配置管理器** - 统一管理所有系统参数。

**主要功能：**
- 加载和解析TOML配置文件 (`config/system.toml`)
- 提供配置访问接口
- 自动路径管理和绝对路径转换
- 默认值管理和配置验证

**配置文件：**
- `../config/system.toml`: 系统参数配置

#### `config/models.py`
**模型配置管理器** - 管理模型别名和路径。

**主要功能：**
- 加载模型配置 (`../config/models.toml`)
- 模型别名验证和路径解析
- 批量模型配置验证

#### `utils/logger.py`
**日志管理器** - 统一日志处理，支持**每日自动轮换**。

**特性：**
- **每日午夜自动轮换**：每天自动创建新的日志文件
- **多级别日志输出**：DEBUG, INFO, WARNING, ERROR, CRITICAL
- **文件和控制台双重输出**：文件记录所有级别，控制台仅显示ERROR级别
- **日志文件自动管理**：自动创建目录，保留7个备份文件
- **性能优化的日志记录**：按需记录，避免重复实例化

**日志轮换机制：**
- **轮换时间**：每天午夜（00:00）
- **文件命名**：`benchmark.log` (当前) → `benchmark.log.2025-11-08` (备份)
- **保留策略**：自动保留最近7天的日志文件
- **格式标准**：包含时间戳、模块名、级别和消息

**查看日志：**
```bash
# 查看当前日志
tail -f logs/benchmark.log

# 查看历史日志
ls -la logs/benchmark.log.*
```

#### `core/executor.py`
**基准测试执行器** - 执行单次MNN LLM基准测试。

**核心功能：**
- 调用MNN的llm_bench可执行文件
- 结果解析和数据收集
- JSON结构化结果生成
- 错误处理和性能指标提取

**工作流程：**
1. 验证模型别名和配置文件
2. 构建MNN benchmark命令
3. 执行基准测试并监控进程
4. 解析Markdown表格结果
5. 生成标准JSON输出

#### `core/orchestrator.py`
**批量测试编排器** - 管理复杂的批量测试任务（当前暂时禁用）。

**计划功能：**
- YAML任务文件解析
- 参数组合和测试计划生成
- 测试执行顺序管理
- 结果汇总和报告

#### `data/processor.py`
**数据处理器** - 处理和分析测试结果。

**处理能力：**
- JSON/CSV数据解析
- 性能指标计算
- 统计分析
- 数据格式转换

#### `utils/output.py`
**彩色输出工具** - 增强用户界面体验。

**输出功能：**
- 彩色状态输出
- 进度指示器
- 错误/成功高亮
- 表格化显示

#### `utils/project.py`
**项目路径工具** - 提供项目根目录识别和路径管理。

#### `utils/exceptions.py`
**异常定义** - 框架专用的异常类型。

## 🧪 测试框架

### 单元测试
位于`tests/unit/`目录，包含以下测试模块：
- `test_system.py`: 系统配置管理器测试
- `test_models.py`: 模型配置管理器测试
- `test_logger.py`: 日志管理器测试
- `test_exceptions.py`: 异常处理测试
- `test_output.py`: 输出工具测试
- `test_project.py`: 项目路径工具测试

### 运行测试
```bash
# 使用pytest运行单元测试
cd framework
python -m pytest tests/unit/ -v

# 运行特定测试模块
python -m pytest tests/unit/test_logger.py -v
```

## 📊 工作流程

### 单次测试流程
1. `benchmark.py` 解析命令行参数
2. `config/system.py` 加载系统配置
3. `config/models.py` 加载模型配置
4. `utils/logger.py` 初始化日志（支持轮换）
5. `core/executor.py` 执行单次测试
6. 解析结果并生成JSON输出
7. 保存到 `results/` 目录

### 批量测试流程（计划）
1. `benchmark.py` 解析YAML配置
2. `core/orchestrator.py` 规划测试计划
3. 依次调用 `core/executor.py` 执行各测试
4. 汇总所有结果
5. 生成综合报告

## 🎯 核心设计原则

### 模块化设计
- 每个模块职责单一，接口清晰
- 松耦合，便于单独测试和替换
- 配置与逻辑分离

### 可扩展性
- 支持新的测试参数和格式
- 插件化的结果处理器
- 灵活的配置系统

### 可靠性
- 完善的错误处理机制
- 详细的日志记录
- 全面的单元测试覆盖

### 用户友好
- 清晰的命令行界面
- 彩色输出和进度提示
- 详细的文档和示例

## 🔧 配置和依赖

### Python依赖
项目使用`uv`管理依赖，主要依赖：
- `pyyaml`: YAML解析
- `toml`: TOML配置解析
- `pandas`: 数据处理
- `matplotlib`: 图表生成
- `requests`: HTTP客户端
- `pytest`: 单元测试

### 系统要求
- Python 3.12+
- MNN LLM基准测试工具 (`llm_bench`)
- 足够的磁盘空间存储测试结果

## 🚀 开发指南

### 添加新功能模块
1. 在`src/`目录创建新模块文件
2. 实现相应的接口和类
3. 在`tests/unit/`添加单元测试
4. 更新相关文档

### 调试和排错
```bash
# 设置调试日志级别
# 在config/system.toml中设置：
[logging]
level = "DEBUG"
console = true
console_level = "DEBUG"

# 查看实时日志
tail -f ../logs/benchmark.log

# 查看历史日志
ls -la ../logs/benchmark.log.*

# 搜索特定错误
grep -i "error\|exception\|failed" ../logs/benchmark.log
```

## 📚 更多信息

- **项目总文档**: 见项目根目录README.md
- **配置说明**: 见`../config/README.md`
- **日志系统**: 见`../logs/README.md`
- **使用示例**: 见`../tasks/README.md`
- **API文档**: 见`docs/`目录（待完善）

## 📝 日志系统重要说明

框架使用**每日自动轮换**的日志系统，确保测试历史被妥善保存：

- **每日轮换**：每天午夜自动创建新日志文件
- **自动管理**：自动创建目录，清理过期文件
- **完整记录**：所有成功和失败的测试都被记录
- **标准格式**：统一的时间戳和日志级别

**配置位置**：`config/system.toml` → `[logging]`
**日志位置**：项目根目录 → `logs/`
**查看命令**：`tail -f logs/benchmark.log`

## 🤝 贡献指南

欢迎提交问题报告和功能请求。开发前请：
1. 运行现有单元测试确保环境正常
2. 遵循现有代码风格和模块结构
3. 为新功能添加相应的测试用例
4. 更新相关文档