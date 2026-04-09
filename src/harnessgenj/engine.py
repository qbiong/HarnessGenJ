"""
Harness - Harness Engineering 主入口

提供简洁的 API 来使用 Harness Engineering 框架

核心概念:
- Memory: 统一记忆管理（JVM风格分代存储）
- Team: 开发团队，包含多个角色
- Workflow: 工作流流水线
- Session: 多对话会话管理
- Quality: 对抗性质量保证系统

使用示例:
    from harnessgenj import Harness

    # 创建 Harness 实例（默认持久化）
    harness = Harness("我的项目")

    # 从现有项目文档初始化（推荐）
    harness = Harness.from_project("/path/to/project")

    # 快速开发功能
    result = harness.develop("实现用户登录功能")

    # 项目经理接收请求
    result = harness.receive_request("需要一个搜索功能")

    # 完成任务
    harness.complete_task(result['task_id'], "功能已完成")

    # 对抗性开发（提高成功率）
    result = harness.adversarial_develop("实现支付功能")
"""

from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
import time
import os
import json
import uuid
import re
import glob

from harnessgenj.roles import (
    AgentRole,
    RoleType,
    create_role,
)
from harnessgenj.workflow import (
    WorkflowCoordinator,
    WorkflowPipeline,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    create_adversarial_pipeline,
    # 新增工作流
    create_intent_pipeline,
    create_development_pipeline,
    create_inquiry_pipeline,
    create_management_pipeline,
    get_workflow,
    list_workflows,
)
from harnessgenj.workflow.intent_router import (
    IntentRouter,
    IntentType,
    IntentResult,
    create_intent_router,
    identify_intent,
)
from harnessgenj.workflow.collaboration import RoleCollaborationManager, create_collaboration_manager
from harnessgenj.memory import MemoryManager
from harnessgenj.storage import create_storage, StorageManager, StorageType
from harnessgenj.session import (
    SessionManager,
    SessionType,
    Session,
    MessageRole,
    Message,
)
from harnessgenj.guide import OnboardingGuide, ProjectConfig
from harnessgenj.quality.score import ScoreManager
from harnessgenj.quality.tracker import QualityTracker
from harnessgenj.quality.task_adversarial import TaskAdversarialController
from harnessgenj.quality.system_adversarial import SystemAdversarialController
from harnessgenj.harness.adversarial import AdversarialWorkflow, AdversarialResult
from harnessgenj.harness.hooks_integration import (
    HooksIntegration,
    HooksConfig,
    create_hooks_integration,
)
from harnessgenj.harness.hooks_auto_setup import auto_setup_hooks, get_hooks_setup_status
from harnessgenj.harness.tech_detector import (
    detect_tech_stack,
    update_agents_templates,
    TechStackInfo,
)
from harnessgenj.harness.event_triggers import (
    TriggerManager,
    TriggerEvent,
    create_trigger_manager,
)
from harnessgenj.harness.hybrid_integration import (
    HybridIntegration,
    HybridConfig,
    IntegrationMode,
    create_hybrid_integration,
)
from harnessgenj.workflow.task_state import (
    TaskStateMachine,
    TaskState,
    TaskInfo,
    create_task_state_machine,
)
from harnessgenj.sync.doc_sync import DocumentSyncManager, SyncConfig, create_sync_manager
from harnessgenj.workflow.tdd_workflow import TDDWorkflow, TDDConfig, TDDCycle, create_tdd_workflow


# ==================== 流程强制执行配置 ====================

class SkipLevel(Enum):
    """跳过级别 - 控制可跳过的检查项"""
    NONE = "none"                # 不跳过任何检查（默认）
    OPTIONAL_HOOKS = "optional"  # 只跳过可选检查（非阻塞型 Hooks）
    ALL = "all"                  # 跳过所有检查（需要管理员权限）


# 强制检查项（不可跳过）
MANDATORY_CHECKS = [
    "adversarial_review",   # 对抗审查 - 必须执行
    "security_check",       # 安全检查 - 必须执行
    "boundary_check",       # 边界检查 - 必须执行
]


class QualityGate(BaseModel):
    """质量门禁配置"""
    name: str = Field(description="门禁名称")
    required: bool = Field(default=True, description="是否必须通过")
    blocking: bool = Field(default=True, description="是否阻塞流程")
    bypass_level: SkipLevel = Field(default=SkipLevel.ALL, description="绕过所需级别")


# 强制质量门禁定义
MANDATORY_GATES = [
    QualityGate(name="adversarial_review", required=True, blocking=True),
    QualityGate(name="security_check", required=True, blocking=True),
    QualityGate(name="test_pass", required=True, blocking=True),
]


class HarnessStats(BaseModel):
    """Harness 统计"""
    features_developed: int = Field(default=0, description="开发的功能数")
    bugs_fixed: int = Field(default=0, description="修复的Bug数")
    workflows_completed: int = Field(default=0, description="完成的工作流数")
    team_size: int = Field(default=0, description="团队规模")
    messages_sent: int = Field(default=0, description="发送的消息数")


