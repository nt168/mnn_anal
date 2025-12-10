#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试换行符处理的简单脚本

作者: MNN Development Team
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LlmStdioClient
    from config_manager import get_config_manager
    from color_output import print_system, print_error
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保在正确的目录中运行脚本")
    sys.exit(1)

def test_line_breaks():
    """测试换行符处理"""
    config_manager = get_config_manager()
    client = LlmStdioClient(
        backend_path=config_manager.get('client', 'default_backend_path'),
        model=config_manager.get_model_config_path()
    )

    print_system("启动客户端进行换行测试...")

    if not client.start():
        print_error("客户端启动失败")
        return False

    # 设置一个会要求列表格式回答的系统提示词
    client.set_system_prompt("你是一个会使用大量换行和列表的AI助手。请用清晰的格式回答，每项占一行。")

    test_prompt = "请列出AI的5个主要特点，每个特点占一行"

    print_system(f"发送测试问题: {test_prompt}")

    if client.chat(test_prompt):
        print_system("对话完成，检查回答中是否有正确的换行格式")
        response = client.assistant_response

        # 检查回答中是否包含换行符
        if '\n' in response:
            print_system(f"✓ 换行测试通过！回答包含 {response.count('\\n')} 个换行符")
            print_system("回答内容预览（前100字符）：")
            print_system(response[:100] + "..." if len(response) > 100 else response)
        else:
            print_error("✗ 换行测试失败！回答中没有包含换行符")
            print_error("回答内容：")
            print_error(response)
    else:
        print_error("测试对话失败")

    client.stop_backend()
    return True

if __name__ == "__main__":
    test_line_breaks()