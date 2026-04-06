"""
Tests for ProjectManager Role - 项目经理角色测试

测试项目经理的核心功能：
- 项目状态管理
- 角色任务调度
- 产出收集与文档更新
- 渐进式披露上下文生成
"""

import pytest
import tempfile
import shutil

from harnessgenj.roles.project_manager import (
    ProjectManager,
    TaskAssignment,
    create_project_manager,
)
from harnessgenj.roles.base import RoleContext, RoleType, TaskType
from harnessgenj.memory.manager import MemoryManager, DocumentType


class TestProjectManagerCreation:
    """测试项目经理创建"""

    def test_create_default(self):
        """使用默认参数创建"""
        pm = ProjectManager()
        assert pm is not None
        assert pm.role_id == "pm_1"
        assert pm.name == "项目经理"
        assert pm.role_type == RoleType.PROJECT_MANAGER

    def test_create_with_custom_params(self):
        """使用自定义参数创建"""
        pm = ProjectManager(
            role_id="pm_custom",
            name="高级项目经理",
        )
        assert pm.role_id == "pm_custom"
        assert pm.name == "高级项目经理"

    def test_create_with_context(self):
        """使用上下文创建"""
        context = RoleContext()
        pm = ProjectManager(context=context)
        assert pm.context is not None

    def test_create_with_state_manager(self):
        """使用状态管理器创建"""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = MemoryManager(temp_dir)
            pm = ProjectManager(state_manager=manager)

            assert pm.state is manager
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_with_factory(self):
        """使用工厂函数创建"""
        pm = create_project_manager(pm_id="pm_factory", name="工厂项目经理")
        assert pm.role_id == "pm_factory"
        assert pm.name == "工厂项目经理"


class TestProjectManagerResponsibilities:
    """测试项目经理职责"""

    def test_responsibilities_list(self):
        """测试职责列表"""
        pm = ProjectManager()
        responsibilities = pm.responsibilities

        assert len(responsibilities) == 7
        assert "项目文档管理" in responsibilities
        assert "角色任务调度" in responsibilities
        assert "进度追踪与报告" in responsibilities
        assert "资源分配与管理" in responsibilities
        assert "风险识别与应对" in responsibilities
        assert "渐进式信息披露" in responsibilities
        assert "团队沟通协调" in responsibilities

    def test_role_type(self):
        """测试角色类型"""
        pm = ProjectManager()
        assert pm.role_type == RoleType.PROJECT_MANAGER

    def test_supported_task_types(self):
        """测试支持的任务类型"""
        pm = ProjectManager()
        task_types = pm.get_supported_task_types()

        assert TaskType.COORDINATE in task_types
        assert TaskType.TRACK_PROGRESS in task_types


class TestProjectManagerSkills:
    """测试项目经理技能"""

    def test_skills_setup(self):
        """测试技能设置"""
        pm = ProjectManager()
        skills = pm.list_skills()

        assert len(skills) == 5

        skill_names = [s.name for s in skills]
        assert "coordinate" in skill_names
        assert "track_progress" in skill_names
        assert "manage_documents" in skill_names
        assert "create_context" in skill_names
        assert "manage_risks" in skill_names


class TestTaskAssignment:
    """测试任务分配记录"""

    def test_task_assignment_creation(self):
        """测试任务分配创建"""
        assignment = TaskAssignment(
            task_id="task_001",
            task_type="feature",
            assigned_to="developer",
            description="实现登录功能",
        )

        assert assignment.task_id == "task_001"
        assert assignment.task_type == "feature"
        assert assignment.assigned_to == "developer"
        assert assignment.description == "实现登录功能"
        assert assignment.status == "pending"
        assert assignment.artifact == {}

    def test_task_assignment_defaults(self):
        """测试任务分配默认值"""
        assignment = TaskAssignment(
            task_id="task_002",
            task_type="bug",
            assigned_to="developer",
            description="修复Bug",
        )

        assert assignment.status == "pending"
        assert assignment.completed_at is None
        assert assignment.artifact == {}

    def test_task_assignment_completion(self):
        """测试任务分配完成"""
        import time

        assignment = TaskAssignment(
            task_id="task_003",
            task_type="feature",
            assigned_to="developer",
            description="功能开发",
            status="completed",
            completed_at=time.time(),
            artifact={"code": "def func(): pass"},
        )

        assert assignment.status == "completed"
        assert assignment.completed_at is not None
        assert "code" in assignment.artifact