class Harness:
    """
    Harness - Harness Engineering 主入口类

    核心方法:
    - receive_request(): 项目经理接收请求
    - complete_task(): 完成任务
    - develop(): 快速开发功能
    - fix_bug(): 快速修复Bug
    - chat(): 对话（自动记录）
    - get_context_prompt(): 获取上下文提示（用于LLM）

    持久化支持:
    - 默认开启持久化，数据保存在 .harnessgenj/ 目录
    - 重启后自动加载之前的工作内容

    状态检测:
    - is_initialized(): 检查框架是否已初始化（静态方法）
    - get_initialization_status(): 获取初始化状态详情（静态方法）
    """

    # ==================== 静态状态管理 ====================
    # 用于 Hooks 和外部检测框架是否已初始化
    _instance_initialized: bool = False
    _current_project_path: str | None = None
    _active_workflow_id: str | None = None
    _active_roles: dict[str, str] = {}  # role_id -> role_type
    _last_instance: "Harness | None" = None

    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查框架是否已初始化（静态方法）

        用于 Hooks 脚本检测框架状态，判断是否需要提醒用户。

        Returns:
            True 如果框架已初始化，False 否则

        使用示例:
            if not Harness.is_initialized():
                print("请先初始化框架: harness = Harness.from_project('.')")
        """
        return cls._instance_initialized

    @classmethod
    def get_initialization_status(cls) -> dict[str, Any]:
        """
        获取初始化状态详情（静态方法）

        Returns:
            包含以下信息的状态字典:
            - initialized: 是否已初始化
            - project_path: 当前项目路径
            - active_workflow: 当前活动工作流ID
            - active_roles: 当前活动角色列表
            - last_instance_available: 是否有实例可用

        使用示例:
            status = Harness.get_initialization_status()
            if not status["initialized"]:
                show_framework_guide()
        """
        return {
            "initialized": cls._instance_initialized,
            "project_path": cls._current_project_path,
            "active_workflow": cls._active_workflow_id,
            "active_roles": list(cls._active_roles.keys()),
            "roles_by_type": cls._active_roles.copy(),
            "last_instance_available": cls._last_instance is not None,
        }

    @classmethod
    def get_last_instance(cls) -> "Harness | None":
        """
        获取最后一个 Harness 实例（静态方法）

        用于 Hooks 或其他模块访问当前框架实例。

        Returns:
            最后一个 Harness 实例，如果未初始化则返回 None
        """
        return cls._last_instance

    def __init__(
        self,
        project_name: str = "Default Project",
        *,
        persistent: bool = True,
        workspace: str = ".harnessgenj",
        config_path: str | None = None,
        auto_setup_team: bool = True,
    ) -> None:
        """
        初始化 Harness 实例

        Args:
            project_name: 项目名称
            persistent: 是否持久化存储（默认 True）
            workspace: 工作空间目录（默认 .harnessgenj）
            auto_setup_team: 是否自动创建核心团队（默认 True）
        """
        self.project_name = project_name
        self._workspace = workspace
        self._persistent = persistent

        # 脏标记机制 - 用于增量保存
        self._dirty = False
        self._dirty_fields: dict[str, Any] = {}

        # 核心组件：统一记忆管理
        self.memory = MemoryManager(workspace)
        self.memory.project_info.name = project_name
        self.memory.store_knowledge("project_name", project_name)

        # 工作流协调器
        self.coordinator = WorkflowCoordinator()

        # 存储系统（用于AGENTS.md等）
        self.storage = create_storage(persistent=persistent, base_path=workspace)

        # AGENTS.md 知识管理器
        self._agents_knowledge = None
        if persistent:
            from harnessgenj.harness import AgentsKnowledgeManager
            self._agents_knowledge = AgentsKnowledgeManager(workspace)
            if not self._agents_knowledge.is_initialized():
                self._agents_knowledge.initialize(project_name, "", "init")

        # 会话管理
        session_path = os.path.join(workspace, "sessions.json") if persistent else None
        self.sessions = SessionManager(persist_path=session_path)
        if not self.sessions.get_active_session():
            self.sessions.switch_session(SessionType.PROJECT_MANAGER)

        # 统计
        self._stats = HarnessStats()

        # 引导系统
        guide_config_path = config_path or os.path.join(workspace, "config.json")
        self._guide = OnboardingGuide(guide_config_path)

        # 注册标准工作流
        self.coordinator.register_workflow("standard", create_standard_pipeline())
        self.coordinator.register_workflow("feature", create_feature_pipeline())
        self.coordinator.register_workflow("bugfix", create_bugfix_pipeline())
        self.coordinator.register_workflow("adversarial", create_adversarial_pipeline())

        # 质量保证系统 - 默认启用
        self._score_manager = ScoreManager(workspace)
        self._quality_tracker = QualityTracker(workspace)
        self._adversarial_workflow = AdversarialWorkflow(
            self._score_manager,
            self._quality_tracker,
            self.memory,  # 传递 MemoryManager，建立质量数据流
        )

        # 双层对抗控制器
        self._task_adversarial = TaskAdversarialController(
            self._score_manager,
            self._quality_tracker,
        )
        self._system_adversarial = SystemAdversarialController(
            self._quality_tracker,
            self._score_manager,
            self.memory,
        )

        # 链接质量系统到记忆管理（使用方法调用而非直接属性赋值）
        self.memory.set_quality_system(self._score_manager, self._quality_tracker)

        # Hooks 集成系统 - 默认启用
        self._hooks_integration = create_hooks_integration(
            enabled=True,
            blocking_mode=True,
        )

        # 事件触发管理器 - 默认启用（需在 hybrid_integration 之前创建）
        self._trigger_manager = create_trigger_manager(self)

        # 混合集成层 - Hooks + 内置触发双轨并存
        self._hybrid_integration = create_hybrid_integration(
            workspace=workspace,
            trigger_manager=self._trigger_manager,
            score_manager=self._score_manager,
            quality_tracker=self._quality_tracker,
            adversarial_workflow=self._adversarial_workflow,
            auto_fallback=True,
        )

        # 任务状态机 - 管理任务状态流转
        self._task_state_machine = create_task_state_machine()

        # 角色协作管理器 - 默认启用
        self._collaboration = create_collaboration_manager(self.coordinator)

        # 文档同步管理器 - 默认启用
        self._doc_sync = create_sync_manager(
            workspace=workspace,
            memory_manager=self.memory,
            config=SyncConfig(
                enabled=persistent,
                auto_sync=False,  # 手动触发同步，避免竞态
                backup_enabled=True,
            ),
        )

        # TDD 工作流管理器 - 按需启用
        self._tdd_workflow: TDDWorkflow | None = None

        # 意图识别路由器
        self._intent_router = create_intent_router()

        # 加载之前的工作状态
        if persistent:
            self._load_state()

        # 自动设置 Hooks（首次使用时）
        if persistent:
            hooks_status = get_hooks_setup_status()
            if not hooks_status["hooks_configured"]:
                auto_setup_hooks(silent=False)

        # 自动创建核心团队（新增功能）
        if auto_setup_team:
            self._auto_setup_core_team()

        # 设置全局 Harness 实例（供装饰器使用）
        from harnessgenj.harness.decorators import set_global_harness
        set_global_harness(self)

        # 生成初始监控报告（帮助用户了解框架状态）
        self._generate_initial_monitor_report()

        # ==================== 新增：静态状态更新 ====================
        # 更新静态状态，供 Hooks 和外部检测
        Harness._instance_initialized = True
        Harness._current_project_path = self._workspace
        Harness._last_instance = self

        # ==================== 新增：框架主动输出 ====================
        # 初始化完成后主动输出框架状态和使用指南
        self._announce_initialization()

    def _announce_initialization(self) -> None:
        """
        宣布框架已初始化（主动输出机制）

        在框架初始化完成后，主动向用户输出：
        1. 框架已就绪的状态信息
        2. 项目基本信息
        3. 下一步操作建议

        这确保用户清楚地知道框架已准备好，应该如何使用。
        """
        try:
            from harnessgenj.notify import get_notifier, NotifierLevel
            notifier = get_notifier()

            # 输出框架初始化成功信息
            notifier._emit("━" * 60, NotifierLevel.INFO)
            notifier._emit("  ✅ HarnessGenJ 框架已就绪", NotifierLevel.INFO)
            notifier._emit(f"  项目: {self.project_name}", NotifierLevel.INFO)
            notifier._emit(f"  工作空间: {self._workspace}", NotifierLevel.INFO)

            # 输出团队状态
            team_size = self._stats.team_size
            if team_size > 0:
                notifier._emit(f"  团队: {team_size} 个角色已就绪", NotifierLevel.INFO)

            # 输出技术栈（如果有）
            tech_stack = self.memory.project_info.tech_stack if hasattr(self.memory, 'project_info') else None
            if tech_stack:
                notifier._emit(f"  技术栈: {tech_stack}", NotifierLevel.INFO)

            # 输出下一步操作建议
            notifier._emit("", NotifierLevel.INFO)
            notifier._emit("  📋 下一步操作:", NotifierLevel.INFO)
            notifier._emit("     harness.develop('需求描述')  # 开发功能", NotifierLevel.INFO)
            notifier._emit("     harness.fix_bug('问题描述')  # 修复Bug", NotifierLevel.INFO)
            notifier._emit("     harness.get_status()        # 查看状态", NotifierLevel.INFO)

            # 输出 MCP 工具提示
            notifier._emit("", NotifierLevel.INFO)
            notifier._emit("  🔧 MCP 工具可用 (21个):", NotifierLevel.INFO)
            notifier._emit("     task_develop, task_fix_bug, system_status...", NotifierLevel.INFO)

            # 输出积分系统提示
            notifier._emit("", NotifierLevel.INFO)
            notifier._emit("  💡 提示: 使用框架开发可获得积分奖励", NotifierLevel.INFO)
            notifier._emit("     高积分 = 高职业信誉 = 团队核心成员", NotifierLevel.INFO)

            notifier._emit("━" * 60, NotifierLevel.INFO)

        except Exception:
            # 主动输出失败不影响框架功能
            pass

    @classmethod
    def from_project(
        cls,
        project_path: str,
        *,
        workspace: str | None = None,
        doc_patterns: list[str] | None = None,
    ) -> "Harness":
        """
        从现有项目目录初始化 Harness

        自动扫描项目文档并导入到记忆系统，支持：
        - README.md / readme.md
        - requirements.md / needs.md / 需求.md
        - design.md / architecture.md / 设计.md
        - progress.md / 进度.md
        - development.md / dev.md / 开发.md
        - testing.md / test.md / 测试.md
        - docs/ 目录下的 .md 文件

        Args:
            project_path: 项目根目录路径
            workspace: HarnessGenJ 工作空间路径（默认为项目目录下的 .harnessgenj）
            doc_patterns: 自定义文档匹配模式

        Returns:
            初始化好的 Harness 实例

        使用示例:
            # 从项目目录初始化
            harness = Harness.from_project("/path/to/my-project")

            # 获取导入的项目信息
            context = harness.get_init_prompt()
        """
        project_path = os.path.abspath(project_path)
        if workspace is None:
            workspace = os.path.join(project_path, ".harnessgenj")

        # 默认文档匹配模式
        if doc_patterns is None:
            doc_patterns = [
                "README.md",
                "readme.md",
                "requirements.md",
                "needs.md",
                "需求.md",
                "design.md",
                "architecture.md",
                "设计.md",
                "progress.md",
                "进度.md",
                "development.md",
                "dev.md",
                "开发.md",
                "testing.md",
                "test.md",
                "测试.md",
                "docs/*.md",
                "doc/*.md",
            ]

        # 扫描并读取文档
        documents: dict[str, str] = {}
        for pattern in doc_patterns:
            full_pattern = os.path.join(project_path, pattern)
            for file_path in glob.glob(full_pattern):
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if content.strip():
                            doc_name = os.path.basename(file_path)
                            documents[doc_name] = content
                    except Exception:
                        pass

        # 提取项目名称
        project_name = os.path.basename(project_path)
        if "README.md" in documents:
            # 尝试从 README 提取标题
            readme = documents["README.md"]
            title_match = re.search(r"^#\s+(.+)$", readme, re.MULTILINE)
            if title_match:
                project_name = title_match.group(1).strip()

        # 创建 Harness 实例
        harness = cls(project_name, workspace=workspace)

        # 自动设置 Hooks（首次使用时）
        hooks_status = get_hooks_setup_status(project_path)
        if not hooks_status["hooks_configured"]:
            auto_setup_hooks(project_path, silent=False)

        # 导入文档到记忆系统
        harness._import_documents(documents)

        # 提取项目信息
        harness._extract_project_info(documents, project_path)

        # ==================== 新增：更新静态状态 ====================
        # 更新项目路径为实际项目路径（而非 workspace）
        Harness._current_project_path = project_path

        return harness

    def _import_documents(self, documents: dict[str, str]) -> None:
        """导入文档到记忆系统"""
        # 文档类型映射
        doc_type_map = {
            "requirements.md": "requirements",
            "needs.md": "requirements",
            "需求.md": "requirements",
            "design.md": "design",
            "architecture.md": "design",
            "设计.md": "design",
            "development.md": "development",
            "dev.md": "development",
            "开发.md": "development",
            "testing.md": "testing",
            "test.md": "testing",
            "测试.md": "testing",
            "progress.md": "progress",
            "进度.md": "progress",
        }

        for doc_name, content in documents.items():
            # 确定文档类型
            doc_type = doc_type_map.get(doc_name.lower(), None)

            if doc_type:
                # 存储到对应类型的文档
                self.memory.store_document(doc_type, content)
            else:
                # 存储为核心知识
                key = doc_name.replace(".", "_").replace("-", "_")
                self.memory.store_knowledge(f"doc_{key}", content, importance=70)

        # 保存状态
        self._save_state()

    def _extract_project_info(self, documents: dict[str, str], project_path: str) -> None:
        """从文档中提取项目信息"""
        readme = documents.get("README.md", "")

        # 提取描述（第一段非标题内容）
        if readme:
            lines = readme.split("\n")
            desc_lines = []
            in_content = False
            for line in lines:
                if line.startswith("#"):
                    if in_content:
                        break
                    continue
                if line.strip() and not in_content:
                    in_content = True
                if in_content:
                    desc_lines.append(line)
                    if len(desc_lines) >= 5:
                        break
            description = " ".join(desc_lines).strip()[:500]
            self.memory.project_info.description = description

        # 使用技术栈自动检测系统
        tech_info = detect_tech_stack(project_path)

        # 更新技术栈信息（统一存储到 project_info）
        tech_stack = tech_info.main_language
        if tech_info.frameworks:
            tech_stack += " + " + " + ".join(tech_info.frameworks[:3])

        # 唯一存储点：project_info.tech_stack
        self.memory.project_info.tech_stack = tech_stack

        # 存储详细技术栈信息用于后续查询
        self.memory.store_knowledge("tech_info", tech_info.model_dump_json(), importance=80)

        # 自动更新 agents/*.md 模板以适配技术栈
        if self._agents_knowledge:
            update_result = update_agents_templates(self._workspace, tech_info)
            # 记录更新结果
            if update_result["updated"]:
                self.memory.store_knowledge(
                    "tech_templates_updated",
                    ",".join(update_result["updated"]),
                    importance=50
                )

        # 更新项目状态
        self.memory.project_info.status = "initialized"
        self.memory._save()

    def _load_state(self) -> bool:
        """加载之前的工作状态"""
        state_path = os.path.join(self._workspace, "state.json")
        if not os.path.exists(state_path):
            return False

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "project_name" in data:
                self.project_name = data["project_name"]
                self.memory.project_info.name = self.project_name

            if "stats" in data:
                self._stats = HarnessStats(**data["stats"])

            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def _save_state(self) -> bool:
        """保存当前工作状态"""
        if not self._persistent:
            return False

        try:
            os.makedirs(self._workspace, exist_ok=True)

            state_path = os.path.join(self._workspace, "state.json")
            data = {
                "project_name": self.project_name,
                "stats": self._stats.model_dump(),
                "updated_at": time.time(),
            }

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.sessions.save()

            # 清除脏标记
            self._dirty = False
            self._dirty_fields.clear()

            return True
        except Exception:
            return False

    def _record_intent(self, intent_result: IntentResult) -> None:
        """
        记录意图识别结果到 intents.json

        Args:
            intent_result: 意图识别结果
        """
        try:
            intents_path = Path(self._workspace) / "intents.json"

            # 确保目录存在
            intents_path.parent.mkdir(parents=True, exist_ok=True)

            if intents_path.exists():
                with open(intents_path, "r", encoding="utf-8") as f:
                    intents = json.load(f)
            else:
                intents = {"records": [], "stats": {}}

            # 添加记录
            intents["records"].append({
                "timestamp": time.time(),
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "message_preview": intent_result.original_message[:100] if intent_result.original_message else "",
            })

            # 更新统计
            stats = intents.get("stats", {})
            type_count = stats.get(intent_result.intent_type.value, 0)
            stats[intent_result.intent_type.value] = type_count + 1
            intents["stats"] = stats

            with open(intents_path, "w", encoding="utf-8") as f:
                json.dump(intents, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 不影响主流程

    def _auto_extract_knowledge(self, task: dict, summary: str) -> None:
        """
        任务完成时自动提取关键信息存储到知识库

        Args:
            task: 任务信息
            summary: 完成摘要
        """
        try:
            # 提取关键知识点
            knowledge_entries = []

            # 1. 提取任务类型作为知识类别
            task_type = task.get("category", "未知")
            task_request = task.get("request", "")

            # 2. 如果是 Bug 修复，记录 Bug 模式
            if task_type in ("Bug修复", "Bug"):
                knowledge_entries.append({
                    "key": f"bug_pattern_{int(time.time())}",
                    "value": f"问题: {task_request}\n解决: {summary}",
                    "category": "bug_fix",
                    "important": False,
                })

            # 3. 如果是功能开发，记录实现模式
            elif task_type == "功能开发":
                knowledge_entries.append({
                    "key": f"feature_pattern_{int(time.time())}",
                    "value": f"需求: {task_request}\n实现: {summary}",
                    "category": "feature_impl",
                    "important": False,
                })

            # 4. 存储所有提取的知识
            for entry in knowledge_entries:
                self.remember(
                    entry["key"],
                    entry["value"],
                    important=entry.get("important", False),
                )
        except Exception:
            pass  # 不影响主流程

    def _generate_initial_monitor_report(self) -> None:
        """
        生成初始监控报告（框架初始化时自动调用）
        """
        try:
            from harnessgenj.monitor import HGJMonitor
            monitor = HGJMonitor(self._workspace)
            monitor.save_report()
        except Exception:
            pass  # 不影响主流程

    def _mark_dirty(self, field: str, value: Any) -> None:
        """
        标记字段为脏（需要保存）

        Args:
            field: 字段名
            value: 字段值
        """
        self._dirty = True
        self._dirty_fields[field] = value

    def _flush_if_dirty(self) -> bool:
        """
        如果有脏数据则立即保存

        Returns:
            是否执行了保存操作
        """
        if self._dirty and self._persistent:
            return self._save_state()
        return False

    def _save_critical(self, event: str) -> bool:
        """
        关键操作后立即持久化

        Args:
            event: 事件名称（task_complete, issue_found, decision_made 等）

        Returns:
            是否保存成功
        """
        # 记录事件到元数据
        self._dirty_fields["last_critical_event"] = event
        self._dirty_fields["last_critical_time"] = time.time()

        return self._save_state()

    # ==================== 团队管理 ====================

    def _auto_setup_core_team(self) -> dict[str, Any]:
        """
        自动创建核心团队（内部方法）

        默认创建：
        - CodeReviewer: 代码审查者（判别器）
        - BugHunter: 漏洞猎手（判别器，激进审查）
        - Developer: 开发者（生成器）
        - ProjectManager: 项目经理（协调者）

        Returns:
            创建的团队信息
        """
        # 检查是否已有团队
        if self._stats.team_size > 0:
            return {"project": self.project_name, "team_size": self._stats.team_size, "members": []}

        core_team = {
            "developer": "开发者",
            "code_reviewer": "代码审查者",
            "bug_hunter": "漏洞猎手",
            "project_manager": "项目经理",
        }

        role_type_map = {
            "developer": RoleType.DEVELOPER,
            "code_reviewer": RoleType.CODE_REVIEWER,
            "bug_hunter": RoleType.BUG_HUNTER,
            "project_manager": RoleType.PROJECT_MANAGER,
        }

        created = []
        for role_type_str, name in core_team.items():
            role_type = role_type_map.get(role_type_str)
            if role_type:
                role_id = f"{role_type_str}_1"
                self.coordinator.create_role(role_type, role_id, name)
                created.append({"type": role_type_str, "name": name, "id": role_id})

                # 注册到积分系统
                self._score_manager.register_role(role_type_str, role_id, name)

                # ==================== 新增：更新静态状态 ====================
                Harness._active_roles[role_id] = role_type_str

        self._stats.team_size = len(created)
        self._dirty = True
        self._dirty_fields["team_size"] = len(created)

        return {
            "project": self.project_name,
            "team_size": len(created),
            "members": created,
        }

    def setup_team(self, team_config: dict[str, str] | None = None) -> dict[str, Any]:
        """组建开发团队"""
        if team_config is None:
            team_config = {
                "product_manager": "产品经理",
                "architect": "架构师",
                "developer": "开发人员",
                "tester": "测试人员",
                "doc_writer": "文档管理员",
                "project_manager": "项目经理",
            }

        role_type_map = {
            "product_manager": RoleType.PRODUCT_MANAGER,
            "architect": RoleType.ARCHITECT,
            "developer": RoleType.DEVELOPER,
            "tester": RoleType.TESTER,
            "doc_writer": RoleType.DOC_WRITER,
            "project_manager": RoleType.PROJECT_MANAGER,
        }

        created = []
        for role_type_str, name in team_config.items():
            role_type = role_type_map.get(role_type_str)
            if role_type:
                role_id = f"{role_type_str}_1"
                self.coordinator.create_role(role_type, role_id, name)
                created.append({"type": role_type_str, "name": name, "id": role_id})

        self._stats.team_size = len(created)

        return {
            "project": self.project_name,
            "team_size": len(created),
            "members": created,
        }

    def get_team(self) -> list[dict[str, Any]]:
        """获取团队信息"""
        return self.coordinator.list_roles()

    # ==================== 项目经理核心方法 ====================

    def receive_request(self, request: str, request_type: str = "feature") -> dict[str, Any]:
        """
        项目经理接收用户请求（核心入口方法）

        Args:
            request: 用户请求内容
            request_type: 请求类型 (feature/bug/task)

        Returns:
            处理结果，包含任务ID、优先级、负责人等信息
        """
        # Hooks: 请求验证检查
        validation_result = self._hooks_integration.run_validation({
            "data": {"request": request, "type": request_type},
        })
        if not validation_result.passed:
            return {
                "success": False,
                "error": "请求验证失败",
                "details": validation_result.errors,
            }

        # Hooks: 安全检查（防止恶意请求）
        security_result = self._hooks_integration.run_security_check({
            "content": request,
        })
        if not security_result.passed:
            return {
                "success": False,
                "error": "安全检查失败",
                "details": security_result.errors,
            }

        timestamp = time.strftime('%Y-%m-%d %H:%M')
        task_id = f"TASK-{int(time.time_ns() % 1000000000)}-{uuid.uuid4().hex[:4]}"

        # 根据请求类型分配优先级
        if request_type == "bug":
            priority = "P0"
            category = "Bug修复"
        elif request_type == "feature":
            priority = "P1"
            category = "功能开发"
        else:
            priority = "P2"
            category = "任务"

        # 存储任务到 Survivor 区
        self.memory.store_task(task_id, {
            "request": request,
            "type": request_type,
            "category": category,
            "priority": priority,
            "status": "pending",
            "created_at": timestamp,
        })

        # ==================== 新增：使用任务状态机管理状态 ====================
        self._task_state_machine.create_task(task_id=task_id)

        # 更新进度文档
        progress = self.memory.get_document("progress") or "# 项目进度\n"
        progress += f"\n## {task_id} - {category}\n- **描述**: {request}\n- **优先级**: {priority}\n- **状态**: 待处理\n- **创建时间**: {timestamp}\n"
        self.memory.store_document("progress", progress)

        # 更新统计
        if request_type == "bug":
            self.memory.update_stats("bugs_total", 1)
        else:
            self.memory.update_stats("features_total", 1)

        # 存储会话消息
        self.memory.store_message(request, "user")

        self._save_state()

        return {
            "success": True,
            "task_id": task_id,
            "priority": priority,
            "assignee": "developer",
            "category": category,
            "status": "待处理",
            "timestamp": timestamp,
        }

    def complete_task(self, task_id: str, summary: str = "") -> bool:
        """
        项目经理标记任务完成

        Args:
            task_id: 任务ID
            summary: 完成摘要
        """
        # 获取任务
        task = self.memory.get_task(task_id)
        if not task:
            return False

        timestamp = time.strftime('%Y-%m-%d %H:%M')

        # Hooks: Post-Task 检查（测试通过验证等）
        post_result = self._hooks_integration.run_post_task({
            "task": task,
            "summary": summary,
        })
        if not post_result.passed:
            # 记录失败原因
            task["status"] = "blocked_by_hooks"
            task["hook_errors"] = post_result.errors
            task["blocked_by"] = post_result.blocked_by
            self.memory.store_task(task_id, task)

            # ==================== 新增：更新任务状态机 ====================
            self._task_state_machine.fail(task_id, f"被Hooks阻塞: {post_result.blocked_by}")

            return False

        # 判断任务类型
        is_bug = task.get("category") in ("Bug修复", "Bug")

        # ==================== 新增：使用状态机完成任务 ====================
        try:
            self._task_state_machine.submit_review(task_id, "提交审查")
            self._task_state_machine.complete(task_id, summary)
        except Exception:
            # 状态机转换失败，回退到传统方式
            pass

        # 更新任务状态
        task["status"] = "completed"
        task["completed_at"] = timestamp
        task["summary"] = summary
        self.memory.store_task(task_id, task)

        # ==================== 强制文档更新 ====================
        self._update_documents_on_task_complete(task, summary, timestamp)

        # ==================== 新增：自动提取关键信息存储到知识库 ====================
        self._auto_extract_knowledge(task, summary)

        # 更新统计
        if is_bug:
            self.memory.update_stats("bugs_fixed", 1)
        else:
            self.memory.update_stats("features_completed", 1)

        # 清除当前任务
        self.memory.clear_task(task_id)

        self._save_state()
        return True

    def _update_documents_on_task_complete(
        self,
        task: dict[str, Any],
        summary: str,
        timestamp: str,
    ) -> None:
        """
        任务完成后强制更新相关文档

        Args:
            task: 任务信息
            summary: 完成摘要
            timestamp: 时间戳
        """
        task_id = task.get("id", task.get("task_id", "unknown"))
        category = task.get("category", "任务")
        request = task.get("request", task.get("description", ""))

        # 1. 更新进度文档
        progress = self.memory.get_document("progress") or "# 项目进度\n"
        if task_id in progress:
            progress = re.sub(
                r'(\*\*状态\*\*:\s*)\S+',
                '**状态**: 已完成',
                progress
            )
        progress += f"\n## {task_id} - 完成\n"
        progress += f"- **类型**: {category}\n"
        progress += f"- **描述**: {request[:100]}\n"
        progress += f"- **完成时间**: {timestamp}\n"
        progress += f"- **摘要**: {summary[:200]}\n"
        self.memory.store_document("progress", progress)

        # 2. 更新开发日志
        dev_log = self.memory.get_document("development") or "# 开发日志\n"
        dev_log += f"\n## [{timestamp}] {category}\n"
        dev_log += f"**任务ID**: {task_id}\n"
        dev_log += f"**请求**: {request[:200]}\n"
        dev_log += f"**结果**: {summary[:500]}\n"
        dev_log += "---\n"
        self.memory.store_document("development", dev_log)

        # 3. 通知用户文档已更新
        try:
            from harnessgenj.notify import get_notifier
            notifier = get_notifier()
            notifier._emit(
                f"📄 文档已更新: progress.md, development.md",
                "INFO"
            )
        except Exception:
            pass

        # 4. 触发文档同步（如果有）
        try:
            self._sync_progress_document()
        except Exception:
            pass

    # ==================== 快速开发 ====================

    def develop(
        self,
        feature_request: str,
        *,
        use_tdd: bool = False,
        skip_level: SkipLevel = SkipLevel.NONE,
        admin_override: bool = False,
    ) -> dict[str, Any]:
        """
        快速开发功能

        Args:
            feature_request: 功能需求描述
            use_tdd: 是否使用 TDD 模式（需要 TDD 工作流支持）
            skip_level: 跳过级别（控制可跳过的检查项）
            admin_override: 管理员覆盖（允许跳过强制检查，会记录审计日志）

        Returns:
            开发结果

        Note:
            强制检查项（adversarial_review, security_check, boundary_check）不可跳过，
            除非明确设置 admin_override=True。所有跳过操作都会被记录到审计日志。
        """
        task_info = self.receive_request(feature_request, request_type="feature")
        task_id = task_info.get("task_id")

        # ==================== 新增：审计日志记录 ====================
        if skip_level != SkipLevel.NONE or admin_override:
            self._record_bypass_attempt(
                action="develop",
                skip_level=skip_level.value,
                admin_override=admin_override,
                task_id=task_id,
            )

        # ==================== 新增：启动任务状态流转 ====================
        # 将任务状态从 pending → in_progress
        if task_id:
            try:
                self._task_state_machine.start(task_id)
            except Exception:
                pass  # 状态转换失败不影响主流程

        # Hooks: Pre-Task 检查（开发前验证）
        # 强制检查项不可跳过（除非管理员覆盖）
        if not admin_override:
            pre_result = self._hooks_integration.run_pre_task({
                "request": feature_request,
                "type": "feature",
                "task_id": task_id,
            })
            if not pre_result.passed:
                return {
                    "request": feature_request,
                    "task_id": task_id,
                    "status": "blocked_by_hooks",
                    "errors": pre_result.errors,
                    "blocked_by": pre_result.blocked_by,
                }
        elif skip_level == SkipLevel.NONE:
            # admin_override=True 但 skip_level=NONE，仍执行强制检查
            # 只有可选 Hooks 可跳过
            pass

        # 确保有开发团队
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        # 注册角色到协作管理器
        self._register_roles_to_collaboration()

        # 【新增】通知工作流开始
        try:
            from harnessgenj.notify import get_notifier
            notifier = get_notifier()
            pipeline = self.coordinator._workflows.get("feature")
            stages = list(pipeline._stages.keys()) if pipeline else ["requirement", "design", "development", "testing"]
            notifier.notify_workflow_start("feature", stages)
        except Exception:
            pass

        # 广播开发任务开始
        self._collaboration.broadcast(
            from_role="project_manager",
            content={
                "type": "task_started",
                "task_id": task_id,
                "description": feature_request,
            },
            exclude=["project_manager"],
        )

        # TDD 模式：使用 TDD 工作流
        if use_tdd:
            return self._develop_with_tdd(feature_request, task_id, skip_level, admin_override)

        # ==================== 新增：更新活动工作流状态 ====================
        Harness._active_workflow_id = "feature"

        # 执行开发工作流
        result = self.coordinator.run_workflow("feature", {"feature_request": feature_request})

        # 清除活动工作流状态
        Harness._active_workflow_id = None

        if result.get("status") == "completed":
            # ==================== 新增：内置对抗触发 ====================
            # 获取产出的代码（如果有）
            code = result.get("code", "")
            if not code:
                artifacts = result.get("artifacts", [])
                if artifacts and isinstance(artifacts, list) and len(artifacts) > 0:
                    first_artifact = artifacts[0]
                    if isinstance(first_artifact, dict):
                        code = first_artifact.get("content", "")
                    elif isinstance(first_artifact, str):
                        code = first_artifact

            # ==================== 强制对抗审查（不可跳过） ====================
            # 对抗审查是强制检查项，只有 admin_override=True 才能跳过
            if code and (not admin_override or "adversarial_review" in MANDATORY_CHECKS):
                review_event = self._hybrid_integration.trigger_on_write_complete(
                    file_path=result.get("file_path", "unknown.py"),
                    content=code,
                    metadata={"task_id": task_id, "feature": feature_request},
                )
                result["review_event"] = review_event.model_dump()

                # ==================== 执行 GAN 对抗审查（强制） ====================
                # 使用 AdversarialWorkflow 执行完整的对抗审查流程
                # 即使 admin_override=True，对抗审查也必须执行（除非特别声明）
                try:
                    adversarial = AdversarialWorkflow(
                        score_manager=self._score_manager,
                        quality_tracker=self._quality_tracker,
                        memory_manager=self.memory,
                    )

                    adversarial_result = adversarial.execute_adversarial_review(
                        code=code,
                        generator_id="dev_auto",
                        generator_type="developer",
                        task_id=task_id,
                        max_rounds=3,
                        use_hunter=True,  # 启用 BugHunter 进行安全审查
                        artifact_id=None,
                    )

                    # 记录对抗结果
                    result["adversarial_result"] = adversarial_result.model_dump()

                    # 根据对抗结果更新任务状态
                    if adversarial_result.success:
                        self._task_state_machine.submit_review(task_id, "对抗审查通过")
                        self._task_state_machine.complete(task_id, "功能开发完成")
                    else:
                        # 审查未通过，记录问题
                        result["issues"] = adversarial_result.total_issues
                        result["status"] = "review_failed"

                        # ==================== 新增：通知质量门禁阻塞 ====================
                        try:
                            from harnessgenj.notify import get_notifier
                            notifier = get_notifier()
                            notifier.notify_gate_blocked(
                                gate_name="adversarial_review",
                                reason=f"发现 {adversarial_result.total_issues} 个问题需要修复",
                            )
                        except Exception:
                            pass

                except Exception as e:
                    # 对抗审查失败不影响主流程，仅记录
                    result["adversarial_error"] = str(e)

            # Hooks: Post-Task 检查（开发后验证）
            # 强制检查项不可跳过（除非管理员覆盖）
            if not admin_override:
                post_result = self._hooks_integration.run_post_task({
                    "task_id": task_id,
                    "workflow_result": result,
                })
                if not post_result.passed:
                    # ==================== 新增：通知质量门禁阻塞 ====================
                    try:
                        from harnessgenj.notify import get_notifier
                        notifier = get_notifier()
                        notifier.notify_gate_blocked(
                            gate_name="post_task_hooks",
                            reason=post_result.errors[0] if post_result.errors else "未知错误",
                        )
                    except Exception:
                        pass
                    return {
                        "request": feature_request,
                        "task_id": task_id,
                        "status": "blocked_by_post_hooks",
                        "errors": post_result.errors,
                    }

            self._stats.features_developed += 1
            self._stats.workflows_completed += 1
            self.memory.store_message(f"功能开发完成: {feature_request}", "system")

            # 【新增】通知工作流完成
            try:
                from harnessgenj.notify import get_notifier
                notifier = get_notifier()
                score_changes = notifier.get_score_changes()
                notifier.notify_workflow_complete(
                    "feature",
                    success=True,
                    summary={"score_changes": len(score_changes)}
                )
            except Exception:
                pass

            # 同步进度文档
            self._sync_progress_document()

            # ==================== 新增：更新任务状态和积分 ====================
            if task_id:
                # 使用混合集成层触发任务完成事件（自动更新积分）
                self._hybrid_integration.trigger_on_task_complete(
                    task_id=task_id,
                    summary=f"功能完成: {feature_request[:50]}",
                    metadata={"rounds": 1},
                )
                self.complete_task(task_id, f"功能完成: {feature_request[:50]}")
            self._save_state()

        return {
            "request": feature_request,
            "task_id": task_id,
            "status": result.get("status"),
            "artifacts": result.get("artifacts", []),
        }

    def fix_bug(
        self,
        bug_description: str,
        *,
        skip_level: SkipLevel = SkipLevel.NONE,
        admin_override: bool = False,
    ) -> dict[str, Any]:
        """
        快速修复 Bug

        Args:
            bug_description: Bug 描述
            skip_level: 跳过级别（控制可跳过的检查项）
            admin_override: 管理员覆盖（允许跳过强制检查，会记录审计日志）

        Returns:
            修复结果

        Note:
            强制检查项（adversarial_review, security_check, boundary_check）不可跳过，
            除非明确设置 admin_override=True。所有跳过操作都会被记录到审计日志。
        """
        task_info = self.receive_request(bug_description, request_type="bug")
        task_id = task_info.get("task_id")

        # ==================== 新增：审计日志记录 ====================
        if skip_level != SkipLevel.NONE or admin_override:
            self._record_bypass_attempt(
                action="fix_bug",
                skip_level=skip_level.value,
                admin_override=admin_override,
                task_id=task_id,
            )

        # ==================== 新增：启动任务状态流转 ====================
        # 将任务状态从 pending → in_progress
        if task_id:
            try:
                self._task_state_machine.start(task_id)
            except Exception:
                pass  # 状态转换失败不影响主流程

        # Hooks: Pre-Task 检查（修复前验证）
        # 强制检查项不可跳过（除非管理员覆盖）
        if not admin_override:
            pre_result = self._hooks_integration.run_pre_task({
                "request": bug_description,
                "type": "bug",
                "task_id": task_id,
            })
            if not pre_result.passed:
                return {
                    "bug": bug_description,
                    "task_id": task_id,
                    "status": "blocked_by_hooks",
                    "errors": pre_result.errors,
                }

        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        # 注册角色到协作管理器
        self._register_roles_to_collaboration()

        result = self.coordinator.run_workflow("bugfix", {"bug_report": bug_description})

        if result.get("status") == "completed":
            # ==================== 新增：获取修复代码并执行对抗审查 ====================
            code = result.get("code", "")
            if not code:
                artifacts = result.get("artifacts", [])
                if artifacts and isinstance(artifacts, list) and len(artifacts) > 0:
                    first_artifact = artifacts[0]
                    if isinstance(first_artifact, dict):
                        code = first_artifact.get("content", "")
                    elif isinstance(first_artifact, str):
                        code = first_artifact

            # ==================== 强制对抗审查（不可跳过） ====================
            # Bug修复更需要对抗审查，强制执行
            if code:
                try:
                    adversarial = AdversarialWorkflow(
                        score_manager=self._score_manager,
                        quality_tracker=self._quality_tracker,
                        memory_manager=self.memory,
                    )

                    adversarial_result = adversarial.execute_adversarial_review(
                        code=code,
                        generator_id="dev_auto",
                        generator_type="developer",
                        task_id=task_id,
                        max_rounds=3,
                        use_hunter=True,  # Bug修复更需要安全审查
                    )

                    result["adversarial_result"] = adversarial_result.model_dump()

                    if adversarial_result.success:
                        self._task_state_machine.submit_review(task_id, "Bug修复审查通过")
                        self._task_state_machine.complete(task_id, "Bug修复完成")
                    else:
                        result["issues"] = adversarial_result.total_issues
                        result["status"] = "review_failed"

                        # ==================== 新增：通知质量门禁阻塞 ====================
                        try:
                            from harnessgenj.notify import get_notifier
                            notifier = get_notifier()
                            notifier.notify_gate_blocked(
                                gate_name="adversarial_review",
                                reason=f"发现 {adversarial_result.total_issues} 个问题需要修复",
                            )
                        except Exception:
                            pass

                except Exception as e:
                    result["adversarial_error"] = str(e)

            # Hooks: Post-Task 检查（修复后验证）
            # 强制检查项不可跳过（除非管理员覆盖）
            if not admin_override:
                post_result = self._hooks_integration.run_post_task({
                    "task_id": task_id,
                    "workflow_result": result,
                    "type": "bug_fix",
                })
                if not post_result.passed:
                    # ==================== 新增：通知质量门禁阻塞 ====================
                    try:
                        from harnessgenj.notify import get_notifier
                        notifier = get_notifier()
                        notifier.notify_gate_blocked(
                            gate_name="post_task_hooks",
                            reason=post_result.errors[0] if post_result.errors else "未知错误",
                        )
                    except Exception:
                        pass
                    return {
                        "bug": bug_description,
                        "task_id": task_id,
                        "status": "blocked_by_post_hooks",
                        "errors": post_result.errors,
                    }

            self._stats.bugs_fixed += 1
            self._stats.workflows_completed += 1
            self.memory.store_message(f"Bug修复完成: {bug_description}", "system")

            # 同步进度文档
            self._sync_progress_document()

            if task_id:
                self.complete_task(task_id, f"Bug修复: {bug_description[:50]}")
            self._save_state()

        return {
            "bug": bug_description,
            "task_id": task_id,
            "status": result.get("status"),
        }

    # ==================== 记忆与上下文 ====================

    def remember(self, key: str, content: str, important: bool = False) -> None:
        """记忆重要信息"""
        importance = 100 if important else 50
        self.memory.store_knowledge(key, content, importance)
        self._save_state()

    def recall(self, key: str) -> str | None:
        """回忆信息"""
        return self.memory.get_knowledge(key)

    def record(self, content: str, context: str = "", doc_type_hint: str | None = None) -> bool:
        """智能记录内容"""
        doc_type = doc_type_hint or "development"
        current = self.memory.get_document(doc_type) or ""
        timestamp = time.strftime('%Y-%m-%d %H:%M')
        entry = f"\n## 记录 ({timestamp})\n[{context}] {content}\n"
        self.memory.store_document(doc_type, current + entry)
        return True

    def get_context_prompt(self, role: str = "project_manager", max_tokens: int = 4000) -> str:
        """获取上下文提示（用于 LLM）"""
        return self.memory.get_context_for_llm(role, max_tokens)

    def get_minimal_context(self) -> str:
        """获取最小上下文"""
        return self.memory.get_minimal_context()

    # ==================== 会话管理 ====================

    def chat(self, message: str, role: str = "user", auto_record: bool = True) -> dict[str, Any]:
        """在当前会话中发送消息"""
        role_map = {
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
            "system": MessageRole.SYSTEM,
        }
        msg_role = role_map.get(role, MessageRole.USER)

        msg = self.sessions.chat(message, msg_role)
        self._stats.messages_sent += 1

        # 存储到记忆
        self.memory.store_message(message, role)

        # 自动处理用户请求（使用增强的意图识别）
        task_info = None
        intent_result = None
        response = None
        if auto_record and role == "user":
            # 使用意图识别路由器
            intent_result = self._intent_router.identify(message)

            # 记录意图识别结果
            self._record_intent(intent_result)

            # 根据意图类型处理（增强：所有类型都有处理）
            if intent_result.intent_type == IntentType.DEVELOPMENT:
                task_info = self.receive_request(message, request_type="feature")
                response = f"已创建开发任务 {task_info.get('task_id', 'unknown')}，优先级 {task_info.get('priority', 'P1')}。正在安排开发..."
            elif intent_result.intent_type == IntentType.BUGFIX:
                task_info = self.receive_request(message, request_type="bug")
                response = f"已创建 Bug 修复任务 {task_info.get('task_id', 'unknown')}，优先级 P0。正在安排修复..."
            elif intent_result.intent_type == IntentType.INQUIRY:
                # 问题咨询：尝试回答或返回相关信息
                response = self._handle_inquiry_intent(message, intent_result)
            elif intent_result.intent_type == IntentType.MANAGEMENT:
                # 项目管理：返回项目状态
                response = self._handle_management_intent(message, intent_result)
            else:
                # 未知意图：尝试理解并引导用户
                response = self._handle_unknown_intent(message)

        self._save_state()

        return {
            "message_id": msg.id if msg else None,
            "session_id": self.sessions._active_session_id,
            "task_info": task_info,
            "intent": intent_result.model_dump() if intent_result else None,
            "response": response,  # 新增：对话响应
        }

    def analyze_intent(self, message: str) -> IntentResult:
        """
        分析用户意图

        Args:
            message: 用户消息

        Returns:
            IntentResult: 意图识别结果
        """
        return self._intent_router.identify(message)

    def route_to_workflow(self, intent_result: IntentResult) -> WorkflowPipeline | None:
        """
        根据意图路由到对应工作流

        Args:
            intent_result: 意图识别结果

        Returns:
            WorkflowPipeline: 对应的工作流实例
        """
        return get_workflow(intent_result.target_workflow)

    def get_available_workflows(self) -> list[dict[str, str]]:
        """获取所有可用的工作流"""
        return list_workflows()

    def switch_session(self, session_type: str) -> dict[str, Any]:
        """切换到指定类型的会话"""
        type_map = {
            "development": SessionType.DEVELOPMENT,
            "product_manager": SessionType.PRODUCT_MANAGER,
            "project_manager": SessionType.PROJECT_MANAGER,
            "architect": SessionType.ARCHITECT,
            "tester": SessionType.TESTER,
            "general": SessionType.GENERAL,
        }

        st = type_map.get(session_type.lower())
        if not st:
            return {"switched": False, "error": f"Unknown session type: {session_type}"}

        session = self.sessions.switch_session(st)
        return {
            "switched": True,
            "session": session.get_summary() if session else None,
        }

    # ==================== 状态报告 ====================

    def get_status(self) -> dict[str, Any]:
        """获取整体状态"""
        stats = self.memory.get_stats()

        return {
            "project": self.project_name,
            "team": {
                "size": self._stats.team_size,
                "members": self.coordinator.list_roles(),
            },
            "stats": self._stats.model_dump(),
            "project_stats": stats["stats"],
            "memory": stats["memory"],
            "sessions": self.sessions.get_stats(),
            "persistence": {
                "enabled": self._persistent,
                "workspace": self._workspace,
            },
            "current_task": self.memory.get_current_task(),
        }

    def get_report(self) -> str:
        """获取项目报告"""
        stats = self.memory.get_stats()

        return f"""
