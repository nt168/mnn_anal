#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析历史数据库管理器

管理分析结果的索引、查询和记录
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

class AnalysisManager:
    """分析历史管理器"""

    def __init__(self, db_path: str = None):
        """初始化数据库连接"""
        if db_path is None:
            # 自动检测项目根目录并构建数据库路径
            current_dir = Path(__file__).parent.parent
            if current_dir.name == "framework":
                db_path = current_dir.parent / "data" / "benchmark_results.db"
            else:
                db_path = current_dir / "data" / "benchmark_results.db"

        self.db_path = str(db_path)
        self._ensure_table()

    def _ensure_table(self):
        """确保分析历史表存在"""
        from .create_analysis_table import create_analysis_history_table
        create_analysis_history_table()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 允许按列名访问
        return conn

    def record_analysis(self,
                       suite_id: int,
                       analysis_type: str,
                       target_variable: Optional[str] = None,
                       fixed_params: Optional[Dict[str, Any]] = None,
                       result_types: Optional[List[str]] = None,
                       analysis_dir: str = "",
                       web_url: str = "",
                       total_cases: int = 0,
                       successful_cases: int = 0,
                       regression_summary: Optional[Dict[str, Any]] = None,
                       duration_ms: int = 0,
                       status: str = "completed",
                       error_message: Optional[str] = None, completed_at: Optional[datetime] = None) -> int:
        """
        记录分析历史

        Args:
            suite_id: 套件ID
            analysis_type: 分析类型 (single_variable, multi_variable, correlation等)
            target_variable: 目标变量名
            fixed_params: 固定参数字典
            result_types: 分析的结果类型列表
            analysis_dir: 分析目录路径
            web_url: Web访问URL
            total_cases: 总案例数
            successful_cases: 成功案例数
            regression_summary: 回归分析摘要
            duration_ms: 分析耗时（毫秒）
            status: 分析状态
            error_message: 错误信息

        Returns:
            新创建的分析记录ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO analysis_history (
                    suite_id, analysis_type, target_variable, fixed_params, result_types,
                    total_cases, successful_cases, regression_result_summary,
                    analysis_dir, web_url, analysis_status, error_message,
                    analysis_duration_ms, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                suite_id,
                analysis_type,
                target_variable,
                json.dumps(fixed_params) if fixed_params else None,
                json.dumps(result_types) if result_types else None,
                total_cases,
                successful_cases,
                json.dumps(regression_summary) if regression_summary else None,
                analysis_dir,
                web_url,
                status,
                error_message,
                duration_ms,
                completed_at if completed_at else datetime.now()
            ))

            analysis_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return analysis_id

        except sqlite3.Error as e:
            print(f"✗ 记录分析历史失败: {e}")
            return -1

    def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取分析记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM analysis_history WHERE id = ?', (analysis_id,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
                # 解析JSON字段
                if result['fixed_params']:
                    result['fixed_params'] = json.loads(result['fixed_params'])
                if result['result_types']:
                    result['result_types'] = json.loads(result['result_types'])
                if result['regression_result_summary']:
                    result['regression_result_summary'] = json.loads(result['regression_result_summary'])

                return result

            return None

        except sqlite3.Error as e:
            print(f"✗ 查询分析记录失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def get_analyses_by_suite(self, suite_id: int) -> List[Dict[str, Any]]:
        """获取指定套件的所有分析记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM analysis_history WHERE suite_id = ? ORDER BY created_at DESC',
                (suite_id,)
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                # 解析JSON字段
                if result['fixed_params']:
                    result['fixed_params'] = json.loads(result['fixed_params'])
                if result['result_types']:
                    result['result_types'] = json.loads(result['result_types'])
                if result['regression_result_summary']:
                    result['regression_result_summary'] = json.loads(result['regression_result_summary'])

                results.append(result)

            return results

        except sqlite3.Error as e:
            print(f"✗ 查询套件分析记录失败: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def get_latest_analysis_by_variable(self, suite_id: int, target_variable: str) -> Optional[Dict[str, Any]]:
        """获取指定变量的最新分析记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM analysis_history
                WHERE suite_id = ? AND target_variable = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (suite_id, target_variable))

            row = cursor.fetchone()

            if row:
                result = dict(row)
                # 解析JSON字段
                if result['fixed_params']:
                    result['fixed_params'] = json.loads(result['fixed_params'])
                if result['result_types']:
                    result['result_types'] = json.loads(result['result_types'])
                if result['regression_result_summary']:
                    result['regression_result_summary'] = json.loads(result['regression_result_summary'])

                return result

            return None

        except sqlite3.Error as e:
            print(f"✗ 查询最新分析记录失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def list_analysis_summary(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的分析摘要"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ah.id, ah.suite_id, s.name as suite_name, s.model_name,
                       ah.analysis_type, ah.target_variable, ah.fixed_params,
                       ah.regression_result_summary, ah.analysis_dir, ah.web_url,
                       ah.analysis_status, ah.created_at, ah.analysis_duration_ms
                FROM analysis_history ah
                JOIN suites s ON ah.suite_id = s.id
                ORDER BY ah.created_at DESC
                LIMIT ?
            ''', (limit,))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                # 解析JSON字段
                if result.get('fixed_params'):
                    result['fixed_params'] = json.loads(result['fixed_params'])
                if result.get('regression_result_summary'):
                    result['regression_result_summary'] = json.loads(result['regression_result_summary'])

                results.append(result)

            return results

        except sqlite3.Error as e:
            print(f"✗ 查询分析摘要失败: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def check_duplicate_analysis(self, suite_id: int, target_variable: str,
                               fixed_params: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """检查是否存在重复的分析，存在则返回记录ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 将固定参数转JSON用于比较
            fixed_params_json = json.dumps(fixed_params, sort_keys=True) if fixed_params else None

            cursor.execute('''
                SELECT id FROM analysis_history
                WHERE suite_id = ? AND target_variable = ?
                AND COALESCE(fixed_params, '{}') = COALESCE(?, '{}')
                AND analysis_status = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (suite_id, target_variable, fixed_params_json or '{}'))

            row = cursor.fetchone()
            return row['id'] if row else None

        except sqlite3.Error as e:
            print(f"✗ 检查重复分析失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def delete_analysis(self, analysis_id: int) -> bool:
        """
        删除分析记录

        Args:
            analysis_id: 要删除的分析记录ID

        Returns:
            是否成功删除
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 先检查是否存在该记录
            cursor.execute('SELECT COUNT(*) FROM analysis_history WHERE id = ?', (analysis_id,))
            if cursor.fetchone()[0] == 0:
                return False

            # 删除记录
            cursor.execute('DELETE FROM analysis_history WHERE id = ?', (analysis_id,))

            if cursor.rowcount > 0:
                conn.commit()
                return True
            else:
                return False

        except sqlite3.Error as e:
            print(f"✗ 删除分析记录失败: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()