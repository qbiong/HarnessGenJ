"""
Harness - Harness Engineering 主入口

提供简洁的 API 来使用 Harness Engineering 框架

核心概念:
- Team: 开发团队，包含多个角色
- Pipeline: 工作流流水线
- Task: 待执行的任务
- Session: 多对话会话管理
- Persistence: 持久化存储，重启后自动恢复

使用示例:
    from py_ha import Harness

    # 创建 Harness 实例（默认持久化）
    harness = Harness("我的项目")

    # 快速开发功能
    result = harness.develop("实现用户登录功能")

    # 多对话支持
    harness.switch_session("product_manager")
    harness.chat("登录功能需要支持哪些方式？")

    harness.switch_session("development")
    harness.chat("继续开发...")

    # 下次启动时自动恢复之前的工作内容
"""

from typing import Any
from pydantic import BaseModel, Field
import time
import os
import json

from py_ha.roles import (
    AgentRole,
    RoleType,
    create_role,
)
from py_ha.workflow import (
    WorkflowCoordinator,
    WorkflowPipeline,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
)
from py_ha.memory import MemoryManager
from py_ha.storage import create_storage, StorageManager, StorageType
from py_ha.session import (
    SessionManager,
    SessionType,
    Session,
    MessageRole,
    Message,
)
from py_ha.guide import OnboardingGuide, ProjectConfig
from py_ha.project import (
    ProjectStateManager,
    DocumentType,
    get_document_region,
)


class HarnessStats(BaseModel):
    """Harness 统计"""

    features_developed: int = Field(default=0, description="开发的功能数")
    bugs_fixed: int = Field(default=0, description="修复的Bug数")
    workflows_completed: int = Field(default=0, description="完成的工作流数")
    team_size: int = Field(default=0, description="团队规模")
    messages_sent: int = Field(default=0, description="发送的消息数")


