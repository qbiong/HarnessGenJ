"""
Storage Module - Lightweight File-based Storage

轻量化存储系统，无需Redis/数据库配置:
- MarkdownStorage: 使用Markdown文件存储
- JsonStorage: 使用JSON文件存储
- MemoryStorage: 内存存储 (默认)
- WriteBatch: 批量写入优化
- KnowledgeType: 知识条目类型枚举
- 类型模板工厂: create_bug_fix_entry, create_decision_pattern_entry, etc.
"""

from harnessgenj.storage.markdown import (
    MarkdownStorage,
    MarkdownKnowledgeBase,
    KnowledgeEntry,
    KnowledgeType,
    create_bug_fix_entry,
    create_decision_pattern_entry,
    create_architecture_change_entry,
    create_test_case_entry,
    create_security_issue_entry,
)
from harnessgenj.storage.json_store import JsonStorage
from harnessgenj.storage.memory import MemoryStorage
from harnessgenj.storage.manager import StorageManager, StorageType, create_storage, WriteBatch

__all__ = [
    # Markdown Storage
    "MarkdownStorage",
    "MarkdownKnowledgeBase",
    "KnowledgeEntry",
    "KnowledgeType",
    # Type Template Factories
    "create_bug_fix_entry",
    "create_decision_pattern_entry",
    "create_architecture_change_entry",
    "create_test_case_entry",
    "create_security_issue_entry",
    # JSON Storage
    "JsonStorage",
    # Memory Storage
    "MemoryStorage",
    # Storage Manager
    "StorageManager",
    "StorageType",
    "create_storage",
    "WriteBatch",
]