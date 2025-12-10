#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库数据提取模块

负责从数据库中提取suite的数据用于分析
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from config.system import SystemConfig
from utils.logger import LoggerManager


class DataExtractor:
    """数据库数据提取器"""

    def __init__(self):
        """初始化数据提取器"""
        self.logger = LoggerManager.get_logger("DataExtractor")
        self.system_config = SystemConfig()

        # 数据库路径
        database_config = self.system_config.get_config("database")
        db_dir = database_config.get("db_dir", "data")
        db_file = database_config.get("db_file", "benchmark_results.db")
        self.db_path = Path(db_dir) / db_file

        # 如果是相对路径，需要相对于项目根目录
        if not self.db_path.is_absolute():
            # 获取项目根目录（framework的上级目录）
            project_root = Path(__file__).parent.parent.parent
            self.db_path = project_root / self.db_path

        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

    def get_suite_list(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的suite列表

        Returns:
            suite信息列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT s.id, s.name, s.model_name, COUNT(c.id) as case_count
                    FROM suites s
                    LEFT JOIN case_definitions c ON s.id = c.suite_id
                    GROUP BY s.id
                    ORDER BY s.id
                """)

                suites = []
                for row in cursor.fetchall():
                    suite_id, name, model_name, case_count = row
                    suites.append({
                        'id': suite_id,
                        'name': name,
                        'model_name': model_name,
                        'case_count': case_count
                    })

                return suites

        except Exception as e:
            self.logger.error(f"获取suite列表失败: {e}")
            raise

    def get_suite_variables(self, suite_id: int) -> List[str]:
        """
        获取suite的变量参数列表

        Args:
            suite_id: suite ID

        Returns:
            变量参数名列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT DISTINCT cvv.variable_name
                    FROM case_variable_values cvv
                    JOIN case_definitions cd ON cvv.case_id = cd.id
                    WHERE cd.suite_id = ?
                    ORDER BY cvv.variable_name
                """, (suite_id,))

                variables = [row[0] for row in cursor.fetchall()]
                return variables

        except Exception as e:
            self.logger.error(f"获取suite变量失败: {e}")
            raise

    def get_suite_result_types(self, suite_id: int) -> List[str]:
        """
        获取suite的结果类型列表

        Args:
            suite_id: suite ID

        Returns:
            结果类型列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT DISTINCT br.result_type
                    FROM benchmark_results br
                    JOIN case_definitions cd ON br.case_id = cd.id
                    WHERE cd.suite_id = ?
                    ORDER BY br.result_type
                """, (suite_id,))

                result_types = [row[0] for row in cursor.fetchall()]
                return result_types

        except Exception as e:
            self.logger.error(f"获取结果类型失败: {e}")
            raise

    def get_variable_median_values(self, suite_id: int) -> Dict[str, Any]:
        """
        获取套件中各变量的中位数值

        Args:
            suite_id: suite ID

        Returns:
            变量名 -> 中位数值的字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取所有变量及其取值
                cursor.execute("""
                    SELECT cvv.variable_name, cvv.variable_value
                    FROM case_variable_values cvv
                    JOIN case_definitions cd ON cvv.case_id = cd.id
                    WHERE cd.suite_id = ?
                    ORDER BY cvv.variable_name, cvv.variable_value
                """, (suite_id,))

                variable_values = {}
                for row in cursor.fetchall():
                    var_name, var_value = row
                    if var_name not in variable_values:
                        variable_values[var_name] = []

                    try:
                        # 尝试转换为数值
                        if '.' in var_value:
                            num_value = float(var_value)
                        else:
                            num_value = int(var_value)
                        variable_values[var_name].append(num_value)
                    except ValueError:
                        # 如果不是数值，跳过
                        continue

                # 计算每个变量的中位数
                median_values = {}
                for var_name, values in variable_values.items():
                    if len(values) > 1:  # 至少有两个不同的值才有意义
                        values.sort()
                        n = len(values)
                        if n % 2 == 0:
                            median_values[var_name] = (values[n//2 - 1] + values[n//2]) / 2
                        else:
                            median_values[var_name] = values[n//2]
                    else:
                        median_values[var_name] = values[0] if values else None

                return median_values

        except Exception as e:
            self.logger.error(f"获取变量中位数值失败: {e}")
            return {}

    
    def _extract_variables_data(self, cursor, case_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        提取案例的变量数据

        Args:
            cursor: 数据库游标
            case_ids: 案例ID列表

        Returns:
            案例变量数据字典 {case_id: {variable_name: variable_value}}
        """
        try:
            placeholders = ','.join(['?' for _ in case_ids])
            cursor.execute(f"""
                SELECT case_id, variable_name, variable_value
                FROM case_variable_values
                WHERE case_id IN ({placeholders})
                ORDER BY case_id, variable_name
            """, case_ids)

            variables_data = {}
            for row in cursor.fetchall():
                case_id, var_name, var_value = row

                if case_id not in variables_data:
                    variables_data[case_id] = {}

                # 尝试转换为数值
                try:
                    if '.' in var_value:
                        variables_data[case_id][var_name] = float(var_value)
                    else:
                        variables_data[case_id][var_name] = int(var_value)
                except ValueError:
                    variables_data[case_id][var_name] = var_value

            return variables_data

        except Exception as e:
            self.logger.error(f"提取变量数据失败: {e}")
            raise

    def validate_analysis_parameters(self, suite_id: int,
                                   x_variable: Optional[str] = None,
                                   y_variable: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证分析参数的有效性

        Args:
            suite_id: suite ID
            x_variable: X轴变量名
            y_variable: Y轴变量名

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 检查suite是否存在
            suite_list = self.get_suite_list()
            suite_ids = [s['id'] for s in suite_list]
            if suite_id not in suite_ids:
                return False, f"Suite {suite_id} 不存在"

            # 获取可用变量
            available_variables = self.get_suite_variables(suite_id)

            # 检查变量是否存在
            if x_variable and x_variable not in available_variables:
                return False, f"变量 '{x_variable}' 不存在，可用变量: {', '.join(available_variables)}"

            if y_variable and y_variable not in available_variables:
                return False, f"变量 '{y_variable}' 不存在，可用变量: {', '.join(available_variables)}"

            # 检查是否有数据
            result_types = self.get_suite_result_types(suite_id)
            if not result_types:
                return False, f"Suite {suite_id} 没有结果数据"

            return True, ""

        except Exception as e:
            return False, f"验证失败: {e}"

    def extract_single_variable_data(self, suite_id: int,
                                   target_variable: str,
                                   fixed_params: Optional[Dict[str, Any]] = None,
                                   result_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        提取单变量分析数据 - 正式分析模式

        Args:
            suite_id: suite ID
            target_variable: 目标分析变量
            fixed_params: 其他变量的固定值字典
            result_types: 要分析的结果类型列表（可选，默认全部）

        Returns:
            分析数据字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取suite基本信息
                cursor.execute("SELECT name, model_name FROM suites WHERE id = ?", (suite_id,))
                suite_info = cursor.fetchone()
                if not suite_info:
                    raise ValueError(f"Suite {suite_id} 不存在")

                suite_name, model_name = suite_info

                # 获取结果类型
                if result_types is None:
                    result_types = self.get_suite_result_types(suite_id)

                # 构建基本查询
                base_query = """
                    SELECT
                        cd.id as case_id,
                        cd.name as case_name,
                        br.result_type,
                        br.result_parameter,
                        br.mean_value,
                        br.std_value,
                        br.unit
                    FROM case_definitions cd
                    JOIN benchmark_results br ON cd.id = br.case_id
                    WHERE cd.suite_id = ?
                """
                params = [suite_id]

                # 如果指定了结果类型，添加过滤
                if result_types:
                    placeholders = ','.join(['?' for _ in result_types])
                    base_query += f" AND br.result_type IN ({placeholders})"
                    params.extend(result_types)

                base_query += " ORDER BY cd.id, br.result_type"
                cursor.execute(base_query, params)
                rows = cursor.fetchall()

                if not rows:
                    return {
                        'suite_info': {
                            'id': suite_id,
                            'name': suite_name,
                            'model_name': model_name
                        },
                        'variables': {},
                        'data': {},
                        'result_types': [],
                        'analysis_mode': 'single_variable',
                        'target_variable': target_variable,
                        'fixed_params': fixed_params or {}
                    }

                # 获取案例id用于后续筛选
                case_ids = list(set(row[0] for row in rows))

                # 获取所有案例的变量数据
                variables_data = self._extract_variables_data(cursor, case_ids)

                # 单变量分析: 筛选符合条件的案例
                filtered_case_ids = []
                if fixed_params:
                    for case_id in case_ids:
                        should_include = True

                        # 检查固定参数是否匹配
                        for param_name, param_value in fixed_params.items():
                            if param_name == target_variable:
                                continue  # 跳过目标变量

                            case_var_value = variables_data.get(case_id, {}).get(param_name)
                            if case_var_value is None:
                                should_include = False
                                break

                            # 比较变量值是否匹配固定值
                            try:
                                case_numeric = float(case_var_value) if isinstance(case_var_value, str) else case_var_value
                                fixed_numeric = float(param_value) if isinstance(param_value, str) else param_value

                                # 允许小数精度误差
                                if abs(case_numeric - fixed_numeric) > 1e-6:
                                    should_include = False
                                    break
                            except (ValueError, TypeError):
                                # 字符串类型需要精确匹配
                                if str(case_var_value) != str(param_value):
                                    should_include = False
                                    break

                        if should_include:
                            filtered_case_ids.append(case_id)

                    if not filtered_case_ids:
                        self.logger.warning("没有找到符合条件的案例进行单变量分析")
                        # 降级为仅按目标变量筛选
                        filtered_case_ids = case_ids
                else:
                    filtered_case_ids = case_ids

                self.logger.info(f"单变量分析筛选: 从{len(case_ids)}个案例中选择了{len(filtered_case_ids)}个案例")

                # 重新组织结果数据，只使用筛选后的案例
                analysis_data = {
                    'suite_info': {
                        'id': suite_id,
                        'name': suite_name,
                        'model_name': model_name
                    },
                    'variables': variables_data,
                    'data': {},
                    'result_types': result_types,
                    'analysis_mode': 'single_variable',
                    'target_variable': target_variable,
                    'fixed_params': fixed_params or {},
                    'filtered_cases': len(filtered_case_ids),
                    'total_cases': len(case_ids)
                }

                # 只处理筛选后的案例的数据
                for row in rows:
                    case_id, case_name, result_type, result_param, mean_val, std_val, unit = row
                    if case_id not in filtered_case_ids:
                        continue

                    # 按结果类型组织数据
                    if result_type not in analysis_data['data']:
                        analysis_data['data'][result_type] = {
                            'case_ids': [],
                            'case_names': [],
                            'result_parameters': [],
                            'mean_values': [],
                            'std_values': [],
                            'units': [],
                            'x_values': [],  # 目标变量值
                            'y_values': []   # 固定参数值（用于显示）
                        }

                    data_dict = analysis_data['data'][result_type]
                    data_dict['case_ids'].append(case_id)
                    data_dict['case_names'].append(case_name)
                    data_dict['result_parameters'].append(result_param)
                    data_dict['mean_values'].append(mean_val)
                    data_dict['std_values'].append(std_val)
                    data_dict['units'].append(unit)

                # 为每个结果类型添加变量数据
                for result_type in analysis_data['data']:
                    data_dict = analysis_data['data'][result_type]

                    for case_id in data_dict['case_ids']:
                        # 获取目标变量值作为X轴
                        target_val = variables_data.get(case_id, {}).get(target_variable, None)
                        data_dict['x_values'].append(target_val)

                        # 对于Y轴，如果是单变量分析，可以保持为空或者设置为固定参数的组合
                        # 这里我们设置为固定参数的描述
                        if fixed_params:
                            # 创建一个简洁的固定参数标识
                            fixed_desc = []
                            for param, value in fixed_params.items():
                                if param != target_variable:
                                    fixed_desc.append(f"{param}={value}")
                            data_dict['y_values'].append(", ".join(fixed_desc))
                        else:
                            data_dict['y_values'].append(None)

                return analysis_data

        except Exception as e:
            self.logger.error(f"提取单变量分析数据失败: {e}")
            raise