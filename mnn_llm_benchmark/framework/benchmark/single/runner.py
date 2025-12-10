#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单次基准测试业务逻辑模块

封装单次MNN LLM基准测试的业务流程，包括：
- 配置管理和验证
- 测试执行控制
- 结果处理和存储
- 错误处理和报告

此模块专注于单次基准测试的业务逻辑，
与core/executor.py的核心执行功能分离。
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any

from benchmark.core.executor import BenchExecutor
from config.system import SystemConfig
from config.models import ModelsConfig
from utils.logger import LoggerManager
from utils.project import ProjectPath
from utils.db_manager import DatabaseManager


class SingleBenchmark:
    """单次基准测试业务逻辑处理器"""

    def __init__(self):
        """
        初始化单次基准测试处理器

        加载系统配置、模型配置，初始化执行器和日志
        """
        # 初始化日志
        self.logger = LoggerManager.get_logger("SingleBenchmark")

        # 加载配置
        self.config_manager = SystemConfig()
        self.models_config_manager = ModelsConfig()

        # 获取配置信息
        self.mnn_bench_path = self.config_manager.get_llm_bench_path()
        self.models_config = self.models_config_manager._load_config()
        self.results_dir = self.config_manager.get_results_dir()

        # 初始化执行器
        try:
            self.executor = BenchExecutor(self.mnn_bench_path, self.models_config)
            self.logger.info(f"SingleBenchmark初始化成功: mnn_bench={self.mnn_bench_path}, 模型数量={len(self.models_config)}")
        except Exception as e:
            self.logger.error(f"SingleBenchmark初始化失败: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """
        获取可用的模型别名列表

        Returns:
            可用模型别名列表
        """
        return list(self.models_config.keys())

    def validate_model(self, model_alias: str) -> tuple[str, str]:
        """
        验证模型别名，返回配置路径和模型名称

        Args:
            model_alias: 模型别名

        Returns:
            (config_path, model_name) 元组

        Raises:
            ValueError: 模型别名无效
            FileNotFoundError: 配置文件不存在
        """
        return self.executor.validate_model(model_alias)

    def execute_single_test(self, model_alias: str, timeout: int = None, **bench_params) -> Dict[str, Any]:
        """
        执行单次基准测试

        Args:
            model_alias: 模型别名
            timeout: 超时时间（默认使用系统配置）
            **bench_params: 基准测试参数

        Returns:
            执行结果字典，包含：
            - success: 是否成功
            - json_result: 结构化JSON结果
            - execution_result: 执行详情
            - result_path: 结果文件路径
            - error: 错误信息（如有）
        """
        self.logger.info(f"开始执行单次基准测试: {model_alias}")

        try:
            # 验证模型
            config_path, model_name = self.validate_model(model_alias)

            # 获取默认超时时间
            if timeout is None:
                timeout = self.config_manager.get_config('execution').get('timeout', 300)

            # 创建结果目录路径
            result_path = self._create_result_path(model_alias)

            # 记录开始时间
            start_time = time.time()

            # 执行基准测试
            execution_result = self.executor.execute_bench(
                model_alias,
                timeout,
                **bench_params
            )
            end_time = time.time()

            # 构建返回结果
            result = {
                "success": execution_result.get("success", False),
                "json_result": execution_result.get("json_result"),
                "execution_result": execution_result.get("execution_result"),
                "result_path": str(result_path),
                "model_info": {
                    "alias": model_alias,
                    "name": model_name,
                    "config_path": str(config_path)
                },
                "execution_time": round(end_time - start_time, 3),
                "parameters": bench_params
            }

            # 如果成功，处理结果文件
            if result["success"] and result["json_result"]:
                if result_path:
                    # 复制原始输出文件到结果目录
                    temp_file_path = result.get("execution_result", {}).get("stdout", "")
                    # 从命令行中提取临时文件路径
                    command = result.get("execution_result", {}).get("command", "")
                    if "-fp " in command:
                        match = re.search(r'-fp\s+(\S+)', command)
                        if match:
                            temp_file_path = match.group(1)

                    self._save_result(result_path, result["json_result"], temp_file_path)
                    # 创建README说明
                    self._create_result_readme(result_path.parent, result["json_result"], temp_file_path)

                    # ★ 将单次测试结果写入数据库
                    self._save_result_to_database(result, model_alias, model_name, config_path, bench_params)

            self.logger.info(f"单次基准测试完成: {model_alias}, 成功={result['success']}")
            return result

        except Exception as e:
            error_msg = f"单次基准测试执行异常: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "json_result": None,
                "execution_result": None,
                "result_path": "",
                "error": str(e),
                "execution_time": 0,
                "parameters": bench_params
            }

    def _create_result_path(self, model_alias: str) -> Path:
        """
        创建结构化的结果目录路径

        Args:
            model_alias: 模型别名

        Returns:
            JSON结果文件的完整路径
        """
        # 创建模型目录
        model_dir = self.results_dir / model_alias
        model_dir.mkdir(parents=True, exist_ok=True)

        # 创建时间戳目录
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        test_dir = model_dir / timestamp
        test_dir.mkdir(parents=True, exist_ok=True)

        # 返回JSON文件路径
        return test_dir / "benchmark.json"

    def _save_result(self, json_path: Path, json_result: Dict[str, Any], temp_file_path: str = None) -> None:
        """
        保存JSON结果到文件

        Args:
            json_path: 文件路径
            json_result: JSON结果数据
            temp_file_path: 原始输出文件路径（仅用于README，不再单独保存）
        """
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_result, f, indent=2, ensure_ascii=False)
            self.logger.info(f"JSON结果已保存到: {json_path}")

            # 原始输出文件内容将包含在README中，不再单独保存raw_output文件
            if temp_file_path and Path(temp_file_path).exists():
                self.logger.info(f"原始输出文件内容已包含在README中: {temp_file_path}")
            else:
                self.logger.debug(f"临时输出文件不存在: {temp_file_path}")

        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")

    def _create_result_readme(self, test_dir: Path, json_result: Dict[str, Any], temp_file_path: str = None) -> None:
        """
        为测试结果创建README说明文件

        Args:
            test_dir: 测试目录路径
            json_result: JSON结果数据
            temp_file_path: 临时输出文件路径
        """
        readme_path = test_dir / "README.md"

        try:
            readme_content = self._generate_readme_content(json_result, temp_file_path)
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            self.logger.info(f"测试说明文件已创建: {readme_path}")
        except Exception as e:
            self.logger.warning(f"创建README文件失败: {e}")
            # README文件创建失败不影响主要功能

    def _generate_readme_content(self, json_result: Dict[str, Any], temp_file_path: str = None) -> str:
        """
        生成README文件内容

        Args:
            json_result: JSON结果数据
            temp_file_path: 临时输出文件路径

        Returns:
            README内容字符串
        """
        try:
            content = f"""# 基准测试结果

## 基本信息
- **基准ID**: {json_result.get('bench_id', 'Unknown')}
- **测试时间**: {json_result.get('timestamp', 'Unknown')}
- **测试者**: 用户

## 模型信息
- **别名**: {json_result.get('model', {}).get('alias', 'Unknown')}
- **名称**: {json_result.get('model', {}).get('name', 'Unknown')}
- **配置路径**: {json_result.get('model', {}).get('config_path', 'Unknown')}
- **模型大小**: {json_result.get('model', {}).get('size_mb', 'Unknown')}

## 执行信息
- **执行命令**: `{json_result.get('execution', {}).get('command', 'Unknown')}`
- **运行时间**: {json_result.get('execution', {}).get('runtime_seconds', 0)} 秒
- **超时设置**: {json_result.get('execution', {}).get('timeout_seconds', 0)} 秒
- **执行状态**: {json_result.get('execution', {}).get('success', False)}

## 基准参数
"""

            # 添加基准参数
            bench_params = json_result.get('bench_parameters', {})
            if bench_params:
                for param, value in bench_params.items():
                    if value != "uses_default":
                        content += f"- **{param}**: {value}\n"

            # 添加性能结果
            content += """
## 性能结果

"""

            results = json_result.get('results', {})
            if results:
                for test_type, test_data in results.items():
                    perf = test_data.get('tokens_per_sec', {})
                    content += f"### {test_type.upper()}\n"
                    content += f"- **测试名称**: {test_data.get('test_name', 'Unknown')}\n"
                    content += f"- **性能**: {perf.get('formatted', 'Unknown')}\n"
                    content += f"- **平均值**: {perf.get('mean', 0)} tokens/秒\n"
                    content += f"- **标准差**: {perf.get('std', 0)} tokens/秒\n\n"

            # 添加原始输出内容
            if temp_file_path and Path(temp_file_path).exists():
                try:
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()

                    content += """## 原始输出

以下是MNN基准测试工具的完整输出：

```
"""
                    content += raw_content
                    content += """\n```\n\n"""
                except Exception as e:
                    self.logger.warning(f"读取临时输出文件失败 {temp_file_path}: {e}")
                    content += "## 原始输出\n\n**读取原始输出文件失败**\n\n"
            else:
                content += "## 原始输出\n\n**无原始输出文件**\n\n"

            content += """---
*此文件由MNN LLM基准测试框架自动生成*
"""
            return content

        except Exception as e:
            self.logger.error(f"生成README内容失败: {e}")
            return "# 基准测试结果\n\n# **生成README时遇到错误**\n"

    def get_summary(self, model_alias: str, limit: int = 10) -> Dict[str, Any]:
        """
        获取指定模型的测试摘要

        Args:
            model_alias: 模型别名
            limit: 返回的测试数量限制

        Returns:
            测试摘要字典
        """
        try:
            model_dir = self.results_dir / model_alias
            if not model_dir.exists():
                return {"error": f"模型目录不存在: {model_alias}"}

            # 获取所有测试目录，按时间排序
            test_dirs = sorted(model_dir.iterdir(), key=lambda x: x.name, reverse=True)

            summary = {
                "model_alias": model_alias,
                "total_tests": len([d for d in test_dirs if d.is_dir()]),
                "recent_tests": []
            }

            # 收集最近的测试信息
            for i, test_dir in enumerate(test_dirs[:limit]):
                if not test_dir.is_dir():
                    continue

                json_path = test_dir / "benchmark.json"
                if not json_path.exists():
                    continue

                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    summary["recent_tests"].append({
                        "test_time": data.get('timestamp'),
                        "bench_id": data.get('bench_id'),
                        "success": data.get('execution', {}).get('success', False),
                        "runtime": data.get('execution', {}).get('runtime_seconds', 0),
                        "results_count": len(data.get('results', {}))
                    })
                except Exception as e:
                    self.logger.warning(f"读取测试结果失败 {json_path}: {e}")
                    continue

            return summary

        except Exception as e:
            return {"error": f"获取测试摘要失败: {e}"}

    def _save_result_to_database(self, result: Dict[str, Any], model_alias: str, model_name: str,
                                config_path: Path, bench_params: Dict[str, Any]) -> None:
        """
        将单次测试结果写入数据库

        Args:
            result: 测试结果
            model_alias: 模型别名
            model_name: 模型名称
            config_path: 模型配置路径
            bench_params: 基准测试参数
        """
        try:
            # 初始化数据库管理器
            db_manager = DatabaseManager()

            # 构造任务信息 - 基于模型和参数
            task_name = f"单次测试_{model_alias}"
            task_description = f"模型 {model_name} 的单次基准测试"

            # 构造测试套件名称 - 基于参数特征
            param_features = []
            if bench_params.get("prompt_file"):
                param_features.append("file")
            if bench_params.get("variable_prompt"):
                param_features.append("variable")

            suite_name = f"性能测试_{'_'.join(param_features) if param_features else 'standard'}"
            suite_description = f"参数: {', '.join([f'{k}={v}' for k, v in bench_params.items() if k != 'uses_default'])}"

            # 创建任务（如果不存在）
            task_config = {
                'task_name': task_name,
                'description': task_description,
                'status': 'completed',
                'original_yaml': '',
                'models': [model_alias]
            }
            task_id = db_manager.create_or_update_task(task_config, 'completed')

            # 创建测试套件（如果不存在）- 直接使用_insert_suite方法
            suite_id = db_manager._insert_suite(task_id, suite_name, model_name, str(config_path),
                                               json.dumps(bench_params, ensure_ascii=False))

            # 丰富bench_params，添加可能的默认参数，确保采集完整
            from config.system import SystemConfig
            config_manager = SystemConfig()
            execution_config = config_manager.get_execution_config()

            # 构建完整的参数集合
            full_params = bench_params.copy()

            # 添加可能缺失的参数，使用默认值
            if 'threads' not in full_params:
                full_params['threads'] = 4  # 默认线程数
            if 'precision' not in full_params:
                full_params['precision'] = 2  # 默认精度 Low
            if 'n_prompt' not in full_params:
                full_params['n_prompt'] = 256  # 默认预填充长度
            if 'n_gen' not in full_params:
                full_params['n_gen'] = 128  # 默认生成长度
            if 'kv_cache' not in full_params:
                full_params['kv_cache'] = 'true'  # 默认启用KV缓存
            if 'variable_prompt' not in full_params:
                # 根据是否有prompt_file来推断pType
                if bench_params.get('prompt_file'):
                    full_params['variable_prompt'] = 0  # 文件模式是固定提示词
                else:
                    full_params['variable_prompt'] = 1  # 否则是可变提示词

            # 创建测试用例配置和数据
            case_data = {
                'suit_name': suite_name,
                'model': model_alias,
                'params': full_params
            }

            # 计算正确的pType
            if bench_params.get("prompt_file"):
                ptype = "file"
            elif bench_params.get("variable_prompt") == 1:
                ptype = "variable"
            else:
                ptype = "fix"

            # 构造类似批量测试的执行结果格式
            bench_execution_result = {
                'json_result': result['json_result'],
                'success': result['success'],
                'execution_time': result['execution_time'],
                'parameters': full_params,
                'raw_data': {
                    'ptypes': ptype  # 明确设置ptypes
                }
            }

            # 使用数据库管理器的高级方法写入结果
            db_manager.create_or_update_case_with_results(
                task_id, suite_id, 1, case_data, bench_execution_result
            )

            self.logger.info(f"单次测试结果已写入数据库: task={task_name}, suite={suite_name}, pType={ptype}")

        except Exception as e:
            self.logger.warning(f"单次测试结果入库失败: {e}", exc_info=True)
            # 数据库入库失败不影响主要功能

    def __repr__(self) -> str:
        return f"SingleBenchmark(models={len(self.models_config)}, executor={self.executor.__class__.__name__})"