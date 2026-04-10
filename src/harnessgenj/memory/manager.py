"""
Memory Manager - JVM-style Memory Management Controller

统一记忆管理器，整合:
- 分代存储: Permanent/Old/Survivor/Eden
- 垃圾回收: 自动清理过期数据
- 热点检测: 识别高频访问数据
- 上下文装配: 渐进式披露
- 文档管理: 所有权控制、版本管理

数据流:
====================

Permanent 区 (核心知识，永不回收):
- 项目配置 (project.json)
- 角色定义 (AGENTS.md)
- 核心知识

Old 区 (文档资产，长期存储):
- requirements.md
- design.md
- progress.md
- development.md
- testing.md

Survivor 区 (当前任务，短期活跃):
- 当前任务上下文
- 任务依赖关系
- 临时状态

Eden 区 (会话消息，可丢弃):
- 用户对话
- AI 响应
"""

from typing import Any
from pydantic import BaseModel, Field
import os
import json
import time
import logging
import threading

from harnessgenj.memory.heap import (
    MemoryHeap,
    MemoryEntry,
    MemoryRegion,
)
from harnessgenj.memory.gc import (
    GarbageCollector,
    GCResult,
)
from harnessgenj.memory.hotspot import HotspotDetector, HotspotInfo
from harnessgenj.memory.structured_knowledge import (
    StructuredKnowledgeManager,
    KnowledgeEntry,
    KnowledgeType,
    CodeLocation,
    create_structured_knowledge_manager,
)

logger = logging.getLogger(__name__)


# ==================== 文档系统定义 ====================

class DocumentType:
    """文档类型常量"""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PROGRESS = "progress"


# 文档所有权配置（用于渐进式披露）
DOCUMENT_OWNERSHIP = {
    DocumentType.REQUIREMENTS: {
        "owner": "product_manager",
        "visible_to": ["project_manager", "product_manager", "developer", "code_reviewer", "bug_hunter"],
        "read_only_for": ["developer", "code_reviewer", "bug_hunter"],
    },
    DocumentType.DESIGN: {
        "owner": "architect",
        "visible_to": ["project_manager", "architect", "developer", "code_reviewer", "bug_hunter"],
        "read_only_for": ["developer", "code_reviewer", "bug_hunter"],
    },
    DocumentType.DEVELOPMENT: {
        "owner": "developer",
        "visible_to": ["project_manager", "developer", "code_reviewer", "bug_hunter"],
        "read_only_for": ["code_reviewer", "bug_hunter"],
    },
    DocumentType.TESTING: {
        "owner": "tester",
        "visible_to": ["project_manager", "tester", "developer", "code_reviewer", "bug_hunter"],
        "read_only_for": ["developer", "code_reviewer", "bug_hunter"],
    },
    DocumentType.PROGRESS: {
        "owner": "project_manager",
        "visible_to": ["project_manager", "product_manager", "architect", "developer", "tester", "code_reviewer", "bug_hunter"],
        "read_only_for": ["product_manager", "architect", "developer", "tester", "code_reviewer", "bug_hunter"],
    },
}

# 文档类型到JVM内存区域的映射
DOCUMENT_REGION_MAP = {
    "project_info": MemoryRegion.PERMANENT,
    "team_config": MemoryRegion.PERMANENT,
    DocumentType.DESIGN: MemoryRegion.OLD,
    DocumentType.REQUIREMENTS: MemoryRegion.SURVIVOR_0,
    DocumentType.PROGRESS: MemoryRegion.SURVIVOR_0,
    DocumentType.DEVELOPMENT: MemoryRegion.EDEN,
    DocumentType.TESTING: MemoryRegion.EDEN,
}

# 区域加载策略（渐进式披露）
REGION_LOAD_STRATEGY = {
    MemoryRegion.PERMANENT: {
        "always_load": True,
        "full_content": True,
        "description": "项目核心信息，始终加载完整内容",
    },
    MemoryRegion.OLD: {
        "always_load": False,
        "full_content": False,
        "description": "长期文档，按需加载摘要",
    },
    MemoryRegion.SURVIVOR_0: {
        "always_load": True,
        "full_content": False,
        "description": "活跃文档，加载摘要",
    },
    MemoryRegion.EDEN: {
        "always_load": False,
        "full_content": False,
        "description": "临时内容，按需加载",
    },
}


