"""
Session Module - 多对话会话管理

支持在项目开发过程中维护多个独立的对话会话：
- 主开发对话 (Development): 核心开发流程，不被打断
- 产品经理对话 (ProductManager): 需求沟通
- 项目经理对话 (ProjectManager): 进度协调
- 架构师对话 (Architect): 技术讨论
- 测试人员对话 (Tester): 测试反馈
- 通用对话 (General): 其他沟通

使用场景:
    harness = Harness()

    # 主开发流程
    harness.chat("实现用户登录功能")

    # 切换到产品经理对话，讨论需求
    harness.switch_session("product_manager")
    harness.chat("登录功能需要支持哪些方式？")

    # 切换回主开发，继续工作
    harness.switch_session("development")
    harness.chat("继续实现...")

    # 查看所有对话历史
    harness.list_sessions()
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid


class SessionType(Enum):
    """
    会话类型 - 按角色分类

    每种类型的会话有独立的记忆空间，互不干扰
    """

    DEVELOPMENT = "development"                # 主开发对话
    PRODUCT_MANAGER = "product_manager"        # 产品经理对话
    PROJECT_MANAGER = "project_manager"        # 项目经理对话
    ARCHITECT = "architect"                    # 架构师对话
    TESTER = "tester"                          # 测试人员对话
    DOC_WRITER = "doc_writer"                  # 文档管理员对话
    GENERAL = "general"                        # 通用对话


class MessageRole(Enum):
    """消息角色"""

    USER = "user"          # 用户消息
    ASSISTANT = "assistant"  # AI 回复
    SYSTEM = "system"      # 系统消息


class Message(BaseModel):
    """
    单条消息

    记录对话中的每条消息，包含：
    - 角色 (用户/AI/系统)
    - 内容
    - 时间戳
    - 元数据
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8], description="消息ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: float = Field(default_factory=time.time, description="时间戳")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    def is_user(self) -> bool:
        """是否是用户消息"""
        return self.role == MessageRole.USER

    def is_assistant(self) -> bool:
        """是否是 AI 回复"""
        return self.role == MessageRole.ASSISTANT


class Session(BaseModel):
    """
    会话 - 单个独立的对话空间

    每个会话包含：
    - 唯一标识
    - 会话类型 (关联角色)
    - 消息历史
    - 会话上下文
    - 重要记忆 (跨会话共享)
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8], description="会话ID")
    name: str = Field(default="", description="会话名称")
    session_type: SessionType = Field(default=SessionType.GENERAL, description="会话类型")
    messages: list[Message] = Field(default_factory=list, description="消息历史")
    context: dict[str, Any] = Field(default_factory=dict, description="会话上下文")
    important_memories: list[str] = Field(default_factory=list, description="重要记忆ID列表")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")

    def add_message(self, role: MessageRole | str, content: str, metadata: dict[str, Any] | None = None) -> Message:
        """
        添加消息

        Args:
            role: 消息角色
            content: 消息内容
            metadata: 元数据

        Returns:
            创建的消息
        """
        if isinstance(role, str):
            role = MessageRole(role)

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self.messages.append(message)
        self.updated_at = time.time()

        return message

    def get_messages(self, limit: int = 0) -> list[Message]:
        """
        获取消息历史

        Args:
            limit: 限制数量 (0 表示全部)

        Returns:
            消息列表
        """
        if limit <= 0:
            return self.messages.copy()
        return self.messages[-limit:]

    def get_last_message(self) -> Message | None:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def clear_messages(self) -> int:
        """
        清空消息历史

        Returns:
            清除的消息数量
        """
        count = len(self.messages)
        self.messages.clear()
        self.updated_at = time.time()
        return count

    def get_summary(self) -> dict[str, Any]:
        """获取会话摘要"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.session_type.value,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def mark_important(self, memory_id: str) -> None:
        """标记重要记忆"""
        if memory_id not in self.important_memories:
            self.important_memories.append(memory_id)

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self.context[key] = value
        self.updated_at = time.time()

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self.context.get(key, default)


