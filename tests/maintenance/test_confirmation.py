"""
Tests for Maintenance Module - Confirmation Manager

测试确认机制管理器的功能
"""

import pytest
import time

from harnessgenj.maintenance.confirmation import (
    ConfirmationManager,
    ConfirmationStatus,
    PendingConfirmation,
    create_confirmation_manager,
)


class TestConfirmationManager:
    """测试确认管理器"""

    def test_create_manager(self):
        """创建管理器"""
        manager = ConfirmationManager()
        assert manager is not None
        assert manager.auto_approve_threshold == 0.95

    def test_create_manager_with_params(self):
        """使用参数创建管理器"""
        manager = ConfirmationManager(
            auto_approve_threshold=0.9,
            expire_seconds=7200,
        )
        assert manager.auto_approve_threshold == 0.9
        assert manager.expire_seconds == 7200

    def test_add_pending_requirement(self):
        """添加待确认需求"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0001",
            "title": "购物车功能",
            "description": "实现购物车功能",
            "req_type": "feature",
            "confidence": 0.7,
        }

        pending = manager.add_pending(requirement)

        assert pending is not None
        assert pending.requirement_id == "REQ-0001"
        assert pending.title == "购物车功能"
        assert pending.status == ConfirmationStatus.PENDING

    def test_auto_approve_high_confidence(self):
        """高置信度自动批准"""
        manager = ConfirmationManager(auto_approve_threshold=0.9)

        requirement = {
            "req_id": "REQ-0002",
            "title": "Bug修复",
            "description": "修复登录问题",
            "req_type": "bug_fix",
            "confidence": 0.95,  # 高于阈值
        }

        pending = manager.add_pending(requirement)

        assert pending.status == ConfirmationStatus.AUTO_APPROVED

    def test_auto_reject_low_confidence(self):
        """低置信度自动拒绝"""
        manager = ConfirmationManager(auto_reject_threshold=0.3)

        requirement = {
            "req_id": "REQ-0003",
            "title": "模糊需求",
            "description": "不太确定的内容",
            "req_type": "feature",
            "confidence": 0.2,  # 低于阈值
        }

        pending = manager.add_pending(requirement)

        assert pending.status == ConfirmationStatus.REJECTED

    def test_generate_confirmation_prompt(self):
        """生成确认提示"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0004",
            "title": "新功能",
            "description": "实现用户管理功能",
            "req_type": "feature",
            "confidence": 0.8,
        }

        pending = manager.add_pending(requirement)
        prompt = manager.generate_confirmation_prompt(pending)

        assert prompt is not None
        assert "新功能" in prompt
        assert "80%" in prompt  # 置信度

    def test_process_approval_response(self):
        """处理批准响应"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0005",
            "title": "测试需求",
            "description": "测试描述",
            "req_type": "feature",
            "confidence": 0.7,
        }

        pending = manager.add_pending(requirement)
        confirmation_id = pending.confirmation_id

        # 处理批准
        result = manager.process_response(confirmation_id, "是")

        assert result is not None
        assert result.status == ConfirmationStatus.APPROVED
        assert result.user_response == "是"

    def test_process_rejection_response(self):
        """处理拒绝响应"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0006",
            "title": "测试需求",
            "description": "测试描述",
            "req_type": "feature",
            "confidence": 0.7,
        }

        pending = manager.add_pending(requirement)
        confirmation_id = pending.confirmation_id

        # 处理拒绝
        result = manager.process_response(confirmation_id, "否")

        assert result is not None
        assert result.status == ConfirmationStatus.REJECTED

    def test_process_modify_response(self):
        """处理修改响应"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0007",
            "title": "测试需求",
            "description": "测试描述",
            "req_type": "feature",
            "confidence": 0.7,
        }

        pending = manager.add_pending(requirement)
        confirmation_id = pending.confirmation_id

        # 处理修改
        result = manager.process_response(
            confirmation_id,
            "修改",
            modification="修改后的描述"
        )

        assert result is not None
        assert result.status == ConfirmationStatus.MODIFIED
        assert result.modification_notes == "修改后的描述"

    def test_get_pending(self):
        """获取待确认项"""
        manager = ConfirmationManager()

        requirement = {
            "req_id": "REQ-0008",
            "title": "测试需求",
            "description": "测试描述",
            "req_type": "feature",
            "confidence": 0.7,
        }

        pending = manager.add_pending(requirement)
        confirmation_id = pending.confirmation_id

        # 获取
        result = manager.get_pending(confirmation_id)
        assert result is not None
        assert result.requirement_id == "REQ-0008"

    def test_get_all_pending(self):
        """获取所有待确认项"""
        manager = ConfirmationManager()

        # 添加多个
        for i in range(3):
            requirement = {
                "req_id": f"REQ-{i:04d}",
                "title": f"需求{i}",
                "description": "描述",
                "req_type": "feature",
                "confidence": 0.6,  # 低置信度，不会被自动批准
            }
            manager.add_pending(requirement)

        pending_list = manager.get_all_pending()
        assert len(pending_list) == 3

    def test_get_approved(self):
        """获取已批准项"""
        manager = ConfirmationManager(auto_approve_threshold=0.9)

        # 添加一个高置信度的（自动批准）
        manager.add_pending({
            "req_id": "REQ-APPROVED",
            "title": "批准的需求",
            "description": "描述",
            "req_type": "feature",
            "confidence": 0.95,
        })

        # 添加一个低置信度的（待确认）
        manager.add_pending({
            "req_id": "REQ-PENDING",
            "title": "待确认需求",
            "description": "描述",
            "req_type": "feature",
            "confidence": 0.6,
        })

        approved = manager.get_approved()
        assert len(approved) == 1
        assert approved[0].requirement_id == "REQ-APPROVED"

    def test_batch_approve(self):
        """批量批准"""
        manager = ConfirmationManager()

        # 添加多个待确认项
        ids = []
        for i in range(3):
            pending = manager.add_pending({
                "req_id": f"REQ-BATCH-{i}",
                "title": f"批量需求{i}",
                "description": "描述",
                "req_type": "feature",
                "confidence": 0.6,
            })
            ids.append(pending.confirmation_id)

        # 批量批准
        results = manager.batch_approve(ids)
        assert len(results) == 3

        for r in results:
            assert r.status == ConfirmationStatus.APPROVED

    def test_batch_reject(self):
        """批量拒绝"""
        manager = ConfirmationManager()

        # 添加多个待确认项
        ids = []
        for i in range(3):
            pending = manager.add_pending({
                "req_id": f"REQ-REJECT-{i}",
                "title": f"批量拒绝{i}",
                "description": "描述",
                "req_type": "feature",
                "confidence": 0.6,
            })
            ids.append(pending.confirmation_id)

        # 批量拒绝
        results = manager.batch_reject(ids)
        assert len(results) == 3

        for r in results:
            assert r.status == ConfirmationStatus.REJECTED

    def test_clear_processed(self):
        """清理已处理的项"""
        manager = ConfirmationManager()

        # 添加并处理
        pending = manager.add_pending({
            "req_id": "REQ-CLEAR",
            "title": "清理测试",
            "description": "描述",
            "req_type": "feature",
            "confidence": 0.6,
        })

        manager.process_response(pending.confirmation_id, "是")

        # 清理
        count = manager.clear_processed()
        assert count == 1

    def test_get_stats(self):
        """获取统计"""
        manager = ConfirmationManager()

        # 添加不同状态的项
        manager.add_pending({
            "req_id": "REQ-STATS-1",
            "title": "待确认",
            "description": "描述",
            "req_type": "feature",
            "confidence": 0.6,
        })

        manager.add_pending({
            "req_id": "REQ-STATS-2",
            "title": "自动批准",
            "description": "描述",
            "req_type": "feature",
            "confidence": 0.98,
        })

        stats = manager.get_stats()

        assert "total" in stats
        assert "by_status" in stats
        assert stats["total"] >= 2


class TestPendingConfirmation:
    """测试待确认项"""

    def test_create_pending(self):
        """创建待确认项"""
        pending = PendingConfirmation(
            confirmation_id="CONF-0001",
            requirement_id="REQ-0001",
            title="测试需求",
            description="测试描述",
            req_type="feature",
            confidence=0.8,
        )

        assert pending.confirmation_id == "CONF-0001"
        assert pending.status == ConfirmationStatus.PENDING

    def test_is_expired(self):
        """检查过期"""
        pending = PendingConfirmation(
            confirmation_id="CONF-0002",
            requirement_id="REQ-0002",
            title="测试",
            description="描述",
            req_type="feature",
            confidence=0.8,
            expires_at=time.time() - 1,  # 已过期
        )

        assert pending.is_expired() is True

    def test_not_expired(self):
        """检查未过期"""
        pending = PendingConfirmation(
            confirmation_id="CONF-0003",
            requirement_id="REQ-0003",
            title="测试",
            description="描述",
            req_type="feature",
            confidence=0.8,
            expires_at=time.time() + 3600,  # 1小时后过期
        )

        assert pending.is_expired() is False

    def test_to_dict(self):
        """转换为字典"""
        pending = PendingConfirmation(
            confirmation_id="CONF-0004",
            requirement_id="REQ-0004",
            title="测试",
            description="描述",
            req_type="feature",
            confidence=0.8,
        )

        data = pending.to_dict()

        assert data["confirmation_id"] == "CONF-0004"
        assert data["requirement_id"] == "REQ-0004"


class TestConfirmationStatus:
    """测试确认状态枚举"""

    def test_all_statuses_exist(self):
        """所有状态都存在"""
        statuses = [
            ConfirmationStatus.PENDING,
            ConfirmationStatus.APPROVED,
            ConfirmationStatus.REJECTED,
            ConfirmationStatus.MODIFIED,
            ConfirmationStatus.TIMEOUT,
            ConfirmationStatus.AUTO_APPROVED,
        ]

        for s in statuses:
            assert s.value is not None


class TestConfirmationPrompts:
    """测试确认提示模板"""

    def test_feature_prompt(self):
        """功能需求提示"""
        manager = ConfirmationManager()

        pending = PendingConfirmation(
            confirmation_id="CONF-FEATURE",
            requirement_id="REQ-FEATURE",
            title="购物车功能",
            description="实现购物车功能",
            req_type="feature",
            confidence=0.8,
        )

        prompt = manager.generate_confirmation_prompt(pending)

        assert "功能需求" in prompt
        assert "购物车功能" in prompt

    def test_bug_fix_prompt(self):
        """Bug修复提示"""
        manager = ConfirmationManager()

        pending = PendingConfirmation(
            confirmation_id="CONF-BUG",
            requirement_id="REQ-BUG",
            title="支付问题",
            description="支付页面报错",
            req_type="bug_fix",
            confidence=0.85,
        )

        prompt = manager.generate_confirmation_prompt(pending)

        assert "Bug" in prompt or "问题" in prompt

    def test_improvement_prompt(self):
        """改进建议提示"""
        manager = ConfirmationManager()

        pending = PendingConfirmation(
            confirmation_id="CONF-IMPROVE",
            requirement_id="REQ-IMPROVE",
            title="性能优化",
            description="优化数据库查询",
            req_type="improvement",
            confidence=0.75,
        )

        prompt = manager.generate_confirmation_prompt(pending)

        assert "改进" in prompt or "优化" in prompt


class TestConfirmationManagerFactory:
    """测试工厂函数"""

    def test_create_confirmation_manager(self):
        """工厂函数创建"""
        manager = create_confirmation_manager(
            auto_approve_threshold=0.92,
            expire_seconds=1800,
        )

        assert manager is not None
        assert manager.auto_approve_threshold == 0.92
        assert manager.expire_seconds == 1800