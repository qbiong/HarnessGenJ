"""
TDD Workflow - 测试驱动开发工作流

提供 TDD 工作流支持：
- Red-Green-Refactor 循环
- 测试覆盖率追踪
- 测试失败修复建议
- 测试优先引导

使用示例:
    from harnessgenj.workflow.tdd_workflow import TDDWorkflow, TDDConfig

    tdd = TDDWorkflow(config=TDDConfig(coverage_threshold=80))

    # 开始 TDD 循环
    cycle = tdd.start_cycle("add_user_function")

    # 写测试 (Red)
    tdd.write_test(cycle, test_code)

    # 写实现 (Green)
    tdd.write_implementation(cycle, impl_code)

    # 重构 (Refactor)
    tdd.refactor(cycle, refactored_code)

    # 完成循环
    result = tdd.complete_cycle(cycle)
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import subprocess
import json


class TDDPhase(Enum):
    """TDD 阶段"""

    RED = "red"           # 写失败的测试
    GREEN = "green"       # 写最少代码通过测试
    REFACTOR = "refactor" # 重构代码


class CycleStatus(Enum):
    """循环状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TEST_WRITTEN = "test_written"
    IMPLEMENTED = "implemented"
    REFACTORED = "refactored"
    COMPLETED = "completed"
    FAILED = "failed"


class TDDConfig(BaseModel):
    """TDD 配置"""

    enabled: bool = Field(default=True, description="是否启用 TDD")
    coverage_threshold: float = Field(default=80.0, description="覆盖率阈值")
    max_refactor_rounds: int = Field(default=3, description="最大重构轮次")
    auto_run_tests: bool = Field(default=True, description="自动运行测试")
    strict_red_phase: bool = Field(default=True, description="严格 Red 阶段（测试必须失败）")
    test_command: str = Field(default="pytest", description="测试命令")
    coverage_command: str = Field(default="pytest --cov --cov-report=json", description="覆盖率命令")


class TestResult(BaseModel):
    """测试结果"""

    passed: int = Field(default=0, description="通过测试数")
    failed: int = Field(default=0, description="失败测试数")
    skipped: int = Field(default=0, description="跳过测试数")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    duration: float = Field(default=0.0, description="执行时间")
    output: str = Field(default="", description="原始输出")


class CoverageReport(BaseModel):
    """覆盖率报告"""

    total_lines: int = Field(default=0, description="总行数")
    covered_lines: int = Field(default=0, description="覆盖行数")
    coverage_percent: float = Field(default=0.0, description="覆盖率百分比")
    missing_lines: list[int] = Field(default_factory=list, description="未覆盖行号")


class TDDCycle(BaseModel):
    """TDD 循环"""

    cycle_id: str
    feature_name: str
    status: CycleStatus = CycleStatus.PENDING
    current_phase: TDDPhase = TDDPhase.RED

    # 代码
    test_code: str = ""
    implementation_code: str = ""
    refactored_code: str = ""

    # 结果
    test_result: TestResult | None = None
    coverage_report: CoverageReport | None = None

    # 时间
    started_at: float = Field(default_factory=time.time)
    test_written_at: float | None = None
    implemented_at: float | None = None
    completed_at: float | None = None

    # 统计
    refactor_rounds: int = 0
    total_iterations: int = 0


class RefactorSuggestion(BaseModel):
    """重构建议"""

    file: str
    line: int
    description: str
    suggestion: str
    priority: int = 0


