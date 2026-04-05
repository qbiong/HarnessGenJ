"""
Workflow Pipeline - 工作流流水线

定义软件开发的标准流程:
1. Requirements: 需求分析 (ProductManager)
2. Design: 架构设计 (Architect)
3. Development: 开发实现 (Developer)
4. Testing: 测试验证 (Tester)
5. Documentation: 文档编写 (DocWriter)
6. Review: 评审验收 (ProjectManager)

每个阶段:
- 输入: 前一阶段的交付物
- 处理: 角色执行任务
- 输出: 当前阶段的交付物
- 验证: 质量门禁检查
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time


class StageStatus(Enum):
    """阶段状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"    # 正在被审查
    REVIEW_FAILED = "review_failed"  # 审查发现问题


class AdversarialStageConfig(BaseModel):
    """对抗审查配置"""

    enabled: bool = Field(default=True, description="是否启用对抗审查")
    intensity: str = Field(default="normal", description="审查强度: normal | aggressive")
    max_rounds: int = Field(default=3, description="最大对抗轮次")
    auto_fix: bool = Field(default=True, description="是否自动修复")
    discriminator_role: str = Field(default="code_reviewer", description="判别器角色")


class WorkflowStage(BaseModel):
    """
    工作流阶段 - 流水线的一个环节

    每个阶段包含:
    - 阶段名称和描述
    - 负责角色
    - 输入要求
    - 输出定义
    - 质量门禁
    """

    name: str = Field(..., description="阶段名称")
    description: str = Field(default="", description="阶段描述")
    role: str = Field(..., description="负责角色")
    inputs: list[str] = Field(default_factory=list, description="所需输入")
    outputs: list[str] = Field(default_factory=list, description="产出输出")
    quality_gates: list[str] = Field(default_factory=list, description="质量门禁")
    dependencies: list[str] = Field(default_factory=list, description="依赖的前置阶段")

    # 对抗审查配置
    adversarial_config: AdversarialStageConfig | None = Field(
        default=None,
        description="对抗审查配置",
    )

    # 执行状态
    status: StageStatus = Field(default=StageStatus.PENDING, description="状态")
    started_at: float | None = Field(default=None, description="开始时间")
    completed_at: float | None = Field(default=None, description="完成时间")
    result: dict[str, Any] | None = Field(default=None, description="执行结果")

    def can_start(self, completed_stages: set[str]) -> bool:
        """检查是否可以开始"""
        return all(dep in completed_stages for dep in self.dependencies)

    def start(self) -> None:
        """开始阶段"""
        self.status = StageStatus.RUNNING
        self.started_at = time.time()

    def complete(self, result: dict[str, Any]) -> None:
        """完成阶段"""
        self.status = StageStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result

    def fail(self, error: str) -> None:
        """阶段失败"""
        self.status = StageStatus.FAILED
        self.completed_at = time.time()
        self.result = {"error": error}


