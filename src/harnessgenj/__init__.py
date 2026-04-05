"""
HarnessGenJ - Python Harness for AI Agents

A Harness Engineering Framework for AI Agent Collaboration

核心特性:
- 角色驱动协作: Developer/Tester/PM/Architect/DocWriter/ProjectManager/CodeReviewer/BugHunter
- 工作流驱动: 需求→设计→开发→测试→文档→发布
- JVM风格记忆管理: 分代存储、自动GC、热点检测
- 渐进式披露: 项目经理协调，每个角色只访问相关信息
- 对抗性质量保证: GAN式开发者-审查者对抗机制
- 轻量化设计: 无需数据库/Redis配置
- 一键执行: 快速完成功能开发/Bug修复
"""

__version__ = "0.6.0"

# 主入口
from harnessgenj.engine import Harness, create_harness

# 会话管理
from harnessgenj.session import (
    SessionManager,
    Session,
    SessionType,
    Message,
    MessageRole,
)

# Roles - 角色系统
from harnessgenj.roles import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    TaskType,
    SkillCategory,
    Developer,
    Tester,
    ProductManager,
    Architect,
    DocWriter,
    ProjectManager,
    CodeReviewer,
    BugHunter,
)

# Workflow - 工作流系统
from harnessgenj.workflow import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
    WorkflowCoordinator,
    WorkflowContext,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
)

# Memory Module - JVM风格记忆管理
from harnessgenj.memory import (
    MemoryManager,
    MemoryHeap,
    GarbageCollector,
    HotspotDetector,
    AutoAssembler,
    # 文档系统
    DocumentType,
    DOCUMENT_OWNERSHIP,
    DOCUMENT_REGION_MAP,
    REGION_LOAD_STRATEGY,
    get_document_region,
    get_region_load_strategy,
)

# Storage Module - 轻量化存储
from harnessgenj.storage import (
    StorageManager,
    MemoryStorage,
    JsonStorage,
    MarkdownStorage,
)
from harnessgenj.storage.manager import StorageType, create_storage

# Guide Module - 首次使用引导
from harnessgenj.guide import (
    OnboardingGuide,
    ProjectConfig,
    create_guide,
)

# Harness Module - 核心能力
from harnessgenj.harness import (
    # AGENTS Knowledge
    AgentsKnowledgeManager,
    KnowledgeSection,
    AgentsKnowledge,
    # Hooks
    HooksManager,
    BaseHook,
    HookType,
    HookMode,
    HookResult,
    HooksResult,
    CodeLintHook,
    SecurityHook,
    ValidationHook,
    TestPassHook,
    FormatHook,
    create_default_hooks,
    # HumanLoop
    HumanLoop,
    ApprovalRequest,
    # Context Assembler
    ContextAssembler,
    ContextSection,
    ContextPriority,
    PermanentKnowledge,
    ActiveTaskContext,
    create_context_assembler,
    # Adversarial
    AdversarialWorkflow,
    AdversarialResult,
    create_adversarial_workflow,
)

# Quality Module - 质量保证系统
from harnessgenj.quality import (
    ScoreManager,
    RoleScore,
    ScoreEvent,
    AdversarialRecord,
    IssueRecord,
    QualityTracker,
    FailurePattern,
)

__all__ = [
    # 主入口
    "Harness",
    "create_harness",
    # 会话管理
    "SessionManager",
    "Session",
    "SessionType",
    "Message",
    "MessageRole",
    # Roles
    "AgentRole",
    "RoleType",
    "RoleSkill",
    "RoleContext",
    "TaskType",
    "SkillCategory",
    "Developer",
    "Tester",
    "ProductManager",
    "Architect",
    "DocWriter",
    "ProjectManager",
    "CodeReviewer",
    "BugHunter",
    # Workflow
    "WorkflowPipeline",
    "WorkflowStage",
    "StageStatus",
    "WorkflowCoordinator",
    "WorkflowContext",
    "create_standard_pipeline",
    "create_feature_pipeline",
    "create_bugfix_pipeline",
    # Memory
    "MemoryManager",
    "MemoryHeap",
    "GarbageCollector",
    "HotspotDetector",
    "AutoAssembler",
    # Memory - 文档系统
    "DocumentType",
    "DOCUMENT_OWNERSHIP",
    "DOCUMENT_REGION_MAP",
    "REGION_LOAD_STRATEGY",
    "get_document_region",
    "get_region_load_strategy",
    # Storage
    "StorageManager",
    "StorageType",
    "create_storage",
    "MemoryStorage",
    "JsonStorage",
    "MarkdownStorage",
    # Guide
    "OnboardingGuide",
    "ProjectConfig",
    "create_guide",
    # Harness - AGENTS Knowledge
    "AgentsKnowledgeManager",
    "KnowledgeSection",
    "AgentsKnowledge",
    # Harness - Hooks
    "HooksManager",
    "BaseHook",
    "HookType",
    "HookMode",
    "HookResult",
    "HooksResult",
    "CodeLintHook",
    "SecurityHook",
    "ValidationHook",
    "TestPassHook",
    "FormatHook",
    "create_default_hooks",
    # Harness - HumanLoop
    "HumanLoop",
    "ApprovalRequest",
    # Harness - Context Assembler
    "ContextAssembler",
    "ContextSection",
    "ContextPriority",
    "PermanentKnowledge",
    "ActiveTaskContext",
    "create_context_assembler",
    # Harness - Adversarial
    "AdversarialWorkflow",
    "AdversarialResult",
    "create_adversarial_workflow",
    # Quality
    "ScoreManager",
    "RoleScore",
    "ScoreEvent",
    "AdversarialRecord",
    "IssueRecord",
    "QualityTracker",
    "FailurePattern",
]