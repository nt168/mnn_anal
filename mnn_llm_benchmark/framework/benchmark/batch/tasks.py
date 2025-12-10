#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务文件加载器

专门负责：
- YAML任务文件的读取和解析
- 任务配置的验证和标准化
- 任务文件错误的处理和报告
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import LoggerManager


class TaskLoader:
    """YAML任务文件加载器"""

    def __init__(self):
        """初始化任务加载器"""
        self.logger = LoggerManager.get_logger("TaskLoader")

    def load_task_file(self, yaml_file: str) -> Dict[str, Any]:
        """
        加载YAML任务文件

        Args:
            yaml_file: YAML文件路径

        Returns:
            解析后的任务配置字典

        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML解析错误
            ValueError: 配置验证失败
        """
        yaml_path = Path(yaml_file)

        if not yaml_path.exists():
            raise FileNotFoundError(f"任务文件不存在: {yaml_path}")

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                task_config = yaml.safe_load(f)

            # 验证任务配置结构
            self._validate_task_config(task_config)

            self.logger.info(f"成功加载任务文件: {yaml_path}")
            return task_config

        except yaml.YAMLError as e:
            error_msg = f"YAML文件解析失败 {yaml_path}: {e}"
            self.logger.error(error_msg)
            raise yaml.YAMLError(error_msg)

        except Exception as e:
            error_msg = f"加载任务文件失败 {yaml_path}: {e}"
            self.logger.error(error_msg)
            raise

    def _validate_task_config(self, config: Dict[str, Any]) -> None:
        """
        验证任务配置的必要字段

        Args:
            config: 任务配置字典

        Raises:
            ValueError: 配置验证失败
        """
        required_fields = [
            'task_name',
            'global_config',
            'benchmark_suits'
        ]

        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            raise ValueError(f"任务配置缺少必要字段: {missing_fields}")

        # 验证全局配置
        global_config = config['global_config']
        if 'models' not in global_config:
            raise ValueError("global_config中缺少models字段")

        # 验证基准套件配置
        benchmark_suits = config['benchmark_suits']
        if not isinstance(benchmark_suits, list) or len(benchmark_suits) == 0:
            raise ValueError("benchmark_suits必须是非空列表")

        for i, suit in enumerate(benchmark_suits):
            self._validate_suit_config(suit, f"benchmark_suits[{i}]")

    def _validate_suit_config(self, suit: Dict[str, Any], path: str) -> None:
        """
        验证单个基准套件配置

        Args:
            suit: 套件配置
            path: 配置路径（用于错误信息）

        Raises:
            ValueError: 套件配置验证失败
        """
        required_suit_fields = ['suit_name']

        missing_fields = [field for field in required_suit_fields if field not in suit]
        if missing_fields:
            raise ValueError(f"{path} 缺少必要字段: {missing_fields}")

        # 验证variables字段格式
        if 'variables' in suit:
            variables = suit['variables']
            if not isinstance(variables, list):
                raise ValueError(f"{path}.variables 必须是列表")

            for i, var in enumerate(variables):
                if 'name' not in var:
                    raise ValueError(f"{path}.variables[{i}] 缺少name字段")

                # 检查变量定义的有效性
                if not any(key in var for key in ['values', 'start', 'end']):
                    raise ValueError(f"{path}.variables[{i}] 必须包含values或start/end定义")

                if 'start' in var and 'end' not in var:
                    raise ValueError(f"{path}.variables[{i}] 包含start但缺少end")

                if 'end' in var and 'start' not in var:
                    raise ValueError(f"{path}.variables[{i}] 包含end但缺少start")

                if 'step' in var and var.get('step') == 0:
                    raise ValueError(f"{path}.variables[{i}] 的step不能为0")