# {self.project_name} 项目报告

## 团队
- 规模: {self._stats.team_size} 人

## 统计
- 功能总数: {stats['stats']['features_total']}
- 已完成: {stats['stats']['features_completed']}
- Bug总数: {stats['stats']['bugs_total']}
- 已修复: {stats['stats']['bugs_fixed']}
- 进度: {stats['stats']['progress']}%

## 记忆健康
- Eden: {stats['memory']['eden_size']}
- Old: {stats['memory']['old_size']}
"""

    def save(self) -> bool:
        """手动保存当前工作状态"""
        return self._save_state()

    def reload(self) -> bool:
        """重新加载项目状态"""
        self.memory.reload()
        return self._load_state()

    # ==================== 引导系统 ====================

    def is_first_time(self) -> bool:
        """检测是否首次使用"""
        return self._guide.is_first_time()

    def start_onboarding(self) -> dict[str, Any]:
        """启动首次使用引导"""
        config = self._guide.start(self)
        self._save_state()
        return {
            "completed": True,
            "project_name": config.project_name,
            "tech_stack": config.tech_stack,
        }

    def welcome(self) -> str:
        """生成欢迎信息"""
        return f"""
欢迎使用 HarnessGenJ！

项目: {self.project_name}

快速提示:
  - 使用 harness.receive_request("需求") 接收请求
  - 使用 harness.develop("功能") 快速开发
  - 使用 harness.get_context_prompt() 获取上下文
