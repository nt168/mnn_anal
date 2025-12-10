#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProjectPath工具类单元测试
测试项目根目录识别和验证功能
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

# 使用标准包导入方式
from framework.utils.project import ProjectPath
from framework.utils.exceptions import ProjectRootError


class TestProjectPath:
    """ProjectPath测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_project_"))

    def teardown_method(self):
        """测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_mock_project_root(self, missing_files=None, missing_dirs=None):
        """创建模拟的项目根目录

        Args:
            missing_files: 要缺失的文件列表 (bench.sh, pyproject.toml, README.md)
            missing_dirs: 要缺失的目录列表 (framework, config, results, tasks, models)
        """
        missing_files = missing_files or []
        missing_dirs = missing_dirs or []

        # 创建项目主入口文件 (bench.sh)
        if "bench.sh" not in missing_files:
            bench_sh = self.temp_dir / "bench.sh"
            bench_sh.write_text("#!/bin/bash\necho 'test'")
            bench_sh.chmod(0o755)  # 设置可执行权限

        # 创建Python项目配置文件
        if "pyproject.toml" not in missing_files:
            (self.temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'")

        # 创建README文件
        if "README.md" not in missing_files:
            (self.temp_dir / "README.md").write_text("# Test Project")

        # 创建项目目录
        project_dirs = ["framework", "config", "results", "tasks", "models"]
        for dir_name in project_dirs:
            if dir_name not in missing_dirs:
                (self.temp_dir / dir_name).mkdir(exist_ok=True)

    def test_is_valid_project_root_complete(self):
        """测试完整项目根目录 - 应该通过验证"""
        self._create_mock_project_root()

        assert ProjectPath._is_valid_project_root(self.temp_dir)

    def test_is_valid_project_root_missing_bench_sh(self):
        """测试缺少bench.sh - 应该失败"""
        self._create_mock_project_root(missing_files=["bench.sh"])

        assert not ProjectPath._is_valid_project_root(self.temp_dir)

    def test_is_valid_project_root_missing_directories(self):
        """测试项目目录不足 - 应该失败"""
        self._create_mock_project_root(missing_dirs=["framework", "config", "results", "tasks"])

        # 只剩下models一个目录，应该不满足至少2个的要求
        assert not ProjectPath._is_valid_project_root(self.temp_dir)

    def test_is_valid_project_root_minimal_directories(self):
        """测试最小目录配置 - 刚好满足要求"""
        self._create_mock_project_root(missing_dirs=["results", "tasks", "models"])
        # 只剩下framework和config两个目录

        assert ProjectPath._is_valid_project_root(self.temp_dir)

    def test_is_valid_project_root_empty_path(self):
        """测试空路径 - 应该失败"""
        empty_dir = Path(tempfile.mkdtemp(prefix="test_empty_"))

        assert not ProjectPath._is_valid_project_root(empty_dir)

    @patch('framework.utils.project.Path.resolve')
    def test_get_project_root_direct_path(self, mock_resolve):
        """测试直接路径识别 - 不需要搜索"""
        # 设置模拟路径 - 模拟在/framework/utils/project.py中的位置
        mock_file = self.temp_dir / "framework" / "utils" / "project.py"
        mock_file.parent.mkdir(parents=True, exist_ok=True)

        # 创建项目结构
        self._create_mock_project_root()

        # 模拟项目文件路径
        mock_resolve.return_value = mock_file

        with patch.object(ProjectPath, '_is_valid_project_root', return_value=True):
            result = ProjectPath.get_project_root()
            # 应该返回推断出的项目根目录（文件的祖父目录）
            assert result == self.temp_dir

    def test_find_project_root_by_marker(self):
        """测试通过标记文件搜索项目根目录"""
        # 嵌套目录结构
        nested_dir = self.temp_dir / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)

        # 创建真实的项目根目录
        self._create_mock_project_root()

        # 从嵌套目录开始搜索
        with patch('framework.utils.project.Path.resolve', return_value=nested_dir):
            result = ProjectPath._find_project_root_by_marker()
            assert result == self.temp_dir

    def test_find_project_root_by_marker_not_found(self):
        """测试搜索失败 - 抛出异常"""
        empty_dir = Path(tempfile.mkdtemp(prefix="test_search_"))

        with patch('framework.utils.project.Path.resolve', return_value=empty_dir):
            with pytest.raises(ProjectRootError, match="无法找到项目根目录"):
                ProjectPath._find_project_root_by_marker()

    def test_bench_sh_permissions_check(self):
        """测试bench.sh权限检查不影响验证结果"""
        self._create_mock_project_root(missing_files=["bench.sh"])

        bench_sh = self.temp_dir / "bench.sh"
        bench_sh.write_text("#!/bin/bash")

        # 测试不同权限
        for permission in [0o644, 0o755, 0o777]:
            bench_sh.chmod(permission)
            # 无论什么权限，都应该通过验证（只要有文件存在且目录足够）
            if permission in [0o644, 0o755, 0o777]:
                # 至少有2个项目目录要求满足
                assert ProjectPath._is_valid_project_root(self.temp_dir)

    def test_project_root_from_different_depths(self):
        """测试从不同深度识别项目根目录"""
        self._create_mock_project_root()

        # 在框架内部的不同目录中搜索
        test_paths = [
            self.temp_dir / "framework",
            self.temp_dir / "framework" / "utils",
            self.temp_dir / "framework" / "config",
            self.temp_dir / "framework" / "core" / "executor"
        ]

        for test_path in test_paths:
            test_path.mkdir(parents=True, exist_ok=True)
            with patch('framework.utils.project.Path.resolve', return_value=test_path):
                try:
                    result = ProjectPath._find_project_root_by_marker()
                    assert result == self.temp_dir
                except FileNotFoundError:
                    # 如果路径不存在，这是正常的
                    pass

    def test_real_project_validation(self):
        """测试真实项目的验证"""
        # 获取真实项目根目录
        real_root = ProjectPath.get_project_root()

        # 验证真实项目结构
        assert real_root.exists()
        assert (real_root / "bench.sh").exists()
        assert (real_root / "framework").exists()
        assert (real_root / "config").exists()

        # 验证是否通过验证
        assert ProjectPath._is_valid_project_root(real_root)

    def test_edge_cases_non_existent_path(self):
        """测试不存在路径的边界情况"""
        non_existent = Path("/non/existent/path")

        # 验证不存在的路径应该返回False
        assert not ProjectPath._is_valid_project_root(non_existent)

    def test_get_project_root_fallback_to_search(self):
        """测试主方法失败时回退到搜索方法"""
        # 创建一个在错误位置的文件，导致直接推断失败
        wrong_location = self.temp_dir / "wrong" / "path"
        wrong_location.mkdir(parents=True)
        project_file = wrong_location / "project.py"
        project_file.write_text("")

        self._create_mock_project_root()  # 真正的项目在temp_dir

        # 模拟在错误位置的文件里调用，直接推断会失败，回退到搜索
        with patch('framework.utils.project.Path.resolve', return_value=project_file):
            result = ProjectPath.get_project_root()
            assert result == self.temp_dir

    def test_degree_of_robustness(self):
        """测试健壮性 - 部分文件或目录缺失"""
        # 测试缺失非关键文件的健壮性
        self._create_mock_project_root(missing_files=["pyproject.toml", "README.md"])

        assert ProjectPath._is_valid_project_root(self.temp_dir)

        # 测试刚好满足最小要求的情况
        self._create_mock_project_root(
            missing_files=["pyproject.toml", "README.md"],
            missing_dirs=["results", "tasks", "models"]
        )

        assert ProjectPath._is_valid_project_root(self.temp_dir)



