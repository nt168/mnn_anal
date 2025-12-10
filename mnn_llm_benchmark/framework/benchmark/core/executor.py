#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基准测试执行模块
负责执行单次MNN基准测试，包含模型验证、性能评估执行和结果收集
"""

import json
import socket
import subprocess
import time
import shlex
from pathlib import Path
from typing import Dict, List, Any, Optional

from config.system import SystemConfig
from utils.logger import LoggerManager


class BenchExecutor:
    """单次基准测试执行器"""

    def __init__(self, mnn_bench_path: Path, models_config: Dict[str, str]):
        """
        初始化基准测试执行器

        Args:
            mnn_bench_path: MNN LLM benchmark工具路径
            models_config: 模型配置字典 {alias: config_path}
        """
        # 初始化日志
        self.logger = LoggerManager.get_logger("BenchExecutor")

        # 验证MNN LLM benchmark工具路径
        self.mnn_bench_path = Path.expanduser(mnn_bench_path)
        if not self.mnn_bench_path.exists():
            self.logger.error(f"MNN LLM benchmark工具不存在: {self.mnn_bench_path}")
            raise FileNotFoundError(f"MNN LLM benchmark工具不存在: {self.mnn_bench_path}")

        # 保存模型配置，延迟验证（使用时再验证）
        self.models_config = models_config
        self.system_config = SystemConfig()

        self.logger.debug(f"初始化BenchExecutor: mnn_bench_path={mnn_bench_path}")
        self.logger.debug(f"BenchExecutor初始化完成，已配置 {len(models_config)} 个模型别名")

    def validate_model(self, model_alias: str) -> tuple[Path, str]:
        """
        验证模型别名和配置文件

        Args:
            model_alias: 模型别名

        Returns:
            (config_path, model_name)

        Raises:
            ValueError: 未知模型别名
            FileNotFoundError: 配置文件不存在
        """
        if model_alias not in self.models_config:
            available_aliases = list(self.models_config.keys())
            self.logger.error(f"未知模型别名: {model_alias}，可用别名: {available_aliases}")
            raise ValueError(f"未知的模型别名: {model_alias}，可用别名: {available_aliases}")

        config_str = self.models_config[model_alias]
        config_path = Path(config_str).expanduser()

        if not config_path.exists():
            self.logger.error(f"模型配置文件不存在: {config_path}")
            raise FileNotFoundError(f"模型配置文件不存在: {config_path}")

        model_name = config_path.parent.name
        self.logger.debug(f"模型验证通过: {model_name} (别名: {model_alias}) -> {config_path}")

        return config_path, model_name

    def build_command(self, config_path: Path, output_path: Path, **params) -> List[str]:
        """
        构建MNN LLM benchmark命令

        Args:
            config_path: 模型配置文件路径
            output_path: 输出文件路径（临时文件）
            **params: 基准测试参数

        Returns:
            完整的命令行参数列表
        """
        cmd = [str(self.mnn_bench_path), "-m", str(config_path), "-fp", str(output_path)]
        self.logger.debug(f"构建命令: {cmd}")

        # 添加参数 - 使用与官方一致的参数名称
        if params.get("threads"):
            cmd.extend(["-t", str(params["threads"])])
        if params.get("precision") is not None:
            cmd.extend(["-c", str(params["precision"])])
        if params.get("n_prompt"):
            cmd.extend(["-p", str(params["n_prompt"])])
        if params.get("n_gen"):
            cmd.extend(["-n", str(params["n_gen"])])
        if params.get("prompt_gen"):
            cmd.extend(["-pg", str(params["prompt_gen"])])
        if params.get("n_repeat"):
            cmd.extend(["-rep", str(params["n_repeat"])])
        if params.get("kv_cache"):
            cmd.extend(["-kv", str(params["kv_cache"])])
        if params.get("mmap"):
            cmd.extend(["-mmp", str(params["mmap"])])
        if params.get("dynamicOption") is not None:
            cmd.extend(["-dyo", str(params["dynamicOption"])])

        # 新版llm_bench_prompt参数支持
        if params.get("variable_prompt") is not None:
            cmd.extend(["-vp", str(params["variable_prompt"])])

        if params.get("prompt_file"):
            # 直接使用传入的路径，在benchmark.py中已处理过路径转换
            cmd.extend(["-pf", params["prompt_file"]])

        return cmd

    def run_command(self, cmd: List[str], timeout: int, taskset_cmd: Optional[str] = None) -> Dict[str, Any]:
        """
        执行MNN LLM benchmark命令

        Args:
            cmd: 命令行参数列表
            timeout: 超时时间（秒），必须由调用者提供
            taskset_cmd: 可选的taskset命令字符串（例如"taskset -c 1"），用于限制CPU核心

        Returns:
            执行结果字典

        Raises:
            ValueError: 超时时间无效
        """
        if timeout <= 0:
            self.logger.error(f"无效的超时时间: {timeout}，必须为正数")
            raise ValueError(f"无效的超时时间: {timeout}，必须为正数")

        full_cmd = cmd
        if taskset_cmd:
            try:
                prefix_parts = shlex.split(taskset_cmd)
            except ValueError as e:
                self.logger.error(f"taskset参数解析失败: {e}")
                prefix_parts = taskset_cmd.split()
            if prefix_parts:
                full_cmd = prefix_parts + cmd
        cmd_str = " ".join([str(c) if c != " " else "←" for c in full_cmd])
        self.logger.info(f"准备执行基准测试: {cmd_str} (超时: {timeout}秒)")

        start_time = time.time()
        try:
            self.logger.info(f"正在启动进程...")
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            end_time = time.time()

            if result.returncode == 0:
                self.logger.info(f"基准测试成功完成 - 耗时: {end_time - start_time:.2f}秒")
                self.logger.debug(f"stdout: {result.stdout[:200]}...")
            else:
                self.logger.error(f"基准测试失败 - 返回码: {result.returncode}")
                self.logger.error(f"错误输出: {result.stderr}")

                # 记录基本错误信息
                self.logger.error(f"基准测试返回码: {result.returncode}")

            return {
                "command": cmd_str,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "runtime": end_time - start_time
            }

        except subprocess.TimeoutExpired:
            end_time = time.time()
            self.logger.error(f"基准测试超时 (>{timeout}秒)")
            return {
                "command": cmd_str,
                "return_code": -1,
                "stdout": "",
                "stderr": f"基准测试超时 (>{timeout}秒)",
                "runtime": end_time - start_time
            }

    def process_benchmark_results(self, output_path: Path, model_alias: str, model_name: str,
                                 bench_params: Dict[str, Any], start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """
        处理MNN LLM benchmark输出结果数据（Markdown表格格式）

        Args:
            output_path: 结果文件路径
            model_alias: 模型别名
            model_name: 模型名称
            bench_params: 基准测试参数
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            处理后的结果数据列表
        """
        if not output_path.exists():
            self.logger.warning(f"结果文件不存在: {output_path}")
            return []

        self.logger.debug(f"处理结果: {output_path}")

        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.logger.debug(f"文件内容预览: {content[:200]}...")

            # 处理Markdown表格格式（内联处理）
            self.logger.debug("解析MNN LLM benchmark Markdown表格结果")
            results = []
            lines = [line.strip() for line in content.split('\n') if line.strip()]

            if len(lines) >= 3:  # 标题行、分隔行、数据行
                # 解析表头
                headers = [h.strip() for h in lines[0].split('|')[1:-1]]
                # 跳过分隔行（|---|---|...）
                data_lines = lines[2:]

                for row_index, line in enumerate(data_lines):
                    if not line.startswith('|'):
                        continue

                    # 解析数据行
                    values = [v.strip() for v in line.split('|')[1:-1]]

                    if len(values) != len(headers):
                        self.logger.warning(f"Markdown表格行{row_index}: 列数不匹配，期望{len(headers)}列，实际{len(values)}列")
                        self.logger.debug(f"表头: {headers}")
                        self.logger.debug(f"数据: {values}")
                        continue

                    # 构造字典并创建结果行
                    row_dict = dict(zip(headers, values))
                    results.append(self._create_result_row(row_dict, model_alias, model_name, bench_params, start_time, end_time))

            self.logger.info(f"成功处理 {len(results)} 条基准测试结果记录")
            return results

        except Exception as e:
            self.logger.error(f"结果处理异常: {e}")
            return []

    
    def _create_result_row(self, row_data: Dict[str, str], model_alias: str, model_name: str,
                          bench_params: Dict[str, Any], start_time: float, end_time: float) -> Dict[str, Any]:
        """创建标准化的结果行，支持两种格式"""
        return {
            "model_alias": model_alias,
            "model_name": model_name,
            "model_size_mb": row_data.get("modelSize", "").strip(),
            "backend": row_data.get("backend", "").strip(),
            "threads": row_data.get("threads", "").strip(),
            "precision": row_data.get("precision", "").strip(),
            # 提示词类型 - 新字段
            "ptypes": row_data.get("pType", "").strip(),
            # kv=false模式的字段
            "test_type": row_data.get("test", "").strip(),
            "tokens_per_sec": row_data.get("t/s", "").strip(),
            # kv=true模式的字段
            "llm_demo": row_data.get("llm_demo", "").strip(),
            "speed(tok/s)": row_data.get("speed(tok/s)", "").strip(),
            "test_runtime_sec": round(end_time - start_time, 3),
            "bench_params": json.dumps(bench_params, ensure_ascii=False),
            "raw_data_json": json.dumps(row_data, ensure_ascii=False)
        }

    
    def execute_bench(self, model_alias: str, timeout: int, taskset_cmd: Optional[str] = None,
                      **bench_params) -> Dict[str, Any]:
        """
        执行单次完整基准测试，返回JSON结构化结果

        Args:
            model_alias: 模型别名
            timeout: 基准测试超时时间（秒）
            taskset_cmd: 可选的taskset命令前缀（例如"taskset -c 1"）
            **bench_params: 基准测试参数

        Returns:
            基准测试执行结果，包含:
            - success: 是否成功
            - execution_result: 执行信息
            - json_result: 结构化JSON结果对象
            - temp_file_path: 临时文件路径
            - error: 错误信息（如果有）
        """
        self.logger.info(f"开始执行基准测试: {model_alias}")
        temp_file_path = None

        try:
            # 验证模型
            config_path, model_name = self.validate_model(model_alias)

            # 创建临时目录并生成临时文件
            temp_dir = self._create_temp_directory()
            temp_filename = f"{model_alias}_{int(time.time())}_raw.txt"
            temp_file_path = temp_dir / temp_filename

            self.logger.debug(f"临时文件: {temp_file_path}")

            # 构建命令（输出到临时文件）
            cmd = self.build_command(config_path, temp_file_path, **bench_params)

            # 执行命令
            start_time = time.time()
            execution_result = self.run_command(cmd, timeout, taskset_cmd=taskset_cmd)
            end_time = time.time()

            # 检查执行结果
            if execution_result["return_code"] != 0:
                error_msg = f"基准测试执行失败 (代码 {execution_result['return_code']}): {execution_result['stderr']}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "execution_result": {
                        **execution_result,
                        "temp_output_file": str(temp_file_path)
                    },
                    "json_result": None,
                    "temp_file_path": str(temp_file_path),
                    "error": error_msg
                }

            # 处理临时文件中的结果
            bench_results = self.process_benchmark_results(
                temp_file_path, model_alias, model_name,
                bench_params, start_time, end_time
            )

            if not bench_results:
                warning_msg = "基准测试未生成有效结果"
                self.logger.warning(warning_msg)
                return {
                    "success": True,
                    "execution_result": {
                        **execution_result,
                        "temp_output_file": str(temp_file_path)
                    },
                    "json_result": None,
                    "temp_file_path": str(temp_file_path),
                    "error": warning_msg
                }

            # 生成JSON结构化结果
            json_result = self._create_json_result(bench_results, execution_result,
                                                  model_name, model_alias, config_path,
                                                  bench_params, start_time, end_time, timeout)

            return {
                "success": True,
                "execution_result": {
                    **execution_result,
                    "temp_output_file": str(temp_file_path)
                },
                "json_result": json_result,
                "temp_file_path": str(temp_file_path)
            }

        except Exception as e:
            error_msg = f"基准测试执行异常: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "execution_result": {
                    "temp_output_file": str(temp_file_path) if temp_file_path else ""
                },
                "json_result": None,
                "temp_file_path": str(temp_file_path) if temp_file_path else "",
                "error": str(e)
            }

    def _create_temp_directory(self) -> Path:
        """创建临时目录"""
        temp_config = self.system_config.get_config('temp')
        temp_dir = Path(temp_config.get('temp_dir', 'temp')).expanduser()

        # 如果是相对路径，则相对于项目根目录
        if not temp_dir.is_absolute():
            project_root = self.system_config.project_root
            temp_dir = project_root / temp_dir

        # 确保目录存在
        temp_dir.mkdir(exist_ok=True)
        return temp_dir

    def _create_json_result(self, bench_results: List[Dict[str, Any]], execution_result: Dict[str, Any],
                           model_name: str, model_alias: str, config_path: Path,
                           bench_params: Dict[str, Any], start_time: float, end_time: float, timeout: int) -> Dict[str, Any]:
        """创建结构化JSON结果对象"""

        if not bench_results:
            self.logger.warning("没有基准测试结果数据")
            return None

        # 构建结构化的JSON结果
        json_result = {
            "bench_id": f"{model_alias}_{int(start_time)}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": {
                "alias": model_alias,
                "name": model_name,
                "config_path": str(config_path.expanduser()),
                "size_mb": bench_results[0].get("model_size_mb", "") if bench_results else ""
            },
            "execution": {
                "command": execution_result.get("command", ""),
                "timeout_seconds": timeout,
                "runtime_seconds": round(end_time - start_time, 3),
                "return_code": execution_result.get("return_code", 0),
                "success": execution_result.get("return_code", 0) == 0
            },
            "bench_parameters": {
                "threads": bench_params.get("threads", "uses_default"),
                "precision": bench_params.get("precision", "uses_default"),
                "n_prompt": bench_params.get("n_prompt", "uses_default"),
                "n_gen": bench_params.get("n_gen", "uses_default"),
                "prompt_gen": bench_params.get("prompt_gen", "uses_default"),
                "n_repeat": bench_params.get("n_repeat", "uses_default"),
                "kv_cache": bench_params.get("kv_cache", "uses_default"),
                "mmap": bench_params.get("mmap", "uses_default"),
                "dynamicOption": bench_params.get("dynamicOption", "uses_default")
            },
            "results": {},
            "system_info": {
                "backend": bench_results[0].get("backend", "") if bench_results else "Unknown",
                "hostname": socket.gethostname()
            }
        }

        # 判断输出格式并处理
        if bench_results and bench_results[0].get("llm_demo"):
            # kv=true模式：llm_demo格式，单行双段结果
            self._process_kv_true_results(bench_results[0], json_result)
        elif bench_results and bench_results[0].get("test_type"):
            # kv=false模式：test格式，多行结果
            self._process_kv_false_results(bench_results, json_result)
        else:
            # 未知格式
            self.logger.warning(f"未知的输出格式，结果: {bench_results[0] if bench_results else 'empty'}")

        return json_result

    def _process_kv_false_results(self, bench_results: List[Dict[str, Any]], json_result: Dict[str, Any]) -> None:
        """处理kv_cache=false模式的多行结果"""
        for result in bench_results:
            test_name = result["test_type"]  # e.g., "pp512", "tg128"

            # 识别测试类型
            if "+" in test_name:
                result_type = "combined"  # pg测试，包含+号
            elif test_name.startswith("pp"):
                result_type = "prefill"
            elif test_name.startswith("tg"):
                result_type = "decode"
            else:
                result_type = "unknown"

            # 解析性能数据 "327.85 ± 4.00" -> {mean: 327.85, std: 4.00}
            perf_str = result["tokens_per_sec"]
            perf_data = self._parse_performance_string(perf_str)

            json_result["results"][result_type] = {
                "test_name": test_name,
                "tokens_per_sec": perf_data
            }

    def _process_kv_true_results(self, bench_result: Dict[str, Any], json_result: Dict[str, Any]) -> None:
        """处理kv_cache=true模式的双段结果"""
        # 解析llm_demo名称，提取prompt和decode值
        llm_demo_info = bench_result["llm_demo"]
        # 格式: "prompt=64<br>decode=32"
        prompt_val, decode_val = self._parse_llm_demo_info(llm_demo_info)

        # 解析双段速度
        speed_data = bench_result["speed(tok/s)"]
        prefill_data, decode_data = self._parse_dual_speed(speed_data)

        json_result["results"]["prefill"] = {
            "test_name": f"pp{prompt_val}",
            "tokens_per_sec": prefill_data,
            "prompt_length": prompt_val
        }

        json_result["results"]["decode"] = {
            "test_name": f"tg{decode_val}",
            "tokens_per_sec": decode_data,
            "generate_length": decode_val
        }

    def _parse_llm_demo_info(self, llm_demo_str: str) -> tuple[int, int]:
        """解析llm_demo信息，提取prompt和decode值"""
        # 格式: "prompt=64<br>decode=32"
        parts = llm_demo_str.split("<br>")
        prompt_part = parts[0].strip()
        decode_part = parts[1].strip()

        # 提取数字
        prompt_val = int(prompt_part.split("=")[1])
        decode_val = int(decode_part.split("=")[1])

        return prompt_val, decode_val

    def _parse_dual_speed(self, speed_str: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """解析双段速度，返回(prefill_data, decode_data)"""
        # 格式: "658.19 ± 12.64<br>67.75 ± 0.79"
        parts = speed_str.split("<br>")
        prefill_str = parts[0].strip()
        decode_str = parts[1].strip()

        prefill_data = self._parse_performance_string(prefill_str)
        decode_data = self._parse_performance_string(decode_str)

        return prefill_data, decode_data

    def _parse_performance_string(self, perf_str: str) -> Dict[str, Any]:
        """解析性能字符串，如 '327.85 ± 4.00'"""
        perf_str = perf_str.strip()
        if not perf_str:
            return {
                "mean": 0.0,
                "std": 0.0,
                "formatted": ""
            }

        if "±" in perf_str:
            mean_str, std_str = perf_str.split("±")
            return {
                "mean": float(mean_str.strip()),
                "std": float(std_str.strip()),
                "formatted": perf_str.strip()
            }
        else:
            # 如果没有标准差信息
            return {
                "mean": float(perf_str.strip()),
                "std": 0.0,
                "formatted": perf_str.strip()
            }

    def __repr__(self) -> str:
        return f"BenchExecutor(mnn_bench_path={self.mnn_bench_path}, models_count={len(self.models_config)})"