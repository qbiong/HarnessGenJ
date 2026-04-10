"""
Structured Knowledge - 结构化知识库系统

为知识库添加结构化支持：
1. 唯一 ID - 每个知识条目有唯一标识符
2. 类型分类 - bug_fix/decision_pattern/architecture_change/security_issue
3. 代码位置索引 - 关联到具体代码文件和行号
4. 时间戳追踪 - 创建时间、更新时间、验证时间

使用示例:
    from harnessgenj.memory.structured_knowledge import (
        StructuredKnowledgeManager,
        KnowledgeEntry,
        KnowledgeType,
    )

    manager = StructuredKnowledgeManager(".harnessgenj")

    # 存储安全问题的知识
    entry = KnowledgeEntry(
        type=KnowledgeType.SECURITY_ISSUE,
        problem="ShellTool命令注入风险",
        solution="使用命令白名单模式",
        code_location={
            "file": "app/src/main/java/com/example/ShellTool.java",
            "lines": [93, 118],
        },
        severity="critical",
        tags=["security", "shell", "injection"],
    )
    manager.store(entry)

    # 按类型查询
    security_issues = manager.query_by_type(KnowledgeType.SECURITY_ISSUE)

    # 按标签查询
    tagged = manager.query_by_tags(["security", "injection"])

    # 按文件查询
    file_knowledge = manager.query_by_file("ShellTool.java")
"""

import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from harnessgenj.utils.exception_handler import log_exception
from enum import Enum
from pydantic import BaseModel, Field


class KnowledgeType(str, Enum):
    """知识类型枚举"""

    BUG_FIX = "bug_fix"
    DECISION_PATTERN = "decision_pattern"
    ARCHITECTURE_CHANGE = "architecture_change"
    SECURITY_ISSUE = "security_issue"
    TEST_CASE = "test_case"
    API_REFERENCE = "api_reference"
    BEST_PRACTICE = "best_practice"
    LESSON_LEARNED = "lesson_learned"


class CodeLocation(BaseModel):
    """代码位置"""

    file: str = Field(..., description="文件路径（相对于项目根目录）")
    lines: list[int] = Field(default_factory=list, description="相关行号列表")
    start_line: int | None = Field(default=None, description="起始行号")
    end_line: int | None = Field(default=None, description="结束行号")
    function_name: str | None = Field(default=None, description="函数名")
    class_name: str | None = Field(default=None, description="类名")


class KnowledgeEntry(BaseModel):
    """
    结构化知识条目

    每个条目包含：
    - 唯一 ID
    - 类型分类
    - 问题描述
    - 解决方案
    - 代码位置（可选）
    - 严重程度（可选）
    - 标签
    - 时间戳
    - 验证状态
    """

    # 唯一标识
    id: str = Field(default_factory=lambda: f"kn-{uuid.uuid4().hex[:8]}", description="唯一标识符")

    # 类型分类
    type: KnowledgeType = Field(..., description="知识类型")

    # 核心内容
    problem: str = Field(..., description="问题描述")
    solution: str = Field(..., description="解决方案")

    # 代码位置（可选）
    code_location: CodeLocation | None = Field(default=None, description="代码位置")

    # 附加信息
    severity: str | None = Field(default=None, description="严重程度: critical/high/medium/low")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    rationale: str | None = Field(default=None, description="决策理由（用于 decision_pattern）")
    alternatives: list[str] = Field(default_factory=list, description="备选方案（用于 decision_pattern）")
    before: str | None = Field(default=None, description="变更前（用于 architecture_change）")
    after: str | None = Field(default=None, description="变更后（用于 architecture_change）")
    reason: str | None = Field(default=None, description="变更原因（用于 architecture_change）")

    # 测试相关（用于 test_case）
    scenario: str | None = Field(default=None, description="测试场景")
    expected: str | None = Field(default=None, description="期望结果")
    actual: str | None = Field(default=None, description="实际结果")

    # 时间戳
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    verified_at: float | None = Field(default=None, description="验证时间")

    # 验证状态
    verified: bool = Field(default=False, description="是否已验证")
    verification_notes: str | None = Field(default=None, description="验证备注")

    # 引用和关联
    related_entries: list[str] = Field(default_factory=list, description="关联条目 ID 列表")
    references: list[str] = Field(default_factory=list, description="外部引用链接")

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    # 来源信息
    source: str | None = Field(default=None, description="来源：agent_id 或 'user'")
    task_id: str | None = Field(default=None, description="关联的任务 ID")

    def touch(self) -> None:
        """更新访问时间"""
        self.updated_at = time.time()

    def verify(self, notes: str | None = None) -> None:
        """
        标记为已验证

        Args:
            notes: 验证备注
        """
        self.verified = True
        self.verified_at = time.time()
        self.verification_notes = notes

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeEntry":
        """从字典创建"""
        # 处理 code_location
        if "code_location" in data and isinstance(data["code_location"], dict):
            data["code_location"] = CodeLocation(**data["code_location"])

        # 处理 type
        if "type" in data and isinstance(data["type"], str):
            data["type"] = KnowledgeType(data["type"])

        return cls(**data)


