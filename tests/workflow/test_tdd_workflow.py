"""
Tests for TDD Workflow Module

测试 TDD 工作流功能:
- Red-Green-Refactor 循环
- 测试覆盖率追踪
- 测试失败修复建议
- 循环状态管理
"""

import pytest
from harnessgenj.workflow.tdd_workflow import (
    TDDWorkflow,
    TDDConfig,
    TDDCycle,
    TDDPhase,
    CycleStatus,
    TestResult,
    CoverageReport,
    RefactorSuggestion,
    create_tdd_workflow,
)


class TestTDDConfig:
    """测试 TDD 配置"""

    def test_create_default_config(self):
        """创建默认配置"""
        config = TDDConfig()
        assert config.enabled is True
        assert config.coverage_threshold == 80.0
        assert config.max_refactor_rounds == 3
        assert config.auto_run_tests is True
        assert config.strict_red_phase is True
        assert config.test_command == "pytest"

    def test_create_custom_config(self):
        """创建自定义配置"""
        config = TDDConfig(
            coverage_threshold=90.0,
            max_refactor_rounds=5,
            strict_red_phase=False,
        )
        assert config.coverage_threshold == 90.0
        assert config.max_refactor_rounds == 5
        assert config.strict_red_phase is False


class TestTestResult:
    """测试测试结果"""

    def test_create_test_result(self):
        """创建测试结果"""
        result = TestResult(
            passed=5,
            failed=2,
            skipped=1,
            duration=1.5,
        )
        assert result.passed == 5
        assert result.failed == 2
        assert result.skipped == 1
        assert result.duration == 1.5

    def test_test_result_with_errors(self):
        """带错误的测试结果"""
        result = TestResult(
            failed=1,
            errors=["AssertionError: expected 5, got 3"],
        )
        assert len(result.errors) == 1


class TestCoverageReport:
    """测试覆盖率报告"""

    def test_create_coverage_report(self):
        """创建覆盖率报告"""
        report = CoverageReport(
            total_lines=100,
            covered_lines=80,
            coverage_percent=80.0,
        )
        assert report.total_lines == 100
        assert report.covered_lines == 80
        assert report.coverage_percent == 80.0

    def test_coverage_with_missing_lines(self):
        """带未覆盖行号的报告"""
        report = CoverageReport(
            total_lines=100,
            covered_lines=75,
            missing_lines=[10, 20, 30, 40, 50],
        )
        assert len(report.missing_lines) == 5


class TestTDDCycle:
    """测试 TDD 循环"""

    def test_create_cycle(self):
        """创建循环"""
        cycle = TDDCycle(
            cycle_id="TDD-001",
            feature_name="add_user",
        )
        assert cycle.cycle_id == "TDD-001"
        assert cycle.feature_name == "add_user"
        assert cycle.status == CycleStatus.PENDING
        assert cycle.current_phase == TDDPhase.RED

    def test_cycle_phase_transitions(self):
        """循环阶段转换"""
        cycle = TDDCycle(cycle_id="TDD-001", feature_name="test")
        cycle.current_phase = TDDPhase.RED
        assert cycle.current_phase == TDDPhase.RED

        cycle.current_phase = TDDPhase.GREEN
        assert cycle.current_phase == TDDPhase.GREEN

        cycle.current_phase = TDDPhase.REFACTOR
        assert cycle.current_phase == TDDPhase.REFACTOR

    def test_cycle_status_transitions(self):
        """循环状态转换"""
        cycle = TDDCycle(cycle_id="TDD-001", feature_name="test")
        cycle.status = CycleStatus.IN_PROGRESS
        assert cycle.status == CycleStatus.IN_PROGRESS

        cycle.status = CycleStatus.TEST_WRITTEN
        assert cycle.status == CycleStatus.TEST_WRITTEN

        cycle.status = CycleStatus.IMPLEMENTED
        assert cycle.status == CycleStatus.IMPLEMENTED

        cycle.status = CycleStatus.COMPLETED
        assert cycle.status == CycleStatus.COMPLETED


