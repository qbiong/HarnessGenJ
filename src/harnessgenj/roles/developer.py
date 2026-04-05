"""
Developer Role - 开发人员角色（渐进式披露版）

职责:
- 功能实现
- Bug修复
- 代码重构
- 代码审查

特点:
- 不获取完整项目信息
- 只接收：项目基本信息 + 当前开发需求 + 相关设计摘要
- 执行后更新开发日志
- 向PM汇报进度

渐进式披露:
- 项目名称、技术栈
- 当前任务需求
- 相关设计摘要（只读）
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


class DeveloperContext(BaseModel):
    """开发者上下文（最小信息）"""

    project_name: str = Field(default="", description="项目名称")
    tech_stack: str = Field(default="", description="技术栈")
    current_task: dict[str, Any] = Field(default_factory=dict, description="当前任务")
    requirements_summary: str = Field(default="", description="需求摘要（只读）")
    design_summary: str = Field(default="", description="设计摘要（只读）")


class Developer(AgentRole):
    """
    开发人员 - 只关注开发任务

    Harness角色定义:
    - 职责边界: 编码实现、Bug修复、代码质量
    - 技能集: 编码、调试、重构、审查
    - 协作: 接收PM任务（最小上下文），完成后汇报

    渐进式披露特点:
    - 不获取完整项目信息
    - 只能看到项目基本信息和当前任务
    - 设计和需求只能看到摘要
    """

    def __init__(
        self,
        role_id: str = "dev_1",
        name: str = "开发人员",
        context: RoleContext | None = None,
    ) -> None:
        super().__init__(role_id=role_id, name=name, context=context)
        self._dev_context: DeveloperContext = DeveloperContext()
        self._pm_callback: Any = None  # PM回调函数

    @property
    def role_type(self) -> RoleType:
        return RoleType.DEVELOPER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "功能开发与实现",
            "Bug诊断与修复",
            "代码重构与优化",
            "代码审查与改进",
            "单元测试编写",
            "向PM汇报进度",
        ]

    def set_context_from_pm(self, context: dict[str, Any]) -> None:
        """
        设置来自PM的最小上下文

        Args:
            context: PM生成的最小上下文
        """
        self._dev_context = DeveloperContext(
            project_name=context.get("project", {}).get("name", ""),
            tech_stack=context.get("project", {}).get("tech_stack", ""),
            current_task=context.get("current_task", {}),
            requirements_summary=context.get("requirements_summary", ""),
            design_summary=context.get("design_summary", ""),
        )

    def set_pm_callback(self, callback: Any) -> None:
        """
        设置PM回调函数

        Args:
            callback: 用于向PM汇报的回调函数
        """
        self._pm_callback = callback

    def get_visible_context(self) -> dict[str, Any]:
        """
        获取可见上下文

        Returns:
            开发者可见的最小信息
        """
        return self._dev_context.model_dump()

    def _setup_skills(self) -> None:
        """设置开发技能"""
        skills = [
            RoleSkill(
                name="implement_feature",
                description="实现新功能",
                category=SkillCategory.CODING,
                inputs=["requirement", "design"],
                outputs=["code", "tests"],
            ),
            RoleSkill(
                name="fix_bug",
                description="修复Bug",
                category=SkillCategory.CODING,
                inputs=["bug_report", "codebase"],
                outputs=["fixed_code", "test_case"],
            ),
            RoleSkill(
                name="refactor_code",
                description="重构代码",
                category=SkillCategory.CODING,
                inputs=["code", "refactor_goal"],
                outputs=["refactored_code"],
            ),
            RoleSkill(
                name="review_code",
                description="代码审查",
                category=SkillCategory.CODING,
                inputs=["code"],
                outputs=["review_comments", "approved"],
            ),
            RoleSkill(
                name="debug",
                description="调试代码",
                category=SkillCategory.CODING,
                inputs=["error_info", "code"],
                outputs=["root_cause", "fix"],
            ),
            RoleSkill(
                name="write_unit_test",
                description="编写单元测试",
                category=SkillCategory.TESTING,
                inputs=["code", "test_requirements"],
                outputs=["test_code", "coverage"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.IMPLEMENT_FEATURE,
            TaskType.FIX_BUG,
            TaskType.REFACTOR,
            TaskType.CODE_REVIEW,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        """执行开发任务"""
        handlers = {
            TaskType.IMPLEMENT_FEATURE: self._implement_feature,
            TaskType.FIX_BUG: self._fix_bug,
            TaskType.REFACTOR: self._refactor_code,
            TaskType.CODE_REVIEW: self._review_code,
        }

        handler = handlers.get(task_type)
        if handler:
            result = handler()
            # 执行完成后汇报给PM
            self._report_to_pm(result)
            return result
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    # ==================== 任务执行方法 ====================

    def _implement_feature(self) -> dict[str, Any]:
        """实现功能"""
        # 使用最小上下文
        task = self._dev_context.current_task
        requirement = task.get("description", "")
        design_summary = self._dev_context.design_summary

        # 模拟实现过程
        result = {
            "status": "completed",
            "outputs": {
                "code": f"# 实现: {requirement}\n# 技术栈: {self._dev_context.tech_stack}\n# 参考: {design_summary[:100]}...",
                "tests": "# 单元测试",
                "implementation_notes": "功能实现完成",
            },
            "metrics": {
                "lines_added": 100,
                "lines_removed": 0,
                "files_changed": 3,
            },
            "context_used": self._dev_context.model_dump(),
        }

        self.context.add_artifact("code", result["outputs"]["code"])
        return result

    def _fix_bug(self) -> dict[str, Any]:
        """修复Bug"""
        task = self._dev_context.current_task
        bug_report = task.get("description", "")

        result = {
            "status": "completed",
            "outputs": {
                "fixed_code": f"# Bug修复: {bug_report}",
                "test_case": "# 回归测试",
                "root_cause": "问题根因分析",
            },
            "metrics": {
                "fix_time": "30min",
                "affected_files": 1,
            },
        }

        self.context.add_artifact("bug_fix", result["outputs"]["fixed_code"])
        return result

    def _refactor_code(self) -> dict[str, Any]:
        """重构代码"""
        task = self._dev_context.current_task
        refactor_goal = task.get("description", "")

        result = {
            "status": "completed",
            "outputs": {
                "refactored_code": f"# 重构后代码: {refactor_goal}",
                "refactor_summary": "重构完成",
            },
            "metrics": {
                "complexity_reduction": "20%",
                "duplication_removed": "15%",
            },
        }

        return result

    def _review_code(self) -> dict[str, Any]:
        """代码审查"""
        task = self._dev_context.current_task

        result = {
            "status": "completed",
            "outputs": {
                "review_comments": [
                    {"line": 10, "comment": "建议使用更清晰的变量名"},
                    {"line": 25, "comment": "可以提取为独立函数"},
                ],
                "approved": True,
                "suggestions": ["添加类型注解", "增加文档字符串"],
            },
        }

        return result

    # ==================== 与PM通信 ====================

    def _report_to_pm(self, result: dict[str, Any]) -> bool:
        """
        向PM汇报进度

        Args:
            result: 执行结果

        Returns:
            是否汇报成功
        """
        if self._pm_callback:
            try:
                self._pm_callback(
                    role_type="developer",
                    artifact={
                        "code": result.get("outputs", {}).get("code", ""),
                        "tests": result.get("outputs", {}).get("tests", ""),
                        "status": result.get("status", ""),
                        "timestamp": time.time(),
                    },
                )
                return True
            except Exception:
                return False
        return False

    def report_progress(self, progress: dict[str, Any]) -> bool:
        """
        手动向PM汇报进度

        Args:
            progress: 进度信息

        Returns:
            是否汇报成功
        """
        return self._report_to_pm(progress)


# ==================== 便捷创建函数 ====================

def create_developer(
    developer_id: str = "dev_1",
    name: str = "开发人员",
    context: RoleContext | None = None,
) -> Developer:
    """创建开发人员实例"""
    return Developer(role_id=developer_id, name=name, context=context)