"""
Tests for Hooks Integration Module

测试 Hooks 集成功能:
- Pre-Hooks 执行
- Post-Hooks 执行
- 安全检查
- 阻塞模式
"""

import pytest
from harnessgenj.harness.hooks_integration import (
    HooksIntegration,
    HooksConfig,
    HooksIntegrationBuilder,
    create_hooks_integration,
)
from harnessgenj.harness.hooks import HooksManager, HooksResult


class TestHooksConfig:
    """测试 Hooks 配置"""

    def test_create_default_config(self):
        """创建默认配置"""
        config = HooksConfig()
        assert config.enabled is True
        assert config.blocking_mode is True
        assert len(config.pre_hooks) > 0
        assert len(config.post_hooks) > 0

    def test_create_custom_config(self):
        """创建自定义配置"""
        config = HooksConfig(
            enabled=True,
            blocking_mode=False,
            pre_hooks=["custom_pre"],
            post_hooks=["custom_post"],
        )
        assert config.blocking_mode is False
        assert config.pre_hooks == ["custom_pre"]

    def test_config_with_security_hooks(self):
        """带安全检查的配置"""
        config = HooksConfig(security_hooks=["security_scan"])
        assert "security_scan" in config.security_hooks

    def test_config_timeout(self):
        """超时配置"""
        config = HooksConfig(timeout_seconds=60.0)
        assert config.timeout_seconds == 60.0

    def test_config_max_retries(self):
        """重试次数配置"""
        config = HooksConfig(max_retries=3)
        assert config.max_retries == 3


class TestHooksIntegration:
    """测试 Hooks 集成"""

    def test_create_integration(self):
        """创建集成"""
        integration = create_hooks_integration()
        assert isinstance(integration, HooksIntegration)
        assert integration.config.enabled is True

    def test_create_disabled_integration(self):
        """创建禁用的集成"""
        integration = create_hooks_integration(enabled=False)
        assert integration.config.enabled is False

    def test_create_non_blocking_integration(self):
        """创建非阻塞集成"""
        integration = create_hooks_integration(blocking_mode=False)
        assert integration.config.blocking_mode is False

    def test_run_pre_task_success(self):
        """Pre-Task 检查成功"""
        integration = create_hooks_integration()
        result = integration.run_pre_task({
            "code": "def hello(): pass",
            "file_path": "test.py",
        })
        # 检查结果
        assert result is not None

    def test_run_pre_task_disabled(self):
        """禁用时 Pre-Task 返回成功"""
        integration = create_hooks_integration(enabled=False)
        result = integration.run_pre_task({"code": "test"})
        assert result.passed is True

    def test_run_post_task_success(self):
        """Post-Task 检查成功"""
        integration = create_hooks_integration()
        result = integration.run_post_task({
            "test_results": {"passed": 5, "failed": 0},
        })
        assert result is not None

    def test_run_post_task_disabled(self):
        """禁用时 Post-Task 返回成功"""
        integration = create_hooks_integration(enabled=False)
        result = integration.run_post_task({"test": "results"})
        assert result.passed is True

    def test_run_security_check(self):
        """安全检查"""
        integration = create_hooks_integration()
        result = integration.run_security_check({
            "code": "def safe_function(): pass",
        })
        assert result is not None

    def test_run_security_check_disabled(self):
        """禁用时安全检查返回成功"""
        integration = create_hooks_integration(enabled=False)
        result = integration.run_security_check({"code": "test"})
        assert result.passed is True

    def test_run_validation(self):
        """验证检查"""
        integration = create_hooks_integration()
        result = integration.run_validation({
            "data": {"name": "test"},
        })
        assert result is not None

    def test_run_all(self):
        """执行所有检查"""
        integration = create_hooks_integration()
        result = integration.run_all({
            "code": "def test(): pass",
        })
        assert result is not None

    def test_check_code(self):
        """快速代码检查"""
        integration = create_hooks_integration()
        result = integration.check_code("def hello(): pass", "test.py")
        assert result is not None

    def test_check_test_results(self):
        """快速测试结果检查"""
        integration = create_hooks_integration()
        result = integration.check_test_results(passed=5, failed=0)
        assert result is not None

    def test_get_stats(self):
        """获取统计"""
        integration = create_hooks_integration()
        integration.run_pre_task({"code": "test"})
        integration.run_post_task({"test_results": {}})

        stats = integration.get_stats()
        assert "total_checks" in stats
        assert "hooks_enabled" in stats

    def test_reset_stats(self):
        """重置统计"""
        integration = create_hooks_integration()
        integration.run_pre_task({"code": "test"})
        integration.reset_stats()

        stats = integration.get_stats()
        assert stats["total_checks"] == 0

    def test_enable_disable_hooks(self):
        """启用/禁用 Hooks"""
        integration = create_hooks_integration()
        integration.disable_hooks()
        assert integration.config.enabled is False

        integration.enable_hooks()
        assert integration.config.enabled is True

    def test_register_hook(self):
        """注册自定义 Hook"""
        integration = create_hooks_integration()
        from harnessgenj.harness.hooks import BaseHook, HookType

        class CustomHook(BaseHook):
            name = "custom_test"
            hook_type = HookType.PRE

            def check(self, context):
                return self._create_result(True)

        hook = CustomHook()
        integration.register_hook(hook)

        # 应该能找到
        retrieved = integration.get_hook("custom_test")
        assert retrieved is not None

    def test_list_hooks(self):
        """列出所有 Hooks"""
        integration = create_hooks_integration()
        hooks = integration.list_hooks()
        assert isinstance(hooks, list)


