import os
import toml
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# 添加路径支持
try:
    from .logger import logger
except ImportError:
    # 适用于直接运行的情况
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logger import logger


@dataclass
class ClientConfig:
    """客户端配置数据类"""
    default_backend_path: str = "./mnn_llm_stdio_backend"
    default_model: str = "./model/config.json"
    init_timeout: float = 30.0
    init_sleep_time: float = 0.1
    response_timeout: float = 60.0
    shutdown_timeout: float = 5.0
    select_timeout: float = 0.1


@dataclass
class DisplayConfig:
    """显示配置数据类"""
    show_timing: bool = True
    show_response_length: bool = True
    time_precision: int = 2
    separator_length: int = 50


@dataclass
class ChatConfig:
    """对话配置数据类"""
    default_prompt: str = "你好，请介绍一下MNN框架"
    default_batch_file: str = "example_commands.txt"
    show_progress: bool = True


@dataclass
class LoggingConfig:
    """日志配置数据类"""
    log_file: str = "mnn_llm_demo.log"
    log_level: str = "INFO"
    enable_file_log: bool = True
    enable_console_log: bool = True


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = self._resolve_config_path(config_file)
        self.config: Dict[str, Any] = {}

        # 配置对象
        self._client_config: Optional[ClientConfig] = None
        self._display_config: Optional[DisplayConfig] = None
        self._chat_config: Optional[ChatConfig] = None
        self._logging_config: Optional[LoggingConfig] = None

        self._load_config()

    def _resolve_config_path(self, config_file: Optional[Union[str, Path]]) -> Path:
        """解析配置文件路径"""
        if config_file is None:
            # 使用当前目录的配置文件
            current_dir = Path(__file__).parent
            return current_dir / "config.toml"

        return Path(config_file)

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            # 只支持TOML格式
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = toml.load(f)
                logger.info(f"成功加载TOML配置文件: {self.config_file}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
                self._set_default_config()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("使用默认配置")
            self._set_default_config()

        # 初始化配置对象
        self._init_config_objects()

    def _set_default_config(self):
        """设置默认配置"""
        self.config = {
            "client": {
                "default_backend_path": "./mnn_llm_stdio_backend",
                "default_model": "./model/config.json",
                "init_timeout": 30.0,
                "init_sleep_time": 0.1,
                "response_timeout": 60.0,
                "shutdown_timeout": 5.0,
                "select_timeout": 0.1
            },
            "chat": {
                "default_prompt": "你好，请介绍一下MNN框架",
                "default_batch_file": "example_commands.txt",
                "show_progress": True
            },
            "display": {
                "show_timing": True,
                "show_response_length": True,
                "time_precision": 2,
                "separator_length": 50
            },
            "logging": {
                "log_file": "mnn_llm_demo.log",
                "log_level": "INFO",
                "enable_file_log": True,
                "enable_console_log": True
            }
        }

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            section: 配置节名称
            key: 配置键名称
            default: 默认值

        Returns:
            配置值
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            logger.warning(f"获取配置失败 [{section}.{key}]: {e}")
            return default

    def _init_config_objects(self) -> None:
        """初始化配置对象"""
        self._client_config = ClientConfig(**self.config.get("client", {}))
        self._display_config = DisplayConfig(**self.config.get("display", {}))
        self._chat_config = ChatConfig(**self.config.get("chat", {}))
        self._logging_config = LoggingConfig(**self.config.get("logging", {}))

    # 新的强类型API
    @property
    def client(self) -> ClientConfig:
        """获取客户端配置（强类型）"""
        return self._client_config or ClientConfig()

    @property
    def display(self) -> DisplayConfig:
        """获取显示配置（强类型）"""
        return self._display_config or DisplayConfig()

    @property
    def chat(self) -> ChatConfig:
        """获取对话配置（强类型）"""
        return self._chat_config or ChatConfig()

    @property
    def logging(self) -> LoggingConfig:
        """获取日志配置（强类型）"""
        return self._logging_config or LoggingConfig()

    
    def get_chat_config(self) -> Dict[str, Any]:
        """获取对话配置"""
        return self.config.get("chat", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config.get("logging", {})

    def get_display_config(self) -> Dict[str, Any]:
        """获取显示配置"""
        return self.config.get("display", {})

    def get_client_config(self) -> Dict[str, Any]:
        """获取客户端配置"""
        return self.config.get("client", {})

    def expand_path(self, path: Union[str, Path]) -> str:
        """
        扩展路径中的用户目录符号

        Args:
            path: 原始路径

        Returns:
            扩展后的路径
        """
        path_str = str(path)
        return os.path.expanduser(os.path.expandvars(path_str))

    def get_backend_path(self, custom_path: Optional[str] = None) -> str:
        """
        获取backend路径

        Args:
            custom_path: 自定义路径，如果提供则使用此路径

        Returns:
            backend路径
        """
        if custom_path:
            return self.expand_path(custom_path)

        return self.expand_path(self.client.default_backend_path)

    def get_model_config_path(self, model_name: Optional[str] = None) -> str:
        """
        获取模型配置文件路径

        Args:
            model_name: 模型名称（为了兼容性保留，现在忽略）

        Returns:
            模型配置文件路径
        """
        if model_name:
            logger.info(f"model_name参数已废弃，直接使用默认模型路径")

        return self.expand_path(self.client.default_model)

    def get_default_prompt(self) -> str:
        """获取默认提示语"""
        return self.chat.default_prompt

    def get_batch_file_path(self, custom_path: Optional[str] = None) -> str:
        """
        获取批量文件路径

        Args:
            custom_path: 自定义路径，如果提供则使用此路径

        Returns:
            批量文件路径
        """
        if custom_path:
            return custom_path

        return self.chat.default_batch_file

    # 为了向后兼容保留的API，但直接使用强类型配置更好
    def should_show_timing(self) -> bool:
        """是否显示时间信息（兼容API）"""
        return self.display.show_timing

    def should_show_response_length(self) -> bool:
        """是否显示响应长度（兼容API）"""
        return self.display.show_response_length

    def should_show_progress(self) -> bool:
        """是否显示进度信息（兼容API）"""
        return self.chat.show_progress

    def get_seperator(self) -> str:
        """获取分隔线（兼容API注意拼写错误）"""
        return self.get_separator()

    def get_separator(self) -> str:
        """获取分隔线"""
        return "=" * self.display.separator_length

    def get_time_precision(self) -> int:
        """获取时间精度（兼容API）"""
        return self.display.time_precision

    def clear_cache(self) -> None:
        """清除缓存，强制重新加载配置"""
        self._load_config()

    def reload(self) -> None:
        """重新加载配置文件（更清晰的API）"""
        self._load_config()

    # 新的便捷方法
    def save_config(self, file_path: Optional[Union[str, Path]] = None) -> bool:
        """
        保存当前配置到文件

        Args:
            file_path: 保存路径，如果为None则使用原路径

        Returns:
            是否保存成功
        """
        try:
            save_path = Path(file_path) if file_path else self.config_file
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'w', encoding='utf-8') as f:
                toml.dump(self.config, f)

            logger.info(f"配置已保存到: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def validate_paths(self) -> bool:
        """
        验证配置中的路径是否有效

        Returns:
            是否都有效
        """
        issues = []

        backend_path = self.expand_path(self.client.default_backend_path)
        if not Path(backend_path).exists():
            issues.append(f"backend路径不存在: {backend_path}")

        model_path = self.expand_path(self.client.default_model)
        if not Path(model_path).exists():
            issues.append(f"模型配置文件不存在: {model_path}")

        batch_file = Path(self.chat.default_batch_file)
        if not batch_file.exists():
            issues.append(f"批量文件不存在: {batch_file}")

        if issues:
            logger.warning("路径验证发现问题:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            return False

        return True


# 全局配置实例
_config_manager = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    获取全局配置管理器实例

    Args:
        config_file: 配置文件路径

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


# 便捷函数
def get_model_config_path(model_name: str) -> str:
    """获取模型配置文件路径"""
    return get_config_manager().get_model_config_path(model_name)


def get_default_prompt() -> str:
    """获取默认提示语"""
    return get_config_manager().get_default_prompt()


def get_batch_file_path(custom_path: Optional[str] = None) -> str:
    """获取批量文件路径"""
    return get_config_manager().get_batch_file_path(custom_path)


def get_backend_path(custom_path: Optional[str] = None) -> str:
    """获取backend路径"""
    return get_config_manager().get_backend_path(custom_path)