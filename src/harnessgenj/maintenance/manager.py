"""
Document Maintenance Manager - 文档维护管理器

负责：
1. 管理文档更新操作
2. 发送团队通知
3. 同步文档变更
4. 维护文档版本历史

与 RequirementDetector 和 ConfirmationManager 配合使用，
完成从需求检测到文档更新的完整流程。
"""

import time
import json
import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DocumentUpdate(BaseModel):
    """文档更新记录"""

    update_id: str = Field(..., description="更新ID")
    document_type: str = Field(..., description="文档类型")
    operation: str = Field(..., description="操作类型（add/update/remove）")
    content_before: str | None = Field(default=None, description="更新前内容")
    content_after: str = Field(..., description="更新后内容")
    change_summary: str = Field(..., description="变更摘要")
    source_requirement_id: str | None = Field(default=None, description="来源需求ID")
    source_confirmation_id: str | None = Field(default=None, description="来源确认ID")
    updated_by: str = Field(default="system", description="更新者")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    notify_team: bool = Field(default=True, description="是否通知团队")
    notified_roles: list[str] = Field(default_factory=list, description="已通知的角色")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class TeamNotification(BaseModel):
    """团队通知"""

    notification_id: str = Field(..., description="通知ID")
    notification_type: str = Field(..., description="通知类型")
    target_roles: list[str] = Field(..., description="目标角色")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    document_type: str | None = Field(default=None, description="相关文档类型")
    action_required: bool = Field(default=False, description="是否需要行动")
    action_description: str | None = Field(default=None, description="行动描述")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    read_by: list[str] = Field(default_factory=list, description="已读角色")
    acknowledged_by: list[str] = Field(default_factory=list, description="已确认角色")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()

    def mark_read(self, role: str) -> None:
        """标记已读"""
        if role not in self.read_by:
            self.read_by.append(role)

    def mark_acknowledged(self, role: str) -> None:
        """标记已确认"""
        if role not in self.acknowledged_by:
            self.acknowledged_by.append(role)


class NotificationType(str, Enum):
    """通知类型"""

    REQUIREMENT_ADDED = "requirement_added"  # 需求新增
    REQUIREMENT_CHANGED = "requirement_changed"  # 需求变更
    DOCUMENT_UPDATED = "document_updated"  # 文档更新
    TASK_CREATED = "task_created"  # 任务创建
    TASK_COMPLETED = "task_completed"  # 任务完成
    REVIEW_REQUESTED = "review_requested"  # 审查请求
    ISSUE_FOUND = "issue_found"  # 问题发现
    PROGRESS_UPDATE = "progress_update"  # 进度更新


