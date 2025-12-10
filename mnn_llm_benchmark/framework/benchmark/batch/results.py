#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果管理器

专门负责：
- 测试结果的结构化存储
- 结果目录的创建和管理
- 任务摘要和报告生成
- README文档的生成
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from utils.logger import LoggerManager
from config.system import SystemConfig


class ResultManager:
    """基准测试结果管理器"""

    def __init__(self):
        """初始化结果管理器"""
        self.logger = LoggerManager.get_logger("ResultManager")
        self.system_config = SystemConfig()

    def create_result_directory(self, task_config: Dict[str, Any]) -> Path:
        """
        创建结果目录结构

        Args:
            task_config: 任务配置

        Returns:
            创建的任务目录路径
        """
        try:
            # 获取任务信息
            task_name = task_config.get('task_name', 'unknown_task')
            # 使用系统配置中的结果输出目录
            base_output_dir = self.system_config.get_results_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 创建目录结构
            task_dir = Path(base_output_dir) / task_name / timestamp

            # 创建子目录
            subdirs = [
                task_dir / "json_results",
                task_dir / "raw_outputs"
            ]

            for subdir in subdirs:
                subdir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"创建结果目录: {task_dir}")
            return task_dir

        except Exception as e:
            self.logger.error(f"创建结果目录失败: {e}")
            raise

    def save_case_result(self, task_dir: Path, case_num: int, suit_name: str,
                        case_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        保存单个测试用例的结果

        Args:
            task_dir: 任务目录
            case_num: 用例编号
            suit_name: 套件名称
            case_data: 用例数据
            result: 执行结果
        """
        try:
            suite_name_safe = suit_name.replace(" ", "_").replace("/", "_")

            # 保存JSON格式结果
            json_path = task_dir / "json_results" / suite_name_safe / f"{case_num}.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # 保存原始输出文件
            self._save_raw_output(task_dir, suite_name_safe, case_num, case_data, result)

            # 保存执行参数文件
            self._save_execution_params(task_dir, suite_name_safe, case_num, case_data)

        except Exception as e:
            self.logger.error(f"保存用例结果失败: {e}")

    def _save_raw_output(self, task_dir: Path, suit_name_safe: str, case_num: int,
                        case_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        保存原始输出文件

        Args:
            task_dir: 任务目录
            suit_name_safe: 安全的套件名称
            case_num: 用例编号
            case_data: 用例数据（预留字段，当前未使用但保留用于将来扩展）
            result: 执行结果
        """
        try:
            # 预留：case_data可能用于在将来版本中记录用例详细信息
            # 当前没有直接使用，但保留参数以维持接口兼容性
            _ = case_data  # 明确未使用但保留
            raw_path = task_dir / "raw_outputs" / suit_name_safe / f"{case_num}_raw.txt"
            raw_path.parent.mkdir(parents=True, exist_ok=True)

            if result.get('success') and result.get('execution_result'):
                # 从执行结果中获取临时文件
                temp_file = result['execution_result'].get('temp_output_file')
                if temp_file and Path(temp_file).exists():
                    # 复制临时文件内容
                    with open(temp_file, 'r', encoding='utf-8') as src:
                        content = src.read()
                    with open(raw_path, 'w', encoding='utf-8') as dst:
                        dst.write(content)
                else:
                    with open(raw_path, 'w', encoding='utf-8') as f:
                        f.write("无原始输出文件\n")
            else:
                # 执行失败的情况
                with open(raw_path, 'w', encoding='utf-8') as f:
                    f.write(f"基准测试执行失败\n\n错误信息: {result.get('error', '未知错误')}\n")

        except Exception as e:
            self.logger.warning(f"保存原始输出失败: {e}")

    def _save_execution_params(self, task_dir: Path, suit_name_safe: str,
                              case_num: int, case_data: Dict[str, Any]) -> None:
        """
        保存执行参数文件

        Args:
            task_dir: 任务目录
            suit_name_safe: 安全的套件名称
            case_num: 用例编号
            case_data: 用例数据
        """
        try:
            exec_path = task_dir / "raw_outputs" / suit_name_safe / f"{case_num}_params.json"
            exec_path.parent.mkdir(parents=True, exist_ok=True)

            with open(exec_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'execution_params': case_data['params'],
                    'global_config': case_data['global_config']
                }, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.warning(f"保存执行参数失败: {e}")

    def save_task_summary(self, task_dir: Path, task_config: Dict[str, Any],
                         results: List[Dict[str, Any]], execution_time: float = 0,
                         preview: bool = False) -> None:
        """
        保存任务执行摘要

        Args:
            task_dir: 任务目录
            task_config: 任务配置
            results: 结果列表
            execution_time: 执行时间（秒）
            preview: 是否为预览模式
        """
        try:
            summary_path = task_dir / "task_summary.json"

            # 计算统计信息
            total_cases = len(results)
            successful_cases = len([r for r in results if r.get('success', True)])
            failed_cases = total_cases - successful_cases

            # 按套件统计
            suit_stats = {}
            for result in results:
                suit_name = result.get('suit_name', 'unknown')
                if suit_name not in suit_stats:
                    suit_stats[suit_name] = {'total': 0, 'success': 0, 'failed': 0}
                suit_stats[suit_name]['total'] += 1
                if result.get('success', True):
                    suit_stats[suit_name]['success'] += 1
                else:
                    suit_stats[suit_name]['failed'] += 1

            # 构建摘要
            summary = {
                'task_info': {
                    'name': task_config.get('task_name'),
                    'description': task_config.get('description'),
                    'execution_time': execution_time,
                    'timestamp': datetime.now().isoformat(),
                    'preview_mode': preview
                },
                'statistics': {
                    'total_cases': total_cases,
                    'successful_cases': successful_cases,
                    'failed_cases': failed_cases,
                    'success_rate': f"{(successful_cases / total_cases * 100):.1f}%" if total_cases > 0 else "0%",
                    'note': '预览模式 - 未实际执行基准测试' if preview else '实际执行结果'
                },
                'suite_statistics': suit_stats,
                'models_used': task_config.get('global_config', {}).get('models', []),
                'configuration': task_config
            }

            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"任务摘要已保存: {summary_path}")

        except Exception as e:
            self.logger.error(f"保存任务摘要失败: {e}")

    def generate_task_readme(self, task_dir: Path, task_config: Dict[str, Any],
                           execution_plan: Dict[str, Any]) -> None:
        """
        生成任务README文件

        Args:
            task_dir: 任务目录
            task_config: 任务配置
            execution_plan: 执行计划
        """
        try:
            readme_path = task_dir / "README.md"

            # 生成README内容
            task_name = task_config.get('task_name', '未命名任务')
            description = task_config.get('description', '')

            content = f"""# {task_name}

## 任务描述

{description}

## 执行配置

| 配置项 | 值 |
|--------|-----|
| 超时时间 | {task_config.get('global_config', {}).get('timeout', 'default')}秒 |
| 使用模型 | {', '.join(task_config.get('global_config', {}).get('models', []))} |

## 基准套件

"""

            # 添加基准套件信息
            benchmark_suits = task_config.get('benchmark_suits', [])
            for suit in benchmark_suits:
                suit_name = suit.get('suit_name', '未命名套件')
                suit_desc = suit.get('description', '无描述')

                # 获取该套件的用例统计
                suit_cases_count = len([c for c in execution_plan.get('execution_plan', [])
                                      if c['suit_name'] == suit_name])

                content += f"""### {suit_name}

**描述**: {suit_desc}

**用例数量**: {suit_cases_count}

"""

                # 添加变量信息
                variables = suit.get('variables', [])
                if variables:
                    content += "**变量定义**:\n"
                    for var in variables:
                        var_name = var.get('name', '未知变量')
                        if 'values' in var:
                            values_str = ', '.join(map(str, var['values']))
                            content += f"- {var_name}: {values_str}\n"
                        elif 'start' in var and 'end' in var:
                            step = var.get('step', 1)
                            start, end = var['start'], var['end']
                            content += f"- {var_name}: {start} 到 {end} (步长: {step})\n"
                    content += "\n"

            # 添加目录结构说明
            content += """## 目录结构

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

*生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

"""

            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"任务README已生成: {readme_path}")

        except Exception as e:
            self.logger.error(f"生成README失败: {e}")