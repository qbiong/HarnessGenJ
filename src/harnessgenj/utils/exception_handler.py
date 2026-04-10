"""
异常处理工具模块

提供统一的异常处理机制，避免静默吞掉错误。

使用方式：
1. 使用 safe_call 包装可能失败的调用
2. 使用 log_exception 记录异常
3. 使用 SafeContext 上下文管理器

示例：
    from harnessgenj.utils.exception_handler import safe_call, log_exception

    # 方式1：安全调用
    result = safe_call(some_function, default=None, log_error=True)

    # 方式2：手动记录
    try:
        some_operation()
    except Exception as e:
        log_exception(e, context="some_operation")
"""

import logging
import functools
from typing import Any, Callable, TypeVar

# 创建模块级日志记录器
logger = logging.getLogger("harnessgenj")

T = TypeVar('T')


def log_exception(
    exception: Exception,
    context: str = "",
    level: int = logging.WARNING,
    include_traceback: bool = False
) -> None:
    """
    记录异常信息

    Args:
        exception: 捕获的异常
        context: 上下文描述
        level: 日志级别
        include_traceback: 是否包含完整堆栈
    """
    if context:
        message = f"[{context}] {type(exception).__name__}: {exception}"
    else:
        message = f"{type(exception).__name__}: {exception}"

    if include_traceback:
        logger.log(level, message, exc_info=True)
    else:
        logger.log(level, message)


def safe_call(
    func: Callable[..., T],
    *args,
    default: Any = None,
    log_error: bool = True,
    context: str = "",
    **kwargs
) -> T | Any:
    """
    安全调用函数，捕获异常并返回默认值

    Args:
        func: 要调用的函数
        *args: 位置参数
        default: 异常时返回的默认值
        log_error: 是否记录错误
        context: 上下文描述
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            log_exception(e, context or func.__name__)
        return default


def silent_call(func: Callable[..., T], *args, **kwargs) -> T | None:
    """
    静默调用函数，不记录错误（用于非关键操作）

    Args:
        func: 要调用的函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数返回值或 None
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


def safe_operation(context: str = "", log_error: bool = True):
    """
    装饰器：为函数添加安全异常处理

    Args:
        context: 上下文描述
        log_error: 是否记录错误

    示例：
        @safe_operation(context="保存积分数据")
        def save_scores(self):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    log_exception(e, context or func.__name__)
                return None
        return wrapper
    return decorator


class SafeContext:
    """
    安全上下文管理器

    示例：
        with SafeContext("文件操作"):
            # 可能失败的操作
            file.write(content)
    """

    def __init__(self, context: str = "", log_error: bool = True):
        self.context = context
        self.log_error = log_error
        self.exception: Exception | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.exception = exc_val
            if self.log_error:
                log_exception(exc_val, self.context)
            return True  # 抑制异常
        return False


# 初始化日志配置
def init_logging(level: int = logging.WARNING) -> None:
    """
    初始化日志配置

    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # 设置 harnessgenj 日志级别
    logging.getLogger("harnessgenj").setLevel(level)