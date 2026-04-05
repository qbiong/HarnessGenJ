"""
Architect Role - 架构师角色

职责:
- 系统架构设计
- 技术方案评审
- 技术选型
- 架构演进规划

技能:
- design_system: 系统设计
- review_architecture: 架构评审
- select_tech_stack: 技术选型
- define_patterns: 定义设计模式
"""

from typing import Any
from harnessgenj.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    SkillCategory,
    TaskType,
)


class Architect(AgentRole):
    """
    架构师 - 负责技术架构

    Harness角色定义:
    - 职责边界: 架构设计、技术决策、技术债务管理
    - 技能集: 系统设计、技术选型、评审
    - 协作: 向Developer提供设计方案，评审实现
    """

    @property
    def role_type(self) -> RoleType:
        return RoleType.ARCHITECT

    @property
    def responsibilities(self) -> list[str]:
        return [
            "系统架构设计",
            "技术方案评审",
            "技术选型决策",
            "设计模式定义",
            "技术债务管理",
            "架构文档编写",
        ]

    def _setup_skills(self) -> None:
        """设置架构技能"""
        skills = [
            RoleSkill(
                name="design_system",
                description="系统架构设计",
                category=SkillCategory.DESIGN,
                inputs=["requirements", "constraints"],
                outputs=["architecture", "design_doc"],
            ),
            RoleSkill(
                name="review_architecture",
                description="架构评审",
                category=SkillCategory.DESIGN,
                inputs=["architecture", "implementation"],
                outputs=["review_report", "recommendations"],
            ),
            RoleSkill(
                name="select_tech_stack",
                description="技术选型",
                category=SkillCategory.DESIGN,
                inputs=["requirements", "constraints"],
                outputs=["tech_stack", "rationale"],
            ),
            RoleSkill(
                name="define_patterns",
                description="定义设计模式",
                category=SkillCategory.DESIGN,
                inputs=["problem_domain"],
                outputs=["patterns", "guidelines"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.DESIGN_SYSTEM,
            TaskType.REVIEW_ARCHITECTURE,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        handlers = {
            TaskType.DESIGN_SYSTEM: self._design_system,
            TaskType.REVIEW_ARCHITECTURE: self._review_architecture,
        }

        handler = handlers.get(task_type)
        if handler:
            return handler()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    def _design_system(self) -> dict[str, Any]:
        """系统设计"""
        requirements = self._current_task.get("inputs", {}).get("requirements", [])

        result = {
            "status": "completed",
            "outputs": {
                "architecture": {
                    "layers": ["表现层", "业务层", "数据层"],
                    "components": ["API Gateway", "Service", "Repository"],
                    "patterns": ["MVC", "Repository", "Dependency Injection"],
                },
                "design_doc": "# 系统架构设计文档",
                "decisions": [
                    {"decision": "采用微服务架构", "rationale": "支持独立部署和扩展"},
                ],
            },
        }

        self.context.add_artifact("architecture", result["outputs"]["architecture"])
        return result

    def _review_architecture(self) -> dict[str, Any]:
        """架构评审"""
        implementation = self._current_task.get("inputs", {}).get("implementation", "")

        result = {
            "status": "completed",
            "outputs": {
                "review_report": {
                    "score": 85,
                    "strengths": ["模块划分清晰", "接口设计合理"],
                    "issues": ["部分模块耦合度较高"],
                },
                "recommendations": [
                    "建议引入消息队列解耦",
                    "考虑添加缓存层",
                ],
            },
        }

        return result


def create_architect(
    architect_id: str,
    name: str = "Architect",
    context: RoleContext | None = None,
) -> Architect:
    """创建架构师实例"""
    return Architect(role_id=architect_id, name=name, context=context)