class TestTDDWorkflow:
    """测试 TDD 工作流"""

    def test_create_workflow(self):
        """创建工作流"""
        workflow = create_tdd_workflow()
        assert isinstance(workflow, TDDWorkflow)
        assert workflow.config.enabled is True

    def test_create_workflow_with_config(self):
        """创建带配置的工作流"""
        config = TDDConfig(coverage_threshold=95.0)
        workflow = create_tdd_workflow(config)
        assert workflow.config.coverage_threshold == 95.0

    def test_start_cycle(self):
        """开始循环"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("new_feature")

        assert cycle is not None
        assert cycle.feature_name == "new_feature"
        assert cycle.status == CycleStatus.IN_PROGRESS
        assert cycle.current_phase == TDDPhase.RED

        # 检查统计
        stats = workflow.get_stats()
        assert stats["total_cycles"] == 1

    def test_write_test(self):
        """写测试 (Red 阶段)"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature_1")

        test_code = '''
def test_add_numbers():
    assert add(1, 2) == 3
'''
        # 使用自定义测试运行器，避免实际运行 pytest
        def mock_runner(code):
            return TestResult(failed=1, errors=["NameError: add not defined"])

        workflow._test_runner = mock_runner

        result = workflow.write_test(cycle, test_code)
        assert cycle.test_code == test_code
        assert cycle.current_phase == TDDPhase.RED
        # 在 strict_red_phase 模式下，测试失败是正常的
        assert cycle.status == CycleStatus.TEST_WRITTEN

    def test_write_test_passes_in_strict_mode(self):
        """严格模式下测试通过会导致失败"""
        config = TDDConfig(strict_red_phase=True)
        workflow = create_tdd_workflow(config)
        cycle = workflow.start_cycle("feature")

        # 模拟测试通过
        def mock_runner(code):
            return TestResult(passed=1, failed=0)

        workflow._test_runner = mock_runner

        result = workflow.write_test(cycle, "def test(): pass")
        # 严格模式下，Red 阶段测试不应该通过
        assert cycle.status == CycleStatus.FAILED

    def test_write_implementation(self):
        """写实现 (Green 阶段)"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature")

        # 先写测试
        workflow.write_test(cycle, "def test(): pass", run_test=False)

        # 模拟测试通过
        def mock_runner(code):
            return TestResult(passed=1, failed=0)

        workflow._test_runner = mock_runner

        impl_code = '''
def add(a, b):
    return a + b
'''
        result = workflow.write_implementation(cycle, impl_code)
        assert cycle.implementation_code == impl_code
        assert cycle.current_phase == TDDPhase.GREEN
        assert cycle.status == CycleStatus.IMPLEMENTED

    def test_refactor(self):
        """重构代码 (Refactor 阶段)"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature")

        # 设置初始状态
        workflow.write_test(cycle, "def test(): pass", run_test=False)
        workflow.write_implementation(cycle, "def add(a, b): return a + b", run_test=False)

        # 模拟测试通过
        def mock_runner(code):
            return TestResult(passed=1, failed=0)

        workflow._test_runner = mock_runner

        refactored_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        result, suggestions = workflow.refactor(cycle, refactored_code)
        assert cycle.refactored_code == refactored_code
        assert cycle.current_phase == TDDPhase.REFACTOR
        assert cycle.refactor_rounds == 1

    def test_complete_cycle(self):
        """完成循环"""
        config = TDDConfig(auto_run_tests=False)
        workflow = create_tdd_workflow(config)
        cycle = workflow.start_cycle("feature")

        workflow.write_test(cycle, "test code", run_test=False)
        workflow.write_implementation(cycle, "impl code", run_test=False)
        workflow.refactor(cycle, "refactored code", run_test=False)

        result = workflow.complete_cycle(cycle)
        assert cycle.status == CycleStatus.COMPLETED
        assert "cycle_id" in result
        assert "feature_name" in result
        assert "status" in result

        stats = workflow.get_stats()
        assert stats["completed_cycles"] == 1

    def test_complete_cycle_with_coverage_check(self):
        """完成循环并检查覆盖率"""
        config = TDDConfig(coverage_threshold=80.0, auto_run_tests=False)
        workflow = create_tdd_workflow(config)
        cycle = workflow.start_cycle("feature")

        cycle.test_code = "test code"
        cycle.implementation_code = "impl code"

        # 手动设置覆盖率
        cycle.coverage_report = CoverageReport(
            total_lines=100,
            covered_lines=90,
            coverage_percent=90.0,
        )

        result = workflow.complete_cycle(cycle)
        assert cycle.status == CycleStatus.COMPLETED

    def test_complete_cycle_coverage_below_threshold(self):
        """覆盖率低于阈值导致失败"""
        config = TDDConfig(coverage_threshold=80.0, auto_run_tests=False)
        workflow = create_tdd_workflow(config)
        cycle = workflow.start_cycle("feature")

        # 手动设置低覆盖率
        cycle.coverage_report = CoverageReport(
            total_lines=100,
            covered_lines=50,
            coverage_percent=50.0,
        )

        # 强制进行覆盖率检查
        workflow.config.auto_run_tests = True
        result = workflow.complete_cycle(cycle)
        # 覆盖率低于阈值会失败
        assert cycle.status == CycleStatus.FAILED

    def test_get_cycle(self):
        """获取循环"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature")
        cycle_id = cycle.cycle_id

        retrieved = workflow.get_cycle(cycle_id)
        assert retrieved is not None
        assert retrieved.cycle_id == cycle_id

        # 不存在的循环
        retrieved = workflow.get_cycle("nonexistent")
        assert retrieved is None

    def test_list_cycles(self):
        """列出循环"""
        workflow = create_tdd_workflow()
        cycle1 = workflow.start_cycle("feature1")
        cycle2 = workflow.start_cycle("feature2")
        cycle3 = workflow.start_cycle("feature3")

        cycles = workflow.list_cycles()
        assert len(cycles) == 3

        # 按状态过滤 - 需要先完成才能按 COMPLETED 过滤
        workflow._test_runner = lambda code: TestResult(passed=1, failed=0)
        workflow.config.auto_run_tests = False

        # 完成前设置状态
        cycle1.status = CycleStatus.COMPLETED
        completed = workflow.list_cycles(status=CycleStatus.COMPLETED)
        assert len(completed) == 1

    def test_get_fix_suggestions(self):
        """获取修复建议"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature")

        # 设置失败的测试结果
        cycle.test_result = TestResult(
            failed=1,
            output="AssertionError: expected 5, got 3\nTypeError: unsupported operand",
        )

        suggestions = workflow.get_fix_suggestions(cycle)
        assert len(suggestions) > 0
        # 建议应该包含断言相关的提示
        assert any("断言" in s for s in suggestions)

    def test_get_fix_suggestions_no_failure(self):
        """无失败时无建议"""
        workflow = create_tdd_workflow()
        cycle = workflow.start_cycle("feature")

        cycle.test_result = TestResult(passed=1, failed=0)

        suggestions = workflow.get_fix_suggestions(cycle)
        assert len(suggestions) == 0

    def test_analyze_for_refactor(self):
        """重构分析"""
        workflow = create_tdd_workflow()

        # 长行代码 - 需要超过100个字符
        code = '''
def very_long_function_with_many_parameters_and_complex_logic(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p):
    pass
'''
        suggestions = workflow._analyze_for_refactor(code)
        # 检查是否有建议（长行检测）
        assert len(suggestions) >= 1

    def test_analyze_for_refactor_complex_condition(self):
        """复杂条件检测"""
        workflow = create_tdd_workflow()

        code = '''
if a and b and c and d and e:
    pass
'''
        suggestions = workflow._analyze_for_refactor(code)
        assert any("条件表达式过于复杂" in s.description for s in suggestions)

    def test_get_stats(self):
        """获取统计"""
        workflow = create_tdd_workflow()
        cycle1 = workflow.start_cycle("feature1")
        cycle2 = workflow.start_cycle("feature2")

        stats = workflow.get_stats()
        assert stats["total_cycles"] == 2
        assert stats["active_cycles"] == 2


