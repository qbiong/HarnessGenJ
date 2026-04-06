"""
Task State Machine 全面测试

测试覆盖：
1. 状态转换验证
2. 无效转换处理
3. 状态历史记录
4. 钩子触发
5. 批量操作
"""

import pytest
import time

from harnessgenj.workflow.task_state import (
    TaskStateMachine,
    TaskState,
    TaskInfo,
    StateChangeEvent,
    InvalidTransitionError,
    create_task_state_machine,
)


class TestTaskState:
    """测试状态枚举"""

    def test_state_values(self):
        """测试状态值"""
        assert TaskState.PENDING.value == "pending"
        assert TaskState.IN_PROGRESS.value == "in_progress"
        assert TaskState.REVIEWING.value == "reviewing"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELLED.value == "cancelled"


class TestTaskInfo:
    """测试任务信息"""

    def test_create_task_info(self):
        """测试创建任务信息"""
        info = TaskInfo(task_id="TASK-001")
        assert info.task_id == "TASK-001"
        assert info.state == TaskState.PENDING
        # description 和 metadata 字段已被移除，不再存储

    def test_add_event(self):
        """测试添加事件"""
        info = TaskInfo(task_id="TASK-001")
        event = StateChangeEvent(
            task_id="TASK-001",
            from_state=TaskState.PENDING,
            to_state=TaskState.IN_PROGRESS,
            reason="开始任务",
        )
        info.add_event(event)
        assert len(info.state_history) == 1


class TestTaskStateMachine:
    """测试状态机核心功能"""

    @pytest.fixture
    def machine(self):
        """创建状态机实例"""
        return create_task_state_machine()

    def test_create_machine(self, machine):
        """测试创建状态机"""
        assert machine is not None

    def test_create_task(self, machine):
        """测试创建任务"""
        task = machine.create_task("TASK-001")
        assert task.task_id == "TASK-001"
        assert task.state == TaskState.PENDING

    def test_create_duplicate_task(self, machine):
        """测试创建重复任务（应返回已存在的任务）"""
        task1 = machine.create_task("TASK-DUP")
        task2 = machine.create_task("TASK-DUP")
        assert task1.task_id == task2.task_id

    def test_get_task(self, machine):
        """测试获取任务"""
        machine.create_task("TASK-GET")
        task = machine.get_task("TASK-GET")
        assert task is not None
        assert task.task_id == "TASK-GET"

    def test_get_nonexistent_task(self, machine):
        """测试获取不存在的任务"""
        task = machine.get_task("TASK-NONEXISTENT")
        assert task is None

    def test_get_state(self, machine):
        """测试获取状态"""
        machine.create_task("TASK-STATE")
        state = machine.get_state("TASK-STATE")
        assert state == TaskState.PENDING

    def test_task_exists(self, machine):
        """测试任务是否存在"""
        machine.create_task("TASK-EXISTS")
        assert machine.task_exists("TASK-EXISTS") is True
        assert machine.task_exists("TASK-NONEXISTENT") is False


