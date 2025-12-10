#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例生成器

专门负责：
- 变量范围定义和验证
- 测试用例参数组合生成
- 基准套件用例规划
"""

import itertools
from typing import Dict, List, Any
from pathlib import Path
from utils.logger import LoggerManager
from config.system import SystemConfig


class VariableRange:
    """变量范围定义类"""

    def __init__(self, name: str, **kwargs):
        """
        初始化变量范围

        Args:
            name: 变量名
            kwargs: 变量范围定义，可以是:
                   - start, end, step: 范围定义
                   - values: 离散值列表
        """
        self.name = name
        self.values = []

        if 'values' in kwargs:
            # 离散值列表
            self.values = kwargs['values']
        elif all(k in kwargs for k in ['start', 'end', 'step']):
            # 范围定义
            start = kwargs['start']
            end = kwargs['end']
            step = kwargs['step']

            if step == 0:
                raise ValueError(f"变量 {name} 的步长不能为0")

            # 生成序列
            step_sign = 1 if step > 0 else -1
            current = start
            while (step_sign * current) <= (step_sign * end):
                self.values.append(current)
                current += step
        else:
            raise ValueError(f"变量 {name} 的范围定义无效")

    def __repr__(self):
        return f"VariableRange(name='{self.name}', values={self.values})"


class BenchSuit:
    """基准测试套件类"""

    def __init__(self, suit_name: str, description: str = "", variables: List[Dict] = None,
                 fixed_params: Dict[str, Any] = None):
        """
        初始化基准测试套件

        Args:
            suit_name: 套件名称
            description: 套件描述
            variables: 变量定义列表
            fixed_params: 固定参数字典
        """
        self.suit_name = suit_name
        self.description = description
        self.fixed_params = fixed_params.copy() if fixed_params else {}
        self.variable_ranges = []

        if variables:
            for var_def in variables:
                if 'name' not in var_def:
                    raise ValueError("变量定义中缺少name字段")

                # 从字典中移除name，避免重复传递
                kwargs = {k: v for k, v in var_def.items() if k != 'name'}
                var_range = VariableRange(var_def['name'], **kwargs)
                self.variable_ranges.append(var_range)

    def generate_bench_cases(self) -> List[Dict[str, Any]]:
        """
        生成所有基准测试用例的组合

        Returns:
            基准测试用例参数列表
        """
        if not self.variable_ranges:
            # 没有变量，只有一个基准测试用例
            return [self._process_params(self.fixed_params.copy())]

        # 生成所有变量值的组合
        var_names = [vr.name for vr in self.variable_ranges]
        var_values = [vr.values for vr in self.variable_ranges]

        bench_cases = []
        for combination in itertools.product(*var_values):
            # 创建每个基准测试用例的参数字典
            bench_case = self.fixed_params.copy()
            for name, value in zip(var_names, combination):
                bench_case[name] = value
            # 处理路径转换
            bench_case = self._process_params(bench_case)
            bench_cases.append(bench_case)

        return bench_cases

    def _process_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理参数中的路径转换，转换为提示词文件的完整绝对路径

        Args:
            params: 原始参数字典

        Returns:
            处理后的参数字典
        """
        processed_params = params.copy()

        # 直接处理提示词文件路径转换：总是转换为完整路径
        if 'prompt_file' in processed_params and processed_params['prompt_file']:
            prompt_file = processed_params['prompt_file']
            system_config = SystemConfig()
            prompt_file_path = system_config.get_prompt_file_path(prompt_file)
            processed_params['prompt_file'] = str(prompt_file_path)

        return processed_params

    def __repr__(self):
        return (f"BenchSuit(name='{self.suit_name}', variables={len(self.variable_ranges)}, "
                f"fixed_params={len(self.fixed_params)})")


class CaseGenerator:
    """基准测试用例生成器"""

    def __init__(self):
        """初始化用例生成器"""
        self.logger = LoggerManager.get_logger("CaseGenerator")

    def generate_all_cases(self, task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成任务中所有基准测试套件的用例

        Args:
            task_config: 任务配置字典

        Returns:
            所有测试用例的列表，每个用例包含套件信息、参数和模型信息，按模型优先排序
        """
        all_cases = []

        try:
            benchmark_suits = task_config.get('benchmark_suits', [])
            global_config = task_config.get('global_config', {})

            # 获取模型列表，如果未配置则使用默认
            models = global_config.get('models', ['default'])
            if not models:
                models = ['default']

            self.logger.info(f"为 {len(models)} 个模型生成测试用例（模型优先排序）")

            # 模型优先排序：先为每个模型生成所有套件
            for model in models:
                self.logger.info(f"为模型 '{model}' 生成测试用例")

                # 为当前模型生成所有套件的用例
                for suit_def in benchmark_suits:
                    # 创建基准套件
                    suit = BenchSuit(**suit_def)

                    # 生成该套件的所有用例
                    suit_cases = suit.generate_bench_cases()

                    # 为当前模型和套件生成用例
                    for case_params in suit_cases:
                        case_data = {
                            'suit_name': suit.suit_name,
                            'suit_description': suit.description,
                            'params': case_params,
                            'global_config': global_config,
                            'model': model  # 添加模型信息
                        }
                        all_cases.append(case_data)

            self.logger.info(f"总共生成 {len(all_cases)} 个测试用例")
            return all_cases

        except Exception as e:
            self.logger.error(f"生成测试用例失败: {e}")
            raise

    