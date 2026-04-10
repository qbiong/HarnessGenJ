"""
Score Manager - 积分管理器

对抗性质量保证系统的核心：
- 角色积分追踪
- 积分变更事件
- 积分持久化
- 等级计算

设计原则：
1. 轻量化：仅在积分变更时更新，不频繁计算
2. 可追溯：记录所有积分变更原因
3. 公平性：生成器和判别器双向激励
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import json
import os
import time
import logging
import threading

from harnessgenj.utils.exception_handler import log_exception

logger = logging.getLogger(__name__)


class ScoreEvent(BaseModel):
    """积分事件记录"""
    timestamp: float = Field(default_factory=time.time)
    role_type: str = Field(..., description="角色类型")
    role_id: str = Field(..., description="角色ID")
    event_type: str = Field(..., description="事件类型")
    delta: int = Field(..., description="积分变化")
    reason: str = Field(default="", description="变更原因")
    task_id: str | None = Field(default=None, description="关联任务ID")
    severity: str | None = Field(default=None, description="问题严重程度")


class RoleScore(BaseModel):
    """角色积分状态"""
    role_type: str = Field(..., description="角色类型")
    role_id: str = Field(..., description="角色ID")
    role_name: str = Field(default="", description="角色名称")

    # 积分
    score: int = Field(default=100, description="当前积分")

    # 统计
    total_tasks: int = Field(default=0, description="总任务数")
    success_tasks: int = Field(default=0, description="成功任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")

    # 对抗统计（用于判别器角色）
    issues_found: int = Field(default=0, description="发现问题数")
    issues_valid: int = Field(default=0, description="有效问题数")
    issues_false_positive: int = Field(default=0, description="误报数")
    issues_missed: int = Field(default=0, description="漏报数")

    # 时间戳
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 1.0
        return self.success_tasks / self.total_tasks

    @property
    def grade(self) -> str:
        """等级评定"""
        if self.score >= 90:
            return "A"
        elif self.score >= 70:
            return "B"
        elif self.score >= 50:
            return "C"
        else:
            return "D"

    @property
    def is_generator(self) -> bool:
        """是否为生成器角色"""
        return self.role_type in ["developer", "architect", "tester", "doc_writer", "product_manager"]

    @property
    def is_discriminator(self) -> bool:
        """是否为判别器角色"""
        return self.role_type in ["code_reviewer", "bug_hunter", "qa_lead", "tech_validator"]


class ScoreRules:
    """积分规则常量"""

    # ========== 生成器角色积分规则 ==========

    # 成功奖励
    ONE_ROUND_PASS = 10       # 一轮通过审查
    TWO_ROUND_PASS = 5        # 二轮通过
    THREE_ROUND_PASS = 2      # 三轮及以上通过

    # 失败惩罚
    BUG_FOUND_MINOR = -3      # 发现小问题
    BUG_FOUND_MAJOR = -5      # 发现中等问题
    BUG_FOUND_CRITICAL = -10  # 发现严重问题
    PRODUCTION_BUG = -20      # 生产环境Bug

    # 误报补偿
    FALSE_POSITIVE_BONUS = 3  # 被误报补偿

    # ========== 判别器角色积分规则 ==========

    # 发现奖励
    FIND_MINOR = 2            # 发现小问题
    FIND_MAJOR = 4            # 发现中等问题
    FIND_CRITICAL = 6         # 发现严重问题
    PREVENT_PRODUCTION = 10   # 阻止生产Bug

    # 失误惩罚
    FALSE_POSITIVE = -2       # 误报
    MISSED_BUG = -8           # 漏报真实Bug
    MISSED_CRITICAL = -15     # 漏报严重Bug

    # ========== 违规惩罚规则（新增） ==========

    BOUNDARY_VIOLATION = -5      # 边界违规
    PERMISSION_DENIED = -3       # 权限拒绝
    GATE_BYPASS_ATTEMPT = -10    # 尝试绕过门禁
    UNAUTHORIZED_CODE_EDIT = -15 # 未授权修改代码

    # ========== 合规奖励规则（新增） ==========

    PROCESS_COMPLIANCE = +2      # 流程合规奖励
    QUALITY_GATE_PASS = +3       # 质量门禁通过

    # ========== 严重程度映射 ==========

    SEVERITY_MULTIPLIER = {
        "minor": 1,
        "major": 2,
        "critical": 3,
    }


class ScoreManager:
    """
    积分管理器

    核心功能：
    1. 管理角色积分
    2. 处理积分事件
    3. 持久化积分数据
    4. 提供积分查询

    使用示例：
        manager = ScoreManager(".harnessgenj")

        # 注册角色
        manager.register_role("developer", "dev_1", "开发者")
        manager.register_role("code_reviewer", "reviewer_1", "审查者")

        # 记录事件
        manager.on_issue_found("dev_1", "reviewer_1", "major", "TASK-001")

        # 查询积分
        score = manager.get_score("dev_1")
    """

    def __init__(self, workspace: str = ".harnessgenj") -> None:
        self.workspace = workspace
        self._scores: dict[str, RoleScore] = {}
        self._events: list[ScoreEvent] = []
        self._max_events = 1000  # 最多保留1000条事件

        # 线程锁保护关键数据结构
        self._lock = threading.RLock()

        # 加载持久化数据
        self._load()

    # ==================== 角色管理 ====================

    def register_role(
        self,
        role_type: str,
        role_id: str,
        role_name: str = "",
        initial_score: int = 100,
    ) -> RoleScore:
        """
        注册角色

        Args:
            role_type: 角色类型
            role_id: 角色ID
            role_name: 角色名称
            initial_score: 初始积分

        Returns:
            角色积分对象
        """
        with self._lock:
            if role_id in self._scores:
                return self._scores[role_id]

            score = RoleScore(
                role_type=role_type,
                role_id=role_id,
                role_name=role_name or role_type,
                score=initial_score,
            )
            self._scores[role_id] = score
            self._save()
            return score

    def get_score(self, role_id: str) -> RoleScore | None:
        """获取角色积分"""
        with self._lock:
            return self._scores.get(role_id)

    def get_all_scores(self) -> list[RoleScore]:
        """获取所有角色积分"""
        with self._lock:
            return list(self._scores.values())

    def get_scores_by_type(self, role_type: str) -> list[RoleScore]:
        """按类型获取积分"""
        with self._lock:
            return [s for s in self._scores.values() if s.role_type == role_type]

    def get_score_by_role_type(self, role_type: str) -> RoleScore | None:
        """按类型获取单个积分（取最高分）"""
        with self._lock:
            scores = [s for s in self._scores.values() if s.role_type == role_type]
            if not scores:
                return None
            return max(scores, key=lambda s: s.score)

    # ==================== 积分变更事件 ====================

    def on_task_success(
        self,
        generator_id: str,
        rounds: int,
        task_id: str | None = None,
    ) -> int:
        """
        任务成功事件

        Args:
            generator_id: 生成器角色ID
            rounds: 对抗轮次
            task_id: 任务ID

        Returns:
            积分变化
        """
        if rounds == 1:
            delta = ScoreRules.ONE_ROUND_PASS
        elif rounds == 2:
            delta = ScoreRules.TWO_ROUND_PASS
        else:
            delta = ScoreRules.THREE_ROUND_PASS

        self._apply_delta(generator_id, delta, "task_success", f"任务通过（{rounds}轮）", task_id)

        # 更新统计
        if generator_id in self._scores:
            self._scores[generator_id].total_tasks += 1
            self._scores[generator_id].success_tasks += 1

        return delta

    def on_task_failed(
        self,
        generator_id: str,
        task_id: str | None = None,
    ) -> int:
        """
        任务失败事件

        Args:
            generator_id: 生成器角色ID
            task_id: 任务ID

        Returns:
            积分变化
        """
        delta = -5  # 任务失败扣5分
        self._apply_delta(generator_id, delta, "task_failed", "任务失败", task_id)

        # 更新统计
        if generator_id in self._scores:
            self._scores[generator_id].total_tasks += 1
            self._scores[generator_id].failed_tasks += 1

        return delta

    def on_issue_found(
        self,
        generator_id: str,
        discriminator_id: str,
        severity: str,
        task_id: str | None = None,
        description: str = "",
    ) -> tuple[int, int]:
        """
        发现问题事件（对抗核心）

        生成器扣分，判别器加分

        Args:
            generator_id: 生成器角色ID
            discriminator_id: 判别器角色ID
            severity: 严重程度 (minor/major/critical)
            task_id: 任务ID
            description: 问题描述

        Returns:
            (生成器积分变化, 判别器积分变化)
        """
        severity = severity.lower()
        multiplier = ScoreRules.SEVERITY_MULTIPLIER.get(severity, 1)

        # 生成器扣分
        if severity == "critical":
            gen_delta = ScoreRules.BUG_FOUND_CRITICAL
        elif severity == "major":
            gen_delta = ScoreRules.BUG_FOUND_MAJOR
        else:
            gen_delta = ScoreRules.BUG_FOUND_MINOR

        gen_delta *= multiplier

        # 判别器加分
        if severity == "critical":
            disc_delta = ScoreRules.FIND_CRITICAL
        elif severity == "major":
            disc_delta = ScoreRules.FIND_MAJOR
        else:
            disc_delta = ScoreRules.FIND_MINOR

        disc_delta *= multiplier

        # 应用变更
        self._apply_delta(
            generator_id, gen_delta, "issue_found",
            f"发现问题: {description}", task_id, severity
        )
        self._apply_delta(
            discriminator_id, disc_delta, "issue_found",
            f"发现问题: {description}", task_id, severity
        )

        # 更新统计
        if generator_id in self._scores:
            self._scores[generator_id].issues_found += 1
        if discriminator_id in self._scores:
            self._scores[discriminator_id].issues_found += 1
            self._scores[discriminator_id].issues_valid += 1

        return gen_delta, disc_delta

    def on_false_positive(
        self,
        discriminator_id: str,
        generator_id: str,
        task_id: str | None = None,
    ) -> tuple[int, int]:
        """
        误报事件

        判别器扣分，生成器补偿

        Args:
            discriminator_id: 判别器角色ID
            generator_id: 生成器角色ID
            task_id: 任务ID

        Returns:
            (判别器积分变化, 生成器积分变化)
        """
        disc_delta = ScoreRules.FALSE_POSITIVE
        gen_delta = ScoreRules.FALSE_POSITIVE_BONUS

        self._apply_delta(
            discriminator_id, disc_delta, "false_positive",
            "误报问题", task_id
        )
        self._apply_delta(
            generator_id, gen_delta, "false_positive_compensation",
            "误报补偿", task_id
        )

        # 更新统计
        if discriminator_id in self._scores:
            self._scores[discriminator_id].issues_false_positive += 1

        return disc_delta, gen_delta

    def on_bug_missed(
        self,
        discriminator_id: str,
        severity: str = "major",
        task_id: str | None = None,
    ) -> int:
        """
        漏报事件

        判别器扣分

        Args:
            discriminator_id: 判别器角色ID
            severity: 严重程度
            task_id: 任务ID

        Returns:
            积分变化
        """
        severity = severity.lower()

        if severity == "critical":
            delta = ScoreRules.MISSED_CRITICAL
        else:
            delta = ScoreRules.MISSED_BUG

        self._apply_delta(
            discriminator_id, delta, "bug_missed",
            f"漏报问题 ({severity})", task_id, severity
        )

        # 更新统计
        if discriminator_id in self._scores:
            self._scores[discriminator_id].issues_missed += 1

        return delta

    def on_production_bug(
        self,
        generator_id: str,
        discriminator_id: str | None = None,
        task_id: str | None = None,
    ) -> int:
        """
        生产环境Bug事件（严重）

        Args:
            generator_id: 生成器角色ID
            discriminator_id: 判别器角色ID（如果有）
            task_id: 任务ID

        Returns:
            积分变化
        """
        gen_delta = ScoreRules.PRODUCTION_BUG
        self._apply_delta(
            generator_id, gen_delta, "production_bug",
            "生产环境Bug", task_id, "critical"
        )

        # 如果有判别器，也算漏报
        if discriminator_id:
            self.on_bug_missed(discriminator_id, "critical", task_id)

        return gen_delta

    # ==================== 违规与合规方法（新增） ====================

    def record_violation(
        self,
        role_id: str,
        violation_type: str,
        action: str,
        blocked: bool = True,
        context: dict | None = None,
    ) -> "ScoreEvent":
        """
        记录违规行为并扣分

        Args:
            role_id: 违规角色ID
            violation_type: 违规类型 (boundary_violation/permission_denied/gate_bypass_attempt/unauthorized_code_edit)
            action: 违规行为描述
            blocked: 是否被阻止
            context: 上下文信息

        Returns:
            积分事件记录
        """
        # 确定扣分
        delta_map = {
            "boundary_violation": ScoreRules.BOUNDARY_VIOLATION,
            "permission_denied": ScoreRules.PERMISSION_DENIED,
            "gate_bypass_attempt": ScoreRules.GATE_BYPASS_ATTEMPT,
            "unauthorized_code_edit": ScoreRules.UNAUTHORIZED_CODE_EDIT,
        }
        delta = delta_map.get(violation_type, -5)

        # 如果被阻止，扣分减半（尝试未成功）
        if blocked:
            delta = delta // 2

        reason = f"违规行为: {action}" + (" (已阻止)" if blocked else " (未阻止)")

        # 记录事件并更新积分
        self._apply_delta(
            role_id=role_id,
            delta=delta,
            event_type=f"violation:{violation_type}",
            reason=reason,
        )

        # 返回最后一个事件
        return self._events[-1] if self._events else None

    def reward_compliance(
        self,
        role_id: str,
        compliance_type: str,
        task_id: str | None = None,
    ) -> "ScoreEvent":
        """
        奖励合规行为

        Args:
            role_id: 角色ID
            compliance_type: 合规类型 (process_compliance/quality_gate_pass)
            task_id: 关联任务ID

        Returns:
            积分事件记录
        """
        delta_map = {
            "process_compliance": ScoreRules.PROCESS_COMPLIANCE,
            "quality_gate_pass": ScoreRules.QUALITY_GATE_PASS,
        }
        delta = delta_map.get(compliance_type, +1)

        self._apply_delta(
            role_id=role_id,
            delta=delta,
            event_type=f"compliance:{compliance_type}",
            reason=f"合规行为: {compliance_type}",
            task_id=task_id,
        )

        # 返回最后一个事件
        return self._events[-1] if self._events else None

    # ==================== 内部方法 ====================

    def _apply_delta(
        self,
        role_id: str,
        delta: int,
        event_type: str,
        reason: str = "",
        task_id: str | None = None,
        severity: str | None = None,
    ) -> None:
        """应用积分变化"""
        with self._lock:
            if role_id not in self._scores:
                return

            # 更新积分
            self._scores[role_id].score += delta
            self._scores[role_id].score = max(0, min(100, self._scores[role_id].score))  # 限制在0-100
            self._scores[role_id].updated_at = time.time()

            # 记录事件
            event = ScoreEvent(
                role_type=self._scores[role_id].role_type,
                role_id=role_id,
                event_type=event_type,
                delta=delta,
                reason=reason,
                task_id=task_id,
                severity=severity,
            )
            self._events.append(event)

            # 限制事件数量
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

            self._save()

        # 【新增】通知积分变化（在锁外执行避免死锁）
        try:
            from harnessgenj.notify import get_notifier
            notifier = get_notifier()
            with self._lock:
                role_type = self._scores[role_id].role_type if role_id in self._scores else ""
                new_score = self._scores[role_id].score if role_id in self._scores else 0
            notifier.notify_score_change(
                role_id=role_id,
                role_type=role_type,
                delta=delta,
                reason=reason or event_type,
                new_score=new_score,
            )
        except Exception as e:
            # 通知失败不影响主流程，记录日志
            log_exception(e, context="_record_event 通知", level=30)

    # ==================== 查询方法 ====================

    def get_recent_events(self, limit: int = 50) -> list[ScoreEvent]:
        """获取最近事件"""
        with self._lock:
            return list(self._events[-limit:])

    def get_events_by_role(self, role_id: str, limit: int = 50) -> list[ScoreEvent]:
        """获取角色相关事件"""
        with self._lock:
            events = [e for e in self._events if e.role_id == role_id]
        return events[-limit:]

    def get_events_by_task(self, task_id: str) -> list[ScoreEvent]:
        """获取任务相关事件"""
        return [e for e in self._events if e.task_id == task_id]

    def get_leaderboard(self, role_type: str | None = None) -> list[dict[str, Any]]:
        """
        获取积分排行榜

        Args:
            role_type: 筛选角色类型（可选）

        Returns:
            排行榜列表
        """
        scores = list(self._scores.values())

        if role_type:
            scores = [s for s in scores if s.role_type == role_type]

        # 按积分排序
        scores.sort(key=lambda s: s.score, reverse=True)

        return [
            {
                "rank": i + 1,
                "role_id": s.role_id,
                "role_name": s.role_name,
                "role_type": s.role_type,
                "score": s.score,
                "grade": s.grade,
                "success_rate": f"{s.success_rate:.1%}",
            }
            for i, s in enumerate(scores)
        ]

    def get_quality_report(self) -> dict[str, Any]:
        """获取质量报告"""
        generators = [s for s in self._scores.values() if s.is_generator]
        discriminators = [s for s in self._scores.values() if s.is_discriminator]

        # 计算平均成功率
        avg_success_rate = 0
        if generators:
            avg_success_rate = sum(s.success_rate for s in generators) / len(generators)

        # 计算判别器有效性
        avg_detection_rate = 0
        if discriminators:
            total_found = sum(s.issues_found for s in discriminators)
            total_valid = sum(s.issues_valid for s in discriminators)
            if total_found > 0:
                avg_detection_rate = total_valid / total_found

        # 等级分布
        grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
        for s in self._scores.values():
            grade_dist[s.grade] += 1

        return {
            "total_roles": len(self._scores),
            "generators": len(generators),
            "discriminators": len(discriminators),
            "avg_success_rate": round(avg_success_rate, 2),
            "avg_detection_rate": round(avg_detection_rate, 2),
            "grade_distribution": grade_dist,
            "total_events": len(self._events),
        }

    # ==================== 持久化 ====================

    def _save(self) -> None:
        """保存到文件"""
        try:
            data_path = os.path.join(self.workspace, "scores.json")

            data = {
                "scores": {rid: s.model_dump() for rid, s in self._scores.items()},
                "events": [e.model_dump() for e in self._events[-100:]],  # 只保存最近100条
            }

            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save score data: {e}")

    def _load(self) -> None:
        """从文件加载"""
        data_path = os.path.join(self.workspace, "scores.json")
        if not os.path.exists(data_path):
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 加载积分
            for rid, sdata in data.get("scores", {}).items():
                self._scores[rid] = RoleScore(**sdata)

            # 加载事件
            for edata in data.get("events", []):
                self._events.append(ScoreEvent(**edata))
        except Exception as e:
            logger.warning(f"Failed to load score data: {e}")

    def reset(self, role_id: str | None = None) -> None:
        """
        重置积分

        Args:
            role_id: 指定角色ID，None则重置全部
        """
        if role_id:
            if role_id in self._scores:
                self._scores[role_id].score = 100
                self._scores[role_id].total_tasks = 0
                self._scores[role_id].success_tasks = 0
                self._scores[role_id].failed_tasks = 0
                self._scores[role_id].issues_found = 0
                self._scores[role_id].issues_valid = 0
                self._scores[role_id].issues_false_positive = 0
                self._scores[role_id].issues_missed = 0
        else:
            self._scores.clear()
            self._events.clear()

        self._save()