class TestStateTransitions:
    """测试状态转换"""

    @pytest.fixture
    def machine(self):
        return create_task_state_machine()

    def test_valid_transition_pending_to_in_progress(self, machine):
        """测试有效转换：pending → in_progress"""
        machine.create_task("TASK-001")
        task = machine.transition("TASK-001", TaskState.IN_PROGRESS, "开始任务")
        assert task.state == TaskState.IN_PROGRESS

    def test_valid_transition_in_progress_to_reviewing(self, machine):
        """测试有效转换：in_progress → reviewing"""
        machine.create_task("TASK-002")
        machine.transition("TASK-002", TaskState.IN_PROGRESS)
        task = machine.transition("TASK-002", TaskState.REVIEWING, "提交审查")
        assert task.state == TaskState.REVIEWING

    def test_valid_transition_reviewing_to_completed(self, machine):
        """测试有效转换：reviewing → completed"""
        machine.create_task("TASK-003")
        machine.transition("TASK-003", TaskState.IN_PROGRESS)
        machine.transition("TASK-003", TaskState.REVIEWING)
        task = machine.transition("TASK-003", TaskState.COMPLETED, "审查通过")
        assert task.state == TaskState.COMPLETED

    def test_invalid_transition_pending_to_completed(self, machine):
        """测试无效转换：pending → completed"""
        machine.create_task("TASK-INVALID")
        with pytest.raises(InvalidTransitionError):
            machine.transition("TASK-INVALID", TaskState.COMPLETED)

    def test_invalid_transition_completed_to_in_progress(self, machine):
        """测试无效转换：completed → in_progress（终态不可转换）"""
        machine.create_task("TASK-COMPLETED")
        machine.transition("TASK-COMPLETED", TaskState.IN_PROGRESS)
        machine.transition("TASK-COMPLETED", TaskState.REVIEWING)
        machine.transition("TASK-COMPLETED", TaskState.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            machine.transition("TASK-COMPLETED", TaskState.IN_PROGRESS)

    def test_can_transition(self, machine):
        """测试检查转换是否有效"""
        machine.create_task("TASK-CAN")
        assert machine.can_transition("TASK-CAN", TaskState.IN_PROGRESS) is True
        assert machine.can_transition("TASK-CAN", TaskState.COMPLETED) is False

    def test_get_allowed_transitions(self, machine):
        """测试获取允许的转换"""
        machine.create_task("TASK-ALLOWED")
        allowed = machine.get_allowed_transitions("TASK-ALLOWED")
        assert TaskState.IN_PROGRESS in allowed
        assert TaskState.CANCELLED in allowed
        assert TaskState.COMPLETED not in allowed


class TestConvenienceMethods:
    """测试便捷方法"""

    @pytest.fixture
    def machine(self):
        return create_task_state_machine()

    def test_start(self, machine):
        """测试 start 方法"""
        machine.create_task("TASK-START")
        task = machine.start("TASK-START")
        assert task.state == TaskState.IN_PROGRESS

    def test_submit_review(self, machine):
        """测试 submit_review 方法"""
        machine.create_task("TASK-REVIEW")
        machine.start("TASK-REVIEW")
        task = machine.submit_review("TASK-REVIEW")
        assert task.state == TaskState.REVIEWING

    def test_complete(self, machine):
        """测试 complete 方法"""
        machine.create_task("TASK-COMPLETE")
        machine.start("TASK-COMPLETE")
        machine.submit_review("TASK-COMPLETE")
        task = machine.complete("TASK-COMPLETE")
        assert task.state == TaskState.COMPLETED

    def test_reject(self, machine):
        """测试 reject 方法"""
        machine.create_task("TASK-REJECT")
        machine.start("TASK-REJECT")
        machine.submit_review("TASK-REJECT")
        task = machine.reject("TASK-REJECT", "代码需要修改")
        assert task.state == TaskState.IN_PROGRESS

    def test_fail(self, machine):
        """测试 fail 方法"""
        machine.create_task("TASK-FAIL")
        machine.start("TASK-FAIL")
        task = machine.fail("TASK-FAIL", "执行失败")
        assert task.state == TaskState.FAILED

    def test_retry(self, machine):
        """测试 retry 方法"""
        machine.create_task("TASK-RETRY")
        machine.start("TASK-RETRY")
        machine.fail("TASK-RETRY")
        task = machine.retry("TASK-RETRY")
        assert task.state == TaskState.IN_PROGRESS

    def test_cancel(self, machine):
        """测试 cancel 方法"""
        machine.create_task("TASK-CANCEL")
        task = machine.cancel("TASK-CANCEL", "用户取消")
        assert task.state == TaskState.CANCELLED


class TestHooks:
    """测试钩子系统"""

    @pytest.fixture
    def machine(self):
        return create_task_state_machine()

    def test_on_enter_state_hook(self, machine):
        """测试进入状态钩子"""
        hook_called = []

        def my_hook(event):
            hook_called.append(event)

        machine.on_enter_state(TaskState.IN_PROGRESS, my_hook)
        machine.create_task("TASK-HOOK")
        machine.start("TASK-HOOK")

        assert len(hook_called) == 1
        assert hook_called[0].to_state == TaskState.IN_PROGRESS

    def test_on_any_change_hook(self, machine):
        """测试任意变更钩子"""
        changes = []

        def my_hook(event):
            changes.append(event)

        machine.on_any_change(my_hook)
        machine.create_task("TASK-ANY")
        machine.start("TASK-ANY")

        assert len(changes) >= 2  # 创建和状态变更


class TestQueries:
    """测试查询方法"""

    @pytest.fixture
    def machine(self):
        return create_task_state_machine()

    def test_get_tasks_by_state(self, machine):
        """测试按状态获取任务"""
        machine.create_task("TASK-PENDING-1")
        machine.create_task("TASK-PENDING-2")
        machine.create_task("TASK-PROGRESS")
        machine.start("TASK-PROGRESS")

        pending = machine.get_pending_tasks()
        active = machine.get_active_tasks()

        assert len(pending) == 2
        assert len(active) == 1

    def test_get_history(self, machine):
        """测试获取状态历史"""
        machine.create_task("TASK-HISTORY")
        machine.start("TASK-HISTORY")
        machine.submit_review("TASK-HISTORY")

        history = machine.get_history("TASK-HISTORY")
        assert len(history) >= 3  # 创建、开始、提交审查

    def test_get_stats(self, machine):
        """测试获取统计信息"""
        machine.create_task("TASK-STATS-1")
        machine.create_task("TASK-STATS-2")
        machine.start("TASK-STATS-1")

        stats = machine.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["by_state"]["pending"] == 1
        assert stats["by_state"]["in_progress"] == 1


class TestClearCompleted:
    """测试清理已完成任务"""

    @pytest.fixture
    def machine(self):
        return create_task_state_machine()

    def test_clear_completed(self, machine):
        """测试清理已完成的任务"""
        machine.create_task("TASK-OLD")
        machine.start("TASK-OLD")
        machine.submit_review("TASK-OLD")
        machine.complete("TASK-OLD")

        # 修改更新时间以模拟旧任务
        machine._tasks["TASK-OLD"].updated_at = time.time() - 3600 * 25  # 25小时前

        cleared = machine.clear_completed(max_age_hours=24)
        assert cleared == 1
        assert not machine.task_exists("TASK-OLD")


class TestTaskInfoNoMetadata:
    """测试 TaskInfo 不存储 metadata 和 description"""

    def test_task_info_fields(self):
        """验证 TaskInfo 字段"""
        info = TaskInfo(task_id="TASK-001")

        # 确认不再有这些字段（Pydantic 会抛出 AttributeError）
        with pytest.raises(AttributeError):
            _ = info.description
        with pytest.raises(AttributeError):
            _ = info.metadata

    def test_create_task_no_metadata_param(self):
        """测试 create_task 不接受 metadata 参数"""
        machine = create_task_state_machine()

        # 创建任务时不传递 metadata
        task = machine.create_task("TASK-NO-META")

        # 任务应该只有 task_id 和 state
        assert task.task_id == "TASK-NO-META"
        assert task.state == TaskState.PENDING