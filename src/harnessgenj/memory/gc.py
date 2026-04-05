"""
Garbage Collector - JVM-style Memory Collection Algorithms

严格实现 JVM GC 算法:
- Mark-Sweep: 标记-清除
- Copying: 复制算法 (Eden→Survivor)
- Mark-Compact: 标记-压缩 (摘要)
- G1-style: 优先回收低价值区
"""

from abc import ABC, abstractmethod
from typing import Any
from enum import Enum
from pydantic import BaseModel, Field

from harnessgenj.memory.heap import (
    MemoryHeap,
    EdenMemory,
    SurvivorMemory,
    OldMemory,
    MemoryEntry,
    MemoryRegion,
)


class GCAlgorithm(Enum):
    """GC算法类型"""

    MARK_SWEEP = "mark_sweep"       # 标记-清除
    COPYING = "copying"             # 复制算法
    MARK_COMPACT = "mark_compact"   # 标记-压缩
    G1 = "g1"                       # G1优先回收


class GCResult(BaseModel):
    """GC执行结果"""

    algorithm: GCAlgorithm = Field(..., description="使用的算法")
    gc_type: str = Field(..., description="GC类型: minor/major/full")
    removed_count: int = Field(default=0, description="清除数量")
    promoted_count: int = Field(default=0, description="晋升数量")
    freed_space: int = Field(default=0, description="释放空间")
    execution_time: float = Field(default=0.0, description="执行时间")
    survived_count: int = Field(default=0, description="存活数量")
    details: dict[str, Any] = Field(default_factory=dict, description="详细信息")


class BaseCollector(ABC):
    """
    收集器基类 - 类似 JVM GC 抽象

    所有GC算法继承此基类
    """

    @abstractmethod
    def collect(self, heap: MemoryHeap, *regions: Any) -> GCResult:
        """
        执行收集

        Args:
            heap: 记忆堆
            regions: 要收集的区域

        Returns:
            GCResult: 收集结果
        """
        pass

    @abstractmethod
    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """
        标记阶段 - 判断存活/无用

        Args:
            entries: 条目列表

        Returns:
            (存活条目, 无用条目)
        """
        pass

    @abstractmethod
    def sweep(self, entries: list[MemoryEntry], region: Any) -> int:
        """
        清除阶段 - 删除无用条目

        Args:
            entries: 无用条目
            region: 所属区域

        Returns:
            清除数量
        """
        pass


class MarkSweepCollector(BaseCollector):
    """
    标记-清除收集器

    类似 JVM Mark-Sweep GC:
    1. Mark: 标记所有存活/无用对象
    2. Sweep: 清除无用对象

    优点: 简单直接
    缺点: 产生内存碎片
    """

    def __init__(self, reference_threshold: int = 0, importance_threshold: int = 30) -> None:
        self.reference_threshold = reference_threshold
        self.importance_threshold = importance_threshold

    def collect(self, heap: MemoryHeap, *regions: Any) -> GCResult:
        """执行标记-清除"""
        import time
        start_time = time.time()

        total_removed = 0
        total_survived = 0

        for region in regions:
            entries = region.list_entries()
            survived, useless = self.mark(entries)
            removed = self.sweep(useless, region)
            total_removed += removed
            total_survived += len(survived)

        execution_time = time.time() - start_time

        return GCResult(
            algorithm=GCAlgorithm.MARK_SWEEP,
            gc_type=self._determine_gc_type(regions),
            removed_count=total_removed,
            freed_space=total_removed,
            execution_time=execution_time,
            survived_count=total_survived,
        )

    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """
        标记阶段 - 基于:
        1. 引用计数 > threshold
        2. 重要性 > threshold
        3. 最近访问时间
        """
        survived = []
        useless = []

        for entry in entries:
            if entry.is_alive(self.reference_threshold):
                survived.append(entry)
            else:
                useless.append(entry)

        return survived, useless

    def sweep(self, entries: list[MemoryEntry], region: Any) -> int:
        """清除阶段"""
        removed = 0
        for entry in entries:
            if region.remove(entry.id):
                removed += 1
        return removed

    def _determine_gc_type(self, regions: tuple) -> str:
        """判断GC类型"""
        region_types = [r.region_type if hasattr(r, "region_type") else None for r in regions]
        if MemoryRegion.OLD in region_types:
            return "major"
        if MemoryRegion.EDEN in region_types:
            return "minor"
        return "unknown"


