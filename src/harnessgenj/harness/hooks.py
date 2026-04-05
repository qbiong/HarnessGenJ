"""
Hooks 系统 - Harness 核心能力

类比 CI/CD 的 Quality Gates:
- 确定性规则约束概率性模型输出
- 执行前/后的质量检查
- 可插拔的检查规则
- 支持阻塞和非阻塞两种模式

Hook 类型:
1. Pre-Hooks: 执行前检查（如代码格式验证）
2. Post-Hooks: 执行后检查（如测试通过验证）
3. Validation-Hooks: 数据验证
4. Security-Hooks: 安全检查

使用示例:
    hooks = HooksManager()

    # 注册代码检查 Hook
    hooks.register_pre_hook("lint", CodeLintHook())

    # 注册安全检查 Hook
    hooks.register_pre_hook("security", SecurityHook())

    # 执行前检查
    result = hooks.run_pre_hooks(code)
    if not result.passed:
        raise Exception(result.errors)
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time


class HookType(Enum):
    """Hook 类型"""

    PRE = "pre"           # 执行前检查
    POST = "post"         # 执行后检查
    VALIDATION = "validation"  # 数据验证
    SECURITY = "security"      # 安全检查


class HookMode(Enum):
    """Hook 模式"""

    BLOCKING = "blocking"     # 阻塞模式：失败时阻止执行
    NON_BLOCKING = "non_blocking"  # 非阻塞模式：仅记录警告


class HookResult(BaseModel):
    """Hook 执行结果"""

    hook_name: str = Field(..., description="Hook 名称")
    passed: bool = Field(..., description="是否通过")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    execution_time: float = Field(default=0.0, description="执行时间(秒)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class HooksResult(BaseModel):
    """多个 Hook 的汇总结果"""

    passed: bool = Field(..., description="是否全部通过")
    results: list[HookResult] = Field(default_factory=list, description="各 Hook 结果")
    total_errors: int = Field(default=0, description="总错误数")
    total_warnings: int = Field(default=0, description="总警告数")
    blocked_by: str | None = Field(default=None, description="阻塞的 Hook 名称")


class BaseHook:
    """
    Hook 基类

    所有 Hook 都需要继承此基类并实现 check 方法
    """

    name: str = "base_hook"
    hook_type: HookType = HookType.PRE
    mode: HookMode = HookMode.BLOCKING
    priority: int = 50  # 执行优先级 (0-100，越高越先执行)

    def check(self, context: dict[str, Any]) -> HookResult:
        """
        执行检查

        Args:
            context: 检查上下文

        Returns:
            HookResult: 检查结果
        """
        raise NotImplementedError

    def _create_result(self, passed: bool, errors: list[str] | None = None, warnings: list[str] | None = None) -> HookResult:
        """创建结果的辅助方法"""
        return HookResult(
            hook_name=self.name,
            passed=passed,
            errors=errors or [],
            warnings=warnings or [],
        )


class CodeLintHook(BaseHook):
    """
    代码 Lint 检查 Hook

    检查代码是否符合规范
    """

    name = "code_lint"
    hook_type = HookType.PRE
    mode = HookMode.BLOCKING
    priority = 80

    # 禁止的模式
    FORBIDDEN_PATTERNS = [
        "eval(",
        "exec(",
        "__import__",
        "import os.system",
        "import subprocess",
    ]

    # 必须的模式（对于某些文件）
    REQUIRED_PATTERNS: dict[str, list[str]] = {}

    def check(self, context: dict[str, Any]) -> HookResult:
        """检查代码"""
        code = context.get("code", "")
        if not code:
            return self._create_result(True)

        errors = []
        warnings = []

        # 检查禁止的模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in code:
                errors.append(f"发现禁止的模式: {pattern}")

        # 检查基本语法（简化实现）
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            errors.append(f"语法错误: {e.msg} (行 {e.lineno})")

        # 检查长度警告
        if len(code) > 10000:
            warnings.append(f"代码过长 ({len(code)} 字符)，建议拆分")

        return self._create_result(len(errors) == 0, errors, warnings)


class SecurityHook(BaseHook):
    """
    安全检查 Hook

    检查代码安全性问题，支持多语言 (Python, Java, Kotlin, JavaScript, TypeScript)
    """

    name = "security"
    hook_type = HookType.SECURITY
    mode = HookMode.BLOCKING
    priority = 90

    # 多语言敏感信息模式
    LANGUAGE_PATTERNS = {
        "python": {
            "sensitive": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'credential\s*=\s*["\'][^"\']+["\']',
            ],
            "high_risk": ["password", "api_key", "secret", "token", "credential"],
        },
        "java": {
            "sensitive": [
                r'String\s+(password|apiKey|secret|token)\s*=\s*"[^"]+"',
                r'private\s+String\s+\w*[Pp]assword\w*\s*=\s*"[^"]+"',
                r'private\s+String\s+\w*[Tt]oken\w*\s*=\s*"[^"]+"',
                r'@Value\s*\(["\'][^"\']*(password|secret|token|key)["\']',
            ],
            "high_risk": ["password", "apiKey", "secret", "token", "credential"],
        },
        "kotlin": {
            "sensitive": [
                r'val\s+(password|apiKey|secret|token)\s*=\s*"[^"]+"',
                r'private\s+val\s+\w*[Pp]assword\w*\s*=',
                r'private\s+val\s+\w*[Tt]oken\w*\s*=',
                r'const\s+val\s+\w*[Kk]ey\w*\s*=\s*"[^"]+"',
            ],
            "high_risk": ["password", "apiKey", "secret", "token", "credential"],
        },
        "javascript": {
            "sensitive": [
                r'(const|let|var)\s+(password|apiKey|secret|token)\s*=\s*["\'][^"\']+["\']',
                r'process\.env\.\w*(PASSWORD|SECRET|TOKEN|KEY)',
            ],
            "high_risk": ["password", "apiKey", "secret", "token", "credential", "PRIVATE_KEY"],
        },
        "typescript": {
            "sensitive": [
                r'(const|let|var)\s+(password|apiKey|secret|token)\s*:\s*string\s*=\s*["\'][^"\']+["\']',
                r'process\.env\.\w*(PASSWORD|SECRET|TOKEN|KEY)',
            ],
            "high_risk": ["password", "apiKey", "secret", "token", "credential"],
        },
    }

    # 通用高危模式（所有语言）
    HIGH_RISK_PATTERNS = [
        "password",
        "secret",
        "api_key",
        "token",
        "credential",
        "private_key",
    ]

    # 默认敏感信息模式（向后兼容）
    SENSITIVE_PATTERNS = [
        r'password\s*=\s*"[^"]+"',
        r'api_key\s*=\s*"[^"]+"',
        r'secret\s*=\s*"[^"]+"',
    ]

    def __init__(self, language: str = "python") -> None:
        """
        初始化安全检查 Hook

        Args:
            language: 目标语言 (python, java, kotlin, javascript, typescript)
        """
        self.language = language.lower()

    def detect_language(self, file_path: str) -> str:
        """
        根据文件扩展名检测语言

        Args:
            file_path: 文件路径

        Returns:
            语言名称
        """
        import os
        ext_map = {
            ".py": "python",
            ".java": "java",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        return ext_map.get(ext, self.language)

    def check(self, context: dict[str, Any]) -> HookResult:
        """检查安全性"""
        import re
        import os

        code = context.get("code", "")
        content = context.get("content", "")
        file_path = context.get("file_path", context.get("path", ""))

        target = code or content
        if not target:
            return self._create_result(True)

        errors = []
        warnings = []

        # 检测语言
        detected_lang = self.detect_language(file_path)

        # 获取该语言的敏感模式
        lang_patterns = self.LANGUAGE_PATTERNS.get(detected_lang, self.LANGUAGE_PATTERNS["python"])

        # 检查语言特定的硬编码敏感信息
        for pattern in lang_patterns["sensitive"]:
            try:
                if re.search(pattern, target, re.IGNORECASE | re.MULTILINE):
                    errors.append(f"[{detected_lang}] 发现硬编码敏感信息: {pattern}")
            except re.error:
                pass

        # 检查高危关键词
        for keyword in lang_patterns["high_risk"]:
            if keyword.lower() in target.lower():
                # 检查是否有赋值语句
                if "=" in target or ":" in target:
                    warnings.append(f"可能包含敏感信息: {keyword}")

        # 检查通用危险模式
        for pattern in self.HIGH_RISK_PATTERNS:
            if pattern.lower() in target.lower():
                # 检查是否在注释中
                lines = target.split('\n')
                for i, line in enumerate(lines):
                    if pattern.lower() in line.lower():
                        # 简单判断是否在注释中
                        stripped = line.strip()
                        if not stripped.startswith('#') and not stripped.startswith('//') and not stripped.startswith('*'):
                            if '=' in line or ':' in line:
                                warnings.append(f"第 {i+1} 行: 可能包含敏感配置 '{pattern}'")

        return self._create_result(len(errors) == 0, errors, warnings)


class ValidationHook(BaseHook):
    """
    数据验证 Hook

    验证输入/输出数据格式
    """

    name = "validation"
    hook_type = HookType.VALIDATION
    mode = HookMode.BLOCKING
    priority = 70

    def __init__(
        self,
        required_fields: list[str] | None = None,
        field_types: dict[str, type] | None = None,
    ) -> None:
        self.required_fields = required_fields or []
        self.field_types = field_types or {}

    def check(self, context: dict[str, Any]) -> HookResult:
        """验证数据"""
        data = context.get("data", {})
        if not data and self.required_fields:
            return self._create_result(False, ["数据为空"])

        errors = []
        warnings = []

        # 检查必需字段
        for field in self.required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")

        # 检查字段类型
        for field, expected_type in self.field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                errors.append(f"字段 {field} 类型错误: 期望 {expected_type}, 实际 {type(data[field])}")

        return self._create_result(len(errors) == 0, errors, warnings)


class TestPassHook(BaseHook):
    """
    测试通过检查 Hook

    检查测试是否通过
    """

    name = "test_pass"
    hook_type = HookType.POST
    mode = HookMode.BLOCKING
    priority = 85

    def check(self, context: dict[str, Any]) -> HookResult:
        """检查测试结果"""
        test_results = context.get("test_results", {})
        if not test_results:
            return self._create_result(True, warnings=["没有测试结果"])

        errors = []
        warnings = []

        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        total = passed + failed

        if failed > 0:
            errors.append(f"测试失败: {failed}/{total}")
            if test_results.get("failures"):
                for failure in test_results["failures"][:5]:
                    errors.append(f"  - {failure}")

        if total == 0:
            warnings.append("没有运行任何测试")

        coverage = test_results.get("coverage", 0)
        if coverage < 80 and coverage > 0:
            warnings.append(f"测试覆盖率较低: {coverage}%")

        return self._create_result(len(errors) == 0, errors, warnings)


class FormatHook(BaseHook):
    """
    格式检查 Hook

    检查输出格式是否符合要求
    """

    name = "format"
    hook_type = HookType.POST
    mode = HookMode.NON_BLOCKING  # 格式问题不阻塞
    priority = 60

    def __init__(self, required_format: str = "markdown") -> None:
        self.required_format = required_format

    def check(self, context: dict[str, Any]) -> HookResult:
        """检查格式"""
        output = context.get("output", "")
        if not output:
            return self._create_result(True)

        warnings = []

        if self.required_format == "markdown":
            # 检查 Markdown 格式
            if not output.strip().startswith("#"):
                warnings.append("输出应以标题开始")

            if "```" in output and not output.count("```") % 2 == 0:
                warnings.append("代码块未正确闭合")

        return self._create_result(True, warnings=warnings)


class HooksManager:
    """
    Hooks 管理器

    Harness 核心能力之一:
    1. 注册和管理 Hooks
    2. 按类型和优先级执行
    3. 支持阻塞和非阻塞模式
    4. 汇总执行结果

    使用示例:
        manager = HooksManager()

        # 注册 Hooks
        manager.register(CodeLintHook())
        manager.register(SecurityHook())

        # 执行前置检查
        result = manager.run_pre_hooks({"code": source_code})
        if not result.passed:
            print(result.errors)
    """

    def __init__(self) -> None:
        self._hooks: dict[str, BaseHook] = {}
        self._hooks_by_type: dict[HookType, list[str]] = {
            HookType.PRE: [],
            HookType.POST: [],
            HookType.VALIDATION: [],
            HookType.SECURITY: [],
        }

        # 统计
        self._stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "blocked_executions": 0,
        }

    def register(self, hook: BaseHook) -> None:
        """
        注册 Hook

        Args:
            hook: Hook 实例
        """
        self._hooks[hook.name] = hook

        # 添加到类型列表并按优先级排序
        type_list = self._hooks_by_type[hook.hook_type]
        type_list.append(hook.name)
        type_list.sort(key=lambda n: self._hooks[n].priority, reverse=True)

    def register_pre_hook(self, name: str, hook: BaseHook) -> None:
        """注册前置 Hook"""
        hook.hook_type = HookType.PRE
        hook.name = name
        self.register(hook)

    def register_post_hook(self, name: str, hook: BaseHook) -> None:
        """注册后置 Hook"""
        hook.hook_type = HookType.POST
        hook.name = name
        self.register(hook)

    def unregister(self, name: str) -> bool:
        """注销 Hook"""
        if name not in self._hooks:
            return False

        hook = self._hooks[name]
        self._hooks_by_type[hook.hook_type].remove(name)
        del self._hooks[name]
        return True

    def get_hook(self, name: str) -> BaseHook | None:
        """获取 Hook"""
        return self._hooks.get(name)

    def list_hooks(self, hook_type: HookType | None = None) -> list[dict[str, Any]]:
        """列出 Hooks"""
        if hook_type:
            names = self._hooks_by_type[hook_type]
        else:
            names = list(self._hooks.keys())

        return [
            {
                "name": name,
                "type": self._hooks[name].hook_type.value,
                "mode": self._hooks[name].mode.value,
                "priority": self._hooks[name].priority,
            }
            for name in names
        ]

    def run_pre_hooks(self, context: dict[str, Any]) -> HooksResult:
        """
        运行所有前置 Hooks

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        return self._run_hooks_of_type(HookType.PRE, context)

    def run_post_hooks(self, context: dict[str, Any]) -> HooksResult:
        """
        运行所有后置 Hooks

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        return self._run_hooks_of_type(HookType.POST, context)

    def run_security_hooks(self, context: dict[str, Any]) -> HooksResult:
        """
        运行安全检查 Hooks

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        return self._run_hooks_of_type(HookType.SECURITY, context)

    def run_validation_hooks(self, context: dict[str, Any]) -> HooksResult:
        """
        运行验证 Hooks

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        return self._run_hooks_of_type(HookType.VALIDATION, context)

    def run_all_hooks(self, context: dict[str, Any]) -> HooksResult:
        """
        运行所有 Hooks

        Args:
            context: 检查上下文

        Returns:
            HooksResult: 汇总结果
        """
        results = []

        # 按类型顺序执行：Security -> Validation -> Pre -> Post
        for hook_type in [HookType.SECURITY, HookType.VALIDATION, HookType.PRE, HookType.POST]:
            type_result = self._run_hooks_of_type(hook_type, context)
            results.extend(type_result.results)

            # 如果有阻塞失败，立即返回
            if type_result.blocked_by:
                return HooksResult(
                    passed=False,
                    results=results,
                    total_errors=sum(len(r.errors) for r in results),
                    total_warnings=sum(len(r.warnings) for r in results),
                    blocked_by=type_result.blocked_by,
                )

        return HooksResult(
            passed=all(r.passed for r in results),
            results=results,
            total_errors=sum(len(r.errors) for r in results),
            total_warnings=sum(len(r.warnings) for r in results),
        )

    def _run_hooks_of_type(self, hook_type: HookType, context: dict[str, Any]) -> HooksResult:
        """运行指定类型的 Hooks"""
        results = []
        blocked_by = None

        for name in self._hooks_by_type[hook_type]:
            hook = self._hooks[name]
            start_time = time.time()

            try:
                result = hook.check(context)
                result.execution_time = time.time() - start_time
                results.append(result)

                self._stats["total_checks"] += 1
                if result.passed:
                    self._stats["passed_checks"] += 1
                else:
                    self._stats["failed_checks"] += 1

                # 阻塞模式失败时停止
                if not result.passed and hook.mode == HookMode.BLOCKING:
                    blocked_by = name
                    self._stats["blocked_executions"] += 1
                    break

            except Exception as e:
                results.append(HookResult(
                    hook_name=name,
                    passed=False,
                    errors=[f"Hook 执行异常: {e}"],
                    execution_time=time.time() - start_time,
                ))
                self._stats["failed_checks"] += 1

                if hook.mode == HookMode.BLOCKING:
                    blocked_by = name
                    break

        return HooksResult(
            passed=blocked_by is None,
            results=results,
            total_errors=sum(len(r.errors) for r in results),
            total_warnings=sum(len(r.warnings) for r in results),
            blocked_by=blocked_by,
        )

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def clear_stats(self) -> None:
        """清除统计"""
        self._stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "blocked_executions": 0,
        }


def create_default_hooks() -> HooksManager:
    """创建默认 Hooks 管理器"""
    manager = HooksManager()
    manager.register(CodeLintHook())
    manager.register(SecurityHook())
    manager.register(TestPassHook())
    manager.register(FormatHook())
    return manager