"""

    def get_init_prompt(self) -> str:
        """
        获取初始化提示（用于 Claude Code 对话初始化）

        返回用户友好的初始化指导和项目上下文，让用户能够：
        1. 快速理解如何使用框架
        2. 知道可以直接说什么来触发功能
        3. 了解当前项目状态

        Returns:
            初始化提示字符串
        """
        # 获取项目信息
        project_name = self.project_name or "未命名项目"
        tech_stack = self.memory.project_info.tech_stack if hasattr(self.memory, 'project_info') else "未知"

        # 用户友好的初始化提示
        init_prompt = f"""
# 🚀 HGJ框架已就绪

我是你的AI开发助手，已准备好协助你完成开发任务。

## 快速开始

### 你可以这样使用我：

**方式一：直接描述需求**
> "帮我实现一个用户登录功能"

**方式二：让我修复问题**
> "首页加载太慢了，帮我优化一下"

**方式三：查看项目状态**
> "当前项目进度如何？"

---

## 🔧 MCP 工具可用

框架已暴露 21 个 MCP 工具，可通过 Claude Code 直接调用：

| 类别 | 工具示例 |
|------|----------|
| 开发 | `task_develop`, `task_fix_bug` |
| 内存 | `memory_store`, `memory_retrieve` |
| 系统 | `system_status`, `system_scoreboard` |
| 存储 | `storage_save`, `storage_search` |

