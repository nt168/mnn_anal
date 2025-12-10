#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 交互式对话演示

演示如何进行多轮交互式对话，支持上下文管理。
保留对话上下文，支持彩色输出。

作者: MNN Development Team
"""

import sys
import os
import argparse
import time

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from client import LlmStdioClient
    from logger import logger
    from config_manager import get_config_manager
    from color_output import (
        get_color_manager, print_system, print_error, print_timing, separator
    )
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保在正确的目录中运行脚本")
    sys.exit(1)


def show_help():
    """显示帮助信息"""
    print_system("可用命令:")
    print_system("  help  - 显示此帮助信息")
    print_system("  reset - 重置对话上下文")
    print_system("  quit/exit/q - 退出程序")


def main():
    """主函数"""
    # 获取配置管理器
    config_manager = get_config_manager()

    # 创建参数解析器
    parser = argparse.ArgumentParser(description="MNN LLM Stdio Backend - 交互式对话演示")

    # 通用参数
    parser.add_argument("--backend",
                        default=config_manager.get('client', 'default_backend_path'),
                        help="backend可执行文件路径")
    parser.add_argument("--model",
                        default=None,
                        help="模型配置文件路径")
    parser.add_argument("--config",
                        default=None,
                        help="客户端配置文件路径")

    # 交互式对话特有参数
    parser.add_argument("--max-tokens",
                        type=int,
                        help="最大生成token数")
    parser.add_argument("--reset",
                        action='store_true',
                        help="重置对话上下文")

    # 解析参数
    args = parser.parse_args()

    try:
        # 初始化客户端
        print_system("启动MNN LLM Stdio Backend客户端...")
        logger.info("启动MNN LLM Stdio Backend客户端...")

        if args.backend:
            print_system(f"Backend路径: {args.backend}")
        if args.model:
            print_system(f"模型配置: {args.model}")
        if args.config:
            print_system(f"配置文件: {args.config}")

        client = LlmStdioClient(
            backend_path=args.backend,
            model=args.model,
            config_file=args.config
        )

        # 启动客户端
        if not client.start():
            print_error("客户端启动失败")
            logger.error("客户端启动失败")
            sys.exit(1)

        # 如果指定了reset参数，重置上下文
        if args.reset:
            client.reset_context()

        print_system("进入交互式对话模式")
        separator("=", 40)
        print_system("输入 'help' 查看命令，输入 'quit' 或 'exit' 退出")
        print_system("输入 'reset' 重置对话上下文")
        separator("=", 40)

        while True:
            try:
                # 获取用户输入
                user_input = input("\n用户: ").strip()

                if not user_input:
                    continue

                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print_system("退出交互式对话")
                    break

                if user_input.lower() == 'help':
                    show_help()
                    continue

                if user_input.lower() == 'reset':
                    client.reset_context()
                    continue

                # 执行对话（使用上下文和彩色输出）
                start_time = time.time()
                success = client.chat_with_context(user_input, show_user_input=False)

                if success:
                    if hasattr(client, 'show_timing') and client.show_timing:
                        elapsed = time.time() - start_time
                        print_timing(elapsed, "对话")
                else:
                    print_error("对话失败")

            except EOFError:
                print_system("\n收到EOF，退出对话")
                break

    except KeyboardInterrupt:
        print_error("\n用户中断")
        logger.info("用户中断程序")
        sys.exit(1)

    except Exception as e:
        print_error(f"\n运行错误: {e}")
        logger.error(f"运行异常: {e}")
        sys.exit(1)

    finally:
        if 'client' in locals():
            print_system("正在停止客户端...")
            client.stop_backend()
            print_system("客户端已停止")


if __name__ == "__main__":
    main()