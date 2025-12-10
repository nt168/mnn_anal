# Tasks 目录批量测试配置说明

本目录用于存放MNN LLM基准测试的批量测试任务配置文件（YAML格式）。

## 📁 目录用途

`tasks/`目录是基准测试框架的批量测试任务存储区域，用于：
- 存放批量测试的YAML编排文件
- 组织和管理复杂的参数化测试场景
- 支持可重现的自动化测试流程

## 📄 配置文件格式

### YAML任务文件结构
```yaml
task_name: "测试任务名称"
description: "任务描述信息"
output_dir: "results/输出目录名"

global_config:
  timeout: 300              # 全局超时时间
  repeat: 2                # 重复测试次数
  models: ["model1", "model2"]  # 测试模型列表

test_suits:
  - suit_name: "测试套件1"
    description: "测试套件描述"
    variables:
      - name: "参数名"
        start: 起始值
        end: 结束值
        step: 步长
      - name: "参数名2"
        values: [值1, 值2]  # 离散值
    fixed_params:
      固定参数名: 固定参数值
```

## 🎯 支持的参数类型

### 变量参数（variables）
可以是以下两种类型之一：

#### 1. 范围型参数
```yaml
- name: "threads"
  start: 1
  end: 8
  step: 2  # 生成: 1, 3, 5, 7
```

#### 2. 枚举型参数
```yaml
- name: "precision"
  values: [0, 1, 2]  # 生成: 0, 1, 2
```

### 固定参数（fixed_params）
在测试套件中保持不变的参数：
```yaml
fixed_params:
  n_prompt: 256
  n_gen: 128
  kv_cache: "true"
```

## 📋 常用测试参数

### 性能相关参数
- `threads`: 线程数 (1-16)
- `precision`: 精度模式 (0=Normal, 1=High, 2=Low)
- `kv_cache`: KV缓存设置 ("true"/"false")
- `mmap`: 内存映射 ("0"/"1")
- `dynamicOption`: 动态优化选项 (0-8)

### 序列长度参数
- `n_prompt`: 预填充序列长度
- `n_gen`: 生成序列长度
- `prompt_gen`: 预填充和生成长度格式 (例: "256,128")

### 提示词参数（新增）
- `variable_prompt`: 可变提示词模式 (0或1)
- `prompt_file`: 提示词文件名 (仅文件名，不包含路径)

### 测试控制参数
- `n_repeat`: 重复测试次数
- `timeout`: 单次测试超时时间（秒）

## 🚀 使用示例

### 创建测试任务
```bash
# 创建示例配置文件
cd framework
python benchmark.py --create-sample

# 编辑生成的tasks/sample_batch_task.yaml文件
```

### 执行批量测试
```bash
# 预览测试计划（不实际执行）
python benchmark.py -b tasks/my_test.yaml --preview

# 实际执行批量测试
python benchmark.py -b tasks/my_test.yaml
```

## 📁 文件命名规范

建议使用有意义的文件名：
- `thread_scaling_test.yaml` - 线程扩展性测试
- `precision_comparison.yaml` - 精度对比测试
- `memory_pressure_test.yaml` - 内存压力测试
- `model_benchmark.yaml` - 模型基准测试

## ⚠️ 注意事项

1. **参数验证**: 确保所有参数在有效范围内
2. **路径配置**: output_dir路径需要存在写入权限
3. **模型可用性**: 确保配置的模型在models.toml中已定义
4. **测试时间**: 复杂的组合测试可能需要很长时间，建议先用preview模式检查
5. **资源监控**: 大规模测试时注意系统资源使用情况

## 🔄 任务文件生命周期

- **创建**: 根据测试需求编写YAML文件
- **预览**: 使用--preview参数验证测试计划
- **执行**: 运行批量测试生成结果
- **归档**: 测试完成后可根据需要保留或删除

## 📚 更多示例

### 提示词参数使用示例
```yaml
# 使用可变提示词模式
fixed_params:
  variable_prompt: 1
  prompt_file: "en_short.txt"

# 使用固定提示词模式
fixed_params:
  variable_prompt: 0
  prompt_file: "zh_medium.txt"

# 使用代码相关提示词
fixed_params:
  variable_prompt: 0
  prompt_file: "code_python.txt"
```

## 💡 提示词参数说明
- `variable_prompt`: 1表示使用可变提示词长度，0表示固定16 token
- `prompt_file`: **仅文件名**（不包含路径），系统会自动拼接完整的绝对路径
- 支持的文件类型详见 `prompts/README.md`

详细的使用方法和完整的配置示例请参考：
- `framework/benchmark.py` 中的`create_sample_yaml()`方法
- 项目根目录的README.md文件
- 系统配置文件 `config/system.toml`
- 提示词文件说明 `prompts/README.md`