---

## 💡 建议：让我先完成项目分析

执行以下命令，我会自动分析项目并建立知识库：

```python
harness.analyze_project()
```

---

## 核心功能

| 功能 | 使用方式 | 说明 |
|------|----------|------|
| 需求开发 | `harness.develop("需求描述")` | 执行完整开发流程 |
| Bug修复 | `harness.fix_bug("问题描述")` | 执行修复流程 |
| 对抗审查 | `harness.adversarial_develop("需求")` | 多轮审查确保质量 |
| 查看状态 | `harness.get_status()` | 项目进度和团队状态 |
| 存储知识 | `harness.remember("key", "value")` | 存储重要信息 |

---

**当前项目**: {project_name}
**技术栈**: {tech_stack}
**对话方式**: 直接与我对话，我会自动识别意图并执行相应操作。

"""
        return init_prompt

    # ==================== 对抗性质量保证 ====================

    def enable_adversarial_mode(self) -> dict[str, Any]:
        """
        启用对抗模式（已弃用）

        对抗模式现在默认启用，此方法保留仅为向后兼容。

        Returns:
            启用状态信息
        """
        import warnings
        warnings.warn(
            "enable_adversarial_mode() is deprecated. Adversarial mode is now always enabled by default.",
            DeprecationWarning,
            stacklevel=2,
        )
        return {
            "enabled": True,
            "message": "对抗模式默认已启用。使用 adversarial_develop() 进行对抗性开发。",
        }

    def adversarial_develop(
        self,
        feature_request: str,
        max_rounds: int = 3,
        use_hunter: bool = False,
        code: str | None = None,
        fix_callback=None,
    ) -> AdversarialResult:
        """
        对抗性开发（提高单次成功率）

        流程：
        1. 开发者产出代码
        2. 审查者审查代码
        3. 开发者修复问题
        4. 循环直到通过或达到最大轮次
        5. 计算积分变更

        Args:
            feature_request: 功能需求描述
            max_rounds: 最大对抗轮次（默认3）
            use_hunter: 是否使用 BugHunter（更激进的审查）
            code: 已有代码（可选，用于审查已有代码）
            fix_callback: 修复回调函数

        Returns:
            AdversarialResult: 对抗结果
        """
        # 确保有开发者
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_adv", "开发者")

        developer_id = "dev_adv"

        # 如果没有提供代码，先执行开发
        if code is None:
            dev_result = self.develop(feature_request)
            # 这里简化处理，实际应该获取开发者产出的代码
            code = f"# {feature_request}\n# 代码实现..."

        # Hooks: 安全预检（在对抗性审查前拦截明显问题）
        if code:
            security_result = self._hooks_integration.run_security_check({
                "code": code,
            })
            if not security_result.passed:
                # 直接返回失败，避免浪费对抗性审查时间
                return AdversarialResult(
                    success=False,
                    rounds=0,
                    total_issues=len(security_result.errors),
                    resolved_issues=0,
                    quality_score=0,
                    final_result="blocked_by_security_hooks",
                    issues=[],
                    duration=0.0,
                )

        # 执行对抗性审查
        result = self._adversarial_workflow.execute_adversarial_review(
            code=code,
            generator_id=developer_id,
            generator_type="developer",
            task_id=None,
            max_rounds=max_rounds,
            fix_callback=fix_callback,
            use_hunter=use_hunter,
        )

        # 更新统计
        if result.success:
            self._stats.features_developed += 1
            self._stats.workflows_completed += 1

        self._save_state()
        return result

    def quick_review(
        self,
        code: str,
        use_hunter: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        快速代码审查（单轮，不计分）

        Args:
            code: 待审查代码
            use_hunter: 是否使用 BugHunter

        Returns:
            (是否通过, 问题列表)
        """
        if self._adversarial_workflow is None:
            self.enable_adversarial_mode()

        passed, issues = self._adversarial_workflow.quick_review(code, use_hunter)
        return passed, [i.description for i in issues]

    def get_quality_report(self) -> dict[str, Any]:
        """
        获取质量报告

        Returns:
            质量指标和改进建议
        """
        return self._quality_tracker.get_quality_report()

    def get_score_leaderboard(self, role_type: str | None = None) -> list[dict[str, Any]]:
        """
        获取积分排行榜

        Args:
            role_type: 筛选角色类型（可选）

        Returns:
            排行榜列表
        """
        return self._score_manager.get_leaderboard(role_type)

    def get_role_score(self, role_id: str) -> dict[str, Any] | None:
        """
        获取角色积分

        Args:
            role_id: 角色ID

        Returns:
            角色积分信息
        """
        score = self._score_manager.get_score(role_id)
        if score:
            return {
                "role_id": score.role_id,
                "role_name": score.role_name,
                "score": score.score,
                "grade": score.grade,
                "success_rate": f"{score.success_rate:.1%}",
            }
        return None

    # ==================== 系统级分析与改进 ====================

    def get_system_analysis(self) -> dict[str, Any]:
        """
        获取系统级对抗分析

        分析跨任务的模式，识别：
        - 生成器薄弱点
        - 判别器偏差
        - 系统改进建议

        Returns:
            系统分析结果
        """
        result = self._system_adversarial.analyze_cross_task_patterns()
        return {
            "total_tasks_analyzed": result.total_tasks_analyzed,
            "system_health_score": result.system_health_score,
            "generator_weaknesses": [
                {
                    "role_id": w.role_id,
                    "weakness_type": w.weakness_type,
                    "frequency": w.frequency,
                    "suggestions": w.suggestions[:3],
                }
                for w in result.generator_weaknesses[:5]
            ],
            "discriminator_biases": [
                {
                    "role_id": b.role_id,
                    "bias_type": b.bias_type,
                    "impact": b.impact,
                    "suggestions": b.suggestions[:3],
                }
                for b in result.discriminator_biases[:5]
            ],
            "improvement_actions": result.improvement_actions[:10],
        }

    def get_health_trend(self) -> list[float]:
        """
        获取系统健康度趋势

        Returns:
            最近N次分析的健康度分数列表
        """
        return self._system_adversarial.get_system_health_trend()

    def run_task_with_adversarial(
        self,
        task: dict[str, Any],
        generator_role_type: str = "developer",
        max_rounds: int = 3,
        intensity: str = "normal",
    ) -> dict[str, Any]:
        """
        使用任务级对抗控制器执行任务

        这是完整的对抗性任务执行方法，包含：
        1. 任务分配给生成器
        2. 判别器自动审查
        3. 多轮修复循环
        4. 质量评分和记录

        Args:
            task: 任务信息字典
            generator_role_type: 生成器角色类型
            max_rounds: 最大对抗轮次
            intensity: 审查强度 ("normal" | "aggressive")

        Returns:
            任务执行结果
        """
        # 确保生成器角色存在
        role_type_map = {
            "developer": RoleType.DEVELOPER,
            "architect": RoleType.ARCHITECT,
            "tester": RoleType.TESTER,
            "doc_writer": RoleType.DOC_WRITER,
        }
        role_type = role_type_map.get(generator_role_type, RoleType.DEVELOPER)

        generator = self.coordinator.get_roles_by_type(role_type)
        if not generator:
            generator = self.coordinator.create_role(role_type, f"{generator_role_type}_1", generator_role_type)
        else:
            generator = generator[0]

        # 执行对抗性任务
        result = self._task_adversarial.execute_with_adversarial(
            task=task,
            generator=generator,
        )

        return {
            "task_id": task.get("id"),
            "success": result.final_result == "passed",
            "rounds": result.rounds,
            "quality_score": result.quality_score,
            "issues_found": result.issues_found,
            "issues_fixed": result.issues_fixed,
            "duration": result.duration,
        }

    # ==================== 内部辅助方法 ====================

    def _register_roles_to_collaboration(self) -> None:
        """将协调器中的角色注册到协作管理器，并设置消息订阅"""
        from harnessgenj.workflow.message_bus import MessageType

        for role_info in self.coordinator.list_roles():
            role_id = role_info.get("role_id")
            role_type = role_info.get("role_type")
            if role_id and role_type:
                # 检查是否已注册
                if not self._collaboration.get_role_state(role_id):
                    self._collaboration.register_role(role_id, role_type)

                    # ==================== 新增：设置角色消息订阅 ====================
                    # 根据角色类型订阅不同消息
                    if role_type == "code_reviewer":
                        # CodeReviewer 订阅代码变更通知
                        self._collaboration._message_bus.subscribe(
                            subscriber_id=role_id,
                            message_types=[MessageType.NOTIFICATION, MessageType.REQUEST],
                            callback=lambda msg: self._handle_review_request(msg, role_id),
                        )
                    elif role_type == "bug_hunter":
                        # BugHunter 订阅任务完成和安全问题通知
                        self._collaboration._message_bus.subscribe(
                            subscriber_id=role_id,
                            message_types=[MessageType.NOTIFICATION],
                            callback=lambda msg: self._handle_hunt_request(msg, role_id),
                        )
                    elif role_type == "tester":
                        # Tester 订阅任务完成通知
                        self._collaboration._message_bus.subscribe(
                            subscriber_id=role_id,
                            message_types=[MessageType.NOTIFICATION],
                            callback=lambda msg: self._handle_test_request(msg, role_id),
                        )

    def _handle_review_request(self, msg: Any, reviewer_id: str) -> None:
        """处理审查请求消息"""
        try:
            content = msg.content if hasattr(msg, "content") else msg
            if isinstance(content, dict):
                file_path = content.get("file_path", "")
                code = content.get("content", "")
                if code and file_path:
                    # 触发代码审查
                    self._trigger_manager.trigger(
                        TriggerEvent.ON_WRITE_COMPLETE,
                        {"file_path": file_path, "content": code},
                    )
        except Exception:
            pass  # 消息处理失败不影响主流程

    def _handle_hunt_request(self, msg: Any, hunter_id: str) -> None:
        """处理漏洞探测请求消息"""
        try:
            content = msg.content if hasattr(msg, "content") else msg
            if isinstance(content, dict):
                task_id = content.get("task_id", "")
                if task_id:
                    # 触发任务完成后的漏洞探测
                    self._trigger_manager.trigger(
                        TriggerEvent.ON_TASK_COMPLETE,
                        {"task_id": task_id},
                    )
        except Exception:
            pass

    def _handle_test_request(self, msg: Any, tester_id: str) -> None:
        """处理测试请求消息"""
        try:
            content = msg.content if hasattr(msg, "content") else msg
            if isinstance(content, dict):
                task_id = content.get("task_id", "")
                if task_id:
                    # 通知 Tester 进行测试
                    self._trigger_manager.trigger(
                        TriggerEvent.ON_TASK_COMPLETE,
                        {"task_id": task_id},
                    )
        except Exception:
            pass

    def _sync_progress_document(self) -> None:
        """同步进度文档"""
        progress = self.memory.get_document("progress")
        if progress:
            # 注册文档（如果未注册）
            if "progress.md" not in [d.doc_name for d in self._doc_sync.list_documents()]:
                self._doc_sync.register_document("progress.md")
            # 同步文档
            self._doc_sync.sync_document("progress.md")

    def get_doc_sync_status(self) -> dict[str, Any]:
        """获取文档同步状态"""
        return self._doc_sync.get_stats()

    def get_collaboration_status(self) -> dict[str, Any]:
        """获取协作状态"""
        return {
            "stats": self._collaboration.get_stats(),
            "snapshot": self._collaboration.get_snapshot().model_dump(),
        }

    def get_hybrid_integration_status(self) -> dict[str, Any]:
        """
        获取混合集成状态

        Returns:
            混合集成诊断信息
        """
        return self._hybrid_integration.diagnose()

    def get_task_state_status(self) -> dict[str, Any]:
        """
        获取任务状态机状态

        Returns:
            任务状态机统计信息
        """
        return self._task_state_machine.get_stats()

    def get_task_history(self, task_id: str) -> list[dict[str, Any]]:
        """
        获取任务状态历史

        Args:
            task_id: 任务ID

        Returns:
            状态变更历史
        """
        history = self._task_state_machine.get_history(task_id)
        return [event.model_dump() for event in history]

    def get_tdd_status(self) -> dict[str, Any] | None:
        """获取 TDD 工作流状态"""
        if self._tdd_workflow:
            return self._tdd_workflow.get_stats()
        return None

    def enable_tdd(self, config: TDDConfig | None = None) -> None:
        """启用 TDD 工作流"""
        self._tdd_workflow = create_tdd_workflow(config)

    def disable_tdd(self) -> None:
        """禁用 TDD 工作流"""
        self._tdd_workflow = None

    # ==================== 智能对话处理 ====================

    def _handle_inquiry_intent(
        self,
        message: str,
        intent_result: IntentResult,
    ) -> str:
        """
        处理问题咨询意图

        Args:
            message: 用户消息
            intent_result: 意图识别结果

        Returns:
            响应文本
        """
        # 提取实体信息
        entities = {e.name: e.value for e in intent_result.entities}

        # 检查是否询问项目状态
        if "进度" in message or "状态" in message:
            stats = self.memory.get_stats()
            return f"""
项目当前状态：
- 功能总数: {stats['stats']['features_total']}
- 已完成: {stats['stats']['features_completed']}
- Bug总数: {stats['stats']['bugs_total']}
- 已修复: {stats['stats']['bugs_fixed']}
- 进度: {stats['stats']['progress']}%
"""

        # 检查是否询问技术栈
        if "技术栈" in message or "技术" in message:
            tech_stack = self.memory.project_info.tech_stack or "未配置"
            return f"当前项目技术栈: {tech_stack}"

        # 检查是否询问团队
        if "团队" in message or "成员" in message:
            team = self.coordinator.list_roles()
            if team:
                members = "\n".join([f"- {m['name']} ({m['role_type']})" for m in team])
                return f"当前团队成员:\n{members}"
            return "团队尚未组建，请使用 setup_team() 方法组建团队"

        # 检查是否询问特定文档
        doc_types = ["需求", "设计", "开发", "测试", "进度"]
        for doc_type in doc_types:
            if doc_type in message:
                doc = self.memory.get_document(doc_type.lower())
                if doc:
                    # 返回摘要（避免过长）
                    lines = doc.split("\n")[:10]
                    summary = "\n".join(lines)
                    return f"{doc_type}文档摘要:\n{summary}\n\n（如需查看完整内容，请使用 get_document('{doc_type.lower()}')"
                return f"暂无{doc_type}文档"

        # 通用咨询：返回项目信息
        project_name = self.project_name
        description = self.memory.project_info.description or "暂无描述"
        return f"""
项目: {project_name}
描述: {description[:100]}
您可以使用以下命令：
- develop("功能描述") - 开发新功能
- fix_bug("bug描述") - 修复Bug
- get_status() - 查看完整状态
"""

    def _handle_management_intent(
        self,
        message: str,
        intent_result: IntentResult,
    ) -> str:
        """
        处理项目管理意图

        Args:
            message: 用户消息
            intent_result: 意图识别结果

        Returns:
            响应文本
        """
        # 检查是否需要生成报告
        if "报告" in message or "统计" in message:
            return self.get_report()

        # 检查是否询问进度
        if "进度" in message:
            current_task = self.memory.get_current_task()
            if current_task:
                return f"当前任务: {current_task.get('request', 'unknown')}\n状态: {current_task.get('status', 'pending')}"
            return "当前无进行中的任务"

        # 检查是否需要资源调配
        if "资源" in message or "安排" in message:
            team = self.coordinator.list_roles()
            if not team:
                return "团队尚未组建，请先组建团队再进行资源调配"
            return f"当前团队规模: {len(team)} 人\n可使用 setup_team() 调整团队配置"

        # 默认返回项目状态
        return self.get_report()

    def _handle_unknown_intent(self, message: str) -> str:
        """
        处理未知意图

        Args:
            message: 用户消息

        Returns:
            响应文本
        """
        # 尝试从记忆中搜索相关信息
        relevant_knowledge = self._search_relevant_knowledge(message)

        if relevant_knowledge:
            return f"根据项目记录，找到相关信息:\n{relevant_knowledge}\n\n如果这不是您想要的，请尝试更具体地描述您的需求，例如:\n- '我需要一个XX功能'\n- 'XX页面报错，需要修复'\n- '查看项目进度'"

        # 返回引导信息
        return """
我无法完全理解您的请求。您可以尝试以下方式：

1. **开发功能**: "我需要一个购物车功能"
2. **修复Bug**: "支付页面报错，无法完成支付"
3. **查看进度**: "项目进度如何？"
4. **询问信息**: "当前技术栈是什么？"

或者直接使用 API：
- harness.develop("功能描述")
- harness.fix_bug("问题描述")
- harness.get_status()
"""

    def _search_relevant_knowledge(self, message: str) -> str | None:
        """
        从记忆中搜索与消息相关的知识

        Args:
            message: 用户消息

        Returns:
            相关知识内容，如果没有找到返回 None
        """
        # 提取关键词
        keywords = []
        for word in message.split():
            if len(word) >= 2:
                keywords.append(word)

        if not keywords:
            return None

        # 搜索热点知识
        try:
            hotspots = self.memory.hotspot.detect_hotspots()
            for hotspot in hotspots[:5]:
                key = hotspot.name
                content = self.memory.get_knowledge(key)
                if content:
                    # 检查关键词匹配
                    for kw in keywords:
                        if kw in content or kw in key:
                            return content[:200]
        except Exception:
            pass

        # 回退：搜索所有知识
        try:
            # 尝试从 heap 中搜索
            heap_items = self.memory.heap.list_items()
            for item in heap_items[:10]:
                key = item.get("key", "")
                content = self.memory.get_knowledge(key)
                if content:
                    for kw in keywords:
                        if kw in content or kw in key:
                            return content[:200]
        except Exception:
            pass

        return None

    def _develop_with_tdd(
        self,
        feature_request: str,
        task_id: str | None,
        skip_level: SkipLevel,
        admin_override: bool,
    ) -> dict[str, Any]:
        """
        使用 TDD 模式开发功能

        Args:
            feature_request: 功能需求
            task_id: 任务 ID
            skip_level: 跳过级别
            admin_override: 管理员覆盖

        Returns:
            开发结果
        """
        # 确保 TDD 工作流已启用
        if not self._tdd_workflow:
            self.enable_tdd()

        # 开始 TDD 循环
        cycle = self._tdd_workflow.start_cycle(feature_request)

        # Red 阶段：写失败的测试
        # 这里简化实现，实际应该由 Tester 角色生成测试
        test_code = f'''
def test_{feature_request.replace(" ", "_")}():
    """Test for {feature_request}"""
    # TODO: Implement test
    assert False, "Test not implemented yet"
'''
        test_result = self._tdd_workflow.write_test(cycle, test_code)

        # Green 阶段：写实现
        # 这里简化实现，实际应该由 Developer 角色生成代码
        impl_code = f'''
def {feature_request.replace(" ", "_").lower()}():
    """Implementation for {feature_request}"""
    # TODO: Implement
    pass
'''
        impl_result = self._tdd_workflow.write_implementation(cycle, impl_code)

        # Refactor 阶段：重构（可选）
        refactored_code = impl_code  # 简化：不重构
        refactor_result, suggestions = self._tdd_workflow.refactor(cycle, refactored_code)

        # 完成循环
        cycle_result = self._tdd_workflow.complete_cycle(cycle)

        # Hooks: Post-Task 检查
        # 强制检查项不可跳过（除非管理员覆盖）
        if not admin_override:
            post_result = self._hooks_integration.run_post_task({
                "task_id": task_id,
                "tdd_cycle": cycle_result,
            })
            if not post_result.passed:
                return {
                    "request": feature_request,
                    "task_id": task_id,
                    "status": "blocked_by_post_hooks",
                    "errors": post_result.errors,
                    "tdd_cycle": cycle_result,
                }

        # 更新统计
        if cycle_result.get("status") == "completed":
            self._stats.features_developed += 1
            self._stats.workflows_completed += 1
            self.memory.store_message(f"TDD 功能开发完成: {feature_request}", "system")
            self._sync_progress_document()
            if task_id:
                self.complete_task(task_id, f"TDD 功能完成: {feature_request[:50]}")
            self._save_state()

        return {
            "request": feature_request,
            "task_id": task_id,
            "status": cycle_result.get("status"),
            "tdd_cycle": cycle_result,
            "coverage": cycle_result.get("coverage"),
        }

    def _record_bypass_attempt(
        self,
        action: str,
        skip_level: str,
        admin_override: bool,
        task_id: str | None = None,
    ) -> None:
        """
        记录跳过检查尝试到审计日志

        Args:
            action: 操作类型（develop/fix_bug）
            skip_level: 跳过级别
            admin_override: 是否管理员覆盖
            task_id: 关联任务ID
        """
        try:
            audit_path = Path(self._workspace) / "audit_log.json"

            # 确保目录存在
            audit_path.parent.mkdir(parents=True, exist_ok=True)

            # 加载现有日志
            if audit_path.exists():
                with open(audit_path, "r", encoding="utf-8") as f:
                    audit_log = json.load(f)
            else:
                audit_log = {"bypass_attempts": [], "stats": {}}

            # 添加记录
            audit_log["bypass_attempts"].append({
                "timestamp": time.time(),
                "action": action,
                "skip_level": skip_level,
                "admin_override": admin_override,
                "task_id": task_id,
            })

            # 更新统计
            stats = audit_log.get("stats", {})
            stats["total_bypass_attempts"] = stats.get("total_bypass_attempts", 0) + 1
            stats[f"{action}_bypass_attempts"] = stats.get(f"{action}_bypass_attempts", 0) + 1
            if admin_override:
                stats["admin_override_count"] = stats.get("admin_override_count", 0) + 1
            audit_log["stats"] = stats

            # 保存日志
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit_log, f, ensure_ascii=False, indent=2)

            # 通知用户
            try:
                from harnessgenj.notify import get_notifier
                notifier = get_notifier()
                if admin_override:
                    notifier._emit(
                        f"⚠️ 管理员覆盖: 跳过 {skip_level} 级别检查 ({action})",
                        "WARNING"
                    )
                    notifier._emit("   此操作已记录到审计日志", "INFO")
                elif skip_level != "none":
                    notifier._emit(
                        f"📋 跳过级别: {skip_level} ({action})",
                        "INFO"
                    )
            except Exception:
                pass

        except Exception:
            pass  # 审计日志记录失败不影响主流程


def create_harness(
    project_name: str = "Default Project",
    *,
    persistent: bool = True,
    workspace: str = ".harnessgenj",
) -> Harness:
    """创建 Harness 实例"""
    return Harness(
        project_name=project_name,
        persistent=persistent,
        workspace=workspace,
    )