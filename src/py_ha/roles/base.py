"""
Agent Role Base - 角色基类定义

Harness Engineering 的核心：角色驱动的Agent协作

每个角色有:
1. 职责范围 (Responsibilities)
2. 技能集 (Skills)
3. 工作流程 (Workflow)
4. 协作接口 (Collaboration)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time


class RoleType(Enum):
    """角色类型"""

    # 生成器角色（产出）
    DEVELOPER = "developer"              # 开发人员
    TESTER = "tester"                    # 测试人员
    PRODUCT_MANAGER = "product_manager"  # 产品经理
    ARCHITECT = "architect"              # 架构师
    DOC_WRITER = "doc_writer"            # 文档管理员
    PROJECT_MANAGER = "project_manager"  # 项目经理
    # 判别器角色（对抗）
    CODE_REVIEWER = "code_reviewer"      # 代码审查者
    BUG_HUNTER = "bug_hunter"            # 漏洞猎手


class RoleCategory(Enum):
    """角色分类"""

    GENERATOR = "generator"        # 生成器：产出代码/文档
    DISCRIMINATOR = "discriminator"  # 判别器：审查/验证产出


class SkillCategory(Enum):
    """技能分类"""

    CODING = "coding"           # 编码类
    TESTING = "testing"         # 测试类
    ANALYSIS = "analysis"       # 分析类
    DOCUMENTATION = "docs"      # 文档类
    MANAGEMENT = "management"   # 管理类
    DESIGN = "design"           # 设计类


class RoleSkill(BaseModel):
    """
    角色技能 - 每个角色具备的具体能力

    技能定义:
    - 名称和描述
    - 执行函数
    - 输入输出规范
    - 依赖关系
    """

    name: str = Field(..., description="技能名称")
    description: str = Field(..., description="技能描述")
    category: SkillCategory = Field(..., description="技能分类")
    inputs: list[str] = Field(default_factory=list, description="所需输入")
    outputs: list[str] = Field(default_factory=list, description="产出输出")
    dependencies: list[str] = Field(default_factory=list, description="依赖的其他技能")
    executor: Callable | None = Field(default=None, description="执行函数", exclude=True)

    def can_execute(self, available_inputs: list[str]) -> bool:
        """检查是否有足够输入执行此技能"""
        return all(inp in available_inputs for inp in self.inputs)

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """执行技能"""
        if self.executor:
            return self.executor(**kwargs)
        return {"status": "no_executor", "skill": self.name}


class TaskType(Enum):
    """任务类型"""

    # 开发任务
    IMPLEMENT_FEATURE = "implement_feature"    # 实现功能
    FIX_BUG = "fix_bug"                        # 修复Bug
    REFACTOR = "refactor"                      # 重构代码
    CODE_REVIEW = "code_review"                # 代码审查

    # 测试任务
    WRITE_TEST = "write_test"                  # 编写测试
    RUN_TEST = "run_test"                      # 执行测试
    BUG_REPORT = "bug_report"                  # Bug报告

    # 产品任务
    ANALYZE_REQUIREMENT = "analyze_requirement"  # 需求分析
    WRITE_USER_STORY = "write_user_story"        # 用户故事
    PRIORITIZE = "prioritize"                    # 优先级排序

    # 架构任务
    DESIGN_SYSTEM = "design_system"            # 系统设计
    REVIEW_ARCHITECTURE = "review_architecture"  # 架构评审

    # 文档任务
    WRITE_DOC = "write_doc"                    # 编写文档
    UPDATE_DOC = "update_doc"                  # 更新文档

    # 管理任务
    COORDINATE = "coordinate"                  # 协调任务
    TRACK_PROGRESS = "track_progress"          # 进度追踪


class RoleContext(BaseModel):
    """
    角色上下文 - 执行任务时的环境信息

    包含:
    - 项目信息
    - 当前任务
    - 协作状态
    - 历史记录
    """

    project_id: str = Field(default="", description="项目ID")
    project_name: str = Field(default="", description="项目名称")
    current_task_id: str | None = Field(default=None, description="当前任务ID")
    working_directory: str = Field(default="", description="工作目录")
    collaborators: dict[str, str] = Field(default_factory=dict, description="协作者列表")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产出物")
    created_at: float = Field(default_factory=time.time, description="创建时间")

    def add_artifact(self, name: str, content: Any) -> None:
        """添加产出物"""
        self.artifacts[name] = {
            "content": content,
            "created_at": time.time(),
        }

    def get_artifact(self, name: str) -> Any | None:
        """获取产出物"""
        artifact = self.artifacts.get(name)
        return artifact["content"] if artifact else None


class AgentRole(ABC):
    """
    Agent角色基类 - 所有角色的抽象基类

    Harness Engineering 核心概念:
    - 每个角色有明确的职责边界
    - 每个角色有特定的技能集
    - 角色之间通过任务协作
    - 角色产出可追溯的交付物
    """

    def __init__(
        self,
        role_id: str,
        name: str,
        context: RoleContext | None = None,
    ) -> None:
        self.role_id = role_id
        self.name = name
        self.context = context or RoleContext()
        self._skills: dict[str, RoleSkill] = {}
        self._task_history: list[dict[str, Any]] = []
        self._current_task: dict[str, Any] | None = None

        # 初始化技能
        self._setup_skills()

    @property
    @abstractmethod
    def role_type(self) -> RoleType:
        """角色类型"""
        pass

    @property
    @abstractmethod
    def responsibilities(self) -> list[str]:
        """职责范围"""
        pass

    @property
    def is_discriminator(self) -> bool:
        """是否为判别器角色"""
        return self.role_type in (RoleType.CODE_REVIEWER, RoleType.BUG_HUNTER)

    @property
    def role_category(self) -> RoleCategory:
        """角色分类"""
        return RoleCategory.DISCRIMINATOR if self.is_discriminator else RoleCategory.GENERATOR

    @abstractmethod
    def _setup_skills(self) -> None:
        """设置技能集 - 子类实现"""
        pass

    # ==================== 技能管理 ====================

    def add_skill(self, skill: RoleSkill) -> None:
        """添加技能"""
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> RoleSkill | None:
        """获取技能"""
        return self._skills.get(name)

    def list_skills(self) -> list[RoleSkill]:
        """列出所有技能"""
        return list(self._skills.values())

    def has_skill(self, skill_name: str) -> bool:
        """检查是否有某技能"""
        return skill_name in self._skills

    # ==================== 任务执行 ====================

    def can_handle(self, task_type: TaskType) -> bool:
        """
        判断是否能处理某类型任务

        基于角色技能和任务类型匹配
        """
        return task_type in self.get_supported_task_types()

    @abstractmethod
    def get_supported_task_types(self) -> list[TaskType]:
        """获取支持的任务类型"""
        pass

    def assign_task(self, task: dict[str, Any]) -> bool:
        """
        分配任务

        Args:
            task: 任务信息，包含 type, description, inputs 等

        Returns:
            是否接受任务
        """
        task_type = task.get("type")

        # 如果是字符串，尝试转换为 TaskType，转换失败也接受
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                # 对于未知的任务类型，也接受（更灵活）
                pass

        # 如果是 TaskType，检查是否支持
        if isinstance(task_type, TaskType):
            if not self.can_handle(task_type):
                return False

        self._current_task = {
            **task,
            "type": task_type,
            "assigned_at": time.time(),
            "status": "assigned",
        }
        return True

    def execute_task(self) -> dict[str, Any]:
        """
        执行当前任务

        Returns:
            执行结果
        """
        if not self._current_task:
            return {"status": "error", "message": "No task assigned"}

        task_type = self._current_task.get("type")

        if isinstance(task_type, TaskType):
            result = self._execute_by_type(task_type)
        elif isinstance(task_type, str):
            result = self._execute_by_stage_name(task_type)
        else:
            result = {"status": "error", "message": f"Unknown task type: {task_type}"}

        # 记录历史
        self._task_history.append({
            "task": self._current_task,
            "result": result,
            "completed_at": time.time(),
        })

        self._current_task = None
        return result

    def _execute_by_stage_name(self, stage_name: str) -> dict[str, Any]:
        """
        按阶段名称执行任务 - 默认实现

        子类可以覆盖此方法来支持自定义阶段名称
        """
        return {
            "status": "completed",
            "outputs": {
                "result": f"Stage {stage_name} completed by {self.name}",
            },
        }

    @abstractmethod
    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        """按类型执行任务 - 子类实现"""
        pass

    # ==================== 协作 ====================

    def handoff_to(self, other_role: "AgentRole", artifact_name: str, artifact_content: Any) -> bool:
        """
        将产出物移交给其他角色

        Harness协作核心：角色间通过交付物协作
        """
        other_role.receive_handoff(self.name, artifact_name, artifact_content)
        return True

    def receive_handoff(self, from_role: str, artifact_name: str, artifact_content: Any) -> None:
        """接收其他角色的移交"""
        self.context.add_artifact(artifact_name, artifact_content)
        self.context.collaborators[from_role] = artifact_name

    def request_review(self, reviewer: "AgentRole", content: Any) -> str:
        """请求其他角色审查"""
        review_id = f"review_{time.time()}"
        reviewer.receive_handoff(self.name, f"review_request_{review_id}", content)
        return review_id

    # ==================== 状态 ====================

    def get_status(self) -> dict[str, Any]:
        """获取角色状态"""
        return {
            "role_id": self.role_id,
            "name": self.name,
            "role_type": self.role_type.value,
            "responsibilities": self.responsibilities,
            "skills": [s.name for s in self._skills.values()],
            "current_task": self._current_task,
            "task_history_count": len(self._task_history),
            "artifacts_count": len(self.context.artifacts),
        }

    def get_task_history(self) -> list[dict[str, Any]]:
        """获取任务历史"""
        return self._task_history.copy()


# ==================== 角色工厂 ====================

def create_role(
    role_type: RoleType,
    role_id: str,
    name: str | None = None,
    context: RoleContext | None = None,
) -> AgentRole:
    """
    创建角色实例

    Args:
        role_type: 角色类型
        role_id: 角色ID
        name: 角色名称
        context: 角色上下文

    Returns:
        角色实例
    """
    from py_ha.roles.developer import Developer
    from py_ha.roles.tester import Tester
    from py_ha.roles.product_manager import ProductManager
    from py_ha.roles.architect import Architect
    from py_ha.roles.doc_writer import DocWriter
    from py_ha.roles.project_manager import ProjectManager
    from py_ha.roles.code_reviewer import CodeReviewer
    from py_ha.roles.bug_hunter import BugHunter

    role_classes = {
        # 生成器角色
        RoleType.DEVELOPER: Developer,
        RoleType.TESTER: Tester,
        RoleType.PRODUCT_MANAGER: ProductManager,
        RoleType.ARCHITECT: Architect,
        RoleType.DOC_WRITER: DocWriter,
        RoleType.PROJECT_MANAGER: ProjectManager,
        # 判别器角色
        RoleType.CODE_REVIEWER: CodeReviewer,
        RoleType.BUG_HUNTER: BugHunter,
    }

    role_class = role_classes.get(role_type)
    if not role_class:
        raise ValueError(f"Unknown role type: {role_type}")

    return role_class(
        role_id=role_id,
        name=name or role_type.value,
        context=context,
    )