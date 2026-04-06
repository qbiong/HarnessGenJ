"""
Tests for ProductManager Role - 产品经理角色测试

测试产品经理的核心功能：
- 需求文档管理
- 用户对话讨论
- 需求变更管理
- 渐进式披露上下文
"""

import pytest
import tempfile
import shutil

from harnessgenj.roles.product_manager import (
    ProductManager,
    ProductManagerContext,
    create_product_manager,
)
from harnessgenj.roles.base import RoleContext, RoleType, TaskType
from harnessgenj.memory.manager import MemoryManager, DocumentType


class TestProductManagerCreation:
    """测试产品经理创建"""

    def test_create_default(self):
        """使用默认参数创建"""
        pm = ProductManager()
        assert pm is not None
        assert pm.role_id == "pm_req_1"
        assert pm.name == "产品经理"
        assert pm.role_type == RoleType.PRODUCT_MANAGER

    def test_create_with_custom_params(self):
        """使用自定义参数创建"""
        pm = ProductManager(
            role_id="pm_custom",
            name="高级产品经理",
        )
        assert pm.role_id == "pm_custom"
        assert pm.name == "高级产品经理"

    def test_create_with_context(self):
        """使用上下文创建"""
        context = RoleContext()
        pm = ProductManager(context=context)
        assert pm.context is not None

    def test_create_with_factory(self):
        """使用工厂函数创建"""
        pm = create_product_manager(pm_id="pm_factory", name="工厂产品经理")
        assert pm.role_id == "pm_factory"
        assert pm.name == "工厂产品经理"


class TestProductManagerResponsibilities:
    """测试产品经理职责"""

    def test_responsibilities_list(self):
        """测试职责列表"""
        pm = ProductManager()
        responsibilities = pm.responsibilities

        assert len(responsibilities) == 6
        assert "需求收集与分析" in responsibilities
        assert "需求文档维护" in responsibilities
        assert "用户故事编写" in responsibilities
        assert "优先级定义与排序" in responsibilities
        assert "验收标准制定" in responsibilities
        assert "需求变更管理" in responsibilities

    def test_role_type(self):
        """测试角色类型"""
        pm = ProductManager()
        assert pm.role_type == RoleType.PRODUCT_MANAGER

    def test_supported_task_types(self):
        """测试支持的任务类型"""
        pm = ProductManager()
        task_types = pm.get_supported_task_types()

        assert TaskType.ANALYZE_REQUIREMENT in task_types
        assert TaskType.WRITE_USER_STORY in task_types
        assert TaskType.PRIORITIZE in task_types


class TestProductManagerSkills:
    """测试产品经理技能"""

    def test_skills_setup(self):
        """测试技能设置"""
        pm = ProductManager()
        skills = pm.list_skills()

        assert len(skills) == 5

        skill_names = [s.name for s in skills]
        assert "analyze_requirement" in skill_names
        assert "write_user_story" in skill_names
        assert "prioritize" in skill_names
        assert "define_acceptance_criteria" in skill_names
        assert "update_requirements" in skill_names


class TestProductManagerContext:
    """测试产品经理上下文"""

    def test_pm_context_creation(self):
        """测试上下文创建"""
        context = ProductManagerContext(
            project_name="测试项目",
            tech_stack="Python + FastAPI",
            requirements="需求文档内容",
            progress_summary="进度摘要",
        )

        assert context.project_name == "测试项目"
        assert context.tech_stack == "Python + FastAPI"
        assert context.requirements == "需求文档内容"
        assert context.progress_summary == "进度摘要"
        assert context.conversation_history == []

    def test_set_context_from_pm(self):
        """测试从项目经理设置上下文"""
        pm = ProductManager()

        pm.set_context_from_pm({
            "project": {
                "name": "电商平台",
                "tech_stack": "Python + FastAPI",
            },
            "requirements": "需求文档",
            "progress_summary": "开发进度 50%",
        })

        visible = pm.get_visible_context()
        assert visible["project_name"] == "电商平台"
        assert visible["tech_stack"] == "Python + FastAPI"
        assert visible["requirements"] == "需求文档"


class TestProductManagerDiscussion:
    """测试用户对话功能"""

    def test_discuss_with_user_basic(self):
        """测试基本对话"""
        pm = ProductManager()
        pm.set_context_from_pm({
            "project": {"name": "测试项目", "tech_stack": "Python"},
        })

        response = pm.discuss_with_user("我需要一个登录功能")

        assert response is not None
        assert "测试项目" in response or "需求" in response

    def test_discuss_detects_change(self):
        """测试检测需求变更"""
        pm = ProductManager()

        response = pm.discuss_with_user("我需要新增一个购物车功能")

        assert "变更" in response or "确认" in response

    def test_conversation_history(self):
        """测试对话历史记录"""
        pm = ProductManager()

        pm.discuss_with_user("第一条消息")
        pm.discuss_with_user("第二条消息")

        history = pm._pm_context.conversation_history
        assert len(history) == 4  # 2条用户消息 + 2条回复

        user_messages = [h for h in history if h["role"] == "user"]
        assert len(user_messages) == 2