class TestProjectManagerStatus:
    """测试项目状态管理"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_get_project_status(self, project_manager):
        """测试获取项目状态"""
        status = project_manager.get_project_status()

        assert "project" in status
        assert "stats" in status
        assert "documents" in status
        assert "summary" in status

    def test_get_project_status_without_state(self):
        """测试无状态管理器时获取状态"""
        pm = ProjectManager()
        status = pm.get_project_status()

        assert "error" in status
        assert status["error"] == "State manager not initialized"

    def test_get_project_summary(self, project_manager, memory_manager):
        """测试获取项目摘要"""
        # 直接设置项目信息属性
        memory_manager.project_info.name = "测试项目"
        memory_manager.project_info.description = "测试项目描述"
        memory_manager.project_info.tech_stack = "Python"

        summary = project_manager.get_project_summary()

        assert summary is not None

    def test_get_project_summary_without_state(self):
        """测试无状态管理器时获取摘要"""
        pm = ProjectManager()
        summary = pm.get_project_summary()

        assert summary == "项目状态管理器未初始化"


class TestProjectManagerTaskScheduling:
    """测试任务调度"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_assign_task_to_developer(self, project_manager):
        """测试向开发者分配任务"""
        result = project_manager.assign_task_to_role("developer", {
            "type": "implement_feature",
            "description": "实现购物车功能",
        })

        assert result["status"] == "assigned"
        assert result["assigned_to"] == "developer"
        assert "assignment_id" in result
        assert "context" in result
        assert "current_task" in result["context"]

    def test_assign_task_to_product_manager(self, project_manager):
        """测试向产品经理分配任务"""
        result = project_manager.assign_task_to_role("product_manager", {
            "type": "analyze_requirement",
            "description": "分析用户需求",
        })

        assert result["status"] == "assigned"
        assert result["assigned_to"] == "product_manager"

    def test_assign_task_to_architect(self, project_manager):
        """测试向架构师分配任务"""
        result = project_manager.assign_task_to_role("architect", {
            "type": "design_system",
            "description": "设计系统架构",
        })

        assert result["status"] == "assigned"
        assert result["assigned_to"] == "architect"

    def test_assign_task_to_tester(self, project_manager):
        """测试向测试人员分配任务"""
        result = project_manager.assign_task_to_role("tester", {
            "type": "write_test",
            "description": "编写单元测试",
        })

        assert result["status"] == "assigned"
        assert result["assigned_to"] == "tester"

    def test_assign_task_creates_record(self, project_manager):
        """测试分配任务创建记录"""
        project_manager.assign_task_to_role("developer", {
            "type": "feature",
            "description": "功能开发",
        })

        assignments = project_manager._task_assignments
        assert len(assignments) == 1
        assert assignments[0].assigned_to == "developer"
        assert assignments[0].status == "pending"

    def test_assign_multiple_tasks(self, project_manager):
        """测试分配多个任务"""
        project_manager.assign_task_to_role("developer", {"type": "feature", "description": "功能A"})
        project_manager.assign_task_to_role("tester", {"type": "test", "description": "测试A"})

        assignments = project_manager._task_assignments
        assert len(assignments) == 2

    def test_assign_task_without_state(self):
        """测试无状态管理器时分配任务"""
        pm = ProjectManager()
        result = pm.assign_task_to_role("developer", {"type": "feature"})

        assert "error" in result