class CopyingCollector(BaseCollector):
    """
    复制收集器

    类似 JVM Copying GC (用于新生代):
    1. 将存活对象从 Eden/Survivor 复制到另一个 Survivor
    2. 清空原区域

    优点: 无碎片，效率高
    缺点: 需要双倍空间
    """

    def __init__(self, promotion_threshold: int = 15) -> None:
        self.promotion_threshold = promotion_threshold

    def collect(
        self,
        heap: MemoryHeap,
        source: EdenMemory | SurvivorMemory,
        target: SurvivorMemory,
        old: OldMemory,
    ) -> GCResult:
        """
        执行复制收集

        Args:
            heap: 记忆堆
            source: 源区域 (Eden或活跃Survivor)
            target: 目标区域 (非活跃Survivor)
            old: 老年代 (晋升目标)
        """
        import time
        start_time = time.time()

        entries = source.list_entries()
        survived, useless = self.mark(entries)

        # 清除无用条目
        removed = self.sweep(useless, source)

        # 复制存活条目到目标区域
        promoted = 0
        copied = 0

        for entry in survived:
            entry.age += 1  # 增加年龄

            # 判断是否晋升到Old
            if entry.age >= self.promotion_threshold or entry.importance >= 80:
                if old.promote(entry):
                    promoted += 1
            else:
                # 复制到目标Survivor
                if target.put(entry):
                    copied += 1

        # 清空源区域
        source.clear()

        execution_time = time.time() - start_time

        return GCResult(
            algorithm=GCAlgorithm.COPYING,
            gc_type="minor",
            removed_count=removed,
            promoted_count=promoted,
            freed_space=removed + copied,
            execution_time=execution_time,
            survived_count=len(survived),
            details={"copied_to_survivor": copied},
        )

    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """标记阶段"""
        survived = []
        useless = []
        for entry in entries:
            if entry.is_alive():
                survived.append(entry)
            else:
                useless.append(entry)
        return survived, useless

    def sweep(self, entries: list[MemoryEntry], region: Any) -> int:
        """清除阶段"""
        return len(entries)  # 复制算法中，源区域会被整体清空


class MarkCompactCollector(BaseCollector):
    """
    标记-压缩收集器

    类似 JVM Mark-Compact GC (用于老年代):
    1. Mark: 标记存活对象
    2. Compact: 压缩存活对象，清理碎片
    3. 可将历史压缩为摘要

    优点: 无碎片，空间利用率高
    缺点: 需要移动对象，较慢
    """

    def __init__(self, compact_threshold: float = 0.8) -> None:
        self.compact_threshold = compact_threshold  # 触发压缩的空间使用率阈值

    def collect(self, heap: MemoryHeap, old: OldMemory) -> GCResult:
        """
        执行标记-压缩

        Args:
            heap: 记忆堆
            old: 老年代
        """
        import time
        start_time = time.time()

        # 先执行标记-清除
        entries = old.list_entries()
        survived, useless = self.mark(entries)
        removed = self.sweep(useless, old)

        # 判断是否需要压缩
        compact_result = {"performed": False}
        if old.size() >= old.max_size * self.compact_threshold:
            compact_result = old.compact()
            compact_result["performed"] = True

        execution_time = time.time() - start_time

        return GCResult(
            algorithm=GCAlgorithm.MARK_COMPACT,
            gc_type="major",
            removed_count=removed + compact_result.get("removed", 0),
            freed_space=removed + compact_result.get("removed", 0),
            execution_time=execution_time,
            survived_count=len(survived),
            details={"compact": compact_result},
        )

    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """
        标记阶段 - 老年代使用更严格的存活判断

        基于:
        1. 引用计数 > 1
        2. 重要性 > 50
        3. 年龄 > 5
        """
        survived = []
        useless = []

        for entry in entries:
            # 老年代存活判断更严格
            if entry.references > 1 or entry.importance >= 50 or entry.age > 5:
                survived.append(entry)
            else:
                useless.append(entry)

        return survived, useless

    def sweep(self, entries: list[MemoryEntry], region: OldMemory) -> int:
        """清除阶段"""
        removed = 0
        for entry in entries:
            if region.remove(entry.id):
                removed += 1
        return removed


