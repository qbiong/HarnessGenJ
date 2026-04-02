"""
Project Module - 项目管理模块

提供渐进式披露的项目管理能力：
- ProjectDocument: 文档实体，支持所有权和版本管理
- ProjectStateManager: 项目状态管理器，提供渐进式信息披露
- DocumentType: 文档类型常量

核心概念:
1. 项目经理维护所有文档，作为中央协调者
2. 每个角色只能访问自己相关的文档
3. 采用渐进式披露，减少Token消耗

使用示例:
    from py_ha.project import ProjectStateManager

    # 创建项目状态管理器
    state = ProjectStateManager(".py_ha")
    state.initialize("电商平台", "Python + FastAPI")

    # 获取开发者上下文（最小信息）
    context = state.get_context_for_role("developer")
    # 只包含: 项目信息 + 需求摘要 + 设计摘要

    # 更新需求文档
    state.update_document("requirements", "# 需求\\n...", "product_manager")
"""

from py_ha.project.document import (
    ProjectDocument,
    DocumentType,
    DocumentVersion,
    DOCUMENT_OWNERSHIP,
)
from py_ha.project.state import (
    ProjectStateManager,
    ProjectInfo,
    ProjectStats,
    create_project_state,
)

__all__ = [
    # 文档
    "ProjectDocument",
    "DocumentType",
    "DocumentVersion",
    "DOCUMENT_OWNERSHIP",
    # 状态管理
    "ProjectStateManager",
    "ProjectInfo",
    "ProjectStats",
    "create_project_state",
]