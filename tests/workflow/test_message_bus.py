"""
Tests for Message Bus Module

测试消息总线功能:
- 消息发送和接收
- 消息类型和优先级
- 广播功能
- 消息确认
- 队列管理
"""

import pytest
from harnessgenj.workflow.message_bus import (
    MessageBus,
    RoleMessage,
    MessageType,
    MessagePriority,
    MessageStatus,
    create_message_bus,
)


class TestRoleMessage:
    """测试角色消息"""

    def test_create_message(self):
        """创建消息"""
        msg = RoleMessage(
            sender_id="developer",
            receiver_id="reviewer",
            content={"code": "test.py"},
        )
        assert msg.sender_id == "developer"
        assert msg.receiver_id == "reviewer"
        assert msg.message_type == MessageType.NOTIFICATION
        assert msg.status == MessageStatus.PENDING
        assert msg.priority == 5

    def test_message_with_type(self):
        """带类型的消息"""
        msg = RoleMessage(
            sender_id="developer",
            receiver_id="reviewer",
            content={"type": "code_review"},
            message_type=MessageType.REQUEST,
        )
        assert msg.message_type == MessageType.REQUEST

    def test_message_with_priority(self):
        """带优先级的消息"""
        msg = RoleMessage(
            sender_id="pm",
            receiver_id="dev_team",
            content={"urgent": True},
            priority=1,
        )
        assert msg.priority == 1

    def test_message_types(self):
        """消息类型枚举"""
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.NOTIFICATION.value == "notification"
        assert MessageType.ARTIFACT.value == "artifact"
        assert MessageType.COMMAND.value == "command"

    def test_message_priority_levels(self):
        """消息优先级枚举"""
        assert MessagePriority.LOW.value == 0
        assert MessagePriority.NORMAL.value == 5
        assert MessagePriority.HIGH.value == 8
        assert MessagePriority.URGENT.value == 10

    def test_message_ack(self):
        """消息确认"""
        msg = RoleMessage(
            sender_id="dev",
            receiver_id="rev",
            content={},
            requires_ack=True,
        )
        assert msg.requires_ack is True
        assert msg.status == MessageStatus.PENDING

        # 确认消息
        msg.status = MessageStatus.ACKNOWLEDGED
        assert msg.status == MessageStatus.ACKNOWLEDGED

    def test_message_is_expired(self):
        """消息过期检查"""
        import time
        msg = RoleMessage(
            sender_id="dev",
            receiver_id="rev",
            content={},
            expires_at=time.time() - 1,  # 已过期
        )
        assert msg.is_expired() is True

        msg2 = RoleMessage(
            sender_id="dev",
            receiver_id="rev",
            content={},
        )
        assert msg2.is_expired() is False

    def test_message_is_broadcast(self):
        """广播消息检查"""
        msg = RoleMessage(
            sender_id="dev",
            receiver_id=None,  # 广播
            content={},
        )
        assert msg.is_broadcast() is True

        msg2 = RoleMessage(
            sender_id="dev",
            receiver_id="rev",
            content={},
        )
        assert msg2.is_broadcast() is False


