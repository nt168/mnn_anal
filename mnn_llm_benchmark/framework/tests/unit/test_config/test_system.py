#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SystemConfig单元测试
测试系统配置管理器的功能
"""

import tempfile
import toml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

# 使用标准包导入方式
from framework.config.system import SystemConfig


class TestSystemConfig:
    """SystemConfig测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_config(self):
        """测试默认配置初始化"""
        mock_project_root = Path("/test/project")
        with patch('framework.utils.project.ProjectPath.get_project_root', return_value=mock_project_root):
            config = SystemConfig()

            assert config.project_root == mock_project_root
            assert config.config_file == str(mock_project_root / "config" / "system.toml")

    def test_init_custom_config(self):
        """测试自定义配置文件初始化"""
        custom_config = str(self.temp_dir / "custom_config.toml")
        config = SystemConfig(custom_config)

        assert config.config_file == custom_config

    def test_get_project_root(self):
        """测试获取项目根目录"""
        config = SystemConfig()
        project_root = config.project_root

        assert isinstance(project_root, Path)
        assert project_root.name == "mnn_llm_bench"  # 假设项目名称

    def test_get_config_toml(self):
        """测试读取TOML配置"""
        # 创建测试配置文件
        test_config = {
            "execution": {"timeout": 600, "threads": 8},
            "temp": {"temp_dir": "temp_dir"},
            "results": {"output_dir": "results"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        result = config.get_config()

        assert result["execution"]["timeout"] == 600
        assert result["execution"]["threads"] == 8
        assert result["temp"]["temp_dir"] == "temp_dir"
        assert result["results"]["output_dir"] == "results"

    def test_get_config_section(self):
        """测试获取特定配置节"""
        test_config = {
            "execution": {"timeout": 300},
            "logging": {"level": "INFO"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))

        # 获取特定节
        exec_config = config.get_config("execution")
        assert exec_config["timeout"] == 300

        # 获取完整配置
        full_config = config.get_config()
        assert full_config["execution"]["timeout"] == 300
        assert full_config["logging"]["level"] == "INFO"

    @patch('pathlib.Path.exists')
    def test_get_config_file_not_found(self, mock_exists):
        """测试配置文件不存在"""
        mock_exists.return_value = False

        with patch('framework.utils.project.ProjectPath.get_project_root', return_value=Path('/test')):
            config = SystemConfig("/nonexistent/config.toml")

        # 应该返回空字典或引发异常
        result = config.get_config()

        # 根据实际实现，应该返回空字典或默认配置
        assert isinstance(result, dict)

    
    
    def test_get_llm_bench_path(self):
        """测试获取MNN LLM基准工具路径"""
        test_config = {
            "llm_bench": {"path": "~/mnn/build/llm_bench"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        llm_bench_path = config.get_llm_bench_path()

        assert "llm_bench" in str(llm_bench_path)
        assert isinstance(llm_bench_path, Path)

    def test_get_results_dir(self):
        """测试获取结果目录"""
        test_config = {
            "results": {"output_dir": "results"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        results_dir = config.get_results_dir()

        assert results_dir.name == "results"
        assert isinstance(results_dir, Path)

    def test_get_database_path(self):
        """测试获取数据库路径"""
        # 测试相对路径
        test_config = {
            "database": {
                "db_dir": "data",
                "db_file": "test_results.db"
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        db_path = config.get_database_path()

        assert db_path.name == "test_results.db"
        assert isinstance(db_path, Path)
        assert str(db_path).endswith("data/test_results.db")

        # 测试绝对路径
        abs_db_dir = "/absolute/data/path"
        test_config_abs = {
            "database": {
                "db_dir": abs_db_dir,
                "db_file": "benchmark.db"
            }
        }

        config_file_abs = self.temp_dir / "config_abs.toml"
        with open(config_file_abs, 'w') as f:
            toml.dump(test_config_abs, f)

        config_abs = SystemConfig(str(config_file_abs))
        abs_path = config_abs.get_database_path()

        assert abs_path == Path(abs_db_dir) / "benchmark.db"

        # 测试默认值
        test_config_default = {}
        config_file_default = self.temp_dir / "config_default.toml"
        with open(config_file_default, 'w') as f:
            toml.dump(test_config_default, f)

        config_default = SystemConfig(str(config_file_default))
        default_path = config_default.get_database_path()

        assert str(default_path).endswith("data/benchmark_results.db")

    def test_get_log_path(self):
        """测试获取日志文件路径"""
        # 测试相对路径
        test_config = {
            "logging": {
                "log_dir": "logs",
                "log_file": "custom.log"
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        log_path = config.get_log_path()

        assert log_path.name == "custom.log"
        assert isinstance(log_path, Path)
        assert str(log_path).endswith("logs/custom.log")

        # 测试绝对路径
        abs_log_dir = "/absolute/log/path"
        test_config_abs = {
            "logging": {
                "log_dir": abs_log_dir,
                "log_file": "app.log"
            }
        }

        config_file_abs = self.temp_dir / "config_abs.toml"
        with open(config_file_abs, 'w') as f:
            toml.dump(test_config_abs, f)

        config_abs = SystemConfig(str(config_file_abs))
        abs_path = config_abs.get_log_path()

        assert abs_path == Path(abs_log_dir) / "app.log"

        # 测试默认值
        test_config_default = {}
        config_file_default = self.temp_dir / "config_default.toml"
        with open(config_file_default, 'w') as f:
            toml.dump(test_config_default, f)

        config_default = SystemConfig(str(config_file_default))
        default_path = config_default.get_log_path()

        assert str(default_path).endswith("logs/benchmark.log")

    
    def test_get_logging_config(self):
        """测试获取日志配置"""
        test_config = {
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "console": True
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        logging_config = config.get_logging_config()

        assert logging_config["level"] == "DEBUG"
        assert logging_config["console"] == True

    
    def test_get_tasks_config(self):
        """测试获取任务配置"""
        test_config = {
            "tasks": {
                "task_dir": "tasks"
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        tasks_config = config.get_tasks_config()

        assert tasks_config["task_dir"] == "tasks"

    def test_get_tasks_dir(self):
        """测试获取任务目录路径"""
        test_config = {
            "tasks": {"task_dir": "test_tasks"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        tasks_dir = config.get_tasks_dir()

        assert tasks_dir.name == "test_tasks"
        assert isinstance(tasks_dir, Path)

    def test_get_models_config_path(self):
        """测试获取模型配置文件路径"""
        # 测试相对路径
        test_config = {
            "model_config": {
                "config_dir": "config",
                "config_file": "models.toml"
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        models_path = config.get_models_config_path()

        assert isinstance(models_path, Path)
        assert str(models_path).endswith("config/models.toml")

        # 测试绝对路径
        abs_config_dir = "/absolute/config/path"
        test_config_abs = {
            "model_config": {
                "config_dir": abs_config_dir,
                "config_file": "models.toml"
            }
        }

        config_file_abs = self.temp_dir / "config_abs.toml"
        with open(config_file_abs, 'w') as f:
            toml.dump(test_config_abs, f)

        config_abs = SystemConfig(str(config_file_abs))
        abs_path = config_abs.get_models_config_path()

        assert abs_path == Path(abs_config_dir) / "models.toml"

        # 测试默认值
        test_config_default = {}

        config_file_default = self.temp_dir / "config_default.toml"
        with open(config_file_default, 'w') as f:
            toml.dump(test_config_default, f)

        config_default = SystemConfig(str(config_file_default))
        default_path = config_default.get_models_config_path()

        assert str(default_path).endswith("config/models.toml")

    def test_get_execution_config(self):
        """测试获取执行配置"""
        test_config = {
            "execution": {
                "timeout": 600,
                "buffer_size": 2048
            }
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        exec_config = config.get_execution_config()

        assert exec_config["timeout"] == 600
        assert exec_config["buffer_size"] == 2048

    def test_get_temp_dir(self):
        """测试获取临时目录路径"""
        # 测试相对路径
        test_config = {
            "temp": {"temp_dir": "temp"}
        }

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))
        temp_dir = config.get_temp_dir()

        assert temp_dir.name == "temp"
        assert isinstance(temp_dir, Path)

        # 测试绝对路径
        abs_temp_dir = "/absolute/temp/path"
        test_config_abs = {
            "temp": {"temp_dir": abs_temp_dir}
        }

        config_file_abs = self.temp_dir / "config_abs.toml"
        with open(config_file_abs, 'w') as f:
            toml.dump(test_config_abs, f)

        config_abs = SystemConfig(str(config_file_abs))
        abs_path = config_abs.get_temp_dir()

        assert abs_path == Path(abs_temp_dir)

        # 测试默认值
        config_file_default = self.temp_dir / "config_default.toml"
        with open(config_file_default, 'w') as f:
            toml.dump({}, f)

        config_default = SystemConfig(str(config_file_default))
        default_path = config_default.get_temp_dir()

        assert default_path.name == "temp"

    def test_repr_method(self):
        """测试字符串表示"""
        config = SystemConfig()
        repr_str = repr(config)

        assert "SystemConfig" in repr_str
        assert str(config.config_file) in repr_str

    def test_config_caching(self):
        """测试配置缓存机制"""
        test_config = {"key": "value"}

        config_file = self.temp_dir / "config.toml"
        with open(config_file, 'w') as f:
            toml.dump(test_config, f)

        config = SystemConfig(str(config_file))

        # 第一次调用
        result1 = config.get_config()
        # 第二次调用应该使用缓存
        result2 = config.get_config()

        assert result1 == result2
        assert result1["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])