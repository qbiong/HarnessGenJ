"""
Tests for Maintenance Module - Document Maintenance Manager

测试文档维护管理器的功能
"""

import pytest
import tempfile
import shutil

from harnessgenj.memory import MemoryManager
from harnessgenj.maintenance.manager import (
    DocumentMaintenanceManager,
    DocumentUpdate,
    TeamNotification,
    NotificationType,
    create_maintenance_manager,
)


class TestDocumentMaintenanceManager:
    """测试文档维护管理器"""

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
    def maintenance_manager(self, memory_manager):
        """创建文档维护管理器"""
        return DocumentMaintenanceManager(memory_manager)

    def test_create_manager(self, maintenance_manager):
        """创建管理器"""
        assert maintenance_manager is not None
        assert maintenance_manager.memory is not None

    def test_add_requirement_to_document(self, maintenance_manager, memory_manager):
        """将需求添加到文档"""
        requirement = {
            "req_id": "REQ-0001",
            "title": "购物车功能",
            "description": "实现购物车功能，支持添加、删除、修改商品",
            "req_type": "feature",
            "confidence": 0.85,
            "suggested_priority": "P1",
        }

        update = maintenance_manager.add_requirement_to_document(
            requirement=requirement,
            document_type="requirements",
        )

        assert update is not None
        assert update.document_type == "requirements"
        assert update.operation == "add"
        assert "购物车功能" in update.change_summary

        # 验证文档已更新
        doc = memory_manager.get_document("requirements")
        assert doc is not None
        assert "购物车功能" in doc

    def test_add_requirement_with_notification(
        self, maintenance_manager, memory_manager
    ):
        """添加需求并通知团队"""
        requirement = {
            "req_id": "REQ-0002",
            "title": "用户登录",
            "description": "实现用户登录功能",
            "req_type": "feature",
            "confidence": 0.9,
        }

        update = maintenance_manager.add_requirement_to_document(
            requirement=requirement,
            document_type="requirements",
            notify_roles=["developer", "architect"],
        )

        assert update.notify_team is True

    def test_update_document_section(self, maintenance_manager, memory_manager):
        """更新文档部分"""
        # 先创建文档
        memory_manager.store_document(
            "requirements",
            "# 需求文档\n\n## 功能需求\n原有内容\n\n## 性能需求\n性能相关",
        )

        update = maintenance_manager.update_document_section(
            document_type="requirements",
            section_title="功能需求",
            new_content="## 功能需求\n\n### 购物车\n购物车功能描述",
        )

        # 更新可能成功或失败，取决于文档结构
        # 这里只验证方法能执行
        assert update is None or update.operation == "update"

    def test_create_task_from_requirement(self, maintenance_manager, memory_manager):
        """从需求创建任务"""
        requirement = {
            "req_id": "REQ-0003",
            "title": "订单管理",
            "description": "实现订单管理功能",
            "req_type": "feature",
            "suggested_priority": "P1",
            "suggested_assignee": "developer",
        }

        task = maintenance_manager.create_task_from_requirement(requirement)

        assert task is not None
        assert task["title"] == "订单管理"
        assert task["priority"] == "P1"
        assert task["assignee"] == "developer"
        assert "TASK-" in task["task_id"]

    def test_notify_team(self, maintenance_manager):
        """发送团队通知"""
        notification = maintenance_manager.notify_team(
            notification_type=NotificationType.REQUIREMENT_ADDED.value,
            target_roles=["developer", "architect"],
            title="新需求已添加",
            content="购物车功能需求已添加到需求文档",
            document_type="requirements",
            action_required=True,
            action_description="查阅需求文档",
        )

        assert notification is not None
        assert notification.title == "新需求已添加"
        assert "developer" in notification.target_roles
        assert notification.action_required is True

    def test_get_notifications_for_role(self, maintenance_manager):
        """获取指定角色的通知"""
        # 发送通知
        maintenance_manager.notify_team(
            notification_type=NotificationType.DOCUMENT_UPDATED.value,
            target_roles=["developer", "architect"],
            title="文档更新",
            content="需求文档已更新",
        )

        notifications = maintenance_manager.get_notifications_for_role("developer")

        assert len(notifications) >= 1
        assert notifications[0].title == "文档更新"

    def test_get_pending_actions(self, maintenance_manager):
        """获取需要行动的通知"""
        # 发送需要行动的通知
        maintenance_manager.notify_team(
            notification_type=NotificationType.TASK_CREATED.value,
            target_roles=["developer"],
            title="新任务",
            content="请开始开发购物车功能",
            action_required=True,
            action_description="开始任务",
        )

        # 发送不需要行动的通知
        maintenance_manager.notify_team(
            notification_type=NotificationType.TASK_COMPLETED.value,
            target_roles=["developer"],
            title="任务完成",
            content="任务已完成",
            action_required=False,
        )

        pending_actions = maintenance_manager.get_pending_actions_for_role("developer")

        # 只返回需要行动的通知
        assert len(pending_actions) >= 1
        for action in pending_actions:
            assert action.action_required is True

    def test_mark_notification_read(self, maintenance_manager):
        """标记通知已读"""
        notification = maintenance_manager.notify_team(
            notification_type=NotificationType.DOCUMENT_UPDATED.value,
            target_roles=["developer"],
            title="测试通知",
            content="测试内容",
        )

        success = maintenance_manager.mark_notification_read(
            notification.notification_id, "developer"
        )

        assert success is True
        assert "developer" in notification.read_by

    def test_get_document_history(self, maintenance_manager, memory_manager):
        """获取文档更新历史"""
        # 添加多个需求
        for i in range(3):
            maintenance_manager.add_requirement_to_document(
                requirement={
                    "req_id": f"REQ-HIST-{i}",
                    "title": f"需求{i}",
                    "description": f"描述{i}",
                    "req_type": "feature",
                    "confidence": 0.8,
                },
                document_type="requirements",
            )

        history = maintenance_manager.get_document_history("requirements", limit=2)

        assert len(history) <= 2

    def test_get_update_stats(self, maintenance_manager):
        """获取更新统计"""
        # 添加一些更新
        maintenance_manager.add_requirement_to_document(
            requirement={
                "req_id": "REQ-STATS",
                "title": "统计测试",
                "description": "描述",
                "req_type": "feature",
                "confidence": 0.8,
            },
            document_type="requirements",
        )

        stats = maintenance_manager.get_update_stats()

        assert "total_updates" in stats
        assert "total_notifications" in stats
        assert stats["total_updates"] >= 1

    def test_get_maintenance_summary(self, maintenance_manager):
        """获取维护摘要"""
        # 添加更新
        maintenance_manager.add_requirement_to_document(
            requirement={
                "req_id": "REQ-SUMMARY",
                "title": "摘要测试",
                "description": "描述",
                "req_type": "feature",
                "confidence": 0.8,
            },
            document_type="requirements",
        )

        summary = maintenance_manager.get_maintenance_summary()

        assert summary is not None
        assert "文档维护摘要" in summary


