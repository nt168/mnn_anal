#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend 简单测试

通过测试用例验证Backend的基本功能是否正常工作。

作者: MNN Development Team
"""

import subprocess
import json
import time
import sys
import os
from typing import Optional

# 获取根目录路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_PATH = os.path.join(ROOT_DIR, "mnn_llm_stdio_backend")

# 测试模型配置
TEST_MODEL_CONFIG = "~/models/Qwen3-0.6B-MNN/config.json"


class BackendTestRunner:
    """Backend测试运行器"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.backend_path = BACKEND_PATH
        self.model_path = os.path.expanduser(TEST_MODEL_CONFIG)

    def start_backend(self) -> bool:
        """启动backend进程"""
        if not os.path.exists(self.backend_path):
            print(f"❌ Backend可执行文件不存在: {self.backend_path}")
            return False

        if not os.path.exists(self.model_path):
            print(f"❌ 模型配置文件不存在: {self.model_path}")
            return False

        try:
            print(f"🚀 启动Backend: {self.backend_path}")
            print(f"📁 使用模型: {self.model_path}")

            self.process = subprocess.Popen(
                [self.backend_path, self.model_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 等待初始化完成
            return self._wait_for_ready()

        except Exception as e:
            print(f"❌ 启动Backend失败: {e}")
            return False

    def _wait_for_ready(self, timeout: int = 30) -> bool:
        """等待backend准备就绪"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                print(f"❌ Backend启动失败，退出码: {self.process.returncode}")
                if stderr:
                    print(f"STDERR: {stderr}")
                return False

            # 检查stderr输出
            try:
                line = self.process.stderr.readline()
                if line:
                    line = line.strip()
                    try:
                        msg = json.loads(line)
                        if msg.get("status") == "ready":
                            print("✅ Backend就绪")
                            return True
                        elif msg.get("status") == "error":
                            print(f"❌ Backend错误: {msg.get('message')}")
                            return False
                    except json.JSONDecodeError:
                        if line:
                            print(f"Backend消息: {line}")
            except Exception:
                pass

            time.sleep(0.1)

        print("❌ Backend初始化超时")
        return False

    def send_command(self, command: dict) -> bool:
        """发送命令到backend"""
        try:
            cmd_str = json.dumps(command, ensure_ascii=False)
            self.process.stdin.write(cmd_str + "\n")
            self.process.stdin.flush()
            return True
        except Exception as e:
            print(f"❌ 发送命令失败: {e}")
            return False

    def read_response(self, timeout: int = 60) -> Optional[dict]:
        """读取响应"""
        start_time = time.time()
        response_text = ""

        while time.time() - start_time < timeout:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break

                line = line.strip()
                try:
                    msg = json.loads(line)
                    msg_type = msg.get("type")

                    if msg_type == "status":
                        if msg.get("status") == "success" and "完成" in msg.get("message", ""):
                            # 响应完成
                            break

                    elif msg_type == "error":
                        print(f"❌ Backend错误: {msg.get('message')}")
                        return None

                except json.JSONDecodeError:
                    continue

            except Exception:
                break

            time.sleep(0.1)

        return {"status": "completed"}

    def stop_backend(self):
        """停止backend"""
        if self.process:
            try:
                self.send_command({"type": "exit"})
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    self.process.kill()
            self.process = None

    def test_basic_chat(self) -> bool:
        """测试基础对话"""
        print("🧪 测试基础对话")

        # 发送聊天命令
        command = {
            "type": "chat",
            "prompt": "你好，请简单介绍一下你自己"
        }

        if not self.send_command(command):
            return False

        # 等待响应
        response = self.read_response(timeout=30)
        if response is None:
            return False

        print("✅ 基础对话测试通过")
        return True

    def test_system_prompt(self) -> bool:
        """测试系统提示词"""
        print("🧪 测试系统提示词")

        # 设置系统提示词
        sys_prompt_cmd = {
            "type": "system_prompt",
            "system_prompt": "你是一个专业的技术专家，所有回答都要用技术性语言。"
        }

        if not self.send_command(sys_prompt_cmd):
            return False

        # 等待设置完成
        time.sleep(0.5)

        # 发送测试对话
        chat_cmd = {
            "type": "chat",
            "prompt": "请解释什么是机器学习"
        }

        if not self.send_command(chat_cmd):
            return False

        response = self.read_response(timeout=30)
        if response is None:
            return False

        print("✅ 系统提示词测试通过")
        return True

    def test_reset(self) -> bool:
        """测试重置功能"""
        print("🧪 测试重置功能")

        # 发送重置命令
        reset_cmd = {"type": "reset"}
        if not self.send_command(reset_cmd):
            return False

        time.sleep(0.5)

        print("✅ 重置功能测试通过")
        return True

    def test_conversation(self) -> bool:
        """测试多轮对话"""
        print("🧪 测试多轮对话")

        # 第一轮对话
        if not self.send_command({"type": "chat", "prompt": "我叫张三"}):
            return False
        self.read_response(timeout=30)

        # 第二轮对话（应该记住用户名字）
        if not self.send_command({"type": "chat", "prompt": "我的名字是什么？"}):
            return False
        response = self.read_response(timeout=30)
        if response is None:
            return False

        print("✅ 多轮对话测试通过")
        return True

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🔥 Backend简单测试开始")
        print("=" * 40)

        # 启动backend
        if not self.start_backend():
            return False

        try:
            tests = [
                ("基础对话", self.test_basic_chat),
                ("系统提示词", self.test_system_prompt),
                ("重置功能", self.test_reset),
                ("多轮对话", self.test_conversation)
            ]

            passed = 0
            total = len(tests)

            for test_name, test_func in tests:
                print(f"\n🧪 执行测试: {test_name}")
                try:
                    if test_func():
                        passed += 1
                        print(f"✅ {test_name} 通过")
                    else:
                        print(f"❌ {test_name} 失败")
                except Exception as e:
                    print(f"❌ {test_name} 异常: {e}")

            print(f"\n📊 测试结果: {passed}/{total} 通过")

            if passed == total:
                print("🎉 所有测试通过！")
                return True
            else:
                print("❌ 部分测试失败")
                return False

        finally:
            # 清理
            self.stop_backend()


def main():
    """主函数"""
    runner = BackendTestRunner()
    success = runner.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())