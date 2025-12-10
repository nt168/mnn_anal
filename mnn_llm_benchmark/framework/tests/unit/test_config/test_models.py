#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ModelsConfig单元测试
测试模型配置管理器的功能
"""

import tempfile
import toml
from pathlib import Path
from unittest.mock import patch
import pytest

# 使用标准包导入方式
from framework.config.models import ModelsConfig
from framework.utils.exceptions import (
    ModelAliasError,
    ModelAliasNotFoundError,
    InvalidModelPathError
)


class TestModelsConfig:
    """ModelsConfig测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_models_config(self):
        """测试默认初始化"""
        models_config = ModelsConfig()

        assert models_config.project_root.name == "mnn_llm_bench"
        assert isinstance(models_config.get_available_models(), list)

    def test_init_custom_project_root(self):
        """测试自定义项目根目录"""
        models_config = ModelsConfig(project_root=self.temp_dir)

        assert models_config.project_root == self.temp_dir

    def test_load_models_config_success(self):
        """测试成功加载模型配置"""
        test_models = {
            "model_mapping": {
                "qwen3_06b": "~/models/Qwen3-0.6B-MNN/config.json",
                "deepseek_r1_15b": "~/models/DeepSeek-R1-1.5B-MNN/config.json"
            }
        }

        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_models, f)

        # 创建系统配置指向这个文件
        system_config_content = {
            "model_config": {
                "config_file": str(config_file),
                "config_dir": str(self.temp_dir)
            }
        }
        system_config_file = self.temp_dir / "system.toml"
        with open(system_config_file, 'w') as f:
            toml.dump(system_config_content, f)

        # 使用patch来模拟系统配置
        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)
            loaded_models = models_config._load_config()

        assert len(loaded_models) == 2
        assert "qwen3_06b" in loaded_models
        assert "deepseek_r1_15b" in loaded_models

    def test_get_available_models(self):
        """测试获取可用模型列表"""
        test_models = {
            "model_mapping": {
                "model_a": "path/a.json",
                "model_b": "path/b.json",
                "model_c": "path/c.json"
            }
        }

        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_models, f)

        # 创建部分模型文件
        (self.temp_dir / "path").mkdir()
        (self.temp_dir / "path" / "a.json").touch()
        (self.temp_dir / "path" / "b.json").touch()
        # model_c 没有文件，应该被过滤掉

        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)
            available_models = models_config.get_available_models()

        assert len(available_models) == 2
        assert "model_a" in available_models
        assert "model_b" in available_models

    def test_get_model_config_path_success(self):
        """测试成功获取模型配置路径"""
        test_models = {
            "model_mapping": {
                "test_model": "model/config.json"
            }
        }

        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_models, f)

        # 创建模型配置文件
        model_dir = self.temp_dir / "model"
        model_dir.mkdir()
        model_config = model_dir / "config.json"
        model_config.touch()

        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)

            path = models_config.get_model_config_path("test_model")

        assert path == model_config
        assert path.exists()

    def test_get_model_config_path_not_found(self):
        """测试获取不存在模型的配置路径"""
        models_config = ModelsConfig(project_root=self.temp_dir)

        with pytest.raises(ModelAliasNotFoundError):
            models_config.get_model_config_path("nonexistent_model")

    def test_invalid_model_path(self):
        """测试无效模型路径异常"""
        test_models = {
            "model_mapping": {
                "invalid_model": "nonexistent/config.json"
            }
        }

        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_models, f)

        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)

            with pytest.raises(InvalidModelPathError):
                models_config.get_model_config_path("invalid_model")

    def test_reload_config(self):
        """测试重新加载配置"""
        models_config_data = {
            "model_mapping": {
                "initial_model": "model/config.json"
            }
        }
        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(models_config_data, f)

        # 创建模型配置文件
        model_dir = self.temp_dir / "model"
        model_dir.mkdir()
        (model_dir / "config.json").touch()

        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)
            initial_available = models_config.get_available_models()
            assert len(initial_available) == 1

            # 修改文件，添加新模型
            models_config_data["model_mapping"]["new_model"] = "new/model.json"
            with open(config_file, 'w') as f:
                toml.dump(models_config_data, f)

            # 重新加载前应该看不到新模型
            assert "new_model" not in models_config.get_available_models()

            # 重新加载配置
            models_config.reload_config()

            # 重新加载后仍然看不到新模型，因为文件不存在
            assert "new_model" not in models_config.get_available_models()

    def test_models_config_caching(self):
        """测试配置缓存机制"""
        models_config_data = {
            "model_mapping": {"test_model": "model/test.json"}
        }
        config_file = self.temp_dir / "models.toml"
        with open(config_file, 'w') as f:
            toml.dump(models_config_data, f)

        # 创建测试模型文件
        model_dir = self.temp_dir / "model"
        model_dir.mkdir()
        (model_dir / "test.json").touch()

        with patch('framework.config.models.SystemConfig') as mock_system:
            mock_system.return_value.get_models_config_path.return_value = config_file
            models_config = ModelsConfig(project_root=self.temp_dir)

            # 第一次调用
            result1 = models_config._load_config()
            # 第二次调用应该使用缓存
            result2 = models_config._load_config()

            assert result1 == result2
            assert result1["test_model"] == "model/test.json"

    def test_repr_method(self):
        """测试字符串表示"""
        models_config = ModelsConfig(project_root=self.temp_dir)
        repr_str = repr(models_config)

        assert "ModelsConfig" in repr_str
        assert "valid=" in repr_str
        assert "total=" in repr_str

    def test_exception_hierarchy(self):
        """测试异常继承关系"""
        assert issubclass(ModelAliasNotFoundError, ModelAliasError)
        assert issubclass(InvalidModelPathError, ModelAliasError)
        assert issubclass(ModelAliasError, Exception)

    def test_config_file_not_found(self):
        """测试配置文件不存在的情况"""
        with patch('framework.config.models.SystemConfig') as mock_system, \
             patch('pathlib.Path.exists', return_value=False):

            mock_system.return_value.get_models_config_path.return_value = Path("/nonexistent/models.toml")
            models_config = ModelsConfig(project_root=self.temp_dir)

            assert models_config.get_available_models() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])