class G1Collector(BaseCollector):
    """
    G1收集器风格 - 优先回收低价值区域

    类似 JVM G1 GC:
    1. 将堆划分为多个Region
    2. 优先回收价值最低的Region
    3. 可预测的停顿时间

    在Agent记忆中:
    - 优先回收低重要性、低引用的记忆区
    - 预设回收目标时间
    """

    def __init__(self, target_pause_time: float = 0.5) -> None:
        self.target_pause_time = target_pause_time  # 目标回收时间

    def collect(self, heap: MemoryHeap, *regions: Any) -> GCResult:
        """
        执行G1风格收集

        优先回收低价值区域
        """
        import time
        start_time = time.time()

        # 计算各区域价值
        region_values = []
        for region in regions:
            value = self._calculate_region_value(region)
            region_values.append((region, value))

        # 按价值排序，优先回收低价值区
        region_values.sort(key=lambda x: x[1], reverse=True)

        total_removed = 0
        collected_regions = []

        for region, _ in region_values[:3]:  # 最多回收3个低价值区
            if time.time() - start_time > self.target_pause_time:
                break  # 达到目标时间，停止

            entries = region.list_entries()
            survived, useless = self.mark(entries)
            removed = self.sweep(useless, region)
            total_removed += removed
            collected_regions.append(region.region_type.value if hasattr(region, "region_type") else "unknown")

        execution_time = time.time() - start_time

        return GCResult(
            algorithm=GCAlgorithm.G1,
            gc_type="g1",
            removed_count=total_removed,
            freed_space=total_removed,
            execution_time=execution_time,
            details={"collected_regions": collected_regions},
        )

    def _calculate_region_value(self, region: Any) -> float:
        """
        计算区域价值

        高价值 = 高重要性 + 高引用 + 近期访问
        低价值 = 优先回收目标
        """
        entries = region.list_entries()
        if not entries:
            return 0

        total_importance = sum(e.importance for e in entries)
        total_references = sum(e.references for e in entries)
        avg_importance = total_importance / len(entries)
        avg_references = total_references / len(entries)

        # 价值 = 平均重要性 + 平均引用 * 10
        return avg_importance + avg_references * 10

    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """标记阶段"""
        survived = []
        useless = []
        for entry in entries:
            # G1风格：保留高价值，清除低价值
            if entry.importance >= 60 or entry.references >= 2:
                survived.append(entry)
            else:
                useless.append(entry)
        return survived, useless

    def sweep(self, entries: list[MemoryEntry], region: Any) -> int:
        """清除阶段"""
        removed = 0
        for entry in entries:
            if region.remove(entry.id):
                removed += 1
        return removed


