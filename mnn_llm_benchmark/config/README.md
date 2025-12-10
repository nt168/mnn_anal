# Config 目录配置说明

本目录包含MNN LLM基准测试框架的所有配置文件。

## 📁 目录结构

```
config/
├── models.toml    # 模型配置文件
└── system.toml    # 系统配置文件
```

## 📄 配置文件说明

### models.toml
模型的别名配置文件，定义了模型别名到实际config.json路径的映射关系。

**功能特性：**
- 支持别名映射，便于命令行调用
- 支持路径扩展（~代表用户主目录）
- 支持多种模型系列配置

**配置格式：**
```toml
[model_mapping]
qwen3_06b = "~/models/Qwen3-0.6B-MNN/config.json"
qwen3_2b_vl = "~/models/Qwen3-VL-2B-Instruct-MNN/config.json"
deepseek_r1_15b = "~/models/DeepSeek-R1-1.5B-Qwen-MNN/config.json"
```

**注意事项：**
- 别名只支持字母、数字、下划线，不支持点号
- 路径使用绝对路径或~扩展
- 右边必须是对应的config.json实际路径

### system.toml
系统级别的配置参数文件，控制基准测试框架的行为。

**主要配置节：**

#### `[llm_bench]`
- `default_path`: 默认的llm_bench可执行文件路径

#### `[database]`
- `db_dir`: 数据库文件目录（相对于项目根目录）
- `db_file`: 数据库文件名

#### `[execution]`
- `timeout`: 测试执行超时时间（秒）
- `buffer_size`: 命令执行缓冲区大小

#### `[temp]`
- `temp_dir`: 临时文件根目录（相对于项目根目录）
- `auto_cleanup`: 是否在测试完成后清理临时文件

#### `[results]`
- `output_dir`: 结果输出根目录（相对于项目根目录）
- `csv_dir`: CSV文件存储目录
- `charts_dir`: 图表输出目录
- `html_dir`: HTML报告目录

#### `[model_config]`
- `config_dir`: 模型配置文件目录（相对于项目根目录）
- `config_file`: 模型配置文件名

#### `[logging]`
- `level`: 日志级别
- `log_dir`: 日志文件目录（相对于项目根目录）
- `log_file`: 日志文件名
- `console`: 是否在控制台输出
- `console_level`: 控制台日志级别

#### `[tasks]`
- `task_dir`: 批量测试任务配置文件目录（相对于项目根目录）
- `file_pattern`: 任务文件模式
- `sample_file`: 默认任务文件名

#### `[prompts]`
- `prompts_dir`: 提示词文件目录（相对于项目根目录）


## 🔧 配置使用

### 首次配置步骤

**重要：** 本项目中的配置文件是本地环境定制的，已从Git跟踪中排除。首次使用需要手动复制样例文件：

1. **配置系统设置：**
   ```bash
   cp config/system.example.toml config/system.toml
   ```
   然后编辑 `config/system.toml`，根据本地环境修改相关路径和参数（特别是 `llm_bench.path`）

2. **扫描生成模型配置：**
   ```bash
   python3 framework/benchmark.py --scan ~/models
   ```
   这将自动扫描 `~/models` 目录下的所有模型（期望结构：`*/config.json`），生成 `config/models.toml` 文件。

3. **验证配置：**
   ```bash
   python3 framework/benchmark.py
   ```
   显示可用模型列表，确认配置正确。

### 模型扫描功能

**自动扫描模型：**
```bash
# 扫描模型目录（跳过已存在的别名）
python3 framework/benchmark.py --scan ~/models

# 扫描并覆盖已存在的别名
python3 framework/benchmark.py --scan ~/models --overwrite
```

**扫描说明：**
- 扫描目录下的 `*/config.json` 文件
- 自动生成模型别名：目录名转换为小写，特殊字符替换为下划线
- 示例：`Qwen3-VL-2B-Instruct-MNN/` → `qwen3_vl_2b_instruct_mnn`
- 自动创建 `config/models.toml` 配置文件

### 添加新模型（手动方式）
如果需要手动添加模型，编辑生成的 `config/models.toml` 文件：
1. 在`[model_mapping]`节中添加新条目
2. 左边为命令行使用的别名（仅字母、数字、下划线）
3. 右边为对应的config.json实际路径

### 修改系统设置
编辑`system.toml`中对应的配置节，修改后重启基准测试工具即可生效。

### 路径配置注意事项
- 所有路径支持使用`~`扩展为用户主目录
- 相对路径相对于项目根目录
- 确保指定路径有相应的读写权限

## 📝 配置示例

详细的使用示例请参考项目根目录的README.md文件。