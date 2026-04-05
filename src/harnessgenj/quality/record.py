"""
Adversarial Record - 对抗记录

记录每一次对抗性审查的完整过程：
- 生成器产出
- 判别器发现
- 多轮对抗
- 最终结果
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class IssueSeverity(str, Enum):
    """问题严重程度"""
    MINOR = "minor"        # 小问题：代码风格、命名
    MAJOR = "major"        # 中等问题：潜在Bug、性能问题
    CRITICAL = "critical"  # 严重问题：安全漏洞、数据丢失


class IssueStatus(str, Enum):
    """问题状态"""
    OPEN = "open"          # 待处理
    FIXED = "fixed"        # 已修复
    FALSE_POSITIVE = "false_positive"  # 误报
    WONT_FIX = "wont_fix"  # 不修复


class IssueRecord(BaseModel):
    """问题记录"""
    issue_id: str = Field(..., description="问题ID")
    description: str = Field(..., description="问题描述")
    severity: IssueSeverity = Field(default=IssueSeverity.MINOR, description="严重程度")
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="状态")

    # 位置信息
    file_path: str | None = Field(default=None, description="文件路径")
    line_number: int | None = Field(default=None, description="行号")
    code_snippet: str | None = Field(default=None, description="代码片段")

    # 审查者信息
    found_by: str = Field(..., description="发现问题者")
    found_at: float = Field(default_factory=time.time, description="发现时间")

    # 修复信息
    fixed_by: str | None = Field(default=None, description="修复者")
    fixed_at: float | None = Field(default=None, description="修复时间")
    fix_description: str | None = Field(default=None, description="修复说明")

    # 验证
    verified: bool = Field(default=False, description="是否已验证")
    verified_by: str | None = Field(default=None, description="验证者")


class AdversarialRound(BaseModel):
    """对抗轮次记录"""
    round_number: int = Field(..., description="轮次号")
    generator_output: str = Field(default="", description="生成器产出")
    discriminator_findings: list[IssueRecord] = Field(default_factory=list, description="判别器发现")
    passed: bool = Field(default=False, description="是否通过")
    started_at: float = Field(default_factory=time.time, description="开始时间")
    ended_at: float | None = Field(default=None, description="结束时间")


class AdversarialRecord(BaseModel):
    """
    对抗记录

    记录一次完整的对抗性审查过程
    """

    # 基本信息
    record_id: str = Field(..., description="记录ID")
    task_id: str | None = Field(default=None, description="关联任务ID")

    # 角色信息
    generator_id: str = Field(..., description="生成器角色ID")
    generator_type: str = Field(..., description="生成器角色类型")
    discriminator_id: str = Field(..., description="判别器角色ID")
    discriminator_type: str = Field(..., description="判别器角色类型")

    # 对抗内容
    artifact_type: str = Field(default="code", description="产出类型")
    artifact_content: str = Field(default="", description="产出内容")

    # 对抗过程
    rounds: list[AdversarialRound] = Field(default_factory=list, description="对抗轮次")
    current_round: int = Field(default=0, description="当前轮次")
    max_rounds: int = Field(default=3, description="最大轮次")

    # 结果
    final_result: str = Field(default="pending", description="最终结果")
    total_issues: int = Field(default=0, description="总问题数")
    resolved_issues: int = Field(default=0, description="已解决数")
    false_positives: int = Field(default=0, description="误报数")

    # 积分变更
    generator_score_delta: int = Field(default=0, description="生成器积分变化")
    discriminator_score_delta: int = Field(default=0, description="判别器积分变化")

    # 时间
    created_at: float = Field(default_factory=time.time, description="创建时间")
    completed_at: float | None = Field(default=None, description="完成时间")

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.final_result != "pending"

    @property
    def duration(self) -> float:
        """持续时间（秒）"""
        if self.completed_at:
            return self.completed_at - self.created_at
        return time.time() - self.created_at

    @property
    def issue_summary(self) -> dict[str, int]:
        """问题摘要"""
        summary = {"minor": 0, "major": 0, "critical": 0}
        for round_data in self.rounds:
            for issue in round_data.discriminator_findings:
                summary[issue.severity.value] += 1
        return summary

    def add_round(self, round_data: AdversarialRound) -> None:
        """添加对抗轮次"""
        self.rounds.append(round_data)
        self.current_round = len(self.rounds)

    def get_all_issues(self) -> list[IssueRecord]:
        """获取所有问题"""
        issues = []
        for round_data in self.rounds:
            issues.extend(round_data.discriminator_findings)
        return issues

    def get_open_issues(self) -> list[IssueRecord]:
        """获取未解决问题"""
        return [i for i in self.get_all_issues() if i.status == IssueStatus.OPEN]

    def complete(self, result: str) -> None:
        """完成对抗"""
        self.final_result = result
        self.completed_at = time.time()

        # 统计问题
        all_issues = self.get_all_issues()
        self.total_issues = len(all_issues)
        self.resolved_issues = len([i for i in all_issues if i.status == IssueStatus.FIXED])
        self.false_positives = len([i for i in all_issues if i.status == IssueStatus.FALSE_POSITIVE])


class AdversarialSummary(BaseModel):
    """对抗摘要（用于统计）"""

    total_sessions: int = Field(default=0, description="总会话数")
    passed_sessions: int = Field(default=0, description="通过会话数")
    failed_sessions: int = Field(default=0, description="失败会话数")

    avg_rounds: float = Field(default=0.0, description="平均轮次")
    avg_duration: float = Field(default=0.0, description="平均时长")

    total_issues: int = Field(default=0, description="总问题数")
    issues_by_severity: dict[str, int] = Field(default_factory=dict, description="按严重程度统计")

    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_sessions == 0:
            return 0.0
        return self.passed_sessions / self.total_sessions


def create_issue(
    description: str,
    severity: IssueSeverity = IssueSeverity.MINOR,
    found_by: str = "",
    file_path: str | None = None,
    line_number: int | None = None,
) -> IssueRecord:
    """创建问题记录"""
    import uuid
    return IssueRecord(
        issue_id=f"ISS-{uuid.uuid4().hex[:8]}",
        description=description,
        severity=severity,
        found_by=found_by,
        file_path=file_path,
        line_number=line_number,
    )


def create_adversarial_record(
    generator_id: str,
    generator_type: str,
    discriminator_id: str,
    discriminator_type: str,
    task_id: str | None = None,
    artifact_type: str = "code",
) -> AdversarialRecord:
    """创建对抗记录"""
    import uuid
    return AdversarialRecord(
        record_id=f"ADV-{uuid.uuid4().hex[:8]}",
        task_id=task_id,
        generator_id=generator_id,
        generator_type=generator_type,
        discriminator_id=discriminator_id,
        discriminator_type=discriminator_type,
        artifact_type=artifact_type,
    )