class QualityAwareCollector(BaseCollector):
    """
    质量感知的垃圾收集器

    在存活判定中考虑质量分数:
    - 高质量内容优先保留
    - 低质量内容优先回收
    - 与对抗审查系统深度集成

    Args:
        quality_threshold: 质量阈值，低于此值且低引用则回收
        reference_threshold: 引用计数阈值
    """

    def __init__(
        self,
        quality_threshold: float = 40.0,
        reference_threshold: int = 0,
        high_quality_threshold: float = 70.0,
    ) -> None:
        self.quality_threshold = quality_threshold
        self.reference_threshold = reference_threshold
        self.high_quality_threshold = high_quality_threshold

    def collect(self, heap: MemoryHeap, *regions: Any) -> GCResult:
        """执行质量感知的标记-清除"""
        import time
        start_time = time.time()

        total_removed = 0
        total_survived = 0
        quality_stats = {"high_kept": 0, "low_removed": 0}

        for region in regions:
            entries = region.list_entries()
            survived, useless = self.mark(entries)
            removed = self.sweep(useless, region)
            total_removed += removed
            total_survived += len(survived)

            # 统计质量相关信息
            for entry in survived:
                if entry.quality_score >= self.high_quality_threshold:
                    quality_stats["high_kept"] += 1
            for entry in useless:
                if entry.quality_score < self.quality_threshold:
                    quality_stats["low_removed"] += 1

        execution_time = time.time() - start_time

        return GCResult(
            algorithm=GCAlgorithm.MARK_SWEEP,
            gc_type=self._determine_gc_type(regions),
            removed_count=total_removed,
            freed_space=total_removed,
            execution_time=execution_time,
            survived_count=total_survived,
            details={"quality_stats": quality_stats},
        )

    def mark(self, entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """
        质量感知的标记阶段

        存活判定优先级:
        1. 高质量 (quality_score >= 70) → 必定存活
        2. 低质量 + 低引用 (quality_score < 30, references < 1) → 必定回收
        3. 其他情况 → 使用原有判定逻辑
        """
        survived = []
        useless = []

        for entry in entries:
            if self._should_survive(entry):
                survived.append(entry)
            else:
                useless.append(entry)

        return survived, useless

    def _should_survive(self, entry: MemoryEntry) -> bool:
        """
        基于质量分数决定存活

        Args:
            entry: 记忆条目

        Returns:
            是否应该存活
        """
        # 高质量内容必定存活
        if entry.quality_score >= self.high_quality_threshold:
            return True

        # 低质量内容：只有高引用或高重要性才能存活
        if entry.quality_score < 30:
            # 低质量但有高引用（>=3）或高重要性（>=80）则保留
            if entry.references >= 3 or entry.importance >= 80:
                return True
            # 否则回收
            return False

        # 中等质量情况，使用综合判定
        # 质量 30-70 之间，根据引用、重要性、访问时间综合判断
        return entry.is_alive(self.reference_threshold)

    def sweep(self, entries: list[MemoryEntry], region: Any) -> int:
        """清除阶段"""
        removed = 0
        for entry in entries:
            if region.remove(entry.id):
                removed += 1
        return removed

    def _determine_gc_type(self, regions: tuple) -> str:
        """判断GC类型"""
        region_types = [r.region_type if hasattr(r, "region_type") else None for r in regions]
        if MemoryRegion.OLD in region_types:
            return "major"
        if MemoryRegion.EDEN in region_types:
            return "minor"
        return "unknown"


class GarbageCollector:
    """
    垃圾收集器 - JVM-style 记忆回收总控制器

    整合所有GC算法:
    - Minor GC: Eden + Survivor (使用Copying算法)
    - Major GC: Old (使用Mark-Compact算法)
    - Full GC: 全部区域 (使用G1或Mark-Sweep)
    - Quality GC: 质量感知收集 (新增)
    """

    def __init__(
        self,
        promotion_threshold: int = 15,
        reference_threshold: int = 0,
        compact_threshold: float = 0.8,
        target_pause_time: float = 0.5,
        quality_threshold: float = 40.0,
    ) -> None:
        # 各算法收集器
        self.copying_collector = CopyingCollector(promotion_threshold)
        self.mark_compact_collector = MarkCompactCollector(compact_threshold)
        self.mark_sweep_collector = MarkSweepCollector(reference_threshold)
        self.g1_collector = G1Collector(target_pause_time)
        self.quality_aware_collector = QualityAwareCollector(quality_threshold, reference_threshold)

        # 配置
        self.promotion_threshold = promotion_threshold

    def minor_gc(self, heap: MemoryHeap) -> GCResult:
        """
        Minor GC - 新生代收集

        类似 JVM Minor GC:
        1. 收集 Eden + Survivor
        2. 使用复制算法
        3. 存活对象复制到另一个 Survivor
        4. 达到年龄阈值晋升到 Old
        """
        result = self.copying_collector.collect(
            heap,
            source=heap.eden,
            target=heap.get_active_survivor(),
            old=heap.old,
        )

        # 交换Survivor
        heap.swap_survivor()

        # 更新统计
        heap.update_gc_stats("minor", result.removed_count, result.promoted_count)

        return result

    def major_gc(self, heap: MemoryHeap) -> GCResult:
        """
        Major GC - 老年代收集

        类似 JVM Major GC:
        1. 收集 Old 区
        2. 使用标记-压缩算法
        3. 可能触发压缩（摘要）
        """
        result = self.mark_compact_collector.collect(heap, heap.old)

        # 更新统计
        heap.update_gc_stats("major", result.removed_count, result.promoted_count)

        return result

    def full_gc(self, heap: MemoryHeap) -> GCResult:
        """
        Full GC - 全堆收集

        类似 JVM Full GC:
        1. 收集所有区域
        2. 可使用 G1 或 Mark-Sweep 算法
        3. 完整清理和压缩
        """
        import time
        start_time = time.time()

        # 依次收集各区域
        minor_result = self.minor_gc(heap)
        major_result = self.major_gc(heap)

        # 处理Permanent区 (可选，通常不回收)
        permanent_result = self.mark_sweep_collector.collect(heap, heap.permanent)

        execution_time = time.time() - start_time

        result = GCResult(
            algorithm=GCAlgorithm.G1,
            gc_type="full",
            removed_count=minor_result.removed_count + major_result.removed_count + permanent_result.removed_count,
            promoted_count=minor_result.promoted_count + major_result.promoted_count,
            freed_space=minor_result.freed_space + major_result.freed_space + permanent_result.freed_space,
            execution_time=execution_time,
            details={
                "minor": minor_result.model_dump(),
                "major": major_result.model_dump(),
                "permanent": permanent_result.model_dump(),
            },
        )

        heap.update_gc_stats("full", result.removed_count, result.promoted_count)

        return result

    def quality_gc(self, heap: MemoryHeap, *regions: Any) -> GCResult:
        """
        Quality GC - 质量感知收集

        使用质量分数进行存活判定:
        1. 高质量内容优先保留
        2. 低质量内容优先回收
        3. 与对抗审查系统深度集成

        Args:
            heap: 记忆堆
            regions: 要收集的区域（默认为 Eden + Old）
        """
        import time
        start_time = time.time()

        # 默认收集 Eden 和 Old
        if not regions:
            regions = (heap.eden, heap.old)

        result = self.quality_aware_collector.collect(heap, *regions)

        # 更新统计
        heap.update_gc_stats("quality", result.removed_count, 0)

        return result

    def auto_gc(self, heap: MemoryHeap) -> GCResult | None:
        """
        自动GC - 根据各区域状态自动触发合适的GC

        类似 JVM 的自动GC触发:
        - Eden满 → Minor GC
        - Old满 → Major GC (使用质量感知)
        - 整体满 → Full GC
        """
        # 检查Eden
        if heap.eden.is_full():
            return self.minor_gc(heap)

        # 检查Old - 使用质量感知收集
        if heap.old.is_full():
            return self.quality_gc(heap, heap.old)

        # 检查整体内存压力
        total_used = heap.eden.size() + heap.old.size()
        total_max = heap.eden.max_size + heap.old.max_size
        if total_used >= total_max * 0.9:
            return self.full_gc(heap)

        return None  # 无需GC

    def get_collector_stats(self) -> dict[str, Any]:
        """获取收集器统计"""
        return {
            "promotion_threshold": self.promotion_threshold,
            "algorithms": {
                "minor": "Copying",
                "major": "Mark-Compact",
                "full": "G1 + Mark-Sweep",
                "quality": "QualityAware",
            },
        }