#!/usr/bin/env python3
"""
MNN LLM Bench Web服务器
用于展示基准测试数据分析结果
"""

import sqlite3
import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'benchmark_results.db')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 参数基本属性定义
PARAM_METADATA = {
    'precision': {
        'name': '精度',
        'cli': '--precision',
        'note': '运行精度，默认值：2（低精度最快）'
    },
    'threads': {
        'name': '线程数',
        'cli': '--threads',
        'note': '运行的线程数，默认值：4'
    },
    'n_prompt': {
        'name': '输入长度',
        'cli': '--n-prompt',
        'note': '输入序列长度，默认值：512'
    },
    'n_gen': {
        'name': '生成长度',
        'cli': '--n-gen',
        'note': '输出序列长度，默认值：128'
    },
    'prompt_gen': {
        'name': 'PG组合',
        'cli': '--prompt-gen',
        'note': '提示词生成组合参数，默认值：无'
    },
    'mmap': {
        'name': '内存映射',
        'cli': '--mmap',
        'note': '内存映射模式，默认值：0（禁用）'
    },
    'n_repeat': {
        'name': '重复次数',
        'cli': '--n-repeat',
        'note': '测试重复次数，默认值：5'
    },
    'kv_cache': {
        'name': 'KV缓存',
        'cli': '--kv-cache',
        'note': 'KV缓存开关，默认值：false（禁用）'
    },
    'dynamicOption': {
        'name': '动态优化',
        'cli': '--dynamicOption',
        'note': '动态优化级别，默认值：0（不优化）'
    },
    'variable_prompt': {
        'name': '可变提示词',
        'cli': '--variable-prompt',
        'note': '可变提示词模式，默认值：0（固定模式）'
    },
    'prompt_file': {
        'name': '提示词文件',
        'cli': '--prompt-file',
        'note': '提示词文件路径，默认值：无（使用内置提示词）'
    }
}

def init_database():
    """检查数据库是否存在，不存在则提示用户"""
    if not os.path.exists(DB_PATH):
        return False

    # 执行数据库迁移
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 检查是否需要添加新字段
        cursor.execute('PRAGMA table_info(tasks)')
        columns = [row[1] for row in cursor.fetchall()]

        # 添加新字段（如果不存在）
        if 'original_name' not in columns:
            cursor.execute('ALTER TABLE tasks ADD COLUMN original_name TEXT')
        if 'run_number' not in columns:
            cursor.execute('ALTER TABLE tasks ADD COLUMN run_number INTEGER')

        # 迁移现有数据
        cursor.execute('SELECT id, name FROM tasks WHERE original_name IS NULL OR run_number IS NULL')
        existing_tasks = cursor.fetchall()

        for task_id, task_name in existing_tasks:
            if '_20' in task_name:  # 检查是否有时间戳格式
                parts = task_name.split('_')
                if len(parts) >= 3:
                    # 提取原始名称
                    original_name = '_'.join(parts[:-2])

                    # 计算运行次数
                    cursor.execute('SELECT COUNT(*) FROM tasks WHERE name LIKE ? AND id <= ?',
                                 (f"{original_name}_%", task_id))
                    run_number = cursor.fetchone()[0]
                else:
                    original_name = task_name
                    run_number = 1
            else:
                original_name = task_name
                run_number = 1

            # 更新记录
            cursor.execute('''
                UPDATE tasks SET
                    original_name = ?,
                    run_number = ?
                WHERE id = ?
            ''', (original_name, run_number, task_id))

        conn.commit()
    return True