class TestMessageBus:
    """测试消息总线"""

    def test_create_bus(self):
        """创建消息总线"""
        bus = create_message_bus()
        assert isinstance(bus, MessageBus)

    def test_send_message(self):
        """发送消息"""
        bus = create_message_bus()
        msg_id = bus.send(
            sender_id="developer",
            receiver_id="reviewer",
            content={"code": "test.py"},
        )
        assert msg_id is not None
        assert len(bus._queues["reviewer"]) == 1

    def test_get_messages(self):
        """获取消息"""
        bus = create_message_bus()
        bus.send("dev1", "dev2", {"data": 1})
        bus.send("dev1", "dev2", {"data": 2})
        bus.send("dev3", "dev2", {"data": 3})

        messages = bus.get_messages("dev2")
        assert len(messages) == 3

    def test_get_messages_limit(self):
        """获取消息限制数量"""
        bus = create_message_bus()
        for i in range(10):
            bus.send("sender", "receiver", {"idx": i})

        messages = bus.get_messages("receiver", limit=5)
        assert len(messages) == 5

    def test_broadcast(self):
        """广播消息"""
        bus = create_message_bus()
        # 预先注册一些接收者队列
        bus._queues["dev1"] = []
        bus._queues["dev2"] = []
        bus._queues["dev3"] = []

        msg_ids = bus.broadcast(
            sender_id="pm",
            content={"meeting": "10am"},
        )
        # 广播应该发送给所有人
        assert len(msg_ids) >= 1

    def test_broadcast_with_exclude(self):
        """广播排除特定接收者"""
        bus = create_message_bus()
        bus._queues["dev1"] = []
        bus._queues["dev2"] = []
        bus._queues["dev3"] = []

        msg_ids = bus.broadcast(
            sender_id="pm",
            content={"note": "test"},
            exclude=["dev1"],
        )
        assert len(msg_ids) >= 1

    def test_ack_message(self):
        """确认消息"""
        bus = create_message_bus()
        msg_id = bus.send(
            sender_id="dev",
            receiver_id="rev",
            content={},
            requires_ack=True,
        )

        result = bus.ack_message("rev", msg_id)
        assert result is True

    def test_ack_nonexistent_message(self):
        """确认不存在消息"""
        bus = create_message_bus()
        result = bus.ack_message("receiver", "nonexistent_id")
        assert result is False

    def test_ack_all(self):
        """确认所有消息"""
        bus = create_message_bus()
        bus.send("dev", "rev", {"data": 1})
        bus.send("dev", "rev", {"data": 2})

        count = bus.ack_all("rev")
        assert count == 2

    def test_clear_queue(self):
        """清空队列"""
        bus = create_message_bus()
        bus.send("s1", "r1", {"data": 1})
        bus.send("s2", "r1", {"data": 2})

        bus.clear_queue("r1")
        messages = bus.get_messages("r1")
        assert len(messages) == 0

    def test_get_stats(self):
        """获取统计"""
        bus = create_message_bus()
        bus.send("s1", "r1", {})
        bus.send("s2", "r2", {})
        bus.send("s3", "r1", {})

        stats = bus.get_stats()
        assert stats["total_sent"] == 3
        assert stats["total_roles"] >= 2

    def test_reset_stats(self):
        """重置统计"""
        bus = create_message_bus()
        bus.send("s", "r", {})
        bus.reset_stats()

        stats = bus.get_stats()
        assert stats["total_sent"] == 0

    def test_message_order_by_priority(self):
        """消息按优先级排序"""
        bus = create_message_bus()
        bus.send("s", "r", {"data": "low"}, priority=0)
        bus.send("s", "r", {"data": "high"}, priority=10)
        bus.send("s", "r", {"data": "normal"}, priority=5)

        messages = bus.get_messages("r")
        # 高优先级应该在前
        priorities = [m.priority for m in messages]
        assert priorities[0] == 10  # 最高优先级在前

    def test_subscribe(self):
        """订阅消息"""
        bus = create_message_bus()
        received = []

        def callback(msg):
            received.append(msg)

        sub_id = bus.subscribe("dev", [MessageType.REQUEST], callback)
        assert sub_id is not None

    def test_unsubscribe(self):
        """取消订阅"""
        bus = create_message_bus()
        bus.subscribe("dev", [MessageType.REQUEST])
        count = bus.unsubscribe("dev")
        assert count >= 1

    def test_get_unread_count(self):
        """获取未读消息数量"""
        bus = create_message_bus()
        bus.send("s", "r", {})
        bus.send("s", "r", {})

        count = bus.get_unread_count("r")
        assert count == 2

    def test_peek_latest(self):
        """查看最新消息"""
        bus = create_message_bus()
        bus.send("s", "r", {"data": 1})
        bus.send("s", "r", {"data": 2})

        msg = bus.peek_latest("r")
        assert msg is not None
        assert msg.content["data"] == 2

    def test_clear_expired(self):
        """清理过期消息"""
        import time
        bus = create_message_bus()
        bus.send("s", "r", {"data": 1}, expires_in=-1)  # 已过期
        bus.send("s", "r", {"data": 2})

        count = bus.clear_expired()
        assert count >= 1


class TestMessageType:
    """测试消息类型"""

    def test_request_type(self):
        """请求类型"""
        assert MessageType.REQUEST.value == "request"

    def test_response_type(self):
        """响应类型"""
        assert MessageType.RESPONSE.value == "response"

    def test_notification_type(self):
        """通知类型"""
        assert MessageType.NOTIFICATION.value == "notification"

    def test_artifact_type(self):
        """产出物类型"""
        assert MessageType.ARTIFACT.value == "artifact"

    def test_command_type(self):
        """命令类型"""
        assert MessageType.COMMAND.value == "command"


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_message_bus(self):
        """创建消息总线"""
        bus = create_message_bus()
        assert isinstance(bus, MessageBus)

    def test_create_with_max_size(self):
        """创建带最大队列大小"""
        bus = create_message_bus(max_queue_size=500)
        assert bus._max_queue_size == 500