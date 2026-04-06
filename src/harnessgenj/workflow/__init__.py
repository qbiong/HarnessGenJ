"""
Workflow Module - 工作流系统

Harness Engineering 核心理念：通过工作流驱动角色协作

工作流定义:
- Pipeline: 完整开发流水线
- Stage: 工作流阶段
- Handoff: 阶段间的交付物传递

标准工作流:
需求分析 → 架构设计 → 开发实现 → 测试验证 → 文档编写 → 部署发布
"""

from harnessgenj.workflow.pipeline import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
    AdversarialStageConfig,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    create_adversarial_pipeline,
)
from harnessgenj.workflow.coordinator import WorkflowCoordinator, create_coordinator
from harnessgenj.workflow.context import WorkflowContext
from harnessgenj.workflow.dependency import (
    DependencyGraph,
    TaskNode,
    TaskStatus,
    create_dependency_graph,
)
from harnessgenj.workflow.message_bus import (
    MessageBus,
    RoleMessage,
    MessageType,
    MessagePriority,
    MessageStatus,
    create_message_bus,
)
from harnessgenj.workflow.collaboration import (
    RoleCollaborationManager,
    CollaborationRole,
    CollaborationSnapshot,
    create_collaboration_manager,
)
from harnessgenj.workflow.tdd_workflow import (
    TDDWorkflow,
    TDDConfig,
    TDDCycle,
    TDDPhase,
    CycleStatus,
    TestResult,
    CoverageReport,
    RefactorSuggestion,
    create_tdd_workflow,
)

__all__ = [
    "WorkflowPipeline",
    "WorkflowStage",
    "StageStatus",
    "AdversarialStageConfig",
    "WorkflowCoordinator",
    "WorkflowContext",
    # Dependency
    "DependencyGraph",
    "TaskNode",
    "TaskStatus",
    "create_dependency_graph",
    # Message Bus
    "MessageBus",
    "RoleMessage",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "create_message_bus",
    # Collaboration
    "RoleCollaborationManager",
    "CollaborationRole",
    "CollaborationSnapshot",
    "create_collaboration_manager",
    # TDD Workflow
    "TDDWorkflow",
    "TDDConfig",
    "TDDCycle",
    "TDDPhase",
    "CycleStatus",
    "TestResult",
    "CoverageReport",
    "RefactorSuggestion",
    "create_tdd_workflow",
    # Pipelines
    "create_coordinator",
    "create_standard_pipeline",
    "create_feature_pipeline",
    "create_bugfix_pipeline",
    "create_adversarial_pipeline",
]