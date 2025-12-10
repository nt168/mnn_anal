#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend 测试运行器

统一运行前端和后端的所有测试。

作者: MNN Development Team
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# 获取项目根目录
ROOT_DIR = Path(__file__).parent
FRONTEND_TEST_DIR = ROOT_DIR / "python_demo" / "tests"
BACKEND_TEST_DIR = ROOT_DIR / "tests"


def print_header(title):
    """打印标题"""
    print("=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def run_subprocess_command(cmd, cwd=None, timeout=None):
    """运行subprocess命令"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令超时"
    except Exception as e:
        return False, "", str(e)


def run_frontend_unit_tests():
    """运行前端单元测试"""
    print_header("前端单元测试")

    if not (FRONTEND_TEST_DIR / "test_client.py").exists():
        print("⚠️ 前端单元测试文件不存在")
        return False

    cmd = [sys.executable, "test_client.py"]
    success, stdout, stderr = run_subprocess_command(cmd, cwd=FRONTEND_TEST_DIR, timeout=120)

    print("前端单元测试输出:")
    if stdout:
        print(stdout)
    if stderr and stderr.strip():
        print("错误输出:")
        print(stderr)

    if success:
        print("✅ 前端单元测试通过")
    else:
        print("❌ 前端单元测试失败")
    return success


def run_frontend_smoke_tests():
    """运行前端冒烟测试"""
    print_header("前端冒烟测试")

    if not (FRONTEND_TEST_DIR / "smoke_test.py").exists():
        print("⚠️ 前端冒烟测试文件不存在")
        return False

    cmd = [sys.executable, "smoke_test.py"]
    success, stdout, stderr = run_subprocess_command(cmd, cwd=FRONTEND_TEST_DIR, timeout=300)

    print("前端冒烟测试输出:")
    if stdout:
        print(stdout)
    if stderr and stderr.strip():
        print("错误输出:")
        print(stderr)

    if success:
        print("✅ 前端冒烟测试通过")
    else:
        print("❌ 前端冒烟测试测试失败")
    return success


def run_backend_tests():
    """运行后端测试"""
    print_header("后端测试")

    if not (BACKEND_TEST_DIR / "test_backend_simple.py").exists():
        print("⚠️ 后端测试文件不存在")
        return False

    cmd = [sys.executable, "test_backend_simple.py"]
    success, stdout, stderr = run_subprocess_command(cmd, cwd=BACKEND_TEST_DIR, timeout=300)

    print("后端测试输出:")
    if stdout:
        print(stdout)
    if stderr and stderr.strip():
        print("错误输出:")
        print(stderr)

    if success:
        print("✅ 后端测试通过")
    else:
        print("❌ 后端测试失败")
    return success


def run_demo_tests():
    """运行演示测试"""
    print_header("演示程序测试")

    demo_dir = ROOT_DIR / "python_demo" / "demos"
    test_demos = [
        ("单次对话演示", "single_chat.py"),
        ("批量对话演示", "batch_chat.py"),
    ]

    all_success = True

    for demo_name, demo_file in test_demos:
        print(f"\n🧪 测试: {demo_name}")

        if not (demo_dir / demo_file).exists():
            print(f"⚠️ {demo_file} 不存在，跳过")
            continue

        # 测试帮助信息
        cmd = [sys.executable, demo_file, "--help"]
        success, stdout, stderr = run_subprocess_command(cmd, cwd=demo_dir, timeout=30)

        if success:
            print(f"✅ {demo_name} 可正常运行")
        else:
            print(f"❌ {demo_name} 运行失败")
            if stderr:
                print(f"错误: {stderr[:200]}...")
            all_success = False

    return all_success


def check_environment():
    """检查环境"""
    print_header("环境检查")

    # 检查Python版本
    python_version = sys.version_info
    print(f"🐍 Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    if python_version < (3, 6):
        print("❌ Python版本过低，需要3.6+")
        return False
    else:
        print("✅ Python版本满足要求")

    # 检查backend文件
    backend_path = ROOT_DIR / "mnn_llm_stdio_backend"
    if backend_path.exists():
        print(f"✅ Backend文件存在: {backend_path}")
    else:
        print(f"⚠️ Backend文件不存在: {backend_path} - 某些测试会被跳过")

    # 检查模型配置
    model_path = Path("~/models/Qwen3-0.6B-MNN/config.json").expanduser()
    if model_path.exists():
        print(f"✅ 测试模型配置存在: {model_path}")
    else:
        print(f"⚠️ 测试模型配置不存在: {model_path} - 某些测试会被跳过")

    # 检查依赖目录
    required_dirs = [
        FRONTEND_TEST_DIR,
        BACKEND_TEST_DIR
    ]

    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"✅ 目录存在: {dir_path.relative_to(ROOT_DIR)}")
        else:
            print(f"❌ 目录不存在: {dir_path.relative_to(ROOT_DIR)}")
            return False

    return True


def print_usage():
    """打印使用说明"""
    print("MNN LLM Stdio Backend 测试运行器")
    print("=" * 50)
    print()
    print("使用方法:")
    print(f"  python {sys.argv[0]} [options]")
    print()
    print("选项:")
    print("  --frontend-only    只运行前端测试")
    print("  --backend-only     只运行后端测试")
    print("  --demo-only        只运行演示测试")
    print("  --unit-only        只运行单元测试")
    print("  --smoke-only       只运行冒烟测试")
    print("  --check-only       只检查环境")
    print("  --help, -h         显示此帮助信息")
    print()


def main():
    """主函数"""
    # 解析参数
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_usage()
        return 0

    # 检查是否只运行特定测试
    frontend_only = "--frontend-only" in args
    backend_only = "--backend-only" in args
    demo_only = "--demo-only" in args
    unit_only = "--unit-only" in args
    smoke_only = "--smoke-only" in args
    check_only = "--check-only" in args

    print_header("MNN LLM Stdio Backend 完整测试套件")
    print(f"🗓️ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 环境检查
    if not check_environment():
        return 1

    if check_only:
        print("✅ 环境检查完成")
        return 0

    start_time = time.time()
    results = []

    # 前端测试
    if not backend_only and not demo_only:
        print("\n🔝 开始前端测试")

        if not smoke_only:
            # 单元测试
            if not frontend_only and not unit_only:
                success = run_frontend_unit_tests()
                results.append(("前端单元测试", success))

        if not unit_only:
            # 冒烟测试
            success = run_frontend_smoke_tests()
            results.append(("前端冒烟测试", success))

    # 后端测试
    if not frontend_only and not demo_only:
        print("\n🔝 开始后端测试")
        success = run_backend_tests()
        results.append(("后端测试", success))

    # 演示测试
    if not frontend_only and not backend_only and not unit_only and not smoke_only:
        print("\n🔝 开始演示测试")
        success = run_demo_tests()
        results.append(("演示程序测试", success))

    # 总结
    elapsed = time.time() - start_time
    print_header("测试结果总结")
    print(f"⏱️ 总耗时: {elapsed:.2f} 秒")
    print()

    passed = 0
    total = 0

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}")
        if success:
            passed += 1
        total += 1

    if total > 0:
        success_rate = passed / total
        print(f"\n📊 测试通过率: {success_rate*100:.1f}% ({passed}/{total})")

        if passed == total:
            print("\n🎉 所有测试通过！系统运行正常。")
            return 0
        else:
            print(f"\n❌ {total-passed}个测试失败，请查看上方的错误信息。")
            return 1
    else:
        print("\n⚠️ 没有执行任何测试。")
        return 0


if __name__ == "__main__":
    sys.exit(main())