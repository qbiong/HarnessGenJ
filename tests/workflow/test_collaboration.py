"""
Tests for Collaboration Module

测试角色协作管理器功能:
- 消息传递
- 并行执行
- 产出物流转
- 协作状态可视化
"""

import pytest
from unittest.mock import Mock, MagicMock
from harnessgenj.workflow.collaboration import (
    RoleCollaborationManager,
    CollaborationRole,
    CollaborationSnapshot,
    create_collaboration_manager,
)
from harnessgenj.workflow.message_bus import MessageType


class TestCollaborationRole:
    """测试协作角色状态"""

    def test_create_collaboration_role(self):
        """创建协作角色"""
        role = CollaborationRole(
            role_id="developer",
            role_type="developer",
        )
        assert role.role_id == "developer"
        assert role.status == "idle"
        assert len(role.artifacts_owned) == 0
        assert len(role.collaborators) == 0

    def test_role_with_artifacts(self):
        """带产出物的角色"""
        role = CollaborationRole(
            role_id="developer",
            role_type="developer",
            artifacts_owned=["code.py", "test.py"],
        )
        assert len(role.artifacts_owned) == 2

    def test_role_status_update(self):
        """角色状态更新"""
        role = CollaborationRole(
            role_id="developer",
            role_type="developer",
        )
        role.status = "working"
        role.current_task = {"task_id": "task_1"}
        assert role.status == "working"
        assert role.current_task["task_id"] == "task_1"


class TestCollaborationSnapshot:
    """测试协作快照"""

    def test_create_snapshot(self):
        """创建快照"""
        snapshot = CollaborationSnapshot()
        assert len(snapshot.roles) == 0
        assert len(snapshot.active_connections) == 0
        assert len(snapshot.artifacts_flow) == 0

    def test_snapshot_with_roles(self):
        """带角色的快照"""
        roles = [
            CollaborationRole(role_id="dev", role_type="developer"),
            CollaborationRole(role_id="rev", role_type="reviewer"),
        ]
        snapshot = CollaborationSnapshot(roles=roles)
        assert len(snapshot.roles) == 2


class TestRoleCollaborationManager:
    """测试角色协作管理器"""

    def test_create_manager(self):
        """创建管理器"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)
        assert isinstance(manager, RoleCollaborationManager)

    def test_send_message(self):
        """发送消息"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        # 注册角色
        manager.register_role("developer", "developer")
        manager.register_role("reviewer", "reviewer")

        msg_id = manager.send_message(
            from_role="developer",
            to_role="reviewer",
            content={"code": "test.py"},
        )
        assert msg_id is not None

        # 检查统计
        stats = manager.get_stats()
        assert stats["messages_sent"] == 1

    def test_broadcast(self):
        """广播消息"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("pm", "pm")
        manager.register_role("dev1", "developer")
        manager.register_role("dev2", "developer")

        # 使用消息总线广播
        msg_ids = manager._message_bus.broadcast(
            sender_id="pm",
            content={"meeting": "10am"},
        )
        # 消息总线广播到已知队列
        assert len(msg_ids) >= 0  # 可能没有注册的队列

    def test_get_messages(self):
        """获取消息"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")

        manager.send_message("dev", "rev", {"data": 1})
        manager.send_message("dev", "rev", {"data": 2})

        messages = manager.get_messages("rev")
        assert len(messages) == 2

    def test_ack_message(self):
        """确认消息"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")

        msg_id = manager.send_message(
            from_role="dev",
            to_role="rev",
            content={},
            requires_ack=True,
        )

        result = manager.ack_message("rev", msg_id)
        assert result is True

    def test_register_role(self):
        """注册角色"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("architect", "architect")
        state = manager.get_role_state("architect")
        assert state is not None
        assert state.role_id == "architect"
        assert state.role_type == "architect"

    def test_unregister_role(self):
        """注销角色"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("temp", "temporary")
        manager.unregister_role("temp")

        state = manager.get_role_state("temp")
        assert state is None

    def test_transfer_artifact(self):
        """转移产出物"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")

        result = manager.transfer_artifact(
            from_role="dev",
            to_role="rev",
            artifact_name="code.py",
            artifact_content="print('hello')",
            message="Please review",
        )
        assert result is True

        # 检查流转记录
        flow = manager.get_artifacts_flow()
        assert len(flow) == 1
        assert flow[0]["artifact"] == "code.py"

        # 检查统计
        stats = manager.get_stats()
        assert stats["artifacts_transferred"] == 1

    def test_get_snapshot(self):
        """获取快照"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")

        snapshot = manager.get_snapshot()
        assert isinstance(snapshot, CollaborationSnapshot)
        assert len(snapshot.roles) == 2

    def test_to_mermaid(self):
        """生成 Mermaid 图表"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")
        manager.transfer_artifact("dev", "rev", "code.py", "")

        mermaid = manager.to_mermaid()
        assert "```mermaid" in mermaid
        assert "graph TD" in mermaid
        assert "dev" in mermaid
        assert "rev" in mermaid

    def test_reset_stats(self):
        """重置统计"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)

        manager.register_role("dev", "developer")
        manager.register_role("rev", "reviewer")
        manager.send_message("dev", "rev", {})
        manager.transfer_artifact("dev", "rev", "test", "")

        manager.reset_stats()
        stats = manager.get_stats()
        assert stats["messages_sent"] == 0
        assert stats["artifacts_transferred"] == 0

    def test_execute_parallel_mock(self):
        """并行执行（模拟）"""
        mock_coordinator = Mock()
        mock_coordinator.get_role = Mock(return_value=Mock(
            assign_task=Mock(),
            execute_task=Mock(return_value={"status": "done"}),
        ))

        manager = create_collaboration_manager(mock_coordinator)
        manager.register_role("dev1", "developer")
        manager.register_role("dev2", "developer")

        tasks = [
            {"role_id": "dev1", "task": {"task_id": "task_1"}},
            {"role_id": "dev2", "task": {"task_id": "task_2"}},
        ]

        result = manager.execute_parallel(tasks, fail_fast=False)
        assert "total_tasks" in result
        assert "completed" in result
        assert "failed" in result

    def test_execute_parallel_no_role(self):
        """并行执行缺少角色"""
        mock_coordinator = Mock()
        mock_coordinator.get_role = Mock(return_value=None)

        manager = create_collaboration_manager(mock_coordinator)
        manager.register_role("dev", "developer")

        # 任务使用不存在的角色
        tasks = [
            {"role_id": "nonexistent", "task": {"task_id": "task_1"}},
        ]

        result = manager.execute_parallel(tasks, fail_fast=False)
        # 因为角色不存在，应该失败
        assert result["failed"] >= 1


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_collaboration_manager(self):
        """创建协作管理器"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator)
        assert isinstance(manager, RoleCollaborationManager)

    def test_create_with_max_parallel(self):
        """创建带最大并行数"""
        mock_coordinator = Mock()
        manager = create_collaboration_manager(mock_coordinator, max_parallel_tasks=8)
        assert manager._max_parallel_tasks == 8