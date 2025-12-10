#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型配置管理模块
专门负责模型相关的配置管理，提供简洁的模型别名映射功能
"""

import toml
import re
from pathlib import Path
from typing import Dict, Optional, List, Set

from utils.project import ProjectPath
from config.system import SystemConfig
from utils.exceptions import (
    ModelAliasNotFoundError,
    InvalidModelPathError
)


class ModelsConfig:
    """模型配置管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化模型配置管理器

        Args:
            project_root: 项目根目录，用于路径解析，默认自动获取
        """
        self.project_root = project_root or ProjectPath.get_project_root()
        self._models_cache: Optional[Dict[str, str]] = None
        self._invalid_models: Set[str] = set()
        self._config_file: Optional[Path] = None

        # 初始化时验证所有模型
        self._validate_all_models()

    def _load_config(self) -> Dict[str, str]:
        """
        加载模型配置文件

        Returns:
            模型别名映射字典 {alias: config_path}
        """
        if self._models_cache is not None:
            return self._models_cache

        # 从系统配置获取模型配置文件路径
        system_config = SystemConfig()
        self._config_file = system_config.get_models_config_path()

        if not self._config_file.exists():
            self._models_cache = {}
            return self._models_cache

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = toml.load(f)
                self._models_cache = data.get("model_mapping", {})
                return self._models_cache
        except Exception as e:
            print(f"警告: 加载模型配置失败 {self._config_file}: {e}")
            self._models_cache = {}
            return self._models_cache

    def _validate_model_path(self, config_path: Path) -> bool:
        """
        验证模型路径是否有效

        Args:
            config_path: 模型配置文件路径

        Returns:
            是否有效
        """
        return config_path.exists() and config_path.suffix == '.json'

    def _validate_all_models(self):
        """验证所有模型的有效性"""
        models_mapping = self._load_config()

        for alias, path_str in models_mapping.items():
            config_path = Path(path_str).expanduser()
            if not config_path.is_absolute():
                config_path = self.project_root / config_path

            if not self._validate_model_path(config_path):
                self._invalid_models.add(alias)

    def get_available_models(self) -> List[str]:
        """
        获取所有有效的模型别名

        Returns:
            有效的模型别名列表（排除无效路径）
        """
        models_mapping = self._load_config()
        return [
            alias for alias in models_mapping.keys()
            if alias not in self._invalid_models
        ]

    def get_model_config_path(self, alias: str) -> Path:
        """
        获取指定模型别名的配置文件路径

        Args:
            alias: 模型别名

        Returns:
            配置文件路径

        Raises:
            ModelAliasNotFoundError: 模型别名不存在
            InvalidModelPathError: 模型路径无效
        """
        models_mapping = self._load_config()

        if alias not in models_mapping:
            raise ModelAliasNotFoundError(f"模型别名不存在: {alias}")

        if alias in self._invalid_models:
            raise InvalidModelPathError(f"模型路径无效: {alias}")

        # 解析路径
        config_path = Path(models_mapping[alias]).expanduser()
        if not config_path.is_absolute():
            config_path = self.project_root / config_path

        # 再次验证（防止文件被删除）
        if not self._validate_model_path(config_path):
            self._invalid_models.add(alias)
            raise InvalidModelPathError(f"模型路径无效: {alias}")

        return config_path

    def _generate_model_alias(self, model_name: str) -> str:
        """
        根据模型名称生成别名

        Args:
            model_name: 原始模型名称（目录名）

        Returns:
            生成的别名（只包含字母、数字、下划线）
        """
        # 转换为小写，将非字母数字字符替换为下划线
        alias = re.sub(r'[^a-zA-Z0-9]', '_', model_name.lower())
        # 移除连续的下划线
        alias = re.sub(r'_+', '_', alias)
        # 移除开头和结尾的下划线
        alias = alias.strip('_')

        # 确保别名只包含字母、数字、下划线
        alias = re.sub(r'[^a-z0-9_]', '', alias)

        return alias

    def scan_and_add_models(self, models_directory: str, overwrite: bool = False) -> int:
        """
        扫描模型存储目录并自动添加到配置文件

        Args:
            models_directory: 模型存储目录的路径
            overwrite: 是否覆盖已存在的别名（False时跳过已存在的）

        Returns:
            添加的模型数量
        """
        models_dir = Path(models_directory).expanduser()
        if not models_dir.exists() or not models_dir.is_dir():
            print(f"错误: 模型目录不存在或不是目录: {models_dir}")
            return 0

        # 扫描目录中的所有config.json文件
        config_files = list(models_dir.glob("*/config.json"))
        if not config_files:
            print(f"警告: 在目录 {models_dir} 中没有找到任何模型（期望结构: */config.json）")
            return 0

        # 加载现有配置
        system_config = SystemConfig()
        config_file = system_config.get_models_config_path()

        # 创建配置文件目录（如果不存在）
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载现有模型映射
        existing_models = {}
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_data = toml.load(f)
                    existing_models = existing_data.get("model_mapping", {})
            except Exception as e:
                print(f"警告: 无法加载现有配置文件 {config_file}: {e}")

        # 准备新添加的模型
        new_models = {}
        skipped_count = 0

        for config_file_path in config_files:
            model_dir = config_file_path.parent
            model_name = model_dir.name

            # 生成别名
            alias = self._generate_model_alias(model_name)

            # 检查是否已存在
            if alias in existing_models and not overwrite:
                print(f"跳过已存在的别名: {alias} -> {existing_models[alias]}")
                skipped_count += 1
                continue

            # 添加到新模型映射
            new_models[alias] = str(config_file_path)
            print(f"添加模型: {alias} -> {config_file_path}")

        if not new_models:
            print(f"没有新模型需要添加（跳过了 {skipped_count} 个已存在的模型）")
            return 0

        # 合并现有模型和新模型
        if overwrite:
            # 覆盖模式：用新映射覆盖同键名的现有映射
            merged_models = existing_models.copy()
            merged_models.update(new_models)
        else:
            # 不覆盖模式：跳过已存在的别名
            merged_models = existing_models.copy()
            merged_models.update(new_models)
            # 如果不覆盖，理论上new_models中的键不应该存在于existing_models中

        # 写入配置文件
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                # 写入注释头
                f.write("# MNN LLM 模型配置文件\n")
                f.write("# 定义模型别名到实际config.json路径的映射\n")
                f.write("# 注意: 此文件由自动扫描工具生成和更新，也可以手动编辑\n")
                f.write("# 别名规则: 原始目录名转换为小写，特殊字符替换为下划线，只保留字母数字下划线\n\n")

                # 写入TOML数据
                f.write("[model_mapping]\n")
                for key, value in merged_models.items():
                    f.write(f'{key} = "{value}"\n')

            print(f"成功更新模型配置文件: {config_file}")
            print(f"新增模型 {len(new_models)} 个，跳过已存在 {skipped_count} 个")
            print(f"总计可用模型: {len(merged_models)} 个")

            # 清除缓存，重新加载配置
            self._models_cache = None
            self._invalid_models.clear()
            self._validate_all_models()

        except Exception as e:
            print(f"错误: 无法写入配置文件 {config_file}: {e}")
            return 0

        return len(new_models)

    def reload_config(self) -> None:
        """重新加载配置，清除缓存并重新验证"""
        self._models_cache = None
        self._invalid_models.clear()
        self._config_file = None
        self._validate_all_models()

    def __repr__(self) -> str:
        valid_count = len(self.get_available_models())
        total_count = len(self._load_config())
        return f"ModelsConfig(valid={valid_count}, total={total_count})"