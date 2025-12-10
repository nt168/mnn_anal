# mnn_llm_t1_c2_kvfalse_mmap0_dyo0_pn_vp_pf

## 任务描述

固定 -t 1, -c 2, -kv false, -mmp 0, -dyo 0, -rep 3， 在 p∈[96..168], n∈[32..64] 下，分别测试： 1) -vp 0；2) -vp 1；3) 使用 -pf /home/phyer/mnn-tst/mnn_llm_benchmark/test_prompt.txt。


## 执行配置

| 配置项 | 值 |
|--------|-----|
| 超时时间 | 600秒 |
| 使用模型 | qwen3_06b, hunyuan_05b |

## 基准套件

### pn_grid_pf_file

**描述**: -t 1, -c 2, -kv false, -mmp 0, -dyo 0， 使用 -pf /home/phyer/mnn-tst/mnn_llm_benchmark/test_prompt.txt， 扫描同样的 p/n 网格。


**用例数量**: 100

**变量定义**:
- n_prompt: 96, 104, 112, 120, 128, 136, 144, 152, 160, 168
- n_gen: 32, 40, 48, 56, 64

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

*生成时间: 2025-11-27 18:34:45