def get_document_region(doc_type: str) -> MemoryRegion:
    """获取文档所属的内存区域"""
    return DOCUMENT_REGION_MAP.get(doc_type, MemoryRegion.EDEN)


def get_region_load_strategy(region: MemoryRegion) -> dict[str, Any]:
    """获取区域的加载策略"""
    return REGION_LOAD_STRATEGY.get(region, REGION_LOAD_STRATEGY[MemoryRegion.EDEN])


class ProjectInfo(BaseModel):
    """项目基本信息"""
    name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目描述")
    tech_stack: str = Field(default="", description="技术栈")
    status: str = Field(default="init", description="项目状态")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ProjectStats(BaseModel):
    """项目统计"""
    features_total: int = Field(default=0)
    features_completed: int = Field(default=0)
    bugs_total: int = Field(default=0)
    bugs_fixed: int = Field(default=0)
    progress: int = Field(default=0)


class MemoryManager:
    """
    统一记忆管理器 - JVM 风格

    核心功能:
    1. 分代存储: 不同数据存入不同区域
    2. 垃圾回收: 自动清理过期数据
    3. 热点检测: 识别高频访问数据
    4. 上下文装配: 为 LLM 生成上下文
    5. 持久化: 自动保存到磁盘

    使用示例:
        memory = MemoryManager(".harnessgenj")

        # 存储项目知识
        memory.store_knowledge("project_name", "电商平台")

        # 存储文档
        memory.store_document("requirements", "# 需求\\n...")

        # 存储当前任务
        memory.store_task("TASK-123", {"desc": "实现登录"})

        # 存储会话消息
        memory.store_message("用户需要一个登录功能", "user")

        # 获取上下文
        context = memory.get_context_for_llm("developer", max_tokens=4000)
    """

    # 文档类型映射到区域
    DOC_REGIONS = {
        "requirements": MemoryRegion.OLD,
        "design": MemoryRegion.OLD,
        "development": MemoryRegion.OLD,
        "testing": MemoryRegion.OLD,
        "progress": MemoryRegion.OLD,
    }

    def __init__(self, workspace: str = ".harnessgenj") -> None:
        """
        初始化记忆管理器

        Args:
            workspace: 工作空间路径，用于持久化
        """
        self.workspace = workspace

        # 线程锁保护关键数据结构
        self._lock = threading.RLock()

        # 核心组件
        self.heap = MemoryHeap()
        self.gc = GarbageCollector()
        self.hotspot = HotspotDetector()

        # 结构化知识管理器
        self.structured = create_structured_knowledge_manager(workspace)
        # 注入 Heap 实现统一存储
        self.structured.set_heap(self.heap)

        # 项目状态
        self.project_info = ProjectInfo()
        self.project_stats = ProjectStats()

        # 当前任务
        self._current_task: dict[str, Any] = {}

        # 质量系统集成（由 Harness 链接）
        self._score_manager: Any | None = None
        self._quality_tracker: Any | None = None

        # 确保目录存在
        self._ensure_directories()

        # 加载持久化数据
        self._load()

    def set_quality_system(self, score_manager: Any, quality_tracker: Any) -> None:
        """
        链接质量系统

        Args:
            score_manager: 积分管理器
            quality_tracker: 质量追踪器
        """
        self._score_manager = score_manager
        self._quality_tracker = quality_tracker

    def _ensure_directories(self) -> None:
        """确保目录存在"""
        dirs = [
            self.workspace,
            os.path.join(self.workspace, "documents"),
            os.path.join(self.workspace, "summaries"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    # ==================== 统一存储接口 ====================

    def store_knowledge(self, key: str, content: str, importance: int = 100) -> None:
        """
        存储核心知识 → Permanent 区

        Args:
            key: 知识键
            content: 知识内容
            importance: 重要性 (默认最高)
        """
        with self._lock:
            self.heap.permanent.store_knowledge(key, content, importance)
            self.hotspot.record_knowledge_reference(key)
            self._save()

    def get_knowledge(self, key: str) -> str | None:
        """获取核心知识"""
        with self._lock:
            self.hotspot.record_knowledge_reference(key)
            entry = self.heap.permanent.get_knowledge(key)
            return entry.content if entry else None

    def store_document(
        self,
        doc_type: str,
        content: str,
        generator_id: str | None = None,
        importance: int = 70,
    ) -> bool:
        """
        存储项目文档 → Old 区

        Args:
            doc_type: 文档类型 (requirements/design/development/testing/progress)
            content: 文档内容
            generator_id: 生成者角色ID
            importance: 重要性评分
        """
        # 存储到 Old 区
        entry = MemoryEntry(
            id=doc_type,
            content=content,
            importance=importance,
            region=MemoryRegion.OLD,
            generator_id=generator_id,
        )
        self.heap.old.put(entry)

        # 记录热点
        self.hotspot.record_knowledge_reference(doc_type)

        # 持久化到文件
        self._save_document(doc_type, content)

        return True

    def get_document(self, doc_type: str) -> str | None:
        """获取项目文档"""
        self.hotspot.record_knowledge_reference(doc_type)
        entry = self.heap.old.get(doc_type)
        return entry.content if entry else None

    def get_document_entry(self, doc_type: str) -> MemoryEntry | None:
        """获取文档条目（包含质量信息）"""
        self.hotspot.record_knowledge_reference(doc_type)
        return self.heap.old.get(doc_type)

    def store_task(
        self,
        task_id: str,
        task_info: dict[str, Any],
        generator_id: str | None = None,
    ) -> None:
        """
        存储当前任务 → Survivor 区

        Args:
            task_id: 任务ID
            task_info: 任务信息
            generator_id: 生成者角色ID
        """
        with self._lock:
            entry = MemoryEntry(
                id=task_id,
                content=json.dumps(task_info),
                importance=80,
                region=MemoryRegion.SURVIVOR_0,
                generator_id=generator_id,
            )
            self.heap.get_active_survivor().put(entry)
            self._current_task = {"task_id": task_id, **task_info}

        # 触发 GC 检查（在锁外执行）
        self._maybe_gc()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """获取任务"""
        with self._lock:
            entry = self.heap.get_active_survivor().get(task_id)
            if entry:
                return json.loads(entry.content)
            return None

    def get_current_task(self) -> dict[str, Any]:
        """获取当前任务"""
        with self._lock:
            return self._current_task.copy()

    def clear_task(self, task_id: str) -> bool:
        """清除任务"""
        with self._lock:
            self.heap.get_active_survivor().remove(task_id)
            if self._current_task.get("task_id") == task_id:
                self._current_task = {}
                # 删除当前任务文件
                current_task_path = os.path.join(self.workspace, "current_task.json")
                if os.path.exists(current_task_path):
                    os.remove(current_task_path)
            self._save()
        return True

    def store_message(self, message: str, role: str = "user", importance: int = 50) -> None:
        """
        存储会话消息 → Eden 区

        Args:
            message: 消息内容
            role: 角色 (user/assistant/system)
            importance: 重要性
        """
        self.heap.allocate(message, importance, {"role": role})

        # 触发 GC 检查
        self._maybe_gc()

    def get_recent_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取最近的消息"""
        entries = self.heap.eden.list_entries()[-limit:]
        return [
            {"content": e.content, "role": e.metadata.get("role", "user")}
            for e in entries
        ]

    # ==================== 质量感知存储接口 ====================

    def store_artifact(
        self,
        artifact_id: str,
        content: str,
        artifact_type: str = "code",
        generator_id: str | None = None,
        importance: int = 60,
    ) -> MemoryEntry:
        """
        存储产出物（代码/文档）→ Old 区

        用于存储对抗审查产生的产出物，记录生成者信息

        Args:
            artifact_id: 产出物ID
            content: 内容
            artifact_type: 类型 (code/document/config)
            generator_id: 生成者角色ID
            importance: 重要性

        Returns:
            创建的记忆条目
        """
        entry = MemoryEntry(
            id=artifact_id,
            content=content,
            importance=importance,
            region=MemoryRegion.OLD,
            generator_id=generator_id,
            metadata={"artifact_type": artifact_type},
        )
        self.heap.old.put(entry)
        self._save()
        return entry

    def get_artifact(self, artifact_id: str) -> MemoryEntry | None:
        """获取产出物条目"""
        return self.heap.old.get(artifact_id)

    def update_entry_quality(
        self,
        entry_id: str,
        quality_score: float,
        review_result: str | None = None,
        discriminator_id: str | None = None,
    ) -> bool:
        """
        更新记忆条目的质量信息

        在对抗审查完成后调用，建立质量数据与记忆的关联

        Args:
            entry_id: 条目ID
            quality_score: 质量分数 (0-100)
            review_result: 审查结果 ("passed" | "failed")
            discriminator_id: 审查者角色ID

        Returns:
            是否更新成功
        """
        entry = self.heap.get_entry(entry_id)
        if entry:
            entry.update_quality(
                quality_score=quality_score,
                review_result=review_result,
                discriminator_id=discriminator_id,
            )
            self._save()
            return True
        return False

    def link_adversarial_result(
        self,
        entry_id: str,
        quality_score: float,
        passed: bool,
        generator_id: str | None = None,
        discriminator_id: str | None = None,
    ) -> bool:
        """
        将对抗审查结果关联到记忆条目

        这是质量数据流的核心方法，在对抗审查完成后调用

        Args:
            entry_id: 条目ID
            quality_score: 质量分数
            passed: 是否通过审查
            generator_id: 生成者ID（可选，用于补充）
            discriminator_id: 审查者ID

        Returns:
            是否关联成功
        """
        entry = self.heap.get_entry(entry_id)
        if not entry:
            return False

        # 更新质量信息
        entry.update_quality(
            quality_score=quality_score,
            review_result="passed" if passed else "failed",
            generator_id=generator_id,
            discriminator_id=discriminator_id,
        )

        # 更新热点追踪
        self.hotspot.record_knowledge_reference(entry_id)

        self._save()
        return True

    def get_entries_by_generator(self, generator_id: str) -> list[MemoryEntry]:
        """获取指定生成者创建的所有条目"""
        entries = []
        for region in [self.heap.old, self.heap.eden, self.heap.get_active_survivor()]:
            for entry in region.list_entries():
                if entry.generator_id == generator_id:
                    entries.append(entry)
        return entries

    def get_entries_by_quality(
        self,
        min_quality: float = 0,
        max_quality: float = 100,
        region: MemoryRegion | None = None,
    ) -> list[MemoryEntry]:
        """
        按质量分数筛选条目

        Args:
            min_quality: 最低质量分数
            max_quality: 最高质量分数
            region: 指定区域（可选）

        Returns:
            符合条件的条目列表
        """
        entries = []

        if region:
            if region == MemoryRegion.OLD:
                source = self.heap.old.list_entries()
            elif region == MemoryRegion.EDEN:
                source = self.heap.eden.list_entries()
            elif region in (MemoryRegion.SURVIVOR_0, MemoryRegion.SURVIVOR_1):
                source = self.heap.get_active_survivor().list_entries()
            else:
                source = self.heap.permanent.list_entries()
            entries = list(source)
        else:
            entries = (
                self.heap.old.list_entries() +
                self.heap.eden.list_entries() +
                self.heap.get_active_survivor().list_entries()
            )

        return [
            e for e in entries
            if min_quality <= e.quality_score <= max_quality
        ]

    # ==================== 上下文装配 ====================

    def get_context_for_llm(self, role: str = "developer", max_tokens: int = 4000) -> str:
        """
        为 LLM 装配上下文（渐进式披露）

        流程:
        1. Permanent (核心知识) - 全量注入
        2. Survivor (当前任务) - 注入
        3. Old (文档) - 按热点和相关性注入
        4. Eden (会话) - 最近 N 条

        Args:
            role: 目标角色
            max_tokens: 最大 Token 数

        Returns:
            装配好的上下文字符串
        """
        sections = []
        current_tokens = 0

        # 0. 核心 API 指导（始终注入）
        api_guide = """# HarnessGenJ 核心 API 指南

## 初始化（已完成）
```python
from harnessgenj import Harness
harness = Harness("项目名")  # 默认持久化到 .harnessgenj/ 目录
```

## 核心方法

### 1. 接收用户请求
```python
# 用户提出需求或Bug
result = harness.receive_request("实现用户登录功能", request_type="feature")  # 功能需求
result = harness.receive_request("登录页面报错", request_type="bug")  # Bug报告
# 返回: {"task_id": "TASK-xxx", "priority": "P1", "assignee": "developer"}
```

### 2. 记忆管理
```python
harness.remember("key", "重要信息", important=True)  # 存储核心知识
harness.recall("key")  # 获取知识
harness.record("开发日志内容", context="开发过程")  # 记录到文档
```

### 3. 对话记录
```python
harness.chat("用户消息")  # 自动记录并识别需求/Bug
harness.chat("AI回复", role="assistant")
```

### 4. 任务完成
```python
harness.complete_task("TASK-xxx", "完成摘要")  # 标记任务完成
```

### 5. 状态查询
```python
status = harness.get_status()  # 获取项目状态
report = harness.get_report()  # 获取项目报告
context = harness.get_context_prompt()  # 获取上下文（每次对话开始时调用）
```

## 自动处理规则
- 用户说"需要/要/添加功能" → 自动调用 receive_request("...", "feature")
- 用户说"bug/问题/错误" → 自动调用 receive_request("...", "bug")
- 所有操作自动持久化，重启后自动恢复

"""
        sections.append(api_guide)
        current_tokens += self._estimate_tokens(api_guide)

        # 1. Permanent - 项目信息
        project_section = f"\n# 项目信息\n- 名称: {self.project_info.name}\n- 技术栈: {self.project_info.tech_stack}\n- 状态: {self.project_info.status}\n"
        sections.append(project_section)
        current_tokens += self._estimate_tokens(project_section)

        # Permanent - 核心知识
        for entry in self.heap.permanent.list_entries():
            if current_tokens < max_tokens * 0.3:
                sections.append(f"\n## {entry.id}\n{entry.content}")
                current_tokens += self._estimate_tokens(entry.content)

        # 2. Survivor - 当前任务
        if self._current_task:
            task_section = f"\n# 当前任务\n- ID: {self._current_task.get('task_id', '')}\n- 描述: {self._current_task.get('request', self._current_task.get('desc', ''))}\n- 状态: {self._current_task.get('status', '')}\n"
            sections.append(task_section)
            current_tokens += self._estimate_tokens(task_section)

        # 3. Old - 按热点加载文档
        hotspots = self.hotspot.detect_hotspots()
        for hotspot in hotspots[:3]:
            if current_tokens < max_tokens * 0.8:
                doc = self.get_document(hotspot.name)
                if doc:
                    summary = doc[:500] + "..." if len(doc) > 500 else doc
                    sections.append(f"\n## {hotspot.name}\n{summary}")
                    current_tokens += self._estimate_tokens(summary)

        # 4. Eden - 最近消息
        if current_tokens < max_tokens * 0.9:
            for msg in self.get_recent_messages(5):
                msg_text = f"\n[{msg['role']}]: {msg['content'][:200]}"
                sections.append(msg_text)
                current_tokens += self._estimate_tokens(msg_text)

        # 5. 项目统计
        stats_section = f"\n# 项目统计\n- 功能: {self.project_stats.features_completed}/{self.project_stats.features_total}\n- Bug: {self.project_stats.bugs_fixed}/{self.project_stats.bugs_total}\n- 进度: {self.project_stats.progress}%\n"
        sections.append(stats_section)

        return "\n".join(sections)

    def get_minimal_context(self) -> str:
        """获取最小上下文（仅项目信息）"""
        return f"# 项目信息\n- 名称: {self.project_info.name}\n- 技术栈: {self.project_info.tech_stack}\n"

    # ==================== GC 和热点检测 ====================

    def _maybe_gc(self) -> GCResult | None:
        """检查并触发 GC"""
        if self.heap.eden.is_full():
            result = self.gc.minor_gc(self.heap)
            self.heap.swap_survivor()
            return result
        if self.heap.old.is_full():
            return self.gc.major_gc(self.heap)
        return None

    def force_gc(self, gc_type: str = "minor") -> GCResult:
        """强制触发 GC"""
        if gc_type == "minor":
            result = self.gc.minor_gc(self.heap)
            self.heap.swap_survivor()
        elif gc_type == "major":
            result = self.gc.major_gc(self.heap)
        else:
            result = self.gc.full_gc(self.heap)
        return result

    def get_hotspots(self) -> list[HotspotInfo]:
        """获取热点数据"""
        return self.hotspot.detect_hotspots()

    # ==================== 统计和状态 ====================

    def update_stats(self, stat_type: str, delta: int = 1) -> None:
        """更新统计"""
        if stat_type == "features_total":
            self.project_stats.features_total += delta
        elif stat_type == "features_completed":
            self.project_stats.features_completed += delta
        elif stat_type == "bugs_total":
            self.project_stats.bugs_total += delta
        elif stat_type == "bugs_fixed":
            self.project_stats.bugs_fixed += delta

        # 重新计算进度
        total = self.project_stats.features_total + self.project_stats.bugs_total
        completed = self.project_stats.features_completed + self.project_stats.bugs_fixed
        self.project_stats.progress = int(completed / total * 100) if total > 0 else 0

        self._save()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "project": self.project_info.model_dump(),
            "stats": self.project_stats.model_dump(),
            "memory": {
                "eden_size": self.heap.eden.size(),
                "survivor_size": self.heap.get_active_survivor().size(),
                "old_size": self.heap.old.size(),
                "permanent_size": self.heap.permanent.size(),
            },
            "hotspots": len(self.get_hotspots()),
        }

    def get_project_info(self) -> dict[str, Any]:
        """获取项目基本信息"""
        return self.project_info.model_dump()

    def get_document_summary(self, doc_type: str) -> str:
        """获取文档摘要"""
        doc = self.get_document(doc_type)
        if not doc:
            return ""
        # 取前500字符作为摘要
        return doc[:500] + "..." if len(doc) > 500 else doc

    def list_documents(self) -> list[dict[str, Any]]:
        """列出所有文档"""
        doc_dir = os.path.join(self.workspace, "documents")
        if not os.path.exists(doc_dir):
            return []

        result = []
        for doc_type in [DocumentType.REQUIREMENTS, DocumentType.DESIGN,
                         DocumentType.DEVELOPMENT, DocumentType.TESTING, DocumentType.PROGRESS]:
            doc_path = os.path.join(doc_dir, f"{doc_type}.md")
            if os.path.exists(doc_path):
                ownership = DOCUMENT_OWNERSHIP.get(doc_type, {})
                result.append({
                    "type": doc_type,
                    "owner": ownership.get("owner", "project_manager"),
                    "exists": True,
                    "path": doc_path,
                })
        return result

    def get_context_for_role(self, role_type: str) -> dict[str, Any]:
        """
        为角色生成最小必要上下文（渐进式披露）

        使用 DOCUMENT_OWNERSHIP 配置进行访问控制

        Args:
            role_type: 角色类型

        Returns:
            角色特定的上下文
        """
        # 项目基本信息（所有角色都可见）
        context: dict[str, Any] = {
            "project": {
                "name": self.project_info.name,
                "tech_stack": self.project_info.tech_stack,
                "status": self.project_info.status,
            },
            "stats": self.project_stats.model_dump(),
        }

        # 添加角色质量信息（如果质量系统已链接）
        if self._score_manager:
            try:
                role_score = self._score_manager.get_score_by_role_type(role_type)
                if role_score:
                    context["role_quality"] = {
                        "score": role_score.score,
                        "grade": role_score.grade,
                        "success_rate": role_score.success_rate,
                    }
            except Exception as e:
                logger.debug(f"Failed to get role score: {e}")

        # 使用 DOCUMENT_OWNERSHIP 配置进行文档访问控制
        context["documents"] = {}
        context["documents_summary"] = {}

        for doc_type, ownership in DOCUMENT_OWNERSHIP.items():
            visible_to = ownership.get("visible_to", [])
            read_only_for = ownership.get("read_only_for", [])
            owner = ownership.get("owner", "")

            # 判断角色是否有权限访问此文档
            has_access = (
                role_type == "project_manager"  # 项目经理有全部访问权限
                or role_type == owner
                or role_type in visible_to
            )

            if has_access:
                doc = self.get_document(doc_type)
                if doc:
                    # 判断是否应该提供完整文档
                    # 1. 是文档的 owner
                    # 2. 是项目经理
                    # 3. 在 read_only_for 列表中（可以看完整内容，但不能修改）
                    can_read_full = (
                        role_type == owner
                        or role_type == "project_manager"
                        or role_type in read_only_for
                    )

                    if can_read_full:
                        context["documents"][doc_type] = doc
                    else:
                        # 其他 visible_to 角色只获取摘要
                        context["documents_summary"][doc_type] = self.get_document_summary(doc_type)

        # 设置权限标志
        context["full_access"] = role_type == "project_manager"
        context["is_owner_for"] = [
            doc_type for doc_type, ownership in DOCUMENT_OWNERSHIP.items()
            if ownership.get("owner") == role_type
        ]

        # 判别器角色的特殊处理：添加质量历史
        if role_type == "code_reviewer":
            if self._quality_tracker:
                try:
                    recent_reviews = self._quality_tracker.get_recent_reviews(limit=10)
                    context["recent_reviews"] = recent_reviews
                except Exception as e:
                    logger.debug(f"Failed to get recent reviews: {e}")

        elif role_type == "bug_hunter":
            if self._quality_tracker:
                try:
                    failed_reviews = self._quality_tracker.get_failed_reviews(limit=10)
                    context["historical_issues"] = failed_reviews
                except Exception as e:
                    logger.debug(f"Failed to get failed reviews: {e}")

        # 优先加载高质量内容（从 Old 区）
        high_quality_entries = self._get_high_quality_entries()
        if high_quality_entries:
            context["high_quality_content"] = [
                {"id": e.id, "content": e.content[:200], "quality_score": e.quality_score}
                for e in high_quality_entries[:5]
            ]

        return context

    def _get_high_quality_entries(self, threshold: float = 70.0) -> list[MemoryEntry]:
        """获取高质量条目"""
        entries = self.heap.old.list_entries()
        return [e for e in entries if e.quality_score >= threshold]

    def get_project_summary(self) -> str:
        """获取项目总摘要"""
        summary_lines = [
            f"# {self.project_info.name}",
            "",
            f"**状态**: {self.project_info.status}",
            f"**技术栈**: {self.project_info.tech_stack}",
            "",
            "## 进度",
            f"- 功能: {self.project_stats.features_completed}/{self.project_stats.features_total}",
            f"- Bug: {self.project_stats.bugs_fixed}/{self.project_stats.bugs_total}",
            f"- 总进度: {self.project_stats.progress}%",
        ]

        # 添加各文档摘要
        for doc_type in [DocumentType.REQUIREMENTS, DocumentType.DESIGN,
                         DocumentType.DEVELOPMENT, DocumentType.TESTING]:
            doc = self.get_document(doc_type)
            if doc:
                summary_lines.append("")
                summary_lines.append(f"## {doc_type.upper()}")
                summary_lines.append(self.get_document_summary(doc_type)[:200] + "...")

        return "\n".join(summary_lines)

    def get_health_report(self) -> dict[str, Any]:
        """获取健康报告"""
        eden_pressure = self.heap.eden.size() / self.heap.eden.max_size
        old_pressure = self.heap.old.size() / self.heap.old.max_size

        if eden_pressure > 0.9 or old_pressure > 0.9:
            status = "critical"
        elif eden_pressure > 0.7 or old_pressure > 0.7:
            status = "warning"
        else:
            status = "healthy"

        return {"status": status}

    # ==================== 持久化 ====================

    def _save(self) -> None:
        """保存状态"""
        try:
            # 保存项目信息
            project_path = os.path.join(self.workspace, "project.json")
            with open(project_path, "w", encoding="utf-8") as f:
                json.dump({
                    "info": self.project_info.model_dump(),
                    "stats": self.project_stats.model_dump(),
                }, f, ensure_ascii=False, indent=2)

            # 保存当前任务
            if self._current_task:
                current_task_path = os.path.join(self.workspace, "current_task.json")
                with open(current_task_path, "w", encoding="utf-8") as f:
                    json.dump(self._current_task, f, ensure_ascii=False, indent=2)

            # 保存 Permanent 区知识
            knowledge_path = os.path.join(self.workspace, "knowledge.json")
            knowledge_data = {}
            for entry in self.heap.permanent.list_entries():
                knowledge_data[entry.id] = {
                    "content": entry.content,
                    "importance": entry.importance,
                }
            with open(knowledge_path, "w", encoding="utf-8") as f:
                json.dump(knowledge_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save knowledge data: {e}")

    def _save_document(self, doc_type: str, content: str) -> None:
        """保存文档"""
        try:
            doc_path = os.path.join(self.workspace, "documents", f"{doc_type}.md")
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Failed to save document '{doc_type}': {e}")

    def _load(self) -> None:
        """加载持久化数据"""
        # 加载项目信息
        project_path = os.path.join(self.workspace, "project.json")
        if os.path.exists(project_path):
            try:
                with open(project_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.project_info = ProjectInfo(**data.get("info", {}))
                self.project_stats = ProjectStats(**data.get("stats", {}))
            except Exception as e:
                logger.warning(f"Failed to load project info: {e}")

        # 加载当前任务
        current_task_path = os.path.join(self.workspace, "current_task.json")
        if os.path.exists(current_task_path):
            try:
                with open(current_task_path, "r", encoding="utf-8") as f:
                    self._current_task = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load current task: {e}")

        # 加载 Permanent 区知识
        knowledge_path = os.path.join(self.workspace, "knowledge.json")
        if os.path.exists(knowledge_path):
            try:
                with open(knowledge_path, "r", encoding="utf-8") as f:
                    knowledge_data = json.load(f)
                for key, value in knowledge_data.items():
                    self.heap.permanent.store_knowledge(
                        key,
                        value.get("content", ""),
                        value.get("importance", 100)
                    )
            except Exception as e:
                logger.warning(f"Failed to load knowledge data: {e}")

        # 加载文档
        doc_dir = os.path.join(self.workspace, "documents")
        if os.path.exists(doc_dir):
            for doc_type in ["requirements", "design", "development", "testing", "progress"]:
                doc_path = os.path.join(doc_dir, f"{doc_type}.md")
                if os.path.exists(doc_path):
                    try:
                        with open(doc_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        self.store_document(doc_type, content)
                    except Exception as e:
                        logger.warning(f"Failed to load document '{doc_type}': {e}")

    def reload(self) -> bool:
        """重新加载"""
        self._load()
        return True

    def _estimate_tokens(self, content: str) -> int:
        """估算 Token 数"""
        import re
        if not content:
            return 0

        chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
        other = len(content) - chinese

        return int(chinese / 1.5) + int(other / 4)

    # ==================== 结构化知识接口 ====================

    def store_structured_knowledge(self, entry: KnowledgeEntry) -> str:
        """
        存储结构化知识

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        return self.structured.store(entry)

    def get_structured_knowledge(self, entry_id: str) -> KnowledgeEntry | None:
        """
        获取结构化知识

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目
        """
        return self.structured.get(entry_id)

    def query_knowledge_by_type(self, knowledge_type: KnowledgeType) -> list[KnowledgeEntry]:
        """
        按类型查询知识

        Args:
            knowledge_type: 知识类型

        Returns:
            知识条目列表
        """
        return self.structured.query_by_type(knowledge_type)

    def query_knowledge_by_tags(self, tags: list[str], match_all: bool = False) -> list[KnowledgeEntry]:
        """
        按标签查询知识

        Args:
            tags: 标签列表
            match_all: 是否需要匹配所有标签

        Returns:
            知识条目列表
        """
        return self.structured.query_by_tags(tags, match_all)

    def query_knowledge_by_file(self, file_path: str) -> list[KnowledgeEntry]:
        """
        按文件查询知识

        Args:
            file_path: 文件路径

        Returns:
            知识条目列表
        """
        return self.structured.query_by_file(file_path)

    def search_structured_knowledge(self, query: str) -> list[KnowledgeEntry]:
        """
        搜索结构化知识

        Args:
            query: 搜索关键词

        Returns:
            匹配的知识条目列表
        """
        return self.structured.search(query)

    def get_knowledge_stats(self) -> dict[str, Any]:
        """获取知识库统计信息"""
        return self.structured.get_stats()


# 便捷函数
def create_memory_manager(workspace: str = ".harnessgenj") -> MemoryManager:
    """创建记忆管理器"""
    return MemoryManager(workspace)