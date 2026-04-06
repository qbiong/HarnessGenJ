"""
Event Triggers - 事件驱动角色触发系统

实现事件驱动的角色激活机制，当特定事件发生时自动触发对应角色。

触发矩阵:
| 事件 | 触发角色 |
|------|----------|
| Write 完成 | CodeReviewer |
| Edit 完成 | CodeReviewer |
| 任务完成 | BugHunter, Tester |
| 安全问题发现 | CodeReviewer, BugHunter |
| 架构变更 | Architect |

使用示例:
    from harnessgenj.harness.event_triggers import EventTrigger, TriggerManager

    # 创建触发管理器
    trigger_manager = TriggerManager(harness)

    # 注册自定义触发规则
    trigger_manager.register_trigger(
        event="on_file_write",
        role_types=["code_reviewer", "bug_hunter"],
        condition=lambda ctx: ctx.get("file_path", "").endswith(".java"),
    )

    # 触发事件
    trigger_manager.trigger("on_file_write", {
        "file_path": "src/main.java",
        "content": "...",
    })

    # 处理来自 Hooks 的事件文件
    trigger_manager.process_pending_events()
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import os
import json
from pathlib import Path


class TriggerEvent(str, Enum):
    """触发事件类型"""

    # 文件操作事件
    ON_WRITE_COMPLETE = "on_write_complete"
    ON_EDIT_COMPLETE = "on_edit_complete"
    ON_FILE_CREATE = "on_file_create"
    ON_FILE_DELETE = "on_file_delete"

    # 任务事件
    ON_TASK_START = "on_task_start"
    ON_TASK_COMPLETE = "on_task_complete"
    ON_TASK_FAIL = "on_task_fail"

    # 质量事件
    ON_SECURITY_ISSUE = "on_security_issue"
    ON_BUG_FOUND = "on_bug_found"
    ON_REVIEW_FAIL = "on_review_fail"

    # 架构事件
    ON_ARCHITECTURE_CHANGE = "on_architecture_change"
    ON_API_CHANGE = "on_api_change"

    # 会话事件
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"


class TriggerRule(BaseModel):
    """触发规则"""

    id: str = Field(..., description="规则 ID")
    event: TriggerEvent = Field(..., description="触发事件")
    role_types: list[str] = Field(..., description="触发的角色类型列表")
    condition: Callable[[dict[str, Any]], bool] | None = Field(
        default=None,
        description="触发条件（可选）"
    )
    priority: int = Field(default=50, description="优先级（越高越先触发）")
    enabled: bool = Field(default=True, description="是否启用")
    async_execution: bool = Field(default=True, description="是否异步执行")
    timeout: float = Field(default=30.0, description="超时时间（秒）")

    class Config:
        arbitrary_types_allowed = True


class TriggerResult(BaseModel):
    """触发结果"""

    rule_id: str = Field(..., description="规则 ID")
    role_type: str = Field(..., description="角色类型")
    triggered: bool = Field(..., description="是否被触发")
    success: bool = Field(default=False, description="执行是否成功")
    message: str | None = Field(default=None, description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    duration: float = Field(default=0.0, description="执行耗时（秒）")
    timestamp: float = Field(default_factory=time.time, description="时间戳")


# 默认触发规则
DEFAULT_TRIGGER_RULES: list[dict[str, Any]] = [
    {
        "id": "code_review_on_write",
        "event": TriggerEvent.ON_WRITE_COMPLETE,
        "role_types": ["code_reviewer"],
        "condition": lambda ctx: ctx.get("file_path", "").endswith(
            (".java", ".kt", ".py", ".js", ".ts", ".tsx", ".go", ".rs")
        ),
        "priority": 80,
    },
    {
        "id": "code_review_on_edit",
        "event": TriggerEvent.ON_EDIT_COMPLETE,
        "role_types": ["code_reviewer"],
        "condition": lambda ctx: ctx.get("file_path", "").endswith(
            (".java", ".kt", ".py", ".js", ".ts", ".tsx", ".go", ".rs")
        ),
        "priority": 80,
    },
    {
        "id": "bug_hunter_on_task_complete",
        "event": TriggerEvent.ON_TASK_COMPLETE,
        "role_types": ["bug_hunter", "tester"],
        "condition": None,
        "priority": 70,
    },
    {
        "id": "security_review_on_issue",
        "event": TriggerEvent.ON_SECURITY_ISSUE,
        "role_types": ["code_reviewer", "bug_hunter"],
        "condition": None,
        "priority": 90,
    },
    {
        "id": "architect_on_change",
        "event": TriggerEvent.ON_ARCHITECTURE_CHANGE,
        "role_types": ["architect"],
        "condition": None,
        "priority": 60,
    },
]


class TriggerManager:
    """
    触发管理器

    管理事件触发规则，并在事件发生时触发对应的角色。

    使用示例:
        manager = TriggerManager(harness)

        # 触发文件写入完成事件
        results = manager.trigger(TriggerEvent.ON_WRITE_COMPLETE, {
            "file_path": "src/main.java",
            "content": "...",
        })
    """

    def __init__(
        self,
        harness: Any,
        max_workers: int = 4,
    ) -> None:
        """
        初始化触发管理器

        Args:
            harness: Harness 实例
            max_workers: 最大并发工作线程数
        """
        self.harness = harness
        self._rules: dict[str, TriggerRule] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: list[TriggerResult] = []
        self._lock = threading.Lock()

        # 注册默认规则
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """注册默认触发规则"""
        for rule_data in DEFAULT_TRIGGER_RULES:
            rule = TriggerRule(
                id=rule_data["id"],
                event=rule_data["event"],
                role_types=rule_data["role_types"],
                condition=rule_data.get("condition"),
                priority=rule_data.get("priority", 50),
            )
            self._rules[rule.id] = rule

    def register_trigger(
        self,
        event: TriggerEvent,
        role_types: list[str],
        rule_id: str | None = None,
        condition: Callable[[dict[str, Any]], bool] | None = None,
        priority: int = 50,
        async_execution: bool = True,
        timeout: float = 30.0,
    ) -> str:
        """
        注册触发规则

        Args:
            event: 触发事件
            role_types: 触发的角色类型列表
            rule_id: 规则 ID（可选）
            condition: 触发条件（可选）
            priority: 优先级
            async_execution: 是否异步执行
            timeout: 超时时间

        Returns:
            规则 ID
        """
        if rule_id is None:
            import uuid
            rule_id = f"rule-{uuid.uuid4().hex[:8]}"

        rule = TriggerRule(
            id=rule_id,
            event=event,
            role_types=role_types,
            condition=condition,
            priority=priority,
            async_execution=async_execution,
            timeout=timeout,
        )
        self._rules[rule_id] = rule

        return rule_id

    def unregister_trigger(self, rule_id: str) -> bool:
        """
        取消注册触发规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功取消
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def enable_trigger(self, rule_id: str) -> bool:
        """启用触发规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_trigger(self, rule_id: str) -> bool:
        """禁用触发规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def trigger(
        self,
        event: TriggerEvent,
        context: dict[str, Any],
    ) -> list[TriggerResult]:
        """
        触发事件

        Args:
            event: 触发事件
            context: 事件上下文

        Returns:
            触发结果列表
        """
        results: list[TriggerResult] = []

        # 找出匹配的规则
        matching_rules = [
            rule for rule in self._rules.values()
            if rule.event == event and rule.enabled
        ]

        # 按优先级排序
        matching_rules.sort(key=lambda r: r.priority, reverse=True)

        # 执行每个规则
        for rule in matching_rules:
            # 检查条件
            if rule.condition and not rule.condition(context):
                continue

            # 触发每个角色
            for role_type in rule.role_types:
                if rule.async_execution:
                    # 异步执行
                    future = self._executor.submit(
                        self._execute_trigger,
                        rule,
                        role_type,
                        context,
                    )
                    # 可以选择等待结果或忽略
                else:
                    # 同步执行
                    result = self._execute_trigger(rule, role_type, context)
                    results.append(result)

        # 记录结果
        with self._lock:
            self._results.extend(results)
            # 保留最近 100 条结果
            if len(self._results) > 100:
                self._results = self._results[-100:]

        return results

    def _execute_trigger(
        self,
        rule: TriggerRule,
        role_type: str,
        context: dict[str, Any],
    ) -> TriggerResult:
        """
        执行触发

        Args:
            rule: 触发规则
            role_type: 角色类型
            context: 事件上下文

        Returns:
            触发结果
        """
        start_time = time.time()
        result = TriggerResult(
            rule_id=rule.id,
            role_type=role_type,
            triggered=True,
        )

        try:
            # 获取角色
            from harnessgenj.roles import RoleType

            role_type_enum = getattr(RoleType, role_type.upper(), None)
            if role_type_enum is None:
                result.success = False
                result.error = f"Unknown role type: {role_type}"
                return result

            # 获取或创建角色
            roles = self.harness.coordinator.get_roles_by_type(role_type_enum)
            if not roles:
                # 创建角色
                role = self.harness.coordinator.create_role(
                    role_type_enum,
                    f"{role_type}_trigger",
                    role_type,
                )
            else:
                role = roles[0]

            # 发送消息到角色
            message = {
                "type": "trigger",
                "event": rule.event.value,
                "context": context,
                "timestamp": time.time(),
            }

            self.harness._collaboration.send_message(
                from_role="system",
                to_role=role.role_id,
                content=message,
            )

            # 执行角色任务
            if hasattr(role, "execute") and callable(role.execute):
                role.execute(context)

            result.success = True
            result.message = f"Successfully triggered {role_type}"

        except Exception as e:
            result.success = False
            result.error = str(e)

        result.duration = time.time() - start_time
        return result

    def get_rules(self) -> list[TriggerRule]:
        """获取所有触发规则"""
        return list(self._rules.values())

    def get_results(self, limit: int = 20) -> list[TriggerResult]:
        """
        获取触发结果

        Args:
            limit: 返回数量限制

        Returns:
            触发结果列表
        """
        with self._lock:
            return self._results[-limit:]

    def clear_results(self) -> None:
        """清除触发结果"""
        with self._lock:
            self._results.clear()

    def process_pending_events(self, workspace: str = ".harnessgenj") -> int:
        """
        处理来自 Hooks 的事件文件

        Hooks 会将事件写入 .harnessgenj/events/ 目录，
        此方法扫描并处理这些事件，然后删除已处理的事件文件。

        Args:
            workspace: 工作空间路径

        Returns:
            处理的事件数量
        """
        events_dir = Path(workspace) / "events"
        if not events_dir.exists():
            return 0

        processed = 0
        event_files = sorted(events_dir.glob("event_*.json"))

        for event_file in event_files:
            try:
                with open(event_file, "r", encoding="utf-8") as f:
                    event_data = json.load(f)

                event_type = event_data.get("type", "")
                event_context = event_data.get("data", {})

                # 映射事件类型到 TriggerEvent
                event_map = {
                    "on_write_complete": TriggerEvent.ON_WRITE_COMPLETE,
                    "on_edit_complete": TriggerEvent.ON_EDIT_COMPLETE,
                    "on_file_create": TriggerEvent.ON_FILE_CREATE,
                    "on_task_complete": TriggerEvent.ON_TASK_COMPLETE,
                    "on_security_issue": TriggerEvent.ON_SECURITY_ISSUE,
                }

                trigger_event = event_map.get(event_type)
                if trigger_event:
                    self.trigger(trigger_event, event_context)
                    processed += 1

                # 删除已处理的事件文件
                event_file.unlink()

            except Exception:
                # 处理失败，保留文件以便后续重试
                pass

        return processed


# 便捷函数
def create_trigger_manager(harness: Any) -> TriggerManager:
    """创建触发管理器"""
    return TriggerManager(harness)