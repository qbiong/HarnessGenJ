"""
Storage Module Tests - 轻量化存储模块测试

测试覆盖:
- MemoryStorage: 内存存储 (默认)
- JsonStorage: JSON文件存储
- MarkdownStorage: Markdown知识库
- StorageManager: 统一存储管理器
"""

import pytest
import tempfile
from pathlib import Path

from harnessgenj.storage.memory import MemoryStorage, MemoryKnowledgeBase
from harnessgenj.storage.json_store import JsonStorage, TaskStateStorage, ContextStorage
from harnessgenj.storage.markdown import MarkdownStorage, MarkdownKnowledgeBase, KnowledgeEntry
from harnessgenj.storage.manager import StorageManager, StorageType, create_storage


class TestMemoryStorage:
    """测试内存存储"""

    def test_basic_operations(self):
        """测试基本操作"""
        storage = MemoryStorage()

        # 保存
        assert storage.save("key1", {"data": "value1"})
        assert storage.save("key2", [1, 2, 3])

        # 加载
        assert storage.load("key1") == {"data": "value1"}
        assert storage.load("key2") == [1, 2, 3]
        assert storage.load("nonexistent") is None

        # 存在检查
        assert storage.exists("key1")
        assert not storage.exists("nonexistent")

        # 列出键
        keys = storage.list_keys()
        assert "key1" in keys
        assert "key2" in keys

        # 删除
        assert storage.delete("key1")
        assert not storage.exists("key1")
        assert not storage.delete("nonexistent")

    def test_statistics(self):
        """测试统计功能"""
        storage = MemoryStorage()

        storage.save("a", 1)
        storage.save("b", 2)
        storage.load("a")
        storage.load("nonexistent")
        storage.delete("b")

        stats = storage.get_stats()
        assert stats["writes"] == 2
        assert stats["reads"] == 2
        assert stats["deletes"] == 1
        assert stats["size"] == 1

    def test_clear(self):
        """测试清空"""
        storage = MemoryStorage()
        storage.save("a", 1)
        storage.save("b", 2)

        count = storage.clear()
        assert count == 2
        assert storage.size() == 0

    def test_deep_copy(self):
        """测试深拷贝 (修改不影响原数据)"""
        storage = MemoryStorage()
        original = {"nested": {"value": 1}}

        storage.save("key", original)
        loaded = storage.load("key")

        loaded["nested"]["value"] = 2
        reloaded = storage.load("key")

        assert reloaded["nested"]["value"] == 1  # 原数据未修改


class TestMemoryKnowledgeBase:
    """测试内存知识库"""

    def test_knowledge_operations(self):
        """测试知识操作"""
        kb = MemoryKnowledgeBase()

        # 保存
        assert kb.save("python", "Python is a programming language", {"category": "tech"})
        assert kb.save("agent", "Agent is an autonomous entity")

        # 加载
        assert kb.load("python") == "Python is a programming language"
        assert kb.load("agent") == "Agent is an autonomous entity"
        assert kb.load("nonexistent") is None

        # 搜索
        results = kb.search("python")
        assert len(results) == 1
        assert results[0]["key"] == "python"

        # 列出
        keys = kb.list_all()
        assert "python" in keys
        assert "agent" in keys

        # 删除
        assert kb.delete("python")
        assert kb.load("python") is None


class TestJsonStorage:
    """测试JSON存储"""

    def test_basic_operations(self):
        """测试基本操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JsonStorage(Path(tmpdir))

            # 保存
            assert storage.save("key1", {"data": "value1"})
            assert storage.save("key2", {"list": [1, 2, 3]})

            # 加载
            result1 = storage.load("key1")
            assert result1["data"] == "value1"
            assert "_meta" in result1

            result2 = storage.load("key2")
            assert result2["list"] == [1, 2, 3]

            assert storage.load("nonexistent") is None

            # 存在检查
            assert storage.exists("key1")
            assert not storage.exists("nonexistent")

            # 列出键
            keys = storage.list_keys()
            assert "key1" in keys
            assert "key2" in keys

            # 删除
            assert storage.delete("key1")
            assert not storage.exists("key1")

    def test_size_calculation(self):
        """测试大小计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JsonStorage(Path(tmpdir))

            storage.save("small", {"a": 1})
            storage.save("large", {"data": "x" * 1000})

            size = storage.get_size()
            assert size > 0

    def test_clear_all(self):
        """测试清空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JsonStorage(Path(tmpdir))

            storage.save("a", {})
            storage.save("b", {})

            count = storage.clear_all()
            assert count == 2
            assert len(storage.list_keys()) == 0


class TestTaskStateStorage:
    """测试任务状态存储"""

    def test_task_operations(self):
        """测试任务操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TaskStateStorage(Path(tmpdir))

            # 保存任务状态 (注意: 传入的是task_id不带task_前缀)
            assert storage.save_task_state("001", {"status": "running", "progress": 50})

            # 加载任务状态
            state = storage.load_task_state("001")
            assert state["status"] == "running"
            assert state["progress"] == 50

            # 列出任务ID (返回不带前缀的ID)
            ids = storage.list_task_ids()
            assert "001" in ids

            # 队列快照
            assert storage.save_queue_snapshot({"queue_size": 10})
            snapshot = storage.load_queue_snapshot()
            assert snapshot["queue_size"] == 10


