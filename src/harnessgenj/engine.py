"""
Harness - Harness Engineering 主入口

提供简洁的 API 来使用 Harness Engineering 框架

核心概念:
- Memory: 统一记忆管理（JVM风格分代存储）
- Team: 开发团队，包含多个角色
- Workflow: 工作流流水线
- Session: 多对话会话管理
- Quality: 对抗性质量保证系统

使用示例:
    from harnessgenj import Harness

    # 创建 Harness 实例（默认持久化）
    harness = Harness("我的项目")

    # 从现有项目文档初始化（推荐）
    harness = Harness.from_project("/path/to/project")

    # 快速开发功能
    result = harness.develop("实现用户登录功能")

    # 项目经理接收请求
    result = harness.receive_request("需要一个搜索功能")

    # 完成任务
    harness.complete_task(result['task_id'], "功能已完成")

    # 对抗性开发（提高成功率）
    result = harness.adversarial_develop("实现支付功能")
"""

from typing import Any
from pydantic import BaseModel, Field
import time
import os
import json
import uuid
import re
import glob

from harnessgenj.roles import (
    AgentRole,
    RoleType,
    create_role,
)
from harnessgenj.workflow import (
    WorkflowCoordinator,
    WorkflowPipeline,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    create_adversarial_pipeline,
)
from harnessgenj.memory import MemoryManager
from harnessgenj.storage import create_storage, StorageManager, StorageType
from harnessgenj.session import (
    SessionManager,
    SessionType,
    Session,
    MessageRole,
    Message,
)
from harnessgenj.guide import OnboardingGuide, ProjectConfig
from harnessgenj.quality.score import ScoreManager
from harnessgenj.quality.tracker import QualityTracker
from harnessgenj.quality.task_adversarial import TaskAdversarialController
from harnessgenj.quality.system_adversarial import SystemAdversarialController
from harnessgenj.harness.adversarial import AdversarialWorkflow, AdversarialResult


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

    核心方法:
    - receive_request(): 项目经理接收请求
    - complete_task(): 完成任务
    - develop(): 快速开发功能
    - fix_bug(): 快速修复Bug
    - chat(): 对话（自动记录）
    - get_context_prompt(): 获取上下文提示（用于LLM）

    持久化支持:
    - 默认开启持久化，数据保存在 .harnessgenj/ 目录
    - 重启后自动加载之前的工作内容
    """

    def __init__(
        self,
        project_name: str = "Default Project",
        *,
        persistent: bool = True,
        workspace: str = ".harnessgenj",
        config_path: str | None = None,
    ) -> None:
        """
        初始化 Harness 实例

        Args:
            project_name: 项目名称
            persistent: 是否持久化存储（默认 True）
            workspace: 工作空间目录（默认 .harnessgenj）
        """
        self.project_name = project_name
        self._workspace = workspace
        self._persistent = persistent

        # 核心组件：统一记忆管理
        self.memory = MemoryManager(workspace)
        self.memory.project_info.name = project_name
        self.memory.store_knowledge("project_name", project_name)

        # 工作流协调器
        self.coordinator = WorkflowCoordinator()

        # 存储系统（用于AGENTS.md等）
        self.storage = create_storage(persistent=persistent, base_path=workspace)

        # AGENTS.md 知识管理器
        self._agents_knowledge = None
        if persistent:
            from harnessgenj.harness import AgentsKnowledgeManager
            self._agents_knowledge = AgentsKnowledgeManager(workspace)
            if not self._agents_knowledge.is_initialized():
                self._agents_knowledge.initialize(project_name, "", "init")

        # 会话管理
        session_path = os.path.join(workspace, "sessions.json") if persistent else None
        self.sessions = SessionManager(persist_path=session_path)
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
        self.coordinator.register_workflow("adversarial", create_adversarial_pipeline())

        # 质量保证系统 - 默认启用
        self._score_manager = ScoreManager(workspace)
        self._quality_tracker = QualityTracker(workspace)
        self._adversarial_workflow = AdversarialWorkflow(
            self._score_manager,
            self._quality_tracker,
            self.memory,  # 传递 MemoryManager，建立质量数据流
        )

        # 双层对抗控制器
        self._task_adversarial = TaskAdversarialController(
            self._score_manager,
            self._quality_tracker,
        )
        self._system_adversarial = SystemAdversarialController(
            self._quality_tracker,
            self._score_manager,
            self.memory,
        )

        # 链接质量系统到记忆管理（使用方法调用而非直接属性赋值）
        self.memory.set_quality_system(self._score_manager, self._quality_tracker)

        # 加载之前的工作状态
        if persistent:
            self._load_state()

    @classmethod
    def from_project(
        cls,
        project_path: str,
        *,
        workspace: str | None = None,
        doc_patterns: list[str] | None = None,
    ) -> "Harness":
        """
        从现有项目目录初始化 Harness

        自动扫描项目文档并导入到记忆系统，支持：
        - README.md / readme.md
        - requirements.md / needs.md / 需求.md
        - design.md / architecture.md / 设计.md
        - progress.md / 进度.md
        - development.md / dev.md / 开发.md
        - testing.md / test.md / 测试.md
        - docs/ 目录下的 .md 文件

        Args:
            project_path: 项目根目录路径
            workspace: HarnessGenJ 工作空间路径（默认为项目目录下的 .harnessgenj）
            doc_patterns: 自定义文档匹配模式

        Returns:
            初始化好的 Harness 实例

        使用示例:
            # 从项目目录初始化
            harness = Harness.from_project("/path/to/my-project")

            # 获取导入的项目信息
            context = harness.get_init_prompt()
        """
        project_path = os.path.abspath(project_path)
        if workspace is None:
            workspace = os.path.join(project_path, ".harnessgenj")

        # 默认文档匹配模式
        if doc_patterns is None:
            doc_patterns = [
                "README.md",
                "readme.md",
                "requirements.md",
                "needs.md",
                "需求.md",
                "design.md",
                "architecture.md",
                "设计.md",
                "progress.md",
                "进度.md",
                "development.md",
                "dev.md",
                "开发.md",
                "testing.md",
                "test.md",
                "测试.md",
                "docs/*.md",
                "doc/*.md",
            ]

        # 扫描并读取文档
        documents: dict[str, str] = {}
        for pattern in doc_patterns:
            full_pattern = os.path.join(project_path, pattern)
            for file_path in glob.glob(full_pattern):
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if content.strip():
                            doc_name = os.path.basename(file_path)
                            documents[doc_name] = content
                    except Exception:
                        pass

        # 提取项目名称
        project_name = os.path.basename(project_path)
        if "README.md" in documents:
            # 尝试从 README 提取标题
            readme = documents["README.md"]
            title_match = re.search(r"^#\s+(.+)$", readme, re.MULTILINE)
            if title_match:
                project_name = title_match.group(1).strip()

        # 创建 Harness 实例
        harness = cls(project_name, workspace=workspace)

        # 导入文档到记忆系统
        harness._import_documents(documents)

        # 提取项目信息
        harness._extract_project_info(documents, project_path)

        return harness

    def _import_documents(self, documents: dict[str, str]) -> None:
        """导入文档到记忆系统"""
        # 文档类型映射
        doc_type_map = {
            "requirements.md": "requirements",
            "needs.md": "requirements",
            "需求.md": "requirements",
            "design.md": "design",
            "architecture.md": "design",
            "设计.md": "design",
            "development.md": "development",
            "dev.md": "development",
            "开发.md": "development",
            "testing.md": "testing",
            "test.md": "testing",
            "测试.md": "testing",
            "progress.md": "progress",
            "进度.md": "progress",
        }

        for doc_name, content in documents.items():
            # 确定文档类型
            doc_type = doc_type_map.get(doc_name.lower(), None)

            if doc_type:
                # 存储到对应类型的文档
                self.memory.store_document(doc_type, content)
            else:
                # 存储为核心知识
                key = doc_name.replace(".", "_").replace("-", "_")
                self.memory.store_knowledge(f"doc_{key}", content, importance=70)

        # 保存状态
        self._save_state()

    def _extract_project_info(self, documents: dict[str, str], project_path: str) -> None:
        """从文档中提取项目信息"""
        readme = documents.get("README.md", "")

        # 提取描述（第一段非标题内容）
        if readme:
            lines = readme.split("\n")
            desc_lines = []
            in_content = False
            for line in lines:
                if line.startswith("#"):
                    if in_content:
                        break
                    continue
                if line.strip() and not in_content:
                    in_content = True
                if in_content:
                    desc_lines.append(line)
                    if len(desc_lines) >= 5:
                        break
            description = " ".join(desc_lines).strip()[:500]
            self.memory.project_info.description = description

        # 检测技术栈
        tech_indicators = {
            "Python": ["requirements.txt", "setup.py", "pyproject.toml", ".py"],
            "Node.js": ["package.json", ".js", ".ts"],
            "Go": ["go.mod", ".go"],
            "Rust": ["Cargo.toml", ".rs"],
            "Java": ["pom.xml", "build.gradle", ".java"],
        }

        detected_tech = []
        for tech, indicators in tech_indicators.items():
            for indicator in indicators:
                if os.path.exists(os.path.join(project_path, indicator)):
                    detected_tech.append(tech)
                    break

        # 检查文档中的技术关键词
        all_content = " ".join(documents.values()).lower()
        tech_keywords = {
            "FastAPI": ["fastapi", "fast-api"],
            "Django": ["django"],
            "Flask": ["flask"],
            "React": ["react"],
            "Vue": ["vue"],
            "PostgreSQL": ["postgresql", "postgres"],
            "MySQL": ["mysql"],
            "MongoDB": ["mongodb"],
            "Redis": ["redis"],
            "Docker": ["docker"],
        }

        for tech, keywords in tech_keywords.items():
            if any(kw in all_content for kw in keywords):
                detected_tech.append(tech)

        if detected_tech:
            tech_stack = " + ".join(dict.fromkeys(detected_tech))
            self.memory.project_info.tech_stack = tech_stack
            self.memory.store_knowledge("tech_stack", tech_stack, importance=100)

        # 更新项目状态
        self.memory.project_info.status = "initialized"
        self.memory._save()

    def _load_state(self) -> bool:
        """加载之前的工作状态"""
        state_path = os.path.join(self._workspace, "state.json")
        if not os.path.exists(state_path):
            return False

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "project_name" in data:
                self.project_name = data["project_name"]
                self.memory.project_info.name = self.project_name

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

            self.sessions.save()
            return True
        except Exception:
            return False

    # ==================== 团队管理 ====================

    def setup_team(self, team_config: dict[str, str] | None = None) -> dict[str, Any]:
        """组建开发团队"""
        if team_config is None:
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

    def get_team(self) -> list[dict[str, Any]]:
        """获取团队信息"""
        return self.coordinator.list_roles()

    # ==================== 项目经理核心方法 ====================

    def receive_request(self, request: str, request_type: str = "feature") -> dict[str, Any]:
        """
        项目经理接收用户请求（核心入口方法）

        Args:
            request: 用户请求内容
            request_type: 请求类型 (feature/bug/task)

        Returns:
            处理结果，包含任务ID、优先级、负责人等信息
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M')
        task_id = f"TASK-{int(time.time_ns() % 1000000000)}-{uuid.uuid4().hex[:4]}"

        # 根据请求类型分配优先级
        if request_type == "bug":
            priority = "P0"
            category = "Bug修复"
        elif request_type == "feature":
            priority = "P1"
            category = "功能开发"
        else:
            priority = "P2"
            category = "任务"

        # 存储任务到 Survivor 区
        self.memory.store_task(task_id, {
            "request": request,
            "type": request_type,
            "category": category,
            "priority": priority,
            "status": "pending",
            "created_at": timestamp,
        })

        # 更新进度文档
        progress = self.memory.get_document("progress") or "# 项目进度\n"
        progress += f"\n## {task_id} - {category}\n- **描述**: {request}\n- **优先级**: {priority}\n- **状态**: 待处理\n- **创建时间**: {timestamp}\n"
        self.memory.store_document("progress", progress)

        # 更新统计
        if request_type == "bug":
            self.memory.update_stats("bugs_total", 1)
        else:
            self.memory.update_stats("features_total", 1)

        # 存储会话消息
        self.memory.store_message(request, "user")

        self._save_state()

        return {
            "success": True,
            "task_id": task_id,
            "priority": priority,
            "assignee": "developer",
            "category": category,
            "status": "待处理",
            "timestamp": timestamp,
        }

    def complete_task(self, task_id: str, summary: str = "") -> bool:
        """
        项目经理标记任务完成

        Args:
            task_id: 任务ID
            summary: 完成摘要
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M')

        # 获取任务
        task = self.memory.get_task(task_id)
        if not task:
            return False

        # 判断任务类型
        is_bug = task.get("category") in ("Bug修复", "Bug")

        # 更新任务状态
        task["status"] = "completed"
        task["completed_at"] = timestamp
        task["summary"] = summary
        self.memory.store_task(task_id, task)

        # 更新进度文档
        progress = self.memory.get_document("progress") or ""
        if task_id in progress:
            progress = re.sub(
                r'(\*\*状态\*\*:\s*)\S+',
                '**状态**: 已完成',
                progress
            )
            progress += f"\n  - **完成时间**: {timestamp}\n  - **完成说明**: {summary}\n"
            self.memory.store_document("progress", progress)

        # 更新统计
        if is_bug:
            self.memory.update_stats("bugs_fixed", 1)
        else:
            self.memory.update_stats("features_completed", 1)

        # 清除当前任务
        self.memory.clear_task(task_id)

        self._save_state()
        return True

    # ==================== 快速开发 ====================

    def develop(self, feature_request: str) -> dict[str, Any]:
        """快速开发功能"""
        task_info = self.receive_request(feature_request, request_type="feature")

        # 确保有开发团队
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        # 执行开发工作流
        result = self.coordinator.run_workflow("feature", {"feature_request": feature_request})

        if result.get("status") == "completed":
            self._stats.features_developed += 1
            self._stats.workflows_completed += 1
            self.memory.store_message(f"功能开发完成: {feature_request}", "system")
            if task_info.get("task_id"):
                self.complete_task(task_info["task_id"], f"功能完成: {feature_request[:50]}")
            self._save_state()

        return {
            "request": feature_request,
            "task_id": task_info.get("task_id"),
            "status": result.get("status"),
            "artifacts": result.get("artifacts", []),
        }

    def fix_bug(self, bug_description: str) -> dict[str, Any]:
        """快速修复 Bug"""
        task_info = self.receive_request(bug_description, request_type="bug")

        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_auto", "开发人员")
        if not self.coordinator.get_roles_by_type(RoleType.TESTER):
            self.coordinator.create_role(RoleType.TESTER, "test_auto", "测试人员")

        result = self.coordinator.run_workflow("bugfix", {"bug_report": bug_description})

        if result.get("status") == "completed":
            self._stats.bugs_fixed += 1
            self._stats.workflows_completed += 1
            self.memory.store_message(f"Bug修复完成: {bug_description}", "system")
            if task_info.get("task_id"):
                self.complete_task(task_info["task_id"], f"Bug修复: {bug_description[:50]}")
            self._save_state()

        return {
            "bug": bug_description,
            "task_id": task_info.get("task_id"),
            "status": result.get("status"),
        }

    # ==================== 记忆与上下文 ====================

    def remember(self, key: str, content: str, important: bool = False) -> None:
        """记忆重要信息"""
        importance = 100 if important else 50
        self.memory.store_knowledge(key, content, importance)
        self._save_state()

    def recall(self, key: str) -> str | None:
        """回忆信息"""
        return self.memory.get_knowledge(key)

    def record(self, content: str, context: str = "", doc_type_hint: str | None = None) -> bool:
        """智能记录内容"""
        doc_type = doc_type_hint or "development"
        current = self.memory.get_document(doc_type) or ""
        timestamp = time.strftime('%Y-%m-%d %H:%M')
        entry = f"\n## 记录 ({timestamp})\n[{context}] {content}\n"
        self.memory.store_document(doc_type, current + entry)
        return True

    def get_context_prompt(self, role: str = "project_manager", max_tokens: int = 4000) -> str:
        """获取上下文提示（用于 LLM）"""
        return self.memory.get_context_for_llm(role, max_tokens)

    def get_minimal_context(self) -> str:
        """获取最小上下文"""
        return self.memory.get_minimal_context()

    # ==================== 会话管理 ====================

    def chat(self, message: str, role: str = "user", auto_record: bool = True) -> dict[str, Any]:
        """在当前会话中发送消息"""
        role_map = {
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
            "system": MessageRole.SYSTEM,
        }
        msg_role = role_map.get(role, MessageRole.USER)

        msg = self.sessions.chat(message, msg_role)
        self._stats.messages_sent += 1

        # 存储到记忆
        self.memory.store_message(message, role)

        # 自动处理用户请求
        task_info = None
        if auto_record and role == "user":
            if any(kw in message for kw in ["需要", "要", "添加", "新增", "功能"]):
                task_info = self.receive_request(message, request_type="feature")
            elif any(kw in message.lower() for kw in ["bug", "问题", "错误", "异常"]):
                task_info = self.receive_request(message, request_type="bug")

        self._save_state()

        return {
            "message_id": msg.id if msg else None,
            "session_id": self.sessions._active_session_id,
            "task_info": task_info,
        }

    def switch_session(self, session_type: str) -> dict[str, Any]:
        """切换到指定类型的会话"""
        type_map = {
            "development": SessionType.DEVELOPMENT,
            "product_manager": SessionType.PRODUCT_MANAGER,
            "project_manager": SessionType.PROJECT_MANAGER,
            "architect": SessionType.ARCHITECT,
            "tester": SessionType.TESTER,
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

    # ==================== 状态报告 ====================

    def get_status(self) -> dict[str, Any]:
        """获取整体状态"""
        stats = self.memory.get_stats()

        return {
            "project": self.project_name,
            "team": {
                "size": self._stats.team_size,
                "members": self.coordinator.list_roles(),
            },
            "stats": self._stats.model_dump(),
            "project_stats": stats["stats"],
            "memory": stats["memory"],
            "sessions": self.sessions.get_stats(),
            "persistence": {
                "enabled": self._persistent,
                "workspace": self._workspace,
            },
            "current_task": self.memory.get_current_task(),
        }

    def get_report(self) -> str:
        """获取项目报告"""
        stats = self.memory.get_stats()

        return f"""
