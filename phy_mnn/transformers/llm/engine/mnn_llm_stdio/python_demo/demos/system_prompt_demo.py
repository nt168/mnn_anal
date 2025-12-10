#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 系统提示词演示

演示如何设置和使用系统提示词功能。

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


def demo_basic_system_prompt(client):
    """基础系统提示词演示"""
    print_system("=== 基础系统提示词演示 ===")

    # 设置一个简单的角色
    simple_prompt = "你是一个专业的AI助手，请用简洁明了的方式回答问题。"
    client.set_system_prompt(simple_prompt)

    # 测试对话
    test_questions = [
        "介绍一下你自己",
        "什么是人工智能？",
        "请用一句话总结深度学习的概念"
    ]

    for question in test_questions:
        print_user(f"问题: {question}")
        separator("-", 40)

        start_time = time.time()
        success = client.chat(question)

        if success:
            elapsed = time.time() - start_time
            separator("-", 40)
            print_timing(elapsed, f"回答问题: {question}")
            print_assistant(f"响应长度: {len(client.assistant_response)} 字符")
            separator()
        else:
            print_error(f"回答问题失败: {question}")
        print()


def demo_complex_system_prompt(client):
    """复杂系统提示词演示"""
    print_system("=== 复杂系统提示词演示 ===")

    # 设置一个复杂的角色和规则
    complex_prompt = """你是一位经验丰富的技术专家，具有以下特点：
1. 专业技术背景：精通计算机科学、人工智能和软件工程
2. 回答风格：专业、准确、有条理
3. 回答格式：使用分点编号的方式组织回答
4. 语言要求：使用中文回答，避免太口语化的表达
5. 特别要求：如果遇到不确定的内容，明确说明而不是猜测

请始终保持这个角色设定。"""

    client.set_system_prompt(complex_prompt)

    # 测试对话
    test_questions = [
        "请解释一下微服务架构的优势和挑战",
        "如何进行有效的代码重构？",
        "什么是LLM的上下文学习？"
    ]

    for question in test_questions:
        print_user(f"问题: {question}")
        separator("-", 40)

        start_time = time.time()
        success = client.chat(question)

        if success:
            elapsed = time.time() - start_time
            separator("-", 40)
            print_timing(elapsed, f"专家回答: {question}")
            print_assistant(f"响应长度: {len(client.assistant_response)} 字符")
            separator()
        else:
            print_error(f"专家回答失败: {question}")
        print()


def demo_system_prompt_switching(client):
    """系统提示词切换演示"""
    print_system("=== 系统提示词切换演示 ===")

    # 角色1：教师
    teacher_prompt = "你是一位有耐心的小学老师，请用简单易懂的方式解释概念，适合学生理解。"
    client.set_system_prompt(teacher_prompt)

    question = "解释什么是算法"
    print_user(f"算法解释（教师角色）: {question}")
    separator("-", 40)

    if client.chat(question):
        separator("-", 40)
        print_assistant(f"教师回答结束，响应长度: {len(client.assistant_response)} 字符")
    print()

    # 角色切换：研究员
    researcher_prompt = "你是一位严谨的计算机科学研究员，请使用专业、准确的术语进行解释。"
    client.set_system_prompt(researcher_prompt)

    print_user(f"算法解释（研究员角色）: {question}")
    separator("-", 40)

    if client.chat(question):
        separator("-", 40)
        print_assistant(f"研究员回答结束，响应长度: {len(client.assistant_response)} 字符")
    print()

    # 清除系统提示词
    client.clear_system_prompt()
    print_system("系统提示词已清除")

    print_user(f"算法解释（无系统提示词）: {question}")
    separator("-", 40)

    if client.chat(question):
        separator("-", 40)
        print_assistant(f"默认回答结束，响应长度: {len(client.assistant_response)} 字符")


def main():
    """主函数"""
    # 获取配置管理器
    config_manager = get_config_manager()

    # 创建参数解析器
    parser = argparse.ArgumentParser(description="MNN LLM Stdio Backend - 系统提示词演示")

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

    # 演示选择
    parser.add_argument("--demo",
                        choices=["basic", "complex", "switching", "all"],
                        default="all",
                        help="选择要运行的演示类型")

    # 解析参数
    args = parser.parse_args()

    try:
        # 初始化客户端
        print_system("启动MNN LLM Stdio Backend客户端...")
        logger.info("启动系统提示词演示...")

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

        # 根据选择运行演示
        if args.demo == "basic" or args.demo == "all":
            demo_basic_system_prompt(client)
            if args.demo == "all":
                separator("*", 50)

        if args.demo == "complex" or args.demo == "all":
            demo_complex_system_prompt(client)
            if args.demo == "all":
                separator("*", 50)

        if args.demo == "switching" or args.demo == "all":
            demo_system_prompt_switching(client)
            if args.demo == "all":
                separator("*", 50)

        print_system("系统提示词演示完成")

    except KeyboardInterrupt:
        print_error("\\n用户中断")
        logger.info("用户中断程序")
        sys.exit(1)

    except Exception as e:
        print_error(f"\\n运行错误: {e}")
        logger.error(f"运行异常: {e}")
        sys.exit(1)

    finally:
        if 'client' in locals():
            print_system("正在停止客户端...")
            client.stop_backend()
            print_system("客户端已停止")


if __name__ == "__main__":
    main()