class WorkflowPipeline:
    """
    工作流流水线 - 定义完整的开发流程

    Harness核心概念:
    - 流水线是阶段的有序集合
    - 阶段之间通过交付物传递
    - 每个阶段有明确的质量门禁
    - 支持并行和串行执行
    """

    def __init__(self, name: str = "default_pipeline") -> None:
        self.name = name
        self._stages: dict[str, WorkflowStage] = {}
        self._stage_order: list[str] = []
        self._artifacts: dict[str, Any] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    def add_stage(self, stage: WorkflowStage) -> None:
        """添加阶段"""
        self._stages[stage.name] = stage
        self._stage_order.append(stage.name)

    def get_stage(self, name: str) -> WorkflowStage | None:
        """获取阶段"""
        return self._stages.get(name)

    def list_stages(self) -> list[WorkflowStage]:
        """列出所有阶段"""
        return [self._stages[name] for name in self._stage_order]

    def get_ready_stages(self) -> list[WorkflowStage]:
        """获取可以执行的阶段"""
        completed = {
            name for name, stage in self._stages.items()
            if stage.status == StageStatus.COMPLETED
        }

        ready = []
        for name in self._stage_order:
            stage = self._stages[name]
            if stage.status == StageStatus.PENDING and stage.can_start(completed):
                ready.append(stage)

        return ready

    def store_artifact(self, name: str, content: Any) -> None:
        """存储交付物"""
        self._artifacts[name] = {
            "content": content,
            "timestamp": time.time(),
        }

    def get_artifact(self, name: str) -> Any | None:
        """获取交付物"""
        artifact = self._artifacts.get(name)
        return artifact["content"] if artifact else None

    def get_status(self) -> dict[str, Any]:
        """获取流水线状态"""
        stages = self.list_stages()
        total = len(stages)
        completed = sum(1 for s in stages if s.status == StageStatus.COMPLETED)
        running = sum(1 for s in stages if s.status == StageStatus.RUNNING)
        failed = sum(1 for s in stages if s.status == StageStatus.FAILED)

        return {
            "pipeline_name": self.name,
            "total_stages": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "progress": f"{completed}/{total}",
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "artifacts_count": len(self._artifacts),
        }

    def reset(self) -> None:
        """重置流水线"""
        for stage in self._stages.values():
            stage.status = StageStatus.PENDING
            stage.started_at = None
            stage.completed_at = None
            stage.result = None
        self._artifacts.clear()


# ==================== 标准工作流 ====================

def create_standard_pipeline() -> WorkflowPipeline:
    """
    创建标准开发流水线

    流程: 需求 → 设计 → 开发 → 测试 → 文档 → 发布
    """
    pipeline = WorkflowPipeline("standard_dev_pipeline")

    # 阶段1: 需求分析
    pipeline.add_stage(WorkflowStage(
        name="requirements",
        description="需求分析与整理",
        role="product_manager",
        inputs=["user_request"],
        outputs=["requirements", "user_stories", "acceptance_criteria"],
        quality_gates=["需求完整性检查", "优先级定义"],
        dependencies=[],
    ))

    # 阶段2: 架构设计
    pipeline.add_stage(WorkflowStage(
        name="design",
        description="架构设计与技术方案",
        role="architect",
        inputs=["requirements"],
        outputs=["architecture", "design_doc", "tech_stack"],
        quality_gates=["架构评审通过", "技术方案确认"],
        dependencies=["requirements"],
    ))

    # 阶段3: 开发实现
    pipeline.add_stage(WorkflowStage(
        name="development",
        description="功能开发与实现",
        role="developer",
        inputs=["design_doc", "user_stories"],
        outputs=["code", "unit_tests"],
        quality_gates=["代码审查通过", "单元测试通过"],
        dependencies=["design"],
    ))

    # 阶段4: 测试验证
    pipeline.add_stage(WorkflowStage(
        name="testing",
        description="测试验证",
        role="tester",
        inputs=["code", "acceptance_criteria"],
        outputs=["test_results", "bug_reports"],
        quality_gates=["测试覆盖率达标", "无严重Bug"],
        dependencies=["development"],
    ))

    # 阶段5: 文档编写
    pipeline.add_stage(WorkflowStage(
        name="documentation",
        description="文档编写与维护",
        role="doc_writer",
        inputs=["code", "architecture"],
        outputs=["api_doc", "user_guide", "release_notes"],
        quality_gates=["文档完整性检查"],
        dependencies=["development"],
    ))

    # 阶段6: 发布评审
    pipeline.add_stage(WorkflowStage(
        name="release",
        description="发布评审",
        role="project_manager",
        inputs=["test_results", "documentation"],
        outputs=["release_approval", "deployment_plan"],
        quality_gates=["所有测试通过", "文档齐全"],
        dependencies=["testing", "documentation"],
    ))

    return pipeline