class TDDWorkflow:
    """
    TDD 工作流管理器

    支持:
    1. Red-Green-Refactor 循环
    2. 测试覆盖率追踪
    3. 测试失败修复建议
    4. 重构建议
    """

    def __init__(
        self,
        config: TDDConfig | None = None,
        test_runner: Callable[[str], TestResult] | None = None,
    ) -> None:
        """
        初始化 TDD 工作流

        Args:
            config: TDD 配置
            test_runner: 自定义测试运行器
        """
        self.config = config or TDDConfig()
        self._test_runner = test_runner
        self._cycles: dict[str, TDDCycle] = {}
        self._stats = {
            "total_cycles": 0,
            "completed_cycles": 0,
            "failed_cycles": 0,
            "average_coverage": 0.0,
        }

    # ==================== 循环管理 ====================

    def start_cycle(self, feature_name: str) -> TDDCycle:
        """
        开始新的 TDD 循环

        Args:
            feature_name: 功能名称

        Returns:
            TDDCycle: 新的循环实例
        """
        import uuid
        cycle_id = f"TDD-{uuid.uuid4().hex[:8]}"

        cycle = TDDCycle(
            cycle_id=cycle_id,
            feature_name=feature_name,
            status=CycleStatus.IN_PROGRESS,
            current_phase=TDDPhase.RED,
        )

        self._cycles[cycle_id] = cycle
        self._stats["total_cycles"] += 1

        return cycle

    def write_test(
        self,
        cycle: TDDCycle,
        test_code: str,
        run_test: bool = True,
    ) -> TestResult:
        """
        写测试 (Red 阶段)

        Args:
            cycle: TDD 循环
            test_code: 测试代码
            run_test: 是否运行测试

        Returns:
            TestResult: 测试结果
        """
        cycle.test_code = test_code
        cycle.current_phase = TDDPhase.RED
        cycle.test_written_at = time.time()

        if run_test and self.config.auto_run_tests:
            result = self._run_test(test_code)
            cycle.test_result = result

            # Red 阶段：测试应该失败
            if self.config.strict_red_phase:
                if result.failed == 0 and result.passed > 0:
                    # 测试通过了，说明功能已经实现，违反 TDD
                    cycle.status = CycleStatus.FAILED
                    return result

            cycle.status = CycleStatus.TEST_WRITTEN
            return result

        return TestResult()

    def write_implementation(
        self,
        cycle: TDDCycle,
        implementation_code: str,
        run_test: bool = True,
    ) -> TestResult:
        """
        写实现 (Green 阶段)

        Args:
            cycle: TDD 循环
            implementation_code: 实现代码
            run_test: 是否运行测试

        Returns:
            TestResult: 测试结果
        """
        cycle.implementation_code = implementation_code
        cycle.current_phase = TDDPhase.GREEN

        if run_test and self.config.auto_run_tests and cycle.test_code:
            # 合并测试和实现
            combined_code = f"{implementation_code}\n\n{cycle.test_code}"
            result = self._run_test(combined_code)
            cycle.test_result = result

            if result.passed > 0 and result.failed == 0:
                cycle.status = CycleStatus.IMPLEMENTED
                cycle.implemented_at = time.time()
            else:
                # 实现不完整，需要继续
                pass

            return result

        cycle.status = CycleStatus.IMPLEMENTED
        cycle.implemented_at = time.time()
        return TestResult()

    def refactor(
        self,
        cycle: TDDCycle,
        refactored_code: str,
        run_test: bool = True,
    ) -> tuple[TestResult, list[RefactorSuggestion]]:
        """
        重构代码 (Refactor 阶段)

        Args:
            cycle: TDD 循环
            refactored_code: 重构后的代码
            run_test: 是否运行测试

        Returns:
            (TestResult, suggestions): 测试结果和重构建议
        """
        cycle.refactored_code = refactored_code
        cycle.current_phase = TDDPhase.REFACTOR
        cycle.refactor_rounds += 1

        suggestions = self._analyze_for_refactor(refactored_code)

        if run_test and self.config.auto_run_tests and cycle.test_code:
            combined_code = f"{refactored_code}\n\n{cycle.test_code}"
            result = self._run_test(combined_code)
            cycle.test_result = result

            # 重构后测试仍然应该通过
            if result.passed > 0 and result.failed == 0:
                cycle.status = CycleStatus.REFACTORED
            else:
                # 重构破坏了功能
                cycle.status = CycleStatus.FAILED

            return result, suggestions

        cycle.status = CycleStatus.REFACTORED
        return TestResult(), suggestions

    def complete_cycle(self, cycle: TDDCycle) -> dict[str, Any]:
        """
        完成 TDD 循环

        Args:
            cycle: TDD 循环

        Returns:
            循环结果
        """
        cycle.completed_at = time.time()

        # 计算覆盖率
        if self.config.auto_run_tests:
            final_code = cycle.refactored_code or cycle.implementation_code
            coverage = self._calculate_coverage(final_code, cycle.test_code)
            cycle.coverage_report = coverage

            # 检查覆盖率是否达标
            if coverage.coverage_percent < self.config.coverage_threshold:
                cycle.status = CycleStatus.FAILED
                self._stats["failed_cycles"] += 1
            else:
                cycle.status = CycleStatus.COMPLETED
                self._stats["completed_cycles"] += 1
        else:
            cycle.status = CycleStatus.COMPLETED
            self._stats["completed_cycles"] += 1

        cycle.total_iterations = cycle.refactor_rounds + 1

        return {
            "cycle_id": cycle.cycle_id,
            "feature_name": cycle.feature_name,
            "status": cycle.status.value,
            "test_result": cycle.test_result.model_dump() if cycle.test_result else None,
            "coverage": cycle.coverage_report.model_dump() if cycle.coverage_report else None,
            "duration": cycle.completed_at - cycle.started_at,
            "iterations": cycle.total_iterations,
        }

    # ==================== 测试运行 ====================

    def _run_test(self, code: str) -> TestResult:
        """运行测试"""
        if self._test_runner:
            return self._test_runner(code)

        # 默认实现：使用 pytest
        try:
            # 创建临时测试文件
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='_test.py',
                delete=False,
            ) as f:
                f.write(code)
                temp_path = f.name

            # 运行 pytest
            result = subprocess.run(
                [self.config.test_command, temp_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # 解析结果
            output = result.stdout + result.stderr
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            skipped = output.count("SKIPPED")

            # 清理临时文件
            import os
            os.unlink(temp_path)

            return TestResult(
                passed=passed,
                failed=failed,
                skipped=skipped,
                output=output,
            )

        except Exception as e:
            return TestResult(
                errors=[str(e)],
            )

    def _calculate_coverage(
        self,
        implementation_code: str,
        test_code: str,
    ) -> CoverageReport:
        """计算覆盖率"""
        # 简化实现：基于行数的估算
        impl_lines = len(implementation_code.strip().split('\n'))

        # 检查测试中是否引用了实现代码的各个部分
        covered = 0
        for line in implementation_code.strip().split('\n'):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            # 简化：假设每个函数调用都会覆盖相关代码
            if any(keyword in test_code for keyword in ['assert', 'call', 'run', 'test']):
                covered += 1

        coverage_percent = (covered / impl_lines * 100) if impl_lines > 0 else 0

        return CoverageReport(
            total_lines=impl_lines,
            covered_lines=covered,
            coverage_percent=min(coverage_percent, 100.0),
        )

    def _analyze_for_refactor(self, code: str) -> list[RefactorSuggestion]:
        """分析代码，生成重构建议"""
        suggestions = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 长行建议
            if len(stripped) > 100:
                suggestions.append(RefactorSuggestion(
                    file="current",
                    line=i,
                    description="行过长",
                    suggestion="考虑将长行拆分为多行",
                    priority=3,
                ))

            # 重复代码检测
            if stripped and stripped in '\n'.join(lines[i:]):
                suggestions.append(RefactorSuggestion(
                    file="current",
                    line=i,
                    description="可能存在重复代码",
                    suggestion="考虑提取为函数或常量",
                    priority=5,
                ))

            # 复杂条件
            if stripped.startswith('if ') and stripped.count('and') + stripped.count('or') > 2:
                suggestions.append(RefactorSuggestion(
                    file="current",
                    line=i,
                    description="条件表达式过于复杂",
                    suggestion="考虑提取条件为变量或函数",
                    priority=4,
                ))

        return suggestions

    # ==================== 修复建议 ====================

    def get_fix_suggestions(self, cycle: TDDCycle) -> list[str]:
        """
        根据测试失败生成修复建议

        Args:
            cycle: TDD 循环

        Returns:
            修复建议列表
        """
        if not cycle.test_result or cycle.test_result.failed == 0:
            return []

        suggestions = []
        output = cycle.test_result.output

        # 分析常见错误
        if "AssertionError" in output:
            suggestions.append("检查断言逻辑是否正确")
            suggestions.append("验证测试数据是否符合预期")

        if "TypeError" in output:
            suggestions.append("检查函数参数类型是否正确")
            suggestions.append("验证返回值类型是否匹配")

        if "NameError" in output:
            suggestions.append("检查是否缺少导入或变量未定义")

        if "AttributeError" in output:
            suggestions.append("检查对象是否具有所需属性")
            suggestions.append("验证对象初始化是否正确")

        if "IndexError" in output:
            suggestions.append("检查列表/数组索引范围")

        if "KeyError" in output:
            suggestions.append("检查字典键是否存在")

        return suggestions

    # ==================== 状态查询 ====================

    def get_cycle(self, cycle_id: str) -> TDDCycle | None:
        """获取循环"""
        return self._cycles.get(cycle_id)

    def list_cycles(self, status: CycleStatus | None = None) -> list[TDDCycle]:
        """列出循环"""
        cycles = list(self._cycles.values())
        if status:
            cycles = [c for c in cycles if c.status == status]
        return cycles

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        completed = [c for c in self._cycles.values() if c.status == CycleStatus.COMPLETED]
        if completed:
            avg_coverage = sum(
                c.coverage_report.coverage_percent for c in completed
                if c.coverage_report
            ) / len(completed)
            self._stats["average_coverage"] = avg_coverage

        return {
            **self._stats,
            "active_cycles": sum(1 for c in self._cycles.values()
                               if c.status in [CycleStatus.IN_PROGRESS, CycleStatus.TEST_WRITTEN]),
        }


# ==================== 便捷函数 ====================

def create_tdd_workflow(config: TDDConfig | None = None) -> TDDWorkflow:
    """创建 TDD 工作流"""
    return TDDWorkflow(config)