class TestProjectManagerArtifactCollection:
    """测试产出收集"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_collect_developer_artifact(self, project_manager, memory_manager):
        """测试收集开发者产出"""
        # 先分配任务
        project_manager.assign_task_to_role("developer", {
            "type": "feature",
            "description": "功能开发",
        })

        # 收集产出
        success = project_manager.collect_artifact("developer", {
            "code": "def shopping_cart(): pass"
        })

        assert success is True

        # 验证开发文档已更新
        doc = memory_manager.get_document(DocumentType.DEVELOPMENT)
        assert "shopping_cart" in doc

    def test_collect_product_manager_artifact(self, project_manager, memory_manager):
        """测试收集产品经理产出"""
        project_manager.assign_task_to_role("product_manager", {
            "type": "requirement",
            "description": "需求分析",
        })

        success = project_manager.collect_artifact("product_manager", {
            "requirements": "# 需求文档\n\n## REQ-001: 登录功能"
        })

        assert success is True

        doc = memory_manager.get_document(DocumentType.REQUIREMENTS)
        assert "登录功能" in doc

    def test_collect_architect_artifact(self, project_manager, memory_manager):
        """测试收集架构师产出"""
        project_manager.assign_task_to_role("architect", {
            "type": "design",
            "description": "架构设计",
        })

        success = project_manager.collect_artifact("architect", {
            "design": "# 设计文档\n\n## 架构概述"
        })

        assert success is True

        doc = memory_manager.get_document(DocumentType.DESIGN)
        assert "架构概述" in doc

    def test_collect_tester_artifact(self, project_manager, memory_manager):
        """测试收集测试人员产出"""
        project_manager.assign_task_to_role("tester", {
            "type": "test",
            "description": "测试执行",
        })

        success = project_manager.collect_artifact("tester", {
            "report": "测试报告：全部通过"
        })

        assert success is True

        doc = memory_manager.get_document(DocumentType.TESTING)
        assert "测试报告" in doc

    def test_collect_artifact_updates_task_status(self, project_manager):
        """测试收集产出更新任务状态"""
        project_manager.assign_task_to_role("developer", {
            "type": "feature",
            "description": "功能开发",
        })

        # 任务状态为 pending
        assert project_manager._task_assignments[0].status == "pending"

        project_manager.collect_artifact("developer", {"code": "code"})

        # 任务状态更新为 completed
        assert project_manager._task_assignments[0].status == "completed"
        assert project_manager._task_assignments[0].completed_at is not None

    def test_collect_artifact_without_state(self):
        """测试无状态管理器时收集产出"""
        pm = ProjectManager()
        success = pm.collect_artifact("developer", {"code": "code"})

        assert success is False


class TestProjectManagerProgressTracking:
    """测试进度追踪"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_progress_update(self, project_manager, memory_manager):
        """测试进度更新"""
        # 分配并完成一个任务
        project_manager.assign_task_to_role("developer", {"type": "feature", "description": "功能A"})
        project_manager.collect_artifact("developer", {"code": "code"})

        # 检查进度文档
        doc = memory_manager.get_document(DocumentType.PROGRESS)
        assert "项目进度报告" in doc
        assert "已完成: 1" in doc

    def test_progress_report_content(self, project_manager, memory_manager):
        """测试进度报告内容"""
        # 分配多个任务
        project_manager.assign_task_to_role("developer", {"type": "feature", "description": "功能A"})
        project_manager.assign_task_to_role("developer", {"type": "feature", "description": "功能B"})
        project_manager.collect_artifact("developer", {"code": "code"})

        doc = memory_manager.get_document(DocumentType.PROGRESS)

        assert "总任务数: 2" in doc
        assert "已完成: 1" in doc
        assert "进行中: 1" in doc
        assert "完成率: 50.0%" in doc

    def test_track_progress_task(self, project_manager):
        """测试进度追踪任务"""
        project_manager._current_task = {"inputs": {}}

        result = project_manager._track_progress()

        assert result["status"] == "completed"
        assert "progress_report" in result["outputs"]
        assert "blockers" in result["outputs"]
        assert "recommendations" in result["outputs"]


