"""
Task Adversarial Controller - 任务级对抗控制器

管理单个任务的开发-审查-修复循环

核心功能：
1. 自动触发对抗审查
2. 管理对抗轮次
3. 协调生成器和判别器
4. 记录对抗结果
"""

from typing import Any
from pydantic import BaseModel, Field
import time

from harnessgenj.quality.score import ScoreManager
from harnessgenj.quality.tracker import QualityTracker
from harnessgenj.quality.record import AdversarialRecord, IssueRecord, IssueSeverity


class TaskAdversarialConfig(BaseModel):
    """任务级对抗配置"""

    max_rounds: int = Field(default=3, description="最大对抗轮次")
    intensity: str = Field(default="normal", description="审查强度: normal | aggressive")
    auto_fix: bool = Field(default=True, description="是否自动修复")
    quality_threshold: float = Field(default=70.0, description="通过阈值")


class TaskAdversarialResult(BaseModel):
    """任务级对抗结果"""

    task_id: str = Field(..., description="任务ID")
    generator_id: str = Field(..., description="生成者ID")
    discriminator_id: str = Field(..., description="审查者ID")
    final_result: str = Field(default="pending", description="最终结果: passed | failed")
    rounds: int = Field(default=0, description="对抗轮次")
    issues_found: int = Field(default=0, description="发现问题数")
    issues_fixed: int = Field(default=0, description="修复问题数")
    quality_score: float = Field(default=50.0, description="最终质量分数")
    duration: float = Field(default=0.0, description="总耗时")
    record: AdversarialRecord | None = Field(default=None, description="完整对抗记录")


