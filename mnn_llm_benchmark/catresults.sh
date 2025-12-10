import sqlite3

conn = sqlite3.connect('data/benchmark_results.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT
        rt.name as task_name,
        s.model_name,
        cd.name as case_name,
        br.result_type,
        br.result_parameter,
        br.mean_value,
        br.std_value
    FROM benchmark_results br
    JOIN case_definitions cd ON br.case_id = cd.id
    JOIN suites s ON cd.suite_id = s.id
    JOIN tasks rt ON s.task_id = rt.id
    ORDER BY br.created_at DESC
    LIMIT -1;
""")

for row in cursor.fetchall():
    task_name, model_name, case_name, result_type, result_param, mean_value, std_value = row
    print(
        f"任务: {task_name}, 模型: {model_name}, 用例: {case_name}, "
        f"类型: {result_type}, 参数: {result_param}, "
        f"性能: {mean_value:.2f}±{std_value:.2f}"
    )

conn.close()