class TestContextStorage:
    """测试上下文存储"""

    def test_context_operations(self):
        """测试上下文操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ContextStorage(Path(tmpdir))

            # 保存上下文 (注意: 传入的是context_id不带ctx_前缀)
            assert storage.save_context("001", {"user": "test", "session": "abc"})

            # 加载上下文
            ctx = storage.load_context("001")
            assert ctx["user"] == "test"

            # 列出上下文ID (返回不带前缀的ID)
            ids = storage.list_context_ids()
            assert "001" in ids


class TestMarkdownKnowledgeBase:
    """测试Markdown知识库"""

    def test_entry_operations(self):
        """测试条目操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = MarkdownKnowledgeBase(Path(tmpdir))

            # 创建条目
            entry = KnowledgeEntry(
                id="test_knowledge",
                title="Test Knowledge",
                content="This is a test knowledge content.",
                category="test",
                tags=["test", "example"],
                importance=80,
            )

            # 保存
            assert kb.save(entry, category="test")

            # 加载
            loaded = kb.load("test_knowledge", category="test")
            assert loaded is not None
            assert loaded.title == "Test Knowledge"
            assert "test knowledge content" in loaded.content.lower()

            # 列出
            entries = kb.list_all()
            assert len(entries) >= 1

            # 搜索
            results = kb.search("Test")
            assert len(results) >= 1

            # 删除
            assert kb.delete("test_knowledge", category="test")

    def test_index_file(self):
        """测试索引文件生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = MarkdownKnowledgeBase(Path(tmpdir))

            entry = KnowledgeEntry(
                id="kb1",
                title="Knowledge 1",
                content="Content 1",
            )
            kb.save(entry, "general")

            # 检查索引文件存在
            index_file = Path(tmpdir) / "index.md"
            assert index_file.exists()

            # 检查索引内容
            content = index_file.read_text()
            assert "Knowledge 1" in content


class TestMarkdownStorage:
    """测试Markdown存储"""

    def test_task_storage(self):
        """测试任务存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MarkdownStorage(Path(tmpdir))

            # 保存任务
            assert storage.save_task("task_001", "Task content here", {"priority": "high"})

            # 加载任务
            content = storage.load_task("task_001")
            assert content is not None
            assert "Task content here" in content

    def test_history_storage(self):
        """测试历史存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MarkdownStorage(Path(tmpdir))

            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]

            assert storage.save_history("session_001", messages)

    def test_config_storage(self):
        """测试配置存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MarkdownStorage(Path(tmpdir))

            config = {"model": "claude", "max_tokens": 1000}
            assert storage.save_config(config)

            config_file = Path(tmpdir) / "config.md"
            assert config_file.exists()

    def test_stats(self):
        """测试统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MarkdownStorage(Path(tmpdir))

            storage.save_task("t1", "content")
            storage.save_task("t2", "content")

            stats = storage.get_stats()
            assert stats["tasks_count"] == 2


class TestStorageManager:
    """测试存储管理器"""

    def test_memory_mode(self):
        """测试内存模式"""
        manager = StorageManager(storage_type=StorageType.MEMORY)

        # 通用存储
        assert manager.save("key1", {"data": "value"})
        assert manager.load("key1") == {"data": "value"}

        # 知识库
        assert manager.save_knowledge("test", "Test knowledge")
        assert manager.load_knowledge("test") == "Test knowledge"

        # 任务状态
        assert manager.save_task_state("task1", {"status": "running"})
        assert manager.load_task_state("task1")["status"] == "running"

        # 上下文
        assert manager.save_context("ctx1", {"user": "test"})
        assert manager.load_context("ctx1")["user"] == "test"

        # 统计
        stats = manager.get_stats()
        assert stats["storage_type"] == "memory"
        assert not manager.is_persistent()

    def test_file_mode(self):
        """测试文件模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                storage_type=StorageType.FILE,
                base_path=Path(tmpdir),
            )

            # 通用存储
            assert manager.save("key1", {"data": "value"})
            result = manager.load("key1")
            assert result["data"] == "value"

            # 知识库
            assert manager.save_knowledge("test", "Test knowledge", {"category": "tech"})
            loaded = manager.load_knowledge("test")
            assert loaded is not None
            assert loaded.startswith("Test knowledge")

            # 检查持久化
            assert manager.is_persistent()
            assert tmpdir in manager.get_storage_info()

    def test_markdown_mode(self):
        """测试Markdown模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                storage_type=StorageType.MARKDOWN,
                base_path=Path(tmpdir),
            )

            # 通用存储
            assert manager.save("key1", {"data": "value"})

            # 知识库
            assert manager.save_knowledge("doc1", "Documentation content", {"category": "docs"})
            loaded = manager.load_knowledge("doc1")
            assert loaded is not None
            assert loaded.startswith("Documentation content")

            # 搜索
            results = manager.search_knowledge("Documentation")
            assert len(results) >= 1

    def test_convenience_function(self):
        """测试便捷函数"""
        # 内存存储
        storage = create_storage()
        assert not storage.is_persistent()

        # 持久化存储
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = create_storage(persistent=True, base_path=tmpdir)
            assert storage.is_persistent()

    def test_list_operations(self):
        """测试列表操作"""
        manager = StorageManager(storage_type=StorageType.MEMORY)

        manager.save("a", 1)
        manager.save("b", 2)
        manager.save_knowledge("k1", "knowledge 1")
        manager.save_task_state("t1", {})
        manager.save_task_state("t2", {})
        manager.save_context("c1", {})

        assert len(manager.list_keys()) == 2
        assert len(manager.list_knowledge()) == 1
        assert len(manager.list_tasks()) == 2
        assert len(manager.list_contexts()) == 1

    def test_stats(self):
        """测试统计"""
        manager = StorageManager(storage_type=StorageType.MEMORY)

        manager.save("key", {})
        manager.save_knowledge("k", "content")
        manager.save_task_state("t", {})
        manager.save_context("c", {})

        stats = manager.get_stats()
        assert stats["data_count"] == 1
        assert stats["knowledge_count"] == 1
        assert stats["task_count"] == 1
        assert stats["context_count"] == 1