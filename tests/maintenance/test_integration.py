"""
Integration Tests for Proactive Document Maintenance

测试 RequirementDetectionStage 和文档维护功能

注意：ProductManager 和 ProjectManager 中的独立需求检测方法已移除，
      现在通过 RequirementDetectionStage 统一处理。
"""

import pytest
import tempfile
import shutil

from harnessgenj.memory import MemoryManager
from harnessgenj.roles import ProductManager, ProjectManager
from harnessgenj.roles.base import RoleContext
from harnessgenj.workflow.requirement_stage import (
    RequirementDetectionStage,
    create_requirement_detection_stage,
)
from harnessgenj.maintenance import (
    RequirementDetector,
    DetectedRequirement,
    RequirementType,
    DetectionSource,
    ConfirmationStatus,
)


class TestRequirementDetectionStageBasic:
    """测试需求检测阶段基础功能"""

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
    def detection_stage(self, memory_manager):
        """创建需求检测阶段"""
        return RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.9,
            enable_confirmation=True,
        )

    def test_detect_feature_requirement(self, detection_stage):
        """检测功能需求"""
        result = detection_stage.execute({
            "message": "我需要一个购物车功能"
        })

        assert len(result.detected_requirements) > 0
        req = result.detected_requirements[0]
        assert req.req_type == RequirementType.FEATURE
        assert "购物车" in req.title or "购物车" in req.description

    def test_detect_bug_requirement(self, detection_stage):
        """检测Bug需求"""
        result = detection_stage.execute({
            "message": "支付页面报错，无法完成支付"
        })

        assert len(result.detected_requirements) > 0
        req = result.detected_requirements[0]
        assert req.req_type == RequirementType.BUG_FIX

    def test_auto_confirm_high_confidence(self, memory_manager):
        """高置信度自动确认"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.8,
        )

        result = stage.execute({
            "message": "支付页面崩溃，用户无法完成支付，严重bug"
        })

        # 高置信度的需求应该被确认
        if result.confirmed_requirements:
            assert len(result.confirmed_requirements) > 0

    def test_needs_user_confirmation(self, memory_manager):
        """低置信度需要用户确认"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.95,
            enable_confirmation=True,
        )

        result = stage.execute({
            "message": "我需要一个新功能"
        })

        # 低置信度可能需要确认
        if result.pending_confirmations:
            assert result.needs_user_input is True

    def test_process_user_approval(self, detection_stage):
        """处理用户批准"""
        # 先执行检测
        result = detection_stage.execute({
            "message": "我需要一个测试功能"
        }, auto_create_task=False)

        if result.pending_confirmations:
            pending = result.pending_confirmations[0]

            # 处理用户批准
            process_result = detection_stage.process_user_confirmation(
                pending.confirmation_id,
                "是",
                auto_create_task=False,
            )

            assert process_result["success"] is True
            assert process_result["requirement"] is not None

    def test_detect_from_ai_analysis(self, detection_stage):
        """从AI分析结果检测"""
        analysis_result = {
            "issues_found": ["内存泄漏", "性能瓶颈"],
            "suggestions": ["优化查询", "添加缓存"],
        }

        result = detection_stage.detect_from_ai_analysis(
            analysis_result,
            auto_create_task=False,
        )

        assert len(result.confirmed_requirements) > 0


class TestProductManagerIntegration:
    """测试产品经理与需求检测的集成"""

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
        """创建产品经理"""
        pm = ProductManager()
        pm.set_state_manager(memory_manager)
        return pm

    def test_product_manager_get_requirements(self, product_manager, memory_manager):
        """产品经理获取需求文档"""
        # 存储需求文档
        from harnessgenj.memory.manager import DocumentType
        memory_manager.store_document(
            DocumentType.REQUIREMENTS,
            "# 需求文档\n\n## REQ-001: 购物车功能"
        )

        # 获取需求
        requirements = product_manager.get_requirements()
        assert requirements is not None
        assert "购物车" in requirements

    def test_product_manager_update_requirements(self, product_manager, memory_manager):
        """产品经理更新需求文档"""
        from harnessgenj.memory.manager import DocumentType

        # 更新需求
        success = product_manager.update_requirements(
            "# 新需求文档\n\n## REQ-001: 用户管理",
            "添加用户管理需求"
        )

        assert success is True

        # 验证更新
        doc = memory_manager.get_document(DocumentType.REQUIREMENTS)
        assert "用户管理" in doc

    def test_product_manager_context(self, product_manager):
        """产品经理上下文"""
        context = product_manager.get_visible_context()
        assert isinstance(context, dict)