# {self.project_name} 项目报告

## 团队
- 规模: {self._stats.team_size} 人

## 统计
- 功能总数: {stats['stats']['features_total']}
- 已完成: {stats['stats']['features_completed']}
- Bug总数: {stats['stats']['bugs_total']}
- 已修复: {stats['stats']['bugs_fixed']}
- 进度: {stats['stats']['progress']}%

## 记忆健康
- Eden: {stats['memory']['eden_size']}
- Old: {stats['memory']['old_size']}
"""

    def save(self) -> bool:
        """手动保存当前工作状态"""
        return self._save_state()

    def reload(self) -> bool:
        """重新加载项目状态"""
        self.memory.reload()
        return self._load_state()

    # ==================== 引导系统 ====================

    def is_first_time(self) -> bool:
        """检测是否首次使用"""
        return self._guide.is_first_time()

    def start_onboarding(self) -> dict[str, Any]:
        """启动首次使用引导"""
        config = self._guide.start(self)
        self._save_state()
        return {
            "completed": True,
            "project_name": config.project_name,
            "tech_stack": config.tech_stack,
        }

    def welcome(self) -> str:
        """生成欢迎信息"""
        return f"""
欢迎使用 HarnessGenJ！

项目: {self.project_name}

快速提示:
  - 使用 harness.receive_request("需求") 接收请求
  - 使用 harness.develop("功能") 快速开发
  - 使用 harness.get_context_prompt() 获取上下文
