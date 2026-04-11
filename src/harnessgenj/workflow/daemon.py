"""
Daemon Worker - 后台守护进程

实现持续运行的后台守护进程：
1. 持续监控任务状态
2. 健康检查和自动恢复
3. 优雅关闭
4. 与 ShutdownProtocol 集成

使用示例:
    from harnessgenj.workflow.daemon import DaemonWorker, DaemonConfig

    daemon = DaemonWorker(
        scheduler=scheduler,
        shutdown_protocol=shutdown_protocol
    )

    # 启动守护进程
    daemon.start()

    # 后台持续运行...

    # 请求关闭
    daemon.request_shutdown("需要重启服务")
"""

from typing import Any, Optional, Callable
from pydantic import BaseModel, Field
import time
import threading
import logging
from enum import Enum
import signal
import sys


class DaemonStatus(str, Enum):
    """守护进程状态"""

    INITIALIZED = "initialized"  # 已初始化
    RUNNING = "running"         # 运行中
    PAUSED = "paused"           # 暂停
    STOPPING = "stopping"       # 正在停止
    STOPPED = "stopped"         # 已停止
    ERROR = "error"             # 错误状态


class DaemonConfig(BaseModel):
    """守护进程配置"""

    scan_interval: float = Field(default=5.0, description="扫描间隔(秒)")
    max_retry: int = Field(default=3, description="最大重试次数")
    heartbeat_interval: float = Field(default=30.0, description="心跳间隔(秒)")
    shutdown_timeout: float = Field(default=30.0, description="关闭超时(秒)")
    health_check_interval: float = Field(default=60.0, description="健康检查间隔(秒)")
    auto_recovery: bool = Field(default=True, description="启用自动恢复")
    signal_handlers: bool = Field(default=True, description="启用信号处理")


class DaemonHealth(BaseModel):
    """守护进程健康状态"""

    is_healthy: bool = Field(default=True, description="是否健康")
    last_check_time: float = Field(default=0.0, description="最后检查时间")
    consecutive_errors: int = Field(default=0, description="连续错误次数")
    memory_usage: float = Field(default=0.0, description="内存使用(MB)")
    uptime: float = Field(default=0.0, description="运行时间(秒)")
    active_threads: int = Field(default=0, description="活跃线程数")


