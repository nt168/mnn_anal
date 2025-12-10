#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量基准测试业务逻辑模块（重构版）

整合各个子模块，提供统一的批量基准测试接口。

原版本716行代码重构为模块化结构：
- TaskLoader: 任务文件加载和验证
- CaseGenerator: 测试用例生成
- TaskRunner: 任务执行管理
- ResultManager: 结果管理

此模块专注于业务流程编排，具体的实现细节委托给专门的子模块。
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import time
import yaml

from benchmark.batch.tasks import TaskLoader
from benchmark.batch.cases import CaseGenerator
from benchmark.batch.runner import TaskRunner
from benchmark.batch.results import ResultManager
from utils.logger import LoggerManager
from config.system import SystemConfig
from config.models import ModelsConfig
from utils.output import ColorOutput

# 数据库导入
from utils.db_manager import DatabaseManager


class BatchBenchmark:
    """批量基准测试业务逻辑处理器（重构版）"""

    def __init__(self):
        """初始化批量基准测试处理器"""
        self.logger = LoggerManager.get_logger("BatchBenchmark")
        self.system_config = SystemConfig()

        # 初始化子模块
        self.task_loader = TaskLoader()
        self.case_generator = CaseGenerator()
        self.task_runner = TaskRunner()
        self.result_manager = ResultManager()

        # 数据库管理器
        try:
            self.db_manager = DatabaseManager()
            self.logger.info("数据库管理器初始化成功")
        except Exception as e:
            self.logger.error(f"数据库管理器初始化失败: {e}")
            self.db_manager = None

    def create_sample_yaml(self, output_path: Optional[str] = None) -> str:
        """
        创建示例YAML任务文件（简单和复杂两个版本）

        Args:
            output_path: 输出路径，如果不指定则使用默认路径

        Returns:
            创建的文件路径（返回简单样例文件路径）
        """
        tasks_dir = self.system_config.get_tasks_dir()
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # 创建简单样例文件
        simple_path = tasks_dir / "simple_sample_task.yaml"
        simple_config = self._create_simple_sample_config()
        simple_config = self._create_well_ordered_config(simple_config)

        with open(simple_path, 'w', encoding='utf-8') as f:
            yaml.dump(simple_config, f, default_flow_style=False,
                     allow_unicode=True, sort_keys=False, indent=2)

        # 创建复杂样例文件
        complex_path = tasks_dir / "complex_sample_task.yaml"
        complex_config = self._create_complex_sample_config()
        complex_config = self._create_well_ordered_config(complex_config)

        with open(complex_path, 'w', encoding='utf-8') as f:
            yaml.dump(complex_config, f, default_flow_style=False,
                     allow_unicode=True, sort_keys=False, indent=2)

        self.logger.info(f"已创建简单样例文件: {simple_path}")
        self.logger.info(f"已创建复杂样例文件: {complex_path}")
        return str(simple_path)

    def _create_simple_sample_config(self) -> dict:
        """创建简单样例配置"""
        return {
            "task_name": "简单基准测试样例",
            "description": "只含有单个套件的简单测试样例，会对指定的模型依次运行。包含VL模型必需的提示词文件参数。",
            "global_config": {
                "timeout": 300,
                "models": ["qwen3_0_6b", "qwen3_2b_vl"]
            },
            "benchmark_suits": [
                {
                    "suit_name": "thread_scaling",
                    "description": "线程数扩展性基准测试，VL模型使用专用提示词文件",
                    "variables": [
                        {
                            "name": "threads",
                            "start": 1,
                            "end": 8,
                            "step": 2
                        },
                        {
                            "name": "precision",
                            "values": [0, 2]
                        }
                    ],
                    "fixed_params": {
                        "n_prompt": 256,
                        "n_gen": 128,
                        "kv_cache": "true",
                        "prompt_file": "vl_standard.txt"
                    }
                }
            ]
        }

    def _create_complex_sample_config(self) -> dict:
        """创建复杂样例配置"""
        return {
            "task_name": "复杂综合基准测试样例",
            "description": "包含多个模型和套件的综合基准测试，涵盖pp+tg组合、步进增长、提示词文件使用和固定参数等多个场景",
            "global_config": {
                "timeout": 600,
                "models": ["qwen3_0_6b", "deepseek_r1_1_5b"]
            },
            "benchmark_suits": [
                {
                    "suit_name": "prompt_file_test",
                    "description": "提示词文件测试，分别测试4种不同提示词的效果",
                    "variables": [
                        {
                            "name": "prompt_file",
                            "description": "不同的文件名",
                            "values": ["code_js.txt", "zh_short.txt", "en_medium.txt", "code_js.txt"]
                        }
                    ],
                    "fixed_params": {
                        "threads": 8,
                        "n_prompt": 128,
                        "n_gen": 128,
                        "prompt_gen": "64,32",
                        "variable_prompt": 0,
                        "n_repeat": 3
                    }
                },
                {
                    "suit_name": "pg_combination_test",
                    "description": "测试prompt_gen参数组合，验证pp+tg结果采集",
                    "variables": [
                        {
                            "name": "prompt_gen",
                            "description": "PG参数组合测试（会产生pp+tg结果）",
                            "values": ["32,16", "32,32", "64,16", "64,32"]
                        }
                    ],
                    "fixed_params": {
                        "threads": 8,
                        "n_repeat": 3
                    }
                },
                {
                    "suit_name": "sequence_step_scaling",
                    "description": "使用step方法测试序列长度对性能的影响",
                    "variables": [
                        {
                            "name": "n_prompt",
                            "description": "输入序列长度 - step增长",
                            "start": 64,
                            "end": 256,
                            "step": 32
                        },
                        {
                            "name": "n_gen",
                            "description": "生成长度 - 配套step增长",
                            "start": 64,
                            "end": 128,
                            "step": 16
                        }
                    ],
                    "fixed_params": {
                        "threads": 8,
                        "n_repeat": 5
                    }
                },
                {
                    "suit_name": "thread_step_performance",
                    "description": "step方法测试线程数对性能的影响",
                    "variables": [
                        {
                            "name": "threads",
                            "description": "线程数step增长测试",
                            "start": 1,
                            "end": 8,
                            "step": 2
                        }
                    ],
                    "fixed_params": {
                        "n_prompt": 16,
                        "n_gen": 8,
                        "n_repeat": 1
                    }
                },
                {
                    "suit_name": "kv_cache_impact",
                    "description": "测试是否使用KV缓存带来的影响",
                    "variables": [
                        {
                            "name": "kv_cache",
                            "description": "KV缓存启用或者关闭",
                            "values": ["true", "false"]
                        }
                    ],
                    "fixed_params": {
                        "threads": 8,
                        "n_prompt": 16,
                        "n_gen": 8,
                        "prompt_gen": "8,8"
                    }
                },
                {
                    "suit_name": "extreme_performance",
                    "description": "极小序列的极致性能测试，单一配置验证",
                    "fixed_params": {
                        "threads": 8,
                        "precision": 2,
                        "n_prompt": 8,
                        "n_gen": 4,
                        "n_repeat": 1
                    }
                }
            ]
        }

    def _create_well_ordered_config(self, config) -> dict:
        """
        重新构建配置，确保YAML输出字段顺序正确（使用普通字典保持插入顺序）

        Args:
            config: 原始配置字典

        Returns:
            字段顺序正确的配置字典
        """
        # Python 3.7+ 字典保持插入顺序，直接用普通字典即可
        result = {}

        # 保持顶层字段顺序
        field_order = ['task_name', 'description', 'global_config', 'benchmark_suits']
        for field in field_order:
            if field in config:
                result[field] = config[field]

        # 处理其他字段
        for key, value in config.items():
            if key not in result:
                result[key] = value

        # 处理基准测试套件，确保变量字段顺序
        if 'benchmark_suits' in result:
            suits = []
            for suit in result['benchmark_suits']:
                suit_ordered = {}
                # 套件字段顺序
                suit_field_order = ['suit_name', 'description', 'variables', 'fixed_params']
                for field in suit_field_order:
                    if field in suit:
                        suit_ordered[field] = suit[field]

                # 处理其他字段
                for key, value in suit.items():
                    if key not in suit_ordered:
                        suit_ordered[key] = value

                # 确保变量字段中name在最前面
                if 'variables' in suit_ordered:
                    variables = []
                    for var in suit_ordered['variables']:
                        var_ordered = {}
                        # 变量字段顺序：name, start, end, step, values
                        if 'name' in var:
                            var_ordered['name'] = var['name']
                        if 'start' in var:
                            var_ordered['start'] = var['start']
                        if 'end' in var:
                            var_ordered['end'] = var['end']
                        if 'step' in var:
                            var_ordered['step'] = var['step']
                        if 'values' in var:
                            var_ordered['values'] = var['values']

                        # 其他字段
                        for key, value in var.items():
                            if key not in var_ordered:
                                var_ordered[key] = value
                        variables.append(var_ordered)
                    suit_ordered['variables'] = variables

                suits.append(suit_ordered)

            result['benchmark_suits'] = suits

        return result

    
    
    def run_task(self, yaml_file: str, preview: bool = True) -> Dict[str, Any]:
        """
        运行批量基准测试任务

        Args:
            yaml_file: YAML任务文件路径
            preview: 是否为预览模式（仅显示计划，不实际执行）

        Returns:
            执行结果摘要
        """
        try:
            start_time = time.time()

            # 1. 加载任务配置
            self.logger.info("开始批量基准测试任务")
            task_config = self.task_loader.load_task_file(yaml_file)

            # 2. 生成所有测试用例
            all_cases = self.case_generator.generate_all_cases(task_config)

            if not all_cases:
                raise ValueError("没有生成任何测试用例")

            # 3. 创建结果目录
            task_dir = self.result_manager.create_result_directory(task_config)

            # 4. 显示执行信息
            self._display_execution_start(task_config, all_cases)

            # 5. 生成README文件
            execution_plan_for_readme = {
                'execution_plan': [{'case_index': i+1, 'suit_name': case['suit_name']} for i, case in enumerate(all_cases)]
            }
            self.result_manager.generate_task_readme(task_dir, task_config, execution_plan_for_readme)

            # 6. 执行任务（预览标志传递给执行器，由执行器决定是否实际执行benchmark）
            results = self.task_runner.execute_batch_task(all_cases, preview, task_dir, task_config)

            # 7. 保存任务摘要并更新任务状态
            end_time = time.time()
            execution_time = end_time - start_time

            # 生成摘要信息
            self.result_manager.save_task_summary(task_dir, task_config, results, execution_time, preview)

            # 更新数据库中的任务状态
            if not preview:
                # 获取实际创建的任务名称（带时间戳）
                task_name = task_config.get('task_name', '未知任务')
                execution_time_seconds = execution_time

                # 从原始配置和执行时间计算实际的任务名称
                timestamp = all_cases[0].get('execution_params', {}).get('timestamp')
                if timestamp:
                    actual_task_name = f"{task_name}_{timestamp}"
                else:
                    # 使用当前时间生成时间戳
                    from datetime import datetime
                    actual_task_name = f"{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                self.task_runner.db_manager.complete_task_with_summary(
                    task_name, execution_time_seconds, results
                )

            # 8. 生成返回摘要
            success_count = len([r for r in results if r.get('success', False)])
            total_count = len(results)

            summary = {
                'success': True,
                'task_name': task_config.get('task_name'),
                'total_cases': total_count,
                'successful_cases': success_count,
                'failed_cases': total_count - success_count,
                'success_rate': f"{(success_count / total_count * 100):.1f}%" if total_count > 0 else "0%",
                'execution_time': execution_time,
                'preview': preview,
                'results_directory': str(task_dir) if task_dir else None,
                'results': results
            }

            # 显示完成信息（统一模式）
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            mode_text = "预览完成" if preview else "执行完成"
            print(f"\n{ColorOutput.green(f'✓ 批量基准测试{mode_text}')}")
            print(f"成功率: {success_count}/{total_count} ({success_rate:.1f}%) | 耗时: {execution_time:.1f}秒")
            print(f"任务文件: {yaml_file}")

            self.logger.info(f"批量基准测试任务完成: {success_count}/{total_count} 成功")
            return summary

        except Exception as e:
            error_msg = f"批量基准测试任务执行失败: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'execution_time': time.time() - start_time if 'start_time' in locals() else 0
            }

    def get_task_status(self, yaml_file: str) -> Dict[str, Any]:
        """
        获取任务状态（简化版本）

        Args:
            yaml_file: 任务文件路径

        Returns:
            任务状态信息
        """
        try:
            # 检查任务文件是否存在
            if not Path(yaml_file).exists():
                return {
                    'success': False,
                    'error': f'任务文件不存在: {yaml_file}',
                    'status': 'file_not_found'
                }

            # 加载任务配置
            task_config = self.task_loader.load_task_file(yaml_file)

            # 生成执行计划（不实际执行）
            execution_plan = self.case_generator.preview_execution_plan(task_config)

            return {
                'success': True,
                'task_file': yaml_file,
                'task_name': task_config.get('task_name'),
                'status': 'ready',
                'execution_plan': execution_plan
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    
    def _display_execution_start(self, task_config: Dict[str, Any], all_cases: List[Dict[str, Any]]) -> None:
        """
        显示任务开始信息（简单版）

        Args:
            task_config: 任务配置
            all_cases: 所有测试用例
        """
        from utils.output import ColorOutput

        task_name = task_config.get('task_name', '未命名任务')
        models = task_config.get('global_config', {}).get('models', [])

        print(f"\n{ColorOutput.green('开始批量基准测试')}")
        print(f"任务: {task_name}")
        print(f"用例: {len(all_cases)}个 | 模型: {', '.join(models)}")
        print("-" * 50)
        print(f"{ColorOutput.yellow('开始执行...')}")
        print()

    
    def __repr__(self) -> str:
        return "BatchBenchmark(modular_version)"