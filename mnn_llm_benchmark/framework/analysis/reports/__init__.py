"""
报告生成模块

提供HTML和Markdown报告生成功能
"""

from .base import BaseFormatter, MetadataBuilder, VarianceExplainer
from .html_formatter import HTMLFormatter
from .markdown_formatter import MarkdownFormatter

__all__ = [
    'BaseFormatter',
    'MetadataBuilder',
    'VarianceExplainer',
    'HTMLFormatter',
    'MarkdownFormatter'
]