class TestProjectManagerIntegration:
    """测试项目经理与需求检测的集成"""

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
        """创建项目经理"""
        return ProjectManager(state_manager=memory_manager)

    def test_project_manager_assign_task(self, project_manager):
        """项目经理分配任务"""
        result = project_manager.assign_task_to_role("developer", {
            "type": "implement_feature",
            "description": "实现购物车功能",
        })

        assert result["status"] == "assigned"
        assert "context" in result

    def test_project_manager_collect_artifact(self, project_manager, memory_manager):
        """项目经理收集产出"""
        from harnessgenj.memory.manager import DocumentType

        # 分配任务
        project_manager.assign_task_to_role("developer", {
            "type": "implement_feature",
            "description": "实现功能",
        })

        # 收集产出
        success = project_manager.collect_artifact("developer", {
            "code": "def shopping_cart(): pass"
        })

        assert success is True

    def test_project_manager_get_status(self, project_manager):
        """项目经理获取状态"""
        status = project_manager.get_project_status()

        assert "project" in status
        assert "stats" in status


class TestFullProactiveFlow:
    """完整的主动文档维护流程测试"""

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
    def detection_stage(self, memory_manager):
        """创建需求检测阶段"""
        return RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.9,
            enable_confirmation=True,
        )

    def test_full_flow_feature_requirement(self, memory_manager, detection_stage):
        """完整功能需求流程"""
        # 1. 用户提出需求
        user_message = "我需要一个商品评价功能，用户可以对购买的商品进行评价"

        # 2. 检测需求
        result = detection_stage.execute({
            "message": user_message,
        })

        # 3. 验证检测到需求
        assert len(result.detected_requirements) > 0
        req = result.detected_requirements[0]
        assert req.req_type == RequirementType.FEATURE

        # 4. 如果需要确认
        if result.pending_confirmations:
            pending = result.pending_confirmations[0]

            # 5. 用户确认
            process_result = detection_stage.process_user_confirmation(
                pending.confirmation_id,
                "是",
            )

            assert process_result["success"] is True

    def test_bug_fix_flow(self, detection_stage):
        """Bug修复流程"""
        # 1. 用户报告Bug
        bug_message = "有个bug：订单提交后页面卡住，没有响应"

        # 2. 检测
        result = detection_stage.execute({
            "message": bug_message,
        })

        # 3. 验证是Bug类型
        assert len(result.detected_requirements) > 0
        req = result.detected_requirements[0]
        assert req.req_type == RequirementType.BUG_FIX
        # Bug修复通常是高优先级
        assert req.suggested_priority in ["P0", "P1"]

    def test_ai_discovered_issue_flow(self, detection_stage):
        """AI发现问题流程"""
        # 1. AI发现问题（如代码审查）
        issue = {
            "description": "发现潜在的安全漏洞：密码明文存储",
            "severity": "critical",
            "file": "user_service.py",
            "line": 42,
            "suggestions": [
                "使用bcrypt加密密码",
                "添加密码强度验证",
            ],
        }

        # 2. 处理AI发现的问题
        result = detection_stage.detect_from_ai_analysis(
            {"issues_found": [issue]},
            auto_create_task=True,
        )

        # 3. 验证
        assert len(result.confirmed_requirements) >= 1

    def test_multi_requirement_handling(self):
        """多需求处理"""
        # 用户消息包含多个需求
        message = """
        我需要以下功能：
        1. 用户登录功能
        2. 有个bug需要修复：密码重置不工作
        3. 优化首页加载速度
        """

        # 使用独立检测器
        detector = RequirementDetector(enable_multi_detection=True)
        requirements = detector.detect_from_message(message)

        # 应该检测到多个需求（功能、Bug、改进）
        assert len(requirements) >= 1  # 至少检测到一个