def create_feature_pipeline() -> WorkflowPipeline:
    """
    创建功能开发流水线（简化版）

    流程: 需求 → 开发 → 测试
    """
    pipeline = WorkflowPipeline("feature_pipeline")

    pipeline.add_stage(WorkflowStage(
        name="requirements",
        description="需求分析",
        role="product_manager",
        inputs=["feature_request"],
        outputs=["requirements", "acceptance_criteria"],
        dependencies=[],
    ))

    pipeline.add_stage(WorkflowStage(
        name="development",
        description="功能开发",
        role="developer",
        inputs=["requirements"],
        outputs=["code", "unit_tests"],
        dependencies=["requirements"],
    ))

    pipeline.add_stage(WorkflowStage(
        name="testing",
        description="功能测试",
        role="tester",
        inputs=["code", "acceptance_criteria"],
        outputs=["test_results"],
        dependencies=["development"],
    ))

    return pipeline


def create_bugfix_pipeline() -> WorkflowPipeline:
    """
    创建Bug修复流水线

    流程: Bug分析 → 修复 → 测试
    """
    pipeline = WorkflowPipeline("bugfix_pipeline")

    pipeline.add_stage(WorkflowStage(
        name="analysis",
        description="Bug分析",
        role="developer",
        inputs=["bug_report"],
        outputs=["root_cause", "fix_plan"],
        dependencies=[],
    ))

    pipeline.add_stage(WorkflowStage(
        name="fix",
        description="Bug修复",
        role="developer",
        inputs=["root_cause", "fix_plan"],
        outputs=["fixed_code", "regression_tests"],
        dependencies=["analysis"],
    ))

    pipeline.add_stage(WorkflowStage(
        name="verification",
        description="验证测试",
        role="tester",
        inputs=["fixed_code", "bug_report"],
        outputs=["verification_result"],
        dependencies=["fix"],
    ))

    return pipeline


def create_adversarial_pipeline(
    intensity: str = "normal",
    max_rounds: int = 3,
) -> WorkflowPipeline:
    """
    创建对抗性流水线

    在每个产出阶段后自动添加审查阶段:
    development -> adversarial_review -> testing

    Args:
        intensity: 审查强度 ("normal" | "aggressive")
        max_rounds: 最大对抗轮次

    Returns:
        配置好对抗审查的流水线
    """
    pipeline = WorkflowPipeline("adversarial_pipeline")

    # 对抗配置
    adversarial_cfg = AdversarialStageConfig(
        enabled=True,
        intensity=intensity,
        max_rounds=max_rounds,
        auto_fix=True,
    )

    # 阶段1: 需求分析
    pipeline.add_stage(WorkflowStage(
        name="requirements",
        description="需求分析",
        role="product_manager",
        inputs=["user_request"],
        outputs=["requirements", "acceptance_criteria"],
        dependencies=[],
    ))

    # 阶段2: 设计
    pipeline.add_stage(WorkflowStage(
        name="design",
        description="架构设计",
        role="architect",
        inputs=["requirements"],
        outputs=["design_doc", "tech_stack"],
        dependencies=["requirements"],
    ))

    # 阶段3: 开发
    pipeline.add_stage(WorkflowStage(
        name="development",
        description="功能开发",
        role="developer",
        inputs=["design_doc", "requirements"],
        outputs=["code", "unit_tests"],
        dependencies=["design"],
        adversarial_config=adversarial_cfg,
    ))

    # 阶段4: 对抗审查（新增）
    pipeline.add_stage(WorkflowStage(
        name="adversarial_review",
        description="对抗性代码审查",
        role="code_reviewer" if intensity == "normal" else "bug_hunter",
        inputs=["code"],
        outputs=["review_result", "issues"],
        dependencies=["development"],
    ))

    # 阶段5: 测试
    pipeline.add_stage(WorkflowStage(
        name="testing",
        description="功能测试",
        role="tester",
        inputs=["code", "acceptance_criteria", "review_result"],
        outputs=["test_results"],
        dependencies=["adversarial_review"],
    ))

    # 阶段6: 发布
    pipeline.add_stage(WorkflowStage(
        name="release",
        description="发布评审",
        role="project_manager",
        inputs=["test_results", "review_result"],
        outputs=["release_approval"],
        dependencies=["testing"],
    ))

    return pipeline