class TestHooksIntegrationBuilder:
    """测试 Builder 模式"""

    def test_builder_create(self):
        """创建 Builder"""
        builder = HooksIntegrationBuilder()
        integration = builder.build()
        assert isinstance(integration, HooksIntegration)

    def test_builder_enabled(self):
        """Builder 设置启用"""
        builder = HooksIntegrationBuilder()
        builder.enabled(False)
        integration = builder.build()
        assert integration.config.enabled is False

    def test_builder_blocking(self):
        """Builder 设置阻塞模式"""
        builder = HooksIntegrationBuilder()
        builder.blocking(False)
        integration = builder.build()
        assert integration.config.blocking_mode is False

    def test_builder_with_pre_hooks(self):
        """Builder 设置 Pre-Hooks"""
        builder = HooksIntegrationBuilder()
        builder.with_pre_hooks(["hook1", "hook2"])
        integration = builder.build()
        assert "hook1" in integration.config.pre_hooks

    def test_builder_with_post_hooks(self):
        """Builder 设置 Post-Hooks"""
        builder = HooksIntegrationBuilder()
        builder.with_post_hooks(["post1"])
        integration = builder.build()
        assert "post1" in integration.config.post_hooks

    def test_builder_with_timeout(self):
        """Builder 设置超时"""
        builder = HooksIntegrationBuilder()
        builder.with_timeout(60.0)
        integration = builder.build()
        assert integration.config.timeout_seconds == 60.0

    def test_builder_chain(self):
        """Builder 链式调用"""
        integration = HooksIntegrationBuilder() \
            .enabled(True) \
            .blocking(True) \
            .with_pre_hooks(["pre"]) \
            .with_post_hooks(["post"]) \
            .with_timeout(30.0) \
            .build()

        assert integration.config.enabled is True
        assert integration.config.blocking_mode is True
        assert "pre" in integration.config.pre_hooks
        assert "post" in integration.config.post_hooks
        assert integration.config.timeout_seconds == 30.0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_hooks_integration(self):
        """创建 Hooks 集成"""
        integration = create_hooks_integration()
        assert isinstance(integration, HooksIntegration)

    def test_create_with_params(self):
        """创建带参数的集成"""
        integration = create_hooks_integration(
            enabled=False,
            blocking_mode=False,
        )
        assert integration.config.enabled is False
        assert integration.config.blocking_mode is False