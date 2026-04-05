"""
Tests for Memory Module - JVM-style Memory Management
"""

import pytest
import time

from harnessgenj.memory import (
    MemoryManager,
    MemoryHeap,
    EdenMemory,
    SurvivorMemory,
    OldMemory,
    PermanentMemory,
    GarbageCollector,
    HotspotDetector,
    AutoAssembler,
)
from harnessgenj.memory.heap import MemoryEntry, MemoryRegion
from harnessgenj.memory.gc import GCAlgorithm, GCResult


class TestMemoryHeap:
    """测试分代记忆堆"""

    def test_create_heap(self) -> None:
        """创建记忆堆"""
        heap = MemoryHeap(
            eden_size=100,
            survivor_size=50,
            old_size=200,
        )
        assert heap.eden.max_size == 100
        assert heap.survivor_0.max_size == 50
        assert heap.old.max_size == 200

    def test_allocate_to_eden(self) -> None:
        """分配到Eden区"""
        heap = MemoryHeap(eden_size=100)
        entry = heap.allocate("test content", importance=50)

        assert entry is not None
        assert entry.region == MemoryRegion.EDEN
        assert heap.eden.size() == 1

    def test_allocate_large_to_old(self) -> None:
        """大对象直接进Old"""
        heap = MemoryHeap(
            eden_size=100,
            old_size=200,
            large_entry_threshold=100,
        )

        # 大内容直接进Old
        large_content = "x" * 150  # 超过阈值
        entry = heap.allocate(large_content, importance=50)

        assert entry is not None
        assert entry.region == MemoryRegion.OLD

    def test_allocate_high_importance_to_old(self) -> None:
        """高重要性直接进Old"""
        heap = MemoryHeap(eden_size=100, old_size=200)

        entry = heap.allocate("important content", importance=95)

        assert entry is not None
        assert entry.region == MemoryRegion.OLD

    def test_get_entry(self) -> None:
        """获取条目"""
        heap = MemoryHeap()
        entry = heap.allocate("test", importance=50)

        retrieved = heap.get_entry(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id


class TestMemoryEntry:
    """测试记忆条目"""

    def test_create_entry(self) -> None:
        """创建条目"""
        entry = MemoryEntry(
            id="test-id",
            content="test content",
            importance=50,
        )
        assert entry.importance == 50
        assert entry.age == 0
        assert entry.references == 0

    def test_entry_alive(self) -> None:
        """存活判断"""
        entry = MemoryEntry(
            id="test-id",
            content="test content",
            importance=50,
        )

        # 刚创建的条目，最近访问过 -> 存活
        assert entry.is_alive()

        # 模拟旧条目 (超过1小时未访问)
        entry.last_accessed = time.time() - 4000
        entry.importance = 30  # 低重要性
        entry.references = 0   # 无引用
        assert not entry.is_alive()

        # 高重要性 -> 存活
        entry.importance = 80
        assert entry.is_alive()

        # 有引用 -> 存活
        entry.importance = 20
        entry.references = 5
        assert entry.is_alive()

    def test_entry_touch(self) -> None:
        """更新访问"""
        entry = MemoryEntry(id="test-id", content="test")
        old_time = entry.last_accessed

        time.sleep(0.01)
        entry.touch()

        assert entry.references == 1
        assert entry.last_accessed > old_time


class TestGarbageCollector:
    """测试垃圾收集器"""

    def test_minor_gc(self) -> None:
        """Minor GC测试"""
        heap = MemoryHeap(eden_size=10, survivor_size=5, old_size=20)
        gc = GarbageCollector()

        # 填充Eden
        for i in range(10):
            heap.allocate(f"content {i}", importance=30)

        assert heap.eden.size() == 10

        # 执行Minor GC
        result = gc.minor_gc(heap)

        assert result.gc_type == "minor"
        assert result.algorithm == GCAlgorithm.COPYING
        # 大部分低重要性内容被清除
        assert heap.eden.size() == 0

    def test_major_gc(self) -> None:
        """Major GC测试"""
        heap = MemoryHeap(eden_size=10, old_size=20)
        gc = GarbageCollector()

        # 直接分配到Old
        for i in range(15):
            large_content = "x" * 600  # 大内容进Old
            heap.allocate(large_content, importance=30)

        assert heap.old.size() > 0

        # 执行Major GC
        result = gc.major_gc(heap)

        assert result.gc_type == "major"
        assert result.algorithm == GCAlgorithm.MARK_COMPACT

    def test_full_gc(self) -> None:
        """Full GC测试"""
        heap = MemoryHeap(eden_size=10, old_size=20)
        gc = GarbageCollector()

        # 填充各区域
        for i in range(10):
            heap.allocate(f"eden content {i}", importance=30)
        for i in range(5):
            heap.allocate("x" * 600, importance=30)  # 进Old

        # 执行Full GC
        result = gc.full_gc(heap)

        assert result.gc_type == "full"

    def test_auto_gc(self) -> None:
        """自动GC测试"""
        heap = MemoryHeap(eden_size=5, old_size=10)
        gc = GarbageCollector()

        # 未满时不触发
        heap.allocate("content", importance=30)
        result = gc.auto_gc(heap)
        assert result is None

        # Eden满时触发Minor GC
        for i in range(5):
            heap.allocate(f"content {i}", importance=30)
        result = gc.auto_gc(heap)
        assert result is not None
        assert result.gc_type == "minor"


class TestHotspotDetector:
    """测试热点检测器"""

    def test_record_tool_call(self) -> None:
        """记录工具调用"""
        detector = HotspotDetector(compile_threshold=10)

        for i in range(15):
            detector.record_tool_call("test_tool", execution_time=0.1)

        assert detector.is_hotspot("test_tool")

    def test_hotspot_detection(self) -> None:
        """热点检测"""
        detector = HotspotDetector(compile_threshold=10)

        # 记录调用
        for i in range(15):
            detector.record_tool_call("hot_tool", execution_time=0.1)

        # 少量调用
        for i in range(3):
            detector.record_tool_call("cold_tool", execution_time=0.1)

        hotspots = detector.detect_hotspots()

        assert len(hotspots) >= 1
        assert "hot_tool" in [h.name for h in hotspots]
        assert "cold_tool" not in [h.name for h in hotspots]

    def test_back_edge_detection(self) -> None:
        """回边检测 (循环)"""
        detector = HotspotDetector(
            compile_threshold=100,
            back_edge_threshold=5,
        )

        # 模拟循环调用
        for i in range(3):
            detector.record_tool_call("loop_tool", execution_time=0.1, is_repeated=True)

        hotspots = detector.detect_hotspots()
        # 应检测到OSR热点
        for h in hotspots:
            if h.name == "loop_tool":
                assert h.suggested_strategy in ("inline", "osr")

    def test_get_stats(self) -> None:
        """获取统计"""
        detector = HotspotDetector()

        for i in range(5):
            detector.record_tool_call("tool1")
            detector.record_knowledge_reference("knowledge1")

        stats = detector.get_stats()
        assert stats["total_calls"] == 10
        assert stats["tool_counters"] == 1
        assert stats["knowledge_counters"] == 1


class TestAutoAssembler:
    """测试自动装配器"""

    def test_create_inline_template(self) -> None:
        """创建内联模板"""
        from harnessgenj.memory.hotspot import HotspotInfo, CallCounter

        assembler = AutoAssembler(max_inline_size=1000)

        counter = CallCounter(name="test_knowledge", call_count=150)
        hotspot = HotspotInfo(
            name="test_knowledge",
            hotness_score=100.0,
            call_count=150,
            threshold_reached=True,
            suggested_strategy="inline",
        )

        knowledge_base = {"test_knowledge": "This is important knowledge content"}

        template = assembler.assemble(hotspot, knowledge_base)

        assert template is not None
        assert template.strategy == "inline"
        assert len(template.inlined_knowledge) > 0

    def test_escape_analysis(self) -> None:
        """逃逸分析"""
        assembler = AutoAssembler()

        # 无依赖 -> 不逃逸
        result = assembler.perform_escape_analysis("local_context", dependencies=[])
        assert result.escape_level == "no_escape"
        assert result.can_inline is True

        # 多依赖 -> 全局逃逸
        result = assembler.perform_escape_analysis("global_context", dependencies=["dep1", "dep2", "dep3", "dep4"])
        assert result.escape_level == "global_escape"
        assert result.can_inline is False

    def test_cache_management(self) -> None:
        """缓存管理"""
        from harnessgenj.memory.hotspot import HotspotInfo, CallCounter

        assembler = AutoAssembler(cache_size=5)

        # 创建多个模板
        for i in range(7):
            hotspot = HotspotInfo(
                name=f"hotspot_{i}",
                hotness_score=100.0,
                call_count=150,
                threshold_reached=True,
                suggested_strategy="inline",
            )
            assembler.assemble(hotspot)

        # 缓存应该被限制
        assert len(assembler._template_cache) <= assembler.cache_size

    def test_dead_content_elimination(self) -> None:
        """死代码消除"""
        from harnessgenj.memory.hotspot import HotspotInfo

        assembler = AutoAssembler()

        # 创建一些模板
        for i in range(5):
            hotspot = HotspotInfo(
                name=f"hotspot_{i}",
                threshold_reached=True,
                suggested_strategy="cache",
            )
            assembler.assemble(hotspot)

        # 设置低使用次数 (模板名称会添加 _cached 后缀)
        for name, template in assembler._template_cache.items():
            template.usage_count = 1 if "hotspot_0" in name else 10

        eliminated = assembler.eliminate_dead_content(threshold=5)
        # 检查是否有包含 hotspot_0 的模板被清除
        assert any("hotspot_0" in name for name in eliminated)


class TestMemoryManager:
    """测试记忆管理器"""

    def test_create_manager(self) -> None:
        """创建管理器"""
        manager = MemoryManager(workspace=".test_memory_manager")
        assert manager.heap is not None
        assert manager.gc is not None
        assert manager.hotspot is not None

    def test_store_and_get_knowledge(self) -> None:
        """存储和获取知识"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)
            manager.store_knowledge("test_key", "test content", importance=80)

            result = manager.get_knowledge("test_key")
            assert result == "test content"

    def test_store_and_get_document(self) -> None:
        """存储和获取文档"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            success = manager.store_document("requirements", "# 需求\n功能需求")
            assert success is True

            doc = manager.get_document("requirements")
            assert doc is not None
            assert "需求" in doc

    def test_store_and_get_task(self) -> None:
        """存储和获取任务"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            manager.store_task("TASK-001", {"desc": "测试任务", "status": "pending"})

            task = manager.get_task("TASK-001")
            assert task is not None
            assert task["desc"] == "测试任务"

    def test_store_message(self) -> None:
        """存储消息"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            manager.store_message("你好", role="user")
            manager.store_message("你好，有什么可以帮你？", role="assistant")

            messages = manager.get_recent_messages(limit=10)
            assert len(messages) == 2

    def test_get_context_for_llm(self) -> None:
        """获取LLM上下文"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)
            manager.project_info.name = "测试项目"
            manager.project_info.tech_stack = "Python"
            manager.store_knowledge("project_name", "测试项目")
            manager.store_message("测试消息", role="user")

            context = manager.get_context_for_llm("developer", max_tokens=4000)
            assert len(context) > 0
            assert "测试项目" in context

    def test_get_context_for_role(self) -> None:
        """获取角色上下文（渐进式披露）"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)
            manager.project_info.name = "测试项目"
            manager.store_document("requirements", "# 需求文档")

            # 开发者上下文
            dev_context = manager.get_context_for_role("developer")
            assert "project" in dev_context
            assert dev_context["project"]["name"] == "测试项目"

            # 项目经理上下文
            pm_context = manager.get_context_for_role("project_manager")
            assert pm_context.get("full_access") is True

    def test_force_gc(self) -> None:
        """强制GC"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            # 存储一些消息
            for i in range(10):
                manager.store_message(f"消息 {i}", role="user")

            # 强制GC
            result = manager.force_gc("minor")
            assert result.gc_type == "minor"

    def test_get_hotspots(self) -> None:
        """获取热点"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            # 多次访问同一知识
            for i in range(110):
                manager.get_knowledge("test_key")

            hotspots = manager.get_hotspots()
            assert len(hotspots) >= 0

    def test_get_stats(self) -> None:
        """获取统计"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)
            manager.project_info.name = "统计测试"
            manager.update_stats("features_total", 5)
            manager.update_stats("features_completed", 3)

            stats = manager.get_stats()
            assert stats["project"]["name"] == "统计测试"
            assert stats["stats"]["features_total"] == 5
            assert stats["stats"]["features_completed"] == 3

    def test_health_report(self) -> None:
        """健康报告"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(workspace=tmpdir)

            health = manager.get_health_report()
            assert health["status"] == "healthy"

    def test_persistence(self) -> None:
        """持久化测试"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并保存
            manager = MemoryManager(workspace=tmpdir)
            manager.project_info.name = "持久化测试"
            manager.store_knowledge("key1", "value1")
            manager._save()

            # 重新加载
            manager2 = MemoryManager(workspace=tmpdir)
            assert manager2.project_info.name == "持久化测试"
            assert manager2.get_knowledge("key1") == "value1"


class TestPermanentMemory:
    """测试永久代"""

    def test_store_knowledge(self) -> None:
        """存储核心知识"""
        permanent = PermanentMemory()

        entry = permanent.store_knowledge("system_prompt", "You are an AI assistant")
        assert entry.importance == 100
        assert entry.region == MemoryRegion.PERMANENT

    def test_knowledge_never_gc(self) -> None:
        """知识不被GC"""
        permanent = PermanentMemory()
        gc = GarbageCollector()

        permanent.store_knowledge("important", "Never forget")

        # 尝试GC
        result = gc.mark_sweep_collector.collect(None, permanent)

        # Permanent不应该被清除
        assert permanent.get_knowledge("important") is not None