"""

    def get_init_prompt(self) -> str:
        """
        获取初始化提示（用于 Claude Code 对话初始化）

        返回完整的初始化指导和项目上下文，让 Claude Code 能够：
        1. 理解 HarnessGenJ 的核心概念
        2. 知道如何使用核心 API
        3. 了解当前项目状态

        Returns:
            初始化提示字符串
        """
        # 获取基础上下文
        context = self.get_context_prompt()

        # 添加初始化说明
        init_header = """
# HarnessGenJ 初始化指南

## 当前状态
HarnessGenJ 已初始化完成，你可以直接使用以下 API 与项目交互。

## 工作流程
1. 用户提出需求 → 调用 `receive_request()`
2. 执行开发任务 → 调用 `develop()` 或手动实现
3. 完成任务 → 调用 `complete_task()`
4. 每次对话开始 → 调用 `get_context_prompt()` 获取上下文

## 重要提示
- 所有操作自动持久化，重启后自动恢复
- 使用 `harness.remember(key, value, important=True)` 存储重要知识
- 使用 `harness.recall(key)` 获取存储的知识

"""
        return init_header + context

    # ==================== 对抗性质量保证 ====================

    def enable_adversarial_mode(self) -> dict[str, Any]:
        """
        启用对抗模式（已弃用）

        对抗模式现在默认启用，此方法保留仅为向后兼容。

        Returns:
            启用状态信息
        """
        import warnings
        warnings.warn(
            "enable_adversarial_mode() is deprecated. Adversarial mode is now always enabled by default.",
            DeprecationWarning,
            stacklevel=2,
        )
        return {
            "enabled": True,
            "message": "对抗模式默认已启用。使用 adversarial_develop() 进行对抗性开发。",
        }

    def adversarial_develop(
        self,
        feature_request: str,
        max_rounds: int = 3,
        use_hunter: bool = False,
        code: str | None = None,
        fix_callback=None,
    ) -> AdversarialResult:
        """
        对抗性开发（提高单次成功率）

        流程：
        1. 开发者产出代码
        2. 审查者审查代码
        3. 开发者修复问题
        4. 循环直到通过或达到最大轮次
        5. 计算积分变更

        Args:
            feature_request: 功能需求描述
            max_rounds: 最大对抗轮次（默认3）
            use_hunter: 是否使用 BugHunter（更激进的审查）
            code: 已有代码（可选，用于审查已有代码）
            fix_callback: 修复回调函数

        Returns:
            AdversarialResult: 对抗结果
        """
        # 确保有开发者
        if not self.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            self.coordinator.create_role(RoleType.DEVELOPER, "dev_adv", "开发者")

        developer_id = "dev_adv"

        # 如果没有提供代码，先执行开发
        if code is None:
            dev_result = self.develop(feature_request)
            # 这里简化处理，实际应该获取开发者产出的代码
            code = f"# {feature_request}\n# 代码实现..."

        # 执行对抗性审查
        result = self._adversarial_workflow.execute_adversarial_review(
            code=code,
            generator_id=developer_id,
            generator_type="developer",
            task_id=None,
            max_rounds=max_rounds,
            fix_callback=fix_callback,
            use_hunter=use_hunter,
        )

        # 更新统计
        if result.success:
            self._stats.features_developed += 1
            self._stats.workflows_completed += 1

        self._save_state()
        return result

    def quick_review(
        self,
        code: str,
        use_hunter: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        快速代码审查（单轮，不计分）

        Args:
            code: 待审查代码
            use_hunter: 是否使用 BugHunter

        Returns:
            (是否通过, 问题列表)
        """
        if self._adversarial_workflow is None:
            self.enable_adversarial_mode()

        passed, issues = self._adversarial_workflow.quick_review(code, use_hunter)
        return passed, [i.description for i in issues]

    def get_quality_report(self) -> dict[str, Any]:
        """
        获取质量报告

        Returns:
            质量指标和改进建议
        """
        return self._quality_tracker.get_quality_report()

    def get_score_leaderboard(self, role_type: str | None = None) -> list[dict[str, Any]]:
        """
        获取积分排行榜

        Args:
            role_type: 筛选角色类型（可选）

        Returns:
            排行榜列表
        """
        return self._score_manager.get_leaderboard(role_type)

    def get_role_score(self, role_id: str) -> dict[str, Any] | None:
        """
        获取角色积分

        Args:
            role_id: 角色ID

        Returns:
            角色积分信息
        """
        score = self._score_manager.get_score(role_id)
        if score:
            return {
                "role_id": score.role_id,
                "role_name": score.role_name,
                "score": score.score,
                "grade": score.grade,
                "success_rate": f"{score.success_rate:.1%}",
            }
        return None

    # ==================== 系统级分析与改进 ====================

    def get_system_analysis(self) -> dict[str, Any]:
        """
        获取系统级对抗分析

        分析跨任务的模式，识别：
        - 生成器薄弱点
        - 判别器偏差
        - 系统改进建议

        Returns:
            系统分析结果
        """
        result = self._system_adversarial.analyze_cross_task_patterns()
        return {
            "total_tasks_analyzed": result.total_tasks_analyzed,
            "system_health_score": result.system_health_score,
            "generator_weaknesses": [
                {
                    "role_id": w.role_id,
                    "weakness_type": w.weakness_type,
                    "frequency": w.frequency,
                    "suggestions": w.suggestions[:3],
                }
                for w in result.generator_weaknesses[:5]
            ],
            "discriminator_biases": [
                {
                    "role_id": b.role_id,
                    "bias_type": b.bias_type,
                    "impact": b.impact,
                    "suggestions": b.suggestions[:3],
                }
                for b in result.discriminator_biases[:5]
            ],
            "improvement_actions": result.improvement_actions[:10],
        }

    def get_health_trend(self) -> list[float]:
        """
        获取系统健康度趋势

        Returns:
            最近N次分析的健康度分数列表
        """
        return self._system_adversarial.get_system_health_trend()

    def run_task_with_adversarial(
        self,
        task: dict[str, Any],
        generator_role_type: str = "developer",
        max_rounds: int = 3,
        intensity: str = "normal",
    ) -> dict[str, Any]:
        """
        使用任务级对抗控制器执行任务

        这是完整的对抗性任务执行方法，包含：
        1. 任务分配给生成器
        2. 判别器自动审查
        3. 多轮修复循环
        4. 质量评分和记录

        Args:
            task: 任务信息字典
            generator_role_type: 生成器角色类型
            max_rounds: 最大对抗轮次
            intensity: 审查强度 ("normal" | "aggressive")

        Returns:
            任务执行结果
        """
        # 确保生成器角色存在
        role_type_map = {
            "developer": RoleType.DEVELOPER,
            "architect": RoleType.ARCHITECT,
            "tester": RoleType.TESTER,
            "doc_writer": RoleType.DOC_WRITER,
        }
        role_type = role_type_map.get(generator_role_type, RoleType.DEVELOPER)

        generator = self.coordinator.get_roles_by_type(role_type)
        if not generator:
            generator = self.coordinator.create_role(role_type, f"{generator_role_type}_1", generator_role_type)
        else:
            generator = generator[0]

        # 执行对抗性任务
        result = self._task_adversarial.execute_with_adversarial(
            task=task,
            generator=generator,
        )

        return {
            "task_id": task.get("id"),
            "success": result.final_result == "passed",
            "rounds": result.rounds,
            "quality_score": result.quality_score,
            "issues_found": result.issues_found,
            "issues_fixed": result.issues_fixed,
            "duration": result.duration,
        }


def create_harness(
    project_name: str = "Default Project",
    *,
    persistent: bool = True,
    workspace: str = ".harnessgenj",
) -> Harness:
    """创建 Harness 实例"""
    return Harness(
        project_name=project_name,
        persistent=persistent,
        workspace=workspace,
    )