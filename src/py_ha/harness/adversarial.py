"""
Adversarial Workflow - 对抗性工作流

实现 GAN 式的开发-审查对抗机制：
1. 开发者产出代码
2. 审查者发现问题
3. 开发者修复
4. 循环直到通过或达到最大轮次
5. 计算积分变更
6. 更新记忆条目质量信息（重要：建立质量数据流）

使用示例：
    workflow = AdversarialWorkflow(harness)

    result = workflow.execute_adversarial_develop(
        task={"description": "实现登录功能"},
        max_rounds=3,
    )
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
import time

from py_ha.quality.score import ScoreManager
from py_ha.quality.record import (
    AdversarialRecord,
    AdversarialRound,
    IssueRecord,
    IssueStatus,
    create_issue,
    create_adversarial_record,
)
from py_ha.quality.tracker import QualityTracker
from py_ha.roles.code_reviewer import CodeReviewer, ReviewResult
from py_ha.roles.bug_hunter import BugHunter, HuntResult


class AdversarialResult(BaseModel):
    """对抗性开发结果"""
    success: bool = Field(..., description="是否成功")
    rounds: int = Field(default=0, description="对抗轮次")
    final_code: str = Field(default="", description="最终代码")
    total_issues: int = Field(default=0, description="总问题数")
    resolved_issues: int = Field(default=0, description="已解决问题")
    generator_score_delta: int = Field(default=0, description="生成器积分变化")
    discriminator_score_delta: int = Field(default=0, description="判别器积分变化")
    record_id: str = Field(default="", description="对抗记录ID")
    duration: float = Field(default=0.0, description="耗时（秒）")
    quality_score: float = Field(default=50.0, description="最终质量分数")
    artifact_id: str | None = Field(default=None, description="关联的记忆条目ID")


class AdversarialWorkflow:
    """
    对抗性工作流管理器

    核心流程：
    1. 生成器（开发者）产出代码
    2. 判别器（审查者）审查
    3. 根据审查结果修复
    4. 循环直到通过或达到最大轮次
    5. 计算双方积分
    6. 更新记忆条目质量信息

    设计原则：
    - 严格的对抗机制
    - 公平的积分系统
    - 完整的记录追踪
    - 质量数据与记忆关联
    """

    def __init__(
        self,
        score_manager: ScoreManager,
        quality_tracker: QualityTracker,
        memory_manager: Any | None = None,
    ) -> None:
        """
        初始化对抗工作流

        Args:
            score_manager: 积分管理器
            quality_tracker: 质量追踪器
            memory_manager: 记忆管理器（可选，用于更新质量信息）
        """
        self.score_manager = score_manager
        self.quality_tracker = quality_tracker
        self.memory_manager = memory_manager

        # 审查者实例（延迟创建）
        self._reviewer: CodeReviewer | None = None
        self._hunter: BugHunter | None = None

    def set_memory_manager(self, memory_manager: Any) -> None:
        """设置记忆管理器"""
        self.memory_manager = memory_manager

    # ==================== 核心对抗方法 ====================

    def execute_adversarial_review(
        self,
        code: str,
        generator_id: str,
        generator_type: str,
        task_id: str | None = None,
        max_rounds: int = 3,
        fix_callback: Callable[[list[IssueRecord]], str] | None = None,
        use_hunter: bool = False,
        artifact_id: str | None = None,
    ) -> AdversarialResult:
        """
        执行对抗性审查

        Args:
            code: 待审查代码
            generator_id: 生成者角色ID
            generator_type: 生成者角色类型
            task_id: 任务ID
            max_rounds: 最大对抗轮次
            fix_callback: 修复回调函数（接收问题列表，返回修复后代码）
            use_hunter: 是否使用BugHunter（更激进的审查）
            artifact_id: 关联的记忆条目ID（可选）

        Returns:
            对抗结果
        """
        import uuid
        start_time = time.time()

        # 创建审查者
        discriminator_id = "reviewer_adv"
        discriminator_type = "code_reviewer"

        if use_hunter:
            from py_ha.roles.bug_hunter import create_bug_hunter
            self._hunter = create_bug_hunter("hunter_adv")
            discriminator_id = "hunter_adv"
            discriminator_type = "bug_hunter"
        else:
            from py_ha.roles.code_reviewer import create_code_reviewer
            self._reviewer = create_code_reviewer("reviewer_adv")

        # 注册角色到积分系统
        self.score_manager.register_role(generator_type, generator_id, generator_type)
        self.score_manager.register_role(discriminator_type, discriminator_id, discriminator_type)

        # 创建对抗记录
        record = create_adversarial_record(
            generator_id=generator_id,
            generator_type=generator_type,
            discriminator_id=discriminator_id,
            discriminator_type=discriminator_type,
            task_id=task_id,
            artifact_type="code",
        )
        record.artifact_content = code
        record.max_rounds = max_rounds

        current_code = code
        round_num = 0

        while round_num < max_rounds:
            round_num += 1
            round_start = time.time()

            # 执行审查
            if use_hunter and self._hunter:
                review_result = self._hunter.hunt(current_code)
                issues = review_result.vulnerabilities
                passed = len([i for i in issues if i.severity.value == "critical"]) == 0
            elif self._reviewer:
                review_result = self._reviewer.review(current_code)
                issues = review_result.issues
                passed = review_result.passed
            else:
                break

            # 记录轮次
            adv_round = AdversarialRound(
                round_number=round_num,
                generator_output=current_code,
                discriminator_findings=issues,
                passed=passed,
                started_at=round_start,
                ended_at=time.time(),
            )
            record.add_round(adv_round)

            # 如果通过，结束对抗
            if passed:
                record.complete("passed")
                break

            # 如果有修复回调，尝试修复
            if fix_callback and round_num < max_rounds:
                current_code = fix_callback(issues)
                record.artifact_content = current_code

        # 如果达到最大轮次仍未通过
        if not record.is_completed:
            record.complete("max_rounds_reached")

        # 计算积分变更
        gen_delta, disc_delta = self._calculate_scores(record, generator_id, discriminator_id)

        record.generator_score_delta = gen_delta
        record.discriminator_score_delta = disc_delta

        # 记录到质量追踪器
        self.quality_tracker.record_adversarial(record)

        # 计算质量分数
        quality_score = self._calculate_quality_score(record, round_num)

        # 更新记忆系统中的质量信息（核心：建立数据流）
        final_artifact_id = artifact_id
        if self.memory_manager:
            if not final_artifact_id:
                # 如果没有提供 artifact_id，创建新的记忆条目
                final_artifact_id = f"artifact_{task_id or uuid.uuid4().hex[:8]}"
                self.memory_manager.store_artifact(
                    artifact_id=final_artifact_id,
                    content=current_code,
                    artifact_type="code",
                    generator_id=generator_id,
                )

            # 更新质量信息
            self.memory_manager.link_adversarial_result(
                entry_id=final_artifact_id,
                quality_score=quality_score,
                passed=record.final_result == "passed",
                generator_id=generator_id,
                discriminator_id=discriminator_id,
            )

        return AdversarialResult(
            success=record.final_result == "passed",
            rounds=round_num,
            final_code=current_code,
            total_issues=record.total_issues,
            resolved_issues=record.resolved_issues,
            generator_score_delta=gen_delta,
            discriminator_score_delta=disc_delta,
            record_id=record.record_id,
            duration=time.time() - start_time,
            quality_score=quality_score,
            artifact_id=final_artifact_id,
        )

    def _calculate_quality_score(
        self,
        record: AdversarialRecord,
        rounds: int,
    ) -> float:
        """
        计算质量分数

        基于：
        1. 审查结果（通过/失败）
        2. 对抗轮次（越少越好）
        3. 发现问题的严重程度

        Args:
            record: 对抗记录
            rounds: 对抗轮次

        Returns:
            质量分数 (0-100)
        """
        base_score = 100.0

        # 未通过审查，基础分降低
        if record.final_result != "passed":
            base_score -= 30

        # 每轮扣分（多轮意味着初始质量较低）
        base_score -= (rounds - 1) * 10

        # 根据问题严重程度扣分
        for issue in record.get_all_issues():
            severity = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
            if severity == "critical":
                base_score -= 15
            elif severity == "major":
                base_score -= 8
            else:
                base_score -= 3

        return max(0.0, min(100.0, base_score))

    def quick_review(
        self,
        code: str,
        use_hunter: bool = False,
    ) -> tuple[bool, list[IssueRecord]]:
        """
        快速审查（单轮，不计分）

        Args:
            code: 待审查代码
            use_hunter: 是否使用BugHunter

        Returns:
            (是否通过, 问题列表)
        """
        if use_hunter:
            from py_ha.roles.bug_hunter import create_bug_hunter
            hunter = create_bug_hunter("hunter_quick")
            result = hunter.hunt(code)
            issues = result.vulnerabilities
            passed = result.risk_score < 30
        else:
            from py_ha.roles.code_reviewer import create_code_reviewer
            reviewer = create_code_reviewer("reviewer_quick")
            result = reviewer.review(code)
            issues = result.issues
            passed = result.passed

        return passed, issues

    # ==================== 积分计算 ====================

    def _calculate_scores(
        self,
        record: AdversarialRecord,
        generator_id: str,
        discriminator_id: str,
    ) -> tuple[int, int]:
        """
        计算双方积分变更

        Returns:
            (生成者积分变化, 审查者积分变化)
        """
        gen_delta = 0
        disc_delta = 0

        # 根据结果计算
        if record.final_result == "passed":
            # 通过：生成者得分
            rounds = record.current_round
            gen_delta = self.score_manager.on_task_success(generator_id, rounds, record.task_id)

            # 审查者：根据发现的问题得分
            for issue in record.get_all_issues():
                if issue.status == IssueStatus.FIXED:
                    # 有效问题
                    _, disc_add = self.score_manager.on_issue_found(
                        generator_id, discriminator_id,
                        issue.severity.value, record.task_id,
                        issue.description,
                    )
                    disc_delta += disc_add
                elif issue.status == IssueStatus.FALSE_POSITIVE:
                    # 误报
                    disc_sub, gen_add = self.score_manager.on_false_positive(
                        discriminator_id, generator_id, record.task_id
                    )
                    disc_delta += disc_sub
                    gen_delta += gen_add

        else:
            # 未通过：生成者扣分
            gen_delta = self.score_manager.on_task_failed(generator_id, record.task_id)

        return gen_delta, disc_delta

    # ==================== 辅助方法 ====================

    def get_reviewer(self) -> CodeReviewer | None:
        """获取当前审查者"""
        return self._reviewer

    def get_hunter(self) -> BugHunter | None:
        """获取当前猎手"""
        return self._hunter


def create_adversarial_workflow(
    workspace: str = ".py_ha",
    memory_manager: Any | None = None,
) -> AdversarialWorkflow:
    """
    创建对抗工作流实例

    Args:
        workspace: 工作空间路径
        memory_manager: 记忆管理器（可选）

    Returns:
        对抗工作流实例
    """
    score_manager = ScoreManager(workspace)
    quality_tracker = QualityTracker(workspace)
    return AdversarialWorkflow(score_manager, quality_tracker, memory_manager)