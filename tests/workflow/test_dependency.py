"""
Tests for Workflow Dependency Module

测试任务依赖图功能:
- 节点添加和状态管理
- 依赖关系建立
- 循环依赖检测
- 拓扑排序
- Mermaid 可视化
"""

import pytest
from harnessgenj.workflow.dependency import (
    DependencyGraph,
    TaskNode,
    TaskStatus,
    create_dependency_graph,
)


class TestTaskNode:
    """测试任务节点"""

    def test_create_task_node(self):
        """创建任务节点"""
        node = TaskNode(
            task_id="task_1",
            name="Test Task",
        )
        assert node.task_id == "task_1"
        assert node.status == TaskStatus.PENDING
        assert len(node.dependencies) == 0
        assert len(node.dependents) == 0

    def test_task_node_with_dependencies(self):
        """带依赖的任务节点"""
        node = TaskNode(
            task_id="task_2",
            name="Dependent Task",
            dependencies=["task_1"],
        )
        assert "task_1" in node.dependencies

    def test_task_status_enum(self):
        """任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.BLOCKED.value == "blocked"


class TestDependencyGraph:
    """测试依赖图"""

    def test_add_task(self):
        """添加任务"""
        graph = DependencyGraph()
        result = graph.add_task("task_1", name="First Task")
        assert result is True
        node = graph.get_task("task_1")
        assert node is not None
        assert node.name == "First Task"

    def test_add_task_with_dependencies(self):
        """添加带依赖的任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])

        node_2 = graph.get_task("task_2")
        assert "task_1" in node_2.dependencies

        node_1 = graph.get_task("task_1")
        assert "task_2" in node_1.dependents

    def test_add_duplicate_task(self):
        """添加重复任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        result = graph.add_task("task_1")
        assert result is False

    def test_cycle_detection(self):
        """循环依赖检测"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        # 尝试创建循环: task_1 -> task_2 -> task_1
        result = graph.add_task("task_1", dependencies=["task_2"])
        # 应该失败因为 task_1 已存在
        assert result is False

    def test_has_cycle_no_cycle(self):
        """无循环依赖"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        graph.add_task("task_3", dependencies=["task_2"])

        assert not graph.has_cycle()

    def test_topological_sort(self):
        """拓扑排序"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        graph.add_task("task_3", dependencies=["task_2"])
        graph.add_task("task_4", dependencies=["task_2"])

        order = graph.topological_sort()
        assert len(order) == 4
        # task_1 应在 task_2 之前
        assert order.index("task_1") < order.index("task_2")
        # task_2 应在 task_3 和 task_4 之前
        assert order.index("task_2") < order.index("task_3")
        assert order.index("task_2") < order.index("task_4")

    def test_get_ready_tasks(self):
        """获取就绪任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        graph.add_task("task_3", dependencies=["task_1"])

        # 只有 task_1 就绪
        ready = graph.get_ready_tasks(set())
        assert len(ready) == 1
        assert "task_1" in ready

        # 完成 task_1 后
        ready = graph.get_ready_tasks({"task_1"})
        assert len(ready) == 2
        assert "task_2" in ready
        assert "task_3" in ready

    def test_update_status(self):
        """更新任务状态"""
        graph = DependencyGraph()
        graph.add_task("task_1")

        result = graph.update_status("task_1", TaskStatus.RUNNING)
        assert result is True
        assert graph.get_task("task_1").status == TaskStatus.RUNNING

    def test_mark_completed(self):
        """标记任务完成"""
        graph = DependencyGraph()
        graph.add_task("task_1")

        result = graph.mark_completed("task_1")
        assert result is True
        assert graph.get_task("task_1").status == TaskStatus.COMPLETED

    def test_mark_failed(self):
        """标记任务失败"""
        graph = DependencyGraph()
        graph.add_task("task_1")

        result = graph.mark_failed("task_1")
        assert result is True
        assert graph.get_task("task_1").status == TaskStatus.FAILED

    def test_analyze_impact(self):
        """影响分析"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        graph.add_task("task_3", dependencies=["task_2"])
        graph.add_task("task_4", dependencies=["task_2"])

        impact = graph.analyze_impact("task_2")
        assert impact["task_id"] == "task_2"
        assert impact["downstream_count"] == 2
        assert "task_3" in impact["downstream_tasks"]
        assert "task_4" in impact["downstream_tasks"]

    def test_to_mermaid(self):
        """Mermaid 可视化"""
        graph = DependencyGraph()
        graph.add_task("task_1", name="Base")
        graph.add_task("task_2", name="Middle", dependencies=["task_1"])
        graph.add_task("task_3", name="Top", dependencies=["task_2"])

        mermaid = graph.to_mermaid()
        assert "```mermaid" in mermaid
        assert "graph TD" in mermaid
        assert "task_1" in mermaid
        assert "task_2" in mermaid
        assert "task_3" in mermaid

    def test_remove_task(self):
        """移除任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])

        result = graph.remove_task("task_1")
        assert result is True
        assert graph.get_task("task_1") is None
        # task_2 的依赖列表应该被更新
        node_2 = graph.get_task("task_2")
        assert node_2 is not None
        assert "task_1" not in node_2.dependencies

    def test_clear(self):
        """清空图"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2")

        graph.clear()
        assert len(graph.list_tasks()) == 0

    def test_list_tasks(self):
        """列出所有任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2")
        graph.add_task("task_3")

        tasks = graph.list_tasks()
        assert len(tasks) == 3

    def test_to_json(self):
        """导出为 JSON"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])

        data = graph.to_json()
        assert "nodes" in data
        assert "has_cycle" in data
        assert "topological_order" in data
        assert len(data["nodes"]) == 2

    def test_get_blocked_tasks(self):
        """获取被阻塞的任务"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])
        graph.add_task("task_3", dependencies=["task_2"])

        blocked = graph.get_blocked_tasks({"task_1"})
        assert "task_2" in blocked
        assert "task_3" in blocked

    def test_find_cycle(self):
        """查找循环路径"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2", dependencies=["task_1"])

        # 手动创建循环（绕过 add_task 的检测）
        graph._nodes["task_1"].dependencies.append("task_2")

        cycle = graph.find_cycle()
        assert cycle is not None

    def test_reset(self):
        """重置所有状态"""
        graph = DependencyGraph()
        graph.add_task("task_1")
        graph.add_task("task_2")

        graph.mark_completed("task_1")
        graph.update_status("task_2", TaskStatus.RUNNING)

        graph.reset()
        for task in graph.list_tasks():
            assert task.status == TaskStatus.PENDING


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_dependency_graph(self):
        """从任务列表创建依赖图"""
        tasks = [
            {"id": "task_1", "name": "First"},
            {"id": "task_2", "name": "Second", "dependencies": ["task_1"]},
            {"id": "task_3", "name": "Third", "dependencies": ["task_2"]},
        ]
        graph = create_dependency_graph(tasks)
        assert len(graph.list_tasks()) == 3