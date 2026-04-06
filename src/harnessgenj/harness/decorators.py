"""
Decorators - 便利性装饰器

提供简洁的 API 来自动记录决策和触发钩子：
- @trace_decision: 自动记录决策
- @on_task_complete: 任务完成时触发
- @on_issue_found: 发现问题时触发

使用示例:
    from harnessgenj.harness.decorators import trace_decision, on_task_complete

    @trace_decision(category="architecture", auto_log=True)
    def choose_database(requirements):
        return "PostgreSQL"

    @on_task_complete
    def my_task():
        return {"status": "done"}
"""

from typing import Any, Callable, TypeVar, Union
from functools import wraps
import time
import uuid

F = TypeVar('F', bound=Callable[..., Any])

# 全局 Harness 实例引用
_global_harness: Any = None


def set_global_harness(harness: Any) -> None:
    """设置全局 Harness 实例"""
    global _global_harness
    _global_harness = harness


def get_global_harness() -> Any | None:
    """获取全局 Harness 实例"""
    return _global_harness


def trace_decision(
    category: str = "general",
    auto_log: bool = True,
    rationale: str | None = None,
    alternatives: list[str] | None = None,
) -> Callable[[F], F]:
    """决策追踪装饰器"""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            func_name = func.__name__
            result = func(*args, **kwargs)

            decision_record = {
                "decision_id": f"DEC-{uuid.uuid4().hex[:8]}",
                "function": func_name,
                "category": category,
                "result": str(result)[:500],
                "rationale": rationale,
                "alternatives": alternatives or [],
                "timestamp": time.time(),
                "duration": time.time() - start_time,
            }

            if auto_log and _global_harness:
                try:
                    key = f"decision_{category}_{func_name}_{int(time.time())}"
                    _global_harness.memory.store_knowledge(key, decision_record, importance=70)
                    if hasattr(_global_harness, '_mark_dirty'):
                        _global_harness._mark_dirty("decision", decision_record)
                except Exception:
                    pass

            return result

        return wrapper  # type: ignore

    return decorator


def on_task_complete(
    func: F | None = None,
    *,
    hook: Callable[[dict[str, Any]], None] | None = None,
) -> Union[Callable[[F], F], F]:
    """
    任务完成钩子装饰器

    支持两种用法:
        @on_task_complete
        def my_func(): ...

        @on_task_complete(hook=lambda r: ...)
        def my_func(): ...
    """
    def actual_decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            result = fn(*args, **kwargs)

            if _global_harness:
                try:
                    task_info = {
                        "function": fn.__name__,
                        "result": result,
                        "timestamp": time.time(),
                    }

                    if hook:
                        hook(task_info)
                    else:
                        _global_harness.record(
                            f"任务完成: {fn.__name__}",
                            context="on_task_complete",
                        )
                        if hasattr(_global_harness, '_save_critical'):
                            _global_harness._save_critical('task_complete')

                except Exception:
                    pass

            return result

        return wrapper  # type: ignore

    # 直接装饰器用法
    if func is not None and callable(func):
        return actual_decorator(func)

    return actual_decorator


def on_issue_found(
    func: F | None = None,
    *,
    hook: Callable[[dict[str, Any]], None] | None = None,
) -> Union[Callable[[F], F], F]:
    """
    发现问题钩子装饰器

    支持两种用法:
        @on_issue_found
        def my_func(): ...

        @on_issue_found(hook=lambda i: ...)
        def my_func(): ...
    """
    def actual_decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            result = fn(*args, **kwargs)

            if _global_harness and result:
                try:
                    issues = []
                    if isinstance(result, dict):
                        if "issues" in result:
                            issues = result["issues"]
                        elif "error" in result:
                            issues = [{"description": result["error"]}]
                    elif isinstance(result, list):
                        issues = result

                    for issue in issues:
                        issue_info = {
                            "function": fn.__name__,
                            "issue": issue,
                            "timestamp": time.time(),
                        }

                        if hook:
                            hook(issue_info)
                        else:
                            _global_harness.memory.store_knowledge(
                                f"issue_{int(time.time())}",
                                issue_info,
                                importance=60,
                            )
                            if hasattr(_global_harness, '_save_critical'):
                                _global_harness._save_critical('issue_found')

                except Exception:
                    pass

            return result

        return wrapper  # type: ignore

    if func is not None and callable(func):
        return actual_decorator(func)

    return actual_decorator


def with_context(role: str = "developer") -> Callable[[F], F]:
    """上下文注入装饰器"""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if _global_harness:
                ctx = {
                    "project_name": _global_harness.project_name,
                    "role": role,
                    "memory": _global_harness.memory,
                    "workspace": _global_harness._workspace,
                }
                return func(ctx, *args, **kwargs)
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


class LifecycleHooks:
    """生命周期钩子管理器"""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable]] = {}

    def on(self, event: str) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].append(func)
            return func
        return decorator

    def trigger(self, event: str, data: dict[str, Any] | None = None) -> None:
        if event in self._hooks:
            for hook in self._hooks[event]:
                try:
                    hook(data or {})
                except Exception:
                    pass

    def clear(self, event: str | None = None) -> None:
        if event:
            self._hooks.pop(event, None)
        else:
            self._hooks.clear()


lifecycle_hooks = LifecycleHooks()