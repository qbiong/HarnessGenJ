"""
Message Bus - 角色间消息传递通道

提供异步、优先级、广播消息传递能力：
- 点对点消息
- 广播消息
- 消息订阅
- 消息确认

使用示例:
    from harnessgenj.workflow.message_bus import MessageBus, RoleMessage

    bus = MessageBus()

    # 发送消息
    msg_id = bus.send("developer", "reviewer", {"type": "code_review", "code": "..."})

    # 广播消息
    bus.broadcast("pm", {"type": "meeting", "time": "10:00"})

    # 接收消息
    messages = bus.get_messages("reviewer")
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid
from collections import defaultdict
import threading


class MessageType(Enum):
    """消息类型"""

    REQUEST = "request"           # 请求消息
    RESPONSE = "response"         # 响应消息
    NOTIFICATION = "notification" # 通知消息
    ARTIFACT = "artifact"         # 产出物消息
    COMMAND = "command"           # 命令消息


class MessagePriority(Enum):
    """消息优先级"""

    LOW = 0
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class MessageStatus(Enum):
    """消息状态"""

    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"


class RoleMessage(BaseModel):
    """角色消息"""

    message_id: str = Field(default_factory=lambda: f"MSG-{uuid.uuid4().hex[:8]}")
    sender_id: str = Field(..., description="发送者角色ID")
    receiver_id: str | None = Field(default=None, description="接收者角色ID（None表示广播）")
    message_type: MessageType = Field(default=MessageType.NOTIFICATION, description="消息类型")
    priority: int = Field(default=5, description="优先级 0-10")
    content: dict[str, Any] = Field(default_factory=dict, description="消息内容")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    expires_at: float | None = Field(default=None, description="过期时间")
    requires_ack: bool = Field(default=False, description="是否需要确认")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="消息状态")
    correlation_id: str | None = Field(default=None, description="关联消息ID（用于请求-响应）")

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_broadcast(self) -> bool:
        """检查是否是广播消息"""
        return self.receiver_id is None


class MessageSubscription(BaseModel):
    """消息订阅"""

    subscriber_id: str
    message_types: list[MessageType]
    callback: Callable[[RoleMessage], None] | None = None
    active: bool = True


class MessageBus:
    """
    消息传递通道

    支持:
    1. 点对点消息
    2. 广播消息
    3. 消息订阅
    4. 消息确认
    5. 过期清理
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        """
        初始化消息通道

        Args:
            max_queue_size: 每个角色最大消息队列大小
        """
        self._queues: dict[str, list[RoleMessage]] = defaultdict(list)
        self._subscriptions: dict[str, list[MessageSubscription]] = defaultdict(list)
        self._max_queue_size = max_queue_size
        self._lock = threading.Lock()
        self._stats = {
            "total_sent": 0,
            "total_broadcasts": 0,
            "total_expired": 0,
            "total_acked": 0,
        }

    # ==================== 消息发送 ====================

    def send(
        self,
        sender_id: str,
        receiver_id: str,
        content: dict[str, Any],
        *,
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: int = 5,
        requires_ack: bool = False,
        expires_in: float | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """
        发送点对点消息

        Args:
            sender_id: 发送者角色ID
            receiver_id: 接收者角色ID
            content: 消息内容
            message_type: 消息类型
            priority: 优先级 (0-10)
            requires_ack: 是否需要确认
            expires_in: 过期时间（秒）
            correlation_id: 关联消息ID

        Returns:
            消息ID
        """
        with self._lock:
            expires_at = time.time() + expires_in if expires_in else None

            message = RoleMessage(
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                priority=priority,
                content=content,
                expires_at=expires_at,
                requires_ack=requires_ack,
                correlation_id=correlation_id,
            )

            # 添加到接收者队列
            queue = self._queues[receiver_id]
            if len(queue) >= self._max_queue_size:
                # 移除最旧的消息
                queue.pop(0)
            queue.append(message)

            # 按优先级排序（高优先级在前）
            queue.sort(key=lambda m: m.priority, reverse=True)

            self._stats["total_sent"] += 1

            # 触发订阅回调
            self._trigger_callbacks(receiver_id, message)

            return message.message_id

    def broadcast(
        self,
        sender_id: str,
        content: dict[str, Any],
        *,
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: int = 5,
        exclude: list[str] | None = None,
    ) -> list[str]:
        """
        广播消息到所有角色

        Args:
            sender_id: 发送者角色ID
            content: 消息内容
            message_type: 消息类型
            priority: 优先级
            exclude: 排除的角色ID列表

        Returns:
            消息ID列表
        """
        with self._lock:
            message_ids = []
            exclude = exclude or []

            # 获取所有已知角色
            all_roles = set(self._queues.keys()) | set(
                sub_id for subs in self._subscriptions.values()
                for sub in subs
                for sub_id in [sub.subscriber_id]
            )

            for role_id in all_roles:
                if role_id in exclude or role_id == sender_id:
                    continue

                message = RoleMessage(
                    sender_id=sender_id,
                    receiver_id=role_id,
                    message_type=message_type,
                    priority=priority,
                    content=content,
                )

                queue = self._queues[role_id]
                if len(queue) >= self._max_queue_size:
                    queue.pop(0)
                queue.append(message)
                queue.sort(key=lambda m: m.priority, reverse=True)

                message_ids.append(message.message_id)
                self._trigger_callbacks(role_id, message)

            self._stats["total_broadcasts"] += 1
            return message_ids

    # ==================== 消息接收 ====================

    def get_messages(
        self,
        receiver_id: str,
        *,
        priority_threshold: int = 0,
        message_types: list[MessageType] | None = None,
        limit: int = 100,
    ) -> list[RoleMessage]:
        """
        获取角色的消息

        Args:
            receiver_id: 接收者角色ID
            priority_threshold: 优先级阈值（只返回高于此值的消息）
            message_types: 消息类型过滤
            limit: 最大返回数量

        Returns:
            消息列表
        """
        with self._lock:
            queue = self._queues.get(receiver_id, [])

            # 过滤过期消息
            valid_messages = [m for m in queue if not m.is_expired()]

            # 清理过期消息
            expired_count = len(queue) - len(valid_messages)
            if expired_count > 0:
                self._queues[receiver_id] = valid_messages
                self._stats["total_expired"] += expired_count

            # 应用过滤条件
            filtered = []
            for msg in valid_messages:
                if msg.priority < priority_threshold:
                    continue
                if message_types and msg.message_type not in message_types:
                    continue
                filtered.append(msg)

            # 标记为已读
            for msg in filtered[:limit]:
                msg.status = MessageStatus.READ

            return filtered[:limit]

    def get_unread_count(self, receiver_id: str) -> int:
        """获取未读消息数量"""
        with self._lock:
            queue = self._queues.get(receiver_id, [])
            return sum(1 for m in queue if m.status == MessageStatus.PENDING)

    def peek_latest(self, receiver_id: str) -> RoleMessage | None:
        """查看最新消息（不标记已读）"""
        with self._lock:
            queue = self._queues.get(receiver_id, [])
            for msg in reversed(queue):
                if not msg.is_expired():
                    return msg
            return None

    # ==================== 消息确认 ====================

    def ack_message(self, receiver_id: str, message_id: str) -> bool:
        """
        确认消息

        Args:
            receiver_id: 接收者角色ID
            message_id: 消息ID

        Returns:
            是否确认成功
        """
        with self._lock:
            queue = self._queues.get(receiver_id, [])
            for msg in queue:
                if msg.message_id == message_id:
                    msg.status = MessageStatus.ACKNOWLEDGED
                    self._stats["total_acked"] += 1
                    return True
            return False

    def ack_all(self, receiver_id: str) -> int:
        """确认所有消息"""
        with self._lock:
            queue = self._queues.get(receiver_id, [])
            count = 0
            for msg in queue:
                if msg.status != MessageStatus.ACKNOWLEDGED:
                    msg.status = MessageStatus.ACKNOWLEDGED
                    count += 1
            self._stats["total_acked"] += count
            return count

    # ==================== 订阅机制 ====================

    def subscribe(
        self,
        subscriber_id: str,
        message_types: list[MessageType],
        callback: Callable[[RoleMessage], None] | None = None,
    ) -> str:
        """
        订阅特定类型消息

        Args:
            subscriber_id: 订阅者角色ID
            message_types: 感兴趣的消息类型
            callback: 回调函数

        Returns:
            订阅ID
        """
        with self._lock:
            subscription = MessageSubscription(
                subscriber_id=subscriber_id,
                message_types=message_types,
                callback=callback,
            )
            self._subscriptions[subscriber_id].append(subscription)
            return f"SUB-{uuid.uuid4().hex[:8]}"

    def unsubscribe(self, subscriber_id: str) -> int:
        """取消订阅"""
        with self._lock:
            count = len(self._subscriptions.get(subscriber_id, []))
            self._subscriptions.pop(subscriber_id, None)
            return count

    def _trigger_callbacks(self, receiver_id: str, message: RoleMessage) -> None:
        """触发订阅回调"""
        subscriptions = self._subscriptions.get(receiver_id, [])
        for sub in subscriptions:
            if not sub.active:
                continue
            if message.message_type in sub.message_types:
                if sub.callback:
                    try:
                        sub.callback(message)
                    except Exception:
                        pass

    # ==================== 管理 ====================

    def clear_queue(self, receiver_id: str) -> int:
        """清空角色消息队列"""
        with self._lock:
            count = len(self._queues.get(receiver_id, []))
            self._queues.pop(receiver_id, None)
            return count

    def clear_expired(self) -> int:
        """清理所有过期消息"""
        with self._lock:
            total = 0
            for role_id, queue in list(self._queues.items()):
                original_len = len(queue)
                self._queues[role_id] = [m for m in queue if not m.is_expired()]
                total += original_len - len(self._queues[role_id])
            self._stats["total_expired"] += total
            return total

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            queue_sizes = {role: len(queue) for role, queue in self._queues.items()}
            return {
                **self._stats,
                "queue_sizes": queue_sizes,
                "total_roles": len(self._queues),
                "total_subscriptions": sum(len(subs) for subs in self._subscriptions.values()),
            }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_sent": 0,
            "total_broadcasts": 0,
            "total_expired": 0,
            "total_acked": 0,
        }


# ==================== 便捷函数 ====================

def create_message_bus(max_queue_size: int = 1000) -> MessageBus:
    """创建消息通道实例"""
    return MessageBus(max_queue_size)