class SessionManager:
    """
    会话管理器 - 管理多个独立对话会话

    核心功能:
    - 创建和管理多个会话
    - 按类型分类会话
    - 会话切换
    - 会话持久化
    - 跨会话重要记忆共享

    使用示例:
        manager = SessionManager()

        # 创建主开发会话
        dev_session = manager.create_session(SessionType.DEVELOPMENT, "主开发")

        # 创建产品经理会话
        pm_session = manager.create_session(SessionType.PRODUCT_MANAGER, "产品沟通")

        # 切换会话
        manager.set_active_session(pm_session.id)

        # 获取当前会话
        current = manager.get_active_session()
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._active_session_id: str | None = None
        self._sessions_by_type: dict[SessionType, list[str]] = {
            st: [] for st in SessionType
        }

        # 默认创建主开发会话
        self._create_default_sessions()

    def _create_default_sessions(self) -> None:
        """创建默认会话"""
        # 主开发会话
        dev_session = Session(
            name="主开发对话",
            session_type=SessionType.DEVELOPMENT,
        )
        self._sessions[dev_session.id] = dev_session
        self._sessions_by_type[SessionType.DEVELOPMENT].append(dev_session.id)
        self._active_session_id = dev_session.id

    def create_session(
        self,
        session_type: SessionType,
        name: str = "",
        set_active: bool = False,
    ) -> Session:
        """
        创建新会话

        Args:
            session_type: 会话类型
            name: 会话名称
            set_active: 是否设为当前会话

        Returns:
            创建的会话
        """
        session = Session(
            name=name or session_type.value,
            session_type=session_type,
        )

        self._sessions[session.id] = session
        self._sessions_by_type[session_type].append(session.id)

        if set_active:
            self._active_session_id = session.id

        return session

    def get_session(self, session_id: str) -> Session | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def get_active_session(self) -> Session | None:
        """获取当前活动会话"""
        if self._active_session_id:
            return self._sessions.get(self._active_session_id)
        return None

    def set_active_session(self, session_id: str) -> bool:
        """
        设置活动会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        if session_id in self._sessions:
            self._active_session_id = session_id
            return True
        return False

    def switch_session(self, session_type: SessionType) -> Session | None:
        """
        按类型切换会话

        优先切换到该类型的第一个会话，如果没有则创建新会话

        Args:
            session_type: 会话类型

        Returns:
            切换后的会话
        """
        sessions = self._sessions_by_type.get(session_type, [])

        if sessions:
            self._active_session_id = sessions[0]
            return self._sessions[sessions[0]]

        # 没有该类型的会话，创建新的
        return self.create_session(session_type, set_active=True)

    def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有会话"""
        return [
            {
                **session.get_summary(),
                "is_active": session.id == self._active_session_id,
            }
            for session in self._sessions.values()
        ]

    def list_sessions_by_type(self, session_type: SessionType) -> list[Session]:
        """按类型列出会话"""
        session_ids = self._sessions_by_type.get(session_type, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        # 不能删除主开发会话
        if session.session_type == SessionType.DEVELOPMENT:
            return False

        # 从类型列表中移除
        if session_id in self._sessions_by_type[session.session_type]:
            self._sessions_by_type[session.session_type].remove(session_id)

        # 删除会话
        del self._sessions[session_id]

        # 如果删除的是当前会话，切换回主开发
        if self._active_session_id == session_id:
            dev_sessions = self._sessions_by_type[SessionType.DEVELOPMENT]
            self._active_session_id = dev_sessions[0] if dev_sessions else None

        return True

    def chat(self, content: str, role: MessageRole = MessageRole.USER) -> Message | None:
        """
        在当前会话中发送消息

        Args:
            content: 消息内容
            role: 消息角色

        Returns:
            创建的消息
        """
        session = self.get_active_session()
        if session:
            return session.add_message(role, content)
        return None

    def get_conversation_history(self, session_id: str | None = None, limit: int = 20) -> list[Message]:
        """
        获取对话历史

        Args:
            session_id: 会话ID (None 表示当前会话)
            limit: 限制数量

        Returns:
            消息列表
        """
        if session_id:
            session = self.get_session(session_id)
        else:
            session = self.get_active_session()

        if session:
            return session.get_messages(limit)
        return []

    def get_all_memories(self) -> list[dict[str, Any]]:
        """
        获取所有会话的重要记忆

        Returns:
            重要记忆列表
        """
        memories = []
        for session in self._sessions.values():
            if session.important_memories:
                memories.append({
                    "session_id": session.id,
                    "session_name": session.name,
                    "session_type": session.session_type.value,
                    "memory_ids": session.important_memories,
                })
        return memories

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        total_messages = sum(len(s.messages) for s in self._sessions.values())

        return {
            "total_sessions": len(self._sessions),
            "active_session_id": self._active_session_id,
            "total_messages": total_messages,
            "sessions_by_type": {
                st.value: len(ids) for st, ids in self._sessions_by_type.items() if ids
            },
        }


# ==================== 便捷函数 ====================

def create_session_manager() -> SessionManager:
    """创建会话管理器"""
    return SessionManager()