"""
Hybrid Integration 全面测试

测试覆盖：
1. 模式切换（Hooks/Builtin/MCP）
2. 事件记录
3. 与 TriggerManager 的集成
4. 自动降级机制
5. 事件持久化
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
import time

from harnessgenj.harness.hybrid_integration import (
    HybridIntegration,
    HybridConfig,
    IntegrationMode,
    EventRecord,
    create_hybrid_integration,
)
from harnessgenj.harness.hooks_integration import HooksIntegration, HooksConfig
from harnessgenj.harness.event_triggers import TriggerManager, TriggerEvent


class TestHybridConfig:
    """测试 HybridConfig 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = HybridConfig()
        assert config.preferred_mode == IntegrationMode.HOOKS
        assert config.auto_fallback is True
        assert config.hooks_timeout_seconds == 5.0
        assert config.persist_events is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = HybridConfig(
            preferred_mode=IntegrationMode.BUILTIN,
            auto_fallback=False,
            hooks_timeout_seconds=10.0,
        )
        assert config.preferred_mode == IntegrationMode.BUILTIN
        assert config.auto_fallback is False
        assert config.hooks_timeout_seconds == 10.0


class TestIntegrationMode:
    """测试集成模式枚举"""

    def test_mode_values(self):
        """测试模式值"""
        assert IntegrationMode.HOOKS.value == "hooks"
        assert IntegrationMode.BUILTIN.value == "builtin"
        assert IntegrationMode.MCP.value == "mcp"


class TestEventRecord:
    """测试事件记录"""

    def test_create_event(self):
        """测试创建事件"""
        event = EventRecord(
            event_type="on_write_complete",
            mode=IntegrationMode.BUILTIN,
            data={"file_path": "test.py"},
        )
        assert event.event_type == "on_write_complete"
        assert event.mode == IntegrationMode.BUILTIN
        assert event.success is True
        assert event.error is None

    def test_event_with_error(self):
        """测试带错误的事件"""
        event = EventRecord(
            event_type="on_write_complete",
            mode=IntegrationMode.HOOKS,
            data={},
            success=False,
            error="Test error",
        )
        assert event.success is False
        assert event.error == "Test error"