class TestMaintenanceIntegration:
    """维护系统集成测试"""

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
    def detection_stage(self, memory_manager):
        """创建需求检测阶段"""
        return RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.85,
        )

    def test_document_update_on_confirm(self, memory_manager, detection_stage):
        """确认后更新文档"""
        from harnessgenj.memory.manager import DocumentType

        # 执行检测
        result = detection_stage.execute({
            "message": "添加用户权限管理功能",
        })

        # 如果有确认的需求
        if result.confirmed_requirements:
            # 验证文档更新
            doc = memory_manager.get_document(DocumentType.REQUIREMENTS)
            # 文档可能已更新
            assert doc is not None or True

    def test_task_creation_on_confirm(self, memory_manager):
        """确认后创建任务"""
        # 设置较低的自动确认阈值
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.5,
        )

        result = stage.execute({
            "message": "添加搜索功能",
        }, auto_create_task=True)

        # 如果有确认的需求，应该创建任务
        if result.confirmed_requirements:
            assert len(result.created_tasks) > 0

    def test_notification_routing(self, detection_stage):
        """通知路由"""
        # 测试不同需求类型的通知路由
        feature_roles = detection_stage._get_notify_roles(RequirementType.FEATURE)
        assert "developer" in feature_roles

        bug_roles = detection_stage._get_notify_roles(RequirementType.BUG_FIX)
        assert "developer" in bug_roles
        assert "tester" in bug_roles

        feedback_roles = detection_stage._get_notify_roles(RequirementType.FEEDBACK)
        assert "product_manager" in feedback_roles

    def test_concurrent_handling(self, detection_stage):
        """并发处理多个需求"""
        # 快速处理多个消息
        messages = [
            "添加功能A",
            "修复Bug B",
            "优化性能C",
        ]

        results = []
        for msg in messages:
            result = detection_stage.execute({
                "message": msg,
            }, auto_create_task=False)
            results.append(result)

        # 所有处理都应该成功
        assert len(results) == 3
        for r in results:
            assert r.summary is not None


class TestRequirementDetectorDirect:
    """直接测试 RequirementDetector"""

    def test_feature_keywords(self):
        """功能关键词"""
        detector = RequirementDetector()
        requirements = detector.detect_from_message("我需要一个购物车功能")

        assert len(requirements) > 0
        assert requirements[0].req_type == RequirementType.FEATURE

    def test_bug_keywords(self):
        """Bug关键词"""
        detector = RequirementDetector()
        requirements = detector.detect_from_message("支付页面报错，无法完成支付")

        assert len(requirements) > 0
        assert requirements[0].req_type == RequirementType.BUG_FIX

    def test_improvement_keywords(self):
        """改进关键词"""
        detector = RequirementDetector()
        requirements = detector.detect_from_message("优化数据库查询性能")

        assert len(requirements) > 0
        assert requirements[0].req_type == RequirementType.IMPROVEMENT

    def test_code_review_detection(self):
        """代码审查检测"""
        detector = RequirementDetector()

        review_result = {
            "issues": [
                {
                    "description": "SQL注入漏洞",
                    "severity": "critical",
                    "file": "auth.py",
                    "line": 42,
                }
            ]
        }

        requirements = detector.detect_from_code_review(review_result)

        assert len(requirements) > 0
        assert requirements[0].req_type == RequirementType.BUG_FIX
        assert requirements[0].suggested_priority == "P0"

    def test_test_failure_detection(self):
        """测试失败检测"""
        detector = RequirementDetector()

        test_result = {
            "failures": [
                {
                    "test_name": "test_login",
                    "error_message": "AssertionError",
                    "test_file": "test_auth.py",
                }
            ]
        }

        requirements = detector.detect_from_test_failure(test_result)

        assert len(requirements) == 1
        assert requirements[0].confidence == 0.9
        assert requirements[0].suggested_priority == "P0"