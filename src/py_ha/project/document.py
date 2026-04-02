"""
ProjectDocument - 项目文档实体

每个文档有明确的所有者、可见性控制和版本管理。
支持摘要生成、增量更新和历史追溯。

文档类型:
- requirements: 需求文档（产品经理维护）
- design: 设计文档（架构师维护）
- development: 开发日志（开发者维护）
- testing: 测试报告（测试人员维护）
- progress: 进度报告（项目经理维护）
"""

from typing import Any
from pydantic import BaseModel, Field
import time


class DocumentType:
    """文档类型常量"""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PROGRESS = "progress"


# 文档所有权配置
DOCUMENT_OWNERSHIP = {
    DocumentType.REQUIREMENTS: {
        "owner": "product_manager",
        "visible_to": ["project_manager", "product_manager", "developer"],
        "read_only_for": ["developer"],
    },
    DocumentType.DESIGN: {
        "owner": "architect",
        "visible_to": ["project_manager", "architect", "developer"],
        "read_only_for": ["developer"],
    },
    DocumentType.DEVELOPMENT: {
        "owner": "developer",
        "visible_to": ["project_manager", "developer"],
        "read_only_for": [],
    },
    DocumentType.TESTING: {
        "owner": "tester",
        "visible_to": ["project_manager", "tester", "developer"],
        "read_only_for": ["developer"],
    },
    DocumentType.PROGRESS: {
        "owner": "project_manager",
        "visible_to": ["project_manager", "product_manager", "architect", "developer", "tester"],
        "read_only_for": ["product_manager", "architect", "developer", "tester"],
    },
}


class DocumentVersion(BaseModel):
    """文档版本记录"""

    version: int = Field(..., description="版本号")
    content: str = Field(default="", description="该版本的完整内容")
    changed_by: str = Field(..., description="变更者角色")
    changed_at: float = Field(default_factory=time.time, description="变更时间")
    change_summary: str = Field(default="", description="变更摘要")


class ProjectDocument(BaseModel):
    """
    项目文档实体

    特点:
    - 明确的所有者和可见性控制
    - 版本历史管理（保存最近N个版本）
    - 支持摘要（用于渐进式披露）
    - Markdown 格式存储
    """

    doc_type: str = Field(..., description="文档类型")
    content: str = Field(default="", description="完整内容")
    summary: str = Field(default="", description="摘要（PM维护）")
    owner: str = Field(default="", description="所有者角色")
    visible_to: list[str] = Field(default_factory=list, description="可见角色列表")
    read_only_for: list[str] = Field(default_factory=list, description="只读角色列表")
    version: int = Field(default=1, description="当前版本号")
    updated_at: float = Field(default_factory=time.time, description="最后更新时间")
    updated_by: str = Field(default="", description="最后更新者")
    history: list[DocumentVersion] = Field(default_factory=list, description="版本历史")
    max_history: int = Field(default=5, description="最大历史版本数")

    def can_read(self, role_type: str) -> bool:
        """
        检查角色是否可读

        Args:
            role_type: 角色类型

        Returns:
            是否可读
        """
        return role_type in self.visible_to or role_type == self.owner

    def can_write(self, role_type: str) -> bool:
        """
        检查角色是否可写

        Args:
            role_type: 角色类型

        Returns:
            是否可写
        """
        if role_type == self.owner:
            return True
        if role_type in self.read_only_for:
            return False
        # 项目经理可以更新所有文档
        if role_type == "project_manager":
            return True
        return False

    def update(self, content: str, role: str, change_summary: str = "") -> bool:
        """
        更新文档内容

        Args:
            content: 新内容
            role: 更新者角色
            change_summary: 变更摘要

        Returns:
            是否更新成功
        """
        if not self.can_write(role):
            return False

        # 保存当前版本到历史
        if self.content:
            self.history.append(DocumentVersion(
                version=self.version,
                content=self.content,
                changed_by=self.updated_by,
                changed_at=self.updated_at,
                change_summary="",
            ))

            # 限制历史版本数量
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

        # 更新内容
        self.content = content
        self.version += 1
        self.updated_at = time.time()
        self.updated_by = role

        return True

    def get_content_for_role(self, role_type: str, full: bool = True) -> str | None:
        """
        获取对特定角色可见的内容

        Args:
            role_type: 角色类型
            full: 是否返回完整内容（False 返回摘要）

        Returns:
            可见内容，无权限返回 None
        """
        if not self.can_read(role_type):
            return None

        if full:
            return self.content
        else:
            return self.summary if self.summary else self._generate_summary()

    def _generate_summary(self) -> str:
        """生成简单摘要（取前500字符）"""
        if not self.content:
            return ""
        lines = self.content.split("\n")
        # 取标题和前几行
        summary_lines = []
        for line in lines[:20]:
            summary_lines.append(line)
            if len("\n".join(summary_lines)) > 500:
                break
        return "\n".join(summary_lines) + ("\n..." if len(self.content) > 500 else "")

    def get_history(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        获取变更历史

        Args:
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        return [
            {
                "version": v.version,
                "changed_by": v.changed_by,
                "changed_at": v.changed_at,
                "change_summary": v.change_summary,
            }
            for v in self.history[-limit:]
        ]

    def to_markdown(self) -> str:
        """导出为 Markdown 格式"""
        return self.content

    @classmethod
    def create(cls, doc_type: str, content: str = "") -> "ProjectDocument":
        """
        创建文档（自动设置所有权）

        Args:
            doc_type: 文档类型
            content: 初始内容

        Returns:
            文档实例
        """
        ownership = DOCUMENT_OWNERSHIP.get(doc_type, {
            "owner": "project_manager",
            "visible_to": ["project_manager"],
            "read_only_for": [],
        })

        return cls(
            doc_type=doc_type,
            content=content,
            owner=ownership["owner"],
            visible_to=ownership["visible_to"],
            read_only_for=ownership["read_only_for"],
        )