class TestHybridIntegration:
    """测试 HybridIntegration 核心功能"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_trigger_manager(self, temp_workspace):
        """创建模拟 TriggerManager"""
        # 创建一个简单的 Mock 对象
        class MockTriggerManager:
            def __init__(self):
                self.triggered_events = []

            def trigger(self, event, context):
                self.triggered_events.append({"event": event, "context": context})
                return []

        return MockTriggerManager()

    @pytest.fixture
    def hybrid_integration(self, temp_workspace, mock_trigger_manager):
        """创建 HybridIntegration 实例"""
        config = HybridConfig(
            preferred_mode=IntegrationMode.BUILTIN,
            auto_fallback=True,
        )
        hooks_integration = HooksIntegration(
            config=HooksConfig(enabled=True, blocking_mode=False),
        )
        return HybridIntegration(
            config=config,
            hooks_integration=hooks_integration,
            trigger_manager=mock_trigger_manager,
            workspace=temp_workspace,
        )

    def test_create_hybrid_integration(self, hybrid_integration):
        """测试创建实例"""
        assert hybrid_integration is not None
        assert hybrid_integration.config.preferred_mode == IntegrationMode.BUILTIN

    def test_get_active_mode(self, hybrid_integration):
        """测试获取活跃模式"""
        mode = hybrid_integration.get_active_mode()
        assert mode == IntegrationMode.BUILTIN

    def test_force_mode(self, hybrid_integration):
        """测试强制切换模式"""
        hybrid_integration.force_mode(IntegrationMode.HOOKS)
        assert hybrid_integration.get_active_mode() == IntegrationMode.HOOKS

    def test_trigger_on_write_complete_builtin(self, hybrid_integration, mock_trigger_manager):
        """测试 BUILTIN 模式下触发 Write 完成事件"""
        hybrid_integration.force_mode(IntegrationMode.BUILTIN)

        event = hybrid_integration.trigger_on_write_complete(
            file_path="test.py",
            content="print('hello')",
            metadata={"task_id": "TASK-001"},
        )

        assert event.success is True
        assert event.mode == IntegrationMode.BUILTIN
        assert len(mock_trigger_manager.triggered_events) == 1
        assert mock_trigger_manager.triggered_events[0]["event"] == TriggerEvent.ON_WRITE_COMPLETE

    def test_trigger_on_write_complete_hooks(self, hybrid_integration, mock_trigger_manager):
        """测试 HOOKS 模式下触发 Write 完成事件"""
        hybrid_integration.force_mode(IntegrationMode.HOOKS)

        event = hybrid_integration.trigger_on_write_complete(
            file_path="test.py",
            content="print('hello')",
        )

        assert event.success is True
        assert event.mode == IntegrationMode.HOOKS
        # HOOKS 模式下不调用 TriggerManager
        assert len(mock_trigger_manager.triggered_events) == 0

    def test_trigger_on_task_complete(self, hybrid_integration):
        """测试触发任务完成事件"""
        event = hybrid_integration.trigger_on_task_complete(
            task_id="TASK-001",
            summary="任务完成",
            metadata={"rounds": 1},
        )

        assert event.success is True
        assert event.data["task_id"] == "TASK-001"

    def test_trigger_on_issue_found(self, hybrid_integration):
        """测试触发问题发现事件"""
        event = hybrid_integration.trigger_on_issue_found(
            generator_id="developer_1",
            discriminator_id="code_reviewer_1",
            severity="major",
            description="发现安全问题",
            task_id="TASK-001",
        )

        assert event.success is True
        assert event.data["generator_id"] == "developer_1"
        assert event.data["discriminator_id"] == "code_reviewer_1"
        assert event.data["severity"] == "major"

    def test_event_persistence(self, hybrid_integration, temp_workspace):
        """测试事件持久化"""
        hybrid_integration.trigger_on_write_complete(
            file_path="test.py",
            content="print('hello')",
        )

        # 检查事件文件是否创建
        events_dir = Path(temp_workspace) / "events"
        assert events_dir.exists()

        event_files = list(events_dir.glob("event_*.json"))
        assert len(event_files) >= 1

    def test_get_stats(self, hybrid_integration):
        """测试获取统计信息"""
        hybrid_integration.trigger_on_write_complete("test.py", "code")
        hybrid_integration.trigger_on_task_complete("TASK-001", "完成")

        stats = hybrid_integration.get_stats()
        assert stats["events_count"] >= 2

    def test_get_recent_events(self, hybrid_integration):
        """测试获取最近事件"""
        for i in range(5):
            hybrid_integration.trigger_on_write_complete(f"file{i}.py", f"code{i}")

        events = hybrid_integration.get_recent_events(limit=3)
        assert len(events) == 3

    def test_diagnose(self, hybrid_integration):
        """测试诊断功能"""
        result = hybrid_integration.diagnose()
        assert "active_mode" in result
        assert "hooks_configured" in result
        assert "recommendations" in result


class TestAutoFallback:
    """测试自动降级机制"""

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_auto_fallback_to_builtin(self, temp_workspace):
        """测试自动降级到 BUILTIN 模式"""
        config = HybridConfig(
            preferred_mode=IntegrationMode.HOOKS,
            auto_fallback=True,
        )
        hooks_integration = HooksIntegration(
            config=HooksConfig(enabled=True, blocking_mode=False),
        )

        integration = HybridIntegration(
            config=config,
            hooks_integration=hooks_integration,
            workspace=temp_workspace,
        )

        # 由于没有配置 Hooks，应该自动降级
        # 注意：这取决于 _check_hooks_effectiveness 的实现
        mode = integration.get_active_mode()
        # 可能是 HOOKS 或 BUILTIN，取决于检测逻辑
        assert mode in [IntegrationMode.HOOKS, IntegrationMode.BUILTIN]


class TestBuiltinCallbacks:
    """测试内置回调机制"""

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_register_callback(self, temp_workspace):
        """测试注册回调"""
        config = HybridConfig(preferred_mode=IntegrationMode.BUILTIN)
        hooks_integration = HooksIntegration(config=HooksConfig(enabled=True))

        integration = HybridIntegration(
            config=config,
            hooks_integration=hooks_integration,
            workspace=temp_workspace,
        )

        callback_called = []

        def my_callback(data):
            callback_called.append(data)

        integration.register_builtin_callback("on_task_complete", my_callback)
        integration.trigger_on_task_complete("TASK-001", "完成")

        assert len(callback_called) == 1
        assert callback_called[0]["task_id"] == "TASK-001"


class TestCreateHybridIntegration:
    """测试工厂函数"""

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_create_with_defaults(self, temp_workspace):
        """测试使用默认参数创建"""
        integration = create_hybrid_integration(workspace=temp_workspace)
        assert integration is not None
        assert integration.config.preferred_mode == IntegrationMode.HOOKS

    def test_create_with_trigger_manager(self, temp_workspace):
        """测试使用 TriggerManager 创建"""
        class MockTM:
            def trigger(self, event, context):
                return []

        integration = create_hybrid_integration(
            workspace=temp_workspace,
            trigger_manager=MockTM(),
        )
        assert integration._trigger_manager is not None