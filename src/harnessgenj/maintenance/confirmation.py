"""
Confirmation Manager - 确认机制管理器

在将检测到的需求添加到文档前，先询问用户确认。
支持：
- 待确认队列管理
- 多种确认方式（单个确认、批量确认、自动确认）
- 确认状态追踪
- 确认超时处理
"""

import time
import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ConfirmationStatus(str, Enum):
    """确认状态"""

    PENDING = "pending"  # 待确认
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    MODIFIED = "modified"  # 已修改（用户提供修改意见）
    TIMEOUT = "timeout"  # 确认超时
    AUTO_APPROVED = "auto_approved"  # 自动批准（高置信度）


class PendingConfirmation(BaseModel):
    """待确认项"""

    confirmation_id: str = Field(..., description="确认ID")
    requirement_id: str = Field(..., description="需求ID")
    title: str = Field(..., description="需求标题")
    description: str = Field(..., description="需求描述")
    req_type: str = Field(..., description="需求类型")
    suggested_action: str = Field(default="添加到需求文档", description="建议操作")
    confidence: float = Field(..., description="置信度")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    expires_at: float | None = Field(default=None, description="过期时间")
    status: ConfirmationStatus = Field(default=ConfirmationStatus.PENDING, description="状态")
    user_response: str | None = Field(default=None, description="用户回复")
    modification_notes: str | None = Field(default=None, description="修改说明")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    original_message: str | None = Field(default=None, description="原始消息")

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class ConfirmationManager:
    """
    确认机制管理器

    管理待确认的需求，在添加到文档前询问用户确认。

    使用示例:
        manager = ConfirmationManager(auto_approve_threshold=0.9)

        # 添加待确认需求
        pending = manager.add_pending(requirement)

        # 高置信度需求会自动批准
        if pending.status == ConfirmationStatus.AUTO_APPROVED:
            # 直接添加到文档
        else:
            # 生成确认提示
            prompt = manager.generate_confirmation_prompt(pending)

        # 处理用户响应
        result = manager.process_response(pending.confirmation_id, "yes")
    """

    # 默认过期时间（秒）
    DEFAULT_EXPIRE_SECONDS = 3600  # 1小时

    # 确认提示模板
    CONFIRMATION_PROMPTS = {
        "feature": """
🔍 检测到新功能需求

**需求标题**: {title}
**需求描述**: {description}
**置信度**: {confidence:.0%}
**建议优先级**: {priority}

是否将此需求添加到需求文档？
- 输入 "是" 或 "yes" 确认添加
- 输入 "否" 或 "no" 拒绝添加
- 输入 "修改" 或 "modify" 后跟修改内容来修改后添加
""",
        "bug_fix": """
🐛 检测到Bug修复需求

**问题描述**: {title}
**详细说明**: {description}
**置信度**: {confidence:.0%}
**建议优先级**: {priority}

是否将此Bug添加到任务列表？
- 输入 "是" 或 "yes" 确认添加
- 输入 "否" 或 "no" 拒绝添加
""",
        "improvement": """
💡 检测到改进建议

**改进标题**: {title}
**改进描述**: {description}
**置信度**: {confidence:.0%}

是否将此改进建议添加到需求文档？
- 输入 "是" 或 "yes" 确认添加
- 输入 "否" 或 "no" 拒绝添加
""",
        "default": """
📋 检测到新需求

**标题**: {title}
**描述**: {description}
**类型**: {req_type}
**置信度**: {confidence:.0%}

是否添加此需求？
- 输入 "是" 或 "yes" 确认添加
- 输入 "否" 或 "no" 拒绝添加
""",
    }

    def __init__(
        self,
        auto_approve_threshold: float = 0.95,
        auto_reject_threshold: float = 0.3,
        expire_seconds: int = DEFAULT_EXPIRE_SECONDS,
        max_pending: int = 50,
    ) -> None:
        """
        初始化确认管理器

        Args:
            auto_approve_threshold: 自动批准阈值（置信度高于此值自动批准）
            auto_reject_threshold: 自动拒绝阈值（置信度低于此值自动拒绝）
            expire_seconds: 待确认项过期时间（秒）
            max_pending: 最大待确认项数量
        """
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_reject_threshold = auto_reject_threshold
        self.expire_seconds = expire_seconds
        self.max_pending = max_pending
        self._pending_queue: dict[str, PendingConfirmation] = {}
        self._confirmation_count = 0

    def add_pending(
        self,
        requirement: dict[str, Any],
        auto_approve: bool = True,
    ) -> PendingConfirmation:
        """
        添加待确认需求

        Args:
            requirement: 检测到的需求
            auto_approve: 是否启用自动批准

        Returns:
            待确认项（可能已被自动批准）
        """
        # 检查队列容量
        if len(self._pending_queue) >= self.max_pending:
            # 清理过期项
            self._cleanup_expired()
            if len(self._pending_queue) >= self.max_pending:
                # 移除最旧的项
                oldest_id = min(
                    self._pending_queue.keys(),
                    key=lambda k: self._pending_queue[k].created_at,
                )
                del self._pending_queue[oldest_id]  # 从队列中删除

        # 创建待确认项
        confirmation_id = self._generate_confirmation_id()
        confidence = requirement.get("confidence", 0.5)

        # 确定初始状态
        initial_status = ConfirmationStatus.PENDING
        if auto_approve:
            if confidence >= self.auto_approve_threshold:
                initial_status = ConfirmationStatus.AUTO_APPROVED
            elif confidence < self.auto_reject_threshold:
                initial_status = ConfirmationStatus.REJECTED

        pending = PendingConfirmation(
            confirmation_id=confirmation_id,
            requirement_id=requirement.get("req_id", ""),
            title=requirement.get("title", "未知需求"),
            description=requirement.get("description", ""),
            req_type=requirement.get("req_type", "feature"),
            suggested_action=self._determine_action(requirement),
            confidence=confidence,
            expires_at=time.time() + self.expire_seconds,
            status=initial_status,
            original_message=requirement.get("original_message", ""),
        )

        self._pending_queue[confirmation_id] = pending
        return pending

    def generate_confirmation_prompt(self, pending: PendingConfirmation) -> str:
        """
        生成确认提示

        Args:
            pending: 待确认项

        Returns:
            确认提示文本
        """
        req_type = pending.req_type
        template = self.CONFIRMATION_PROMPTS.get(req_type, self.CONFIRMATION_PROMPTS["default"])

        # 优先级从上下文获取，如果没有则使用默认值
        priority = "P2"
        if pending.context and "priority" in pending.context:
            priority = pending.context["priority"]

        return template.format(
            title=pending.title,
            description=pending.description,
            confidence=pending.confidence,
            req_type=req_type,
            priority=priority,
        )

    def process_response(
        self,
        confirmation_id: str,
        response: str,
        modification: str | None = None,
    ) -> PendingConfirmation | None:
        """
        处理用户响应

        Args:
            confirmation_id: 确认ID
            response: 用户响应（yes/no/modify等）
            modification: 修改内容（如果用户选择修改）

        Returns:
            更新后的待确认项，如果不存在返回None
        """
        pending = self._pending_queue.get(confirmation_id)
        if pending is None:
            return None

        # 检查是否过期
        if pending.is_expired():
            pending.status = ConfirmationStatus.TIMEOUT
            return pending

        # 解析响应
        response_lower = response.lower().strip()

        if response_lower in ["是", "yes", "y", "确认", "ok"]:
            pending.status = ConfirmationStatus.APPROVED
            pending.user_response = response

        elif response_lower in ["否", "no", "n", "拒绝", "cancel"]:
            pending.status = ConfirmationStatus.REJECTED
            pending.user_response = response

        elif response_lower in ["修改", "modify", "m", "edit"] or modification:
            pending.status = ConfirmationStatus.MODIFIED
            pending.user_response = response
            pending.modification_notes = modification

        return pending

    def get_pending(self, confirmation_id: str) -> PendingConfirmation | None:
        """获取待确认项"""
        return self._pending_queue.get(confirmation_id)

    def get_all_pending(self) -> list[PendingConfirmation]:
        """获取所有待确认项（不包括已处理的）"""
        return [
            p for p in self._pending_queue.values()
            if p.status == ConfirmationStatus.PENDING
        ]

    def get_approved(self) -> list[PendingConfirmation]:
        """获取已批准的待确认项"""
        return [
            p for p in self._pending_queue.values()
            if p.status in [ConfirmationStatus.APPROVED, ConfirmationStatus.AUTO_APPROVED, ConfirmationStatus.MODIFIED]
        ]

    def get_rejected(self) -> list[PendingConfirmation]:
        """获取已拒绝的待确认项"""
        return [
            p for p in self._pending_queue.values()
            if p.status in [ConfirmationStatus.REJECTED, ConfirmationStatus.TIMEOUT]
        ]

    def clear_processed(self) -> int:
        """清理已处理的待确认项"""
        to_remove = [
            id for id, p in self._pending_queue.items()
            if p.status != ConfirmationStatus.PENDING
        ]
        for id in to_remove:
            del self._pending_queue[id]
        return len(to_remove)

    def batch_approve(self, confirmation_ids: list[str]) -> list[PendingConfirmation]:
        """批量批准"""
        results = []
        for id in confirmation_ids:
            pending = self._pending_queue.get(id)
            if pending and not pending.is_expired():
                pending.status = ConfirmationStatus.APPROVED
                pending.user_response = "batch_approved"
                results.append(pending)
        return results

    def batch_reject(self, confirmation_ids: list[str]) -> list[PendingConfirmation]:
        """批量拒绝"""
        results = []
        for id in confirmation_ids:
            pending = self._pending_queue.get(id)
            if pending and not pending.is_expired():
                pending.status = ConfirmationStatus.REJECTED
                pending.user_response = "batch_rejected"
                results.append(pending)
        return results

    def get_stats(self) -> dict[str, Any]:
        """获取确认统计"""
        total = len(self._pending_queue)
        by_status = {}
        for status in ConfirmationStatus:
            by_status[status.value] = sum(
                1 for p in self._pending_queue.values()
                if p.status == status
            )

        return {
            "total": total,
            "by_status": by_status,
            "pending_count": by_status.get("pending", 0),
            "approved_count": by_status.get("approved", 0) + by_status.get("auto_approved", 0),
            "rejected_count": by_status.get("rejected", 0) + by_status.get("timeout", 0),
        }

    # ==================== 内部方法 ====================

    def _generate_confirmation_id(self) -> str:
        """生成确认ID（使用UUID确保唯一性）"""
        return f"CONF-{uuid.uuid4().hex[:8].upper()}"

    def _determine_action(self, requirement: dict[str, Any]) -> str:
        """确定建议操作"""
        req_type = requirement.get("req_type", "feature")

        actions = {
            "feature": "添加到需求文档",
            "bug_fix": "添加到任务列表（Bug修复）",
            "improvement": "添加到改进计划",
            "constraint": "添加到设计约束",
            "question": "记录到咨询记录",
            "feedback": "添加到反馈列表",
        }

        return actions.get(req_type, "添加到需求文档")

    def _cleanup_expired(self) -> int:
        """清理过期项"""
        expired_ids = [
            id for id, p in self._pending_queue.items()
            if p.is_expired()
        ]
        for id in expired_ids:
            self._pending_queue[id].status = ConfirmationStatus.TIMEOUT
        return len(expired_ids)


def create_confirmation_manager(
    auto_approve_threshold: float = 0.95,
    expire_seconds: int = 3600,
) -> ConfirmationManager:
    """创建确认管理器"""
    return ConfirmationManager(
        auto_approve_threshold=auto_approve_threshold,
        expire_seconds=expire_seconds,
    )