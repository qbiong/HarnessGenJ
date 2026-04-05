"""
Memory Module - JVM-style Memory Management

统一记忆管理系统:
- MemoryManager: 统一管理入口（整合项目状态、文档、会话）
- MemoryHeap: 分代堆 (Permanent/Old/Survivor/Eden)
- GarbageCollector: 垃圾回收
- HotspotDetector: 热点检测
- AutoAssembler: 自动装配
- DocumentType: 文档类型常量
- DOCUMENT_OWNERSHIP: 文档所有权配置
"""

from harnessgenj.memory.manager import (
    MemoryManager,
    ProjectInfo,
    ProjectStats,
    DocumentType,
    DOCUMENT_OWNERSHIP,
    DOCUMENT_REGION_MAP,
    REGION_LOAD_STRATEGY,
    get_document_region,
    get_region_load_strategy,
)
from harnessgenj.memory.heap import (
    MemoryHeap,
    MemoryEntry,
    MemoryRegion,
    EdenMemory,
    SurvivorMemory,
    OldMemory,
    PermanentMemory,
)
from harnessgenj.memory.gc import (
    GarbageCollector,
    GCResult,
    GCAlgorithm,
    QualityAwareCollector,
)
from harnessgenj.memory.hotspot import HotspotDetector, HotspotInfo, CallCounter
from harnessgenj.memory.assembler import AutoAssembler, AssemblyTemplate

__all__ = [
    # 主入口
    "MemoryManager",
    "ProjectInfo",
    "ProjectStats",
    # 文档系统
    "DocumentType",
    "DOCUMENT_OWNERSHIP",
    "DOCUMENT_REGION_MAP",
    "REGION_LOAD_STRATEGY",
    "get_document_region",
    "get_region_load_strategy",
    # Heap
    "MemoryHeap",
    "MemoryEntry",
    "MemoryRegion",
    "EdenMemory",
    "SurvivorMemory",
    "OldMemory",
    "PermanentMemory",
    # GC
    "GarbageCollector",
    "GCResult",
    "GCAlgorithm",
    "QualityAwareCollector",
    # Hotspot
    "HotspotDetector",
    "HotspotInfo",
    "CallCounter",
    # Assembler
    "AutoAssembler",
    "AssemblyTemplate",
]