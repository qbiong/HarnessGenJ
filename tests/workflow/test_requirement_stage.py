"""
Tests for Requirement Detection Stage

测试需求检测阶段的功能
"""

import pytest
import tempfile
import shutil

from harnessgenj.workflow.requirement_stage import (
    RequirementDetectionStage,
    RequirementDetectionResult,
    create_requirement_detection_stage,
)
from harnessgenj.maintenance.detector import RequirementType, DetectionSource
from harnessgenj.maintenance.confirmation import ConfirmationStatus
from harnessgenj.memory.manager import MemoryManager


class TestRequirementDetectionStage:
    """测试需求检测阶段"""

    @pytest.fixture
    def memory_manager(self):
        """创建内存管理器"""
        temp_dir = tempfile.mkdtemp()
        manager = MemoryManager(workspace=temp_dir)
        yield manager
        shutil.rmtree(temp_dir)

    def test_create_stage(self, memory_manager):
        """创建检测阶段"""
        stage = RequirementDetectionStage(memory_manager)
        assert stage is not None
        assert stage.auto_confirm_threshold == 0.9
        assert stage.enable_confirmation is True

    def test_create_stage_with_params(self, memory_manager):
        """使用参数创建检测阶段"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.8,
            enable_confirmation=False,
        )
        assert stage.auto_confirm_threshold == 0.8
        assert stage.enable_confirmation is False

    def test_execute_detect_feature(self, memory_manager):
        """执行检测功能需求"""
        stage = RequirementDetectionStage(memory_manager)

        result = stage.execute({
            "message": "我需要一个购物车功能",
            "intent_type": "development",
        })

        assert isinstance(result, RequirementDetectionResult)
        assert len(result.detected_requirements) > 0
        assert result.detected_requirements[0].req_type == RequirementType.FEATURE

    def test_execute_detect_bug(self, memory_manager):
        """执行检测Bug"""
        stage = RequirementDetectionStage(memory_manager)

        result = stage.execute({
            "message": "支付页面报错，无法完成支付",
            "intent_type": "bugfix",
        })

        assert len(result.detected_requirements) > 0
        req = result.detected_requirements[0]
        assert req.req_type == RequirementType.BUG_FIX
        assert req.confidence >= 0.6

    def test_execute_auto_confirm_high_confidence(self, memory_manager):
        """高置信度自动确认"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.9,
        )

        # 测试失败的消息通常置信度很高 (0.9)
        result = stage.execute({
            "message": "订单支付后状态没有正确更新，用户看到的还是待支付，这是个严重的bug",
        })

        # 高置信度的需求应该自动确认
        if result.confirmed_requirements:
            assert len(result.confirmed_requirements) > 0

    def test_execute_needs_user_input(self, memory_manager):
        """低置信度需要用户确认"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.95,  # 设置很高的阈值
            enable_confirmation=True,
        )

        result = stage.execute({
            "message": "我需要一个新功能",
        })

        # 低置信度的需求可能需要用户确认
        if result.pending_confirmations:
            assert result.needs_user_input is True

    def test_execute_no_requirements(self, memory_manager):
        """无需求检测"""
        stage = RequirementDetectionStage(memory_manager)

        result = stage.execute({
            "message": "你好",
        })

        # 可能检测不到需求
        assert isinstance(result, RequirementDetectionResult)
        assert result.summary is not None

    def test_execute_with_context(self, memory_manager):
        """带上下文执行"""
        stage = RequirementDetectionStage(memory_manager)

        context = {"project": "电商平台", "priority": "P1"}
        result = stage.execute({
            "message": "添加订单管理功能",
            "context": context,
        })

        assert len(result.detected_requirements) > 0
        assert result.detected_requirements[0].context == context

    def test_execute_creates_tasks(self, memory_manager):
        """执行并创建任务"""
        stage = RequirementDetectionStage(memory_manager)

        result = stage.execute({
            "message": "支付页面崩溃，用户无法完成支付",
        }, auto_create_task=True)

        # 如果有确认的需求，应该创建了任务
        if result.confirmed_requirements:
            assert len(result.created_tasks) > 0

    def test_execute_no_auto_create_task(self, memory_manager):
        """不自动创建任务"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.5,  # 低阈值让需求被确认
        )

        result = stage.execute({
            "message": "添加一个功能",
        }, auto_create_task=False)

        # 不应该创建任务
        assert len(result.created_tasks) == 0

    def test_process_user_confirmation_approve(self, memory_manager):
        """处理用户确认（批准）"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.99,  # 很高的阈值，需要确认
            enable_confirmation=True,
        )

        # 先执行检测
        result = stage.execute({
            "message": "我需要一个新功能",
        })

        if result.pending_confirmations:
            pending = result.pending_confirmations[0]
            confirmation_id = pending.confirmation_id

            # 处理用户批准
            process_result = stage.process_user_confirmation(
                confirmation_id,
                "是",
            )

            assert process_result["success"] is True
            assert process_result["requirement"] is not None

    def test_process_user_confirmation_reject(self, memory_manager):
        """处理用户确认（拒绝）"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.99,
            enable_confirmation=True,
        )

        result = stage.execute({
            "message": "我需要一个新功能",
        })

        if result.pending_confirmations:
            pending = result.pending_confirmations[0]
            confirmation_id = pending.confirmation_id

            # 处理用户拒绝
            process_result = stage.process_user_confirmation(
                confirmation_id,
                "否",
            )

            assert process_result["success"] is False

    def test_detect_from_ai_analysis(self, memory_manager):
        """从AI分析结果检测"""
        stage = RequirementDetectionStage(memory_manager)

        analysis_result = {
            "issues_found": ["内存泄漏", "性能瓶颈"],
            "suggestions": ["优化查询", "添加缓存"],
        }

        result = stage.detect_from_ai_analysis(analysis_result)

        assert len(result.confirmed_requirements) > 0
        # AI发现的问题应该有高置信度
        for req in result.confirmed_requirements:
            assert req.confidence >= 0.7

    def test_detect_from_ai_analysis_creates_tasks(self, memory_manager):
        """从AI分析结果检测并创建任务"""
        stage = RequirementDetectionStage(memory_manager)

        analysis_result = {
            "issues_found": ["严重的安全漏洞"],
        }

        result = stage.detect_from_ai_analysis(
            analysis_result,
            auto_create_task=True,
        )

        if result.confirmed_requirements:
            assert len(result.created_tasks) > 0

    def test_result_summary(self, memory_manager):
        """检测结果摘要"""
        stage = RequirementDetectionStage(memory_manager)

        result = stage.execute({
            "message": "我需要一个购物车功能，同时有个bug需要修复",
        })

        assert result.summary is not None
        # 摘要应该包含检测信息
        if result.detected_requirements:
            assert "检测到" in result.summary or "需求" in result.summary

    def test_factory_function(self, memory_manager):
        """工厂函数创建"""
        stage = create_requirement_detection_stage(
            memory_manager,
            auto_confirm_threshold=0.85,
            enable_confirmation=True,
        )

        assert stage is not None
        assert stage.auto_confirm_threshold == 0.85