class KnowledgeIndex(BaseModel):
    """知识索引"""

    # 按类型索引
    by_type: dict[str, list[str]] = Field(default_factory=dict, description="类型 -> ID列表")

    # 按标签索引
    by_tag: dict[str, list[str]] = Field(default_factory=dict, description="标签 -> ID列表")

    # 按文件索引
    by_file: dict[str, list[str]] = Field(default_factory=dict, description="文件 -> ID列表")

    # 按严重程度索引
    by_severity: dict[str, list[str]] = Field(default_factory=dict, description="严重程度 -> ID列表")

    # 更新时间
    last_updated: float = Field(default_factory=time.time, description="最后更新时间")


class StructuredKnowledgeManager:
    """
    结构化知识管理器

    提供知识的结构化存储、检索和索引功能。

    设计原则：
    - 知识条目统一存储到 MemoryHeap (Old 区)
    - 索引保存在本地文件用于快速查询
    - 与 MemoryManager 集成，利用 GC 机制

    使用示例:
        manager = StructuredKnowledgeManager(".harnessgenj")

        # 存储知识
        entry = KnowledgeEntry(...)
        manager.store(entry)

        # 查询知识
        entries = manager.query_by_type(KnowledgeType.BUG_FIX)
        entries = manager.query_by_tags(["security"])
        entries = manager.query_by_file("ShellTool.java")

        # 搜索知识
        results = manager.search("命令注入")
    """

    def __init__(self, workspace: str = ".harnessgenj", heap: Any = None) -> None:
        """
        初始化结构化知识管理器

        Args:
            workspace: 工作空间路径
            heap: MemoryHeap 实例（用于统一存储）
        """
        self.workspace = workspace
        self.heap = heap
        self.knowledge_dir = Path(workspace) / "structured_knowledge"
        self.index_file = self.knowledge_dir / "index.json"

        # 知识条目存储（本地缓存）
        self._entries: dict[str, KnowledgeEntry] = {}

        # 索引
        self._index = KnowledgeIndex()

        # 确保目录存在
        self._ensure_directories()

        # 加载索引
        self._load_index()

    def set_heap(self, heap: Any) -> None:
        """
        设置 Heap 实例（延迟注入）

        Args:
            heap: MemoryHeap 实例
        """
        self.heap = heap

    def _ensure_directories(self) -> None:
        """确保目录存在"""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def store(self, entry: KnowledgeEntry) -> str:
        """
        存储知识条目

        存储策略：
        1. 存储到 MemoryHeap Old 区（如果有 heap）
        2. 更新本地索引

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        # 存储到 Heap（统一管理）
        if self.heap:
            from harnessgenj.memory.heap import MemoryEntry, MemoryRegion
            heap_entry = MemoryEntry(
                id=f"knowledge_{entry.id}",
                content=entry.model_dump_json(),
                importance=self._get_importance_for_heap(entry),
                region=MemoryRegion.OLD,
                metadata={
                    "type": "structured_knowledge",
                    "knowledge_type": entry.type.value,
                    "knowledge_id": entry.id,
                },
            )
            self.heap.old.put(heap_entry)

        # 本地缓存
        self._entries[entry.id] = entry

        # 更新索引
        self._update_index(entry)

        # 保存索引
        self._save_index()

        return entry.id

    def _get_importance_for_heap(self, entry: KnowledgeEntry) -> int:
        """根据知识类型计算 Heap 存储重要性"""
        severity_map = {
            "critical": 100,
            "high": 90,
            "medium": 70,
            "low": 50,
        }
        base_importance = severity_map.get(entry.severity or "", 70)
        # 已验证的知识更重要
        if entry.verified:
            base_importance = min(100, base_importance + 10)
        return base_importance

    def update(self, entry_id: str, updates: dict[str, Any]) -> KnowledgeEntry | None:
        """
        更新知识条目

        Args:
            entry_id: 条目 ID
            updates: 更新内容

        Returns:
            更新后的条目，如果不存在返回 None
        """
        if entry_id not in self._entries:
            return None

        entry = self._entries[entry_id]

        # 更新字段
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.touch()

        # 更新 Heap 中的条目
        if self.heap:
            heap_entry = self.heap.old.get(f"knowledge_{entry_id}")
            if heap_entry:
                heap_entry.content = entry.model_dump_json()
                heap_entry.importance = self._get_importance_for_heap(entry)

        # 更新索引
        self._rebuild_index()

        # 保存索引
        self._save_index()

        return entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """
        获取知识条目

        优先从本地缓存获取，如果不存在则尝试从 Heap 加载

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目，如果不存在返回 None
        """
        # 先查本地缓存
        if entry_id in self._entries:
            return self._entries[entry_id]

        # 尝试从 Heap 加载
        if self.heap:
            heap_entry = self.heap.old.get(f"knowledge_{entry_id}")
            if heap_entry and heap_entry.metadata.get("type") == "structured_knowledge":
                try:
                    entry = KnowledgeEntry.from_dict(json.loads(heap_entry.content))
                    self._entries[entry_id] = entry
                    return entry
                except Exception as e:
                    log_exception(e, context=f"get_entry {entry_id}", level=30)

        return None

    def delete(self, entry_id: str) -> bool:
        """
        删除知识条目

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        if entry_id not in self._entries:
            return False

        # 从 Heap 删除
        if self.heap:
            self.heap.old.remove(f"knowledge_{entry_id}")

        # 从本地缓存删除
        del self._entries[entry_id]

        # 重建索引
        self._rebuild_index()

        # 保存索引
        self._save_index()

        return True

    def query_by_type(self, knowledge_type: KnowledgeType) -> list[KnowledgeEntry]:
        """
        按类型查询知识

        Args:
            knowledge_type: 知识类型

        Returns:
            知识条目列表
        """
        ids = self._index.by_type.get(knowledge_type.value, [])
        return [self._entries[id_] for id_ in ids if id_ in self._entries]

    def query_by_tags(self, tags: list[str], match_all: bool = False) -> list[KnowledgeEntry]:
        """
        按标签查询知识

        Args:
            tags: 标签列表
            match_all: 是否需要匹配所有标签

        Returns:
            知识条目列表
        """
        if not tags:
            return []

        # 获取每个标签对应的 ID 列表
        id_sets = []
        for tag in tags:
            ids = set(self._index.by_tag.get(tag, []))
            id_sets.append(ids)

        if not id_sets:
            return []

        # 取交集或并集
        if match_all:
            result_ids = set.intersection(*id_sets)
        else:
            result_ids = set.union(*id_sets)

        return [self._entries[id_] for id_ in result_ids if id_ in self._entries]

    def query_by_file(self, file_path: str) -> list[KnowledgeEntry]:
        """
        按文件查询知识

        Args:
            file_path: 文件路径（可以是部分路径）

        Returns:
            知识条目列表
        """
        # 先尝试精确匹配
        ids = self._index.by_file.get(file_path, [])

        # 如果没有结果，尝试部分匹配
        if not ids:
            for file_key, entry_ids in self._index.by_file.items():
                if file_path in file_key or file_key in file_path:
                    ids.extend(entry_ids)

        return [self._entries[id_] for id_ in ids if id_ in self._entries]

    def query_by_severity(self, severity: str) -> list[KnowledgeEntry]:
        """
        按严重程度查询知识

        Args:
            severity: 严重程度

        Returns:
            知识条目列表
        """
        ids = self._index.by_severity.get(severity, [])
        return [self._entries[id_] for id_ in ids if id_ in self._entries]

    def search(self, query: str) -> list[KnowledgeEntry]:
        """
        搜索知识

        在问题描述、解决方案、标签中进行搜索

        Args:
            query: 搜索关键词

        Returns:
            匹配的知识条目列表
        """
        query_lower = query.lower()
        results = []

        for entry in self._entries.values():
            # 在问题描述中搜索
            if query_lower in entry.problem.lower():
                results.append(entry)
                continue

            # 在解决方案中搜索
            if query_lower in entry.solution.lower():
                results.append(entry)
                continue

            # 在标签中搜索
            for tag in entry.tags:
                if query_lower in tag.lower():
                    results.append(entry)
                    break

        return results

    def get_recent(self, limit: int = 10) -> list[KnowledgeEntry]:
        """
        获取最近的知识条目

        Args:
            limit: 返回数量限制

        Returns:
            按创建时间排序的知识条目列表
        """
        entries = sorted(
            self._entries.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )
        return entries[:limit]

    def get_unverified(self) -> list[KnowledgeEntry]:
        """
        获取未验证的知识条目

        Returns:
            未验证的知识条目列表
        """
        return [e for e in self._entries.values() if not e.verified]

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_entries": len(self._entries),
            "by_type": {},
            "by_severity": {},
            "verified_count": 0,
            "unverified_count": 0,
        }

        for entry in self._entries.values():
            # 按类型统计
            type_name = entry.type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

            # 按严重程度统计
            if entry.severity:
                stats["by_severity"][entry.severity] = stats["by_severity"].get(entry.severity, 0) + 1

            # 验证状态统计
            if entry.verified:
                stats["verified_count"] += 1
            else:
                stats["unverified_count"] += 1

        return stats

    def _update_index(self, entry: KnowledgeEntry) -> None:
        """
        更新索引（添加单个条目）

        Args:
            entry: 知识条目
        """
        # 按类型索引
        type_key = entry.type.value
        if type_key not in self._index.by_type:
            self._index.by_type[type_key] = []
        if entry.id not in self._index.by_type[type_key]:
            self._index.by_type[type_key].append(entry.id)

        # 按标签索引
        for tag in entry.tags:
            if tag not in self._index.by_tag:
                self._index.by_tag[tag] = []
            if entry.id not in self._index.by_tag[tag]:
                self._index.by_tag[tag].append(entry.id)

        # 按文件索引
        if entry.code_location:
            file_key = entry.code_location.file
            if file_key not in self._index.by_file:
                self._index.by_file[file_key] = []
            if entry.id not in self._index.by_file[file_key]:
                self._index.by_file[file_key].append(entry.id)

        # 按严重程度索引
        if entry.severity:
            if entry.severity not in self._index.by_severity:
                self._index.by_severity[entry.severity] = []
            if entry.id not in self._index.by_severity[entry.severity]:
                self._index.by_severity[entry.severity].append(entry.id)

        self._index.last_updated = time.time()

    def _rebuild_index(self) -> None:
        """重建索引"""
        self._index = KnowledgeIndex()

        for entry in self._entries.values():
            self._update_index(entry)

    def _save_index(self) -> None:
        """保存索引"""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self._index.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_exception(e, context="_save_index", level=30)

    def _load_index(self) -> None:
        """加载索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                self._index = KnowledgeIndex(**index_data)
            except Exception as e:
                log_exception(e, context="_load_index", level=30)
                self._rebuild_index()

    def _load_entries_from_heap(self) -> None:
        """从 Heap 加载条目到本地缓存"""
        if not self.heap:
            return

        try:
            for entry in self.heap.old.list_entries():
                metadata = entry.metadata
                if metadata.get("type") == "structured_knowledge":
                    knowledge_id = metadata.get("knowledge_id")
                    if knowledge_id:
                        try:
                            knowledge_entry = KnowledgeEntry.from_dict(
                                json.loads(entry.content)
                            )
                            self._entries[knowledge_id] = knowledge_entry
                        except Exception as e:
                            log_exception(e, context=f"_load_entries_from_heap {knowledge_id}", level=30)
        except Exception as e:
            log_exception(e, context="_load_entries_from_heap", level=30)

    def export_to_markdown(self, output_path: str | Path | None = None) -> str:
        """
        导出知识库为 Markdown 格式

        Args:
            output_path: 输出文件路径（可选）

        Returns:
            Markdown 内容
        """
        lines = [
            "# 结构化知识库",
            "",
            f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 总条目数: {len(self._entries)}",
            "",
        ]

        # 按类型分组
        for knowledge_type in KnowledgeType:
            entries = self.query_by_type(knowledge_type)
            if not entries:
                continue

            lines.append(f"## {knowledge_type.value}")
            lines.append("")

            for entry in entries:
                lines.append(f"### {entry.id}")
                lines.append("")
                lines.append(f"**问题**: {entry.problem}")
                lines.append("")
                lines.append(f"**解决方案**: {entry.solution}")
                lines.append("")

                if entry.code_location:
                    lines.append(f"**代码位置**: `{entry.code_location.file}`")
                    if entry.code_location.lines:
                        lines.append(f"  - 行号: {', '.join(map(str, entry.code_location.lines))}")
                    lines.append("")

                if entry.tags:
                    lines.append(f"**标签**: {', '.join(entry.tags)}")
                    lines.append("")

                if entry.severity:
                    lines.append(f"**严重程度**: {entry.severity}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        content = "\n".join(lines)

        # 保存到文件
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")

        return content


def create_structured_knowledge_manager(workspace: str = ".harnessgenj") -> StructuredKnowledgeManager:
    """创建结构化知识管理器"""
    return StructuredKnowledgeManager(workspace)