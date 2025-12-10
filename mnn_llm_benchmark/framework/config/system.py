#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置管理模块
统一管理项目中的各种配置文件读取和路径管理
"""

import toml
from pathlib import Path
from typing import Dict, Any, Optional

from utils.project import ProjectPath


class SystemConfig:
    """系统配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化系统配置管理器

        Args:
            config_file: 系统配置文件路径，默认使用../config/system.toml
        """
        self.project_root = ProjectPath.get_project_root()
        self.config_file = config_file or str(self.project_root / "config" / "system.toml")
        self._config_cache = None

    def get_config(self, section: str = None) -> Dict[str, Any]:
        """
        获取系统配置

        Args:
            section: 配置节名，如 'logging'、'llm_bench'等

        Returns:
            完整配置或指定节的配置
        """
        if self._config_cache is None:
            self._config_cache = self._load_config()

        if section is None:
            return self._config_cache

        return self._config_cache.get(section, {})

    def _load_config(self) -> Dict[str, Any]:
        """加载TOML格式配置文件"""
        config_path = Path(self.config_file)

        if not config_path.exists():
            print(f"警告: 系统配置文件不存在: {config_path}")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return toml.load(f) or {}
        except Exception as e:
            print(f"警告: 加载系统配置失败 {config_path}: {e}")
            return {}

    def get_llm_bench_path(self) -> Path:
        """获取llm_bench工具路径"""
        config = self.get_config("llm_bench")
        path_str = config.get("path", "~/nt/mnn-tst/phy_mnn/build/llm_bench")
        return Path(path_str).expanduser()

    def get_database_path(self) -> Path:
        """获取数据库文件路径（绝对路径）"""
        config = self.get_config("database")
        db_file = config.get("db_file", "benchmark_results.db")
        db_dir = config.get("db_dir", "data")

        # 直接返回绝对路径：项目根目录 + 配置目录 + 文件名
        return self.project_root / db_dir / db_file

    def get_models_config_path(self) -> Path:
        """获取模型配置文件的完整路径（绝对路径）"""
        config = self.get_config("model_config")
        config_file = config.get("config_file", "models.toml")
        config_dir = config.get("config_dir", "config")

        # 直接返回绝对路径：项目根目录 + 配置目录 + 文件名
        return self.project_root / config_dir / config_file

    def get_log_path(self) -> Path:
        """获取日志文件路径（绝对路径）"""
        config = self.get_config("logging")
        log_file = config.get("log_file", "benchmark.log")
        log_dir = config.get("log_dir", "logs")

        # 直接返回绝对路径：项目根目录 + 配置目录 + 文件名
        return self.project_root / log_dir / log_file

    def get_results_dir(self) -> Path:
        """获取结果输出目录（绝对路径）"""
        config = self.get_config("results")
        out_dir = config.get("output_dir", "results")
        # 直接返回绝对路径：项目根目录 + 配置目录
        return self.project_root / out_dir

    def get_temp_dir(self) -> Path:
        """获取临时目录路径（绝对路径）"""
        config = self.get_config("temp")
        temp_dir = config.get("temp_dir", "temp")
        # 直接返回绝对路径：项目根目录 + 配置目录
        return self.project_root / temp_dir
    
    def get_tasks_dir(self) -> Path:
        """获取批量测试任务目录路径"""
        config = self.get_tasks_config()
        task_dir = config.get("task_dir", "tasks")
        return self.project_root / task_dir

    def get_prompts_dir(self) -> Path:
        """获取提示词文件目录路径（绝对路径）"""
        config = self.get_config("prompts")
        prompts_dir = config.get("prompts_dir", "prompts")
        return self.project_root / prompts_dir

    def get_prompt_file_path(self, prompt_filename: str) -> Path:
        """获取提示词文件的完整绝对路径

        Args:
            prompt_filename: 提示词文件名

        Returns:
            提示词文件的完整绝对路径
        """
        return self.get_prompts_dir() / prompt_filename

    def get_task_file_path(self, task_filename: str) -> Path:
        """获取任务文件的完整绝对路径

        Args:
            task_filename: 任务文件名

        Returns:
            任务文件的完整绝对路径
        """
        return self.get_tasks_dir() / task_filename

    def get_execution_config(self) -> Dict[str, Any]:
        """获取执行配置"""
        return self.get_config("execution")
    
    def get_tasks_config(self) -> Dict[str, Any]:
        """获取批量测试任务配置"""
        return self.get_config("tasks")

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        config = self.get_config("logging").copy()

        # 直接返回日志配置，路径处理由get_log_path方法负责
        return config

    def get_data_processing_config(self) -> Dict[str, Any]:
        """获取数据处理配置"""
        return self.get_config("data_processing")

    def get_web_server_config(self) -> Dict[str, Any]:
        """获取Web服务器配置"""
        return self.get_config("web_server")

    def get_web_static_dir(self) -> Path:
        """获取Web服务器静态文件目录路径（绝对路径）"""
        config = self.get_config("web_server")
        static_root = config.get("static_root", "web_server/static")
        return self.project_root / static_root

    def get_analysis_web_dir(self) -> Path:
        """获取分析报告Web目录路径（绝对路径）"""
        config = self.get_config("web_server")
        static_root = config.get("static_root", "web_server/static")
        analysis_subdir = config.get("analysis_subdir", "analysis")
        return self.project_root / static_root / analysis_subdir

    def __repr__(self) -> str:
        return f"SystemConfig(config_file={self.config_file}, project_root={self.project_root})"