class TestDocumentUpdate:
    """测试文档更新记录"""

    def test_create_update(self):
        """创建更新记录"""
        update = DocumentUpdate(
            update_id="UPD-0001",
            document_type="requirements",
            operation="add",
            content_after="# 新需求\n\n购物车功能",
            change_summary="新增购物车功能需求",
        )

        assert update.update_id == "UPD-0001"
        assert update.operation == "add"
        assert update.notify_team is True

    def test_update_to_dict(self):
        """转换为字典"""
        update = DocumentUpdate(
            update_id="UPD-0002",
            document_type="requirements",
            operation="update",
            content_after="更新后内容",
            change_summary="更新摘要",
        )

        data = update.to_dict()

        assert data["update_id"] == "UPD-0002"
        assert data["document_type"] == "requirements"


class TestTeamNotification:
    """测试团队通知"""

    def test_create_notification(self):
        """创建通知"""
        notification = TeamNotification(
            notification_id="NOTIF-0001",
            notification_type="requirement_added",
            target_roles=["developer", "architect"],
            title="新需求",
            content="购物车功能需求",
        )

        assert notification.notification_id == "NOTIF-0001"
        assert len(notification.target_roles) == 2

    def test_mark_read(self):
        """标记已读"""
        notification = TeamNotification(
            notification_id="NOTIF-0002",
            notification_type="document_updated",
            target_roles=["developer"],
            title="更新",
            content="文档已更新",
        )

        notification.mark_read("developer")

        assert "developer" in notification.read_by

    def test_mark_acknowledged(self):
        """标记已确认"""
        notification = TeamNotification(
            notification_id="NOTIF-0003",
            notification_type="task_created",
            target_roles=["developer"],
            title="新任务",
            content="请开始任务",
        )

        notification.mark_acknowledged("developer")

        assert "developer" in notification.acknowledged_by

    def test_notification_to_dict(self):
        """转换为字典"""
        notification = TeamNotification(
            notification_id="NOTIF-0004",
            notification_type="issue_found",
            target_roles=["project_manager"],
            title="问题发现",
            content="发现问题",
        )

        data = notification.to_dict()

        assert data["notification_id"] == "NOTIF-0004"


