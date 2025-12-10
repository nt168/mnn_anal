#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常模块单元测试
测试框架异常类的继承关系和功能
"""

from framework.utils.exceptions import (
    FrameworkError,
    ConfigError,
    ModelAliasError,
    ModelAliasNotFoundError,
    InvalidModelPathError,
    ProjectRootError
)


class TestExceptions:
    """异常类测试"""

    def test_exception_hierarchy(self):
        """测试异常继承关系"""
        # 框架异常基类
        assert issubclass(FrameworkError, Exception)

        # 配置异常基类
        assert issubclass(ConfigError, FrameworkError)
        assert issubclass(ConfigError, Exception)

        # 模型别名异常基类
        assert issubclass(ModelAliasError, ConfigError)
        assert issubclass(ModelAliasError, FrameworkError)
        assert issubclass(ModelAliasError, Exception)

        # 具体异常类
        assert issubclass(ModelAliasNotFoundError, ModelAliasError)
        assert issubclass(ModelAliasNotFoundError, ConfigError)
        assert issubclass(ModelAliasNotFoundError, FrameworkError)
        assert issubclass(ModelAliasNotFoundError, Exception)

        assert issubclass(InvalidModelPathError, ModelAliasError)
        assert issubclass(InvalidModelPathError, ConfigError)
        assert issubclass(InvalidModelPathError, FrameworkError)
        assert issubclass(InvalidModelPathError, Exception)

        assert issubclass(ProjectRootError, FrameworkError)
        assert issubclass(ProjectRootError, Exception)

    def test_exception_instantiation(self):
        """测试异常实例化"""
        # 基础异常
        base_error = FrameworkError("基础框架错误")
        assert str(base_error) == "基础框架错误"

        # 配置异常
        config_error = ConfigError("配置错误")
        assert str(config_error) == "配置错误"

        # 模型别名异常
        alias_error = ModelAliasError("模型别名错误")
        assert str(alias_error) == "模型别名错误"

        # 具体异常
        not_found_error = ModelAliasNotFoundError("模型不存在")
        assert str(not_found_error) == "模型不存在"

        invalid_path_error = InvalidModelPathError("路径无效")
        assert str(invalid_path_error) == "路径无效"

        project_error = ProjectRootError("项目根目录错误")
        assert str(project_error) == "项目根目录错误"

    def test_exception_catching(self):
        """测试异常捕获"""
        # 测试基类捕获具体异常
        try:
            raise ModelAliasNotFoundError("测试错误")
        except ModelAliasError as e:
            assert isinstance(e, ModelAliasError)
            assert "测试错误" in str(e)

        # 测试更广泛的异常捕获
        try:
            raise InvalidModelPathError("路径错误")
        except ConfigError as e:  # 捕获配置相关异常
            assert isinstance(e, ConfigError)
            assert isinstance(e, ModelAliasError)
            assert "路径错误" in str(e)

        # 测试最基础的异常捕获
        try:
            raise ProjectRootError("项目错误")
        except FrameworkError as e:
            assert isinstance(e, FrameworkError)
            assert "项目错误" in str(e)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])