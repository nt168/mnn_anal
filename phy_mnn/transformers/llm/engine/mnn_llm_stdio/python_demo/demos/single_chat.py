#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 单次对话演示

演示如何进行单次对话测试。

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
        print_system, print_user, print_assistant,
        print_error, print_timing, separator
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
    parser = argparse.ArgumentParser(description="MNN LLM Stdio Backend - 单次对话演示")

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

    # 单次对话特有参数
    parser.add_argument("--prompt",
                        help="单次对话的提示语")
    parser.add_argument("--system-prompt",
                        help="系统提示词（可选）")
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

        # 设置系统提示词（如果提供）
        if args.system_prompt:
            print_system(f"设置系统提示词: {args.system_prompt}")
            if not client.set_system_prompt(args.system_prompt):
                print_error("设置系统提示词失败")
                logger.error("设置系统提示词失败")
                client.stop_backend()
                sys.exit(1)

        # 获取提示语
        prompt = args.prompt
        if not prompt:
            prompt = config_manager.get_default_prompt()

        print_user(f"提问: {prompt}")
        separator("-", 40)

        start_time = time.time()

        # 执行单次对话（使用彩色输出）
        success = client.chat(prompt)

        if success:
            separator("-", 40)

            if hasattr(client, 'show_timing') and client.show_timing:
                elapsed = time.time() - start_time
                print_timing(elapsed, "单次对话")

            if hasattr(client, 'show_response_length') and client.show_response_length:
                print_system(f"响应长度: {len(client.assistant_response)} 字符")

            logger.info(f"单次对话完成")
            print_system("单次对话完成")
        else:
            print_error("对话失败")
            logger.error("单次对话失败")
            sys.exit(1)

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