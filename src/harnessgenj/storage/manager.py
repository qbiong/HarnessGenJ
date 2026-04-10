"""
Storage Manager - 统一存储管理

提供简单的API，自动选择存储后端:
- 默认使用内存存储 (无需配置)
- 可选文件存储 (持久化)
- 批量写入优化 (WriteBatch)
"""

import threading
import time
from pathlib import Path
from typing import Any, Callable
from enum import Enum

from harnessgenj.storage.markdown import MarkdownStorage, MarkdownKnowledgeBase
from harnessgenj.storage.json_store import JsonStorage, TaskStateStorage, ContextStorage
from harnessgenj.storage.memory import MemoryStorage, MemoryKnowledgeBase
from harnessgenj.utils.exception_handler import log_exception


class StorageType(Enum):
    """存储类型"""

    MEMORY = "memory"       # 内存存储 (默认，无需配置)
    FILE = "file"           # 文件存储 (持久化)
    MARKDOWN = "markdown"   # Markdown存储 (人类可读)


class WriteBatch:
    """
    批量写入优化器

    功能:
    - 收集多次写入请求
    - 延迟批量执行
    - 减少磁盘 I/O 次数
    - 自动去重（同一文件只保留最后一次写入）

    使用示例:
        batch = WriteBatch()
        batch.queue("file1.md", "content1")
        batch.queue("file2.md", "content2")
        batch.flush()  # 批量写入

        # 或者使用自动刷新
        batch = WriteBatch(auto_flush=True, flush_interval=1.0)
        batch.queue("file.md", "content")  # 1秒后自动刷新
    """

    def __init__(
        self,
        auto_flush: bool = False,
        flush_interval: float = 1.0,
        on_flush: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        """
        初始化批量写入器

        Args:
            auto_flush: 是否自动刷新
            flush_interval: 自动刷新间隔（秒）
            on_flush: 刷新时的回调函数
        """
        self._pending: dict[str, str] = {}
        self._timer: threading.Timer | None = None
        self._auto_flush = auto_flush
        self._flush_interval = flush_interval
        self._on_flush = on_flush
        self._lock = threading.Lock()
        self._stats = {
            "queued": 0,
            "flushed": 0,
            "deduplicated": 0,
        }

    def queue(self, file_path: str, content: str) -> None:
        """
        加入写入队列

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        with self._lock:
            if file_path in self._pending:
                self._stats["deduplicated"] += 1

            self._pending[file_path] = content
            self._stats["queued"] += 1

            # 设置自动刷新定时器
            if self._auto_flush and self._timer is None:
                self._timer = threading.Timer(self._flush_interval, self.flush)
                self._timer.start()

    def flush(self) -> dict[str, bool]:
        """
        执行批量写入

        Returns:
            各文件的写入结果
        """
        with self._lock:
            # 取消定时器
            if self._timer:
                self._timer.cancel()
                self._timer = None

            # 获取待写入内容
            pending = self._pending.copy()
            self._pending.clear()

        results = {}

        # 执行写入
        for file_path, content in pending.items():
            try:
                # 确保目录存在
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                # 写入文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                results[file_path] = True
                self._stats["flushed"] += 1

            except Exception as e:
                results[file_path] = False
                log_exception(e, context=f"flush_file {file_path}", level=30)

        # 调用回调
        if self._on_flush and results:
            self._on_flush(results)

        return results

    def get_pending_count(self) -> int:
        """获取待写入数量"""
        return len(self._pending)

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()

    def clear(self) -> int:
        """
        清空待写入队列（不写入）

        Returns:
            清除的数量
        """
        with self._lock:
            count = len(self._pending)
            self._pending.clear()

            if self._timer:
                self._timer.cancel()
                self._timer = None

            return count


class StorageManager:
    """
    存储管理器 - 统一管理所有存储

    设计原则:
    - 默认内存存储，无需任何配置
    - 可选持久化，一行配置即可
    - 统一API，切换透明
    """

    def __init__(
        self,
        storage_type: StorageType = StorageType.MEMORY,
        base_path: Path | str = ".harnessgenj",
    ) -> None:
        self.storage_type = storage_type
        self.base_path = Path(base_path)

        # 知识分类映射 (记录每个key对应的category)
        self._knowledge_categories: dict[str, str] = {}

        # 根据类型初始化存储
        if storage_type == StorageType.MEMORY:
            self._storage = MemoryStorage()
            self._knowledge_base = MemoryKnowledgeBase()
            self._task_storage = MemoryStorage()
            self._context_storage = MemoryStorage()
        else:
            # 文件存储
            self._storage = JsonStorage(self.base_path / "data")
            self._knowledge_base = MarkdownKnowledgeBase(self.base_path / "knowledge")
            self._task_storage = TaskStateStorage(self.base_path / "data" / "tasks")
            self._context_storage = ContextStorage(self.base_path / "data" / "contexts")

            # 如果是markdown存储，创建额外结构
            if storage_type == StorageType.MARKDOWN:
                self._markdown = MarkdownStorage(self.base_path)

    # ==================== 通用存储 ====================

    def save(self, key: str, data: Any) -> bool:
        """保存数据"""
        return self._storage.save(key, data)

    def load(self, key: str) -> Any | None:
        """加载数据"""
        return self._storage.load(key)

    def delete(self, key: str) -> bool:
        """删除数据"""
        return self._storage.delete(key)

    def exists(self, key: str) -> bool:
        """检查数据是否存在"""
        return self._storage.exists(key)

    def list_keys(self) -> list[str]:
        """列出所有键"""
        return self._storage.list_keys()

    # ==================== 知识库 ====================

    def save_knowledge(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
        """保存知识"""
        category = metadata.get("category", "general") if metadata else "general"
        # 记录分类映射
        self._knowledge_categories[key] = category

        if isinstance(self._knowledge_base, MemoryKnowledgeBase):
            return self._knowledge_base.save(key, content, metadata)
        else:
            from harnessgenj.storage.markdown import KnowledgeEntry
            entry = KnowledgeEntry(
                id=key,
                title=key,
                content=content,
                metadata=metadata or {},
            )
            return self._knowledge_base.save(entry, category)

    def load_knowledge(self, key: str) -> str | None:
        """加载知识"""
        if isinstance(self._knowledge_base, MemoryKnowledgeBase):
            return self._knowledge_base.load(key)
        else:
            # 使用映射获取正确的category
            category = self._knowledge_categories.get(key, "general")
            entry = self._knowledge_base.load(key, category=category)
            return entry.content if entry else None

    def search_knowledge(self, query: str) -> list[dict[str, Any]]:
        """搜索知识"""
        return self._knowledge_base.search(query)

    def list_knowledge(self) -> list[str]:
        """列出所有知识键"""
        if isinstance(self._knowledge_base, MemoryKnowledgeBase):
            return self._knowledge_base.list_all()
        return [e.id for e in self._knowledge_base.list_all()]

    # ==================== 任务状态 ====================

    def save_task_state(self, task_id: str, state: dict[str, Any]) -> bool:
        """保存任务状态"""
        return self._task_storage.save(f"task_{task_id}", state)

    def load_task_state(self, task_id: str) -> dict[str, Any] | None:
        """加载任务状态"""
        return self._task_storage.load(f"task_{task_id}")

    def list_tasks(self) -> list[str]:
        """列出所有任务ID"""
        keys = self._task_storage.list_keys()
        return [k.replace("task_", "") for k in keys if k.startswith("task_")]

    # ==================== 上下文 ====================

    def save_context(self, context_id: str, context: dict[str, Any]) -> bool:
        """保存上下文"""
        return self._context_storage.save(f"ctx_{context_id}", context)

    def load_context(self, context_id: str) -> dict[str, Any] | None:
        """加载上下文"""
        return self._context_storage.load(f"ctx_{context_id}")

    def list_contexts(self) -> list[str]:
        """列出所有上下文ID"""
        keys = self._context_storage.list_keys()
        return [k.replace("ctx_", "") for k in keys if k.startswith("ctx_")]

    # ==================== 统计与清理 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取存储统计"""
        return {
            "storage_type": self.storage_type.value,
            "data_count": len(self.list_keys()),
            "knowledge_count": len(self.list_knowledge()),
            "task_count": len(self.list_tasks()),
            "context_count": len(self.list_contexts()),
            "base_path": str(self.base_path) if self.storage_type != StorageType.MEMORY else "memory",
        }

    def clear_all(self) -> dict[str, int]:
        """清空所有存储"""
        return {
            "data": len(self.list_keys()),
            "knowledge": len(self.list_knowledge()),
            "tasks": len(self.list_tasks()),
            "contexts": len(self.list_contexts()),
        }

    # ==================== 便捷方法 ====================

    def is_persistent(self) -> bool:
        """是否持久化存储"""
        return self.storage_type != StorageType.MEMORY

    def get_storage_info(self) -> str:
        """获取存储信息"""
        if self.storage_type == StorageType.MEMORY:
            return "Memory Storage (no persistence)"
        else:
            return f"File Storage at {self.base_path}"


def create_storage(
    persistent: bool = False,
    base_path: str = ".harnessgenj",
) -> StorageManager:
    """
    创建存储管理器 - 便捷函数

    Args:
        persistent: 是否持久化 (默认False，使用内存)
        base_path: 存储路径

    Returns:
        StorageManager实例

    Examples:
        # 内存存储 (默认)
        storage = create_storage()

        # 持久化存储
        storage = create_storage(persistent=True)
    """
    storage_type = StorageType.FILE if persistent else StorageType.MEMORY
    return StorageManager(storage_type=storage_type, base_path=base_path)