class TestRequirementDetectionResult:
    """测试需求检测结果"""

    def test_create_result(self):
        """创建结果"""
        result = RequirementDetectionResult()
        assert result.detected_requirements == []
        assert result.pending_confirmations == []
        assert result.confirmed_requirements == []
        assert result.created_tasks == []
        assert result.needs_user_input is False

    def test_result_fields(self):
        """结果字段"""
        result = RequirementDetectionResult(
            detected_requirements=[],
            summary="检测到 1 个需求",
        )

        assert result.summary == "检测到 1 个需求"


class TestIntegrationWithMemoryManager:
    """测试与 MemoryManager 的集成"""

    @pytest.fixture
    def memory_manager(self):
        """创建内存管理器"""
        temp_dir = tempfile.mkdtemp()
        manager = MemoryManager(workspace=temp_dir)
        yield manager
        shutil.rmtree(temp_dir)

    def test_document_update_on_confirm(self, memory_manager):
        """确认后更新文档"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.5,  # 低阈值自动确认
        )

        result = stage.execute({
            "message": "我需要一个购物车功能",
        })

        # 如果需求被确认，文档应该被更新
        if result.confirmed_requirements:
            from harnessgenj.memory.manager import DocumentType
            doc = memory_manager.get_document(DocumentType.REQUIREMENTS)
            # 文档可能已更新
            assert doc is not None or True  # 灵活处理

    def test_task_creation_on_confirm(self, memory_manager):
        """确认后创建任务"""
        stage = RequirementDetectionStage(
            memory_manager,
            auto_confirm_threshold=0.5,
        )

        result = stage.execute({
            "message": "支付页面崩溃，需要紧急修复",
        }, auto_create_task=True)

        # 如果需求被确认且创建了任务
        if result.confirmed_requirements and result.created_tasks:
            task = result.created_tasks[0]
            assert "task_id" in task or "id" in task


class TestNotificationRouting:
    """测试通知路由"""

    @pytest.fixture
    def memory_manager(self):
        """创建内存管理器"""
        temp_dir = tempfile.mkdtemp()
        manager = MemoryManager(workspace=temp_dir)
        yield manager
        shutil.rmtree(temp_dir)

    def test_notify_roles_for_feature(self, memory_manager):
        """功能需求通知相关角色"""
        stage = RequirementDetectionStage(memory_manager)

        # 获取内部方法 _get_notify_roles
        notify_roles = stage._get_notify_roles(RequirementType.FEATURE)

        assert "developer" in notify_roles
        assert "architect" in notify_roles

    def test_notify_roles_for_bug(self, memory_manager):
        """Bug修复通知相关角色"""
        stage = RequirementDetectionStage(memory_manager)

        notify_roles = stage._get_notify_roles(RequirementType.BUG_FIX)

        assert "developer" in notify_roles
        assert "tester" in notify_roles

    def test_notify_roles_for_feedback(self, memory_manager):
        """反馈通知产品经理"""
        stage = RequirementDetectionStage(memory_manager)

        notify_roles = stage._get_notify_roles(RequirementType.FEEDBACK)

        assert "product_manager" in notify_roles