"""
Dependency Graph - 任务依赖图管理

提供任务依赖关系的高级管理能力：
- 循环依赖检测
- 依赖图可视化 (Mermaid)
- 影响分析
- 拓扑排序

使用示例:
    from harnessgenj.workflow.dependency import DependencyGraph

    graph = DependencyGraph()
    graph.add_task("design", [])
    graph.add_task("develop", ["design"])
    graph.add_task("test", ["develop"])

    # 检测循环依赖
    if graph.has_cycle():
        print("存在循环依赖!")

    # 生成 Mermaid 图
    print(graph.to_mermaid())
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskNode(BaseModel):
    """任务节点"""

    task_id: str = Field(..., description="任务ID")
    name: str = Field(default="", description="任务名称")
    dependencies: list[str] = Field(default_factory=list, description="依赖任务ID列表")
    dependents: list[str] = Field(default_factory=list, description="被依赖的任务ID列表")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class DependencyGraph:
    """
    任务依赖图

    支持:
    1. 添加任务和依赖关系
    2. 循环依赖检测
    3. 影响分析（修改任务时标记受影响任务）
    4. 拓扑排序
    5. Mermaid 可视化
    """

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}

    # ==================== 节点管理 ====================

    def add_task(
        self,
        task_id: str,
        dependencies: list[str] | None = None,
        name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        添加任务节点

        Args:
            task_id: 任务ID
            dependencies: 依赖任务ID列表
            name: 任务名称
            metadata: 元数据

        Returns:
            是否添加成功（如果存在循环依赖则返回 False）
        """
        if task_id in self._nodes:
            return False

        dependencies = dependencies or []
        node = TaskNode(
            task_id=task_id,
            name=name or task_id,
            dependencies=dependencies,
            metadata=metadata or {},
        )

        # 暂时添加节点
        self._nodes[task_id] = node

        # 检查是否引入循环依赖
        if self._has_cycle_from(task_id):
            # 回滚
            del self._nodes[task_id]
            return False

        # 更新依赖节点的 dependents 列表
        for dep_id in dependencies:
            if dep_id in self._nodes:
                self._nodes[dep_id].dependents.append(task_id)

        return True

    def remove_task(self, task_id: str) -> bool:
        """移除任务节点"""
        if task_id not in self._nodes:
            return False

        node = self._nodes[task_id]

        # 从依赖节点的 dependents 中移除
        for dep_id in node.dependencies:
            if dep_id in self._nodes:
                self._nodes[dep_id].dependents.remove(task_id)

        # 从被依赖节点的 dependencies 中移除
        for dependent_id in node.dependents:
            if dependent_id in self._nodes:
                self._nodes[dependent_id].dependencies.remove(task_id)

        del self._nodes[task_id]
        return True

    def get_task(self, task_id: str) -> TaskNode | None:
        """获取任务节点"""
        return self._nodes.get(task_id)

    def list_tasks(self) -> list[TaskNode]:
        """列出所有任务"""
        return list(self._nodes.values())

    # ==================== 依赖检测 ====================

    def has_cycle(self) -> bool:
        """
        检测是否存在循环依赖

        Returns:
            是否存在循环依赖
        """
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def _has_cycle_from(self, start_id: str) -> bool:
        """检测从指定节点开始是否存在循环"""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        return dfs(start_id)

    def find_cycle(self) -> list[str] | None:
        """
        查找循环依赖路径

        Returns:
            循环路径列表，如果不存在则返回 None
        """
        visited = set()
        rec_stack = []
        path = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.append(node_id)

            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id in rec_stack:
                        # 找到循环
                        cycle_start = rec_stack.index(dep_id)
                        return rec_stack[cycle_start:] + [dep_id]
                    if dep_id not in visited:
                        result = dfs(dep_id)
                        if result:
                            return result

            rec_stack.pop()
            return None

        for node_id in self._nodes:
            if node_id not in visited:
                result = dfs(node_id)
                if result:
                    return result

        return None

    # ==================== 执行顺序 ====================

    def topological_sort(self) -> list[str]:
        """
        拓扑排序

        Returns:
            拓扑排序后的任务ID列表
        """
        in_degree = {node_id: 0 for node_id in self._nodes}

        for node_id, node in self._nodes.items():
            for dep_id in node.dependencies:
                if dep_id in in_degree:
                    in_degree[node_id] += 1

        # 使用优先级队列保证稳定性
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # 按字母顺序排序保证稳定性
            queue.sort()
            node_id = queue.pop(0)
            result.append(node_id)

            node = self._nodes.get(node_id)
            if node:
                for dependent_id in node.dependents:
                    if dependent_id in in_degree:
                        in_degree[dependent_id] -= 1
                        if in_degree[dependent_id] == 0:
                            queue.append(dependent_id)

        return result if len(result) == len(self._nodes) else []

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """
        获取可以执行的任务

        Args:
            completed: 已完成的任务ID集合

        Returns:
            可以执行的任务ID列表
        """
        ready = []
        for node_id, node in self._nodes.items():
            if node_id in completed:
                continue
            if node.status == TaskStatus.COMPLETED:
                continue
            if all(dep_id in completed for dep_id in node.dependencies):
                ready.append(node_id)
        return ready

    def get_blocked_tasks(self, failed: set[str]) -> list[str]:
        """
        获取被阻塞的任务

        Args:
            failed: 失败的任务ID集合

        Returns:
            被阻塞的任务ID列表
        """
        blocked = set()
        for failed_id in failed:
            node = self._nodes.get(failed_id)
            if node:
                self._collect_dependents(failed_id, blocked)
        return list(blocked)

    def _collect_dependents(self, task_id: str, collected: set[str]) -> None:
        """递归收集所有依赖指定任务的节点"""
        node = self._nodes.get(task_id)
        if node:
            for dependent_id in node.dependents:
                if dependent_id not in collected:
                    collected.add(dependent_id)
                    self._collect_dependents(dependent_id, collected)

    # ==================== 影响分析 ====================

    def analyze_impact(self, task_id: str) -> dict[str, Any]:
        """
        分析修改任务的影响范围

        Args:
            task_id: 任务ID

        Returns:
            影响分析结果
        """
        if task_id not in self._nodes:
            return {"error": f"Task not found: {task_id}"}

        node = self._nodes[task_id]

        # 收集所有上游依赖
        upstream = set()
        self._collect_upstream(task_id, upstream)

        # 收集所有下游依赖
        downstream = set()
        self._collect_downstream(task_id, downstream)

        return {
            "task_id": task_id,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "upstream_tasks": list(upstream),
            "downstream_tasks": list(downstream),
            "risk_level": self._calculate_risk(len(upstream), len(downstream)),
        }

    def _collect_upstream(self, task_id: str, collected: set[str]) -> None:
        """递归收集所有上游依赖"""
        node = self._nodes.get(task_id)
        if node:
            for dep_id in node.dependencies:
                if dep_id not in collected:
                    collected.add(dep_id)
                    self._collect_upstream(dep_id, collected)

    def _collect_downstream(self, task_id: str, collected: set[str]) -> None:
        """递归收集所有下游依赖"""
        node = self._nodes.get(task_id)
        if node:
            for dependent_id in node.dependents:
                if dependent_id not in collected:
                    collected.add(dependent_id)
                    self._collect_downstream(dependent_id, collected)

    def _calculate_risk(self, upstream_count: int, downstream_count: int) -> str:
        """计算风险等级"""
        total = upstream_count + downstream_count
        if total == 0:
            return "low"
        elif total <= 3:
            return "medium"
        elif total <= 7:
            return "high"
        else:
            return "critical"

    # ==================== 可视化 ====================

    def to_mermaid(self, title: str = "Dependency Graph") -> str:
        """
        生成 Mermaid 图表代码

        Args:
            title: 图表标题

        Returns:
            Mermaid 代码字符串
        """
        lines = [f"```mermaid", f"graph TD", f"    title[{title}]"]

        # 添加节点
        for node_id, node in self._nodes.items():
            label = node.name or node_id
            status_color = {
                TaskStatus.PENDING: "",
                TaskStatus.RUNNING: ":::running",
                TaskStatus.COMPLETED: ":::completed",
                TaskStatus.FAILED: ":::failed",
                TaskStatus.BLOCKED: ":::blocked",
            }.get(node.status, "")
            lines.append(f"    {node_id}[{label}]{status_color}")

        # 添加边
        for node in self._nodes.values():
            for dep_id in node.dependencies:
                if dep_id in self._nodes:
                    lines.append(f"    {dep_id} --> {node.task_id}")

        # 添加样式
        lines.extend([
            "",
            "    classDef completed fill:#90EE90,stroke:#228B22",
            "    classDef running fill:#FFD700,stroke:#DAA520",
            "    classDef failed fill:#FF6B6B,stroke:#DC143C",
            "    classDef blocked fill:#D3D3D3,stroke:#A9A9A9",
            "```",
        ])

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """导出为 JSON 格式"""
        return {
            "nodes": {
                node_id: {
                    "name": node.name,
                    "dependencies": node.dependencies,
                    "dependents": node.dependents,
                    "status": node.status.value,
                }
                for node_id, node in self._nodes.items()
            },
            "has_cycle": self.has_cycle(),
            "topological_order": self.topological_sort(),
        }

    # ==================== 状态管理 ====================

    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        if task_id not in self._nodes:
            return False
        self._nodes[task_id].status = status
        return True

    def mark_completed(self, task_id: str) -> bool:
        """标记任务完成"""
        return self.update_status(task_id, TaskStatus.COMPLETED)

    def mark_failed(self, task_id: str) -> bool:
        """标记任务失败"""
        return self.update_status(task_id, TaskStatus.FAILED)

    def reset(self) -> None:
        """重置所有任务状态"""
        for node in self._nodes.values():
            node.status = TaskStatus.PENDING

    def clear(self) -> None:
        """清空所有节点"""
        self._nodes.clear()


# ==================== 便捷函数 ====================

def create_dependency_graph(tasks: list[dict[str, Any]]) -> DependencyGraph:
    """
    从任务列表创建依赖图

    Args:
        tasks: 任务列表，每个任务包含 id, name, dependencies 字段

    Returns:
        DependencyGraph 实例
    """
    graph = DependencyGraph()
    for task in tasks:
        graph.add_task(
            task_id=task.get("id", ""),
            name=task.get("name", ""),
            dependencies=task.get("dependencies", []),
            metadata=task.get("metadata"),
        )
    return graph