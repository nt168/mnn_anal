#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行器

专门负责：
- 单个测试用例的执行
- 批量测试任务的编排和调度
- 进度跟踪和错误处理
"""

import time
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from benchmark.core.executor import BenchExecutor
from config.system import SystemConfig
from config.models import ModelsConfig
from utils.logger import LoggerManager
from utils.output import ColorOutput
from utils.db_manager import DatabaseManager
import yaml


class TaskRunner:
    """基准测试任务执行器"""

    def __init__(self):
        """初始化任务执行器"""
        self.logger = LoggerManager.get_logger("TaskRunner")

        # 初始化配置管理器
        self.config_manager = SystemConfig()
        self.models_config_manager = ModelsConfig()

        # 数据库管理器
        try:
            self.db_manager = DatabaseManager()
            self.logger.info("数据库管理器初始化成功")
        except Exception as e:
            self.logger.error(f"数据库管理器初始化失败: {e}")
            self.db_manager = None

        # 任务执行状态管理
        self._current_task_config = None
        self._current_task_id = None
        self._current_suite_ids = {}  # {model_name: suite_id}
        self._current_case_counter = 0

    def create_executor(self) -> BenchExecutor:
        """
        创建基准测试执行器

        Returns:
            初始化完成的执行器
        """
        try:
            mnn_bench_path = self.config_manager.get_llm_bench_path()
            models_config = self.models_config_manager._load_config()

            executor = BenchExecutor(mnn_bench_path, models_config)
            self.logger.info("基准测试执行器创建成功")
            return executor

        except Exception as e:
            self.logger.error(f"创建执行器失败: {e}")
            raise

    def execute_single_case(self, executor: BenchExecutor, case_data: Dict[str, Any],
                            taskset_cmd: Optional[str] = None) -> Dict[str, Any]:
        """
        执行单个测试用例

        Args:
            executor: 执行器实例
            case_data: 测试用例数据
            taskset_cmd: 可选的taskset命令前缀

        Returns:
            执行结果
        """
        try:
            # 获取参数和配置
            params = case_data['params'].copy()
            global_config = case_data['global_config']

            # 从case_data获取模型（确保每个模型独立运行）
            model = case_data.get('model', 'default')
            timeout = params.get("timeout", global_config.get("timeout", 300))

            # 从params中移除timeout和model，避免重复传递
            exec_params = {k: v for k, v in params.items() if k not in ['timeout', 'model']}

            # 简化日志
            self.logger.debug(f"执行用例 - 套件: {case_data['suit_name']}")

            # 执行基准测试
            result = executor.execute_bench(model, timeout, taskset_cmd=taskset_cmd, **exec_params)

            # 添加用例信息到结果
            result.update({
                'suit_name': case_data['suit_name'],
                'suit_description': case_data['suit_description'],
                'execution_params': exec_params,
                'model': model
            })

            self.logger.info(f"用例执行完成 - 套件: {case_data['suit_name']}, 成功: {result.get('success', False)}")
            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'suit_name': case_data['suit_name'],
                'suit_description': case_data['suit_description'],
                'execution_params': case_data['params'],
                'model': case_data.get('model', 'default')
            }
            self.logger.error(f"用例执行失败 - 套件: {case_data['suit_name']}, 错误: {e}")
            return error_result

    def execute_batch_task(self, all_cases: List[Dict[str, Any]], preview: bool = False,
                          task_dir: Optional[Path] = None, task_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        执行批量基准测试任务

        Args:
            all_cases: 所有测试用例列表
            preview: 是否为预览模式（仅显示计划，不实际执行）
            task_dir: 任务结果目录（预览模式时可为None）
            task_config: 任务配置信息

        Returns:
            所有用例的执行结果列表
        """
        results = []
        taskset_cmd = None
        if task_config:
            taskset_cmd = task_config.get('taskset') or task_config.get('global_config', {}).get('taskset')

        # 创建执行器
        try:
            # 创建执行器
            executor = self.create_executor()
            total_cases = len(all_cases)

            # 初始化任务状态（立即写入任务条目）
            self._current_task_config = task_config
            self._current_suite_ids = {}
            self._current_case_counter = 0

            # 如果不是预览模式且有数据库管理器，立即创建任务记录
            if not preview and self.db_manager:
                self._current_task_id = self.db_manager.create_or_update_task(task_config, 'pending')
                self.logger.info(f"开始执行批量任务，共 {total_cases} 个测试用例 (task_id={self._current_task_id})")
            else:
                self._current_task_id = None
                self.logger.info(f"开始执行批量任务，共 {total_cases} 个测试用例")

            start_time = time.time()

            for i, case in enumerate(all_cases):
                suit_name = case['suit_name']
                case_num = i + 1

                # 模型切换显示
                if i == 0 or (i > 0 and case.get('model') != all_cases[i-1].get('model')):
                    model = case.get('model', 'default')
                    # 计算该模型的用例数量，方便显示
                    model_case_count = sum(1 for c in all_cases if c.get('model') == model)
                    print(f"\n{ColorOutput.blue('模型')}: {model} ({model_case_count}个用例)")
                    print(f"{'-' * 40}")

                # 套件切换显示
                if i == 0 or case['suit_name'] != all_cases[i-1]['suit_name']:
                    suit_name = case['suit_name']
                    suit_desc = case.get('suit_description', '')
                    if suit_desc:
                        print(f"\n{ColorOutput.cyan('套件')}: {suit_name} ({suit_desc})")
                    else:
                        print(f"\n{ColorOutput.cyan('套件')}: {suit_name}")
                    print("-" * 30)

                # 用例详情
                params_str = []
                for key, value in case['params'].items():
                    if value is not None:
                        params_str.append(f"{key}={value}")
                print(f"  测试 {case_num}/{total_cases}: {', '.join(params_str)}")

                # 简化日志信息
                self.logger.info(f"进度: {case_num}/{total_cases}")

                # 根据预览模式决定是否执行
                if preview:
                    # 预览模式：返回模拟结果
                    result = {
                        'success': True,
                        'preview': True,
                        'model': case.get('model', 'default'),
                        'execution_time': 0,
                        'execution_result': None,
                        'json_result': None
                    }
                else:
                    # 实际执行：调用执行器
                    result = self.execute_single_case(executor, case, taskset_cmd=taskset_cmd)

                result['case_number'] = case_num
                results.append(result)

                # 保存单个用例结果（仅限实际执行）
                if not preview and task_dir:
                    self._save_case_result_if_needed(task_dir, case_num, case, result)
                    # 直接写入数据库（实时写入）
                    self._write_case_result_directly(case_num, case, result)

            end_time = time.time()
            execution_time = end_time - start_time

            self.logger.info(f"批量任务执行完成，耗时: {execution_time:.2f}秒，"
                           f"成功: {sum(1 for r in results if r.get('success', False))}/{total_cases}")

            return results

        except Exception as e:
            self.logger.error(f"批量任务执行失败: {e}")
            raise

    def _save_case_result_if_needed(self, task_dir: Path, case_num: int,
                                   case_data: Dict, result: Dict) -> None:
        """
        保存单个用例的结果（JSON结果和原始输出）

        Args:
            task_dir: 任务目录
            case_num: 用例编号
            case_data: 用例数据
            result: 执行结果
        """
        try:
            if not result.get('success'):
                self.logger.info(f"用例 {case_num} 失败，跳过保存详细结果")
                return

            # 保存JSON结果
            if result.get('json_result'):
                model_name = case_data.get('model', 'default')
                suit_name = case_data['suit_name']

                # 按模型分组目录结构
                json_dir = task_dir / "json_results" / model_name / suit_name
                json_dir.mkdir(parents=True, exist_ok=True)

                json_file = json_dir / f"{case_num}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(result['json_result'], f, indent=2, ensure_ascii=False)
                self.logger.info(f"已保存JSON结果: {json_file}")

            # 保存原始输出文件
            execution_result = result.get('execution_result', {})
            if 'temp_output_file' in execution_result:
                temp_file = execution_result['temp_output_file']
                temp_path = Path(temp_file)

                if temp_path.exists():
                    # 按模型分组目录结构
                    model_name = case_data.get('model', 'default')
                    suit_name = case_data['suit_name']

                    raw_dir = task_dir / "raw_outputs" / model_name / suit_name
                    raw_dir.mkdir(parents=True, exist_ok=True)

                    # 复制原始文件
                    raw_file = raw_dir / f"{case_num}_raw.txt"
                    shutil.copy2(temp_path, raw_file)
                    self.logger.info(f"已保存原始输出: {raw_file}")

                    # 保存执行参数
                    params_file = raw_dir / f"{case_num}_params.json"
                    params_data = {
                        "case_number": case_num,
                        "suit_name": suit_name,
                        "model": model_name,
                        "execution_params": case_data.get('execution_params', {}),
                        "execution_result": {
                            k: v for k, v in execution_result.items()
                            if k not in ['temp_output_file', 'stdout', 'stderr']
                        }
                    }
                    with open(params_file, 'w', encoding='utf-8') as f:
                        json.dump(params_data, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"已保存执行参数: {params_file}")
                else:
                    self.logger.warning(f"临时文件不存在: {temp_file}")

        except Exception as e:
            self.logger.warning(f"保存用例结果失败 (用例 {case_num}): {e}", exc_info=True)

    def _write_case_result_directly(self, case_num: int, case_data: Dict, result: Dict):
        """
        实时写入单个case结果到数据库，使用db_manager高级方法

        Args:
            case_num: 用例编号
            case_data: 用例数据
            result: 执行结果
        """
        if not self.db_manager or not result.get('success'):
            return

        try:
            # 确保套件记录存在
            model_name = case_data.get('model', 'default')

            # 检查套件是否已在当前任务中创建 - 使用suite_name+model_name作为缓存键
            suite_name = case_data['suit_name']
            cache_key = f'{suite_name}_{model_name}'
            if cache_key in self._current_suite_ids:
                suite_id = self._current_suite_ids[cache_key]
            else:
                # 使用db_manager的高级方法创建或获取套件
                suite_id = self.db_manager.create_or_update_suite(
                    self._current_task_id, case_data, self._current_task_config
                )
                # 缓存套件ID - 使用suite_name+model_name作为键
                self._current_suite_ids[cache_key] = suite_id

            # 使用db_manager的高级方法创建用例并写入结果
            case_id = self.db_manager.create_or_update_case_with_results(
                self._current_task_id, suite_id, case_num, case_data, result
            )

            self.logger.info(f"实时写入case {case_num} 成功 (case_id={case_id})")

        except Exception as e:
            self.logger.error(f"实时写入case {case_num} 失败: {e}", exc_info=True)

    

    
    
    
    
    
    
    
    