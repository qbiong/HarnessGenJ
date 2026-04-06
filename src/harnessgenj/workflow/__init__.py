"""
Workflow Module - 工作流系统

Harness Engineering 核心理念：通过工作流驱动角色协作

工作流定义:
- Pipeline: 完整开发流水线
- Stage: 工作流阶段
- Handoff: 阶段间的交付物传递

工作流类型:
- IntentPipeline: 意图识别与路由
- DevelopmentPipeline: 统一开发流水线（含GAN对抗）
- BugFixPipeline: Bug修复流水线（含GAN对抗）
- InquiryPipeline: 问题咨询流水线
- ManagementPipeline: 项目管理流水线

质量保证环节（所有代码变更必经）:
- 需求识别
- 架构规划
- 代码编写
- 对抗优化（GAN）
- 单元测试
- 集成测试

记忆管理集成:
- StageMemoryMapping: 定义阶段产出物到记忆区域的映射
- WorkflowExecutor: 执行阶段并自动管理记忆读写
"""

from harnessgenj.workflow.pipeline import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
    AdversarialConfig,
    QualityGate,
    QualityGateType,
    create_standard_quality_gates,
    # 新工作流工厂
    create_intent_pipeline,
    create_development_pipeline,
    create_bugfix_pipeline,
    create_inquiry_pipeline,
    create_management_pipeline,
    get_workflow,
    list_workflows,
    WORKFLOW_REGISTRY,
    # 向后兼容
    create_standard_pipeline,
    create_feature_pipeline,
    create_adversarial_pipeline,
)
from harnessgenj.workflow.intent_router import (
    IntentRouter,
    IntentType,
    IntentResult,
    IntentConfidence,
    IntentPattern,
    ExtractedEntity,
    create_intent_router,
    identify_intent,
)
from harnessgenj.workflow.memory_mapping import (
    StageMemoryMapping,
    InputSource,
    OutputTarget,
    OutputAction,
    MemoryRegion,
    get_stage_mapping,
    get_pipeline_mappings,
    list_mappings,
    DEVELOPMENT_PIPELINE_MAPPINGS,
    BUGFIX_PIPELINE_MAPPINGS,
    INTENT_PIPELINE_MAPPINGS,
    INQUIRY_PIPELINE_MAPPINGS,
    MANAGEMENT_PIPELINE_MAPPINGS,
)
from harnessgenj.workflow.executor import (
    WorkflowExecutor,
    StageResult,
    WorkflowExecutionResult,
    create_executor,
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
    # Pipeline Core
    "WorkflowPipeline",
    "WorkflowStage",
    "StageStatus",
    "AdversarialConfig",
    "QualityGate",
    "QualityGateType",
    "create_standard_quality_gates",
    # Workflow Coordinator
    "WorkflowCoordinator",
    "WorkflowContext",
    "create_coordinator",
    # Intent Router
    "IntentRouter",
    "IntentType",
    "IntentResult",
    "IntentConfidence",
    "IntentPattern",
    "ExtractedEntity",
    "create_intent_router",
    "identify_intent",
    # Memory Mapping
    "StageMemoryMapping",
    "InputSource",
    "OutputTarget",
    "OutputAction",
    "MemoryRegion",
    "get_stage_mapping",
    "get_pipeline_mappings",
    "list_mappings",
    "DEVELOPMENT_PIPELINE_MAPPINGS",
    "BUGFIX_PIPELINE_MAPPINGS",
    "INTENT_PIPELINE_MAPPINGS",
    "INQUIRY_PIPELINE_MAPPINGS",
    "MANAGEMENT_PIPELINE_MAPPINGS",
    # Workflow Executor
    "WorkflowExecutor",
    "StageResult",
    "WorkflowExecutionResult",
    "create_executor",
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
    # New Workflows
    "create_intent_pipeline",
    "create_development_pipeline",
    "create_bugfix_pipeline",
    "create_inquiry_pipeline",
    "create_management_pipeline",
    "get_workflow",
    "list_workflows",
    "WORKFLOW_REGISTRY",
    # Backward Compatibility
    "create_standard_pipeline",
    "create_feature_pipeline",
    "create_adversarial_pipeline",
]