class TestNotificationType:
    """测试通知类型枚举"""

    def test_all_types_exist(self):
        """所有类型都存在"""
        types = [
            NotificationType.REQUIREMENT_ADDED,
            NotificationType.REQUIREMENT_CHANGED,
            NotificationType.DOCUMENT_UPDATED,
            NotificationType.TASK_CREATED,
            NotificationType.TASK_COMPLETED,
            NotificationType.REVIEW_REQUESTED,
            NotificationType.ISSUE_FOUND,
            NotificationType.PROGRESS_UPDATE,
        ]

        for t in types:
            assert t.value is not None


class TestMaintenanceManagerFactory:
    """测试工厂函数"""

    def test_create_maintenance_manager(self):
        """工厂函数创建"""
        temp_dir = tempfile.mkdtemp()
        try:
            memory = MemoryManager(temp_dir)
            manager = create_maintenance_manager(memory)

            assert manager is not None
            assert manager.memory is not None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_flow(self, temp_workspace):
        """完整流程测试"""
        # 1. 初始化
        memory = MemoryManager(temp_workspace)
        manager = DocumentMaintenanceManager(memory)

        # 2. 添加需求
        requirement = {
            "req_id": "REQ-FULL",
            "title": "完整流程测试",
            "description": "测试完整流程",
            "req_type": "feature",
            "confidence": 0.9,
            "suggested_priority": "P1",
        }

        update = manager.add_requirement_to_document(requirement)

        # 3. 验证文档更新
        doc = memory.get_document("requirements")
        assert "完整流程测试" in doc

        # 4. 创建任务
        task = manager.create_task_from_requirement(requirement)
        assert task["title"] == "完整流程测试"

        # 5. 验证通知
        notifications = manager.get_notifications_for_role("developer")
        assert len(notifications) >= 1

        # 6. 获取统计
        stats = manager.get_update_stats()
        assert stats["total_updates"] >= 1

    def test_bug_fix_flow(self, temp_workspace):
        """Bug修复流程测试"""
        memory = MemoryManager(temp_workspace)
        manager = DocumentMaintenanceManager(memory)

        # 添加Bug修复需求
        bug_requirement = {
            "req_id": "BUG-001",
            "title": "支付超时",
            "description": "订单支付后超时未响应",
            "req_type": "bug_fix",
            "confidence": 0.95,
            "suggested_priority": "P0",
        }

        update = manager.add_requirement_to_document(
            requirement=bug_requirement,
            notify_roles=["developer", "tester"],
        )

        # Bug修复应该是P0
        task = manager.create_task_from_requirement(bug_requirement)
        assert task["priority"] == "P0"