class TestProjectManagerContextGeneration:
    """测试上下文生成"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_create_context_for_developer(self, project_manager):
        """测试为开发者创建上下文"""
        context = project_manager.create_context_for_developer()

        assert isinstance(context, dict)

    def test_create_context_for_product_manager(self, project_manager):
        """测试为产品经理创建上下文"""
        context = project_manager.create_context_for_product_manager()

        assert isinstance(context, dict)

    def test_create_context_for_architect(self, project_manager):
        """测试为架构师创建上下文"""
        context = project_manager.create_context_for_architect()

        assert isinstance(context, dict)

    def test_create_context_for_tester(self, project_manager):
        """测试为测试人员创建上下文"""
        context = project_manager.create_context_for_tester()

        assert isinstance(context, dict)

    def test_create_context_without_state(self):
        """测试无状态管理器时创建上下文"""
        pm = ProjectManager()

        context = pm.create_context_for_developer()
        assert context == {}


class TestProjectManagerDocumentManagement:
    """测试文档管理"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def project_manager(self, memory_manager):
        """创建带状态管理器的项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_get_document_full(self, project_manager, memory_manager):
        """测试获取完整文档"""
        memory_manager.store_document(DocumentType.REQUIREMENTS, "完整需求文档内容")

        doc = project_manager.get_document(DocumentType.REQUIREMENTS, full=True)

        assert doc == "完整需求文档内容"

    def test_get_document_summary(self, project_manager, memory_manager):
        """测试获取文档摘要"""
        memory_manager.store_document(DocumentType.REQUIREMENTS, "需求文档内容")

        doc = project_manager.get_document(DocumentType.REQUIREMENTS, full=False)

        assert doc is not None

    def test_update_document(self, project_manager, memory_manager):
        """测试更新文档"""
        success = project_manager.update_document(
            DocumentType.DESIGN,
            "# 设计文档\n\n## 概述"
        )

        assert success is True

        doc = memory_manager.get_document(DocumentType.DESIGN)
        assert "设计文档" in doc

    def test_get_document_without_state(self):
        """测试无状态管理器时获取文档"""
        pm = ProjectManager()
        doc = pm.get_document(DocumentType.REQUIREMENTS)

        assert doc is None

    def test_update_document_without_state(self):
        """测试无状态管理器时更新文档"""
        pm = ProjectManager()
        success = pm.update_document(DocumentType.REQUIREMENTS, "内容")

        assert success is False


class TestProjectManagerTaskExecution:
    """测试任务执行"""

    def test_coordinate_task(self):
        """测试协调任务"""
        pm = ProjectManager()
        pm._current_task = {
            "inputs": {
                "tasks": ["任务A", "任务B", "任务C"]
            }
        }

        result = pm._execute_by_type(TaskType.COORDINATE)

        assert result["status"] == "completed"
        assert "assignments" in result["outputs"]
        assert "schedule" in result["outputs"]

    def test_track_progress_task(self):
        """测试进度追踪任务"""
        pm = ProjectManager()
        pm._current_task = {"inputs": {}}

        result = pm._execute_by_type(TaskType.TRACK_PROGRESS)

        assert result["status"] == "completed"
        assert "progress_report" in result["outputs"]

    def test_execute_unsupported_task(self):
        """测试不支持的任务类型"""
        pm = ProjectManager()

        # WRITE_USER_STORY 不在 ProjectManager 支持的任务类型中
        result = pm._execute_by_type(TaskType.WRITE_USER_STORY)

        assert result["status"] == "error"
        assert "Unsupported task" in result["message"]


class TestProjectManagerIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    def test_full_workflow(self, memory_manager):
        """测试完整工作流"""
        # 1. 创建项目经理
        pm = ProjectManager(state_manager=memory_manager)

        # 2. 分配任务给开发者
        result = pm.assign_task_to_role("developer", {
            "type": "implement_feature",
            "description": "实现购物车功能",
        })
        assert result["status"] == "assigned"

        # 3. 收集开发者产出
        success = pm.collect_artifact("developer", {
            "code": "class ShoppingCart: pass"
        })
        assert success is True

        # 4. 获取项目状态
        status = pm.get_project_status()
        assert "project" in status

        # 5. 检查进度报告
        progress = memory_manager.get_document(DocumentType.PROGRESS)
        assert "项目进度报告" in progress

    def test_multi_role_collaboration(self, memory_manager):
        """测试多角色协作"""
        pm = ProjectManager(state_manager=memory_manager)

        # 产品经理分析需求
        pm.assign_task_to_role("product_manager", {"type": "analyze", "description": "分析需求"})
        pm.collect_artifact("product_manager", {"requirements": "# 需求\n登录功能"})

        # 架构师设计
        pm.assign_task_to_role("architect", {"type": "design", "description": "设计架构"})
        pm.collect_artifact("architect", {"design": "# 设计\nMVC架构"})

        # 开发者实现
        pm.assign_task_to_role("developer", {"type": "develop", "description": "实现功能"})
        pm.collect_artifact("developer", {"code": "def login(): pass"})

        # 测试人员测试
        pm.assign_task_to_role("tester", {"type": "test", "description": "执行测试"})
        pm.collect_artifact("tester", {"report": "测试通过"})

        # 验证所有文档已更新
        assert memory_manager.get_document(DocumentType.REQUIREMENTS) is not None
        assert memory_manager.get_document(DocumentType.DESIGN) is not None
        assert memory_manager.get_document(DocumentType.DEVELOPMENT) is not None
        assert memory_manager.get_document(DocumentType.TESTING) is not None

        # 验证进度报告
        progress = memory_manager.get_document(DocumentType.PROGRESS)
        assert "已完成: 4" in progress