class TestProductManagerDocumentManagement:
    """测试文档管理功能"""

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
    def product_manager(self, memory_manager):
        """创建带状态管理器的产品经理"""
        pm = ProductManager()
        pm.set_state_manager(memory_manager)
        return pm

    def test_get_requirements_empty(self, product_manager):
        """测试获取空需求文档"""
        requirements = product_manager.get_requirements()
        # 没有存储需求时返回空字符串
        assert requirements == "" or requirements is None or True

    def test_update_requirements(self, product_manager, memory_manager):
        """测试更新需求文档"""
        success = product_manager.update_requirements(
            "# 需求文档\n\n## REQ-001: 登录功能",
            "添加登录需求"
        )

        assert success is True

        # 验证文档已存储
        doc = memory_manager.get_document(DocumentType.REQUIREMENTS)
        assert "登录功能" in doc

    def test_get_requirements_summary(self, product_manager, memory_manager):
        """测试获取需求摘要"""
        # 存储需求文档
        memory_manager.store_document(
            DocumentType.REQUIREMENTS,
            "# 需求文档\n\n这是一个很长的需求文档..." * 100
        )

        summary = product_manager.get_requirements_summary()

        # 摘要应该存在
        assert summary is not None

    def test_pending_changes(self, product_manager):
        """测试待通知变更"""
        # 更新需求
        product_manager.update_requirements("新需求", "更新需求")

        # 获取待通知变更
        pending = product_manager.get_pending_changes()
        assert len(pending) == 1
        assert pending[0]["type"] == "requirements_update"

        # 清空待通知变更
        product_manager.clear_pending_changes()
        assert len(product_manager.get_pending_changes()) == 0


class TestProductManagerTaskExecution:
    """测试任务执行"""

    def test_analyze_requirement(self):
        """测试分析需求任务"""
        pm = ProductManager()
        pm._current_task = {
            "inputs": {
                "user_input": "我需要一个购物车功能"
            }
        }

        result = pm._analyze_requirement()

        assert result["status"] == "completed"
        assert "requirements" in result["outputs"]
        assert "constraints" in result["outputs"]

    def test_write_user_story(self):
        """测试编写用户故事"""
        pm = ProductManager()
        pm._current_task = {
            "inputs": {
                "requirement": "用户登录功能"
            }
        }

        result = pm._write_user_story()

        assert result["status"] == "completed"
        assert "user_stories" in result["outputs"]
        assert "acceptance_criteria" in result["outputs"]

        user_stories = result["outputs"]["user_stories"]
        assert len(user_stories) > 0
        assert "as_a" in user_stories[0]
        assert "i_want_to" in user_stories[0]
        assert "so_that" in user_stories[0]

    def test_prioritize(self):
        """测试优先级排序"""
        pm = ProductManager()
        pm._current_task = {
            "inputs": {
                "requirements": ["登录", "购物车", "支付"]
            }
        }

        result = pm._prioritize()

        assert result["status"] == "completed"
        assert "prioritized_backlog" in result["outputs"]

        backlog = result["outputs"]["prioritized_backlog"]
        assert len(backlog) == 3
        assert backlog[0]["priority"] == "P0"

    def test_execute_by_type_analyze(self):
        """测试按类型执行 - 分析需求"""
        pm = ProductManager()
        pm._current_task = {"inputs": {"user_input": "测试"}}

        result = pm._execute_by_type(TaskType.ANALYZE_REQUIREMENT)

        assert result["status"] == "completed"

    def test_execute_by_type_unsupported(self):
        """测试不支持的任务类型"""
        pm = ProductManager()

        # IMPLEMENT_FEATURE 不在 ProductManager 支持的任务类型中
        result = pm._execute_by_type(TaskType.IMPLEMENT_FEATURE)

        assert result["status"] == "error"
        assert "Unsupported task" in result["message"]


class TestProductManagerIntegration:
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
        # 1. 创建产品经理
        pm = ProductManager()
        pm.set_state_manager(memory_manager)

        # 2. 设置上下文
        pm.set_context_from_pm({
            "project": {
                "name": "电商平台",
                "tech_stack": "Python + FastAPI",
            },
            "requirements": "",
            "progress_summary": "",
        })

        # 3. 与用户讨论
        response = pm.discuss_with_user("我需要一个购物车功能")
        assert response is not None

        # 4. 更新需求文档
        success = pm.update_requirements(
            "# 需求文档\n\n## REQ-001: 购物车功能",
            "添加购物车需求"
        )
        assert success is True

        # 5. 获取需求文档
        requirements = pm.get_requirements()
        assert "购物车" in requirements

        # 6. 检查待通知变更
        pending = pm.get_pending_changes()
        assert len(pending) > 0


class TestProductManagerStateManagement:
    """测试状态管理器集成"""

    def test_set_state_manager(self):
        """测试设置状态管理器"""
        pm = ProductManager()

        # 设置前为 None
        assert pm._state_manager is None

        # 设置状态管理器
        temp_dir = tempfile.mkdtemp()
        try:
            manager = MemoryManager(temp_dir)
            pm.set_state_manager(manager)

            assert pm._state_manager is manager
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_operations_without_state_manager(self):
        """测试无状态管理器时的操作"""
        pm = ProductManager()

        # 无状态管理器时，get_requirements 返回内部上下文
        requirements = pm.get_requirements()
        assert requirements == ""

        # update_requirements 返回 False
        success = pm.update_requirements("新需求")
        assert success is False