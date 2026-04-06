"""
Project Manager Role - 项目经理角色（中央协调者）

核心职责:
1. 维护项目所有文档
2. 调度其他角色执行任务
3. 管理项目状态和进度
4. 提供渐进式信息披露

特点:
- 作为中央协调者，拥有所有文档的访问和修改权限
- 为其他角色提供最小必要上下文
- 收集角色产出并更新项目文档
- 维护项目进度和状态

使用示例:
    pm = ProjectManager(state_manager=state)

    # 获取项目状态
    status = pm.get_project_status()

    # 调度开发者执行任务
    result = pm.assign_task_to_role("developer", {
        "type": "implement_feature",
        "description": "实现购物车功能",
    })

    # 收集产出
    pm.collect_artifact("developer", {"code": "shopping_cart.py"})

注意: 需求检测功能已移至 workflow/requirement_stage.py
       项目经理通过 RequirementDetectionStage 获取需求检测结果
"""

from typing import Any
from pydantic import BaseModel, Field
import time

from harnessgenj.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    SkillCategory,
    TaskType,
)
from harnessgenj.memory.manager import MemoryManager, DocumentType


class TaskAssignment(BaseModel):
    """任务分配记录"""

    task_id: str = Field(default="", description="任务ID")
    task_type: str = Field(default="", description="任务类型")
    assigned_to: str = Field(default="", description="分配给哪个角色")
    description: str = Field(default="", description="任务描述")
    status: str = Field(default="pending", description="状态: pending/in_progress/completed")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    completed_at: float | None = Field(default=None, description="完成时间")
    artifact: dict[str, Any] = Field(default_factory=dict, description="产出物")


