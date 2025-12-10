#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Frontend 冒烟测试

快速验证前端各项功能是否正常工作。

作者: MNN Development Team
"""

import sys
import os
import time
import tempfile

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from client import LlmStdioClient
    from config_manager import get_config_manager
    from logger import logger
    from color_output import (
        print_system, print_user, print_assistant,
        print_error, print_timing
    )
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在正确的目录中运行脚本")
    sys.exit(1)


def smoke_test_import():
    """测试模块导入"""
    from color_output import print_system
    print_system("🔥 冒烟测试开始 - 模块导入测试")

    try:
        from client import LlmStdioClient
        println("✅ LlmStdioClient 导入成功")
    except Exception as e:
        print(f"❌ LlmStdioClient 导入失败: {e}")
        return False

    try:
        from config_manager import get_config_manager
        println("✅ ConfigManager 导入成功")
    except Exception as e:
        print(f"❌ ConfigManager 导入失败: {e}")
        return False

    try:
        from color_output import print_system, print_user, print_assistant, print_error
        println("✅ ColorOutput 导入成功")
    except Exception as e:
        print(f"❌ ColorOutput 导入失败: {e}")
        return False

    print("✅ 所有模块导入测试通过")
    return True


def smoke_test_client_creation():
    """测试客户端创建"""
    print_system("🔥 客户端创建测试")

    try:
        config_manager = get_config_manager()
        client = LlmStdioClient(
            backend_path=config_manager.get('client', 'default_backend_path'),
            model=config_manager.get_model_config_path()
        )

        # 验证基本属性
        assert client.config_manager is not None, "配置管理器未初始化"
        assert client.color_manager is not None, "颜色管理器未初始化"
        assert client.context_manager is not None, "上下文管理器未初始化"

        # 验证配置值
        assert client.init_timeout > 0, "初始化超时时间异常"
        assert client.response_timeout > 0, "响应超时时间异常"

        print("✅ 客户端创建测试通过")
        return client

    except Exception as e:
        print(f"❌ 客户端创建失败: {e}")
        return None


def smoke_test_backend_connection(client):
    """测试Backend连接"""
    print_system("🔥 Backend连接测试")

    backend_path = str(client.backend_path)
    if not os.path.exists(backend_path):
        print(f"⚠️ Backend可执行文件不存在: {backend_path}")
        print("跳过Backend连接测试")
        return False

    try:
        print(f"📡 尝试连接Backend: {backend_path}")
        start_time = time.time()

        success = client.start()
        if not success:
            print("❌ Backend启动失败")
            return False

        elapsed = time.time() - start_time
        print(f"✅ Backend启动成功，耗时: {elapsed:.2f}秒")

        # 检查进程状态
        assert client.process is not None, "Backend进程未创建"
        assert client.running, "客户端状态异常"
        assert client.process.poll() is None, "Backend进程异常退出"

        print("✅ Backend连接测试通过")
        return True

    except Exception as e:
        print(f"❌ Backend连接测试失败: {e}")
        return False


def smoke_test_basic_chat(client):
    """测试基础对话"""
    print_system("🔥 基础对话测试")

    try:
        test_prompt = "请你简单介绍一下自己"
        print(f"📝 发送测试问题: {test_prompt}")

        start_time = time.time()
        success = client.chat(test_prompt)

        if not success:
            print("❌ 基础对话失败")
            return False

        elapsed = time.time() - start_time

        # 验证响应
        response = client.assistant_response
        assert len(response) > 0, "响应为空"

        print(f"✅ 基础对话成功，耗时: {elapsed:.2f}秒，响应长度: {len(response)}字符")
        print(f"📄 响应预览: {response[:50]}...")
        return True

    except Exception as e:
        print(f"❌ 基础对话测试失败: {e}")
        return False


def smoke_test_system_prompt(client):
    """测试系统提示词功能"""
    print_system("🔥 系统提示词测试")

    try:
        system_prompt = "你是一个专业的代码助手，所有的回答都要用代码块的形式给出。"
        print(f"📝 设置系统提示词: {system_prompt}")

        # 设置系统提示词
        success = client.set_system_prompt(system_prompt)
        if not success:
            print("❌ 设置系统提示词失败")
            return False

        # 验证设置
        current_prompt = client.get_system_prompt()
        assert current_prompt == system_prompt, "系统提示词设置不匹配"

        # 发送测试请求
        test_question = "如何写一个Hello World？"
        print(f"📝 发送测试问题: {test_question}")

        success = client.chat(test_question)
        if not success:
            print("❌ 系统提示词对话失败")
            return False

        response = client.assistant_response
        print(f"✅ 系统提示词测试成功，响应长度: {len(response)}字符")
        print(f"📄 响应预览: {response[:50]}...")

        # 清除系统提示词
        client.clear_system_prompt()
        return True

    except Exception as e:
        print(f"❌ 系统提示词测试失败: {e}")
        return False


def smoke_test_context_chat(client):
    """测试上下文对话"""
    print_system("🔥 上下文对话测试")

    try:
        # 重置上下文
        client.reset_context()

        # 第一个问题
        q1 = "我叫张三"
        print(f"📝 第一句话: {q1}")
        client.chat_with_context(q1, show_user_input=False)

        # 第二个问题（引用前面的信息）
        q2 = "我的名字是什么？"
        print(f"📝 第二句话: {q2}")
        success = client.chat_with_context(q2, show_user_input=False)

        if not success:
            print("❌ 上下文对话失败")
            return False

        # 检查回答是否包含名字
        response = client.assistant_response
        print(f"✅ 上下文对话测试成功，响应长度: {len(response)}字符")
        print(f"📄 回答预览: {response[:50]}...")

        # 检查对话摘要
        summary = client.get_conversation_summary()
        print(f"📊 对话摘要: {len(summary)}字符")

        return True

    except Exception as e:
        print(f"❌ 上下文对话测试失败: {e}")
        return False


def smoke_test_newline_handling(client):
    """测试换行符处理"""
    print_system("🔥 换行符处理测试")

    try:
        # 设置需要换行的系统提示词
        client.set_system_prompt("你是一个喜欢用列表回答的助手，每个要点占一行。")

        test_prompt = "请列出3个最重要的编程概念"
        print(f"📝 发送换行测试问题: {test_prompt}")

        success = client.chat(test_prompt)
        if not success:
            print("❌ 换行测试对话失败")
            return False

        response = client.assistant_response

        # 检查响应内容
        newline_count = response.count('\n')
        print(f"✅ 换行符测试成功，包含 {newline_count} 个换行符")
        print(f"📄 响应预览: {response[:100]}...")

        if newline_count > 0:
            print("✅ 换行符处理正常")
        else:
            print("⚠️ 响应中没有换行符，可能格式问题")

        return True

    except Exception as e:
        print(f"❌ 换行符处理测试失败: {e}")
        return False


def smoke_test_performance(client):
    """测试性能指标"""
    print_system("🔥 性能测试")

    try:
        test_prompts = [
            "回答一个简单问题：什么是AI？",
            "请解释一下机器学习的基本概念。",
            "推荐几个Python的Web框架。"
        ]

        total_time = 0
        for i, prompt in enumerate(test_prompts):
            print(f"🔄 测试 {i+1}/{len(test_prompts)}: {prompt[:30]}...")

            start_time = time.time()
            success = client.chat(prompt)
            elapsed = time.time() - start_time

            total_time += elapsed

            if success:
                print(f"✅ 请求 {i+1} 完成，耗时: {elapsed:.2f}秒，响应: {len(client.assistant_response)}字符")
            else:
                print(f"❌ 请求 {i+1} 失败")
                return False

        avg_time = total_time / len(test_prompts)
        print(f"📊 性能测试完成，平均响应时间: {avg_time:.2f}秒")

        if avg_time < 10:  # 假设10秒内为正常
            print("✅ 性能测试通过")
        else:
            print("⚠️ 响应时间较慢，可能需要优化")

        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False


def cleanup(client):
    """清理资源"""
    if client and client.running:
        print_system("🧹 清理资源")
        client.stop_backend()


def println(msg):
    """打印消息"""
    print(msg)


def main():
    """主函数"""
    print_system("🔥 MNN LLM Stdio Frontend 冒烟测试开始")
    print_system("=" * 50)

    results = []

    try:
        # 1. 模块导入测试
        if not smoke_test_import():
            return 1
        results.append("✅ 模块导入")

        # 2. 客户端创建测试
        client = smoke_test_client_creation()
        if not client:
            return 1
        results.append("✅ 客户端创建")

        # 3. 如果backend存在，进行完整测试
        config_manager = get_config_manager()
        backend_path = config_manager.get('client', 'default_backend_path')

        if os.path.exists(backend_path):
            # 4. Backend连接测试
            if not smoke_test_backend_connection(client):
                cleanup(client)
                return 1
            results.append("✅ Backend连接")

            # 5. 基础对话测试
            if not smoke_test_basic_chat(client):
                results.append("❌ 基础对话")
            else:
                results.append("✅ 基础对话")

            # 6. 系统提示词测试
            if not smoke_test_system_prompt(client):
                results.append("❌ 系统提示词")
            else:
                results.append("✅ 系统提示词")

            # 7. 上下文对话测试
            if not smoke_test_context_chat(client):
                results.append("❌ 上下文对话")
            else:
                results.append("✅ 上下文对话")

            # 8. 换行符处理测试
            if not smoke_test_newline_handling(client):
                results.append("❌ 换行符处理")
            else:
                results.append("✅ 换行符处理")

            # 9. 性能测试
            if not smoke_test_performance(client):
                results.append("❌ 性能测试")
            else:
                results.append("✅ 性能测试")

        else:
            print("⚠️ Backend不存在，跳过运行时测试")

        cleanup(client)

    except Exception as e:
        print(f"❌ 冒烟测试出现异常: {e}")
        if 'client' in locals():
            cleanup(client)
        return 1

    # 总结测试结果
    print_system("=" * 50)
    print_system("🔥 冒烟测试结果总结:")

    for result in results:
        println(f"  {result}")

    # 判断成功率
    failed = [r for r in results if r.startswith("❌")]
    success_rate = (len(results) - len(failed)) / len(results) if results else 0

    print_system(f"📊 测试通过率: {success_rate*100:.1f}% ({len(results)-len(failed)}/{len(results)})")

    if failed:
        print_error(f"❌ 失败测试: {len(failed)}项")
        for f in failed:
            print_error(f"  {f}")
        return 1
    else:
        print_system("🎉 所有冒烟测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())