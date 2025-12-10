#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架异常模块
定义框架中的所有自定义异常类
"""


class FrameworkError(Exception):
    """框架异常基类"""
    pass


class ConfigError(FrameworkError):
    """配置相关异常基类"""
    pass


class ModelAliasError(ConfigError):
    """模型别名相关异常的基类"""
    pass


class ModelAliasNotFoundError(ModelAliasError):
    """模型别名不存在异常"""
    pass


class InvalidModelPathError(ModelAliasError):
    """模型路径无效异常"""
    pass


class ProjectRootError(FrameworkError):
    """项目根目录相关异常"""
    pass


class FileNotFoundError(ProjectRootError):
    """找不到项目根目录异常"""
    pass


class BenchmarkError(FrameworkError):
    """基准测试错误异常"""

    def __init__(self, error_info):
        self.error_info = error_info
        super().__init__(str(error_info))


class ExecutorError(FrameworkError):
    """执行器错误异常"""

    def __init__(self, message, return_code=None, stderr=None):
        self.message = message
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(message)