class DaemonWorker:
    """
    后台守护进程

    功能：
    1. 持续监控循环
    2. 健康检查和自动恢复
    3. 优雅关闭
    4. 信号处理

    支持作为独立进程运行或嵌入其他应用。
    """

    def __init__(
        self,
        scheduler: Optional[Any] = None,  # TaskScheduler
        shutdown_protocol: Optional[Any] = None,  # ShutdownProtocol
        config: Optional[DaemonConfig] = None,
        on_shutdown_request: Optional[Callable[[str], bool]] = None,
        on_health_check: Optional[Callable[[], DaemonHealth]] = None,
    ):
        """
        初始化守护进程

        Args:
            scheduler: 任务调度器
            shutdown_protocol: 关闭协议
            config: 守护进程配置
            on_shutdown_request: 关闭请求回调（返回是否批准）
            on_health_check: 健康检查回调
        """
        self._scheduler = scheduler
        self._shutdown_protocol = shutdown_protocol
        self._config = config or DaemonConfig()
        self._on_shutdown_request = on_shutdown_request
        self._on_health_check = on_health_check

        # 状态
        self._status = DaemonStatus.INITIALIZED
        self._health = DaemonHealth()
        self._start_time: float = 0
        self._last_heartbeat: float = 0
        self._last_health_check: float = 0

        # 线程控制
        self._lock = threading.RLock()
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._shutdown_requested = False
        self._shutdown_reason: str = ""

        # 日志
        self._logger = logging.getLogger("harnessgenj.daemon")

        # 注册信号处理
        if self._config.signal_handlers:
            self._register_signal_handlers()

    def start(self) -> None:
        """启动守护进程"""
        with self._lock:
            if self._status in [DaemonStatus.RUNNING, DaemonStatus.PAUSED]:
                return

            self._stop_event.clear()
            self._pause_event.clear()
            self._start_time = time.time()
            self._status = DaemonStatus.RUNNING
            self._health.is_healthy = True

            self._daemon_thread = threading.Thread(
                target=self._run_loop,
                name="DaemonWorker-Main",
                daemon=True
            )
            self._daemon_thread.start()

            self._logger.info(f"DaemonWorker started with config: {self._config}")

    def stop(self, timeout: Optional[float] = None) -> bool:
        """
        停止守护进程

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功停止
        """
        with self._lock:
            if self._status == DaemonStatus.STOPPED:
                return True

            self._status = DaemonStatus.STOPPING
            self._stop_event.set()

        timeout = timeout or self._config.shutdown_timeout

        if self._daemon_thread:
            self._daemon_thread.join(timeout=timeout)
            if self._daemon_thread.is_alive():
                self._logger.warning("Daemon thread did not stop gracefully")
                return False

        with self._lock:
            self._status = DaemonStatus.STOPPED
            self._health.is_healthy = False

        self._logger.info("DaemonWorker stopped")
        return True

    def pause(self) -> None:
        """暂停守护进程"""
        with self._lock:
            if self._status == DaemonStatus.RUNNING:
                self._pause_event.set()
                self._status = DaemonStatus.PAUSED
                self._logger.info("DaemonWorker paused")

    def resume(self) -> None:
        """恢复守护进程"""
        with self._lock:
            if self._status == DaemonStatus.PAUSED:
                self._pause_event.clear()
                self._status = DaemonStatus.RUNNING
                self._logger.info("DaemonWorker resumed")

    def request_shutdown(self, reason: str = "") -> bool:
        """
        请求关闭

        Args:
            reason: 关闭原因

        Returns:
            是否批准关闭
        """
        # 检查是否可以关闭
        pending_tasks: list[str] = []

        if self._scheduler:
            pending_tasks = self._scheduler.get_all_pending_tasks()

        if pending_tasks:
            self._logger.warning(f"Shutdown rejected: {len(pending_tasks)} pending tasks")
            return False

        # 执行回调
        if self._on_shutdown_request:
            approved = self._on_shutdown_request(reason)
            if not approved:
                return False

        # 设置关闭标志
        self._shutdown_requested = True
        self._shutdown_reason = reason

        # 停止守护进程
        self.stop()

        self._logger.info(f"Shutdown approved: {reason}")
        return True

    def get_status(self) -> DaemonStatus:
        """获取守护进程状态"""
        with self._lock:
            return self._status

    def get_health(self) -> DaemonHealth:
        """获取健康状态"""
        with self._lock:
            self._health.uptime = time.time() - self._start_time if self._start_time else 0
            self._health.active_threads = threading.active_count()
            return self._health

    def is_running(self) -> bool:
        """检查是否运行中"""
        return self._status == DaemonStatus.RUNNING

    def _run_loop(self) -> None:
        """守护进程主循环"""
        self._logger.info("Daemon loop started")

        while not self._stop_event.is_set():
            # 检查暂停
            while self._pause_event.is_set() and not self._stop_event.is_set():
                time.sleep(1)

            if self._stop_event.is_set():
                break

            try:
                # 执行监控循环
                self._monitor_cycle()

                # 心跳检查
                self._heartbeat()

                # 健康检查
                self._health_check_cycle()

                # 等待下次扫描
                time.sleep(self._config.scan_interval)

            except Exception as e:
                self._logger.error(f"Daemon loop error: {e}")
                self._handle_error(e)

        self._logger.info("Daemon loop stopped")

    def _monitor_cycle(self) -> None:
        """监控循环"""
        # 如果有调度器，驱动调度
        if self._scheduler:
            # 调度器自动处理任务扫描和执行
            pass  # TaskScheduler 有自己的 daemon loop

        # 检查关闭请求
        if self._shutdown_requested:
            self._logger.info(f"Shutdown requested: {self._shutdown_reason}")
            self._stop_event.set()

    def _heartbeat(self) -> None:
        """心跳检查"""
        now = time.time()
        if now - self._last_heartbeat >= self._config.heartbeat_interval:
            self._last_heartbeat = now
            self._logger.debug(f"Daemon heartbeat: status={self._status.value}, uptime={self._health.uptime:.1f}s")

    def _health_check_cycle(self) -> None:
        """健康检查循环"""
        now = time.time()
        if now - self._last_health_check >= self._config.health_check_interval:
            self._last_health_check = now

            # 执行健康检查
            health = self._do_health_check()

            with self._lock:
                self._health = health

            if not health.is_healthy:
                self._logger.warning(f"Health check failed: consecutive_errors={health.consecutive_errors}")
                if self._config.auto_recovery:
                    self._attempt_recovery()

    def _do_health_check(self) -> DaemonHealth:
        """执行健康检查"""
        health = DaemonHealth(
            last_check_time=time.time(),
            uptime=time.time() - self._start_time if self._start_time else 0,
            active_threads=threading.active_count(),
        )

        # 执行自定义健康检查
        if self._on_health_check:
            custom_health = self._on_health_check()
            if custom_health:
                health.is_healthy = custom_health.is_healthy
                health.consecutive_errors = custom_health.consecutive_errors

        # 检查调度器状态
        if self._scheduler:
            scheduler_state = self._scheduler.get_state()
            # 调度器停止则守护进程不健康
            if scheduler_state.value == "stopped":
                health.is_healthy = False

        return health

    def _handle_error(self, error: Exception) -> None:
        """处理错误"""
        with self._lock:
            self._health.consecutive_errors += 1

            if self._health.consecutive_errors >= 5:
                self._status = DaemonStatus.ERROR
                self._health.is_healthy = False

                if self._config.auto_recovery:
                    self._attempt_recovery()

    def _attempt_recovery(self) -> None:
        """尝试恢复"""
        self._logger.info("Attempting recovery...")

        # 重置错误计数
        self._health.consecutive_errors = 0

        # 如果调度器停止，尝试重启
        if self._scheduler:
            scheduler_state = self._scheduler.get_state()
            if scheduler_state.value == "stopped":
                self._scheduler.start_daemon()

        # 恢复到运行状态
        with self._lock:
            if self._status == DaemonStatus.ERROR:
                self._status = DaemonStatus.RUNNING
                self._health.is_healthy = True

        self._logger.info("Recovery completed")

    def _register_signal_handlers(self) -> None:
        """注册信号处理"""
        def handle_sigterm(signum, frame):
            self._logger.info(f"Received signal {signum}, shutting down...")
            self.request_shutdown(f"Signal {signum} received")
            sys.exit(0)

        def handle_sigint(signum, frame):
            self._logger.info(f"Received SIGINT, shutting down...")
            self.request_shutdown("SIGINT received")
            sys.exit(0)

        try:
            signal.signal(signal.SIGTERM, handle_sigterm)
            signal.signal(signal.SIGINT, handle_sigint)
        except Exception:
            # Windows 可能不支持某些信号
            pass


def create_daemon_worker(
    scheduler: Optional[Any] = None,
    shutdown_protocol: Optional[Any] = None,
    **kwargs: Any,
) -> DaemonWorker:
    """创建守护进程"""
    return DaemonWorker(scheduler, shutdown_protocol, **kwargs)