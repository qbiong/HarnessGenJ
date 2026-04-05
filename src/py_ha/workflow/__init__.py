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

from py_ha.workflow.pipeline import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
    AdversarialStageConfig,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    create_adversarial_pipeline,
)
from py_ha.workflow.coordinator import WorkflowCoordinator, create_coordinator
from py_ha.workflow.context import WorkflowContext

__all__ = [
    "WorkflowPipeline",
    "WorkflowStage",
    "StageStatus",
    "AdversarialStageConfig",
    "WorkflowCoordinator",
    "WorkflowContext",
    "create_coordinator",
    "create_standard_pipeline",
    "create_feature_pipeline",
    "create_bugfix_pipeline",
    "create_adversarial_pipeline",
]