class Harness:
    """
    Harness - Harness Engineering 主入口类

    提供简洁的 API 来管理开发团队和工作流

    核心方法:
    - setup_team(): 组建开发团队
    - develop(): 快速开发功能
    - fix_bug(): 快速修复Bug
    - analyze(): 分析需求
    - review(): 代码审查
    - chat(): 多对话会话管理
    - switch_session(): 切换对话会话

    持久化支持:
    - 默认开启持久化，数据保存在 .py_ha/ 目录
    - 重启后自动加载之前的工作内容
    - 会话历史、项目配置、记忆都会持久化

    使用示例:
        # 默认持久化
        harness = Harness("我的项目")

        # 禁用持久化（仅内存）
        harness = Harness("我的项目", persistent=False)

        # 自定义存储路径
        harness = Harness("我的项目", workspace=".my_project")

        harness.setup_team()  # 创建默认团队
        result = harness.develop("用户登录功能")

        # 多对话支持
        harness.switch_session("product_manager")
        harness.chat("登录功能需求讨论...")

        harness.switch_session("development")
        harness.chat("继续开发...")
    """

    def __init__(
        self,
        project_name: str = "Default Project",
        *,
        persistent: bool = True,
        workspace: str = ".py_ha",
        config_path: str | None = None,
    ) -> None:
        """
        初始化 Harness 实例

        Args:
            project_name: 项目名称
            persistent: 是否持久化存储（默认 True）
            workspace: 工作空间目录（默认 .py_ha）
            config_path: 配置文件路径（可选）
        """
        self.project_name = project_name
        self._workspace = workspace
        self._persistent = persistent

        # 初始化核心组件
        self.coordinator = WorkflowCoordinator()

        # 存储系统
        self.storage = create_storage(persistent=persistent, base_path=workspace)

        # 记忆系统
        self.memory = MemoryManager()

        # 项目状态管理器（核心持久化组件）
        self.project_state: ProjectStateManager | None = None
        if persistent:
            self.project_state = ProjectStateManager(workspace)
            # 如果项目信息为空，初始化项目名称
            if not self.project_state.project_info.name:
                self.project_state.project_info.name = project_name
                self.project_state._save()
            else:
                # 恢复项目名称
                self.project_name = self.project_state.project_info.name

        # 会话管理（支持持久化）- 默认使用项目经理会话
        session_path = os.path.join(workspace, "sessions.json") if persistent else None
        self.sessions = SessionManager(persist_path=session_path)

        # 确保默认会话是项目经理（用户通过项目经理对接）
        if not self.sessions.get_active_session():
            self.sessions.switch_session(SessionType.PROJECT_MANAGER)

        # 统计
        self._stats = HarnessStats()

        # 引导系统
        guide_config_path = config_path or os.path.join(workspace, "config.json")
        self._guide = OnboardingGuide(guide_config_path)

        # 注册标准工作流
        self.coordinator.register_workflow("standard", create_standard_pipeline())
        self.coordinator.register_workflow("feature", create_feature_pipeline())
        self.coordinator.register_workflow("bugfix", create_bugfix_pipeline())

        # 尝试加载之前的工作状态
        if persistent:
            self._load_state()

    def _load_state(self) -> bool:
        """加载之前的工作状态"""
        state_path = os.path.join(self._workspace, "state.json")
        if not os.path.exists(state_path):
            return False

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 恢复项目名称
            if "project_name" in data:
                self.project_name = data["project_name"]

            # 恢复统计
            if "stats" in data:
                self._stats = HarnessStats(**data["stats"])

            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def _save_state(self) -> bool:
        """保存当前工作状态"""
        if not self._persistent:
            return False

        try:
            os.makedirs(self._workspace, exist_ok=True)

            state_path = os.path.join(self._workspace, "state.json")
            data = {
                "project_name": self.project_name,
                "stats": self._stats.model_dump(),
                "updated_at": time.time(),
            }

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 同时保存会话
            self.sessions.save()

            return True
        except Exception:
            return False

    def is_persistent(self) -> bool:
        """是否使用持久化存储"""
        return self._persistent

    def get_workspace(self) -> str:
        """获取工作空间路径"""
        return self._workspace

    # ==================== 团队管理 ====================

    def setup_team(self, team_config: dict[str, str] | None = None) -> dict[str, Any]:
        """
        组建开发团队

        Args:
            team_config: 团队配置，key=角色类型，value=角色名称
                        默认创建完整团队

        Returns:
            团队信息

        Examples:
            # 默认团队
            harness.setup_team()

            # 自定义团队
            harness.setup_team({
                "developer": "小李",
                "tester": "小张",
            })
        """
        if team_config is None:
            # 默认团队配置
            team_config = {
                "product_manager": "产品经理",
                "architect": "架构师",
                "developer": "开发人员",
                "tester": "测试人员",
                "doc_writer": "文档管理员",
                "project_manager": "项目经理",
            }

        role_type_map = {
            "product_manager": RoleType.PRODUCT_MANAGER,
            "architect": RoleType.ARCHITECT,
            "developer": RoleType.DEVELOPER,
            "tester": RoleType.TESTER,
            "doc_writer": RoleType.DOC_WRITER,
            "project_manager": RoleType.PROJECT_MANAGER,
        }

        created = []
        for role_type_str, name in team_config.items():
            role_type = role_type_map.get(role_type_str)
            if role_type:
                role_id = f"{role_type_str}_1"
                self.coordinator.create_role(role_type, role_id, name)
                created.append({"type": role_type_str, "name": name, "id": role_id})

        self._stats.team_size = len(created)

        return {
            "project": self.project_name,
            "team_size": len(created),
            "members": created,
        }

    def add_role(self, role_type: str, name: str) -> AgentRole:
        """
        添加单个角色

        Args:
            role_type: 角色类型 (developer, tester, product_manager 等)
            name: 角色名称

        Returns:
            创建的角色实例
        """
        role_type_map = {
            "product_manager": RoleType.PRODUCT_MANAGER,
            "architect": RoleType.ARCHITECT,
            "developer": RoleType.DEVELOPER,
            "tester": RoleType.TESTER,
            "doc_writer": RoleType.DOC_WRITER,
            "project_manager": RoleType.PROJECT_MANAGER,
        }

        rt = role_type_map.get(role_type.lower())
        if not rt:
            raise ValueError(f"Unknown role type: {role_type}")

        import uuid
        role_id = f"{role_type}_{uuid.uuid4().hex[:6]}"
        role = self.coordinator.create_role(rt, role_id, name)
        self._stats.team_size += 1

        return role

    def get_team(self) -> list[dict[str, Any]]:
        """获取团队信息"""
        return self.coordinator.list_roles()

    # ==================== 快速开发 ====================

    def develop(self, feature_request: str) -> dict[str, Any]:
        """
        快速开发功能（通过项目经理调度）

        流程: 项目经理接收 → 分配任务 → 开发实现 → 测试验证 → 项目经理确认

        Args:
            feature_request: 功能需求描述

        Returns:
            开发结果

        Examples:
            result = harness.develop("实现用户登录功能")
        """
        # 1. 项目经理接收请求
        task_info = self.receive_request(feature_request, request_type="feature")

        # 2. 确保有开发团队
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        # 3. 执行开发工作流
        result = self.coordinator.run_workflow(
            "feature",
            {"feature_request": feature_request},
        )

        # 4. 项目经理更新状态
        if result.get("status") == "completed":
            self._stats.features_developed += 1
            self._stats.workflows_completed += 1

            # 保存到记忆
            self.memory.store_conversation(
                f"功能开发: {feature_request}",
                role="system",
                importance=70,
            )

            # 项目经理标记任务完成
            if self.project_state and task_info.get("task_id"):
                self.complete_task(
                    task_info["task_id"],
                    summary=f"功能开发完成: {feature_request[:50]}"
                )

            # 保存状态
            self._save_state()

        return {
            "request": feature_request,
            "task_id": task_info.get("task_id"),
            "priority": task_info.get("priority"),
            "assignee": task_info.get("assignee"),
            "status": result.get("status"),
            "stages_completed": len(result.get("results", [])),
            "artifacts": result.get("artifacts", []),
        }

    def fix_bug(self, bug_description: str) -> dict[str, Any]:
        """
        快速修复 Bug（通过项目经理调度）

        流程: 项目经理接收 → 分配任务 → Bug分析 → 代码修复 → 验证测试

        Args:
            bug_description: Bug 描述

        Returns:
            修复结果

        Examples:
            result = harness.fix_bug("登录页面无法提交表单")
        """
        # 1. 项目经理接收请求
        task_info = self.receive_request(bug_description, request_type="bug")

        # 2. 确保有开发团队
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        # 3. 执行修复工作流
        result = self.coordinator.run_workflow(
            "bugfix",
            {"bug_report": bug_description},
        )

        # 4. 项目经理更新状态
        if result.get("status") == "completed":
            self._stats.bugs_fixed += 1
            self._stats.workflows_completed += 1

            # 保存到记忆
            self.memory.store_conversation(
                f"Bug修复: {bug_description}",
                role="system",
                importance=60,
            )

            # 项目经理标记任务完成
            if self.project_state and task_info.get("task_id"):
                self.complete_task(
                    task_info["task_id"],
                    summary=f"Bug修复完成: {bug_description[:50]}"
                )

            # 保存状态
            self._save_state()

        return {
            "bug": bug_description,
            "task_id": task_info.get("task_id"),
            "priority": task_info.get("priority"),
            "assignee": task_info.get("assignee"),
            "status": result.get("status"),
            "stages_completed": len(result.get("results", [])),
        }

    def analyze(self, requirement: str) -> dict[str, Any]:
        """
        分析需求

        Args:
            requirement: 需求描述

        Returns:
            分析结果
        """
        if not self.coordinator.get_roles_by_type(RoleType.PRODUCT_MANAGER):
            self.coordinator.create_role(RoleType.PRODUCT_MANAGER, "pm_auto", "产品经理")

        pm = self.coordinator.get_roles_by_type(RoleType.PRODUCT_MANAGER)[0]

        pm.assign_task({
            "type": "requirements",
            "description": f"分析需求: {requirement}",
            "inputs": {"user_input": requirement},
        })

        result = pm.execute_task()

        return {
            "requirement": requirement,
            "analysis": result.get("outputs", {}),
        }

    def design(self, system_description: str) -> dict[str, Any]:
        """
        设计系统架构

        Args:
            system_description: 系统描述

        Returns:
            设计结果
        """
        if not self.coordinator.get_roles_by_type(RoleType.ARCHITECT):
            self.coordinator.create_role(RoleType.ARCHITECT, "arch_auto", "架构师")

        arch = self.coordinator.get_roles_by_type(RoleType.ARCHITECT)[0]

        arch.assign_task({
            "type": "design",
            "description": f"设计系统: {system_description}",
            "inputs": {"requirements": system_description},
        })

        result = arch.execute_task()

        return {
            "system": system_description,
            "design": result.get("outputs", {}),
        }

    def review_code(self, code: str) -> dict[str, Any]:
        """
        代码审查

        Args:
            code: 待审查的代码

        Returns:
            审查结果
        """
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")

        dev = self.coordinator.get_roles_by_type(RoleType.DEVELOPER)[0]

        dev.assign_task({
            "type": "code_review",
            "description": "代码审查",
            "inputs": {"code": code},
        })

        result = dev.execute_task()

        return {
            "review": result.get("outputs", {}),
        }

    # ==================== 工作流管理 ====================

    def run_pipeline(self, pipeline_type: str = "feature", **inputs: Any) -> dict[str, Any]:
        """
        运行工作流

        Args:
            pipeline_type: 工作流类型 (standard, feature, bugfix)
            **inputs: 输入参数

        Returns:
            执行结果
        """
        result = self.coordinator.run_workflow(pipeline_type, inputs)

        if result.get("status") == "completed":
            self._stats.workflows_completed += 1

        return result

    def get_pipeline_status(self) -> dict[str, Any]:
        """获取工作流状态"""
        return {
            "stats": self._stats.model_dump(),
            "coordinator_stats": self.coordinator.get_stats().model_dump(),
        }

    # ==================== 记忆与存储 ====================

    def remember(self, key: str, content: str, important: bool = False) -> None:
        """
        记忆重要信息

        Args:
            key: 键名
            content: 内容
            important: 是否重要（重要信息永不清除）
        """
        if important:
            self.memory.store_important_knowledge(key, content)
        else:
            self.memory.store_conversation(content, importance=50)

        self.storage.save_knowledge(key, content)

        # 保存状态
        self._save_state()

    def recall(self, key: str) -> str | None:
        """
        回忆信息

        Args:
            key: 键名

        Returns:
            存储的内容
        """
        # 先从存储获取
        content = self.storage.load_knowledge(key)
        if content:
            return content

        # 再从记忆获取
        return self.memory.get_knowledge(key)

    # ==================== 智能记录（核心方法） ====================

    def receive_request(self, request: str, request_type: str = "feature") -> dict[str, Any]:
        """
        项目经理接收用户请求（核心入口方法）

        这是 AI 对话的主要入口，项目经理负责：
        1. 接收用户需求/Bug报告
        2. 分配优先级和负责人
        3. 更新项目文档和统计
        4. 创建任务并安排执行

        Args:
            request: 用户请求内容
            request_type: 请求类型 (feature/bug/task/discussion)

        Returns:
            处理结果，包含任务ID、优先级、负责人等信息

        Examples:
            # 用户提出需求
            harness.receive_request("我需要一个用户登录功能")

            # 用户报告 Bug
            harness.receive_request("登录页面验证码显示异常", request_type="bug")
        """
        if not self.project_state:
            return {"success": False, "error": "项目状态未初始化"}

        timestamp = time.strftime('%Y-%m-%d %H:%M')
        task_id = f"TASK-{int(time.time())}"

        # 根据请求类型分配优先级和负责人
        if request_type == "bug":
            priority = "P0"  # Bug 默认高优先级
            assignee = "developer"
            doc_type = DocumentType.TESTING
            category = "Bug修复"
        elif request_type == "feature":
            priority = "P1"  # 功能默认中优先级
            assignee = "developer"
            doc_type = DocumentType.REQUIREMENTS
            category = "功能开发"
        else:
            priority = "P2"
            assignee = "developer"
            doc_type = DocumentType.REQUIREMENTS
            category = "任务"

        # 1. 更新需求/测试文档（结构化格式）
        current_doc = self.project_state.get_document(
            doc_type, "project_manager", full=True
        ) or self._get_doc_header(doc_type)

        new_entry = f"""
### {category} [{priority}] ({timestamp})

**任务ID**: {task_id}
**描述**: {request}
**负责人**: {assignee}
**状态**: 待处理

---
"""
        self.project_state.update_document(
            doc_type,
            current_doc + new_entry,
            "project_manager",
            f"新增{category}: {request[:30]}..."
        )

        # 2. 更新进度文档
        progress_doc = self.project_state.get_document(
            DocumentType.PROGRESS, "project_manager", full=True
        ) or "# 项目进度\n"

        task_entry = f"""
## {task_id} - {category}

- **内容**: {request}
- **优先级**: {priority}
- **负责人**: {assignee}
- **状态**: 待处理
- **创建时间**: {timestamp}

"""
        self.project_state.update_document(
            DocumentType.PROGRESS,
            progress_doc + task_entry,
            "project_manager",
            f"创建任务: {task_id}"
        )

        # 3. 更新项目统计
        if request_type == "bug":
            self.project_state.stats.bugs_total += 1
        else:
            self.project_state.stats.features_total += 1

        # 4. 设置为当前任务（其他窗口可检测）
        self.project_state.set_current_task(task_id, request)

        self.project_state._save()

        # 5. 保存 Harness 状态
        self._save_state()

        return {
            "success": True,
            "task_id": task_id,
            "priority": priority,
            "assignee": assignee,
            "category": category,
            "status": "待处理",
            "timestamp": timestamp,
            "message": f"项目经理已接收请求，任务 {task_id} 已分配给 {assignee}，优先级 {priority}"
        }

    def _get_doc_header(self, doc_type: str) -> str:
        """获取文档标题"""
        headers = {
            DocumentType.REQUIREMENTS: "# 项目需求\n\n本文档记录所有功能需求和用户故事。\n",
            DocumentType.TESTING: "# 测试报告\n\n本文档记录 Bug 报告和测试结果。\n",
            DocumentType.DEVELOPMENT: "# 开发日志\n\n本文档记录开发过程和技术决策。\n",
            DocumentType.PROGRESS: "# 项目进度\n\n本文档记录任务进度和里程碑。\n",
            DocumentType.DESIGN: "# 设计文档\n\n本文档记录系统架构和设计方案。\n",
        }
        return headers.get(doc_type, "# 文档\n")

    def assign_task(self, task_id: str, assignee: str, priority: str = None) -> bool:
        """
        项目经理分配任务

        Args:
            task_id: 任务ID
            assignee: 负责人
            priority: 可选的新优先级

        Returns:
            是否成功
        """
        if not self.project_state:
            return False

        # 更新进度文档中的任务
        progress = self.project_state.get_document(
            DocumentType.PROGRESS, "project_manager", full=True
        ) or ""

        if task_id in progress:
            # 更新负责人
            import re
            if assignee:
                progress = re.sub(
                    rf'(\*\*负责人\*\*:\s*)\w+',
                    f'**负责人**: {assignee}',
                    progress
                )
            if priority:
                progress = re.sub(
                    rf'(\*\*优先级\*\*:\s*)P\d',
                    f'**优先级**: {priority}',
                    progress
                )

            self.project_state.update_document(
                DocumentType.PROGRESS,
                progress,
                "project_manager",
                f"分配任务 {task_id} 给 {assignee}"
            )
            self.project_state._save()
            return True

        return False

    def complete_task(self, task_id: str, summary: str = "") -> bool:
        """
        项目经理标记任务完成

        Args:
            task_id: 任务ID
            summary: 完成摘要

        Returns:
            是否成功
        """
        if not self.project_state:
            return False

        timestamp = time.strftime('%Y-%m-%d %H:%M')

        # 更新进度文档
        progress = self.project_state.get_document(
            DocumentType.PROGRESS, "project_manager", full=True
        ) or ""

        if task_id in progress:
            import re
            # 更新状态
            progress = re.sub(
                rf'(\*\*状态\*\*:\s*)\S+',
                f'**状态**: 已完成',
                progress
            )

            # 添加完成记录
            completion_note = f"\n  - **完成时间**: {timestamp}"
            if summary:
                completion_note += f"\n  - **完成说明**: {summary}"

            self.project_state.update_document(
                DocumentType.PROGRESS,
                progress + completion_note,
                "project_manager",
                f"完成任务: {task_id}"
            )

            # 更新统计
            self.project_state.stats.features_completed += 1
            self.project_state.stats.progress = int(
                self.project_state.stats.features_completed /
                max(self.project_state.stats.features_total, 1) * 100
            )

            # 清除当前任务
            self.project_state.clear_current_task()

            self.project_state._save()
            self._save_state()

            return True

        return False

    def record(self, content: str, context: str = "") -> bool:
        """
        智能记录内容到项目文档（自动识别类型）

        AI 对话时只需调用此方法，系统自动判断内容类型并持久化到对应文档。

        自动识别规则：
        - 需求类关键词（"需求"、"功能"、"需要"、"要"、"添加"、"新增"）
          → requirements.md
        - Bug类关键词（"bug"、"问题"、"错误"、"异常"、"失败"、"修复"）
          → testing.md
        - 进度类关键词（"完成"、"已"、"进度"、"状态"、"更新"）
          → progress.md
        - 其他内容 → development.md（开发日志）

        Args:
            content: 要记录的内容
            context: 可选的上下文信息（如 "用户说"、"AI分析"）

        Returns:
            是否成功记录

        Examples:
            # AI 自动记录用户需求
            harness.record("用户需要一个登录功能")

            # AI 记录分析结果
            harness.record("已完成登录模块开发", context="AI汇报")

            # AI 记录 Bug 信息
            harness.record("发现登录页面验证码显示异常")
        """
        if not self.project_state:
            return False

        # 关键词分类（优先级：进度 > Bug > 需求，因为需求关键词最宽泛）
        # 需求关键词：明确的需求表述
        requirement_keywords = ["需求", "功能", "需要", "要", "添加", "新增", "设计"]
        # Bug关键词：问题相关
        bug_keywords = ["bug", "问题", "错误", "异常", "失败", "修复", "fix", "报错", "崩溃"]
        # 进度关键词：状态更新（优先级最高）
        progress_keywords = ["完成", "已", "进度", "状态", "更新", "通过", "成功"]
        # 开发关键词：开发过程中的动作
        development_keywords = ["实现", "开发", "编写", "修改", "优化", "重构"]

        # 判断内容类型（按优先级匹配）
        content_lower = content.lower()
        doc_type = DocumentType.DEVELOPMENT  # 默认开发日志

        # 先匹配进度（最高优先级）
        if any(kw in content_lower for kw in progress_keywords):
            doc_type = DocumentType.PROGRESS
        # 再匹配 Bug
        elif any(kw in content_lower for kw in bug_keywords):
            doc_type = DocumentType.TESTING
        # 再匹配需求
        elif any(kw in content_lower for kw in requirement_keywords):
            doc_type = DocumentType.REQUIREMENTS
        # 开发动作默认已经是 development

        # 获取当前文档内容
        current = self.project_state.get_document(
            doc_type, "project_manager", full=True
        ) or ""

        # 格式化新条目
        timestamp = time.strftime('%Y-%m-%d %H:%M')
        context_prefix = f"[{context}] " if context else ""
        entry = f"\n\n## 记录 ({timestamp})\n\n{context_prefix}{content}\n"

        # 更新文档（使用 project_manager 角色，因为 PM 可以更新所有文档）
        success = self.project_state.update_document(
            doc_type,
            current + entry,
            "project_manager",  # PM 可以更新所有文档
            f"自动记录: {content[:30]}..."
        )

        if success:
            self.project_state._save()
            self._save_state()

        return success

    def record_requirement(self, content: str, priority: str = "P1") -> bool:
        """
        显式记录需求（当需要指定优先级时使用）

        Args:
            content: 需求内容
            priority: 优先级 P0/P1/P2/P3

        Returns:
            是否成功
        """
        return self.record(f"[{priority}] {content}")

    def record_bug(self, description: str, severity: str = "medium") -> bool:
        """
        显式记录 Bug（当需要指定严重程度时使用）

        Args:
            description: Bug 描述
            severity: 严重程度 low/medium/high/critical

        Returns:
            是否成功
        """
        return self.record(f"[{severity}] {description}")

    def record_progress(self, status: str, details: str = "") -> bool:
        """
        显式记录进度（当需要详细状态时使用）

        Args:
            status: 状态描述
            details: 详细信息

        Returns:
            是否成功
        """
        return self.record(f"{status}\n{details}" if details else status)

    # ==================== 需求与任务管理（底层方法） ====================

    def add_requirement(self, requirement: str, priority: str = "P1") -> bool:
        """
        添加需求到需求文档

        Args:
            requirement: 需求描述
            priority: 优先级 (P0/P1/P2)

        Returns:
            是否成功
        """
        if not self.project_state:
            return False

        current = self.project_state.get_document(
            DocumentType.REQUIREMENTS, "project_manager", full=True
        ) or ""

        new_entry = f"\n\n### 需求 [{priority}] ({time.strftime('%Y-%m-%d %H:%M')})\n\n{requirement}\n"

        return self.project_state.update_document(
            DocumentType.REQUIREMENTS,
            current + new_entry,
            "product_manager",
            f"新增需求: {requirement[:50]}..."
        )

    def get_requirements(self) -> str:
        """获取需求文档"""
        if self.project_state:
            return self.project_state.get_document(
                DocumentType.REQUIREMENTS, "project_manager", full=True
            ) or ""
        return ""

    def get_progress(self) -> str:
        """获取进度报告"""
        if self.project_state:
            return self.project_state.get_document(
                DocumentType.PROGRESS, "project_manager", full=True
            ) or ""
        return ""

    def get_development_log(self) -> str:
        """获取开发日志"""
        if self.project_state:
            return self.project_state.get_document(
                DocumentType.DEVELOPMENT, "project_manager", full=True
            ) or ""
        return ""

    def get_project_info(self) -> dict[str, Any]:
        """获取项目信息"""
        if self.project_state:
            return self.project_state.get_project_info()
        return {"name": self.project_name}

    def get_current_task(self) -> dict[str, Any]:
        """
        获取当前执行的任务（不同窗口可检测）

        Returns:
            当前任务信息，包含 task_id, task_desc, status
        """
        if self.project_state:
            return self.project_state.get_current_task()
        return {"task_id": "", "task_desc": "", "status": ""}

    def has_active_task(self) -> bool:
        """检查是否有正在执行的任务"""
        if self.project_state:
            return self.project_state.has_active_task()
        return False

    def reload(self) -> bool:
        """
        重新加载项目状态（从文件系统）

        用于多窗口场景，确保获取最新数据

        Returns:
            是否成功加载
        """
        if self.project_state:
            success = self.project_state.reload()
            if success:
                # 同时恢复项目名称
                self.project_name = self.project_state.project_info.name
                self._load_state()
            return success
        return False

    # ==================== 状态报告 ====================

    def get_status(self) -> dict[str, Any]:
        """
        获取整体状态

        Returns:
            状态信息
        """
        status = {
            "project": self.project_name,
            "team": {
                "size": self._stats.team_size,
                "members": self.coordinator.list_roles(),
            },
            "stats": self._stats.model_dump(),
            "memory_health": self.memory.get_health_report()["status"],
            "sessions": self.sessions.get_stats(),
            "persistence": {
                "enabled": self._persistent,
                "workspace": self._workspace,
            },
        }

        # 添加项目状态信息
        if self.project_state:
            status["project_stats"] = self.project_state.get_stats()
            status["documents"] = self.project_state.list_documents()
            status["current_task"] = self.project_state.get_current_task()
            status["has_active_task"] = self.project_state.has_active_task()

        return status

    def save(self) -> bool:
        """
        手动保存当前工作状态

        Returns:
            是否保存成功
        """
        return self._save_state()

    # ==================== 多会话管理（自动记录） ====================

    def chat(self, message: str, role: str = "user", auto_record: bool = True) -> dict[str, Any]:
        """
        在当前会话中发送消息（自动持久化）

        AI 对话时的核心方法，自动将消息记录到对应文档。

        Args:
            message: 消息内容
            role: 消息角色 (user/assistant/system)
            auto_record: 是否自动记录到文档（默认 True）

        Returns:
            消息信息

        自动记录规则（当 auto_record=True）：
            - 用户消息（role="user"）：
              → 调用 record() 智能识别内容类型并记录
            - AI 消息（role="assistant"）：
              → 调用 record() 记录 AI 的响应/分析结果

        Examples:
            # 用户提出需求（项目经理自动接收并分配）
            harness.chat("我需要一个用户登录功能")

            # AI 回复（自动记录）
            harness.chat("好的，我来分析一下登录功能的实现方案", role="assistant")

            # 禁用自动记录（仅存储到会话历史）
            harness.chat("临时讨论的内容", auto_record=False)
        """
        role_map = {
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
            "system": MessageRole.SYSTEM,
        }
        msg_role = role_map.get(role, MessageRole.USER)

        # 存储到会话历史
        msg = self.sessions.chat(message, msg_role)
        self._stats.messages_sent += 1

        # 存储到记忆系统
        self.memory.store_conversation(message, role=role, importance=50)

        # 自动记录到文档（核心功能）
        task_info = None
        action_result = None
        if auto_record and self.project_state:
            if role == "user":
                # 用户消息：智能识别意图并处理
                message_lower = message.lower()

                # 1. 开发请求：帮我开发/实现...
                is_develop = any(kw in message for kw in ["帮我开发", "帮我实现", "开发一下", "实现一下", "开始开发", "开始实现"])
                if is_develop:
                    action_result = self.develop(message.replace("帮我开发", "").replace("帮我实现", "").replace("开发一下", "").replace("实现一下", "").strip())
                    task_info = {"task_id": action_result.get("task_id"), "action": "develop"}

                # 2. 修复请求：帮我修复...
                elif any(kw in message for kw in ["帮我修复", "修复一下", "帮我改"]):
                    action_result = self.fix_bug(message.replace("帮我修复", "").replace("修复一下", "").replace("帮我改", "").strip())
                    task_info = {"task_id": action_result.get("task_id"), "action": "fix_bug"}

                # 3. 状态查询：项目进展/当前状态
                elif any(kw in message for kw in ["进展", "状态", "项目情况", "项目报告"]):
                    action_result = self.get_status()
                    task_info = {"action": "get_status"}

                # 4. 当前任务查询
                elif any(kw in message for kw in ["当前任务", "正在做", "在做什么"]):
                    action_result = self.get_current_task()
                    task_info = {"action": "get_current_task"}

                # 5. Bug报告
                elif any(kw in message_lower for kw in ["bug", "问题", "错误", "异常", "失败", "修复"]):
                    task_info = self.receive_request(message, request_type="bug")

                # 6. 新需求
                elif any(kw in message for kw in ["需要", "要", "添加", "新增", "功能", "需求"]):
                    task_info = self.receive_request(message, request_type="feature")

                # 7. 普通讨论
                else:
                    self.record(message, context="用户")
            else:
                # AI 消息：简单记录
                self.record(message, context="AI")

        # 保存状态
        self._save_state()

        return {
            "message_id": msg.id if msg else None,
            "session_id": self.sessions._active_session_id,
            "sent": msg is not None,
            "recorded": auto_record and self.project_state is not None,
            "task_info": task_info,
            "action_result": action_result,  # 返回执行结果（如开发结果、状态等）
        }

    def switch_session(self, session_type: str) -> dict[str, Any]:
        """
        切换到指定类型的会话

        不同类型的会话有独立的对话历史，互不干扰：
        - development: 主开发对话
        - product_manager: 产品经理对话
        - project_manager: 项目经理对话
        - architect: 架构师对话
        - tester: 测试人员对话
        - general: 通用对话

        Args:
            session_type: 会话类型

        Returns:
            切换结果

        Examples:
            # 切换到产品经理对话
            harness.switch_session("product_manager")
            harness.chat("登录功能需要支持哪些方式？")

            # 切换回主开发对话
            harness.switch_session("development")
            harness.chat("继续实现登录功能...")
        """
        type_map = {
            "development": SessionType.DEVELOPMENT,
            "product_manager": SessionType.PRODUCT_MANAGER,
            "project_manager": SessionType.PROJECT_MANAGER,
            "architect": SessionType.ARCHITECT,
            "tester": SessionType.TESTER,
            "doc_writer": SessionType.DOC_WRITER,
            "general": SessionType.GENERAL,
        }

        st = type_map.get(session_type.lower())
        if not st:
            return {"switched": False, "error": f"Unknown session type: {session_type}"}

        session = self.sessions.switch_session(st)
        return {
            "switched": True,
            "session": session.get_summary() if session else None,
        }

    def create_session(self, session_type: str, name: str = "") -> dict[str, Any]:
        """
        创建新会话

        Args:
            session_type: 会话类型
            name: 会话名称

        Returns:
            创建的会话信息
        """
        type_map = {
            "development": SessionType.DEVELOPMENT,
            "product_manager": SessionType.PRODUCT_MANAGER,
            "project_manager": SessionType.PROJECT_MANAGER,
            "architect": SessionType.ARCHITECT,
            "tester": SessionType.TESTER,
            "doc_writer": SessionType.DOC_WRITER,
            "general": SessionType.GENERAL,
        }

        st = type_map.get(session_type.lower(), SessionType.GENERAL)
        session = self.sessions.create_session(st, name)

        return {"created": True, "session": session.get_summary()}

    def get_current_session(self) -> dict[str, Any] | None:
        """
        获取当前活动会话

        Returns:
            当前会话信息
        """
        session = self.sessions.get_active_session()
        return session.get_summary() if session else None

    def get_session_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        获取当前会话的对话历史

        Args:
            limit: 限制消息数量

        Returns:
            消息列表
        """
        messages = self.sessions.get_conversation_history(limit=limit)
        return [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp,
            }
            for msg in messages
        ]

    def list_sessions(self) -> list[dict[str, Any]]:
        """
        列出所有会话

        Returns:
            会话列表
        """
        return self.sessions.list_sessions()

    def get_session_report(self) -> str:
        """
        获取会话报告

        Returns:
            格式化的会话报告
        """
        sessions = self.list_sessions()

        report_lines = [f"# {self.project_name} 会话报告\n"]
        report_lines.append("## 所有会话\n")

        for session in sessions:
            active_mark = " (当前)" if session.get("is_active") else ""
            report_lines.append(f"### {session['name']}{active_mark}")
            report_lines.append(f"- 类型: {session['type']}")
            report_lines.append(f"- 消息数: {session['message_count']}")
            report_lines.append("")

        return "\n".join(report_lines)

    def get_report(self) -> str:
        """
        获取项目报告

        Returns:
            格式化的报告字符串
        """
        status = self.get_status()

        report = f"""
