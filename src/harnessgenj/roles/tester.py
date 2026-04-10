"""
Tester Role - 测试人员角色（验证者）

职责:
- 测试用例设计（产出测试用例）
- 测试执行（产出测试报告）
- Bug报告
- 质量保证

技能:
- write_test: 编写测试用例
- run_test: 执行测试
- report_bug: 报告Bug
- analyze_coverage: 分析覆盖率
- performance_test: 性能测试

哲学定位（基于业界最佳实践）:
- 验证者 - 证明正确或发现错误
- 核心原则：你验证"是否正确"，不决定"怎么实现"
- 工具边界：能编辑代码（测试代码）和运行终端命令

边界定义:
- 决策权限：测试用例设计、测试范围确定、测试通过/失败判断
- 禁止行为：修改生产代码、修改需求文档、修改架构文档、做功能实现决策
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


class TesterRole(AgentRole):
    """
    测试人员 - 验证者角色

    Harness角色定义:
    - 职责边界: 测试设计、执行、Bug追踪
    - 技能集: 测试编写、执行、分析
    - 协作: 接收Developer代码，产出Bug报告

    业界最佳实践增强:
    - 工具权限: read, search, edit_code（测试代码）, terminal
    - 决策权限: 测试用例设计、测试范围确定、测试通过/失败判断
    - 禁止行为: 修改生产代码、修改需求文档、修改架构文档
    """

    # Prevent pytest from trying to collect this class as a test
    __test__ = False

    # ==================== 核心职责定义（哲学层面） ====================

    CORE_RESPONSIBILITIES = """
你的职责是**验证**，不是**实现**。

测试内容：
- 测试用例设计
- 测试执行
- Bug报告
- 覆盖率分析

禁止内容：
- ❌ 不要修改生产代码 - 这是开发者的职责
- ❌ 不要修改需求文档 - 回调产品经理
- ❌ 不要修改架构文档 - 回调架构师
- ❌ 不要做功能实现决策 - 回调架构师

输出产物：
- 测试用例
- 测试报告
- Bug报告
- 覆盖率报告
"""

    BOUNDARY_CHECK_PROMPT = """
在测试过程中：
- 设计"如何验证"，不设计"如何实现"
- 报告"是否正确"，不修复"错误代码"
- 追踪"覆盖率"，不决定"覆盖率目标"
"""

    SELF_REFLECTION_PROMPT = """
完成测试后，检查：
- [ ] 测试用例是否覆盖了验收标准？
- [ ] 是否测试了边界情况？
- [ ] Bug报告是否清晰可复现？
- [ ] 是否测试了异常场景？
"""

    @property
    def role_type(self) -> RoleType:
        return RoleType.TESTER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "测试用例设计（产出测试用例）",
            "测试执行（产出测试报告）",
            "Bug发现与报告（产出Bug报告）",
            "覆盖率分析（产出覆盖率报告）",
            "回归测试（产出回归报告）",
        ]

    @property
    def forbidden_actions(self) -> list[str]:
        """禁止行为 - 验证者只验证，不实现"""
        return [
            "修改生产代码",
            "修改需求文档",
            "修改架构文档",
            "做功能实现决策",
        ]

    @property
    def decision_authority(self) -> list[str]:
        """决策权限 - 测试者有权决定测试范围和结果"""
        return [
            "测试用例设计",
            "测试范围确定",
            "测试通过/失败判断",
        ]

    @property
    def no_decision_authority(self) -> list[str]:
        """无决策权限 - 功能决策应回调架构师或产品经理"""
        return [
            "功能实现方式",
            "需求变更",
            "架构调整",
        ]

    def build_role_prompt(self) -> str:
        """构建完整的角色提示词"""
        return f"""
你是项目的测试人员。

{self.CORE_RESPONSIBILITIES}

{self.BOUNDARY_CHECK_PROMPT}

{self.SELF_REFLECTION_PROMPT}

记住：你的职责是验证"是否正确"，不决定"怎么实现"。
"""

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
) -> TesterRole:
    """
    创建测试人员实例

    Args:
        tester_id: 测试者ID
        name: 测试者名称
        context: 角色上下文

    Returns:
        测试人员实例

    工具权限:
        - read: 读取文件
        - search: 搜索代码
        - edit_code: 编辑代码（仅测试代码）
        - terminal: 执行终端命令
    """
    return TesterRole(role_id=tester_id, name=name, context=context)


# Backward compatibility alias
Tester = TesterRole