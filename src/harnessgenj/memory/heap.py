"""
Memory Heap - JVM-style Generational Memory Management

严格实现 JVM Heap 的分代结构:
- EdenMemory (新生代Eden区): 最新消息
- SurvivorMemory ( Survivor区): 存活消息缓冲
- OldMemory (老年代): 长期重要历史
- PermanentMemory (永久代): 核心知识/Agent定义
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class MemoryRegion(Enum):
    """记忆区域类型"""

    EDEN = "eden"               # 新生代Eden
    SURVIVOR_0 = "survivor_0"   # Survivor区S0
    SURVIVOR_1 = "survivor_1"   # Survivor区S1
    OLD = "old"                 # 老年代
    PERMANENT = "permanent"     # 永久代


class MemoryEntry(BaseModel):
    """
    记忆条目 - 类似 JVM 中的对象

    Attributes:
        id: 唯一标识
        content: 内容
        importance: 重要性评分 (0-100)，影响存活和晋升
        age: 年龄 (经历GC次数)，用于晋升判断
        region: 当前所在区域
        references: 被引用次数，用于可达性分析
        created_at: 创建时间
        last_accessed: 最后访问时间
        metadata: 元数据
        quality_score: 质量分数 (0-100)，来自对抗审查
        review_count: 审查次数
        last_review_result: 最后审查结果
        generator_id: 生成者角色ID
        discriminator_id: 审查者角色ID
    """

    id: str = Field(..., description="唯一标识")
    content: str = Field(..., description="内容")
    importance: int = Field(default=50, ge=0, le=100, description="重要性评分")
    age: int = Field(default=0, ge=0, description="年龄(经历GC次数)")
    region: MemoryRegion = Field(default=MemoryRegion.EDEN, description="当前区域")
    references: int = Field(default=0, ge=0, description="被引用次数")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    last_accessed: float = Field(default_factory=time.time, description="最后访问时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    # 质量相关字段
    quality_score: float = Field(default=50.0, ge=0, le=100, description="质量分数(来自对抗审查)")
    review_count: int = Field(default=0, ge=0, description="审查次数")
    last_review_result: str | None = Field(default=None, description="最后审查结果: passed/failed")
    generator_id: str | None = Field(default=None, description="生成者角色ID")
    discriminator_id: str | None = Field(default=None, description="审查者角色ID")

    def touch(self) -> None:
        """更新访问时间和引用计数"""
        self.last_accessed = time.time()
        self.references += 1

    def update_quality(
        self,
        quality_score: float | None = None,
        review_result: str | None = None,
        generator_id: str | None = None,
        discriminator_id: str | None = None,
    ) -> None:
        """
        更新质量信息

        Args:
            quality_score: 质量分数 (0-100)
            review_result: 审查结果 ("passed" | "failed")
            generator_id: 生成者角色ID
            discriminator_id: 审查者角色ID
        """
        if quality_score is not None:
            self.quality_score = max(0, min(100, quality_score))
        if review_result is not None:
            self.last_review_result = review_result
            self.review_count += 1
        if generator_id is not None:
            self.generator_id = generator_id
        if discriminator_id is not None:
            self.discriminator_id = discriminator_id
        self.last_accessed = time.time()

    def is_alive(self, threshold: int = 0) -> bool:
        """
        判断是否存活 (类似 JVM 的存活判定)

        基于:
        1. 引用计数 > threshold
        2. 重要性评分 > 30
        3. 最近访问时间
        4. 质量分数 (新增)
        """
        # 高质量内容优先存活
        if self.quality_score >= 70:
            return True
        # 低质量：只有高引用或高重要性才能存活
        if self.quality_score < 30:
            if self.references >= 3 or self.importance >= 80:
                return True
            return False
        if self.references > threshold:
            return True
        if self.importance >= 70:
            return True
        # 最近1小时内访问过
        if time.time() - self.last_accessed < 3600:
            return True
        return False


class BaseMemoryRegion(ABC):
    """
    记忆区域基类 - 类似 JVM 的内存区域抽象

    所有记忆区域都继承此基类
    """

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max_size
        self._entries: dict[str, MemoryEntry] = {}
        self._current_size: int = 0

    @property
    @abstractmethod
    def region_type(self) -> MemoryRegion:
        """区域类型"""
        pass

    def put(self, entry: MemoryEntry) -> bool:
        """
        放入条目

        Returns:
            是否成功放入 (空间不足时返回False)
        """
        if self._current_size >= self.max_size:
            return False
        entry.region = self.region_type
        self._entries[entry.id] = entry
        self._current_size += 1
        return True

    def get(self, id: str) -> MemoryEntry | None:
        """获取条目"""
        entry = self._entries.get(id)
        if entry:
            entry.touch()
        return entry

    def remove(self, id: str) -> MemoryEntry | None:
        """移除条目"""
        entry = self._entries.pop(id, None)
        if entry:
            self._current_size -= 1
        return entry

    def list_entries(self) -> list[MemoryEntry]:
        """列出所有条目"""
        return list(self._entries.values())

    def size(self) -> int:
        """当前大小"""
        return self._current_size

    def is_full(self) -> bool:
        """是否已满"""
        return self._current_size >= self.max_size

    def clear(self) -> int:
        """清空区域，返回清除数量"""
        count = self._current_size
        self._entries.clear()
        self._current_size = 0
        return count


class EdenMemory(BaseMemoryRegion):
    """
    Eden区 - 新生代主要区域

    类似 JVM Eden:
    - 新消息首先分配到Eden
    - Minor GC 时清理
    - 存活对象复制到Survivor
    """

    def __init__(self, max_size: int = 1000) -> None:
        super().__init__(max_size)

    @property
    def region_type(self) -> MemoryRegion:
        return MemoryRegion.EDEN

    def allocate(self, content: str, importance: int = 50, metadata: dict[str, Any] | None = None) -> MemoryEntry | None:
        """
        分配新条目 - 类似 JVM 对象分配

        Args:
            content: 内容
            importance: 重要性评分
            metadata: 元数据

        Returns:
            分配的条目 (空间不足时返回None)
        """
        import uuid
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            importance=importance,
            metadata=metadata or {},
        )
        if self.put(entry):
            return entry
        return None


class SurvivorMemory(BaseMemoryRegion):
    """
    Survivor区 - 新生代存活缓冲区

    类似 JVM Survivor:
    - 存放Eden GC后的存活对象
    - S0和S1之间复制交换
    - 年龄增长，达到阈值晋升到Old
    """

    def __init__(self, max_size: int = 500) -> None:
        super().__init__(max_size)

    @property
    def region_type(self) -> MemoryRegion:
        return MemoryRegion.SURVIVOR_0  # 实例化时指定

    def increment_age(self) -> list[MemoryEntry]:
        """
        增加所有条目的年龄

        Returns:
            达到晋升阈值的条目列表
        """
        promotion_candidates = []
        for entry in self._entries.values():
            entry.age += 1
        return promotion_candidates


class OldMemory(BaseMemoryRegion):
    """
    老年代 - 长期存活记忆

    类似 JVM Old Generation:
    - 存放长期存活的对象
    - Major GC / Full GC 时清理
    - 可以压缩为摘要
    """

    def __init__(self, max_size: int = 5000) -> None:
        super().__init__(max_size)

    @property
    def region_type(self) -> MemoryRegion:
        return MemoryRegion.OLD

    def promote(self, entry: MemoryEntry) -> bool:
        """
        晋升条目到老年代

        Args:
            entry: 要晋升的条目

        Returns:
            是否成功晋升
        """
        entry.region = MemoryRegion.OLD
        return self.put(entry)

    def compact(self) -> dict[str, Any]:
        """
        压缩 - 类似 JVM 的 Mark-Compact

        将历史内容压缩为摘要，释放空间

        Returns:
            压缩统计信息
        """
        if self.size() < self.max_size * 0.8:
            return {"status": "skipped", "reason": "not_full_enough"}

        # 按重要性分组压缩
        high_importance = [e for e in self.list_entries() if e.importance >= 80]
        medium_importance = [e for e in self.list_entries() if 50 <= e.importance < 80]
        low_importance = [e for e in self.list_entries() if e.importance < 50]

        # 清除低重要性
        removed_count = 0
        for entry in low_importance:
            self.remove(entry.id)
            removed_count += 1

        # 中等重要性压缩为摘要
        if medium_importance:
            summary = self._create_summary(medium_importance)
            for entry in medium_importance:
                self.remove(entry.id)
                removed_count += 1
            # 存储摘要
            import uuid
            summary_entry = MemoryEntry(
                id=str(uuid.uuid4()),
                content=summary,
                importance=60,
                region=MemoryRegion.OLD,
                metadata={"type": "summary", "original_count": len(medium_importance)},
            )
            self.put(summary_entry)

        return {
            "status": "completed",
            "removed": removed_count,
            "high_importance_kept": len(high_importance),
            "summary_created": len(medium_importance) > 0,
        }

    def _create_summary(self, entries: list[MemoryEntry]) -> str:
        """创建摘要"""
        # 简化实现: 拼接关键内容
        contents = [e.content[:100] for e in entries[:5]]
        return f"摘要 ({len(entries)}条历史): " + " | ".join(contents)


class PermanentMemory(BaseMemoryRegion):
    """
    永久代 - 核心知识存储

    类似 JVM Permanent Generation / Metaspace:
    - 存放类信息、常量池
    - 对应Agent: Agent定义、核心知识、系统提示
    - 永不回收 (除非手动清除)
    """

    def __init__(self, max_size: int = 10000) -> None:
        super().__init__(max_size)

    @property
    def region_type(self) -> MemoryRegion:
        return MemoryRegion.PERMANENT

    def store_knowledge(self, key: str, content: str, importance: int = 100) -> MemoryEntry:
        """
        存储核心知识

        Args:
            key: 知识键 (用作ID)
            content: 知识内容
            importance: 重要性 (默认最高)

        Returns:
            存储的条目
        """
        entry = MemoryEntry(
            id=key,
            content=content,
            importance=importance,
            region=MemoryRegion.PERMANENT,
        )
        self.put(entry)
        return entry

    def get_knowledge(self, key: str) -> MemoryEntry | None:
        """获取核心知识"""
        return self.get(key)


class MemoryHeap:
    """
    记忆堆 - JVM-style 分代记忆管理

    严格实现 JVM Heap 的分代结构:
    - Eden: 新消息
    - Survivor (S0, S1): 存活缓冲
    - Old: 老年代
    - Permanent: 永久代
    """

    # 项目规模预设配置
    SCALE_CONFIGS = {
        "small": {"eden": 500, "survivor": 250, "old": 2000, "permanent": 5000},
        "medium": {"eden": 1000, "survivor": 500, "old": 5000, "permanent": 10000},
        "large": {"eden": 5000, "survivor": 2000, "old": 20000, "permanent": 50000},
    }

    def __init__(
        self,
        project_scale: str = "medium",  # "small" | "medium" | "large"
        eden_size: int | None = None,
        survivor_size: int | None = None,
        old_size: int | None = None,
        permanent_size: int | None = None,
        survivor_ratio: int = 8,  # Eden:Survivor比例
        promotion_threshold: int = 15,  # 晋升阈值 (类似MaxTenuringThreshold)
        large_entry_threshold: int = 500,  # 大条目阈值 (类似PretenureSizeThreshold)
    ) -> None:
        # 根据项目规模获取默认配置
        scale_config = self.SCALE_CONFIGS.get(project_scale, self.SCALE_CONFIGS["medium"])

        # 优先使用显式指定的值，否则使用规模配置
        eden_size = eden_size or scale_config["eden"]
        survivor_size = survivor_size or scale_config["survivor"]
        old_size = old_size or scale_config["old"]
        permanent_size = permanent_size or scale_config["permanent"]

        # 分代区域
        self.eden = EdenMemory(max_size=eden_size)
        self.survivor_0 = SurvivorMemory(max_size=survivor_size)
        self.survivor_1 = SurvivorMemory(max_size=survivor_size)
        self.old = OldMemory(max_size=old_size)
        self.permanent = PermanentMemory(max_size=permanent_size)

        # 配置参数
        self.project_scale = project_scale
        self.survivor_ratio = survivor_ratio
        self.promotion_threshold = promotion_threshold
        self.large_entry_threshold = large_entry_threshold

        # 当前活跃Survivor (S0或S1)
        self._active_survivor: SurvivorMemory = self.survivor_0
        self._inactive_survivor: SurvivorMemory = self.survivor_1

        # 统计信息
        self._gc_stats: dict[str, Any] = {
            "minor_gc_count": 0,
            "major_gc_count": 0,
            "full_gc_count": 0,
            "total_removed": 0,
            "total_promoted": 0,
        }

    def allocate(self, content: str, importance: int = 50, metadata: dict[str, Any] | None = None) -> MemoryEntry | None:
        """
        分配新记忆条目 - 类似 JVM 对象分配

        分配策略:
        1. 小条目 → Eden
        2. 大条目 (超过阈值) → 直接进Old
        3. 高重要性 → 直接进Old

        Args:
            content: 内容
            importance: 重要性评分
            metadata: 元数据

        Returns:
            分配的条目
        """
        # 判断是否直接进Old
        is_large = len(content) > self.large_entry_threshold
        is_high_importance = importance >= 90

        if is_large or is_high_importance:
            # 直接进入老年代 (类似JVM的大对象直接分配)
            import uuid
            entry = MemoryEntry(
                id=str(uuid.uuid4()),
                content=content,
                importance=importance,
                region=MemoryRegion.OLD,
                metadata=metadata or {},
            )
            if self.old.put(entry):
                return entry
            # Old满了，触发Major GC后重试
            return None

        # 正常分配到Eden
        return self.eden.allocate(content, importance, metadata)

    def swap_survivor(self) -> None:
        """
        交换Survivor区 - 类似 JVM 的 Survivor 复制算法

        S0 ↔ S1 交换，清空 inactive 区准备下一次GC
        """
        self._active_survivor, self._inactive_survivor = (
            self._inactive_survivor,
            self._active_survivor,
        )
        self._inactive_survivor.clear()

    def get_active_survivor(self) -> SurvivorMemory:
        """获取当前活跃Survivor"""
        return self._active_survivor

    def get_entry(self, id: str) -> MemoryEntry | None:
        """
        获取条目 - 从所有区域查找

        Args:
            id: 条目ID

        Returns:
            找到的条目
        """
        # 依次查找各区域
        for region in [self.eden, self._active_survivor, self.old, self.permanent]:
            entry = region.get(id)
            if entry:
                return entry
        return None

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._gc_stats,
            "eden_size": self.eden.size(),
            "survivor_size": self._active_survivor.size(),
            "old_size": self.old.size(),
            "permanent_size": self.permanent.size(),
            "eden_max": self.eden.max_size,
            "old_max": self.old.max_size,
        }

    def update_gc_stats(self, gc_type: str, removed: int, promoted: int) -> None:
        """更新GC统计"""
        if gc_type == "minor":
            self._gc_stats["minor_gc_count"] += 1
        elif gc_type == "major":
            self._gc_stats["major_gc_count"] += 1
        elif gc_type == "full":
            self._gc_stats["full_gc_count"] += 1
        self._gc_stats["total_removed"] += removed
        self._gc_stats["total_promoted"] += promoted