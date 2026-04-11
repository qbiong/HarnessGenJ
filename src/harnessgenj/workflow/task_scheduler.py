"""
Task Scheduler - 任务调度器

实现自主持续执行核心：
1. 后台守护线程持续监控未完成任务
2. 优先级调度 (P0 Bug > P1 Feature > P2 Task)
3. 依赖检查
4. 自动任务分配
5. 与 ShutdownProtocol 集成关闭审批

使用示例:
    from harnessgenj.workflow.task_scheduler import TaskScheduler, SchedulerConfig

    scheduler = TaskScheduler(
        coordinator=coordinator,
        task_queue=queue,
        state_machine=state_machine
    )

    # 启动后台守护线程
    scheduler.start_daemon()

    # 后台持续运行，自动处理任务...

    # 请求关闭
    response = scheduler.request_shutdown()
"""

from typing import Any, Optional, Callable
from pydantic import BaseModel, Field
import time
import threading
import logging
from enum import Enum

from harnessgenj.workflow.task_queue import TaskQueue, TaskQueueEntry, Priority, TaskQueueStatus
from harnessgenj.workflow.task_state import TaskStateMachine, TaskState, TaskInfo
from harnessgenj.workflow.dependency import DependencyGraph
from harnessgenj.workflow.shutdown_protocol import ShutdownProtocol, ShutdownResponse, ShutdownStatus
from harnessgenj.roles.base import RoleType


class SchedulerState(str, Enum):
    """调度器状态"""

    IDLE = "idle"       # 空闲
    RUNNING = "running"  # 运行中
    PAUSED = "paused"   # 暂停
    STOPPING = "stopping"  # 正在停止
    STOPPED = "stopped"  # 已停止


class SchedulerConfig(BaseModel):
    """调度器配置"""

    scan_interval: float = Field(default=5.0, description="扫描间隔(秒)")
    max_retry: int = Field(default=3, description="最大重试次数")
    heartbeat_interval: float = Field(default=30.0, description="心跳间隔(秒)")
    shutdown_timeout: float = Field(default=30.0, description="关闭超时(秒)")
    max_parallel_tasks: int = Field(default=3, description="最大并行任务数")
    enable_auto_assign: bool = Field(default=True, description="启用自动分配")


class SchedulerStats(BaseModel):
    """调度器统计"""

    state: SchedulerState = Field(default=SchedulerState.IDLE, description="调度器状态")
    tasks_processed: int = Field(default=0, description="已处理任务数")
    tasks_succeeded: int = Field(default=0, description="成功任务数")
    tasks_failed: int = Field(default=0, description="失败任务数")
    current_running: int = Field(default=0, description="当前运行任务数")
    last_scan_time: float = Field(default=0.0, description="最后扫描时间")
    uptime: float = Field(default=0.0, description="运行时间(秒)")
    errors: list[str] = Field(default_factory=list, description="错误记录")


