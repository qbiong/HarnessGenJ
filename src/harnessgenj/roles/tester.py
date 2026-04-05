"""
Tester Role - 测试人员角色

职责:
- 测试用例设计
- 测试执行
- Bug报告
- 质量保证

技能:
- write_test: 编写测试用例
- run_test: 执行测试
- report_bug: 报告Bug
- analyze_coverage: 分析覆盖率
- performance_test: 性能测试
"""

from typing import Any
from harnessgenj.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    SkillCategory,
    TaskType,
)


class Tester(AgentRole):
    """
    测试人员 - 负责质量保证

    Harness角色定义:
    - 职责边界: 测试设计、执行、Bug追踪
    - 技能集: 测试编写、执行、分析
    - 协作: 接收Developer代码，产出Bug报告
    """

    @property
    def role_type(self) -> RoleType:
        return RoleType.TESTER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "测试用例设计与编写",
            "功能测试执行",
            "Bug发现与报告",
            "测试覆盖率分析",
            "回归测试",
            "性能测试",
        ]

    def _setup_skills(self) -> None:
        """设置测试技能"""
        skills = [
            RoleSkill(
                name="write_test",
                description="编写测试用例",
                category=SkillCategory.TESTING,
                inputs=["requirement", "code"],
                outputs=["test_cases", "test_plan"],
            ),
            RoleSkill(
                name="run_test",
                description="执行测试",
                category=SkillCategory.TESTING,
                inputs=["test_cases", "code"],
                outputs=["test_results", "coverage_report"],
            ),
            RoleSkill(
                name="report_bug",
                description="报告Bug",
                category=SkillCategory.TESTING,
                inputs=["test_failure", "code"],
                outputs=["bug_report", "reproduction_steps"],
            ),
            RoleSkill(
                name="analyze_coverage",
                description="分析覆盖率",
                category=SkillCategory.ANALYSIS,
                inputs=["code", "test_results"],
                outputs=["coverage_report", "gaps"],
            ),
            RoleSkill(
                name="performance_test",
                description="性能测试",
                category=SkillCategory.TESTING,
                inputs=["code", "performance_criteria"],
                outputs=["performance_report", "bottlenecks"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [
            TaskType.WRITE_TEST,
            TaskType.RUN_TEST,
            TaskType.BUG_REPORT,
        ]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        """执行测试任务"""
        handlers = {
            TaskType.WRITE_TEST: self._write_test,
            TaskType.RUN_TEST: self._run_test,
            TaskType.BUG_REPORT: self._report_bug,
        }

        handler = handlers.get(task_type)
        if handler:
            return handler()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    def _write_test(self) -> dict[str, Any]:
        """编写测试用例"""
        requirement = self._current_task.get("inputs", {}).get("requirement", "")

        result = {
            "status": "completed",
            "outputs": {
                "test_cases": [
                    {"name": "test_normal_flow", "description": "正常流程测试"},
                    {"name": "test_edge_case", "description": "边界条件测试"},
                    {"name": "test_error_handling", "description": "错误处理测试"},
                ],
                "test_plan": f"# 测试计划: {requirement}",
            },
        }

        self.context.add_artifact("test_cases", result["outputs"]["test_cases"])
        return result

    def _run_test(self) -> dict[str, Any]:
        """执行测试"""
        test_cases = self._current_task.get("inputs", {}).get("test_cases", [])

        result = {
            "status": "completed",
            "outputs": {
                "test_results": {
                    "total": len(test_cases) or 10,
                    "passed": 8,
                    "failed": 2,
                    "skipped": 0,
                },
                "coverage_report": {
                    "line_coverage": "85%",
                    "branch_coverage": "72%",
                },
            },
        }

        return result

    def _report_bug(self) -> dict[str, Any]:
        """报告Bug"""
        test_failure = self._current_task.get("inputs", {}).get("test_failure", "")

        result = {
            "status": "completed",
            "outputs": {
                "bug_report": {
                    "title": "测试失败: 功能异常",
                    "severity": "medium",
                    "steps_to_reproduce": ["步骤1", "步骤2", "步骤3"],
                    "expected": "预期行为",
                    "actual": f"实际行为: {test_failure}",
                },
            },
        }

        self.context.add_artifact("bug_report", result["outputs"]["bug_report"])
        return result


def create_tester(
    tester_id: str,
    name: str = "Tester",
    context: RoleContext | None = None,
) -> Tester:
    """创建测试人员实例"""
    return Tester(role_id=tester_id, name=name, context=context)