# MNN LLM Bench - MNN大语言模型基准测试框架

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![uv](https://img.shields.io/badge/uv-python%20manager-brightgreen.svg)](https://github.com/astral-sh/uv)

本项目是专门为MNN大语言模型推理框架设计的性能基准测试工具，提供自动化测试执行、数据收集和结果展示与分析功能。项目采用**Python配置驱动+命令行工具+批量编排**架构，专注于MNN LLM的性能评估和优化研究。

## 一、核心特性

### 1. 统一测试入口
- ✅ **统一测试脚本入口**: `bench.sh` 为主要命令行入口
- ✅ **批量基准测试编排**: 支持YAML配置的复杂基准测试场景
- ✅ **智能模型扫描**: 自动发现和添加新模型到配置文件
- ✅ **模型别名系统**: 简化多模型基准测试配置
- ✅ **彩色输出界面**: 清晰的基准测试状态和进度显示

### 2. 基准测试执行能力
- ✅ **单次基准测试**: 快速性能评估和指标收集
- ✅ **批量参数化基准测试**: 多变量组合测试场景
- ✅ **基准测试预览功能**: 执行前验证基准测试计划
- ✅ **错误处理机制**: 完善的异常捕获和重试

### 3. 数据管理能力
- ✅ **结构化数据存储**: JSON格式结果存储
- ✅ **数据库支持**: 集成SQLite数据库，支持复杂查询和数据分析
- ✅ **标准化记录**: 统一的结果类型(pp/tg/pp+tg)和参数格式
- ✅ **配置统一管理**: TOML格式的系统和模型配置
- ✅ **日志系统**: 多级别日志记录和查看
- ✅ **基准测试结果汇总**: 自动生成基准测试摘要信息

### 4. 系统可靠性
- ✅ **模块化设计**: 清晰的代码结构和职责分离
- ✅ **配置验证**: 参数有效性检查和错误提示
- ✅ **路径处理**: 智能路径扩展和验证
- ✅ **异常处理**: 完善的错误捕获和用户友好提示


## 二、快速开始

### 1. 环境要求

- **MNN工具链**: 已编译的`llm_bench`命令行工具
- **Python 3.12+**: 支持现代Python特性
- **uv包管理器**: 现代Python包管理工具
- **模型文件**: 配置好的MNN LLM模型

### 2. 基础环境配置

```bash
# 1. 安装uv包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用pipx安装
pipx install uv

# 2. 配置项目环境（使用项目配置）
cd mnn_llm_bench
uv sync  # 自动安装pyproject.toml中定义的依赖

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 验证环境 - 两种方式
uv run framework/benchmark.py --help
./bench.sh benchmark --help
```

### 3. Shell脚本入口

bench.sh提供更便利的shell接口：

```bash
# 查看帮助信息
./bench.sh benchmark --help    # 单次测试帮助
./bench.sh batch --help        # 批量测试帮助

# 智能模型扫描
./bench.sh benchmark --scan /data/models             # 添加模型别名到配置文件
./bench.sh benchmark --scan /data/models --overwrite # 用扫描结果覆盖模型配置文件

# 单次基准测试
./bench.sh benchmark qwen3_06b
./bench.sh benchmark qwen3_06b --threads 4 --precision 2

# 批量基准测试（正式开始前务必使用预览模式验证流程正确性）
./bench.sh batch --task verification_test.yaml --preview
./bench.sh batch --task verification_test.yaml
./bench.sh batch --create-sample  # 创建示例配置文件
```

### 4. python程序入口

#### 命令行方式
```bash
# 1. 查看可用的模型别名
ls config/models.toml
python framework/benchmark.py

# 2. 智能模型扫描 - 自动发现新模型
python framework/benchmark.py --scan /data/models
python framework/benchmark.py --scan /data/models --overwrite

# 3. 基础单次基准测试
python framework/benchmark.py qwen3_06b -t 4 -c 2 -rep 2

# 4. 批量基准测试 - 创建示例配置
python framework/benchmark.py --create-sample

# 5. 预览批量基准测试计划
python framework/benchmark.py -b tasks/sample_batch_task.yaml --preview

# 6. 执行批量基准测试
python framework/benchmark.py -b tasks/sample_batch_task.yaml
```


## 三、详细使用指南

### 1. 智能模型扫描

框架提供自动模型发现和配置功能，无需手动编辑配置文件：

```bash
# 基础扫描 - 自动发现并添加新模型
python framework/benchmark.py --scan /data/models

# 覆盖模式 - 更新已存在模型的别名
python framework/benchmark.py --scan /data/models --overwrite
```

#### 扫描特性

- **自动发现**: 批量扫描目录中所有包含 `config.json` 的模型
- **智能命名**: 根据目录名自动生成规范的别名
- **灵活配置**: 支持新建配置文件或追加到现有配置
- **重复检查**: 自动跳过已存在的别名，避免重复添加

#### 别名生成规则

原始目录名 → 批量化别名（只包含字母、数字、下划线）：

| 原始目录名 | 生成的别名 |
|-----------|----------|
| `Qwen3-0.6B-MNN` | `qwen3_0_6b_mnn` |
| `Qwen3-VL-2B-Instruct-MNN` | `qwen3_vl_2b_instruct_mnn` |
| `DeepSeek-R1-1.5B-Qwen-MNN` | `deepseek_r1_1_5b_qwen_mnn` |

#### 适用场景

```text
✅ 新机器上的模型批量导入
✅ 模型版本更新后的重新配置
✅ 团队间模型配置的标准化
✅ 快速验证模型可用性
```

### 2. 单次基准测试命令

```bash
# 基础基准测试
python framework/benchmark.py [模型别名] [参数]

# 常用参数:
# -t, --threads NUM         线程数 (1-16，建议物理核心数)
# -c, --precision NUM       精度 (0=Normal, 1=High, 2=Low)
# -p, --n-prompt NUM        预填充序列长度
# -n, --n-gen NUM           生成序列长度
# -rep, --n-repeat NUM      重复次数 (建议≥2)
# -kv, --kv-cache true|false KV缓存开关
# -mmp, --mmap 0|1         内存映射开关
# -dyo, --dynamicOption NUM 动态优化级别

# 示例:
python framework/benchmark.py qwen3_06b -t 4 -c 2 -rep 3 -kv true
python framework/benchmark.py deepseek_r1_15b -p 512 -n 256 -rep 2
```

### 3. 批量基准测试编排

#### Python CLI方式
```bash
# 1. 创建示例配置文件
python framework/benchmark.py --create-sample

# 2. 编辑配置文件（支持复杂参数组合）
vim tasks/sample_batch_task.yaml

# 3. 预览基准测试计划（不实际执行）
python framework/benchmark.py -b tasks/my_test.yaml --preview

# 4. 执行批量基准测试
python framework/benchmark.py -b tasks/my_test.yaml
```

#### Shell脚本方式（推荐）
```bash
# 1. 创建示例配置文件
./bench.sh benchmark --create-sample

# 2. 编辑配置文件
vim tasks/sample_batch_task.yaml

# 3. 预览基准测试计划（验证配置正确性）
./bench.sh batch --task my_test.yaml --preview

# 4. 执行批量基准测试
./bench.sh batch --task my_test.yaml
```

**推荐流程**: 使用`--preview`先验证测试计划，确认无误后再执行实际测试，避免耗时测试。

#### YAML配置示例

```yaml
task_name: "线程数对性能的影响基准测试"
description: "基准测试不同线程数和精度下的推理性能"
output_dir: "results/thread_scaling"

global_config:
  timeout: 300
  repeat: 2
  models: ["qwen3_06b", "qwen3_2b_vl"]

benchmark_suits:
  - suit_name: "thread_scaling"
    description: "线程数扩展性基准测试"
    variables:
      - name: "threads"
        start: 1
        end: 8
        step: 2
      - name: "precision"
        values: [0, 2]
    fixed_params:
      n_prompt: 256
      n_gen: 128
      kv_cache: "true"
```

### 4. 基准测试结果查看

```bash
# 基准测试结果保存在results/目录
ls results/
# 包含JSON格式的基准测试数据和汇总信息

# 查看批量测试结果目录结构（按模型分组）
ls results/任务名/时间戳/
├── json_results/          # JSON格式结果，按模型和套件分组
│   ├── qwen3_0_6b/       # 模型分组目录
│   │   ├── thread_test/  # 套件目录
│   │   │   ├── 1.json   # 用例结果文件
│   │   │   └── 2.json
│   │   └── sequence_test/
│   └── qwen3_1_7b/
└── raw_outputs/          # 原始输出文件，按模型和套件分组
    ├── qwen3_0_6b/       # 模型分组目录
    │   ├── thread_test/
    │   │   ├── 1_raw.txt   # 原始输出
    │   │   ├── 1_params.json # 执行参数
    │   │   └── 2_raw.txt
    │   └── sequence_test/
    └── qwen3_1_7b/

# 查看基准测试日志
tail -f framework/logs/benchmark.log

# 查看系统配置
cat config/system.toml
cat config/models.toml
```

## 四、数据库管理系统

### 1. 数据库结构设计

系统使用SQLite数据库存储基准测试结果，位于 `data/benchmark_results.db`。数据库采用关系型设计，支持复杂的测试结果查询和分析。

#### 核心表结构

**`benchmark_results`  - 基准测试结果表**
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `case_id` | INTEGER | 测试用例ID | 1 |
| `result_type` | TEXT | 结果类型 | `pp`, `tg`, `pp+tg` |
| `result_parameter` | TEXT | 结果参数 | `64`, `32`, `32,64` |
| `mean_value` | REAL | 平均性能值 | 327.85 |
| `std_value` | REAL | 标准差 | 4.00 |
| `unit` | TEXT | 单位 | `tokens/sec` |

**其他核心表**
- `tasks`: 测试任务定义和状态
- `suites`: 测试套件配置
- `case_definitions`: 测试用例定义
- `case_variable_values`: 测试变量值

### 2. 结果类型规范

#### 结果类型分类
- **`pp`**: 预填充（Prefill）测试，表示输入序列编码阶段
- **`tg`**: 令牌生成（Tokengenerate）测试，表示序列解码阶段
- **`pp+tg`**: 组合测试，用于prompt_gen参数生成的混合测试

#### 参数格式规范
- **`pp`类型**: 单个数字，表示预填充序列长度
  - 示例: `64`, `128`, `512`
- **`tg`类型**: 单个数字，表示生成长度
  - 示例: `32`, `64`, `128`
- **`pp+tg`类型**: 逗号分隔的两个数字，表示预填充和生成长度组合
  - 示例: `32,64`, `64,128`, `512,256`

### 3. 数据库约束设计

#### 唯一性约束
`UNIQUE(case_id, result_type, result_parameter)`

确保：
- 同一测试用例的同种结果类型不会记录重复参数
- 不同参数但相同类型的结果可以并存
- 支持复杂测试场景的数据完整性

### 4. 数据查询示例

#### 查看所有测试结果
```python
import sqlite3

conn = sqlite3.connect('data/benchmark_results.db')
cursor = conn.cursor()

# 查看最新的基准测试结果
cursor.execute("""
    SELECT
        rt.name as task_name,
        s.model_name,
        cd.name as case_name,
        br.result_type,
        br.result_parameter,
        br.mean_value,
        br.std_value
    FROM benchmark_results br
    JOIN case_definitions cd ON br.case_id = cd.id
    JOIN suites s ON cd.suite_id = s.id
    JOIN tasks rt ON s.task_id = rt.id
    ORDER BY br.created_at DESC
    LIMIT 10;
""")

for row in cursor.fetchall():
    print(f"任务: {row[0]}, 模型: {row[1]}, 类型: {row[2]}, 参数: {row[3]}, 性能: {row[4]:.2f}±{row[5]:.2f}")

conn.close()
```

#### 性能趋势分析
```sql
-- 查看特定模型的线程数性能趋势
SELECT
    cd.base_parameters,
    br.result_type,
    br.result_parameter,
    AVG(br.mean_value) as avg_performance,
    MIN(br.mean_value) as min_performance,
    MAX(br.mean_value) as max_performance
FROM benchmark_results br
JOIN case_definitions cd ON br.case_id = cd.id
JOIN suites s ON cd.suite_id = s.id
WHERE s.model_name = 'qwen3_0_6b'
  AND br.result_type = 'pp'
  AND json_extract(cd.base_parameters, '$.threads') IS NOT NULL
GROUP BY cd.base_parameters, br.result_type, br.result_parameter
ORDER BY avg_performance DESC;
```

#### 完整性检查
```sql
-- 检查结果记录完整性
SELECT
    COUNT(DISTINCT br.case_id) as total_cases,
    COUNT(DISTINCT br.result_type) as result_types,
    COUNT(*) as total_records,
    COUNT(CASE WHEN br.std_value > 0 THEN 1 END) as reliable_tests
FROM benchmark_results br;
```

### 5. 数据管理功能

#### 自动数据采集
- 批量测试执行时自动记录所有测试结果
- 支持重复测试的标准差计算
- 完整的参数组合记录和分析

#### 数据一致性
- 外键约束确保数据关联完整性
- 唯一约束避免重复记录
- 自动时间戳记录测试时间

#### 扩展性支持
- 模块化设计支持新的结果类型
- 灵活的参数格式适应未来需求
- 标准化接口便于数据分析

## 五、项目架构

### 1. 核心设计原则
- **模块化架构**: 清晰的功能分离和职责划分
- **命令行便利**: CLI工具提供完整的参数控制
- **批量编排**: YAML配置支持复杂的测试场景设计

### 2. 目录结构
```
mnn_llm_bench/
├── 🚪 入口层
│   ├── framework/benchmark.py          # 主CLI工具 ⭐
│   └── bench.sh                       # Shell脚本入口
├── 🏗️ 核心框架层
│   ├── benchmark/
│   │   ├── core/
│   │   │   └── executor.py            # MNN执行器核心
│   │   ├── single/
│   │   │   └── runner.py              # 单次测试业务逻辑
│   │   ├── batch/
│   │   │   ├── orchestrator.py        # 批量测试编排器
│   │   │   ├── tasks.py               # 任务配置管理
│   │   │   ├── cases.py               # 测试用例生成
│   │   │   └── results.py             # 结果聚合处理
│   │   └── __init__.py                # 导出控制
│   ├── config/
│   │   ├── system.py                  # 系统配置管理
│   │   ├── models.py                  # 模型配置管理和智能扫描
│   │   └── __init__.py                # 配置导出控制
│   └── utils/
│       ├── logger.py                  # 日志管理
│       ├── output.py                  # 彩色输出
│       ├── project.py                 # 项目路径管理
│       ├── exceptions.py              # 异常定义
│       └── __init__.py                # 工具导出控制
├── ⚙️ 配置系统
│   ├── config/
│   │   ├── models.toml               # 模型别名配置
│   │   └── system.toml               # 系统配置
│   └── tasks/                        # 批量基准测试任务配置
│       └── README.md                 # 任务配置说明
├── 🧪 质量保障
│   └── framework/tests/               # 单元基准测试
│       ├── unit/                     # 单元基准测试模块
│       └── run_unit_tests.py         # 基准测试运行器
├── 📊 结果输出
│   ├── results/                      # 基准测试结果存储
│   ├── data/                         # 数据库文件
│   └── logs/                         # 日志文件
├── 🔧 项目配置
│   ├── pyproject.toml                # uv项目配置
│   ├── uv.lock                       # 依赖锁定文件
│   └── .gitignore                    # Git忽略规则
└── 📚 文档
    ├── README.md                     # 项目说明
    ├── CLAUDE.md                     # 开发者指南
    ├── config/README.md              # 配置说明
    ├── tasks/README.md               # 任务配置说明
    └── framework/README.md           # 框架代码说明
```

## 六、设计原理

### 1. 模块化架构设计

```
framework/
├── benchmark/           # 基准测试模块
│   ├── batch/          # 批量测试子模块
│   │   ├── orchestrator.py  # 业务编排（流程统一）
│   │   ├── runner.py        # 任务执行器（预览控制点）
│   │   ├── cases.py         # 测试用例生成
│   │   ├── tasks.py         # 任务配置加载
│   │   └── results.py       # 结果管理
│   ├── core/           # 核心执行器
│   └── single/         # 单次测试子模块
├── config/            # 配置管理
└── utils/             # 工具和辅助模块
```
### 2. 预览模式架构设计

本框架采用**统一的执行流程**设计理念，预览模式和实际执行模式使用完全相同的工作流程，唯一的区别在于最终是否调用`llm_bench`命令。

#### 设计原则
1. **流程统一性**: 预览和实际执行使用相同的任务编排、结果管理和文件生成流程
2. **控制集中化**: 预览开关仅在最终执行层面控制，不污染其他业务逻辑
3. **代码简洁性**: 避免条件分支扩散，保持代码可维护性

#### 架构流程
```
TaskLoader加载配置 → CaseGenerator生成用例 → TaskRunner统一处理
                                     ↓
                              [预览模式检查]
                               ↙        ↘
                      [返回模拟结果]  [调用BenchExecutor]
                              ↓             ↓
                      其他流程完全一致（文件保存、日志记录等）
```

#### 核心实现
- **预览模式**: `TaskRunner.execute_batch_task()` 在不调用 `BenchExecutor` 的情况下返回模拟结果
- **执行模式**: 正常调用 `BenchExecutor` 进行实际的基准测试
- **统一接口**: 其他所有模块（编排器、结果管理、文件保存等）使用相同逻辑

#### 优势
- **测试简单**: 预览模式快速验证配置正确性（0.1秒内完成）
- **逻辑一致**: 减少维护复杂度，避免预览/执行双套逻辑
- **扩展友好**: 新功能自动支持预览和执行模式
- **资源节约**: 预览模式不消耗模型推理资源


## 七、配置系统详解

### 1. 系统配置 (`config/system.toml`)

```toml
[llm_bench]
# llm_bench可执行文件路径
default_path = "~/mnn/build/llm_bench"

[database]
# SQLite数据库路径和配置
path = "data/benchmark_results.db"
# 数据库所有表会自动创建，包括：tasks, suites, case_definitions, case_variable_values, benchmark_results
# 支持外键约束和唯一性约束，确保数据完整性

[execution]
# 测试执行配置
timeout = 300          # 超时时间（秒）
buffer_size = 1048576  # 缓冲区大小

[results]
# 结果输出配置
output_dir = "results"
csv_dir = "results/csv"
charts_dir = "results/charts"
html_dir = "results/html"

[logging]
# 日志配置
level = "INFO"
file = "logs/benchmark.log"
console = true
console_level = "ERROR"

[tasks]
# 批量测试配置
task_dir = "tasks"
file_pattern = "*.yaml"
sample_file = "tasks/sample_batch_task.yaml"
```

### 2. 模型配置 (`config/models.toml`)

```toml
[model_mapping]
# 模型别名 = config.json路径
# 注意：别名只支持字母、数字、下划线

# Qwen系列文本模型
qwen3_06b = "~/models/Qwen3-0.6B-MNN/config.json"

# Qwen系列视觉语言模型
qwen3_2b_vl = "~/models/Qwen3-VL-2B-Instruct-MNN/config.json"
qwen3_4b_vl = "~/models/Qwen3-VL-4B-Instruct-MNN/config.json"
qwen3_8b_vl = "~/models/Qwen3-VL-8B-Instruct-MNN/config.json"

# DeepSeek推理模型
deepseek_r1_15b = "~/models/DeepSeek-R1-1.5B-Qwen-MNN/config.json"
deepseek_r1_7b = "~/models/DeepSeek-R1-7B-Qwen-MNN/config.json"
```

## 八、支持的测试参数

### 1. 性能参数
| 参数 | 类型 | 范围/选项 | 说明 |
|------|------|-----------|------|
| `threads` | 整数 | 1-16 | 线程数，影响并行处理能力 |
| `precision` | 整数 | 0,1,2 | 精度模式：0=Normal, 1=High, 2=Low |
| `kv_cache` | 字符串 | "true","false" | KV缓存，显著影响生成速度 |
| `mmap` | 字符串 | "0","1" | 内存映射，大模型加载优化 |
| `dynamicOption` | 整数 | 0-8 | 动态优化级别 |

### 2. 序列参数
| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `n_prompt` | 整数 | 1-2048+ | 预填充序列长度 |
| `n_gen` | 整数 | 1-1024+ | 生成序列长度 |
| `prompt_gen` | 字符串 | "pp,tg" | 预填充和生成长度组合 |
| `n_repeat` | 整数 | 1-10 | 重复测试次数 |

## 九、MNN llm_bench 参数使用逻辑

### 1. 输出格式决定机制

MNN llm_bench工具具有两种完全不同的测试模式，由`kv_cache`参数决定输出格式和行为：

#### **模式1: 基准测试模式 (kv_cache=false)**
- **输出列**: `test` + `t/s`
- **测试行数**: 可变 (1-3行)
- **速度格式**: 单一速度值 (例: `623.34 ± 5.70`)
- **测试名称**: `pp512`, `tg128`, `pp32+tg16` 等
- **参数处理**: 处理所有输入参数组合

#### **模式2: 实际应用模式 (kv_cache=true)**
- **输出列**: `llm_demo` + `speed(tok/s)`
- **测试行数**: 固定1行
- **速度格式**: 双段速度 (例: `626.40 ± 10.03<br>54.53 ± 0.69`)
- **测试名称**: HTML格式 (例: `prompt=512<br>decode=128`)
- **参数处理**: 参数选择性行为，见下文详细说明

---

### 2. 参数组合行为详解

#### **p/n 参数组合**
```bash
# 基础序列长度测试
-p 64 -n 32
# 两种模式都会使用指定的p/n值
# kv=false: 输出两行 pp64, tg32
# kv=true: 输出一行 prompt=64<br>decode=32
```

#### **pg 参数组合**
```bash
# 组合序列长度测试
-pg 32,16
# kv=false: 输出三行 pp512, tg128 + 额外 pp32+tg16
# kv=true:  **参数完全无效**，输出使用默认值的一行 prompt=512<br>decode=128
# 原因：pg参数生成的测试实例强制设置kv=false，在kv=true模式下完全不执行
```

#### **p/n + pg 混合参数**
```bash
-p 64 -n 32 -pg 32,16 -kv false
# 输出三行: pp64, tg32 (p/n参数) + pp32+tg16 (pg参数)

-p 64 -n 32 -pg 32,16 -kv true
# 输出一行: prompt=64<br>decode=32 (只使用p/n参数，pg参数完全无效)
# 因为pg参数生成的测试实例被跳过，不执行
```

---

### 3. 参数影响矩阵

| 参数组合 | kv_cache=false | kv_cache=true |
|----------|----------------|---------------|
| **单p/n** | 2行: ppX+tgY (使用p/n参数) | 1行: prompt=X<br>decode=Y |
| **单pg** | 3行: 默认pp512+tg128 + ppX+tgY | 1行: 忽略pg，使用p/n默认值pp512+tg128 |
| **p+n+pg** | 3行: ppX+tgY (前两行) + ppY+tgZ (第三行) | 1行: 只使用p/n参数值 |

---

### 4. 主要参数效果

#### **序列长度参数**
- `-p X`: 生成`ppX`测试行 (预填充)
- `-n Y`: 生成`tgY`测试行 (生成)
- `-pg X,Y`: 生成额外`ppX+tgY`组合测试行

#### **KV缓存模式切换**
- `-kv false`: llama.cpp兼容模式，多行输出
- `-kv true`: 实际应用模式，单行输出，启用KV缓存优化

#### **输出格式细节**
- **test列**: 基准测试模式专用，显示测试类型
- **llm_demo列**: 实际应用模式专用，HTML格式显示参数
- **t/s列**: 单一速度值格式
- **speed(tok/s)列**: 双段速度格式 (prefill+decode分离)

---

### 5. 关键机制说明

1. **参数优先级**: `kv_cache`参数是最高优先级，决定整个测试模式和输出格式
2. **模式互斥**: 两种测试模式完全独立执行，不会同时运行
3. **参数选择性**: 实际应用模式下，`pg`参数会被忽略，只使用`p`和`n`参数
4. **多行测试**: 基准测试模式下，所有参数组合都会产生独立的测试行

## 十、开发和测试

### 1. 单元测试

```bash
# 运行所有单元测试
cd framework
python tests/run_unit_tests.py

# 使用pytest运行
python -m pytest tests/unit/

# 查看测试覆盖率（如果安装了pytest-cov）
python -m pytest tests/unit/ --cov=src
```

### 2. 调试模式

```bash
# 启用详细日志
# 修改config/system.toml:
[logging]
level = "DEBUG"
```

#### ⚡ 调试性能优化指南

**调试时避免使用耗时参数组合**：

| 参数组合 | 耗时程度 | 推荐值 | 不推荐值 |
|----------|----------|--------|----------|
| **线程数** | 高 | 1-2线程 | 4+线程 |
| **序列长度** | 极高 | p≤64, n≤32 | p≥256, n≥128 |
| **重复次数** | 中 | 1-2次 | ≥5次 |
| **精度模式** | 中 | Low(2) | High(1) |
| **KV缓存** | 低 | false(稳定) | true(复杂) |

**推荐的调试配置示例**：
```yaml
# 极速调试配置
variables:
  - name: "threads"
    values: [1]  # 单线程
  - name: "precision"
    values: [2] # 低精度
fixed_params:
  n_prompt: 64     # 短预填充
  n_gen: 32         # 短生成
  kv_cache: "false" # 稳定格式
  n_repeat: 1       # 最少重复
```

**耗时警告**：使用大参数组合(如p=512,n=128,threads=4)可能需要数分钟，强烈建议调试时使用小参数。

```bash
# 查看实时日志
tail -f framework/logs/benchmark.log
```

## 十一、 常见使用场景

### 场景1：新环境快速配置
```bash
# 1. 批量扫描发现所有可用模型
python framework/benchmark.py --scan /data/models

# 2. 快速验证模型可用性
python framework/benchmark.py qwen3_06b -t 4 -rep 2

# 3. 对比不同精度模式
python framework/benchmark.py qwen3_06b -c 0 -rep 2
python framework/benchmark.py qwen3_06b -c 1 -rep 2
python framework/benchmark.py qwen3_06b -c 2 -rep 2
```

### 场景2：基础性能评估
```bash
# 快速验证模型可用性
python framework/benchmark.py qwen3_06b -t 4 -rep 2

# 对比不同精度模式
python framework/benchmark.py qwen3_06b -c 0 -rep 2
python framework/benchmark.py qwen3_06b -c 1 -rep 2
python framework/benchmark.py qwen3_06b -c 2 -rep 2
```

### 场景3：参数优化研究
```bash
# 线程数优化测试
cat > tasks/thread_test.yaml << EOF
task_name: "线程数优化测试"
global_config:
  models: ["qwen3_06b"]
benchmark_suits:
  - suit_name: "thread_scaling"
    variables:
      - name: "threads"
        start: 1
        end: 8
        step: 1
    fixed_params:
      precision: 2
      n_prompt: 256
      n_gen: 128
EOF

python framework/benchmark.py -b tasks/thread_test.yaml --preview
python framework/benchmark.py -b tasks/thread_test.yaml
```

### 场景3：模型对比评估
```yaml
# tasks/model_comparison.yaml
task_name: "模型性能对比"
global_config:
  repeat: 3
benchmark_suits:
  - suit_name: "model_comparison"
    variables:
      - name: "precision"
        values: [0, 2]
    fixed_params:
      threads: 4
      n_prompt: 512
      n_gen: 256
    models: ["qwen3_06b", "qwen3_2b_vl", "deepseek_r1_15b"]
```

## 十二、故障排查

### 1. 常见问题

1. **扫描目录中没有模型**
   ```bash
   # 检查目录结构
   ls -la /data/models/*/
   # 确认每个模型目录都有config.json
   find /data/models -name "config.json"
   ```

2. **找不到llm_bench工具**
   ```bash
   # 检查工具路径
   ls ~/mnn/build/llm_bench
   # 或修改config/system.toml中的default_path
   ```

2. **模型别名未定义**
   ```bash
   # 查看可用别名
   grep -E "^[a-z]" config/models.toml
   # 或添加新模型配置
   ```

3. **权限问题**
   ```bash
   # 确保输出目录可写
   mkdir -p results logs data
   chmod 755 results logs data
   ```

4. **数据库问题**
   ```bash
   # 检查数据库文件权限
   ls -la data/benchmark_results.db
   # 确保data目录存在
   mkdir -p data

   # 验证数据库结构
   sqlite3 data/benchmark_results.db ".schema"

   # 测试数据库连接
   sqlite3 data/benchmark_results.db "SELECT name FROM sqlite_master WHERE type='table';"
   ```

5. **数据记录问题**
   ```bash
   # 检查最近的测试结果
   sqlite3 data/benchmark_results.db """
       SELECT
           result_type,
           result_parameter,
           mean_value,
           std_value
       FROM benchmark_results
       ORDER BY created_at DESC
       LIMIT 5;
   """

   # 检查数据完整性
   sqlite3 data/benchmark_results.db """
       SELECT
           COUNT(*) as total_records,
           COUNT(DISTINCT result_type) as types_count
       FROM benchmark_results;
   """
   ```

6. **Python环境问题**
   ```bash
   # 重新同步环境
   uv sync
   # 或重建虚拟环境
   rm -rf .venv && uv sync
   ```

### 2. 调试步骤

```bash
# 1. 检查系统状态
python framework/benchmark.py  #列出可用模型

# 2. 验证配置
python framework/benchmark.py --create-sample
python framework/benchmark.py -b tasks/sample_batch_task.yaml --preview

# 3. 查看日志
tail -f framework/logs/benchmark.log

# 4. 运行测试套件（⚠️ 调试时用小参数！）
# 好的调试示例：
python framework/benchmark.py qwen3_06b --threads 1 --precision 2

# ❌ 避免的调试参数（耗时极长）：
# --threads 4 --precision 1 （多线程+高精度）
# 使用耗时默认参数 p=512,n=128
```

**⚠️ 调试必看**：避免使用默认参数调试，推荐手动指定小参数：
```bash
# 推荐的调试参数组合示例
thread=1, precision=2, p≤64, n≤32, repeat=1
```

## 十三、技术栈

- **核心语言**: Python 3.12+
- **包管理**: uv (现代Python包管理器)
- **配置格式**: TOML (系统配置), YAML (任务配置)
- **数据处理**: pandas, numpy, psutil
- **MNN集成**: subprocess (MNN llm_bench工具)
- **可视化**: matplotlib, plotly (未来扩展)
- **测试**: pytest
- **日志**: Python logging + 彩色控制台输出
- **模型配置**: MNN模型文件动态路径管理

---

**MNN LLM Bench - 专业的MNN LLM性能基准测试工具** 

*为MNN大语言模型性能研究和优化提供完整的测试解决方案*