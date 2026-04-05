"""
Roles Module - Agent角色定义

Harness Engineering 核心理念：用真实团队角色替代抽象概念

生成器角色（产出）:
- Developer: 开发人员，负责编码实现
- Tester: 测试人员，负责测试编写
- ProductManager: 产品经理，负责需求管理
- Architect: 架构师，负责技术方案
- DocWriter: 文档管理员，负责文档编写
- ProjectManager: 项目经理，负责任务协调

判别器角色（对抗）:
- CodeReviewer: 代码审查者，负责代码质量审查
- BugHunter: 漏洞猎手，负责深度漏洞挖掘
"""

from py_ha.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    TaskType,
    SkillCategory,
    RoleCategory,
    create_role,
)
from py_ha.roles.developer import Developer, create_developer
from py_ha.roles.tester import Tester, create_tester
from py_ha.roles.product_manager import ProductManager, create_product_manager
from py_ha.roles.architect import Architect, create_architect
from py_ha.roles.doc_writer import DocWriter, create_doc_writer
from py_ha.roles.project_manager import ProjectManager, create_project_manager
from py_ha.roles.code_reviewer import CodeReviewer, create_code_reviewer
from py_ha.roles.bug_hunter import BugHunter, create_bug_hunter

__all__ = [
    # 基类
    "AgentRole",
    "RoleType",
    "RoleSkill",
    "RoleContext",
    "TaskType",
    "SkillCategory",
    "RoleCategory",
    "create_role",
    # 生成器角色
    "Developer",
    "Tester",
    "ProductManager",
    "Architect",
    "DocWriter",
    "ProjectManager",
    # 判别器角色
    "CodeReviewer",
    "BugHunter",
    # 便捷函数
    "create_developer",
    "create_tester",
    "create_product_manager",
    "create_architect",
    "create_doc_writer",
    "create_project_manager",
    "create_code_reviewer",
    "create_bug_hunter",
]