class TestTDDPhase:
    """测试 TDD 阶段枚举"""

    def test_red_phase(self):
        """Red 阶段"""
        assert TDDPhase.RED.value == "red"

    def test_green_phase(self):
        """Green 阶段"""
        assert TDDPhase.GREEN.value == "green"

    def test_refactor_phase(self):
        """Refactor 阶段"""
        assert TDDPhase.REFACTOR.value == "refactor"


class TestCycleStatus:
    """测试循环状态枚举"""

    def test_pending_status(self):
        """Pending 状态"""
        assert CycleStatus.PENDING.value == "pending"

    def test_in_progress_status(self):
        """In Progress 状态"""
        assert CycleStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_status(self):
        """Completed 状态"""
        assert CycleStatus.COMPLETED.value == "completed"

    def test_failed_status(self):
        """Failed 状态"""
        assert CycleStatus.FAILED.value == "failed"


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_tdd_workflow(self):
        """创建 TDD 工作流"""
        workflow = create_tdd_workflow()
        assert isinstance(workflow, TDDWorkflow)

    def test_create_tdd_workflow_with_config(self):
        """创建带配置的 TDD 工作流"""
        config = TDDConfig(coverage_threshold=95.0)
        workflow = create_tdd_workflow(config)
        assert workflow.config.coverage_threshold == 95.0