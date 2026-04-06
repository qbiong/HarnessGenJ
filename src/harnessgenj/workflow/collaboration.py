"""
Collaboration - 角色协作管理器

提供多角色协作能力：
- 消息传递
- 并行执行
- 产出物流转
- 协作状态可视化

使用示例:
    from harnessgenj.workflow.collaboration import RoleCollaborationManager

    manager = RoleCollaborationManager(coordinator)

    # 发送消息
    manager.send_message("developer", "reviewer", {"code": "..."})

    # 并行执行
    results = manager.execute_parallel([task1, task2])

    # 获取协作状态
    snapshot = manager.get_snapshot()
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed

from harnessgenj.workflow.message_bus import (
    MessageBus,
    RoleMessage,
    MessageType,
    MessagePriority,
    create_message_bus,
)
from harnessgenj.workflow.coordinator import WorkflowCoordinator


class CollaborationRole(BaseModel):
    """协作角色状态"""

    role_id: str
    role_type: str
    status: str = "idle"  # idle | working | waiting | reviewing
    current_task: dict[str, Any] | None = None
    artifacts_owned: list[str] = Field(default_factory=list)
    collaborators: list[str] = Field(default_factory=list)
    last_activity: float = Field(default_factory=time.time)
    message_count: int = 0


class CollaborationSnapshot(BaseModel):
    """协作快照"""

    timestamp: float = Field(default_factory=time.time)
    roles: list[CollaborationRole] = Field(default_factory=list)
    active_connections: list[tuple[str, str]] = Field(default_factory=list)
    artifacts_flow: list[dict[str, Any]] = Field(default_factory=list)
    pipeline_progress: dict[str, Any] = Field(default_factory=dict)


class ParallelTask(BaseModel):
    """并行任务"""

    task_id: str
    task: dict[str, Any]
    executor_role_id: str | None = None  # 使用角色ID而非对象，避免Pydantic schema问题
    status: str = "pending"  # pending | running | completed | failed
    result: dict[str, Any] | None = None
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None


class RoleCollaborationManager:
    """
    角色协作管理器

    支持:
    1. 角色间消息传递
    2. 并行任务执行
    3. 产出物流转
    4. 协作状态可视化
    """

    def __init__(
        self,
        coordinator: WorkflowCoordinator,
        max_parallel_tasks: int = 4,
    ) -> None:
        """
        初始化协作管理器

        Args:
            coordinator: 工作流协调器
            max_parallel_tasks: 最大并行任务数
        """
        self.coordinator = coordinator
        self._message_bus = create_message_bus()
        self._max_parallel_tasks = max_parallel_tasks
        self._executor = ThreadPoolExecutor(max_workers=max_parallel_tasks)
        self._lock = threading.Lock()

        # 角色状态跟踪
        self._role_states: dict[str, CollaborationRole] = {}

        # 产出物流转记录
        self._artifacts_flow: list[dict[str, Any]] = []

        # 统计
        self._stats = {
            "messages_sent": 0,
            "parallel_executions": 0,
            "artifacts_transferred": 0,
        }

    # ==================== 消息传递 ====================

    def send_message(
        self,
        from_role: str,
        to_role: str,
        content: dict[str, Any],
        *,
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: int = 5,
        requires_ack: bool = False,
    ) -> str:
        """
        发送角色间消息

        Args:
            from_role: 发送者角色ID
            to_role: 接收者角色ID
            content: 消息内容
            message_type: 消息类型
            priority: 优先级
            requires_ack: 是否需要确认

        Returns:
            消息ID
        """
        msg_id = self._message_bus.send(
            sender_id=from_role,
            receiver_id=to_role,
            content=content,
            message_type=message_type,
            priority=priority,
            requires_ack=requires_ack,
        )

        # 更新角色状态
        self._update_role_activity(from_role)
        self._update_role_activity(to_role)

        self._stats["messages_sent"] += 1
        return msg_id

    def broadcast(
        self,
        from_role: str,
        content: dict[str, Any],
        *,
        exclude: list[str] | None = None,
    ) -> list[str]:
        """
        广播消息到所有角色

        Args:
            from_role: 发送者角色ID
            content: 消息内容
            exclude: 排除的角色ID列表

        Returns:
            消息ID列表
        """
        msg_ids = self._message_bus.broadcast(
            sender_id=from_role,
            content=content,
            exclude=exclude,
        )

        self._update_role_activity(from_role)
        self._stats["messages_sent"] += len(msg_ids)
        return msg_ids

    def get_messages(self, role_id: str, limit: int = 50) -> list[RoleMessage]:
        """获取角色的消息"""
        return self._message_bus.get_messages(role_id, limit=limit)

    def ack_message(self, role_id: str, message_id: str) -> bool:
        """确认消息"""
        return self._message_bus.ack_message(role_id, message_id)

    # ==================== 并行执行 ====================

    def execute_parallel(
        self,
        tasks: list[dict[str, Any]],
        *,
        timeout: float | None = None,
        fail_fast: bool = True,
    ) -> dict[str, Any]:
        """
        并行执行多个任务

        Args:
            tasks: 任务列表，每个任务包含 role_id, task_data
            timeout: 超时时间（秒）
            fail_fast: 是否在第一个失败时取消其他任务

        Returns:
            执行结果
        """
        futures: dict[str, Future] = {}
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}

        def execute_task(role_id: str, task_data: dict[str, Any]) -> dict[str, Any]:
            """执行单个任务"""
            role = self.coordinator.get_role(role_id)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            self._update_role_status(role_id, "working", task_data)

            try:
                role.assign_task(task_data)
                result = role.execute_task()
                self._update_role_status(role_id, "idle")
                return result
            except Exception as e:
                self._update_role_status(role_id, "idle")
                raise e

        with self._lock:
            for i, task_item in enumerate(tasks):
                role_id = task_item.get("role_id")
                task_data = task_item.get("task", {})

                if not role_id:
                    continue

                task_id = task_data.get("task_id", f"parallel_{i}")
                future = self._executor.submit(execute_task, role_id, task_data)
                futures[task_id] = future

            self._stats["parallel_executions"] += 1

        # 等待所有任务完成
        cancelled = False
        for task_id, future in futures.items():
            try:
                result = future.result(timeout=timeout)
                results[task_id] = {
                    "status": "completed",
                    "result": result,
                }
            except Exception as e:
                errors[task_id] = str(e)
                results[task_id] = {
                    "status": "failed",
                    "error": str(e),
                }

                if fail_fast and not cancelled:
                    cancelled = True
                    for f in futures.values():
                        f.cancel()

        return {
            "total_tasks": len(tasks),
            "completed": len(results) - len(errors),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    def execute_with_dependencies(
        self,
        tasks: list[dict[str, Any]],
        dependencies: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        按依赖关系执行任务

        Args:
            tasks: 任务列表
            dependencies: 依赖关系 {task_id: [depends_on_task_ids]}

        Returns:
            执行结果
        """
        results: dict[str, Any] = {}
        completed: set[str] = set()
        failed: set[str] = set()

        # 构建任务映射
        task_map = {t.get("task_id"): t for t in tasks if t.get("task_id")}

        # 拓扑排序执行
        while len(completed) + len(failed) < len(task_map):
            # 找出可以执行的任务
            ready = []
            for task_id, task in task_map.items():
                if task_id in completed or task_id in failed:
                    continue
                deps = dependencies.get(task_id, [])
                if all(d in completed for d in deps):
                    ready.append(task)
                elif any(d in failed for d in deps):
                    # 依赖失败，标记为失败
                    failed.add(task_id)

            if not ready:
                break

            # 并行执行就绪任务
            batch_results = self.execute_parallel(
                [t for t in ready if t.get("role_id")],
                fail_fast=False,
            )

            for task_id, result in batch_results.get("results", {}).items():
                if result.get("status") == "completed":
                    completed.add(task_id)
                else:
                    failed.add(task_id)

        return {
            "completed": len(completed),
            "failed": len(failed),
            "results": results,
        }

    # ==================== 产出物流转 ====================

    def transfer_artifact(
        self,
        from_role: str,
        to_role: str,
        artifact_name: str,
        artifact_content: Any,
        *,
        message: str | None = None,
    ) -> bool:
        """
        转移产出物

        Args:
            from_role: 发送者角色ID
            to_role: 接收者角色ID
            artifact_name: 产出物名称
            artifact_content: 产出物内容
            message: 附加消息

        Returns:
            是否成功
        """
        # 记录流转
        flow_record = {
            "from": from_role,
            "to": to_role,
            "artifact": artifact_name,
            "timestamp": time.time(),
            "message": message,
        }
        self._artifacts_flow.append(flow_record)

        # 更新角色状态
        if from_role in self._role_states:
            if artifact_name in self._role_states[from_role].artifacts_owned:
                self._role_states[from_role].artifacts_owned.remove(artifact_name)

        if to_role in self._role_states:
            self._role_states[to_role].artifacts_owned.append(artifact_name)

        # 发送通知消息
        self.send_message(
            from_role=from_role,
            to_role=to_role,
            content={
                "type": "artifact_transfer",
                "artifact_name": artifact_name,
                "message": message,
            },
            message_type=MessageType.ARTIFACT,
        )

        self._stats["artifacts_transferred"] += 1
        return True

    def get_artifacts_flow(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取产出物流转记录"""
        return self._artifacts_flow[-limit:]

    # ==================== 状态管理 ====================

    def _update_role_activity(self, role_id: str) -> None:
        """更新角色活动时间"""
        if role_id in self._role_states:
            self._role_states[role_id].last_activity = time.time()
            self._role_states[role_id].message_count += 1

    def _update_role_status(
        self,
        role_id: str,
        status: str,
        current_task: dict[str, Any] | None = None,
    ) -> None:
        """更新角色状态"""
        if role_id not in self._role_states:
            # 创建新状态
            role = self.coordinator.get_role(role_id)
            self._role_states[role_id] = CollaborationRole(
                role_id=role_id,
                role_type=role.role_type.value if role else "unknown",
                status=status,
                current_task=current_task,
            )
        else:
            self._role_states[role_id].status = status
            self._role_states[role_id].current_task = current_task
            self._role_states[role_id].last_activity = time.time()

    def register_role(self, role_id: str, role_type: str) -> None:
        """注册角色到协作管理器"""
        self._role_states[role_id] = CollaborationRole(
            role_id=role_id,
            role_type=role_type,
        )

    def unregister_role(self, role_id: str) -> None:
        """注销角色"""
        self._role_states.pop(role_id, None)
        self._message_bus.clear_queue(role_id)

    def get_role_state(self, role_id: str) -> CollaborationRole | None:
        """获取角色状态"""
        return self._role_states.get(role_id)

    # ==================== 可视化 ====================

    def get_snapshot(self) -> CollaborationSnapshot:
        """获取协作快照"""
        # 收集角色状态
        roles = list(self._role_states.values())

        # 收集活跃连接
        active_connections = []
        for flow in self._artifacts_flow[-20:]:
            active_connections.append((flow["from"], flow["to"]))

        return CollaborationSnapshot(
            roles=roles,
            active_connections=active_connections,
            artifacts_flow=self._artifacts_flow[-50:],
        )

    def to_mermaid(self, title: str = "Role Collaboration") -> str:
        """生成 Mermaid 图表"""
        lines = [
            "```mermaid",
            f"graph TD",
            f"    title[{title}]",
        ]

        # 添加节点
        for role_id, state in self._role_states.items():
            label = f"{role_id}\\n({state.status})"
            color_map = {
                "idle": "#90EE90",
                "working": "#FFD700",
                "waiting": "#87CEEB",
                "reviewing": "#DDA0DD",
            }
            color = color_map.get(state.status, "#FFFFFF")
            lines.append(f'    {role_id}["{label}"]:::style_{state.status}')

        # 添加连接（最近的消息传递）
        for flow in self._artifacts_flow[-10:]:
            lines.append(f'    {flow["from"]} -->|{flow["artifact"]}| {flow["to"]}')

        # 添加样式
        lines.extend([
            "",
            "    classDef style_idle fill:#90EE90,stroke:#228B22",
            "    classDef style_working fill:#FFD700,stroke:#DAA520",
            "    classDef style_waiting fill:#87CEEB,stroke:#4682B4",
            "    classDef style_reviewing fill:#DDA0DD,stroke:#9370DB",
            "```",
        ])

        return "\n".join(lines)

    # ==================== 统计 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        bus_stats = self._message_bus.get_stats()
        return {
            **self._stats,
            "message_bus": bus_stats,
            "active_roles": len(self._role_states),
            "artifacts_flow_count": len(self._artifacts_flow),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "messages_sent": 0,
            "parallel_executions": 0,
            "artifacts_transferred": 0,
        }
        self._artifacts_flow.clear()
        self._message_bus.reset_stats()


# ==================== 便捷函数 ====================

def create_collaboration_manager(
    coordinator: WorkflowCoordinator,
    max_parallel_tasks: int = 4,
) -> RoleCollaborationManager:
    """创建角色协作管理器"""
    return RoleCollaborationManager(coordinator, max_parallel_tasks)