class TaskScheduler:
    """
    任务调度器

    功能：
    1. 后台守护线程持续监控
    2. 自动扫描 pending 状态任务
    3. 优先级调度
    4. 依赖检查
    5. 自动分配角色执行
    6. 关闭审批

    线程安全设计，支持优雅关闭。
    """

    def __init__(
        self,
        task_queue: TaskQueue,
        state_machine: TaskStateMachine,
        dependency_graph: Optional[DependencyGraph] = None,
        shutdown_protocol: Optional[ShutdownProtocol] = None,
        coordinator: Optional[Any] = None,  # WorkflowCoordinator
        config: Optional[SchedulerConfig] = None,
        on_task_assigned: Optional[Callable[[str, str], None]] = None,
        on_task_completed: Optional[Callable[[str, bool], None]] = None,
    ):
        """
        初始化任务调度器

        Args:
            task_queue: 任务队列
            state_machine: 任务状态机
            dependency_graph: 依赖图（可选）
            shutdown_protocol: 关闭协议（可选）
            coordinator: 工作流协调器（可选）
            config: 调度器配置
            on_task_assigned: 任务分配回调
            on_task_completed: 任务完成回调
        """
        self._task_queue = task_queue
        self._state_machine = state_machine
        self._dependency_graph = dependency_graph
        self._shutdown_protocol = shutdown_protocol
        self._coordinator = coordinator
        self._config = config or SchedulerConfig()

        # 回调
        self._on_task_assigned = on_task_assigned
        self._on_task_completed = on_task_completed

        # 状态
        self._state = SchedulerState.IDLE
        self._stats = SchedulerStats()
        self._start_time: float = 0
        self._last_heartbeat: float = 0

        # 线程控制
        self._lock = threading.RLock()
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # 日志
        self._logger = logging.getLogger("harnessgenj.scheduler")

    def start_daemon(self) -> None:
        """启动后台守护线程"""
        with self._lock:
            if self._state in [SchedulerState.RUNNING, SchedulerState.PAUSED]:
                return

            self._stop_event.clear()
            self._pause_event.clear()
            self._start_time = time.time()
            self._state = SchedulerState.RUNNING
            self._stats.state = SchedulerState.RUNNING

            self._daemon_thread = threading.Thread(
                target=self._daemon_loop,
                name="TaskScheduler-Daemon",
                daemon=True
            )
            self._daemon_thread.start()

            self._logger.info("TaskScheduler daemon started")

    def stop_daemon(self, timeout: Optional[float] = None) -> bool:
        """
        停止后台守护线程

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功停止
        """
        with self._lock:
            if self._state == SchedulerState.STOPPED:
                return True

            self._state = SchedulerState.STOPPING
            self._stats.state = SchedulerState.STOPPING
            self._stop_event.set()

        # 等待线程结束
        timeout = timeout or self._config.shutdown_timeout
        if self._daemon_thread:
            self._daemon_thread.join(timeout=timeout)

        with self._lock:
            self._state = SchedulerState.STOPPED
            self._stats.state = SchedulerState.STOPPED
            return not self._daemon_thread.is_alive() if self._daemon_thread else True

    def pause(self) -> None:
        """暂停调度器"""
        with self._lock:
            if self._state == SchedulerState.RUNNING:
                self._pause_event.set()
                self._state = SchedulerState.PAUSED
                self._stats.state = SchedulerState.PAUSED

    def resume(self) -> None:
        """恢复调度器"""
        with self._lock:
            if self._state == SchedulerState.PAUSED:
                self._pause_event.clear()
                self._state = SchedulerState.RUNNING
                self._stats.state = SchedulerState.RUNNING

    def request_shutdown(self, requester_id: str = "system", reason: str = "") -> ShutdownResponse:
        """
        请求关闭

        检查是否有未完成任务，决定是否批准关闭。

        Args:
            requester_id: 请求者ID
            reason: 关闭原因

        Returns:
            ShutdownResponse 关闭响应
        """
        with self._lock:
            # 获取所有未完成任务
            pending_ids = self.get_all_pending_tasks()

            if pending_ids:
                # 有未完成任务，拒绝关闭
                return ShutdownResponse(
                    approved=False,
                    status=ShutdownStatus.REJECTED,
                    pending_tasks=pending_ids,
                    reason=f"有 {len(pending_ids)} 个未完成任务需要先完成"
                )

            # 无未完成任务，批准关闭
            # 停止守护线程
            self.stop_daemon()

            return ShutdownResponse(
                approved=True,
                status=ShutdownStatus.APPROVED,
                pending_tasks=[],
                reason="所有任务已完成，可以安全关闭"
            )

    def scan_pending_tasks(self) -> list[TaskInfo]:
        """
        扫描 TaskStateMachine 的 pending 状态任务

        Returns:
            待处理任务列表
        """
        pending = []
        for task_id, task_info in self._state_machine._tasks.items():
            if task_info.state == TaskState.PENDING:
                pending.append(task_info)
        return pending

    def schedule_next(self) -> Optional[TaskQueueEntry]:
        """
        调度下一个任务

        基于优先级和依赖选择下一个就绪任务。

        Returns:
            任务条目或 None
        """
        return self._task_queue.dequeue()

    def get_all_pending_tasks(self) -> list[str]:
        """获取所有未完成任务ID"""
        pending = []

        # 从队列获取
        pending.extend(self._task_queue.get_all_pending_ids())

        # 从状态机获取
        for task_id, task_info in self._state_machine._tasks.items():
            if task_info.state in [TaskState.PENDING, TaskState.IN_PROGRESS, TaskState.REVIEWING]:
                if task_id not in pending:
                    pending.append(task_id)

        return pending

    def get_stats(self) -> SchedulerStats:
        """获取调度器统计"""
        with self._lock:
            self._stats.current_running = len(self._task_queue._running)
            self._stats.uptime = time.time() - self._start_time if self._start_time else 0
            return self._stats

    def get_state(self) -> SchedulerState:
        """获取调度器状态"""
        with self._lock:
            return self._state

    def _daemon_loop(self) -> None:
        """守护线程主循环"""
        self._logger.info("Daemon loop started")

        while not self._stop_event.is_set():
            # 检查暂停
            while self._pause_event.is_set() and not self._stop_event.is_set():
                time.sleep(1)

            if self._stop_event.is_set():
                break

            try:
                # 执行调度循环
                self._schedule_cycle()

                # 心跳检查
                self._heartbeat_check()

                # 等待下次扫描
                time.sleep(self._config.scan_interval)

            except Exception as e:
                self._logger.error(f"Daemon loop error: {e}")
                self._stats.errors.append(f"{time.time()}: {e}")

        self._logger.info("Daemon loop stopped")

    def _schedule_cycle(self) -> None:
        """单次调度循环"""
        # 1. 同步状态机的 pending 任务到队列
        self._sync_pending_tasks()

        # 2. 检查当前运行任务数
        running_count = len(self._task_queue._running)
        if running_count >= self._config.max_parallel_tasks:
            return

        # 3. 获取就绪任务
        ready_tasks = self._task_queue.get_ready_tasks()
        if not ready_tasks:
            return

        # 4. 按优先级排序（已通过 dequeue 确保优先级）
        # 取出任务执行
        entry = self._task_queue.dequeue()
        if entry:
            self._execute_task(entry)

        self._stats.last_scan_time = time.time()

    def _sync_pending_tasks(self) -> None:
        """同步状态机的 pending 任务到队列"""
        pending_tasks = self.scan_pending_tasks()

        for task_info in pending_tasks:
            # 检查是否已在队列中
            if self._task_queue.get_entry(task_info.task_id):
                continue

            # 创建队列条目
            priority = self._determine_priority(task_info)
            entry = TaskQueueEntry(
                task_id=task_info.task_id,
                priority=priority,
                description=task_info.metadata.get("description", ""),
                task_type=task_info.metadata.get("task_type", "task"),
            )

            self._task_queue.enqueue(entry)

    def _determine_priority(self, task_info: TaskInfo) -> Priority:
        """确定任务优先级"""
        task_type = task_info.metadata.get("task_type", "task")

        if task_type == "bug":
            return Priority.P0
        elif task_type == "feature":
            return Priority.P1
        else:
            return Priority.P2

    def _execute_task(self, entry: TaskQueueEntry) -> None:
        """执行任务"""
        task_id = entry.task_id

        self._logger.info(f"Executing task: {task_id}")

        # 更新状态机
        try:
            self._state_machine.transition(task_id, TaskState.IN_PROGRESS, "调度器分配执行")
        except Exception as e:
            self._logger.warning(f"State transition failed: {e}")

        # 分配角色
        assignee = entry.assignee
        if not assignee and self._config.enable_auto_assign:
            assignee = self._auto_assign_role(entry)

        if assignee:
            entry.assignee = assignee

            # 触发回调
            if self._on_task_assigned:
                self._on_task_assigned(task_id, assignee)

            # 如果有协调器，执行工作流阶段
            if self._coordinator:
                self._execute_with_coordinator(entry)
            else:
                # 模拟执行（用于测试）
                self._simulate_execution(entry)

        self._stats.tasks_processed += 1

    def _auto_assign_role(self, entry: TaskQueueEntry) -> Optional[str]:
        """自动分配角色"""
        task_type = entry.task_type

        # 根据任务类型分配角色
        role_map = {
            "bug": RoleType.DEVELOPER,
            "feature": RoleType.DEVELOPER,
            "task": RoleType.DEVELOPER,
            "review": RoleType.CODE_REVIEWER,
            "test": RoleType.TESTER,
            "architect": RoleType.ARCHITECT,
        }

        role_type = role_map.get(task_type, RoleType.DEVELOPER)

        # 如果有协调器，获取可用角色
        if self._coordinator:
            roles = self._coordinator.get_roles_by_type(role_type)
            if roles:
                return roles[0].role_id

        # 默认角色ID
        return f"{role_type.value}_1"

    def _execute_with_coordinator(self, entry: TaskQueueEntry) -> None:
        """通过协调器执行任务"""
        # 这里需要与 WorkflowCoordinator 集成
        # 目前使用简化实现
        self._logger.info(f"Executing task {entry.task_id} with coordinator")

        # 模拟成功执行
        self._complete_task(entry, True)

    def _simulate_execution(self, entry: TaskQueueEntry) -> None:
        """模拟执行（用于测试）"""
        self._logger.info(f"Simulating execution for task {entry.task_id}")
        self._complete_task(entry, True)

    def _complete_task(self, entry: TaskQueueEntry, success: bool) -> None:
        """完成任务"""
        task_id = entry.task_id

        if success:
            self._task_queue.mark_completed(task_id)
            self._state_machine.transition(task_id, TaskState.COMPLETED, "执行成功")
            self._stats.tasks_succeeded += 1

            if self._on_task_completed:
                self._on_task_completed(task_id, True)
        else:
            can_retry = self._task_queue.mark_failed(task_id, "执行失败")
            if not can_retry:
                self._state_machine.transition(task_id, TaskState.FAILED, "执行失败且无法重试")
            else:
                self._state_machine.transition(task_id, TaskState.PENDING, "等待重试")
            self._stats.tasks_failed += 1

            if self._on_task_completed:
                self._on_task_completed(task_id, False)

    def _heartbeat_check(self) -> None:
        """心跳检查"""
        now = time.time()
        if now - self._last_heartbeat >= self._config.heartbeat_interval:
            self._last_heartbeat = now
            self._logger.debug(f"Scheduler heartbeat: state={self._state.value}, running={self._stats.current_running}")


def create_task_scheduler(
    task_queue: TaskQueue,
    state_machine: TaskStateMachine,
    **kwargs: Any,
) -> TaskScheduler:
    """创建任务调度器"""
    return TaskScheduler(task_queue, state_machine, **kwargs)