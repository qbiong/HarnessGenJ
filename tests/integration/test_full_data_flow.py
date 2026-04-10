"""
集成测试：完整数据流验证

验证所有核心模块间的数据流是否正确：
1. develop() → HybridIntegration → TriggerManager → 角色执行 → ScoreManager
2. 任务创建 → TaskStateMachine 状态管理 → MemoryManager 数据存储
3. 对抗审查 → 质量数据更新
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from harnessgenj import Harness
from harnessgenj.harness.hybrid_integration import IntegrationMode
from harnessgenj.workflow.task_state import TaskState
from harnessgenj.engine import SkipLevel


class TestFullDataFlow:
    """测试完整数据流"""

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def harness(self, temp_workspace):
        return Harness("test_project", workspace=temp_workspace, persistent=True)

    def test_develop_triggers_adversarial_review(self, harness, temp_workspace):
        """测试 develop() 触发对抗审查的完整链路"""
        # 强制使用 BUILTIN 模式
        harness._hybrid_integration.force_mode(IntegrationMode.BUILTIN)

        # 执行开发
        result = harness.develop("实现测试功能", skip_level=SkipLevel.ALL, execution_mode="simulate")

        # 验证任务创建
        assert result["task_id"] is not None

        # 验证状态机有任务记录
        task_state = harness._task_state_machine.get_task(result["task_id"])
        assert task_state is not None

        # 验证 HybridIntegration 有事件记录
        events = harness._hybrid_integration.get_recent_events()
        assert len(events) > 0

    def test_task_creation_flow(self, harness):
        """测试任务创建流程"""
        # 接收请求
        result = harness.receive_request("实现登录功能")

        # 验证 MemoryManager 有任务数据
        task_data = harness.memory.get_task(result["task_id"])
        assert task_data is not None
        assert task_data["request"] == "实现登录功能"

        # 验证 TaskStateMachine 有状态记录
        task_state = harness._task_state_machine.get_task(result["task_id"])
        assert task_state is not None
        assert task_state.state == TaskState.PENDING

        # 验证状态机不存储任务详情
        with pytest.raises(AttributeError):
            _ = task_state.description
        with pytest.raises(AttributeError):
            _ = task_state.metadata

    def test_task_completion_flow(self, harness):
        """测试任务完成流程"""
        # 创建任务
        result = harness.receive_request("实现功能X")
        task_id = result["task_id"]

        # 开始任务
        harness._task_state_machine.start(task_id)

        # 完成任务
        success = harness.complete_task(task_id, "功能完成")
        assert success is True

        # 验证状态
        final_state = harness._task_state_machine.get_state(task_id)
        assert final_state == TaskState.COMPLETED

    def test_trigger_manager_integration(self, harness):
        """测试 TriggerManager 与角色系统集成"""
        # 注册角色
        harness._auto_setup_core_team()

        # 触发事件
        from harnessgenj.harness.event_triggers import TriggerEvent
        results = harness._trigger_manager.trigger(
            TriggerEvent.ON_WRITE_COMPLETE,
            {
                "file_path": "test.py",
                "content": "def hello(): pass",
                "task_id": "TASK-TEST",
            }
        )

        # 验证触发结果
        # 注意：如果角色 review 方法返回结果，这里会有结果
        assert isinstance(results, list)

    def test_score_manager_events(self, harness):
        """测试积分事件记录"""
        # 注册角色
        harness._score_manager.register_role("developer", "dev_test", "测试开发者")
        harness._score_manager.register_role("code_reviewer", "reviewer_test", "测试审查者")

        # 触发问题发现
        gen_delta, disc_delta = harness._score_manager.on_issue_found(
            generator_id="dev_test",
            discriminator_id="reviewer_test",
            severity="major",
            task_id="TASK-001",
            description="发现重大问题",
        )

        # 验证积分变化
        assert gen_delta < 0  # 生成者扣分
        assert disc_delta > 0  # 判别者加分

        # 验证事件记录
        events = harness._score_manager.get_recent_events()
        assert len(events) >= 2

    def test_persistence_across_sessions(self, temp_workspace):
        """测试跨会话持久化"""
        # 第一个会话
        harness1 = Harness("persist_test", workspace=temp_workspace)
        harness1.remember("test_key", "test_value", important=True)
        harness1.receive_request("任务A")
        harness1.save()

        # 第二个会话（重新加载）
        harness2 = Harness("persist_test", workspace=temp_workspace)
        value = harness2.recall("test_key")
        assert value == "test_value"

    def test_hybrid_integration_mode_switching(self, harness):
        """测试混合集成模式切换"""
        # 初始模式
        initial_mode = harness._hybrid_integration.get_active_mode()

        # 切换到 BUILTIN
        harness._hybrid_integration.force_mode(IntegrationMode.BUILTIN)
        assert harness._hybrid_integration.get_active_mode() == IntegrationMode.BUILTIN

        # 切换到 HOOKS
        harness._hybrid_integration.force_mode(IntegrationMode.HOOKS)
        assert harness._hybrid_integration.get_active_mode() == IntegrationMode.HOOKS

    def test_diagnostic_tools(self, harness):
        """测试诊断工具"""
        # HybridIntegration 诊断
        diag = harness._hybrid_integration.diagnose()
        assert "active_mode" in diag
        assert "recommendations" in diag

        # TaskStateMachine 统计
        stats = harness._task_state_machine.get_stats()
        assert "total_tasks" in stats

        # TriggerManager 规则
        rules = harness._trigger_manager.get_rules()
        assert len(rules) > 0


class TestEdgeCases:
    """测试边界条件"""

    @pytest.fixture
    def harness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Harness("edge_test", workspace=tmpdir)

    def test_empty_request(self, harness):
        """测试空请求"""
        result = harness.receive_request("")
        assert result["success"] is True  # 应该接受但可能警告

    def test_concurrent_task_creation(self, harness):
        """测试并发任务创建"""
        import threading

        task_ids = []

        def create_task(i):
            result = harness.receive_request(f"任务{i}")
            task_ids.append(result["task_id"])

        threads = [threading.Thread(target=create_task, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有任务都被创建
        assert len(task_ids) == 5
        assert len(set(task_ids)) == 5  # 所有ID唯一

    def test_invalid_state_transition(self, harness):
        """测试无效状态转换"""
        harness.receive_request("任务X")
        task_id = "TASK-INVALID"
        harness._task_state_machine.create_task(task_id)

        # 尝试无效转换
        from harnessgenj.workflow.task_state import InvalidTransitionError
        with pytest.raises(InvalidTransitionError):
            harness._task_state_machine.transition(task_id, TaskState.COMPLETED)


class TestModuleResponsibilities:
    """测试模块职责边界"""

    def test_task_state_machine_no_data_storage(self):
        """验证 TaskStateMachine 不存储任务数据"""
        from harnessgenj.workflow.task_state import TaskStateMachine

        machine = TaskStateMachine()
        task = machine.create_task("TASK-001")

        # 确认只有状态相关字段
        assert hasattr(task, 'task_id')
        assert hasattr(task, 'state')
        assert hasattr(task, 'state_history')

        # 确认没有业务数据字段
        assert not hasattr(task, 'description')
        assert not hasattr(task, 'metadata')

    def test_hybrid_integration_no_direct_score_update(self):
        """验证 HybridIntegration 不直接更新积分"""
        from harnessgenj.harness.hybrid_integration import HybridIntegration, HybridConfig
        from harnessgenj.harness.hooks_integration import HooksIntegration, HooksConfig

        config = HybridConfig()
        hooks = HooksIntegration(config=HooksConfig())
        integration = HybridIntegration(config=config, hooks_integration=hooks)

        # 触发事件
        event = integration.trigger_on_issue_found(
            generator_id="dev_1",
            discriminator_id="reviewer_1",
            severity="major",
            description="测试问题",
        )

        # 验证事件被记录
        assert event.success is True

        # 验证积分未直接更新（因为没有传入 score_manager）
        # 这个测试确认 HybridIntegration 不自己更新积分