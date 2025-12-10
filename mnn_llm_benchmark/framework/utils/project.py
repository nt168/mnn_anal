#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目路径工具
提供项目根目录获取等公共路径相关功能
"""

from pathlib import Path
from utils.exceptions import ProjectRootError


class ProjectPath:
    """项目路径工具类"""

    @staticmethod
    def get_project_root() -> Path:
        """
        获取项目根目录

        Returns:
            项目根目录路径

        Raises:
            ProjectRootError: 无法找到项目根目录
        """
        # 方法1: 基于当前文件路径推断
        # 对于framework/utils/project.py，需要回到项目根目录
        current_file = Path.resolve(Path(__file__))
        project_root = current_file.parent.parent.parent

        # 验证是否是有效的项目根目录
        if not ProjectPath._is_valid_project_root(project_root):
            # 方法2: 搜索项目标记文件
            project_root = ProjectPath._find_project_root_by_marker()

        return project_root

    @staticmethod
    def _is_valid_project_root(path: Path) -> bool:
        """
        验证路径是否为有效的项目根目录

        验证优先级：
        1. 主要标志：项目主入口 (bench.sh)
        2. 次要标志：项目目录结构 (framework/, config/ 等)
        3. 可选标志：Python项目文件 (pyproject.toml)
        """
        # 主要标志：项目主入口脚本
        if not (path / "bench.sh").exists():
            return False

        # 次要标志：验证这是可执行的主入口，而不仅仅是同名文件
        bench_sh_path = path / "bench.sh"
        try:
            if not oct(bench_sh_path.stat().st_mode)[-3] in ('755', '754', '755', '750', '744'):
                # 不是可执行文件，可能不是真正的主入口
                pass
        except (OSError, AttributeError):
            pass

        # 通用标志：项目目录结构
        project_indicators = [
            "framework",  # 框架代码目录
            "config",     # 配置文件目录
            "results",    # 结果输出目录
            "tasks",       # 任务文件目录
            "models"       # 模型目录
        ]

        # 至少包含两个核心项目目录
        found_dirs = sum(1 for indicator in project_indicators if (path / indicator).exists())
        if found_dirs < 2:
            return False

        # 基本验证：看起来像是一个MNN LLM基准测试项目
        return True

    @staticmethod
    def _find_project_root_by_marker() -> Path:
        """通过搜索项目标记文件来找到项目根目录"""
        current = Path.resolve(Path(__file__))

        while current != current.parent:  # 直到根目录
            if ProjectPath._is_valid_project_root(current):
                return current
            current = current.parent

        raise ProjectRootError("无法找到项目根目录，请确保在项目内执行或提供项目根目录")