# {self.project_name} 项目报告

## 团队
- 规模: {status['team']['size']} 人

## 统计
- 开发功能: {status['stats']['features_developed']} 个
- 修复Bug: {status['stats']['bugs_fixed']} 个
- 完成工作流: {status['stats']['workflows_completed']} 个

## 健康状态
- 记忆系统: {status['memory_health']}
"""
        return report.strip()

    # ==================== 引导系统 ====================

    def is_first_time(self) -> bool:
        """
        检测是否首次使用

        Returns:
            True 如果是首次使用（没有完成引导）
        """
        return self._guide.is_first_time()

    def start_onboarding(self) -> dict[str, Any]:
        """
        启动首次使用引导

        引导流程包括:
        1. 项目信息收集
        2. 团队角色配置
        3. 使用方式介绍
        4. 快速上手示例
        5. 项目初始化

        Returns:
            引导完成的配置信息
        """
        config = self._guide.start(self)

        # 保存状态
        self._save_state()

        return {
            "completed": True,
            "project_name": config.project_name,
            "project_description": config.project_description,
            "tech_stack": config.tech_stack,
            "team_config": config.team_config,
        }

    def load_project_config(self) -> dict[str, Any] | None:
        """
        加载项目配置

        Returns:
            项目配置，如果没有返回 None
        """
        config = self._guide.load_config()
        if config:
            return {
                "project_name": config.project_name,
                "project_description": config.project_description,
                "tech_stack": config.tech_stack,
                "team_config": config.team_config,
                "onboarding_completed": config.onboarding_completed,
            }
        return None

    def show_help(self) -> None:
        """
        显示快速帮助信息
        """
        self._guide.show_quick_help()

    def welcome(self) -> str:
        """
        生成欢迎信息和使用提示

        Returns:
            格式化的欢迎信息
        """
        config = self.load_project_config()

        if config and config.get("onboarding_completed"):
            # 已完成引导，显示项目欢迎信息
            return f"""
