"""
Doc Writer Role - 文档管理员角色

职责:
- 技术文档编写
- API文档维护
- 用户手册编写
- 文档版本管理

技能:
- write_doc: 编写文档
- update_doc: 更新文档
- generate_api_doc: 生成API文档
- create_user_guide: 创建用户指南
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


class DocWriter(AgentRole):
    """
    文档管理员 - 负责文档管理

    Harness角色定义:
    - 职责边界: 文档编写、维护、版本管理
    - 技能集: 技术写作、API文档、用户指南
    - 协作: 收集各角色产出，整理成文档
    """

    @property
    def role_type(self) -> RoleType:
        return RoleType.DOC_WRITER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "技术文档编写",
            "API文档维护",
            "用户手册编写",
            "文档版本管理",
            "文档质量审核",
            "知识库维护",
        ]

    def _setup_skills(self) -> None:
        """设置文档技能"""
        skills = [
            RoleSkill(
                name="write_doc",
                description="编写文档",
                category=SkillCategory.DOCUMENTATION,
                inputs=["content", "template"],
                outputs=["document"],
            ),
            RoleSkill(
                name="update_doc",
                description="更新文档",
                category=SkillCategory.DOCUMENTATION,
                inputs=["document", "changes"],
                outputs=["updated_document"],
            ),
            RoleSkill(
                name="generate_api_doc",
                description="生成API文档",
                category=SkillCategory.DOCUMENTATION,
                inputs=["code", "annotations"],
                outputs=["api_documentation"],
            ),
            RoleSkill(
                name="create_user_guide",
                description="创建用户指南",
                category=SkillCategory.DOCUMENTATION,
                inputs=["features", "workflows"],
                outputs=["user_guide"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.WRITE_DOC,
            TaskType.UPDATE_DOC,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        handlers = {
            TaskType.WRITE_DOC: self._write_doc,
            TaskType.UPDATE_DOC: self._update_doc,
        }

        handler = handlers.get(task_type)
        if handler:
            return handler()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    def _write_doc(self) -> dict[str, Any]:
        """编写文档"""
        content = self._current_task.get("inputs", {}).get("content", "")

        result = {
            "status": "completed",
            "outputs": {
                "document": {
                    "title": "技术文档",
                    "sections": ["概述", "使用说明", "API参考", "FAQ"],
                    "content": f"# 文档内容\n\n{content}",
                    "format": "markdown",
                },
            },
        }

        self.context.add_artifact("document", result["outputs"]["document"])
        return result

    def _update_doc(self) -> dict[str, Any]:
        """更新文档"""
        changes = self._current_task.get("inputs", {}).get("changes", "")

        result = {
            "status": "completed",
            "outputs": {
                "updated_document": {
                    "version": "1.1.0",
                    "changes": changes,
                    "updated_at": "2024-01-01",
                },
            },
        }

        return result


def create_doc_writer(
    writer_id: str,
    name: str = "DocWriter",
    context: RoleContext | None = None,
) -> DocWriter:
    """创建文档管理员实例"""
    return DocWriter(role_id=writer_id, name=name, context=context)