class DocumentMaintenanceManager:
    """
    文档维护管理器

    管理文档更新和团队通知，确保团队成员能够访问最新文档。

    使用示例:
        from harnessgenj.memory import MemoryManager
        from harnessgenj.maintenance import DocumentMaintenanceManager

        memory = MemoryManager(".harnessgenj")
        maint_manager = DocumentMaintenanceManager(memory)

        # 添加需求到文档
        update = maint_manager.add_requirement_to_document(
            requirement={"title": "购物车功能", "description": "..."},
            document_type="requirements",
        )

        # 通知团队
        notification = maint_manager.notify_team(
            notification_type="requirement_added",
            target_roles=["developer", "architect"],
            title="新需求已添加",
            content="购物车功能需求已添加到需求文档",
        )
    """

    # 通知模板
    NOTIFICATION_TEMPLATES = {
        NotificationType.REQUIREMENT_ADDED: {
            "title": "新需求已添加",
            "template": "需求 '{requirement_title}' 已添加到需求文档。\n请查阅并确认。",
            "action_required": True,
            "action": "查阅需求文档",
        },
        NotificationType.REQUIREMENT_CHANGED: {
            "title": "需求已变更",
            "template": "需求 '{requirement_title}' 已变更。\n变更内容: {change_summary}",
            "action_required": True,
            "action": "查阅变更内容",
        },
        NotificationType.DOCUMENT_UPDATED: {
            "title": "文档已更新",
            "template": "{document_type} 文档已更新。\n更新摘要: {change_summary}",
            "action_required": False,
        },
        NotificationType.TASK_CREATED: {
            "title": "新任务已创建",
            "template": "任务 '{task_title}' 已创建并分配给 {assignee}。\n优先级: {priority}",
            "action_required": True,
            "action": "开始任务",
        },
        NotificationType.TASK_COMPLETED: {
            "title": "任务已完成",
            "template": "任务 '{task_title}' 已由 {assignee} 完成。",
            "action_required": False,
        },
        NotificationType.ISSUE_FOUND: {
            "title": "发现问题",
            "template": "在 {context} 发现问题: '{issue_title}'。\n建议优先级: {priority}",
            "action_required": True,
            "action": "处理问题",
        },
    }

    # 角色通知权限映射
    ROLE_NOTIFICATION_MAPPING = {
        NotificationType.REQUIREMENT_ADDED: ["developer", "architect", "tester"],
        NotificationType.REQUIREMENT_CHANGED: ["developer", "architect"],
        NotificationType.DOCUMENT_UPDATED: ["all"],
        NotificationType.TASK_CREATED: ["assignee"],
        NotificationType.TASK_COMPLETED: ["project_manager"],
        NotificationType.ISSUE_FOUND: ["developer", "project_manager"],
    }

    def __init__(
        self,
        memory_manager: Any,
        enable_version_history: bool = True,
        max_version_history: int = 10,
    ) -> None:
        """
        初始化文档维护管理器

        Args:
            memory_manager: MemoryManager 实例
            enable_version_history: 是否启用版本历史
            max_version_history: 最大版本历史数量
        """
        self.memory = memory_manager
        self.enable_version_history = enable_version_history
        self.max_version_history = max_version_history
        self._update_history: list[DocumentUpdate] = []
        self._notifications: dict[str, TeamNotification] = {}
        self._update_count = 0
        self._notification_count = 0

    # ==================== 文档更新操作 ====================

    def add_requirement_to_document(
        self,
        requirement: dict[str, Any],
        document_type: str = "requirements",
        notify_roles: list[str] | None = None,
    ) -> DocumentUpdate:
        """
        将需求添加到文档

        Args:
            requirement: 需求信息
            document_type: 目标文档类型
            notify_roles: 需要通知的角色列表

        Returns:
            文档更新记录
        """
        # 获取当前文档内容
        current_content = self.memory.get_document(document_type) or ""

        # 构建新内容
        new_requirement_text = self._format_requirement_text(requirement)
        new_content = current_content + "\n\n" + new_requirement_text

        # 存储更新
        self.memory.store_document(document_type, new_content)

        # 创建更新记录
        update = DocumentUpdate(
            update_id=self._generate_update_id(),
            document_type=document_type,
            operation="add",
            content_before=current_content,
            content_after=new_content,
            change_summary=f"新增需求: {requirement.get('title', '未知需求')}",
            source_requirement_id=requirement.get("req_id"),
            notify_team=True,
        )

        self._update_history.append(update)

        # 限制版本历史大小
        if len(self._update_history) > self.max_version_history:
            self._update_history = self._update_history[-self.max_version_history:]

        # 发送通知
        if notify_roles is None:
            notify_roles = self.ROLE_NOTIFICATION_MAPPING.get(
                NotificationType.REQUIREMENT_ADDED, []
            )

        if update.notify_team:
            self._send_requirement_notification(requirement, notify_roles)

        return update

    def update_document_section(
        self,
        document_type: str,
        section_title: str,
        new_content: str,
        notify_roles: list[str] | None = None,
    ) -> DocumentUpdate | None:
        """
        更新文档特定部分

        Args:
            document_type: 文档类型
            section_title: 部分标题
            new_content: 新内容
            notify_roles: 需要通知的角色

        Returns:
            文档更新记录
        """
        current = self.memory.get_document(document_type) or ""
        if not current:
            return None

        # 查找并替换部分内容
        updated = self._replace_section(current, section_title, new_content)
        if updated == current:
            return None  # 没有变化

        # 存储
        self.memory.store_document(document_type, updated)

        # 创建记录
        update = DocumentUpdate(
            update_id=self._generate_update_id(),
            document_type=document_type,
            operation="update",
            content_before=current,
            content_after=updated,
            change_summary=f"更新部分: {section_title}",
            notify_team=True,
        )

        self._update_history.append(update)

        # 通知
        if notify_roles:
            self.notify_team(
                notification_type=NotificationType.DOCUMENT_UPDATED.value,
                target_roles=notify_roles,
                title=f"{document_type} 文档已更新",
                content=f"部分 '{section_title}' 已更新。",
            )

        return update

    def remove_from_document(
        self,
        document_type: str,
        requirement_id: str,
        notify_roles: list[str] | None = None,
    ) -> DocumentUpdate | None:
        """
        从文档中移除需求

        Args:
            document_type: 文档类型
            requirement_id: 需求ID
            notify_roles: 需要通知的角色

        Returns:
            文档更新记录
        """
        current = self.memory.get_document(document_type) or ""
        if not current:
            return None

        # 查找并移除需求
        updated = self._remove_requirement(current, requirement_id)
        if updated == current:
            return None

        # 存储
        self.memory.store_document(document_type, updated)

        # 创建记录
        update = DocumentUpdate(
            update_id=self._generate_update_id(),
            document_type=document_type,
            operation="remove",
            content_before=current,
            content_after=updated,
            change_summary=f"移除需求: {requirement_id}",
            source_requirement_id=requirement_id,
            notify_team=True,
        )

        self._update_history.append(update)

        # 通知
        if notify_roles:
            self.notify_team(
                notification_type=NotificationType.REQUIREMENT_CHANGED.value,
                target_roles=notify_roles,
                title="需求已移除",
                content=f"需求 {requirement_id} 已从 {document_type} 移除。",
            )

        return update

    # ==================== 任务管理 ====================

    def create_task_from_requirement(
        self,
        requirement: dict[str, Any],
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """
        从需求创建任务

        Args:
            requirement: 需求信息
            assignee: 指定负责人

        Returns:
            任务信息
        """
        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"  # 使用UUID生成唯一ID

        task = {
            "task_id": task_id,
            "title": requirement.get("title", ""),
            "description": requirement.get("description", ""),
            "type": requirement.get("req_type", "feature"),
            "priority": requirement.get("suggested_priority", "P2"),
            "assignee": assignee or requirement.get("suggested_assignee", "developer"),
            "status": "pending",
            "created_at": time.time(),
            "source_requirement": requirement.get("req_id"),
        }

        # 存储任务
        self.memory.store_task(task_id, task)

        # 任务不需要再存储到知识库，已经通过store_task存储

        # 通知
        self.notify_team(
            notification_type=NotificationType.TASK_CREATED.value,
            target_roles=[task["assignee"], "project_manager"],
            title="新任务已创建",
            content=f"任务 '{task['title']}' 已创建并分配给 {task['assignee']}。\n优先级: {task['priority']}",
            document_type="progress",
            action_required=True,
            action_description="开始任务",
        )

        return task

    # ==================== 团队通知 ====================

    def notify_team(
        self,
        notification_type: str,
        target_roles: list[str],
        title: str,
        content: str,
        document_type: str | None = None,
        action_required: bool = False,
        action_description: str | None = None,
    ) -> TeamNotification:
        """
        发送团队通知

        Args:
            notification_type: 通知类型
            target_roles: 目标角色
            title: 通知标题
            content: 通知内容
            document_type: 相关文档类型
            action_required: 是否需要行动
            action_description: 行动描述

        Returns:
            通知记录
        """
        notification = TeamNotification(
            notification_id=self._generate_notification_id(),
            notification_type=notification_type,
            target_roles=target_roles,
            title=title,
            content=content,
            document_type=document_type,
            action_required=action_required,
            action_description=action_description,
        )

        self._notifications[notification.notification_id] = notification

        # 存储通知到记忆（持久化）
        self.memory.store_knowledge(
            f"notification_{notification.notification_id}",
            json.dumps(notification.to_dict()),  # 转换为JSON字符串
        )

        return notification

    def get_notifications_for_role(self, role: str) -> list[TeamNotification]:
        """
        获取指定角色的通知

        Args:
            role: 角色类型

        Returns:
            通知列表（未读优先）
        """
        notifications = []
        for n in self._notifications.values():
            if "all" in n.target_roles or role in n.target_roles:
                if role not in n.read_by:
                    notifications.append(n)

        # 按创建时间倒序
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications

    def mark_notification_read(
        self,
        notification_id: str,
        role: str,
    ) -> bool:
        """标记通知已读"""
        notification = self._notifications.get(notification_id)
        if notification:
            notification.mark_read(role)
            return True
        return False

    def get_pending_actions_for_role(self, role: str) -> list[TeamNotification]:
        """获取需要行动的通知"""
        notifications = self.get_notifications_for_role(role)
        return [n for n in notifications if n.action_required]

    # ==================== 版本历史 ====================

    def get_document_history(
        self,
        document_type: str,
        limit: int = 5,
    ) -> list[DocumentUpdate]:
        """获取文档更新历史"""
        history = [
            u for u in self._update_history
            if u.document_type == document_type
        ]
        return history[-limit:]

    def get_latest_update(self, document_type: str) -> DocumentUpdate | None:
        """获取最新更新"""
        history = self.get_document_history(document_type, 1)
        return history[0] if history else None

    def rollback_document(
        self,
        document_type: str,
        update_id: str,
    ) -> bool:
        """
        回滚文档到指定版本

        Args:
            document_type: 文档类型
            update_id: 更新ID

        Returns:
            是否成功
        """
        # 查找更新记录
        update = None
        for u in self._update_history:
            if u.update_id == update_id and u.document_type == document_type:
                update = u
                break

        if not update or not update.content_before:
            return False

        # 回滚
        self.memory.store_document(document_type, update.content_before)

        # 记录回滚
        rollback_update = DocumentUpdate(
            update_id=self._generate_update_id(),
            document_type=document_type,
            operation="rollback",
            content_before=update.content_after,
            content_after=update.content_before,
            change_summary=f"回滚到版本 {update_id}",
        )
        self._update_history.append(rollback_update)

        return True

    # ==================== 统计和状态 ====================

    def get_update_stats(self) -> dict[str, Any]:
        """获取更新统计"""
        by_document = {}
        for u in self._update_history:
            doc_type = u.document_type
            if doc_type not in by_document:
                by_document[doc_type] = {"count": 0, "operations": {}}
            by_document[doc_type]["count"] += 1
            op = u.operation
            by_document[doc_type]["operations"][op] = (
                by_document[doc_type]["operations"].get(op, 0) + 1
            )

        return {
            "total_updates": len(self._update_history),
            "by_document": by_document,
            "total_notifications": len(self._notifications),
            "unread_notifications": sum(
                1 for n in self._notifications.values()
                if len(n.read_by) == 0
            ),
        }

    def get_maintenance_summary(self) -> str:
        """获取维护摘要"""
        stats = self.get_update_stats()
        recent_updates = self._update_history[-5:] if self._update_history else []

        summary = f"""# 文档维护摘要

## 统计
- 总更新次数: {stats['total_updates']}
- 总通知数: {stats['total_notifications']}
- 未读通知: {stats['unread_notifications']}

## 最近更新
"""
        for u in recent_updates:
            summary += f"\n- [{u.document_type}] {u.change_summary} ({time.strftime('%Y-%m-%d %H:%M', time.localtime(u.updated_at))})"

        return summary

    # ==================== 内部方法 ====================

    def _format_requirement_text(self, requirement: dict[str, Any]) -> str:
        """格式化需求文本"""
        title = requirement.get("title", "未知需求")
        description = requirement.get("description", "")
        req_type = requirement.get("req_type", "feature")
        priority = requirement.get("suggested_priority", "P2")
        req_id = requirement.get("req_id", "")

        return f"""### {title}

- **ID**: {req_id}
- **类型**: {req_type}
- **优先级**: {priority}
- **描述**: {description}
- **添加时间**: {time.strftime('%Y-%m-%d %H:%M')}
"""

    def _replace_section(
        self,
        content: str,
        section_title: str,
        new_section_content: str,
    ) -> str:
        """替换文档部分"""
        # 查找部分标题
        lines = content.split("\n")
        in_section = False
        section_start = -1
        section_end = -1

        for i, line in enumerate(lines):
            if line.strip().startswith("#") and section_title in line:
                section_start = i
                in_section = True
            elif in_section and line.strip().startswith("#") and not section_title in line:
                section_end = i
                break

        if section_start == -1:
            return content

        if section_end == -1:
            section_end = len(lines)

        # 替换内容
        new_lines = lines[:section_start] + new_section_content.split("\n") + lines[section_end:]
        return "\n".join(new_lines)

    def _remove_requirement(self, content: str, requirement_id: str) -> str:
        """移除需求"""
        # 查找需求块
        lines = content.split("\n")
        requirement_start = -1
        requirement_end = -1

        for i, line in enumerate(lines):
            if requirement_id in line and "ID" in line:
                # 找到需求ID行
                # 向前查找标题行
                for j in range(i - 1, max(0, i - 5), -1):
                    if lines[j].strip().startswith("###"):
                        requirement_start = j
                        break
                # 向后查找下一个标题或结束
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("###") or lines[j].strip().startswith("#"):
                        requirement_end = j
                        break
                if requirement_end == -1:
                    requirement_end = len(lines)
                break

        if requirement_start == -1:
            return content

        # 移除需求块
        new_lines = lines[:requirement_start] + lines[requirement_end:]
        return "\n".join(new_lines)

    def _send_requirement_notification(
        self,
        requirement: dict[str, Any],
        roles: list[str],
    ) -> None:
        """发送需求通知"""
        template_data = self.NOTIFICATION_TEMPLATES.get(
            NotificationType.REQUIREMENT_ADDED, {}
        )

        title = template_data.get("title", "新需求已添加")
        content_template = template_data.get("template", "")
        content = content_template.format(
            requirement_title=requirement.get("title", ""),
        )

        self.notify_team(
            notification_type=NotificationType.REQUIREMENT_ADDED.value,
            target_roles=roles,
            title=title,
            content=content,
            document_type="requirements",
            action_required=template_data.get("action_required", True),
            action_description=template_data.get("action", ""),
        )

    def _generate_update_id(self) -> str:
        """生成更新ID"""
        self._update_count += 1
        return f"UPD-{self._update_count:04d}"

    def _generate_notification_id(self) -> str:
        """生成通知ID"""
        self._notification_count += 1
        return f"NOTIF-{self._notification_count:04d}"


def create_maintenance_manager(
    memory_manager: Any,
    enable_version_history: bool = True,
) -> DocumentMaintenanceManager:
    """创建文档维护管理器"""
    return DocumentMaintenanceManager(
        memory_manager=memory_manager,
        enable_version_history=enable_version_history,
    )