欢迎回来，{config['project_name']}！

项目状态:
  - 团队规模: {self._stats.team_size} 人
  - 开发功能: {self._stats.features_developed} 个
  - 修复Bug: {self._stats.bugs_fixed} 个

快速提示:
  - 使用 harness.chat('你的需求') 开始对话
  - 使用 harness.develop('功能') 快速开发
  - 使用 harness.show_help() 查看更多帮助

准备好继续开发了吗？
"""
        else:
            # 首次使用，引导用户
            return """
欢迎使用 py_ha！

看起来你是第一次使用，让我帮你快速上手：
  - 使用 harness.start_onboarding() 开始引导配置
  - 使用 harness.show_help() 查看快速帮助
  - 或直接使用 harness.develop('功能描述') 开始开发

准备好了吗？开始你的 AI Agent 开发之旅吧！
"""


# ==================== 便捷函数 ====================

def create_harness(
    project_name: str = "Default Project",
    *,
    persistent: bool = True,
    workspace: str = ".py_ha",
) -> Harness:
    """
    创建 Harness 实例

    Args:
        project_name: 项目名称
        persistent: 是否持久化存储（默认 True）
        workspace: 工作空间目录

    Returns:
        Harness 实例

    Examples:
        # 默认持久化
        harness = create_harness("我的项目")

        # 禁用持久化
        harness = create_harness("我的项目", persistent=False)
    """
    return Harness(
        project_name=project_name,
        persistent=persistent,
        workspace=workspace,
    )