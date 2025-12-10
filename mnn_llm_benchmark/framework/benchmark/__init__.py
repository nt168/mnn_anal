#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MNN LLM 基准测试模块 (重构版)

统一的基准测试入口，整合单次和批量基准测试功能。

模块结构：
- core/: 核心MNN执行器
- single/: 单次基准测试
- batch/: 批量基准测试

使用示例：
```python
# 单次基准测试
from benchmark.single import SingleBenchmark
benchmark = SingleBenchmark()
result = benchmark.run(model, **params)

# 批量基准测试
from benchmark.batch import BatchBenchmark
batch = BatchBenchmark()
result = batch.run_task(task_file, preview=False)
```
"""

from benchmark.core.executor import BenchExecutor

__all__ = [
    "BenchExecutor"
]