#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 创建分析历史表

用于分析结果的索引和管理
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def create_analysis_history_table():
    """创建分析历史记录表"""

    # 检测数据库路径
    current_dir = Path(__file__).parent
    if current_dir.name == "framework":
        db_path = current_dir.parent / "data" / "benchmark_results.db"
    else:
        db_path = current_dir / "data" / "benchmark_results.db"

    # 确保数据库目录存在
    db_path.parent.mkdir(exist_ok=True)

    # 连接数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 创建表SQL
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suite_id INTEGER NOT NULL,
        analysis_type VARCHAR(50) NOT NULL,
        target_variable VARCHAR(100),
        fixed_params TEXT,  -- JSON格式存储固定参数
        result_types TEXT,  -- JSON格式存储结果类型列表

        -- 分析结果统计
        total_cases INTEGER DEFAULT 0,
        successful_cases INTEGER DEFAULT 0,
        regression_result_summary TEXT,  -- 回归分析摘要

        -- 路径信息
        analysis_dir VARCHAR(500) NOT NULL,
        web_url VARCHAR(500),

        -- 元数据
        analysis_status VARCHAR(20) DEFAULT 'completed',
        error_message TEXT,

        -- 时间戳
        analysis_duration_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,

        -- 外键约束
        FOREIGN KEY (suite_id) REFERENCES suites (id)
    )
    '''

    try:
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_history'")
        table_exists = cursor.fetchone() is not None

        cursor.execute(create_table_sql)

        # 创建索引提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_analysis_suite_id
            ON analysis_history(suite_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_analysis_type_variable
            ON analysis_history(analysis_type, target_variable)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_analysis_created_at
            ON analysis_history(created_at)
        ''')

        conn.commit()

        if not table_exists:
            print("✓ 分析历史表创建成功")
            # 显示表结构
            cursor.execute("PRAGMA table_info(analysis_history)")
            columns = cursor.fetchall()
            print("\n表结构:")
            for col in columns:
                print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3]==1 else 'NULL'}")

    except sqlite3.Error as e:
        print(f"✗ 创建表失败: {e}")
        return False

    return True

def get_db_connection():
    """获取数据库连接"""
    # 检测数据库路径
    current_dir = Path(__file__).parent
    if current_dir.name == "framework":
        db_path = current_dir.parent / "data" / "benchmark_results.db"
    else:
        db_path = current_dir / "data" / "benchmark_results.db"

    return sqlite3.connect(str(db_path))

if __name__ == "__main__":
    create_analysis_history_table()