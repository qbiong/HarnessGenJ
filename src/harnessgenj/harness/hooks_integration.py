"""
Hooks Integration - Hooks 集成层

将 Hooks 系统集成到 Harness 工作流中：
- 任务执行前检查 (Pre-Hooks)
- 任务执行后检查 (Post-Hooks)
- 安全检查 (Security-Hooks)
- 验证检查 (Validation-Hooks)

使用示例:
    from harnessgenj.harness.hooks_integration import HooksIntegration, HooksConfig

    # 创建配置
    config = HooksConfig(
        enabled=True,
        blocking_mode=True,
        pre_hooks=["code_lint", "security"],
        post_hooks=["test_pass", "format"],
    )

    # 创建集成实例
    integration = HooksIntegration(config)

    # 执行前置检查
    result = integration.run_pre_task({"code": source_code})
    if not result.passed:
        print(f"被阻塞: {result.blocked_by}")
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time

from harnessgenj.harness.hooks import (
    HooksManager,
    BaseHook,
    HookType,
    HookMode,
    HookResult,
    HooksResult,
    CodeLintHook,
    SecurityHook,
    ValidationHook,
    TestPassHook,
    FormatHook,
    create_default_hooks,
)


class HooksConfig(BaseModel):
    """Hooks 配置"""

    enabled: bool = Field(default=True, description="是否启用 Hooks")
    blocking_mode: bool = Field(default=True, description="是否阻塞模式")
    pre_hooks: list[str] = Field(
        default_factory=lambda: ["code_lint", "security"],
        description="前置 Hooks 列表",
    )
    post_hooks: list[str] = Field(
        default_factory=lambda: ["test_pass", "format"],
        description="后置 Hooks 列表",
    )
    security_hooks: list[str] = Field(
        default_factory=lambda: ["security"],
        description="安全 Hooks 列表",
    )
    validation_hooks: list[str] = Field(
        default_factory=lambda: ["validation"],
        description="验证 Hooks 列表",
    )
    timeout_seconds: float = Field(default=30.0, description="Hook 执行超时时间")
    max_retries: int = Field(default=1, description="失败重试次数")


class HookEventType(Enum):
    """Hook 事件类型"""

    PRE_TASK = "pre_task"
    POST_TASK = "post_task"
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    PRE_DEVELOP = "pre_develop"
    POST_DEVELOP = "post_develop"
    SECURITY_CHECK = "security_check"
    VALIDATION = "validation"


class HooksIntegration:
    """
    Hooks 集成层

    将 HooksManager 的能力集成到 Harness 工作流中，
    提供统一的检查接口和结果处理。
    """

    def __init__(
        self,
        config: HooksConfig | None = None,
        hooks_manager: HooksManager | None = None,
        on_blocked: Callable[[HooksResult], None] | None = None,
        on_warning: Callable[[list[str]], None] | None = None,
    ) -> None:
        """
        初始化 Hooks 集成层

        Args:
            config: Hooks 配置
            hooks_manager: Hooks 管理器（可选，默认创建默认）
            on_blocked: 被阻塞时的回调
            on_warning: 有警告时的回调
        """
        self.config = config or HooksConfig()
        self._hooks = hooks_manager or create_default_hooks()
        self._on_blocked = on_blocked
        self._on_warning = on_warning
        self._stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "blocked_checks": 0,
            "total_warnings": 0,
        }

    # ==================== Hooks 管理 ====================

    def register_hook(self, hook: BaseHook) -> None:
        """注册自定义 Hook"""
        self._hooks.register(hook)

    def unregister_hook(self, name: str) -> bool:
        """注销 Hook"""
        return self._hooks.unregister(name)

    def get_hook(self, name: str) -> BaseHook | None:
        """获取 Hook"""
        return self._hooks.get_hook(name)

    def list_hooks(self) -> list[dict[str, Any]]:
        """列出所有 Hooks"""
        return self._hooks.list_hooks()

    def enable_hooks(self) -> None:
        """启用 Hooks"""
        self.config.enabled = True

    def disable_hooks(self) -> None:
        """禁用 Hooks"""
        self.config.enabled = False

    # ==================== 检查执行 ====================

    def run_pre_task(self, context: dict[str, Any]) -> HooksResult:
        """
        执行任务前置检查

        检查内容：
        - 代码 Lint
        - 安全检查

        Args:
            context: 检查上下文，包含 code, file_path 等

        Returns:
            HooksResult: 检查结果
        """
        if not self.config.enabled:
            return HooksResult(passed=True, results=[])

        start_time = time.time()
        self._stats["total_checks"] += 1

        # 执行前置检查
        result = self._hooks.run_pre_hooks(context)

        # 处理结果
        self._handle_result(result, "pre_task")

        result_dict = result.model_dump()
        result_dict["duration"] = time.time() - start_time

        return result

    def run_post_task(self, context: dict[str, Any]) -> HooksResult:
        """
        执行任务后置检查

        检查内容：
        - 测试通过检查
        - 格式检查

        Args:
            context: 检查上下文，包含 test_results, output 等

        Returns:
            HooksResult: 检查结果
        """
        if not self.config.enabled:
            return HooksResult(passed=True, results=[])

        start_time = time.time()
        self._stats["total_checks"] += 1

        # 执行后置检查
        result = self._hooks.run_post_hooks(context)

        # 处理结果
        self._handle_result(result, "post_task")

        result_dict = result.model_dump()
        result_dict["duration"] = time.time() - start_time

        return result

    def run_security_check(self, context: dict[str, Any]) -> HooksResult:
        """
        执行安全检查

        专门用于对抗性开发前的安全预检

        Args:
            context: 检查上下文，包含 code, file_path 等

        Returns:
            HooksResult: 检查结果
        """
        if not self.config.enabled:
            return HooksResult(passed=True, results=[])

        self._stats["total_checks"] += 1

        result = self._hooks.run_security_hooks(context)
        self._handle_result(result, "security_check")

        return result

    def run_validation(self, context: dict[str, Any]) -> HooksResult:
        """
        执行数据验证

        用于验证输入/输出数据格式

        Args:
            context: 检查上下文，包含 data, required_fields 等

        Returns:
            HooksResult: 检查结果
        """
        if not self.config.enabled:
            return HooksResult(passed=True, results=[])

        self._stats["total_checks"] += 1

        result = self._hooks.run_validation_hooks(context)
        self._handle_result(result, "validation")

        return result

    def run_all(self, context: dict[str, Any]) -> HooksResult:
        """
        执行所有 Hooks

        按顺序执行：Security → Validation → Pre → Post

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        if not self.config.enabled:
            return HooksResult(passed=True, results=[])

        self._stats["total_checks"] += 1

        result = self._hooks.run_all_hooks(context)
        self._handle_result(result, "all")

        return result

    # ==================== 结果处理 ====================

    def _handle_result(self, result: HooksResult, event_type: str) -> None:
        """处理检查结果"""
        if result.passed:
            self._stats["passed_checks"] += 1
        else:
            self._stats["blocked_checks"] += 1
            if self._on_blocked:
                self._on_blocked(result)

        # 处理警告
        if result.total_warnings > 0:
            self._stats["total_warnings"] += result.total_warnings
            if self._on_warning:
                warnings = []
                for r in result.results:
                    warnings.extend(r.warnings)
                self._on_warning(warnings)

    # ==================== 统计 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "hooks_enabled": self.config.enabled,
            "blocking_mode": self.config.blocking_mode,
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "blocked_checks": 0,
            "total_warnings": 0,
        }

    # ==================== 便捷方法 ====================

    def check_code(self, code: str, file_path: str = "") -> HooksResult:
        """
        快速代码检查

        结合 Lint 和 Security 检查

        Args:
            code: 源代码
            file_path: 文件路径

        Returns:
            HooksResult: 检查结果
        """
        return self.run_pre_task({
            "code": code,
            "file_path": file_path,
        })

    def check_test_results(
        self,
        passed: int,
        failed: int,
        coverage: float = 0,
        failures: list[str] | None = None,
    ) -> HooksResult:
        """
        快速测试结果检查

        Args:
            passed: 通过测试数
            failed: 失败测试数
            coverage: 覆盖率
            failures: 失败详情

        Returns:
            HooksResult: 检查结果
        """
        return self.run_post_task({
            "test_results": {
                "passed": passed,
                "failed": failed,
                "coverage": coverage,
                "failures": failures or [],
            }
        })

    def validate_data(
        self,
        data: dict[str, Any],
        required_fields: list[str] | None = None,
        field_types: dict[str, type] | None = None,
    ) -> HooksResult:
        """
        快速数据验证

        Args:
            data: 待验证数据
            required_fields: 必需字段
            field_types: 字段类型映射

        Returns:
            HooksResult: 验证结果
        """
        # 创建临时验证 Hook
        validation_hook = ValidationHook(
            required_fields=required_fields or [],
            field_types=field_types or {},
        )

        # 临时注册并执行
        original_hooks = self._hooks._hooks.copy()
        self._hooks.register(validation_hook)
        result = self.run_validation({"data": data})

        # 恢复原始状态
        self._hooks._hooks = original_hooks

        return result


