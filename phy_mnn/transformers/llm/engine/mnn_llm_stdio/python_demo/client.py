#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MNN LLM Stdio Backend - 核心客户端模块

实现与 MNN LLM Stdio Backend 的通信功能，包括进程管理、命令发送和输出处理。

作者: MNN Development Team
"""

import subprocess
import json
import sys
import time
import threading
from select import select
from typing import Optional, List, Dict, Any

try:
    from .logger import logger
    from .config_manager import get_config_manager
    from .color_output import get_color_manager, print_system, print_user, print_assistant, print_error, print_timing
    from .context_manager import get_context_manager
except ImportError:
    # 适用于直接运行的情况
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logger import logger
    from config_manager import get_config_manager
    from color_output import get_color_manager, print_system, print_user, print_assistant, print_error, print_timing
    from context_manager import get_context_manager


# 配置常量
STREAM_START_MARKER = "[LLM_STREAM_START]"
STREAM_END_MARKER = "[LLM_STREAM_END]"


class LlmStdioClient:
    """MNN LLM Stdio Backend的Python客户端"""

    def __init__(self, backend_path: str = None, model: str = None, config_file: str = None):
        """
        初始化客户端

        Args:
            backend_path: backend可执行文件路径
            model: 模型名称，直接传递给backend
            config_file: 客户端配置文件路径
        """
        # 保存传入的参数
        self._backend_path_param = backend_path
        self._model_param = model
        self._config_file_param = config_file

        # 初始化配置管理器
        self.config_manager = get_config_manager(config_file)
        self._init_config()

        # 初始化其他组件
        self.color_manager = get_color_manager()
        self.context_manager = get_context_manager()

        # 初始化状态变量
        self._init_state()

    def _init_config(self):
        """初始化配置"""
        # 处理backend路径
        if self._backend_path_param:
            self.backend_path = self.config_manager.expand_path(self._backend_path_param)
        else:
            backend_path = self.config_manager.get('client', 'default_backend_path')
            self.backend_path = self.config_manager.expand_path(backend_path)

        # 模型名称（直接传递给backend）
        if self._model_param:
            self.model = self._model_param
        else:
            model_path = self.config_manager.get('client', 'default_model')
            self.model = self.config_manager.expand_path(model_path) if model_path else None

        # 获取超时配置
        self.init_timeout = self.config_manager.get('client', 'init_timeout', 30.0)
        self.response_timeout = self.config_manager.get('client', 'response_timeout', 60.0)
        self.shutdown_timeout = self.config_manager.get('client', 'shutdown_timeout', 5.0)
        self.init_sleep_time = self.config_manager.get('client', 'init_sleep_time', 0.1)
        self.select_timeout = self.config_manager.get('client', 'select_timeout', 0.1)

        # 获取显示配置
        self.show_timing = self.config_manager.get('display', 'show_timing', True)
        self.show_response_length = self.config_manager.get('display', 'show_response_length', True)
        self.time_precision = self.config_manager.get('display', 'time_precision', 2)

        # 初始化思考标签配置
        self._init_thinking_config()

    def _init_thinking_config(self):
        """初始化思考标签配置"""
        # 获取思考标签配置
        self.enable_thinking_display = self.config_manager.get('thinking', 'enable_thinking_display', True)

        # 分别获取开始和结束标签
        start_tags = self.config_manager.get('thinking', 'thinking_start_tags', ["<thinking>", "【思考】"])
        end_tags = self.config_manager.get('thinking', 'thinking_end_tags', ["</thinking>", "【/思考】"])

        # 确保开始和结束标签数量一致
        min_len = min(len(start_tags), len(end_tags))
        self.thinking_start_tags = start_tags[:min_len]
        self.thinking_end_tags = end_tags[:min_len]

        # 获取思考指示器
        self.thinking_start_indicator = self.config_manager.get('thinking', 'thinking_start_indicator', "[思考开始]\n")
        self.thinking_end_indicator = self.config_manager.get('thinking', 'thinking_end_indicator', "[思考完成]\n")

        # 获取思考模式配置
        self.implicit_thinking = self.config_manager.get('thinking', 'implicit_thinking', False)

    def _init_state(self):
        """初始化状态变量"""
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.response_complete = False
        self.assistant_response = ""

    def _start_backend(self) -> bool:
        """启动backend进程"""
        try:
            logger.info(f"启动backend进程: {self.backend_path}")
            model_path = self._get_model_path()

            # 启动backend进程
            backend_args = [self.backend_path, model_path]
            self.process = subprocess.Popen(
                backend_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # 以字节模式处理
            )

            logger.info(f"Backend进程已启动 (PID: {self.process.pid})")

            # 等待初始化完成
            ready = self._wait_for_ready()
            if not ready:
                print_error("Backend初始化失败")
                logger.error("Backend初始化失败")
                self.stop_backend()
                return False

            print_system("Backend初始化成功")
            logger.info("Backend初始化成功")
            return True

        except Exception as e:
            print_error(f"启动backend失败: {e}")
            logger.error(f"启动backend失败: {e}")
            return False

    def _check_process_exited(self, context: str) -> bool:
        """检查进程是否已退出，如果退出则记录错误"""
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            error_msg = f"{context}时进程意外退出，退出码: {self.process.returncode}"
            print_error(error_msg)
            logger.error(error_msg)
            if stderr:
                logger.error(f" stderr输出: {stderr_str}")
            return True
        return False

    def _decode_line(self, line: bytes) -> str:
        """将字节转换为UTF-8字符串"""
        # 对于流式内容，保留完整的行，包括换行符（但去掉尾部Windows换行符）
        decoded = line.decode('utf-8', errors='replace')
        # 只移除行尾的\r然后处理\n
        if decoded.endswith('\r\n'):
            return decoded[:-2] + '\n'
        elif decoded.endswith('\r'):
            return decoded[:-1]
        elif decoded.endswith('\n'):
            return decoded
        else:
            return decoded

    def _parse_json_message(self, line_str: str) -> Optional[Dict[str, Any]]:
        """解析JSON消息，失败返回None"""
        try:
            return json.loads(line_str.strip())
        except json.JSONDecodeError:
            return None

    def _clean_thinking_tags(self, line_str: str) -> str:
        """清理行中的思考标签"""
        cleaned = line_str
        for tag in self.thinking_start_tags + self.thinking_end_tags:
            if tag in cleaned:
                cleaned = cleaned.replace(tag, "")
        return cleaned

    def _check_thinking_tags(self, original_line: str, current_in_thinking: bool) -> Dict[str, Any]:
        """检查思考标签，返回处理结果"""
        result = {
            'should_start_thinking': False,
            'should_end_thinking': False,
            'cleaned_line': self._clean_thinking_tags(original_line)
        }

        # 检查开始标签
        if not self.implicit_thinking or not current_in_thinking:
            for tag in self.thinking_start_tags:
                if tag in original_line:
                    result['should_start_thinking'] = True
                    break

        # 检查结束标签
        for tag in self.thinking_end_tags:
            if tag in original_line:
                result['should_end_thinking'] = True
                break

        return result

    def _get_model_path(self) -> str:
        """获取模型路径配置"""
        if self.model is None:
            model_path = self.config_manager.get_model_config_path()
            logger.info(f"使用默认模型配置: {model_path}")
            return model_path
        else:
            logger.info(f"使用命令行模型配置: {self.model}")
            return self.model

    def _wait_for_ready(self, timeout: float = None) -> bool:
        """等待backend准备就绪"""
        start_time = time.time()
        logger.info("等待backend初始化...")
        timeout = timeout if timeout is not None else self.init_timeout

        while time.time() - start_time < timeout:
            if self._check_process_exited("Backend初始化"):
                return False

            # 检查stderr是否有ready消息
            rlist, _, _ = select([self.process.stderr], [], [], self.init_sleep_time)
            if rlist:
                line = self.process.stderr.readline()
                if not line:
                    continue

                line_str = self._decode_line(line)
                msg = self._parse_json_message(line_str)

                if msg:
                    msg_status = msg.get("status")
                    msg_text = msg.get("message", line_str.strip())

                    if msg_status == "ready":
                        logger.info(f"Backend就绪: {msg_text}")
                        return True
                    elif msg_status == "error":
                        print_error(f"Backend错误: {msg_text}")
                        logger.error(f"Backend错误: {msg_text}")
                    else:
                        logger.info(f"Backend状态: {msg_text}")
                else:
                    if line_str.strip():
                        logger.info(f"Backend消息: {line_str.strip()}")

        error_msg = f"Backend初始化超时 (>{timeout}秒)"
        print_error(error_msg)
        logger.error(error_msg)
        return False

    def _process_stream_content(self, line_str: str, in_thinking: bool) -> bool:
        """
        处理流式内容，包含思考标签逻辑

        Args:
            line_str: 原始行内容（可能包含换行符）
            in_thinking: 当前是否在思考状态

        Returns:
            新的思考状态
        """
        if not self.enable_thinking_display:
            # 简单模式：直接输出所有内容，保留换行符
            if line_str:
                self.color_manager.print_colored(line_str, message_type="assistant", end='', flush=True)
                self.assistant_response += line_str
            return in_thinking

        # 复杂模式：处理思考标签
        thinking_result = self._check_thinking_tags(line_str, in_thinking)
        cleaned_line = thinking_result['cleaned_line']

        # 处理思考状态切换
        if thinking_result['should_start_thinking'] and not in_thinking:
            self.color_manager.print_colored(self.thinking_start_indicator, message_type="thinking", end="", flush=True)
            in_thinking = True

        # 输出内容，保留换行符
        if cleaned_line:  # 只处理非空内容
            if in_thinking:
                # 思考内容：使用思考颜色显示，保留换行符
                self.color_manager.print_colored(cleaned_line, message_type="thinking", end='', flush=True)
                self.assistant_response += cleaned_line
            else:
                # 正常输出：使用助手颜色显示，保留换行符
                self.color_manager.print_colored(cleaned_line, message_type="assistant", end='', flush=True)
                self.assistant_response += cleaned_line

        # 处理思考状态结束
        if thinking_result['should_end_thinking'] and in_thinking:
            self.color_manager.print_colored(self.thinking_end_indicator, message_type="thinking", flush=True)
            in_thinking = False

        return in_thinking

    def _start_output_monitor(self):
        """启动输出监控线程"""
        def monitor_stdout():
            """监控stdout（流式输出）"""
            stream_started = False
            in_thinking = False

            while self.running and self.process and self.process.poll() is None:
                rlist, _, _ = select([self.process.stdout], [], [], self.select_timeout)
                if rlist:
                    line = self.process.stdout.readline()
                    if not line:
                        break

                    line_str = self._decode_line(line)
                    logger.debug(f"收到stdout行: {repr(line_str)}")

                    if line_str.strip() == STREAM_START_MARKER:
                        stream_started = True
                        logger.info("开始接收LLM流式输出")

                        # 配置隐式思考模式时，流式开始即进入思考状态
                        if self.implicit_thinking and not in_thinking:
                            self.color_manager.print_colored(self.thinking_start_indicator, message_type="thinking", end="", flush=True)
                            in_thinking = True

                    elif line_str.strip() == STREAM_END_MARKER:
                        # 处理思考状态结束
                        if in_thinking:
                            self.color_manager.print_colored(self.thinking_end_indicator, message_type="thinking")
                            in_thinking = False

                        stream_started = False
                        self.response_complete = True
                        logger.info(f"LLM流式输出完成，当前响应长度: {len(self.assistant_response)}")
                        logger.debug(f"当前assistant_response内容: {repr(self.assistant_response[:200])}")

                    elif stream_started:
                        in_thinking = self._process_stream_content(line_str, in_thinking)

                    elif line_str.strip():
                        # 其他输出
                        logger.debug(f"Backend stdout: {line_str}")

        def monitor_stderr():
            """监控stderr（状态消息）"""
            while self.running and self.process and self.process.poll() is None:
                rlist, _, _ = select([self.process.stderr], [], [], self.select_timeout)
                if rlist:
                    line = self.process.stderr.readline()
                    if not line:
                        break

                    line_str = self._decode_line(line)
                    msg = self._parse_json_message(line_str)

                    if msg:
                        self._process_backend_message(msg)
                    else:
                        self._process_non_json_message(line_str)

    def _process_backend_message(self, msg: Dict[str, Any]):
        """处理 backend 消息"""
        msg_type = msg.get("type")
        msg_status = msg.get("status")
        msg_text = msg.get("message", "")

        if msg_type == "status":
            if msg_status == "success":
                if "Streaming completed" in msg_text or "完整响应已生成" in msg_text:
                    self.response_complete = True
                    logger.info(f"响应完成: {msg_text}")
                else:
                    logger.info(f"状态: {msg_text}")
            elif msg_status == "processing":
                logger.info(f"处理中: {msg_text}")
            else:
                logger.info(f"状态: {msg_text}")
        elif msg_type == "response":
            logger.info(f"后端响应: {msg_text}")
        elif msg_type == "error":
            print_error(f"{msg_text}")
            logger.error(f"Backend错误: {msg_text}")
        elif msg_type == "message":
            logger.debug(f"Backend消息: {msg_text}")
        else:
            logger.debug(f"Backend状态: {msg}")

    def _process_non_json_message(self, line_str: str):
        """处理非 JSON 消息"""
        if line_str.strip():
            try:
                import codecs
                # 尝试解码转义的Unicode字符串
                decoded_text = line_str.strip().encode().decode('unicode_escape')
                logger.debug(f"Backend stderr: {decoded_text}")
            except:
                logger.debug(f"Backend stderr: {line_str.strip()}")

    def _start_output_monitor(self):
        """启动输出监控线程"""
        def monitor_stdout():
            """监控stdout（流式输出）"""
            stream_started = False
            in_thinking = False

            while self.running and self.process and self.process.poll() is None:
                rlist, _, _ = select([self.process.stdout], [], [], self.select_timeout)
                if rlist:
                    line = self.process.stdout.readline()
                    if not line:
                        break

                    line_str = self._decode_line(line)
                    logger.debug(f"收到stdout行: {repr(line_str)}")

                    if line_str.strip() == STREAM_START_MARKER:
                        stream_started = True
                        logger.info("开始接收LLM流式输出")

                        # 配置隐式思考模式时，流式开始即进入思考状态
                        if self.implicit_thinking and not in_thinking:
                            self.color_manager.print_colored(self.thinking_start_indicator, message_type="thinking", end="", flush=True)
                            in_thinking = True

                    elif line_str.strip() == STREAM_END_MARKER:
                        # 处理思考状态结束
                        if in_thinking:
                            self.color_manager.print_colored(self.thinking_end_indicator, message_type="thinking")
                            in_thinking = False

                        stream_started = False
                        self.response_complete = True
                        logger.info(f"LLM流式输出完成，当前响应长度: {len(self.assistant_response)}")
                        logger.debug(f"当前assistant_response内容: {repr(self.assistant_response[:200])}")

                    elif stream_started:
                        in_thinking = self._process_stream_content(line_str, in_thinking)

                    elif line_str.strip():
                        # 其他输出
                        logger.debug(f"Backend stdout: {line_str}")

        def monitor_stderr():
            """监控stderr（状态消息）"""
            while self.running and self.process and self.process.poll() is None:
                rlist, _, _ = select([self.process.stderr], [], [], self.select_timeout)
                if rlist:
                    line = self.process.stderr.readline()
                    if not line:
                        break

                    line_str = self._decode_line(line)
                    msg = self._parse_json_message(line_str)

                    if msg:
                        self._process_backend_message(msg)
                    else:
                        self._process_non_json_message(line_str)

        # 启动监控线程
        logger.info("启动stdout监控线程")
        threading.Thread(target=monitor_stdout, daemon=True).start()
        logger.info("启动stderr监控线程")
        threading.Thread(target=monitor_stderr, daemon=True).start()

    def start(self) -> bool:
        """
        启动客户端
        """
        if self.running:
            print_system("客户端已在运行")
            return True

        # 启动backend
        if not self._start_backend():
            return False

        self.running = True
        self.response_complete = False
        self.assistant_response = ""

        # 启动输出监控
        self._start_output_monitor()

        return True

    def stop_backend(self):
        """停止backend进程"""
        logger.info("停止客户端和backend进程")
        self.running = False

        if self.process:
            try:
                # 发送退出命令
                self.send_command({"type": "exit"})
                # 等待进程退出
                try:
                    self.process.wait(timeout=5)
                    logger.info("Backend进程正常退出")
                except subprocess.TimeoutExpired:
                    logger.warning("Backend进程未及时退出，强制终止")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                        logger.info("Backend进程已终止")
                    except subprocess.TimeoutExpired:
                        logger.error("Backend进程无法终止，强制杀死")
                        self.process.kill()
                        self.process.wait()
            except Exception as e:
                logger.error(f"停止backend时出错: {e}")

            self.process = None

    def send_command(self, command: Dict[str, Any]) -> bool:
        """
        发送命令到backend

        Args:
            command: 命令字典

        Returns:
            是否发送成功
        """
        if not self.process or self.process.poll() is not None:
            print_error("Backend进程未运行")
            logger.error("Backend进程未运行，无法发送命令")
            return False

        try:
            command_str = json.dumps(command, ensure_ascii=False)
            self.process.stdin.write((command_str + '\n').encode('utf-8'))
            self.process.stdin.flush()
            if command.get("type") == "chat":
                logger.info(f"发送聊天命令: {command_str}")
            else:
                logger.debug(f"发送命令: {command_str}")
            return True
        except Exception as e:
            print_error(f"发送命令失败: {e}")
            logger.error(f"发送命令失败: {e}")
            return False

    def _wait_for_completion(self, timeout: float = None, context: str = "操作") -> bool:
        """等待操作完成"""
        start_time = time.time()
        timeout = timeout if timeout is not None else self.response_timeout

        while time.time() - start_time < timeout:
            if self.response_complete:
                return True

            if self._check_process_exited(context):
                return False

            # 报告等待状态
            elapsed = time.time() - start_time
            if int(elapsed) % 10 == 0 and elapsed > 0:  # 每10秒报告一次
                logger.info(f"等待{context}完成中，已等待 {elapsed:.1f} 秒，当前响应长度: {len(self.assistant_response)} 字符")

            time.sleep(0.01)

        error_msg = f"{context}超时 (>{timeout}秒)"
        print_error(error_msg)
        logger.error(error_msg)
        return False

    def chat(self, prompt: str, max_tokens: Optional[int] = None) -> bool:
        """
        发送聊天请求并等待完成（不带上下文）

        Args:
            prompt: 用户提示
            max_tokens: 最大生成token数

        Returns:
            是否成功完成
        """
        logger.info(f"发送聊天请求: {prompt}")
        cmd = {"type": "chat", "prompt": prompt}
        if max_tokens:
            cmd["max_new_tokens"] = max_tokens

        success = self.send_command(cmd)
        if not success:
            return False

        if not self._wait_for_completion(context="聊天"):
            return False

        logger.info(f"聊天完成，响应长度: {len(self.assistant_response)}")
        return True

    def set_system_prompt(self, system_prompt: str) -> bool:
        """
        设置系统提示词

        Args:
            system_prompt: 系统提示词内容

        Returns:
            是否设置成功
        """
        logger.info(f"设置系统提示词: {system_prompt}")
        cmd = {"type": "system_prompt", "system_prompt": system_prompt}

        success = self.send_command(cmd)
        if not success:
            return False

        # 等待确认完成（系统提示词设置通常是同步的）
        time.sleep(0.1)

        # 更新客户端上下文管理器
        self.context_manager.set_system_prompt(system_prompt)

        print_system("系统提示词已设置")
        logger.info("系统提示词设置完成")
        return True

    def get_system_prompt(self) -> str:
        """
        获取当前系统提示词

        Returns:
            当前系统提示词
        """
        return self.context_manager.get_system_prompt()

    def clear_system_prompt(self) -> bool:
        """
        清除系统提示词

        Returns:
            是否清除成功
        """
        return self.set_system_prompt("")

    def chat_with_context(self, prompt: str, max_tokens: Optional[int] = None, show_user_input: bool = True) -> bool:
        """
        发送带上下文的聊天请求

        注意：后端已经管理对话历史，所以客户端只需要发送当前的用户提示

        Args:
            prompt: 用户提示
            max_tokens: 最大生成token数
            show_user_input: 是否在控制台显示用户输入（交互式demo通常会显示）

        Returns:
            是否成功完成
        """
        # 重置响应状态
        self.response_complete = False
        self.assistant_response = ""

        # 显示用户输入（彩色）- 仅在需要时显示
        if show_user_input:
            print_user(prompt)

        # 构建命令发送给后端 - 只发送当前的prompt，后端会管理历史
        cmd = {"type": "chat", "prompt": prompt}
        if max_tokens:
            cmd["max_new_tokens"] = max_tokens

        success = self.send_command(cmd)
        if not success:
            return False

        if not self._wait_for_completion(context="上下文聊天"):
            return False

        # 保存对话上下文
        self.context_manager.add_user_message(prompt)
        self.context_manager.add_assistant_response(self.assistant_response)

        logger.info(f"上下文聊天完成，响应长度: {len(self.assistant_response)}")
        return True

    def _format_context_as_prompt(self, context: List[Dict[str, str]]) -> str:
        """
        将上下文数组格式化为prompt字符串

        Args:
            context: 上下文消息列表

        Returns:
            格式化后的prompt字符串
        """
        if not context:
            return ""

        prompt_parts = []
        for msg in context:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue

            if role == "system":
                prompt_parts.append(f"系统：{content}")
            elif role == "user":
                prompt_parts.append(f"用户：{content}")
            elif role == "assistant":
                prompt_parts.append(f"助手：{content}")
            else:
                prompt_parts.append(f"{role}：{content}")

        return "\n\n".join(prompt_parts)

    def reset_context(self, keep_system_prompt: bool = True):
        """重置对话上下文"""
        logger.info("重置对话上下文")

        # 向后端发送reset命令
        reset_cmd = {"type": "reset"}
        success = self.send_command(reset_cmd)
        if success:
            logger.info("后端上下文已重置")
        else:
            logger.warning("后端重置命令发送失败")

        # 重置客户端上下文管理器
        self.context_manager.reset_context(keep_system_prompt)

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        return self.context_manager.get_conversation_summary()