#!/usr/bin/env python3
"""
数据库管理模块
负责数据库初始化和数据写入操作
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from config.system import SystemConfig

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库管理器"""
        # 如果没有指定路径，从系统配置获取
        if db_path is None:
            system_config = SystemConfig()
            db_path = str(system_config.get_database_path())

        self.db_path = db_path

        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 创建tasks表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        original_name TEXT,
                        run_number INTEGER,
                        description TEXT,
                        original_yaml TEXT NOT NULL,
                        summary_json TEXT,
                        execution_time_seconds REAL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 创建suites表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS suites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        model_path TEXT NOT NULL,
                        suite_yaml TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        UNIQUE(task_id, name, model_name)
                    )
                ''')

                # 创建case_definitions表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS case_definitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        suite_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        base_parameters TEXT NOT NULL,
                        model_size TEXT,
                        backend TEXT,
                        threads INTEGER,
                        precision TEXT,
                        execution_time_seconds REAL,
                        status TEXT DEFAULT 'success',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (suite_id) REFERENCES suites(id) ON DELETE CASCADE,
                        UNIQUE(suite_id, name)
                    )
                ''')

                # 创建case_variable_values表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS case_variable_values (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id INTEGER NOT NULL,
                        variable_name TEXT NOT NULL,
                        variable_value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (case_id) REFERENCES case_definitions(id) ON DELETE CASCADE,
                        UNIQUE(case_id, variable_name)
                    )
                ''')

                # 创建benchmark_results表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS benchmark_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id INTEGER NOT NULL,
                        result_type TEXT NOT NULL,
                        result_parameter TEXT NOT NULL,
                        mean_value REAL NOT NULL,
                        std_value REAL,
                        value_type TEXT DEFAULT 'single',
                        unit TEXT DEFAULT 'tokens/sec',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (case_id) REFERENCES case_definitions(id) ON DELETE CASCADE,
                        UNIQUE(case_id, result_type, result_parameter)
                    )
                ''')

                # 数据库迁移：添加新字段
                cursor.execute('PRAGMA table_info(tasks)')
                columns = [row[1] for row in cursor.fetchall()]

                # 检查是否需要添加新字段
                if 'original_name' not in columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN original_name TEXT')
                if 'run_number' not in columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN run_number INTEGER')

                # 检查benchmark_results表是否需要添加ptypes字段
                cursor.execute('PRAGMA table_info(benchmark_results)')
                result_columns = [row[1] for row in cursor.fetchall()]
                if 'ptypes' not in result_columns:
                    cursor.execute('ALTER TABLE benchmark_results ADD COLUMN ptypes TEXT')

                # 检查case_definitions表是否需要添加execution_time_seconds字段
                cursor.execute('PRAGMA table_info(case_definitions)')
                case_columns = [row[1] for row in cursor.fetchall()]
                if 'execution_time_seconds' not in case_columns:
                    cursor.execute('ALTER TABLE case_definitions ADD COLUMN execution_time_seconds REAL')

                # 迁移现有数据：解析原始名称到新字段
                cursor.execute('SELECT id, name FROM tasks WHERE original_name IS NULL OR run_number IS NULL')
                existing_tasks = cursor.fetchall()

                for task_id, task_name in existing_tasks:
                    if '_20' in task_name:  # 检查是否有时间戳格式
                        # 解析：原始名称_YYYYMMDD_HHMMSS
                        parts = task_name.split('_')
                        if len(parts) >= 3:
                            # 提取原始名称（除了时间戳的部分）
                            original_name = '_'.join(parts[:-2])

                            # 获取该任务的运行次数
                            cursor.execute('SELECT COUNT(*) FROM tasks WHERE name LIKE ? AND id <= ?',
                                         (f"{original_name}_%", task_id))
                            run_number = cursor.fetchone()[0]

                        else:
                            original_name = task_name
                            run_number = 1
                    else:
                        original_name = task_name
                        run_number = 1

                    # 更新新字段
                    cursor.execute('''
                        UPDATE tasks SET
                            original_name = ?,
                            run_number = ?
                        WHERE id = ?
                    ''', (original_name, run_number, task_id))

                # 创建索引以提高查询性能
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_suites_task_id ON suites(task_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cases_suite_id ON case_definitions(suite_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_case_id ON benchmark_results(case_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_case_variables_case_id ON case_variable_values(case_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_original_name ON tasks(original_name)')
                
                conn.commit()
                logger.info("数据库初始化成功")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _insert_task(self, name: str, description: str, original_yaml: str, status: str = 'pending') -> int:
        """插入任务记录，每次运行都创建新任务"""
        try:
            # 生成时间戳和其他信息
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{name}_{timestamp}"

            # 计算运行次数
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM tasks WHERE original_name = ?', (name,))
                run_number = cursor.fetchone()[0] + 1

                cursor.execute('''
                    INSERT INTO tasks (name, original_name, run_number,
                                     description, original_yaml, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (unique_name, name, run_number, description, original_yaml, status))
                task_id = cursor.lastrowid
                conn.commit()
                logger.info(f"插入任务记录: {unique_name} (ID: {task_id}, Run: {run_number}, Status: {status})")
                return task_id
        except Exception as e:
            logger.error(f"插入任务记录失败: {e}")
            raise

    def _insert_suite(self, task_id: int, name: str, model_name: str, model_path: str, suite_yaml: str) -> int:
        """插入测试套件记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO suites (task_id, name, model_name, model_path, suite_yaml)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task_id, name, model_name, model_path, suite_yaml))
                suite_id = cursor.lastrowid
                conn.commit()
                logger.info(f"插入套件记录: {name} (ID: {suite_id})")
                return suite_id
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                # 套件已存在，返回已存在的套件ID
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM suites WHERE task_id = ? AND model_name = ?', (task_id, model_name))
                    result = cursor.fetchone()
                    if result:
                        suite_id = result[0]
                        logger.info(f"套件已存在: {name} (ID: {suite_id})")
                        return suite_id
            logger.error(f"插入套件记录失败: {e}")
            # 输出详细的调试信息
            logger.error(f"插入参数: task_id={task_id}, name={name}, model_name={model_name}")
            # 检查是否违反了唯一约束
            if "UNIQUE constraint failed" in str(e):
                logger.error(f"唯一约束冲突 - 可能的原因: 相同任务中已有相同套件名和模型名的记录")
            raise

    def _insert_case_definition(self, suite_id: int, name: str, base_parameters: Dict) -> int:
        """插入用例定义记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO case_definitions (suite_id, name, base_parameters, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (suite_id, name, json.dumps(base_parameters)))
                case_id = cursor.lastrowid
                conn.commit()
                logger.info(f"插入用例定义: {name} (ID: {case_id})")
                return case_id
        except Exception as e:
            logger.error(f"插入用例定义失败: {e}")
            raise

    def _insert_case_variable_values(self, case_id: int, variable_values: Dict[str, str]):
        """插入用例变量值"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for var_name, var_value in variable_values.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO case_variable_values (case_id, variable_name, variable_value)
                        VALUES (?, ?, ?)
                    ''', (case_id, var_name, var_value))
                conn.commit()
                logger.info(f"插入用例变量: case_id={case_id}, variables={list(variable_values.keys())}")
        except Exception as e:
            logger.error(f"插入用例变量失败: {e}")
            raise

    def _update_case_results(self, case_id: int, case_info: Dict, execution_time: float = None):
        """更新用例运行结果信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 构建动态SQL
                update_fields = ["model_size = ?", "backend = ?", "threads = ?", "precision = ?", "status = 'success'"]
                params = [
                    case_info.get('model_size'),
                    case_info.get('backend'),
                    case_info.get('threads'),
                    case_info.get('precision')
                ]

                # 如果提供了执行时间，添加到更新语句
                if execution_time is not None:
                    update_fields.append("execution_time_seconds = ?")
                    params.append(execution_time)

                params.append(case_id)

                update_sql = f"UPDATE case_definitions SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(update_sql, params)
                conn.commit()
                logger.info(f"更新用例结果: case_id={case_id}, execution_time={execution_time}")
        except Exception as e:
            logger.error(f"更新用例结果失败: {e}")
            raise

    def _insert_benchmark_results(self, case_id: int, results: List[Dict]):
        """插入基准测试结果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for result in results:
                    cursor.execute('''
                        INSERT OR REPLACE INTO benchmark_results
                        (case_id, result_type, result_parameter, mean_value, std_value, value_type, unit, ptypes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        case_id,
                        result['result_type'],
                        result['result_parameter'],
                        result['mean_value'],
                        result.get('std_value'),
                        result.get('value_type', 'single'),
                        result.get('unit', 'tokens/sec'),
                        result.get('ptypes', 'fix')  # 默认为fix模式
                    ))
                conn.commit()
                logger.info(f"插入基准测试结果: case_id={case_id}, count={len(results)}")
        except Exception as e:
            logger.error(f"插入基准测试结果失败: {e}")
            raise

    def _update_task_status(self, task_id: int, status: str, summary_json: Optional[Dict] = None, execution_time: Optional[float] = None):
        """更新任务状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                update_query = "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP"
                params = [status]

                if summary_json:
                    update_query += ", summary_json = ?"
                    params.append(json.dumps(summary_json))

                if execution_time:
                    update_query += ", execution_time_seconds = ?"
                    params.append(execution_time)

                update_query += " WHERE id = ?"
                params.append(task_id)

                cursor.execute(update_query, params)
                conn.commit()
                logger.info(f"更新任务状态: task_id={task_id}, status={status}")
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            raise

    def _get_task_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tasks WHERE name = ?', (name,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None

    def _get_suite_by_task_and_model(self, task_id: int, model_name: str) -> Optional[Dict]:
        """根据任务ID和模型名获取套件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM suites WHERE task_id = ? AND model_name = ?', (task_id, model_name))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取套件失败: {e}")
            return None

    def _get_suite_by_task_and_name(self, task_id: int, suite_name: str, model_name: str = None) -> Optional[Dict]:
        """根据任务ID、套件名和模型名获取套件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if model_name:
                    cursor.execute('SELECT * FROM suites WHERE task_id = ? AND name = ? AND model_name = ?',
                                  (task_id, suite_name, model_name))
                else:
                    cursor.execute('SELECT * FROM suites WHERE task_id = ? AND name = ?', (task_id, suite_name))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取套件失败: {e}")
            return None

    def _get_case_by_suite_and_name(self, suite_id: int, case_name: str) -> Optional[Dict]:
        """根据套件ID和用例名获取用例"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM case_definitions WHERE suite_id = ? AND name = ?', (suite_id, case_name))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取用例失败: {e}")
            return None

    # ==================== 高级业务方法 ====================

    def create_or_update_task(self, task_config: Dict, status: str = 'pending') -> int:
        """
        创建新任务记录的高级方法 (每次运行都创建新任务)

        Args:
            task_config: 任务配置信息
            status: 任务状态

        Returns:
            任务ID
        """
        try:
            # 每次运行都创建新任务
            task_name = task_config.get('task_name', '未知任务')
            description = task_config.get('description', '')
            original_yaml = json.dumps(task_config, ensure_ascii=False, indent=2)

            return self._insert_task(task_name, description, original_yaml, status)

        except Exception as e:
            logger.error(f"创建新任务失败: {e}")
            raise

    def create_or_update_suite(self, task_id: int, case_data: Dict, task_config: Dict) -> int:
        """
        创建或更新测试套件的高级方法

        Args:
            task_id: 任务ID
            case_data: 测试用例数据
            task_config: 任务配置

        Returns:
            套件ID
        """
        try:
            model_name = case_data.get('model', 'default')
            suit_name = case_data['suit_name']

            # 检查套件是否已存在 - 使用task_id、suite_name和model_name联合判断
            existing_suite = self._get_suite_by_task_and_name(task_id, suit_name, model_name)
            if existing_suite:
                logger.info(f"套件已存在: {suit_name} (ID: {existing_suite['id']})")
                return existing_suite['id']
            logger.info(f"创建新套件: {suit_name}")

            # 创建新套件 - 注意：这里需要模型配置路径
            # 由于db_manager不直接访问models_config，我们简化处理
            model_path = f"/models/{model_name}"  # 简化路径

            # 获取套件YAML配置
            suite_yaml = ''
            if task_config:
                for suite in task_config.get('benchmark_suits', []):
                    if suite.get('suit_name') == suit_name:
                        suite_yaml = json.dumps(suite, ensure_ascii=False, indent=2)
                        break

            return self._insert_suite(task_id, suit_name, model_name, model_path, suite_yaml)

        except Exception as e:
            logger.error(f"创建或更新套件失败: {e}")
            raise

    def create_or_update_case_with_results(self, task_id: int, suite_id: int, case_num: int,
                                         case_data: Dict, bench_result: Dict) -> int:
        """
        创建用例并写入完整测试结果的高级方法

        Args:
            task_id: 任务ID
            suite_id: 套件ID
            case_num: 用例编号
            case_data: 用例数据
            bench_result: 基准测试结果

        Returns:
            用例ID
        """
        try:
            case_name = f"case_{case_num}"

            # 检查用例是否已存在
            existing_case = self._get_case_by_suite_and_name(suite_id, case_name)
            if existing_case:
                case_id = existing_case['id']
            else:
                # 创建新用例
                base_parameters = case_data.get('params', {})
                case_id = self._insert_case_definition(suite_id, case_name, base_parameters)

            # 写入变量值
            params = case_data.get('params', {})
            variable_values = {}
            for key, value in params.items():
                if value is not None and value != '':
                    variable_values[key] = str(value)

            if variable_values:
                self._insert_case_variable_values(case_id, variable_values)

            # 写入基准测试结果
            results = []

            # 从JSON结果中提取性能数据和执行时间
            json_result = bench_result.get('json_result', {})
            execution_info = json_result.get('execution', {})
            execution_time = execution_info.get('runtime_seconds')

            # 获取pType信息
            ptypes = bench_result.get('raw_data', {}).get('ptypes', 'fix')

            if 'results' in json_result:
                bench_data = json_result['results']

                # PP结果
                if 'prefill' in bench_data:
                    pp_result = bench_data['prefill']
                    # 从test_name解析prompt长度，如"pp512" -> 512
                    test_name = pp_result.get('test_name', '')
                    if test_name.startswith('pp'):
                        try:
                            prompt_length = int(test_name[2:])  # 提取"pp"后面的数字
                        except (ValueError, IndexError):
                            prompt_length = pp_result.get('prompt_length', 64)
                    else:
                        prompt_length = pp_result.get('prompt_length', 64)

                    results.append({
                        'result_type': 'pp',
                        'result_parameter': str(prompt_length),
                        'mean_value': pp_result['tokens_per_sec']['mean'],
                        'std_value': pp_result['tokens_per_sec']['std'],
                        'value_type': 'single',
                        'unit': 'tokens/sec',
                        'ptypes': ptypes
                    })

                # TG结果
                if 'decode' in bench_data:
                    tg_result = bench_data['decode']
                    # 从test_name解析generate长度，如"tg128" -> 128
                    test_name = tg_result.get('test_name', '')
                    if test_name.startswith('tg'):
                        try:
                            generate_length = int(test_name[2:])  # 提取"tg"后面的数字
                        except (ValueError, IndexError):
                            generate_length = tg_result.get('generate_length', 32)
                    else:
                        generate_length = tg_result.get('generate_length', 32)

                    results.append({
                        'result_type': 'tg',
                        'result_parameter': str(generate_length),
                        'mean_value': tg_result['tokens_per_sec']['mean'],
                        'std_value': tg_result['tokens_per_sec']['std'],
                        'value_type': 'single',
                        'unit': 'tokens/sec',
                        'ptypes': ptypes
                    })

                # Combined结果 (pg参数生成的pp+tg组合)
                if 'combined' in bench_data:
                    combined_result = bench_data['combined']
                    test_name = combined_result.get('test_name', 'pp32+tg64')
                    if '+' in test_name:
                        # 解析pp32+tg64为pp=32, tg=64
                        parts = test_name.split('+')
                        if len(parts) == 2:
                            pp_val = parts[0].replace('pp', '')
                            tg_val = parts[1].replace('tg', '')
                            results.append({
                                'result_type': 'pp+tg',
                                'result_parameter': f"{pp_val},{tg_val}",
                                'mean_value': combined_result['tokens_per_sec']['mean'],
                                'std_value': combined_result['tokens_per_sec']['std'],
                                'value_type': 'single',
                                'unit': 'tokens/sec',
                                'ptypes': ptypes
                            })

            # 批量写入结果
            for result_item in results:
                self._insert_benchmark_results(case_id, [result_item])

            # 更新用例执行信息
            model_info = json_result.get('model', {})
            bench_parameters = json_result.get('bench_parameters', {})

            case_info = {
                'model_size': model_info.get('size_mb'),
                'backend': json_result.get('system_info', {}).get('backend'),
                'threads': bench_parameters.get('threads'),
                'precision': bench_parameters.get('precision')
            }

            self._update_case_results(case_id, case_info, execution_time)

            return case_id

        except Exception as e:
            logger.error(f"创建或更新用例及结果失败: {e}")
            raise

    def complete_task_with_summary(self, task_name: str, execution_time: float, results: List[Dict]):
        """
        完成任务并更新摘要的高级方法

        Args:
            task_name: 任务名称（原始名称）
            execution_time: 执行时间
            results: 执行结果列表
        """
        try:
            # 查找最近创建的匹配任务（按创建时间排序，取最新的）
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 查找以task_name开头的最新任务记录
                cursor.execute('SELECT id, name, status FROM tasks WHERE name LIKE ? ORDER BY created_at DESC LIMIT 1', (f"{task_name}_%",))
                matching_task = cursor.fetchone()

                if not matching_task:
                    # 如果没找到带时间戳的任务，尝试直接查找原始名称（兼容旧数据）
                    cursor.execute('SELECT id, name, status FROM tasks WHERE name = ? LIMIT 1', (task_name,))
                    matching_task = cursor.fetchone()

                    if not matching_task:
                        logger.error(f"找不到匹配的任务记录: {task_name}")
                        # 列出所有任务用于调试
                        cursor.execute('SELECT name, created_at FROM tasks ORDER BY created_at DESC LIMIT 5')
                        recent_tasks = cursor.fetchall()
                        logger.error(f"最近的任务记录: {recent_tasks}")
                        return

            task_id, actual_task_name, current_status = matching_task
            logger.info(f"找到任务记录: {actual_task_name} (ID: {task_id})")

            # 计算状态
            success_count = len([r for r in results if r.get('success', False)])
            total_count = len(results)
            status = 'completed' if success_count == total_count else 'partial_failure' if success_count > 0 else 'failed'

            # 构建摘要
            summary = {
                'statistics': {
                    'total_cases': total_count,
                    'successful_cases': success_count,
                    'failed_cases': total_count - success_count,
                    'success_rate': f"{(success_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
                }
            }

            # 更新任务状态
            self._update_task_status(task_id, status, summary, execution_time)
            logger.info(f"任务完成: {actual_task_name} -> {status} (ID: {task_id})")
            return task_id

        except Exception as e:
            logger.error(f"完成任务失败: {e}")
            # 添加详细的错误信息和调试信息
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise