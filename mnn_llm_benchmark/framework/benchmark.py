#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MNN LLM基准测试工具 - 重构版本入口

专注于：自动化性能评估 + 结果数据收集

新的模块化架构：
- core/: 核心MNN执行器
- single/: 单次基准测试
- batch/: 批量基准测试
"""

import argparse
import sys
from pathlib import Path

# 当前脚本作为命令行工具运行时，需要添加项目根目录到路径
framework_dir = Path(__file__).parent
project_root = framework_dir.parent
sys.path.insert(0, str(project_root))

# 工具和配置模块导入
from utils.output import ColorOutput
from utils.exceptions import BenchmarkError
from config.models import ModelsConfig
from config.system import SystemConfig

# 基准测试模块导入（使用新的模块化结构）
from benchmark.single.runner import SingleBenchmark
from benchmark.batch.orchestrator import BatchBenchmark


def show_available_models():
    """显示可用模型列表"""
    models_config_manager = ModelsConfig()
    available_models = models_config_manager._load_config()
    print("可用的模型别名:")
    for alias in available_models.keys():
        print(f"  {alias}")
    return available_models.keys()


def handle_benchmark_error(error_info):
    """在最外层处理基准测试错误信息"""

    model_alias = error_info.get('model_alias', 'unknown')
    model_info = error_info.get('model_info', {})
    execution_result = error_info.get('execution_result', None)
    error_msg = error_info.get('error', '')

    print(f"\n{ColorOutput.red(f'✗ {model_alias} 测试失败')}")
    if model_info.get('name'):
        print(f"  模型: {model_info.get('name')}")

    # 显示基本错误信息
    if error_msg and error_msg.strip():
        print(f"  错误: {error_msg.strip()}")

    # 显示执行结果（如果存在）
    if execution_result:
        return_code = execution_result.get('return_code', 'unknown')
        stderr = execution_result.get('stderr', '')
        stdout = execution_result.get('stdout', '')

        if return_code != 'unknown':
            print(f"  返回码: {return_code}")

        if stderr and stderr.strip():
            print(f"  stderr: {stderr.strip()}")
        if stdout and stdout.strip():
            print(f"  stdout: {stdout.strip()}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MNN LLM基准测试工具")

    # 基本参数（单次测试）
    parser.add_argument("models", nargs="*", help="单次测试：模型别名列表，不指定则显示可用别名")

    # 批量测试模式参数
    parser.add_argument("-b", "--batch", type=str, help="批量测试：指定YAML编排文件路径")
    parser.add_argument("--preview", action="store_true", help="预览批量测试任务（仅显示计划，不执行）")
    parser.add_argument("--create-sample", action="store_true", help="创建示例YAML编排文件到tasks/目录，包含批量测试配置示例")

    # 数据分析模式参数
    parser.add_argument("-a", "--analyze", type=int, help="数据分析：指定Suite ID进行分析")
    parser.add_argument("--list-suites", action="store_true", help="列出所有可用的Suite供分析")
    parser.add_argument("--x-variable", type=str, help="分析的自变量（如: n_prompt, threads等）")
    parser.add_argument("--y-variable", type=str, help="分析的第二个自变量（可选）")
    parser.add_argument("--result-types", type=str, help="要分析的结果类型，逗号分隔（如: pp,tg,pp+tg）")

    # 删除分析报告参数
    parser.add_argument("--delete-analysis", type=int, help="删除指定ID的分析报告（删除数据库记录和文件目录）")
    parser.add_argument("--list-analysis", action="store_true", help="列出所有分析报告历史记录")

    # 单变量分析参数
    parser.add_argument("--single-variable", type=str, help="单变量分析：指定要分析的变量名（正式分析模式）")
    parser.add_argument("--fixed-params", type=str, help="其他变量的固定值，JSON格式（如: '{\"threads\": 4, \"precision\": 2}'）")

    # 模型扫描参数
    parser.add_argument("--scan", type=str, help="扫描指定目录并自动添加模型到配置文件")
    parser.add_argument("--overwrite", action="store_true", help="扫描时覆盖已存在的模型别名")

    # 单次测试参数
    parser.add_argument("-t", "--threads", type=int, help="线程数")
    parser.add_argument("-p", "--n-prompt", type=int, help="提示词长度")
    parser.add_argument("-n", "--n-gen", type=int, help="生成长度")
    parser.add_argument("-pg", "--prompt-gen", type=str, help="预填充和生成长度格式: pp,tg (逗号分隔)")
    parser.add_argument("-rep", "--n-repeat", type=int, help="重复次数")
    parser.add_argument("-c", "--precision", type=int, choices=[0, 1, 2], help="精度: (0:Normal,1:High,2:Low)")
    parser.add_argument("-kv", "--kv-cache", type=str, choices=["true", "false"], help="启用KV缓存 (true|false)")
    parser.add_argument("-mmp", "--mmap", type=int, choices=[0, 1], help="启用内存映射 (0|1)")
    parser.add_argument("-dyo", "--dynamicOption", type=int, help="动态选项 (0-8)")

    # 新版llm_bench_prompt参数支持
    parser.add_argument("-vp", "--variable-prompt", type=int, choices=[0, 1], help="可变提示词模式 (0或1)")
    parser.add_argument("-pf", "--prompt-file", type=str, help="提示词文件路径")

    args = parser.parse_args()

    # 如果是删除分析报告模式
    if args.delete_analysis:
        from analysis.analyzer import DataAnalyzer
        analyzer = DataAnalyzer()

        analysis_id = args.delete_analysis
        print(f"\n{ColorOutput.blue('🗑️ 删除分析报告')}")
        print("=" * 60)

        # 获取分析记录信息
        from db.analysis_manager import AnalysisManager
        analysis_manager = AnalysisManager()
        analysis_record = analysis_manager.get_analysis_by_id(analysis_id)

        if not analysis_record:
            print(f"{ColorOutput.red('✗ 分析记录不存在')}: ID {analysis_id}")
            return 1

        # 显示要删除的分析信息
        suite_id = analysis_record['suite_id']
        target_variable = analysis_record['target_variable']
        analysis_dir = analysis_record['analysis_dir']
        created_at = analysis_record['created_at']

        print(f"准备删除分析报告:")
        print(f"  ID: {analysis_id}")
        print(f"  Suite ID: {suite_id}")
        print(f"  目标变量: {target_variable}")
        print(f"  创建时间: {created_at}")
        print(f"  目录: {analysis_dir}")

        # 确认删除
        import sys
        try:
            confirm = input(f"\n{ColorOutput.yellow('确认删除此分析报告? (y/N): ')}").strip().lower()
        except KeyboardInterrupt:
            print("\n删除操作已取消")
            return 1

        if confirm != 'y' and confirm != 'yes':
            print("删除操作已取消")
            return 1

        # 执行删除
        try:
            import shutil

            # 删除文件目录
            analysis_path = Path(analysis_dir)
            if analysis_path.exists():
                shutil.rmtree(analysis_path)
                print(f"{ColorOutput.green('✓ 已删除报告目录')}: {analysis_dir}")
            else:
                print(f"{ColorOutput.yellow('⚠ 报告目录不存在')}: {analysis_dir}")

            # 从数据库删除记录
            if analysis_manager.delete_analysis(analysis_id):
                print(f"{ColorOutput.green('✓ 已删除数据库记录')}: ID {analysis_id}")
            else:
                print(f"{ColorOutput.red('✗ 删除数据库记录失败')}: ID {analysis_id}")

            print(f"{ColorOutput.green('✓ 分析报告删除完成')}")

        except Exception as e:
            print(f"{ColorOutput.red('✗ 删除失败')}: {e}")
            return 1

        return 0

    # 如果是列出分析记录模式
    if args.list_analysis:
        print(f"\n{ColorOutput.blue('📋 分析报告历史记录')}")
        print("=" * 80)

        from db.analysis_manager import AnalysisManager
        analysis_manager = AnalysisManager()
        records = analysis_manager.list_analysis_summary(limit=20)

        if not records:
            print(f"{ColorOutput.yellow('没有找到分析记录')}")
        else:
            print(f"{'ID':<4} {'Suite':<6} {'变量':<12} {'类型':<12} {'状态':<10} {'创建时间':<20}")
            print("-" * 80)
            for record in records:
                suite_id = record['suite_id'] or 'N/A'
                target_var = record['target_variable'] or 'N/A'
                analysis_type = record['analysis_type'] or 'N/A'
                status = record['analysis_status'] or 'N/A'
                created_at = record['created_at'] or 'N/A'

                # 截断创建时间显示
                created_short = str(created_at)[:19] if created_at else 'N/A'

                print(f"{record['id']:<4} {suite_id:<6} {target_var:<12} {analysis_type:<12} {status:<10} {created_short:<20}")
        print()
        return 0

    # 如果是数据分析模式
    if args.analyze or args.list_suites:
        from analysis.analyzer import DataAnalyzer
        analyzer = DataAnalyzer()

        if args.list_suites:
            print(f"\n{ColorOutput.blue('📊 可用的Suite列表')}")
            print("=" * 60)
            suites = analyzer.list_available_suites()
            if suites:
                for suite in suites:
                    print(f"Suite {suite['id']}: {suite['name']} ({suite['model_name']}) - {suite['case_count']}个用例")

                    # 显示变量信息
                    variables = analyzer.get_suite_variables(suite['id'])
                    if variables:
                        print(f"  变量: {', '.join(variables)}")

                    # 显示结果类型
                    result_types = analyzer.get_suite_result_types(suite['id'])
                    if result_types:
                        print(f"  结果类型: {', '.join(result_types)}")
                    print()
            else:
                print(f"{ColorOutput.yellow('没有找到可用的Suite数据')}")
            return 0

        if args.analyze:
            print(f"\n{ColorOutput.blue('🔬 开始数据分析')}")
            print(f"Suite ID: {args.analyze}")

            # 解析结果类型
            result_types = None
            if args.result_types:
                result_types = [t.strip() for t in args.result_types.split(',')]

            # 解析固定参数
            fixed_params = None
            if args.fixed_params:
                try:
                    import json
                    fixed_params = json.loads(args.fixed_params)
                except json.JSONDecodeError as e:
                    print(f"\n{ColorOutput.red('✗ 固定参数JSON格式错误')}")
                    print(f"错误: {e}")
                    return 1

            # 确定分析模式
            analysis_mode = "single_variable" if args.single_variable else "simple"
            target_variable = args.single_variable or args.x_variable

            try:
                # 获取Web服务器静态目录
                system_config = SystemConfig()
                web_static_dir = system_config.get_web_static_dir()

                # 检查目录是否已存在（防止重复分析）
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # 获取suite信息用于生成目录名
                suites = analyzer.list_available_suites()
                suite_info = next((s for s in suites if s['id'] == args.analyze), None)
                if not suite_info:
                    print(f"\n{ColorOutput.red('✗ Suite {args.analyze} 不存在')}")
                    return 1

                # 新的简单命名规则: 分析目录名只包含 suite_id
                web_analysis_dir = web_static_dir / "analysis" / str(args.analyze)

                # 确保 suite 的分析目录存在
                web_analysis_dir.mkdir(parents=True, exist_ok=True)

                # 临时修改报告生成器的输出目录
                original_output_dir = analyzer.report_generator.output_dir
                analyzer.report_generator.output_dir = web_analysis_dir
                web_analysis_dir.mkdir(parents=True, exist_ok=True)

                # 只支持单变量分析
                report_path = analyzer.analyze_single_variable(
                    suite_id=args.analyze,
                    target_variable=target_variable,
                    fixed_params=fixed_params,
                    result_types=result_types
                )

                # 恢复原始输出目录
                analyzer.report_generator.output_dir = original_output_dir

                print(f"\n{ColorOutput.green('✓ 分析完成')}")
                print(f"Suite分析目录: {web_analysis_dir}")
                print(f"\n{ColorOutput.cyan('📂 查看报告:')}")
                # 获取实际生成的报告路径
                actual_report_dir = Path(report_path)
                relative_path = actual_report_dir.relative_to(web_static_dir)
                print(f"实际报告路径: {actual_report_dir}")
                print(f"HTML: http://localhost:9998/{relative_path}/analysis_report.html")
                print(f"Markdown: {actual_report_dir}/analysis_report.md")
                print(f"压缩包: {actual_report_dir}/report_package.zip")
                print(f"\n{ColorOutput.yellow('💡 提示: 启动Web服务器查看报告: ./bench.sh web')}")
                return 0

            except Exception as e:
                print(f"\n{ColorOutput.red('✗ 分析失败')}")
                print(f"错误: {e}")
                return 1

    # 如果是扫描模式
    if args.scan:
        models_config = ModelsConfig()
        print(f"\n{ColorOutput.blue('正在扫描模型目录...')}")
        print(f"目标目录: {args.scan}")
        if args.overwrite:
            print(f"模式: 覆盖现有别名\n")

        count = models_config.scan_and_add_models(args.scan, overwrite=args.overwrite)

        if count > 0:
            print(f"\n{ColorOutput.green(f'成功添加 {count} 个模型到配置文件')}")
            print("\n当前可用模型列表:")
            for alias in models_config.get_available_models():
                print(f"  {alias}")
        else:
            print(f"\n{ColorOutput.yellow('没有发现新模型需要添加')}")
        return 0

    # 如果是批量模式
    if args.batch or args.preview or args.create_sample:
        if args.create_sample:
            batch = BatchBenchmark()
            sample_file = batch.create_sample_yaml()
            print(f"完成: 示例YAML配置文件已创建: {sample_file}")
            print(f"使用示例配置: python3 benchmark.py -b {sample_file}")
            return 0

        if args.batch:
            # 执行批量测试
            preview = args.preview

            # 处理批量测试文件路径
            batch_file = args.batch
            if not Path(batch_file).is_absolute():
                # 相对路径：相对于项目根目录处理
                batch_file = str(project_root / batch_file)
                # 如果还找不到，尝试相对于tasks目录
                if not Path(batch_file).exists():
                    task_dir = project_root / "tasks"
                    batch_file = str(task_dir / args.batch)

            # 显示执行信息和模式
            mode_text = "预览模式" if preview else "实际执行"
            print(f"{ColorOutput.cyan(f'正在批量基准测试: {args.batch} ({mode_text})')}")

            batch = BatchBenchmark()
            result = batch.run_task(batch_file, preview=preview)
            success = result.get('success', False)

            if not success:
                print(f"\n{ColorOutput.red('批量基准测试任务失败')}")
                return 1

            # 成功时显示统一总结（由batch.run_task处理）
        return 0

    # 如果没有提供模型参数，显示可用模型列表
    if not args.models:
        show_available_models()
        return 0

    # 否则执行单次测试
    benchmark = SingleBenchmark()

    # 收集参数
    test_params = {}
    if args.threads is not None:
        test_params["threads"] = args.threads
    if args.n_prompt is not None:
        test_params["n_prompt"] = args.n_prompt
    if args.n_gen is not None:
        test_params["n_gen"] = args.n_gen
    if args.prompt_gen:
        test_params["prompt_gen"] = args.prompt_gen
    if args.n_repeat is not None:
        test_params["n_repeat"] = args.n_repeat
    if args.precision is not None:
        test_params["precision"] = args.precision
    if args.kv_cache:
        test_params["kv_cache"] = args.kv_cache
    if args.mmap is not None:
        test_params["mmap"] = args.mmap
    if args.dynamicOption:
        test_params["dynamicOption"] = args.dynamicOption

    # 新版llm_bench_prompt参数
    if args.variable_prompt is not None:
        test_params["variable_prompt"] = args.variable_prompt

    if args.prompt_file:
        # 使用便捷方法获取提示词文件的完整绝对路径
        system_config = SystemConfig()
        prompt_file_path = system_config.get_prompt_file_path(args.prompt_file)
        test_params["prompt_file"] = str(prompt_file_path)

    try:
        # 执行基准测试 - 逐个模型执行
        results = []
        for model_alias in args.models:
            result = benchmark.execute_single_test(model_alias, **test_params)
            results.append(result)

            # 显示测试结果摘要
            if result.get('success', False):
                success_color = ColorOutput.green
                model_info = result.get('model_info', {})
                json_result = result.get('json_result', {})

                print(f"\n{success_color(f'✓ {model_alias} 测试完成')}")
                print(f"  模型: {model_info.get('name', 'Unknown')}")
                print(f"  测试ID: {json_result.get('bench_id', 'Unknown')}")
                print(f"  运行时间: {result.get('execution_time', 0)}秒")

                # 显示性能结果
                results_data = json_result.get('results', {})
                if results_data:
                    for test_type, test_data in results_data.items():
                        perf = test_data.get('tokens_per_sec', {})
                        formatted_perf = perf.get('formatted', 'Unknown')
                        print(f"  {test_type.upper()}性能: {formatted_perf}")
            else:
                # 记录失败信息，但继续执行其他模型
                error_color = ColorOutput.red
                model_info = result.get('model_info', {})

                print(f"\n{error_color(f'✗ {model_alias} 测试失败')}")
                print(f"  模型: {model_info.get('name', 'Unknown')}")

                # 显示基本的错误信息
                exec_result = result.get('execution_result', {})
                return_code = exec_result.get('return_code', None)
                if return_code is not None:
                    # 返回码含义解析
                    signal_map = { -11: "SIGSEGV", 139: "SIGSEGV", 1: "SIGHUP", 2: "SIGINT", 9: "SIGKILL", 15: "SIGTERM" }
                    signal_name = signal_map.get(return_code, "未知信号")
                    print(f"  返回码: {return_code} ({signal_name})")

                error_msg = result.get('error', '未知错误')
                print(f"  错误: {error_msg}")

        # 返回结果代码（基于是否有失败的测试）
        success = all(result.get('success', False) for result in results if isinstance(result, dict))
        return 0 if success else 1

    except (ValueError, FileNotFoundError, Exception) as e:
        # 捕获系统级别异常（非模型测试失败）
        print(f"\n{ColorOutput.red('✗ 测试过程中发生严重错误')}")
        print(f"  错误: {str(e)}")
        print(f"  类型: {type(e).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())