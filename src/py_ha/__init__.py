"""
py_ha - Python Harness for AI Agents

A Harness Engineering Framework for AI Agent Collaboration

核心特性:
- 角色驱动协作: Developer/Tester/PM/Architect/DocWriter/ProjectManager
- 工作流驱动: 需求→设计→开发→测试→文档→发布
- JVM风格记忆管理: 分代存储、自动GC、热点检测
- 渐进式披露: 项目经理协调，每个角色只访问相关信息
- 轻量化设计: 无需数据库/Redis配置
- 一键执行: 快速完成功能开发/Bug修复
"""

__version__ = "0.3.0"

# 主入口
from py_ha.engine import Harness, create_harness

# 会话管理
from py_ha.session import (
    SessionManager,
    Session,
    SessionType,
    Message,
    MessageRole,
)

# Roles - 角色系统
from py_ha.roles import (
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
)

# Workflow - 工作流系统
from py_ha.workflow import (
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
from py_ha.memory import (
    MemoryManager,
    MemoryHeap,
    GarbageCollector,
    HotspotDetector,
    AutoAssembler,
)

# Storage Module - 轻量化存储
from py_ha.storage import (
    StorageManager,
    MemoryStorage,
    JsonStorage,
    MarkdownStorage,
)
from py_ha.storage.manager import StorageType, create_storage

# Guide Module - 首次使用引导
from py_ha.guide import (
    OnboardingGuide,
    ProjectConfig,
    create_guide,
)

# Project Module - 项目管理与渐进式披露
from py_ha.project import (
    ProjectStateManager,
    ProjectDocument,
    ProjectInfo,
    ProjectStats,
    DocumentType,
    create_project_state,
    # JVM风格区域映射
    MemoryRegion,
    DOCUMENT_REGION_MAP,
    REGION_LOAD_STRATEGY,
    get_document_region,
    get_region_load_strategy,
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
    # Project
    "ProjectStateManager",
    "ProjectDocument",
    "ProjectInfo",
    "ProjectStats",
    "DocumentType",
    "create_project_state",
    # JVM风格区域映射
    "MemoryRegion",
    "DOCUMENT_REGION_MAP",
    "REGION_LOAD_STRATEGY",
    "get_document_region",
    "get_region_load_strategy",
]