class HooksIntegrationBuilder:
    """
    Hooks 集成层构建器

    提供流畅的 API 来配置和创建 HooksIntegration
    """

    def __init__(self) -> None:
        self._config = HooksConfig()
        self._hooks_manager: HooksManager | None = None
        self._on_blocked: Callable[[HooksResult], None] | None = None
        self._on_warning: Callable[[list[str]], None] | None = None

    def enabled(self, enabled: bool = True) -> "HooksIntegrationBuilder":
        """设置是否启用"""
        self._config.enabled = enabled
        return self

    def blocking(self, blocking: bool = True) -> "HooksIntegrationBuilder":
        """设置阻塞模式"""
        self._config.blocking_mode = blocking
        return self

    def with_pre_hooks(self, hooks: list[str]) -> "HooksIntegrationBuilder":
        """设置前置 Hooks"""
        self._config.pre_hooks = hooks
        return self

    def with_post_hooks(self, hooks: list[str]) -> "HooksIntegrationBuilder":
        """设置后置 Hooks"""
        self._config.post_hooks = hooks
        return self

    def with_timeout(self, seconds: float) -> "HooksIntegrationBuilder":
        """设置超时时间"""
        self._config.timeout_seconds = seconds
        return self

    def with_hooks_manager(self, manager: HooksManager) -> "HooksIntegrationBuilder":
        """设置 Hooks 管理器"""
        self._hooks_manager = manager
        return self

    def on_blocked(self, callback: Callable[[HooksResult], None]) -> "HooksIntegrationBuilder":
        """设置阻塞回调"""
        self._on_blocked = callback
        return self

    def on_warning(self, callback: Callable[[list[str]], None]) -> "HooksIntegrationBuilder":
        """设置警告回调"""
        self._on_warning = callback
        return self

    def build(self) -> HooksIntegration:
        """构建 HooksIntegration 实例"""
        return HooksIntegration(
            config=self._config,
            hooks_manager=self._hooks_manager,
            on_blocked=self._on_blocked,
            on_warning=self._on_warning,
        )


# ==================== 便捷函数 ====================

def create_hooks_integration(
    enabled: bool = True,
    blocking_mode: bool = True,
    pre_hooks: list[str] | None = None,
    post_hooks: list[str] | None = None,
) -> HooksIntegration:
    """
    创建 HooksIntegration 实例

    Args:
        enabled: 是否启用
        blocking_mode: 是否阻塞模式
        pre_hooks: 前置 Hooks
        post_hooks: 后置 Hooks

    Returns:
        HooksIntegration 实例
    """
    config = HooksConfig(
        enabled=enabled,
        blocking_mode=blocking_mode,
        pre_hooks=pre_hooks or ["code_lint", "security"],
        post_hooks=post_hooks or ["test_pass", "format"],
    )
    return HooksIntegration(config)