class ProjectManager(AgentRole):
    """
    项目经理 - 中央协调者

    核心职责:
    1. 维护项目所有文档
    2. 调度其他角色执行任务
    3. 管理项目状态和进度
    4. 提供渐进式信息披露

    Harness角色定义:
    - 职责边界: 文档管理、任务调度、进度追踪、风险管理
    - 技能集: 协调、文档管理、上下文生成
    - 协作: 作为所有角色的协调中心

    渐进式披露:
    - 为开发者生成最小上下文：项目基本信息 + 当前需求
    - 为产品经理生成上下文：项目信息 + 需求文档
    - 为架构师生成上下文：项目信息 + 需求摘要 + 设计文档
    """

    def __init__(
        self,
        role_id: str = "pm_1",
        name: str = "项目经理",
        context: RoleContext | None = None,
        state_manager: MemoryManager | None = None,
    ) -> None:
        super().__init__(role_id=role_id, name=name, context=context)
        self.state = state_manager
        self._task_assignments: list[TaskAssignment] = []

    @property
    def role_type(self) -> RoleType:
        return RoleType.PROJECT_MANAGER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "项目文档管理",
            "角色任务调度",
            "进度追踪与报告",
            "资源分配与管理",
            "风险识别与应对",
            "渐进式信息披露",
            "团队沟通协调",
        ]

    def _setup_skills(self) -> None:
        """设置管理技能"""
        skills = [
            RoleSkill(
                name="coordinate",
                description="协调任务",
                category=SkillCategory.MANAGEMENT,
                inputs=["tasks", "team"],
                outputs=["assignments", "schedule"],
            ),
            RoleSkill(
                name="track_progress",
                description="进度追踪",
                category=SkillCategory.MANAGEMENT,
                inputs=["tasks", "milestones"],
                outputs=["progress_report", "blockers"],
            ),
            RoleSkill(
                name="manage_documents",
                description="文档管理",
                category=SkillCategory.MANAGEMENT,
                inputs=["document_type", "content"],
                outputs=["document_updated", "version"],
            ),
            RoleSkill(
                name="create_context",
                description="生成角色上下文",
                category=SkillCategory.MANAGEMENT,
                inputs=["role_type"],
                outputs=["context"],
            ),
            RoleSkill(
                name="manage_risks",
                description="风险管理",
                category=SkillCategory.MANAGEMENT,
                inputs=["project_context"],
                outputs=["risk_register", "mitigation_plan"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.COORDINATE,
            TaskType.TRACK_PROGRESS,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        handlers = {
            TaskType.COORDINATE: self._coordinate,
            TaskType.TRACK_PROGRESS: self._track_progress,
        }

        handler = handlers.get(task_type)
        if handler:
            return handler()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    # ==================== 项目管理核心方法 ====================

    def get_project_status(self) -> dict[str, Any]:
        """
        获取项目整体状态

        Returns:
            项目状态信息
        """
        if not self.state:
            return {"error": "State manager not initialized"}

        return {
            "project": self.state.get_project_info(),
            "stats": self.state.get_stats(),
            "documents": self.state.list_documents(),
            "summary": self.state.get_project_summary(),
        }

    def get_project_summary(self) -> str:
        """
        获取项目摘要

        Returns:
            项目摘要文本
        """
        if not self.state:
            return "项目状态管理器未初始化"
        return self.state.get_project_summary()

    # ==================== 角色调度 ====================

    def assign_task_to_role(
        self,
        role_type: str,
        task: dict[str, Any],
    ) -> dict[str, Any]:
        """
        向指定角色分配任务

        自动注入最小必要上下文，角色只能看到自己需要的信息

        Args:
            role_type: 角色类型 (developer, product_manager, architect, tester)
            task: 任务信息

        Returns:
            分配结果（包含角色上下文）
        """
        if not self.state:
            return {"error": "State manager not initialized"}

        # 创建任务分配记录
        assignment = TaskAssignment(
            task_id=f"task_{len(self._task_assignments) + 1}",
            task_type=task.get("type", "unknown"),
            assigned_to=role_type,
            description=task.get("description", ""),
            status="pending",
        )
        self._task_assignments.append(assignment)

        # 获取角色特定上下文（渐进式披露）
        role_context = self.state.get_context_for_role(role_type)

        # 添加任务特定信息
        role_context["current_task"] = task

        return {
            "assignment_id": assignment.task_id,
            "assigned_to": role_type,
            "context": role_context,
            "status": "assigned",
        }

    def collect_artifact(
        self,
        role_type: str,
        artifact: dict[str, Any],
    ) -> bool:
        """
        收集角色产出，更新相关文档

        Args:
            role_type: 角色类型
            artifact: 产出物

        Returns:
            是否成功
        """
        if not self.state:
            return False

        # 更新任务分配状态
        for assignment in self._task_assignments:
            if assignment.assigned_to == role_type and assignment.status == "pending":
                assignment.status = "completed"
                assignment.completed_at = time.time()
                assignment.artifact = artifact
                break

        # 根据角色类型更新对应文档
        if role_type == "developer":
            # 开发者产出更新开发日志
            current = self.state.get_document(DocumentType.DEVELOPMENT) or ""
            new_content = current + f"\n\n## {time.strftime('%Y-%m-%d %H:%M')}\n{artifact.get('code', '')}"
            self.state.store_document(DocumentType.DEVELOPMENT, new_content)

        elif role_type == "product_manager":
            # 产品经理产出更新需求文档
            if "requirements" in artifact:
                self.state.store_document(
                    DocumentType.REQUIREMENTS,
                    artifact["requirements"],
                )

        elif role_type == "architect":
            # 架构师产出更新设计文档
            if "design" in artifact:
                self.state.store_document(
                    DocumentType.DESIGN,
                    artifact["design"],
                )

        elif role_type == "tester":
            # 测试人员产出更新测试报告
            current = self.state.get_document(DocumentType.TESTING) or ""
            new_content = current + f"\n\n## {time.strftime('%Y-%m-%d %H:%M')}\n{artifact.get('report', '')}"
            self.state.store_document(DocumentType.TESTING, new_content)

        # 更新进度报告
        self._update_progress()

        return True

    def _update_progress(self) -> None:
        """更新进度报告"""
        if not self.state:
            return

        # 统计任务状态
        total = len(self._task_assignments)
        completed = sum(1 for a in self._task_assignments if a.status == "completed")

        # 生成进度报告
        progress_content = f"""# 项目进度报告

## 统计
- 总任务数: {total}
- 已完成: {completed}
- 进行中: {total - completed}
- 完成率: {(completed / total * 100) if total > 0 else 0:.1f}%

## 最近活动
"""
        for a in self._task_assignments[-5:]:
            status_emoji = "✅" if a.status == "completed" else "🔄"
            progress_content += f"\n{status_emoji} [{a.assigned_to}] {a.description[:50]}..."

        self.state.store_document(DocumentType.PROGRESS, progress_content)

    # ==================== 渐进式披露 ====================

    def create_context_for_developer(self) -> dict[str, Any]:
        """
        为开发者创建最小上下文

        只包含:
        - 项目基本信息（名称、技术栈）
        - 需求摘要
        - 设计摘要
        - 开发日志
        """
        if not self.state:
            return {}
        return self.state.get_context_for_role("developer")

    def create_context_for_product_manager(self) -> dict[str, Any]:
        """
        为产品经理创建上下文

        包含:
        - 项目基本信息
        - 完整需求文档
        - 进度摘要
        """
        if not self.state:
            return {}
        return self.state.get_context_for_role("product_manager")

    def create_context_for_architect(self) -> dict[str, Any]:
        """
        为架构师创建上下文

        包含:
        - 项目基本信息
        - 需求摘要
        - 完整设计文档
        """
        if not self.state:
            return {}
        return self.state.get_context_for_role("architect")

    def create_context_for_tester(self) -> dict[str, Any]:
        """
        为测试人员创建上下文

        包含:
        - 项目基本信息
        - 需求摘要
        - 测试文档
        - 开发摘要
        """
        if not self.state:
            return {}
        return self.state.get_context_for_role("tester")

    # ==================== 文档管理 ====================

    def get_document(self, doc_type: str, full: bool = True) -> str | None:
        """
        获取文档

        Args:
            doc_type: 文档类型
            full: 是否获取完整内容

        Returns:
            文档内容
        """
        if not self.state:
            return None
        if full:
            return self.state.get_document(doc_type)
        return self.state.get_document_summary(doc_type)

    def update_document(self, doc_type: str, content: str, summary: str = "") -> bool:
        """
        更新文档

        Args:
            doc_type: 文档类型
            content: 文档内容
            summary: 文档摘要（可选）

        Returns:
            是否成功
        """
        if not self.state:
            return False
        return self.state.store_document(doc_type, content)

    # ==================== 内部方法 ====================

    def _coordinate(self) -> dict[str, Any]:
        """协调任务"""
        tasks = self._current_task.get("inputs", {}).get("tasks", [])

        result = {
            "status": "completed",
            "outputs": {
                "assignments": [
                    {"task": t, "assignee": f"role_{i}", "deadline": "2024-01-01"}
                    for i, t in enumerate(tasks[:5])
                ],
                "schedule": {
                    "sprint": "Sprint 1",
                    "duration": "2 weeks",
                    "start_date": "2024-01-01",
                },
            },
        }

        return result

    def _track_progress(self) -> dict[str, Any]:
        """进度追踪"""
        if self.state:
            stats = self.state.get_stats()
            # stats 结构: {"project": ..., "stats": {...}, "memory": ..., "hotspots": ...}
            project_stats = stats.get("stats", {})
            result = {
                "status": "completed",
                "outputs": {
                    "progress_report": {
                        "total_features": project_stats.get("features_total", 0),
                        "completed_features": project_stats.get("features_completed", 0),
                        "total_bugs": project_stats.get("bugs_total", 0),
                        "fixed_bugs": project_stats.get("bugs_fixed", 0),
                        "completion_rate": f"{project_stats.get('progress', 0)}%",
                    },
                    "blockers": [],
                    "recommendations": [
                        "继续按计划推进",
                    ],
                },
            }
        else:
            result = {
                "status": "completed",
                "outputs": {
                    "progress_report": {
                        "total_tasks": 20,
                        "completed": 12,
                        "in_progress": 5,
                        "blocked": 3,
                        "completion_rate": "60%",
                    },
                    "blockers": [
                        {"task": "TASK-005", "reason": "等待外部依赖"},
                    ],
                    "recommendations": [
                        "建议增加资源处理阻塞任务",
                    ],
                },
            }

        return result


def create_project_manager(
    pm_id: str = "pm_1",
    name: str = "项目经理",
    context: RoleContext | None = None,
    state_manager: MemoryManager | None = None,
) -> ProjectManager:
    """创建项目经理实例"""
    return ProjectManager(
        role_id=pm_id,
        name=name,
        context=context,
        state_manager=state_manager,
    )