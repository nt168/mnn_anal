#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 统一演示入口

提供统一的演示程序入口，用户可以选择不同的演示模式。
也可以直接调用各个独立的演示程序。

作者: MNN Development Team
"""

import subprocess
import sys
import os

# 确保能找到演示程序安装路径
demo_dir = os.path.dirname(os.path.abspath(__file__))
demos_dir = os.path.join(demo_dir, 'demos')


def print_usage():
    """打印使用说明"""
    print("MNN LLM Stdio Backend 演示程序")
    print("=" * 50)
    print()
    print("使用方法:")
    print(f"  python {os.path.basename(__file__)} <mode> [options]")
    print()
    print("可用模式:")
    print("  single   - 单次对话演示")
    print("  batch    - 批量对话演示")
    print("  chat     - 交互式对话演示")
    print("  help     - 显示此帮助信息")
    print()
    print("示例:")
    print(f"  python {os.path.basename(__file__)} single --prompt '你好'")
    print(f"  python {os.path.basename(__file__)} batch --file example_commands.txt")
    print(f"  python {os.path.basename(__file__)} chat")
    print()
    print("你也可以直接调用各个演示程序:")
    print("  python demos/single_chat.py --help")
    print("  python demos/batch_chat.py --help")
    print("  python demos/interactive_chat.py --help")


def run_demo(mode: str, args: list):
    """运行指定的演示程序"""
    demo_scripts = {
        'single': 'single_chat.py',
        'batch': 'batch_chat.py',
        'chat': 'interactive_chat.py'
    }

    if mode not in demo_scripts:
        print(f"错误: 未知模式 '{mode}'")
        print("可用模式: single, batch, chat")
        return False

    demo_path = os.path.join(demos_dir, demo_scripts[mode])

    if not os.path.exists(demo_path):
        print(f"错误: 找不到演示程序 {demo_path}")
        return False

    try:
        # 构建命令
        cmd = [sys.executable, demo_path] + args

        # 运行演示程序
        result = subprocess.run(cmd, cwd=demo_dir)
        return result.returncode == 0

    except Exception as e:
        print(f"运行演示程序时出错: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode in ['help', '-h', '--help']:
        print_usage()
        sys.exit(0)

    # 传递剩余参数给演示程序
    args = sys.argv[2:]

    success = run_demo(mode, args)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()