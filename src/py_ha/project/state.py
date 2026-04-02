"""
ProjectStateManager - 项目状态管理器

作为项目经理的核心工具，提供:
1. 所有项目文档的统一管理
2. 渐进式信息披露（为不同角色生成最小必要上下文）
3. 文档版本管理和历史追溯
4. 项目状态持久化

渐进式披露原则:
- 项目经理: 可访问所有信息
- 产品经理: 只看到需求相关 + 项目基本信息
- 架构师: 只看到设计相关 + 需求摘要
- 开发者: 只看到项目基本信息 + 当前开发需求 + 相关设计摘要
- 测试人员: 只看到测试相关 + 需求摘要
"""

from typing import Any
from pydantic import BaseModel, Field
import os
import json
import time

from py_ha.project.document import (
    ProjectDocument,
    DocumentType,
    DOCUMENT_OWNERSHIP,
)


class ProjectInfo(BaseModel):
    """项目基本信息"""

    name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目描述")
    tech_stack: str = Field(default="", description="技术栈")
    status: str = Field(default="init", description="项目状态: init/in_progress/completed")
    current_phase: str = Field(default="", description="当前阶段")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")


class ProjectStats(BaseModel):
    """项目统计信息"""

    features_total: int = Field(default=0, description="功能总数")
    features_completed: int = Field(default=0, description="已完成功能")
    bugs_total: int = Field(default=0, description="Bug总数")
    bugs_fixed: int = Field(default=0, description="已修复Bug")
    progress: int = Field(default=0, description="进度百分比")


