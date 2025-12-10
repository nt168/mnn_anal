# mnn_llm_t1_param_sweep

## 任务描述

t=1 时，在固定 p=128, n=64 下，分别评估 dynamicOption/mmap/precision/kv_cache 对性能的影响

## 执行配置

| 配置项 | 值 |
|--------|-----|
| 超时时间 | 600秒 |
| 使用模型 | qwen3_06b, hunyuan_05b |

## 基准套件

### dynamic_option_effect_t1

**描述**: t=1, p=128, n=64, c=0, kv=false, mmap=0 时，dynamicOption 0-8 对性能的影响

**用例数量**: 18

**变量定义**:
- dynamicOption: 0, 1, 2, 3, 4, 5, 6, 7, 8

### mmap_effect_t1

**描述**: t=1, p=128, n=64, c=0, dyo=0, kv=false 时，mmap 0/1 对性能的影响

**用例数量**: 4

**变量定义**:
- mmap: 0, 1

### precision_effect_t1

**描述**: t=1, p=128, n=64, dyo=0, kv=false, mmap=0 时，precision 0/1/2 对性能的影响

**用例数量**: 6

**变量定义**:
- precision: 0, 1, 2

### kv_cache_effect_t1

**描述**: t=1, p=128, n=64, c=0, dyo=0, mmap=0 时，KV cache 开关对性能的影响

**用例数量**: 4

**变量定义**:
- kv_cache: false, true

## 目录结构

```
.
├── README.md             # 本文件，任务说明和计划
├── task_summary.json     # 任务执行摘要和统计
├── json_results/         # JSON格式结果，按模型和套件分组
│   └── [模型名称]/
│       └── [套件名称]/
│           └── [用例编号].json
└── raw_outputs/          # 原始输出文件和参数，按模型和套件分组
    └── [模型名称]/
        └── [套件名称]/
            ├── [用例编号]_raw.txt
            └── [用例编号]_params.json
```

## 结果查看

- **任务摘要**: 查看 `task_summary.json` 获取整体统计
- **用例结果**: `json_results/` 目录包含详细的JSON格式结果，按模型名称分组便于对比分析
- **原始输出**: `raw_outputs/` 目录包含MNN llm_bench的原始输出，按模型名称分组
- **执行参数**: `raw_outputs/*/[套件名称]/params.json` 包含每个用例的执行参数

**模型优先组织说明**: 目录采用"模型名称 → 套件名称 → 用例"的层级结构，便于进行同模型不同配置的对比分析和不同模型间的性能比较。

---

*生成时间: 2025-11-19 17:52:40