@app.route('/')
def index():
    """首页：按任务分组显示套件，支持分页"""
    if not init_database():
        return render_template('error.html', message="数据库文件不存在，请先运行基准测试生成数据")

    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    # 限制每页任务的合理范围
    if per_page < 5:
        per_page = 5
    elif per_page > 100:
        per_page = 100

    offset = (page - 1) * per_page

    conn = get_db_connection()
    try:
        # 获取任务总数用于分页
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

        # 获取当前页的任务（按创建时间倒序）
        task_rows = conn.execute("""
            SELECT t.id, t.name, t.original_name, t.run_number, t.description, t.status, t.created_at, t.updated_at
            FROM tasks t
            ORDER BY t.updated_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()

        tasks = []
        for task_row in task_rows:
            task = dict(task_row)

            # 获取该任务下的所有套件
            suite_rows = conn.execute("""
                SELECT s.id, s.name, s.model_name, s.suite_yaml, s.created_at
                FROM suites s
                WHERE s.task_id = ?
                ORDER BY s.created_at DESC
            """, (task['id'],)).fetchall()

            task_suites = []
            total_cases = 0
            for suite_row in suite_rows:
                suite = dict(suite_row)

                # 获取该套件的测试用例数量
                case_count = conn.execute(
                    "SELECT COUNT(*) FROM case_definitions WHERE suite_id = ?",
                    (suite['id'],)
                ).fetchone()[0]

                suite['case_count'] = case_count
                total_cases += case_count

                # 从suite_yaml中提取描述信息
                if suite.get('suite_yaml'):
                    try:
                        import json
                        suite_config = json.loads(suite['suite_yaml'])
                        suite['description'] = suite_config.get('description', suite['name'])
                    except:
                        suite['description'] = suite['name']
                else:
                    suite['description'] = suite['name']

                task_suites.append(suite)

            task['suites'] = task_suites
            task['total_cases'] = total_cases
            task['suite_count'] = len(task_suites)
            tasks.append(task)

        # 计算分页信息
        total_pages = (total_tasks + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

        return render_template('index.html',
                             tasks=tasks,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             has_prev=has_prev,
                             has_next=has_next,
                             total_tasks=total_tasks)
    finally:
        conn.close()

@app.route('/api/suites')
def api_suites():
    """API: 获取所有套件信息的JSON格式"""
    if not init_database():
        return jsonify({"error": "数据库文件不存在"}), 404

    conn = get_db_connection()
    try:
        suites = conn.execute("SELECT * FROM suites ORDER BY created_at DESC").fetchall()
        result = []
        for suite in suites:
            result.append({
                'id': suite['id'],
                'name': suite['name'],
                'model_name': suite['model_name'],
                'model_path': suite['model_path'],
                'config': suite['suite_yaml'],
                'created_at': suite['created_at']
            })
        return jsonify(result)
    finally:
        conn.close()

def get_suite_analysis_results(suite_id):
    """从数据库获取指定套件的分析报告列表"""
    try:
        conn = get_db_connection()

        # 查询该套件的所有分析记录
        analyses = conn.execute("""
            SELECT id, analysis_type, target_variable, fixed_params, result_types,
                   analysis_duration_ms, completed_at, analysis_dir, web_url
            FROM analysis_history
            WHERE suite_id = ? AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
        """, (suite_id,)).fetchall()

        analysis_results = []

        for analysis in analyses:
            analysis_dict = dict(analysis)
            # 添加默认的status字段以保持兼容性
            analysis_dict['analysis_status'] = 'completed'

            # 解析固定参数
            fixed_params = None
            if analysis_dict['fixed_params']:
                try:
                    import json
                    fixed_params = json.loads(analysis_dict['fixed_params'])
                except:
                    pass

            # 解析结果类型
            result_types = []
            try:
                import json
                result_types = json.loads(analysis_dict['result_types']) or []
            except:
                pass

            # 直接使用数据库中存储的路径信息
            if analysis_dict['completed_at'] and analysis_dict.get('web_url'):
                from pathlib import Path

                # 使用数据库中的web_url，但要添加开头的 '/'
                html_url = f"/{analysis_dict['web_url'].lstrip('/')}"

                # 从html_url路径构建其他文件的路径
                html_path = Path(html_url)
                base_path = str(html_path.parent)

                analysis_results.append({
                    'id': analysis_dict['id'],
                    'analysis_type': analysis_dict['analysis_type'],
                    'target_variable': analysis_dict['target_variable'],
                    'fixed_params': fixed_params,
                    'result_types': result_types,
                    'completed_at': analysis_dict['completed_at'],
                    'duration_ms': analysis_dict['analysis_duration_ms'],
                    'html_url': html_url,
                    'md_url': f"{base_path}/analysis_report.md",
                    'zip_url': f"{base_path}/report_package.zip"
                })

        conn.close()
        return analysis_results

    except Exception as e:
        print(f"ERROR getting analysis results for suite {suite_id}: {e}")
        return []

@app.route('/suite/<int:suite_id>')
def suite_detail(suite_id):
    """套件详情页"""
    if not init_database():
        return render_template('error.html', message="数据库文件不存在")

    conn = get_db_connection()
    try:
        # 获取套件信息
        suite = conn.execute("SELECT * FROM suites WHERE id = ?", (suite_id,)).fetchone()
        if not suite:
            return render_template('error.html', message="套件不存在"), 404

        # 解析suite配置获取中文描述和参数分类
        suite_dict = dict(suite)
        suite_config = None
        if suite_dict.get('suite_yaml'):
            try:
                import json
                import html
                # 解码HTML实体
                decoded_yaml = html.unescape(suite_dict['suite_yaml'])
                suite_config = json.loads(decoded_yaml)
                suite_dict['description'] = suite_config.get('description', suite_dict['name'])

                # 提取参数配置
                fixed_params = suite_config.get('fixed_params', {})
                variables = suite_config.get('variables', [])

                # 目标参数列表（只关心这11个参数）
                target_params = list(PARAM_METADATA.keys())

                # 基于llm_bench真实的默认参数列表
                llm_bench_defaults = {
                    'precision': 2,
                    'threads': 4,
                    'n_prompt': 512,
                    'n_gen': 128,
                    'prompt_gen': None,        # 表示没有默认值
                    'mmap': 0,
                    'n_repeat': 5,
                    'kv_cache': 'false',
                    'dynamicOption': 0,
                    'variable_prompt': 0,
                    'prompt_file': None         # 表示没有默认值
                }

                # 分类参数存储
                suite_fixed_values = []  # 固定值参数
                suite_default_values = []  # 默认值参数
                suite_variable_params = []  # 变量参数

                # 识别变量参数
                for var_config in variables:
                    var_name = var_config.get('name')
                    if var_name and var_name in target_params:
                        suite_variable_params.append({
                            'name': var_name,
                            'param_meta': PARAM_METADATA[var_name]
                        })

                # 识别套件不变参数：在fixed_params中或默认值中但不在variables中的参数
                for param_name in target_params:
                    # 如果是变量参数则跳过
                    if any(v['name'] == param_name for v in suite_variable_params):
                        continue

                    # 在固定参数中？
                    if param_name in fixed_params:
                        param_value = fixed_params[param_name]
                        param_type = '固定'
                        param_display_value = param_value
                    else:
                        # 不是变量也不是固定参数，即为默认值参数
                        param_type = '默认'
                        param_display_value = '默认值'

                    # 添加到对应分类
                    param_info = {
                        'name': param_name,
                        'type': param_type,
                        'value': param_display_value,
                        'param_meta': PARAM_METADATA[param_name]
                    }

                    if param_type == '固定':
                        suite_fixed_values.append(param_info)
                    else:
                        suite_default_values.append(param_info)

                # 存储分类后的参数信息
                suite_dict['suite_fixed_values'] = suite_fixed_values
                suite_dict['suite_default_values'] = suite_default_values
                suite_dict['suite_variable_params'] = suite_variable_params

            except Exception as e:
                print(f"ERROR parsing suite {suite_id}: {e}")
                import traceback
                traceback.print_exc()
                suite_dict['description'] = suite_dict['name']
                # 提供默认的空分类
                suite_dict['suite_fixed_values'] = []
                suite_dict['suite_default_values'] = []
                suite_dict['suite_variable_params'] = []
        else:
            suite_dict['description'] = suite_dict['name']
            # 提供默认的空分类
            suite_dict['suite_fixed_values'] = []
            suite_dict['suite_default_values'] = []
            suite_dict['suite_variable_params'] = []

        # 获取该套件的模型大小（从第一个case获取）
        model_size = conn.execute(
            "SELECT DISTINCT model_size FROM case_definitions WHERE suite_id = ? LIMIT 1",
            (suite_id,)
        ).fetchone()
        if model_size:
            suite_dict['model_size'] = model_size[0]

        suite = type('Row', (), suite_dict)()  # 转换为Row对象

        # 获取该套件的所有测试用例
        cases = conn.execute("""
            SELECT cd.*, cv.variable_name, cv.variable_value
            FROM case_definitions cd
            LEFT JOIN case_variable_values cv ON cd.id = cv.case_id
            WHERE cd.suite_id = ?
            ORDER BY cd.id, cv.id
        """, (suite_id,)).fetchall()

        # 重组数据结构：按case分组
        cases_dict = {}
        for row in cases:
            case_id = row['id']
            if case_id not in cases_dict:
                cases_dict[case_id] = {
                    'id': row['id'],
                    'name': row['name'],
                    'base_parameters': row['base_parameters'],
                    'model_size': row['model_size'],
                    'backend': row['backend'],
                    'threads': row['threads'],
                    'precision': row['precision'],
                    'execution_time_seconds': row['execution_time_seconds'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'variables': {},
                    'variable_params': [],  # 新增：变量参数详细信息
                    'results': []
                }

            # 添加变量信息
            if row['variable_name']:
                var_name = row['variable_name']
                var_value = row['variable_value']
                cases_dict[case_id]['variables'][var_name] = var_value

                # 添加变量参数详细信息（仅在套件variables中定义的参数）
                # 检查这个变量是否真的在套件的variables中定义
                suite_variables = [var['name'] for var in suite_variable_params]
                if var_name in PARAM_METADATA and var_name in suite_variables:
                    cases_dict[case_id]['variable_params'].append({
                        'name': var_name,
                        'value': var_value,
                        'param_meta': PARAM_METADATA[var_name]
                    })

        # 为每个case设置pType并获取测试结果
        for case_id in cases_dict.keys():
            # 计算case的pType - 基于base_parameters
            base_params = cases_dict[case_id]['base_parameters']
            case_ptype = 'fix'  # 默认值
            if base_params:
                try:
                    import json
                    params = json.loads(base_params) if isinstance(base_params, str) else base_params
                    if 'prompt_file' in params:
                        case_ptype = 'file'
                    elif 'variable_prompt' in params and params['variable_prompt']:
                        case_ptype = 'variable'
                    else:
                        case_ptype = 'fix'
                except:
                    case_ptype = 'fix'
            # 将pType直接添加到case字典中，供模板使用
            cases_dict[case_id]['ptypes'] = case_ptype

            results = conn.execute("""
                SELECT * FROM benchmark_results
                WHERE case_id = ?
                ORDER BY created_at ASC
            """, (case_id,)).fetchall()

            # 转换为字典，提取实际运行参数，使用数据库中的ptypes（如果没有则使用计算的pType）
            actual_pp_length = None
            actual_tg_length = None

            for i, result_row in enumerate(results):
                result_dict = dict(result_row)
                # 如果数据库结果中有ptypes就使用，否则使用计算的pType
                if not result_dict.get('ptypes') or result_dict['ptypes'] == 'fix':
                    result_dict['ptypes'] = case_ptype

                # 提取实际运行参数从结果中
                if result_dict['result_type'] == 'pp':
                    actual_pp_length = result_dict.get('result_parameter')
                elif result_dict['result_type'] == 'tg':
                    actual_tg_length = result_dict.get('result_parameter')

                results[i] = result_dict

            # 将实际运行参数添加到case中，供模板使用
            cases_dict[case_id]['actual_pp'] = actual_pp_length
            cases_dict[case_id]['actual_tg'] = actual_tg_length

            cases_dict[case_id]['results'] = results

        # 转换为列表
        case_list = list(cases_dict.values())

        # 获取分析结果
        analysis_results = get_suite_analysis_results(suite_id)

        return render_template('suite_detail.html', suite=suite, cases=case_list, analysis_results=analysis_results)
    finally:
        conn.close()

@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("启动MNN LLM Bench Web服务器...")
    print(f"数据库路径: {DB_PATH}")

    if not init_database():
        print("警告: 数据库文件不存在，请先运行基准测试生成数据")

    # 工作在0.0.0.0上，端口9998（避免与常用端口冲突）
    app.run(host='0.0.0.0', port=9998, debug=True)