class ProjectStateManager:
    """
    项目状态管理器

    核心职责:
    1. 管理项目所有文档（CRUD）
    2. 提供渐进式信息披露
    3. 维护项目状态和统计
    4. 持久化到文件系统

    使用示例:
        state = ProjectStateManager(".py_ha")
        state.initialize("电商平台", "Python + FastAPI")

        # 获取开发者上下文（最小信息）
        context = state.get_context_for_role("developer")

        # 更新需求文档
        state.update_document("requirements", "# 需求\n...", "product_manager")
    """

    def __init__(self, workspace: str = ".py_ha"):
        """
        初始化状态管理器

        Args:
            workspace: 工作空间路径
        """
        self.workspace = workspace
        self.documents: dict[str, ProjectDocument] = {}
        self.project_info = ProjectInfo()
        self.stats = ProjectStats()

        # 确保目录存在
        self._ensure_directories()

        # 尝试加载已有数据
        self._load()

    def _ensure_directories(self) -> None:
        """确保所有必要目录存在"""
        dirs = [
            self.workspace,
            os.path.join(self.workspace, "documents"),
            os.path.join(self.workspace, "summaries"),
            os.path.join(self.workspace, "history"),
            os.path.join(self.workspace, "sessions"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    # ==================== 项目管理 ====================

    def initialize(
        self,
        name: str,
        tech_stack: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """
        初始化项目

        Args:
            name: 项目名称
            tech_stack: 技术栈
            description: 项目描述

        Returns:
            项目信息
        """
        self.project_info = ProjectInfo(
            name=name,
            tech_stack=tech_stack,
            description=description,
            status="init",
        )

        # 创建默认文档
        for doc_type in [
            DocumentType.REQUIREMENTS,
            DocumentType.DESIGN,
            DocumentType.DEVELOPMENT,
            DocumentType.TESTING,
            DocumentType.PROGRESS,
        ]:
            self.documents[doc_type] = ProjectDocument.create(doc_type)

        self._save()

        return self.project_info.model_dump()

    def get_project_info(self) -> dict[str, Any]:
        """获取项目基本信息"""
        return self.project_info.model_dump()

    def update_project_info(self, **kwargs: Any) -> bool:
        """
        更新项目信息

        Args:
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        for key, value in kwargs.items():
            if hasattr(self.project_info, key):
                setattr(self.project_info, key, value)
        self.project_info.updated_at = time.time()
        self._save()
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取项目统计"""
        return self.stats.model_dump()

    # ==================== 文档管理 ====================

    def get_document(
        self,
        doc_type: str,
        role: str = "project_manager",
        full: bool = True,
    ) -> str | None:
        """
        获取文档内容（基于角色权限）

        Args:
            doc_type: 文档类型
            role: 请求角色
            full: 是否获取完整内容（False 返回摘要）

        Returns:
            文档内容，无权限返回 None
        """
        doc = self.documents.get(doc_type)
        if not doc:
            return None

        return doc.get_content_for_role(role, full=full)

    def get_document_summary(self, doc_type: str) -> str:
        """
        获取文档摘要（任何人都可以获取摘要）

        Args:
            doc_type: 文档类型

        Returns:
            文档摘要
        """
        doc = self.documents.get(doc_type)
        if not doc:
            return ""

        if doc.summary:
            return doc.summary
        return doc._generate_summary()

    def update_document(
        self,
        doc_type: str,
        content: str,
        role: str,
        change_summary: str = "",
    ) -> bool:
        """
        更新文档

        Args:
            doc_type: 文档类型
            content: 新内容
            role: 更新者角色
            change_summary: 变更摘要

        Returns:
            是否更新成功
        """
        doc = self.documents.get(doc_type)
        if not doc:
            doc = ProjectDocument.create(doc_type)
            self.documents[doc_type] = doc

        success = doc.update(content, role, change_summary)
        if success:
            # 保存到文件
            self._save_document(doc_type)
            # 更新项目状态
            self.project_info.updated_at = time.time()
            self._save()

        return success

    def list_documents(self) -> list[dict[str, Any]]:
        """列出所有文档"""
        return [
            {
                "type": doc_type,
                "owner": doc.owner,
                "version": doc.version,
                "updated_at": doc.updated_at,
                "updated_by": doc.updated_by,
                "content_length": len(doc.content),
            }
            for doc_type, doc in self.documents.items()
        ]

    def get_document_history(
        self,
        doc_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        获取文档变更历史

        Args:
            doc_type: 文档类型
            limit: 返回数量

        Returns:
            历史记录列表
        """
        doc = self.documents.get(doc_type)
        if not doc:
            return []
        return doc.get_history(limit)

    # ==================== 渐进式披露核心 ====================

    def get_context_for_role(self, role_type: str) -> dict[str, Any]:
        """
        为角色生成最小必要上下文

        这是渐进式披露的核心方法，根据角色类型返回不同的信息：
        - project_manager: 所有信息
        - product_manager: 项目信息 + 需求文档 + 用户对话历史
        - architect: 项目信息 + 需求摘要 + 设计文档
        - developer: 项目信息 + 当前开发需求 + 相关设计摘要
        - tester: 项目信息 + 需求摘要 + 测试相关

        Args:
            role_type: 角色类型

        Returns:
            角色特定的上下文
        """
        # 项目基本信息（所有角色都可见）
        context = {
            "project": {
                "name": self.project_info.name,
                "tech_stack": self.project_info.tech_stack,
                "status": self.project_info.status,
                "current_phase": self.project_info.current_phase,
            },
            "stats": self.stats.model_dump(),
        }

        # 根据角色类型添加特定信息
        if role_type == "project_manager":
            # 项目经理可以看到所有信息
            context["documents"] = {
                doc_type: doc.content
                for doc_type, doc in self.documents.items()
            }
            context["full_access"] = True

        elif role_type == "product_manager":
            # 产品经理：需求文档完整 + 其他摘要
            context["requirements"] = self.get_document(
                DocumentType.REQUIREMENTS, role="product_manager", full=True
            ) or ""
            context["progress_summary"] = self.get_document_summary(DocumentType.PROGRESS)

        elif role_type == "architect":
            # 架构师：需求摘要 + 设计文档完整
            context["requirements_summary"] = self.get_document_summary(DocumentType.REQUIREMENTS)
            context["design"] = self.get_document(
                DocumentType.DESIGN, role="architect", full=True
            ) or ""

        elif role_type == "developer":
            # 开发者：最小信息
            context["requirements_summary"] = self.get_document_summary(DocumentType.REQUIREMENTS)
            context["design_summary"] = self.get_document_summary(DocumentType.DESIGN)
            context["development"] = self.get_document(
                DocumentType.DEVELOPMENT, role="developer", full=True
            ) or ""

        elif role_type == "tester":
            # 测试人员：需求摘要 + 测试文档
            context["requirements_summary"] = self.get_document_summary(DocumentType.REQUIREMENTS)
            context["testing"] = self.get_document(
                DocumentType.TESTING, role="tester", full=True
            ) or ""
            context["development_summary"] = self.get_document_summary(DocumentType.DEVELOPMENT)

        return context

    def get_project_summary(self) -> str:
        """
        获取项目总摘要

        用于快速了解项目状态，不包含详细文档内容

        Returns:
            项目摘要文本
        """
        summary_lines = [
            f"# {self.project_info.name}",
            "",
            f"**状态**: {self.project_info.status}",
            f"**技术栈**: {self.project_info.tech_stack}",
            f"**当前阶段**: {self.project_info.current_phase or '未开始'}",
            "",
            "## 进度",
            f"- 功能: {self.stats.features_completed}/{self.stats.features_total}",
            f"- Bug: {self.stats.bugs_fixed}/{self.stats.bugs_total}",
            f"- 总进度: {self.stats.progress}%",
        ]

        # 添加各文档摘要
        for doc_type in [
            DocumentType.REQUIREMENTS,
            DocumentType.DESIGN,
            DocumentType.DEVELOPMENT,
            DocumentType.TESTING,
        ]:
            doc = self.documents.get(doc_type)
            if doc and doc.content:
                summary_lines.append("")
                summary_lines.append(f"## {doc_type.upper()}")
                summary_lines.append(self.get_document_summary(doc_type)[:200] + "...")

        return "\n".join(summary_lines)

    # ==================== 持久化 ====================

    def _save(self) -> bool:
        """保存项目状态"""
        try:
            # 保存项目信息
            project_path = os.path.join(self.workspace, "project.json")
            with open(project_path, "w", encoding="utf-8") as f:
                json.dump({
                    "info": self.project_info.model_dump(),
                    "stats": self.stats.model_dump(),
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _save_document(self, doc_type: str) -> bool:
        """保存单个文档"""
        try:
            doc = self.documents.get(doc_type)
            if not doc:
                return False

            # 保存文档内容
            doc_path = os.path.join(self.workspace, "documents", f"{doc_type}.md")
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(doc.content)

            # 保存摘要
            if doc.summary:
                summary_path = os.path.join(self.workspace, "summaries", f"{doc_type}.summary.md")
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(doc.summary)

            # 保存历史版本
            if doc.history:
                for v in doc.history[-doc.max_history:]:
                    history_path = os.path.join(
                        self.workspace, "history", f"{doc_type}.v{v.version}.md"
                    )
                    with open(history_path, "w", encoding="utf-8") as f:
                        f.write(v.content)

            return True
        except Exception:
            return False

    def _load(self) -> bool:
        """加载项目状态"""
        try:
            # 加载项目信息
            project_path = os.path.join(self.workspace, "project.json")
            if os.path.exists(project_path):
                with open(project_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.project_info = ProjectInfo(**data.get("info", {}))
                    self.stats = ProjectStats(**data.get("stats", {}))

            # 加载文档
            for doc_type in [
                DocumentType.REQUIREMENTS,
                DocumentType.DESIGN,
                DocumentType.DEVELOPMENT,
                DocumentType.TESTING,
                DocumentType.PROGRESS,
            ]:
                doc_path = os.path.join(self.workspace, "documents", f"{doc_type}.md")
                if os.path.exists(doc_path):
                    with open(doc_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.documents[doc_type] = ProjectDocument.create(doc_type, content)
                else:
                    self.documents[doc_type] = ProjectDocument.create(doc_type)

            return True
        except Exception:
            return False

    def save_all(self) -> bool:
        """保存所有数据"""
        success = self._save()
        for doc_type in self.documents:
            success = success and self._save_document(doc_type)
        return success


def create_project_state(workspace: str = ".py_ha") -> ProjectStateManager:
    """创建项目状态管理器"""
    return ProjectStateManager(workspace=workspace)