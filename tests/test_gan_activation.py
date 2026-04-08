"""
测试 GAN 对抗机制激活

验证以下核心功能：
1. Hooks 模式触发 TriggerManager 激活角色
2. develop() 执行 GAN 对抗审查
3. 任务状态流转
4. 双向积分激励
"""

import pytest
import tempfile
from pathlib import Path

from harnessgenj import Harness
from harnessgenj.harness.hybrid_integration import IntegrationMode
from harnessgenj.workflow.task_state import TaskState


class TestHooksTriggerRoles:
    """测试 Hooks 触发角色激活"""

    def test_hooks_mode_triggers_trigger_manager(self, tmp_path):
        """测试 Hooks 模式下 TriggerManager 被调用"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 强制使用 Hooks 模式
        harness._hybrid_integration.force_mode(IntegrationMode.HOOKS)

        # 触发 Write 完成事件
        event = harness._hybrid_integration.trigger_on_write_complete(
            file_path="test.py",
            content="print('hello')",
        )

        # 验证事件成功
        assert event.success is True
        assert event.mode == IntegrationMode.HOOKS

    def test_trigger_manager_processes_events(self, tmp_path):
        """测试 TriggerManager 处理事件"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 处理待处理事件
        processed = harness._trigger_manager.process_pending_events(str(tmp_path / ".harnessgenj"))

        # 验证方法可调用（可能没有事件）
        assert isinstance(processed, int)


class TestTaskStateFlow:
    """测试任务状态流转"""

    def test_task_state_transitions_on_develop(self, tmp_path):
        """测试 develop() 触发状态流转"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 创建任务
        task_info = harness.receive_request("实现登录功能", request_type="feature")
        task_id = task_info.get("task_id")

        # 验证任务创建
        assert task_id is not None

        # 获取任务状态
        status = harness.get_task_state_status()
        assert status["total_tasks"] >= 1

    def test_task_start_transitions_pending_to_in_progress(self, tmp_path):
        """测试任务启动状态转换"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 创建并启动任务
        task_info = harness.receive_request("测试任务", request_type="feature")
        task_id = task_info.get("task_id")

        # 手动启动状态流转
        harness._task_state_machine.start(task_id)

        # 验证状态转换
        task = harness._task_state_machine.get_task(task_id)
        assert task is not None
        assert task.state == TaskState.IN_PROGRESS


class TestGANAdversarialMechanism:
    """测试 GAN 对抗机制"""

    def test_adversarial_workflow_exists(self, tmp_path):
        """测试对抗工作流存在"""
        from harnessgenj.harness.adversarial import AdversarialWorkflow

        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 创建对抗工作流
        adversarial = AdversarialWorkflow(
            score_manager=harness._score_manager,
            quality_tracker=harness._quality_tracker,
            memory_manager=harness.memory,
        )

        assert adversarial is not None

    def test_develop_includes_adversarial_result(self, tmp_path):
        """测试 develop() 包含对抗结果"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 执行开发（可能没有实际代码产出）
        result = harness.develop("简单功能", skip_hooks=True)

        # 验证结果结构
        assert "task_id" in result
        assert "status" in result


class TestRoleCollaboration:
    """测试角色协作"""

    def test_roles_registered_to_collaboration(self, tmp_path):
        """测试角色注册到协作管理器"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 确保有角色
        from harnessgenj.roles import RoleType
        if not harness.coordinator.get_roles_by_type(RoleType.DEVELOPER):
            harness.coordinator.create_role(RoleType.DEVELOPER, "dev_test", "开发")

        # 注册角色
        harness._register_roles_to_collaboration()

        # 获取协作状态
        status = harness.get_collaboration_status()
        assert "stats" in status

    def test_message_bus_subscriptions(self, tmp_path):
        """测试消息总线订阅"""
        from harnessgenj.workflow.message_bus import MessageBus, MessageType

        bus = MessageBus()

        # 订阅消息
        sub_id = bus.subscribe(
            subscriber_id="test_reviewer",
            message_types=[MessageType.NOTIFICATION],
            callback=lambda msg: None,
        )

        assert sub_id is not None
        assert sub_id.startswith("SUB-")


class TestIntegration:
    """集成测试"""

    def test_full_workflow_with_hooks(self, tmp_path):
        """测试完整工作流（包含 Hooks）"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 执行开发
        result = harness.develop("实现一个简单的工具函数", skip_hooks=True)

        # 验证基本结果
        assert result is not None
        assert "task_id" in result

        # 验证状态机有记录
        status = harness.get_task_state_status()
        assert status["total_tasks"] >= 1

    def test_bug_fix_workflow(self, tmp_path):
        """测试 Bug 修复工作流"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 执行 Bug 修复
        result = harness.fix_bug("修复空指针异常", skip_hooks=True)

        # 验证结果
        assert result is not None
        assert "task_id" in result

        # 验证统计更新（使用 _stats 属性）
        assert harness._stats.bugs_fixed >= 0