class TaskAdversarialController:
    """
    任务级对抗控制器

    管理单个任务的开发-审查-修复循环

    使用示例：
        controller = TaskAdversarialController(score_manager, quality_tracker)

        # 执行带对抗审查的任务
        result = controller.execute_with_adversarial(
            task={"id": "TASK-001", "description": "实现登录功能"},
            generator=developer_role,
            discriminator=code_reviewer_role,
        )
    """

    def __init__(
        self,
        score_manager: ScoreManager,
        quality_tracker: QualityTracker,
        max_rounds: int = 3,
        intensity: str = "normal",
    ) -> None:
        self.score_manager = score_manager
        self.quality_tracker = quality_tracker
        self.config = TaskAdversarialConfig(
            max_rounds=max_rounds,
            intensity=intensity,
        )

    def execute_with_adversarial(
        self,
        task: dict[str, Any],
        generator: Any,
        discriminator: Any | None = None,
        initial_output: str | None = None,
    ) -> TaskAdversarialResult:
        """
        执行任务并自动触发对抗审查

        流程：
        1. 生成器执行任务产生初始输出
        2. 判别器审查输出发现问题
        3. 如有问题，生成器修复后重新审查
        4. 最多进行 max_rounds 轮对抗
        5. 记录对抗结果并更新积分

        Args:
            task: 任务信息
            generator: 生成器角色
            discriminator: 判别器角色（可选，自动选择）
            initial_output: 初始输出（可选）

        Returns:
            对抗结果
        """
        start_time = time.time()

        task_id = task.get("id", "TASK-UNKNOWN")

        # 注册角色
        gen_id = generator.role_id if hasattr(generator, "role_id") else f"gen_{task_id}"
        disc_id = discriminator.role_id if discriminator else f"disc_{task_id}"

        self.score_manager.register_role(
            generator.role_type.value if hasattr(generator, "role_type") else "developer",
            gen_id,
            generator.name if hasattr(generator, "name") else "生成器",
        )

        if discriminator:
            self.score_manager.register_role(
                discriminator.role_type.value if hasattr(discriminator, "role_type") else "code_reviewer",
                disc_id,
                discriminator.name if hasattr(discriminator, "name") else "审查者",
            )

        # 创建对抗记录
        record = AdversarialRecord(
            task_id=task_id,
            generator_id=gen_id,
            discriminator_id=disc_id,
            max_rounds=self.config.max_rounds,
        )

        # 执行对抗循环
        current_round = 1
        all_issues: list[IssueRecord] = []
        current_output = initial_output

        while current_round <= self.config.max_rounds:
            # 模拟审查过程
            issues = self._simulate_review(current_output, current_round)

            # 记录本轮
            record.add_round(
                round_num=current_round,
                generator_output=current_output or "",
                discriminator_findings=issues,
            )

            all_issues.extend(issues)

            if not issues:
                # 无问题，通过审查
                break

            if self.config.auto_fix and current_round < self.config.max_rounds:
                # 模拟修复
                current_output = self._simulate_fix(current_output, issues)
                current_round += 1
            else:
                # 不自动修复或已达到最大轮次
                break

        # 计算最终结果
        final_result = "passed" if len(all_issues) == 0 or current_round <= self.config.max_rounds else "failed"
        quality_score = self._calculate_quality_score(all_issues, current_round)

        # 更新对抗记录
        record.complete(final_result)

        # 更新积分
        if final_result == "passed":
            self.score_manager.on_task_success(gen_id, current_round, task_id)
        else:
            self.score_manager.on_task_failed(gen_id, task_id)

        # 记录发现的问题
        for issue in all_issues:
            self.score_manager.on_issue_found(
                gen_id, disc_id,
                issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                task_id, issue.description,
            )

        # 保存对抗记录
        self.quality_tracker.record_adversarial(record)

        duration = time.time() - start_time

        return TaskAdversarialResult(
            task_id=task_id,
            generator_id=gen_id,
            discriminator_id=disc_id,
            final_result=final_result,
            rounds=current_round,
            issues_found=len(all_issues),
            issues_fixed=len(all_issues) if final_result == "passed" else 0,
            quality_score=quality_score,
            duration=duration,
            record=record,
        )

    def _simulate_review(self, output: str | None, round_num: int) -> list[IssueRecord]:
        """
        模拟审查过程

        实际实现中，这里会调用判别器角色进行真正的审查

        Args:
            output: 当前输出
            round_num: 当前轮次

        Returns:
            发现的问题列表
        """
        # 这是模拟实现，实际应该调用判别器
        # 在真实场景中，判别器会分析代码/文档并返回具体问题

        issues = []

        # 第一轮通常会发现一些问题（模拟）
        if output and round_num == 1:
            # 模拟发现一些常见问题
            if "error" not in output.lower() and "exception" not in output.lower():
                # 缺少错误处理
                pass  # 实际应该创建 IssueRecord

        return issues

    def _simulate_fix(self, output: str | None, issues: list[IssueRecord]) -> str:
        """
        模拟修复过程

        实际实现中，这里会调用生成器角色进行真正的修复

        Args:
            output: 当前输出
            issues: 待修复问题

        Returns:
            修复后的输出
        """
        # 这是模拟实现，实际应该调用生成器
        # 在真实场景中，生成器会根据问题修复代码/文档

        if output is None:
            return ""

        # 模拟修复后的输出
        fixed_output = output

        for issue in issues:
            # 根据问题类型添加相应内容
            if "error" in issue.description.lower():
                fixed_output += "\n# Added error handling"

        return fixed_output

    def _calculate_quality_score(
        self,
        issues: list[IssueRecord],
        rounds: int,
    ) -> float:
        """
        计算质量分数

        Args:
            issues: 发现的问题列表
            rounds: 对抗轮次

        Returns:
            质量分数 (0-100)
        """
        base_score = 100.0

        # 问题扣分
        for issue in issues:
            severity = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            if severity == "critical":
                base_score -= 20
            elif severity == "major":
                base_score -= 10
            else:
                base_score -= 5

        # 轮次扣分（多轮意味着初始质量较低）
        base_score -= (rounds - 1) * 5

        return max(0.0, min(100.0, base_score))

    def get_task_statistics(self, task_id: str) -> dict[str, Any]:
        """获取任务级对抗统计"""
        records = self.quality_tracker.get_records_by_task(task_id)

        if not records:
            return {"task_id": task_id, "records": 0}

        return {
            "task_id": task_id,
            "records": len(records),
            "total_rounds": sum(r.current_round for r in records),
            "total_issues": sum(r.total_issues for r in records),
            "pass_rate": sum(1 for r in records if r.final_result == "passed") / len(records),
        }


def create_task_adversarial(
    score_manager: ScoreManager,
    quality_tracker: QualityTracker,
    max_rounds: int = 3,
    intensity: str = "normal",
) -> TaskAdversarialController:
    """创建任务级对抗控制器"""
    return TaskAdversarialController(
        score_manager,
        quality_tracker,
        max_rounds,
        intensity,
    )