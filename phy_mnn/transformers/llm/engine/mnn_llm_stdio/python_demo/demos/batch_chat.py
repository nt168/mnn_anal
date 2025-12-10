#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 批量对话演示

演示如何批量执行对话命令，支持从文件读取命令列表。
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
        print_system, print_error, print_timing, separator
    )
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保在正确的目录中运行脚本")
    sys.exit(1)


def main():
    """主函数"""
    # 获取配置管理器
    config_manager = get_config_manager()

    # 创建参数解析器
    parser = argparse.ArgumentParser(description="MNN LLM Stdio Backend - 批量对话演示")

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

    # 批量对话特有参数
    parser.add_argument("--file",
                        help="包含批量命令的文件路径")
    parser.add_argument("--max-tokens",
                        type=int,
                        help="最大生成token数")

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

        # 获取批量文件路径
        batch_file = args.file or config_manager.get_batch_file_path()

        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                commands = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print_error(f"无法读取批量文件 {batch_file}: {e}")
            return

        if not commands:
            print_error("批量文件中没有找到有效命令")
            return

        print_system(f"开始执行批量对话，共 {len(commands)} 条命令")
        separator("=", 50)

        for i, command in enumerate(commands, 1):
            print_system(f"\n[{i}/{len(commands)}] 执行: {command}")
            separator("-", 40)

            start_time = time.time()

            # 检查是否是reset命令
            if command.lower() == 'reset':
                client.reset_context()
                success = True
                separator("-", 40)
                if hasattr(client, 'show_timing') and client.show_timing:
                    elapsed = time.time() - start_time
                    print_timing(elapsed, f"命令[{i}]")
                print_system("对话上下文已重置")
                print_system(f"命令 [{i}] 完成 (上下文已重置)")
                separator("=", 50)
                continue
            else:
                # 普通聊天命令
                success = client.chat_with_context(command, show_user_input=False)

            if success:
                separator("-", 40)
                if hasattr(client, 'show_timing') and client.show_timing:
                    elapsed = time.time() - start_time
                    print_timing(elapsed, f"命令[{i}]")
                print_system(f"命令 [{i}] 完成")
                separator("=", 50)
            else:
                print_error(f"命令 [{i}] 执行失败")
                separator("=", 50)

        print_system(f"\n批量对话完成，总共处理 {len(commands)} 条命令")
        logger.info(f"批量对话完成，共处理 {len(commands)} 条命令")

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