"""
Task Queue - 任务队列管理器

实现优先级任务队列，支持：
1. 三级优先级调度 (P0 Bug > P1 Feature > P2 Task)
2. 依赖关系检查
3. 持久化存储
4. 状态分区管理

与 TaskStateMachine 集成，提供任务调度基础。

使用示例:
    from harnessgenj.workflow.task_queue import TaskQueue, Priority, TaskQueueEntry

    queue = TaskQueue(".harnessgenj")

    # 创建任务条目
    entry = TaskQueueEntry(
        task_id="TASK-001",
        priority=Priority.P0,
        description="修复登录验证Bug",
        task_type="bug"
    )

    # 入队
    queue.enqueue(entry)

    # 获取就绪任务
    ready_tasks = queue.get_ready_tasks(completed_ids=["TASK-000"])
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import json
import os
import time
import threading
from pathlib import Path


class Priority(int, Enum):
    """任务优先级"""

    P0 = 0  # 最高优先级 - Bug修复
    P1 = 1  # 正常优先级 - 功能开发
    P2 = 2  # 低优先级 - 一般任务


class TaskQueueStatus(str, Enum):
    """队列条目状态"""

    READY = "ready"       # 就绪（依赖满足）
    BLOCKED = "blocked"   # 阻塞（依赖未满足）
    RUNNING = "running"   # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"     # 失败


class TaskQueueEntry(BaseModel):
    """任务队列条目"""

    task_id: str = Field(..., description="任务ID")
    priority: Priority = Field(default=Priority.P1, description="优先级")
    task_type: str = Field(default="task", description="任务类型: feature/bug/task")
    description: str = Field(default="", description="任务描述")
    assignee: Optional[str] = Field(default=None, description="分配的角色ID")
    dependencies: list[str] = Field(default_factory=list, description="依赖任务ID列表")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    deadline: Optional[float] = Field(default=None, description="截止时间")
    retry_count: int = Field(default=0, description="重试次数")
    max_retry: int = Field(default=3, description="最大重试次数")
    status: TaskQueueStatus = Field(default=TaskQueueStatus.READY, description="条目状态")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    def is_ready(self, completed_ids: set[str]) -> bool:
        """检查任务是否就绪（依赖已满足）"""
        if not self.dependencies:
            return True
        return all(dep_id in completed_ids for dep_id in self.dependencies)

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retry

    def increment_retry(self) -> None:
        """增加重试计数"""
        self.retry_count += 1
        self.updated_at = time.time()


class TaskQueueStats(BaseModel):
    """队列统计信息"""

    total_tasks: int = Field(default=0, description="总任务数")
    pending_by_priority: dict[str, int] = Field(default_factory=lambda: {"P0": 0, "P1": 0, "P2": 0}, description="按优先级待处理数")
    running_tasks: int = Field(default=0, description="运行中任务数")
    blocked_tasks: int = Field(default=0, description="阻塞任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    avg_wait_time: float = Field(default=0.0, description="平均等待时间(秒)")


class TaskQueue:
    """
    任务队列管理器

    功能：
    1. 优先级队列管理
    2. 依赖关系检查
    3. 持久化存储
    4. 状态追踪

    线程安全设计，支持并发访问。
    """

    # 存储文件名
    QUEUE_FILE = "task_queue.json"

    def __init__(self, storage_path: str = ".harnessgenj"):
        """
        初始化任务队列

        Args:
            storage_path: 存储目录路径
        """
        self._storage_path = Path(storage_path)
        self._lock = threading.RLock()

        # 分区队列
        self._queues: dict[Priority, list[TaskQueueEntry]] = {
            Priority.P0: [],
            Priority.P1: [],
            Priority.P2: [],
        }

        # 状态分区
        self._running: dict[str, TaskQueueEntry] = {}
        self._completed: set[str] = set()
        self._failed: dict[str, TaskQueueEntry] = {}

        # 索引
        self._entries: dict[str, TaskQueueEntry] = {}

        # 加载持久化数据
        self._load()

    def enqueue(self, entry: TaskQueueEntry) -> None:
        """
        将任务入队

        Args:
            entry: 任务队列条目
        """
        with self._lock:
            # 更新状态
            if entry.dependencies:
                # 有依赖的任务初始状态为 BLOCKED
                completed_set = self._completed
                if not entry.is_ready(completed_set):
                    entry.status = TaskQueueStatus.BLOCKED

            # 存入对应优先级队列
            self._queues[entry.priority].append(entry)
            self._entries[entry.task_id] = entry

            # 持久化
            self._persist()

    def dequeue(self) -> Optional[TaskQueueEntry]:
        """
        从队列取出最高优先级就绪任务

        Returns:
            任务条目或 None
        """
        with self._lock:
            # 按优先级顺序查找
            for priority in [Priority.P0, Priority.P1, Priority.P2]:
                queue = self._queues[priority]
                for i, entry in enumerate(queue):
                    if entry.status == TaskQueueStatus.READY and entry.is_ready(self._completed):
                        # 移出队列
                        queue.pop(i)
                        entry.status = TaskQueueStatus.RUNNING
                        self._running[entry.task_id] = entry
                        self._persist()
                        return entry
            return None

    def get_ready_tasks(self, completed_ids: Optional[list[str]] = None) -> list[TaskQueueEntry]:
        """
        获取所有就绪任务

        Args:
            completed_ids: 已完成任务ID列表（可选，默认使用内部状态）

        Returns:
            就绪任务列表（按优先级排序）
        """
        with self._lock:
            completed_set = set(completed_ids) if completed_ids else self._completed
            ready_tasks = []

            for priority in [Priority.P0, Priority.P1, Priority.P2]:
                for entry in self._queues[priority]:
                    if entry.status in [TaskQueueStatus.READY, TaskQueueStatus.BLOCKED]:
                        if entry.is_ready(completed_set):
                            entry.status = TaskQueueStatus.READY
                            ready_tasks.append(entry)

            return ready_tasks

    def get_blocked_tasks(self) -> list[TaskQueueEntry]:
        """获取所有阻塞任务"""
        with self._lock:
            blocked = []
            for priority in [Priority.P0, Priority.P1, Priority.P2]:
                for entry in self._queues[priority]:
                    if entry.status == TaskQueueStatus.BLOCKED:
                        blocked.append(entry)
            return blocked

    def mark_completed(self, task_id: str) -> bool:
        """
        标记任务完成

        Args:
            task_id: 任务ID

        Returns:
            是否成功标记
        """
        with self._lock:
            # 从运行区移除
            if task_id in self._running:
                entry = self._running.pop(task_id)
                entry.status = TaskQueueStatus.COMPLETED
                self._completed.add(task_id)
                # 更新依赖此任务的其他任务状态
                self._update_blocked_tasks()
                self._persist()
                return True

            # 可能已在队列中（未取出）
            if task_id in self._entries:
                entry = self._entries[task_id]
                entry.status = TaskQueueStatus.COMPLETED
                self._completed.add(task_id)
                # 从队列移除
                for queue in self._queues.values():
                    for i, e in enumerate(queue):
                        if e.task_id == task_id:
                            queue.pop(i)
                            break
                self._update_blocked_tasks()
                self._persist()
                return True

            return False

    def mark_failed(self, task_id: str, reason: str = "") -> bool:
        """
        标记任务失败

        Args:
            task_id: 任务ID
            reason: 失败原因

        Returns:
            是否可以重试
        """
        with self._lock:
            if task_id not in self._running:
                return False

            entry = self._running.pop(task_id)
            entry.metadata["failure_reason"] = reason
            entry.updated_at = time.time()

            if entry.can_retry():
                # 重试：放回队列
                entry.status = TaskQueueStatus.READY
                entry.increment_retry()
                self._queues[entry.priority].append(entry)
                self._persist()
                return True
            else:
                # 不再重试：标记失败
                entry.status = TaskQueueStatus.FAILED
                self._failed[task_id] = entry
                self._persist()
                return False

    def reassign(self, task_id: str, new_assignee: str) -> bool:
        """
        重新分配任务

        Args:
            task_id: 任务ID
            new_assignee: 新的角色ID

        Returns:
            是否成功重分配
        """
        with self._lock:
            if task_id not in self._entries:
                return False

            entry = self._entries[task_id]
            entry.assignee = new_assignee
            entry.updated_at = time.time()
            self._persist()
            return True

    def get_stats(self) -> TaskQueueStats:
        """获取队列统计信息"""
        with self._lock:
            stats = TaskQueueStats()

            # 统计各优先级待处理数
            for priority, queue in self._queues.items():
                pending = len([e for e in queue if e.status in [TaskQueueStatus.READY, TaskQueueStatus.BLOCKED]])
                stats.pending_by_priority[priority.name] = pending
                stats.total_tasks += pending

            stats.running_tasks = len(self._running)
            stats.blocked_tasks = len(self.get_blocked_tasks())
            stats.completed_tasks = len(self._completed)
            stats.failed_tasks = len(self._failed)

            # 计算平均等待时间
            now = time.time()
            wait_times = []
            for queue in self._queues.values():
                for entry in queue:
                    if entry.status in [TaskQueueStatus.READY, TaskQueueStatus.BLOCKED]:
                        wait_times.append(now - entry.created_at)
            if wait_times:
                stats.avg_wait_time = sum(wait_times) / len(wait_times)

            return stats

    def get_entry(self, task_id: str) -> Optional[TaskQueueEntry]:
        """获取任务条目"""
        with self._lock:
            return self._entries.get(task_id)

    def get_all_pending_ids(self) -> list[str]:
        """获取所有待处理任务ID"""
        with self._lock:
            pending = []
            for queue in self._queues.values():
                for entry in queue:
                    if entry.status in [TaskQueueStatus.READY, TaskQueueStatus.BLOCKED]:
                        pending.append(entry.task_id)
            # 包含运行中的任务
            pending.extend(self._running.keys())
            return pending

    def clear_completed(self) -> int:
        """清除已完成任务记录，返回清除数量"""
        with self._lock:
            count = len(self._completed)
            self._completed.clear()
            self._persist()
            return count

    def _update_blocked_tasks(self) -> None:
        """更新阻塞任务状态"""
        for queue in self._queues.values():
            for entry in queue:
                if entry.status == TaskQueueStatus.BLOCKED:
                    if entry.is_ready(self._completed):
                        entry.status = TaskQueueStatus.READY

    def _persist(self) -> None:
        """持久化存储"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_path / self.QUEUE_FILE

        data = {
            "queues": {
                priority.name: [entry.model_dump() for entry in queue]
                for priority, queue in self._queues.items()
            },
            "running": {task_id: entry.model_dump() for task_id, entry in self._running.items()},
            "completed": list(self._completed),
            "failed": {task_id: entry.model_dump() for task_id, entry in self._failed.items()},
            "updated_at": time.time(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载持久化数据"""
        file_path = self._storage_path / self.QUEUE_FILE

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 加载队列
            for priority_name, entries_data in data.get("queues", {}).items():
                priority = Priority[priority_name]
                self._queues[priority] = [
                    TaskQueueEntry(**entry_data) for entry_data in entries_data
                ]
                for entry in self._queues[priority]:
                    self._entries[entry.task_id] = entry

            # 加载运行中任务
            for task_id, entry_data in data.get("running", {}).items():
                entry = TaskQueueEntry(**entry_data)
                self._running[task_id] = entry
                self._entries[task_id] = entry

            # 加载已完成
            self._completed = set(data.get("completed", []))

            # 加载失败任务
            for task_id, entry_data in data.get("failed", {}).items():
                entry = TaskQueueEntry(**entry_data)
                self._failed[task_id] = entry
                self._entries[task_id] = entry

        except (json.JSONDecodeError, KeyError, TypeError):
            # 加载失败时使用空队列
            pass


def create_task_queue(storage_path: str = ".harnessgenj") -> TaskQueue:
    """创建任务队列"""
    return TaskQueue(storage_path)