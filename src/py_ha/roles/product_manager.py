"""
Product Manager Role - 产品经理角色（渐进式披露版）

职责:
- 需求分析与整理
- 用户故事编写
- 需求文档维护
- 需求变更管理

特点:
- 在独立对话框与用户交互
- 只维护需求文档
- 需求变更通过PM协调到其他角色
- 支持多会话需求讨论

渐进式披露:
- 项目基本信息
- 完整需求文档
- 进度摘要（了解开发进展）
"""

from typing import Any
from pydantic import BaseModel, Field
import time

from py_ha.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    SkillCategory,
    TaskType,
)
from py_ha.project.state import DocumentType


class ProductManagerContext(BaseModel):
    """产品经理上下文"""

    project_name: str = Field(default="", description="项目名称")
    tech_stack: str = Field(default="", description="技术栈")
    requirements: str = Field(default="", description="需求文档")
    progress_summary: str = Field(default="", description="进度摘要")
    conversation_history: list[dict[str, str]] = Field(default_factory=list, description="对话历史")


class ProductManager(AgentRole):
    """
    产品经理 - 专注于需求管理

    Harness角色定义:
    - 职责边界: 需求分析、需求文档维护、需求变更管理
    - 技能集: 需求分析、用户故事、优先级
    - 协作: 在独立对话框与用户交互，变更通知PM

    渐进式披露特点:
    - 只维护需求文档
    - 看不到设计、开发等详细内容
    - 只能看到进度摘要
    """

    def __init__(
        self,
        role_id: str = "pm_req_1",
        name: str = "产品经理",
        context: RoleContext | None = None,
    ) -> None:
        super().__init__(role_id=role_id, name=name, context=context)
        self._pm_context: ProductManagerContext = ProductManagerContext()
        self._state_manager: Any = None
        self._pending_changes: list[dict[str, Any]] = []

    @property
    def role_type(self) -> RoleType:
        return RoleType.PRODUCT_MANAGER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "需求收集与分析",
            "需求文档维护",
            "用户故事编写",
            "优先级定义与排序",
            "验收标准制定",
            "需求变更管理",
        ]

    def set_state_manager(self, state_manager: Any) -> None:
        """
        设置项目状态管理器

        Args:
            state_manager: ProjectStateManager 实例
        """
        self._state_manager = state_manager

    def set_context_from_pm(self, context: dict[str, Any]) -> None:
        """
        设置来自PM的上下文

        Args:
            context: PM生成的上下文
        """
        self._pm_context = ProductManagerContext(
            project_name=context.get("project", {}).get("name", ""),
            tech_stack=context.get("project", {}).get("tech_stack", ""),
            requirements=context.get("requirements", ""),
            progress_summary=context.get("progress_summary", ""),
        )

    def get_visible_context(self) -> dict[str, Any]:
        """获取可见上下文"""
        return self._pm_context.model_dump()

    def _setup_skills(self) -> None:
        """设置产品技能"""
        skills = [
            RoleSkill(
                name="analyze_requirement",
                description="分析需求",
                category=SkillCategory.ANALYSIS,
                inputs=["user_input", "business_goal"],
                outputs=["requirements", "constraints"],
            ),
            RoleSkill(
                name="write_user_story",
                description="编写用户故事",
                category=SkillCategory.DOCUMENTATION,
                inputs=["requirement"],
                outputs=["user_stories", "acceptance_criteria"],
            ),
            RoleSkill(
                name="prioritize",
                description="优先级排序",
                category=SkillCategory.MANAGEMENT,
                inputs=["requirements", "constraints"],
                outputs=["prioritized_backlog"],
            ),
            RoleSkill(
                name="define_acceptance_criteria",
                description="定义验收标准",
                category=SkillCategory.ANALYSIS,
                inputs=["user_story"],
                outputs=["acceptance_criteria", "test_scenarios"],
            ),
            RoleSkill(
                name="update_requirements",
                description="更新需求文档",
                category=SkillCategory.DOCUMENTATION,
                inputs=["changes"],
                outputs=["updated_requirements"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.ANALYZE_REQUIREMENT,
            TaskType.WRITE_USER_STORY,
            TaskType.PRIORITIZE,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        handlers = {
            TaskType.ANALYZE_REQUIREMENT: self._analyze_requirement,
            TaskType.WRITE_USER_STORY: self._write_user_story,
            TaskType.PRIORITIZE: self._prioritize,
        }

        handler = handlers.get(task_type)
        if handler:
            return handler()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    # ==================== 需求讨论（独立对话框） ====================

    def discuss_with_user(self, message: str) -> str:
        """
        与用户讨论需求（在产品经理对话框中调用）

        Args:
            message: 用户消息

        Returns:
            回复内容
        """
        # 记录对话历史
        self._pm_context.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": str(time.time()),
        })

        # 分析用户消息，判断是否需要更新需求
        response = self._analyze_user_message(message)

        # 记录回复
        self._pm_context.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": str(time.time()),
        })

        return response

    def _analyze_user_message(self, message: str) -> str:
        """
        分析用户消息

        Args:
            message: 用户消息

        Returns:
            分析结果
        """
        # 检测是否包含需求变更关键词
        change_keywords = ["新增", "修改", "删除", "变更", "调整", "优化"]
        has_change = any(kw in message for kw in change_keywords)

        if has_change:
            return f"收到您的需求变更。我会更新需求文档并通知项目经理协调开发团队。\n\n当前项目: {self._pm_context.project_name}\n请确认变更详情。"
        else:
            return f"理解您的需求。当前项目技术栈: {self._pm_context.tech_stack}。\n请详细描述您的需求，我会整理到需求文档中。"

    # ==================== 需求文档管理 ====================

    def get_requirements(self) -> str:
        """
        获取当前需求文档

        Returns:
            需求文档内容
        """
        if self._state_manager:
            return self._state_manager.get_document(
                DocumentType.REQUIREMENTS,
                "product_manager",
                full=True,
            ) or ""
        return self._pm_context.requirements

    def update_requirements(self, new_content: str, change_summary: str = "") -> bool:
        """
        更新需求文档

        Args:
            new_content: 新的需求内容
            change_summary: 变更摘要

        Returns:
            是否成功
        """
        if self._state_manager:
            success = self._state_manager.update_document(
                DocumentType.REQUIREMENTS,
                new_content,
                "product_manager",
                change_summary,
            )
            if success:
                self._pm_context.requirements = new_content
                # 记录待通知的变更
                self._pending_changes.append({
                    "type": "requirements_update",
                    "summary": change_summary,
                    "timestamp": time.time(),
                })
            return success
        return False

    def get_requirements_summary(self) -> str:
        """
        获取需求摘要（用于传递给其他角色）

        Returns:
            需求摘要
        """
        if self._state_manager:
            return self._state_manager.get_document_summary(DocumentType.REQUIREMENTS)
        return self._pm_context.requirements[:500] if self._pm_context.requirements else ""

    def get_pending_changes(self) -> list[dict[str, Any]]:
        """
        获取待通知的变更

        Returns:
            变更列表
        """
        return self._pending_changes

    def clear_pending_changes(self) -> None:
        """清空待通知变更"""
        self._pending_changes.clear()

    # ==================== 任务执行方法 ====================

    def _analyze_requirement(self) -> dict[str, Any]:
        """分析需求"""
        user_input = self._current_task.get("inputs", {}).get("user_input", "")

        result = {
            "status": "completed",
            "outputs": {
                "requirements": [
                    {"id": "REQ-001", "description": "核心功能需求"},
                    {"id": "REQ-002", "description": "性能需求"},
                    {"id": "REQ-003", "description": "安全需求"},
                ],
                "constraints": ["技术约束", "时间约束", "资源约束"],
                "analysis_summary": f"需求分析完成: {user_input}",
            },
        }

        self.context.add_artifact("requirements", result["outputs"]["requirements"])
        return result

    def _write_user_story(self) -> dict[str, Any]:
        """编写用户故事"""
        requirement = self._current_task.get("inputs", {}).get("requirement", "")

        result = {
            "status": "completed",
            "outputs": {
                "user_stories": [
                    {
                        "id": "US-001",
                        "as_a": "用户",
                        "i_want_to": "执行某操作",
                        "so_that": "实现某价值",
                        "points": 3,
                    }
                ],
                "acceptance_criteria": [
                    "Given: 前置条件",
                    "When: 执行操作",
                    "Then: 预期结果",
                ],
            },
        }

        self.context.add_artifact("user_stories", result["outputs"]["user_stories"])
        return result

    def _prioritize(self) -> dict[str, Any]:
        """优先级排序"""
        result = {
            "status": "completed",
            "outputs": {
                "prioritized_backlog": [
                    {"id": "US-001", "priority": "P0", "reason": "核心功能"},
                    {"id": "US-002", "priority": "P1", "reason": "重要功能"},
                    {"id": "US-003", "priority": "P2", "reason": "优化功能"},
                ],
            },
        }

        return result


def create_product_manager(
    pm_id: str = "pm_req_1",
    name: str = "产品经理",
    context: RoleContext | None = None,
) -> ProductManager:
    """创建产品经理实例"""
    return ProductManager(role_id=pm_id, name=name, context=context)