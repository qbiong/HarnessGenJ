"""
Workflow Coordinator - 工作流协调器

Harness Engineering 核心组件:
- 协调多个角色协作
- 管理工作流执行
- 处理阶段间的交付物传递
- 追踪执行进度
"""

from typing import Any
from pydantic import BaseModel, Field
import time

from py_ha.workflow.pipeline import WorkflowPipeline, WorkflowStage, StageStatus
from py_ha.workflow.context import WorkflowContext
from py_ha.roles.base import AgentRole, RoleType, create_role


class CoordinatorStats(BaseModel):
    """协调器统计"""

    workflows_started: int = Field(default=0, description="启动的工作流数")
    workflows_completed: int = Field(default=0, description="完成的工作流数")
    workflows_failed: int = Field(default=0, description="失败的工作流数")
    stages_executed: int = Field(default=0, description="执行的阶段数")
    artifacts_produced: int = Field(default=0, description="产出的交付物数")


class WorkflowCoordinator:
    """
    工作流协调器 - Harness 核心组件

    职责:
    1. 角色管理: 创建和管理角色实例
    2. 工作流执行: 驱动流水线执行
    3. 交付物管理: 管理阶段间的交付物传递
    4. 进度追踪: 追踪和报告执行进度
    """

    def __init__(self) -> None:
        self._roles: dict[str, AgentRole] = {}
        self._workflows: dict[str, WorkflowPipeline] = {}
        self._contexts: dict[str, WorkflowContext] = {}
        self._stats = CoordinatorStats()

    # ==================== 角色管理 ====================

    def create_role(
        self,
        role_type: RoleType,
        role_id: str | None = None,
        name: str | None = None,
    ) -> AgentRole:
        """
        创建角色实例

        Args:
            role_type: 角色类型
            role_id: 角色ID（可选，自动生成）
            name: 角色名称（可选）

        Returns:
            创建的角色实例
        """
        import uuid
        role_id = role_id or f"{role_type.value}_{uuid.uuid4().hex[:8]}"
        name = name or role_type.value

        role = create_role(role_type, role_id, name)
        self._roles[role_id] = role

        return role

    def get_role(self, role_id: str) -> AgentRole | None:
        """获取角色"""
        return self._roles.get(role_id)

    def list_roles(self) -> list[dict[str, Any]]:
        """列出所有角色"""
        return [role.get_status() for role in self._roles.values()]

    def get_roles_by_type(self, role_type: RoleType) -> list[AgentRole]:
        """按类型获取角色"""
        return [r for r in self._roles.values() if r.role_type == role_type]

    # ==================== 工作流管理 ====================

    def register_workflow(self, workflow_id: str, pipeline: WorkflowPipeline) -> None:
        """注册工作流"""
        self._workflows[workflow_id] = pipeline

    def get_workflow(self, workflow_id: str) -> WorkflowPipeline | None:
        """获取工作流"""
        return self._workflows.get(workflow_id)

    def create_context(self, project_id: str, project_name: str = "") -> WorkflowContext:
        """创建工作流上下文"""
        context = WorkflowContext(
            project_id=project_id,
            project_name=project_name,
        )
        self._contexts[project_id] = context
        return context

    # ==================== 工作流执行 ====================

    def start_workflow(
        self,
        workflow_id: str,
        initial_inputs: dict[str, Any],
        context: WorkflowContext | None = None,
    ) -> dict[str, Any]:
        """
        启动工作流

        Args:
            workflow_id: 工作流ID
            initial_inputs: 初始输入
            context: 工作流上下文

        Returns:
            启动结果
        """
        pipeline = self._workflows.get(workflow_id)
        if not pipeline:
            return {"status": "error", "message": f"Workflow not found: {workflow_id}"}

        self._stats.workflows_started += 1

        # 存储初始输入
        for key, value in initial_inputs.items():
            pipeline.store_artifact(key, value)

        # 记录事件
        if context:
            context.record_event("workflow_started", {"workflow_id": workflow_id})

        return {
            "status": "started",
            "workflow_id": workflow_id,
            "pipeline_status": pipeline.get_status(),
        }

    def execute_stage(
        self,
        workflow_id: str,
        stage_name: str,
        executor_role_id: str | None = None,
    ) -> dict[str, Any]:
        """
        执行工作流阶段

        Args:
            workflow_id: 工作流ID
            stage_name: 阶段名称
            executor_role_id: 执行角色ID（可选，自动匹配）

        Returns:
            执行结果
        """
        pipeline = self._workflows.get(workflow_id)
        if not pipeline:
            return {"status": "error", "message": "Workflow not found"}

        stage = pipeline.get_stage(stage_name)
        if not stage:
            return {"status": "error", "message": f"Stage not found: {stage_name}"}

        if stage.status != StageStatus.PENDING:
            return {"status": "error", "message": f"Stage is {stage.status.value}"}

        # 检查依赖
        completed = {
            name for name, s in pipeline._stages.items()
            if s.status == StageStatus.COMPLETED
        }
        if not stage.can_start(completed):
            return {"status": "blocked", "message": "Dependencies not met"}

        # 获取或创建执行角色
        role = None
        if executor_role_id:
            role = self._roles.get(executor_role_id)
        else:
            # 自动匹配角色
            role_type_map = {
                # 生成器角色
                "product_manager": RoleType.PRODUCT_MANAGER,
                "architect": RoleType.ARCHITECT,
                "developer": RoleType.DEVELOPER,
                "tester": RoleType.TESTER,
                "doc_writer": RoleType.DOC_WRITER,
                "project_manager": RoleType.PROJECT_MANAGER,
                # 判别器角色
                "code_reviewer": RoleType.CODE_REVIEWER,
                "bug_hunter": RoleType.BUG_HUNTER,
            }
            role_type = role_type_map.get(stage.role)
            if role_type:
                roles = self.get_roles_by_type(role_type)
                role = roles[0] if roles else self.create_role(role_type)

        if not role:
            return {"status": "error", "message": "No available role for this stage"}

        # 准备输入
        inputs = {}
        for input_name in stage.inputs:
            artifact = pipeline.get_artifact(input_name)
            if artifact:
                inputs[input_name] = artifact

        # 执行阶段
        stage.start()

        task = {
            "type": stage_name,
            "description": stage.description,
            "inputs": inputs,
        }

        if role.assign_task(task):
            result = role.execute_task()
            stage.complete(result)

            # 存储输出
            if result.get("outputs"):
                for output_name, output_value in result["outputs"].items():
                    pipeline.store_artifact(output_name, output_value)

            self._stats.stages_executed += 1

            return {
                "status": "completed",
                "stage": stage_name,
                "result": result,
                "pipeline_status": pipeline.get_status(),
            }

        stage.fail("Failed to assign task to role")
        return {"status": "failed", "message": "Failed to assign task"}

    def run_workflow(
        self,
        workflow_id: str,
        initial_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        运行完整工作流

        自动按顺序执行所有阶段
        """
        result = self.start_workflow(workflow_id, initial_inputs)
        if result["status"] != "started":
            return result

        pipeline = self._workflows[workflow_id]
        results = []

        while True:
            ready_stages = pipeline.get_ready_stages()
            if not ready_stages:
                break

            for stage in ready_stages:
                stage_result = self.execute_stage(workflow_id, stage.name)
                results.append(stage_result)

                if stage_result["status"] == "failed":
                    self._stats.workflows_failed += 1
                    return {
                        "status": "failed",
                        "workflow_id": workflow_id,
                        "failed_stage": stage.name,
                        "results": results,
                    }

        status = pipeline.get_status()
        if status["failed"] > 0:
            self._stats.workflows_failed += 1
        else:
            self._stats.workflows_completed += 1

        return {
            "status": "completed",
            "workflow_id": workflow_id,
            "pipeline_status": status,
            "results": results,
            "artifacts": list(pipeline._artifacts.keys()),
        }

    # ==================== 状态查询 ====================

    def get_stats(self) -> CoordinatorStats:
        """获取统计"""
        return self._stats

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """获取工作流状态"""
        pipeline = self._workflows.get(workflow_id)
        if not pipeline:
            return None
        return pipeline.get_status()

    # ==================== 对抗调度 ====================

    def get_discriminator_for_stage(
        self,
        stage_name: str,
        intensity: str = "normal",
    ) -> AgentRole | None:
        """
        根据阶段自动选择判别器

        Args:
            stage_name: 阶段名称
            intensity: "normal" -> CodeReviewer, "aggressive" -> BugHunter

        Returns:
            判别器角色实例
        """
        role_type = RoleType.BUG_HUNTER if intensity == "aggressive" else RoleType.CODE_REVIEWER
        roles = self.get_roles_by_type(role_type)
        return roles[0] if roles else self.create_role(role_type)

    def schedule_adversarial_review(
        self,
        stage_name: str,
        artifacts: dict[str, Any],
        max_rounds: int = 3,
        intensity: str = "normal",
        generator_id: str | None = None,
    ) -> dict[str, Any]:
        """
        自动调度对抗审查

        Args:
            stage_name: 阶段名称
            artifacts: 产出物
            max_rounds: 最大对抗轮次
            intensity: 审查强度 ("normal" | "aggressive")
            generator_id: 生成者角色ID

        Returns:
            对抗审查结果
        """
        from py_ha.harness.adversarial import AdversarialWorkflow
        from py_ha.quality.score import ScoreManager
        from py_ha.quality.tracker import QualityTracker

        # 获取判别器
        discriminator = self.get_discriminator_for_stage(stage_name, intensity)
        if not discriminator:
            return {"status": "error", "message": "No discriminator available"}

        # 获取代码产出物
        code = artifacts.get("code", artifacts.get("implementation", ""))

        # 执行审查
        if intensity == "aggressive":
            from py_ha.roles.bug_hunter import BugHunter
            if isinstance(discriminator, BugHunter):
                result = discriminator.hunt(code)
                issues = result.vulnerabilities
                passed = result.risk_score < 30
            else:
                result = discriminator.review(code)
                issues = result.issues
                passed = result.passed
        else:
            result = discriminator.review(code)
            issues = result.issues
            passed = result.passed

        return {
            "status": "completed",
            "passed": passed,
            "issues": [{"description": i.description, "severity": i.severity.value} for i in issues],
            "reviewer_id": discriminator.role_id,
            "intensity": intensity,
        }


# ==================== 便捷函数 ====================

def create_coordinator() -> WorkflowCoordinator:
    """创建协调器实例"""
    return WorkflowCoordinator()