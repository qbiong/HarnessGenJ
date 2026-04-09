"""
违规记录模块

与积分系统联动，记录并惩罚违规行为

核心功能：
1. 记录边界违规、权限拒绝等违规行为
2. 触发积分扣减
3. 生成审计报告
"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ViolationSeverity(Enum):
    """违规严重程度"""
    LOW = "low"          # 轻微违规，扣分较少
    MEDIUM = "medium"    # 中等违规
    HIGH = "high"        # 严重违规
    CRITICAL = "critical"  # 关键违规


class ViolationType(Enum):
    """违规类型"""
    BOUNDARY_VIOLATION = "boundary_violation"      # 边界违规
    PERMISSION_DENIED = "permission_denied"        # 权限拒绝
    GATE_BYPASS_ATTEMPT = "gate_bypass_attempt"    # 尝试绕过门禁
    UNAUTHORIZED_CODE_EDIT = "unauthorized_code_edit"  # 未授权修改代码
    UNAUTHORIZED_ACTION = "unauthorized_action"    # 未授权操作


class ViolationRecord(BaseModel):
    """违规记录"""
    timestamp: str = Field(description="时间戳")
    violation_type: str = Field(description="违规类型")
    role_id: str = Field(description="违规角色ID")
    role_type: str = Field(description="角色类型")
    action: str = Field(description="违规行为")
    reason: str = Field(description="违规原因")
    severity: ViolationSeverity = Field(description="严重程度")
    blocked: bool = Field(description="是否被阻止")
    score_delta: int = Field(description="积分变化")
    suggestion: str | None = Field(default=None, description="建议处理方式")
    context: dict[str, Any] | None = Field(default=None, description="上下文")


class ViolationManager:
    """
    违规管理器

    与 ScoreManager 联动：
    - 记录违规行为
    - 触发积分扣减
    - 生成审计报告
    """

    def __init__(self, score_manager, audit_dir: str = ".harnessgenj"):
        """
        初始化违规管理器

        Args:
            score_manager: 积分管理器实例
            audit_dir: 审计日志目录
        """
        self.score_manager = score_manager
        self.audit_dir = audit_dir
        self._violations: list[ViolationRecord] = []

    def record(
        self,
        role_id: str,
        violation_type: str,
        action: str,
        reason: str,
        severity: ViolationSeverity = ViolationSeverity.MEDIUM,
        blocked: bool = True,
        suggestion: str | None = None,
        context: dict | None = None,
    ) -> ViolationRecord:
        """
        记录违规并扣分

        Args:
            role_id: 违规角色ID
            violation_type: 违规类型
            action: 违规行为
            reason: 原因
            severity: 严重程度
            blocked: 是否被阻止
            suggestion: 建议处理方式
            context: 上下文

        Returns:
            违规记录
        """
        # 获取角色信息
        role_score = self.score_manager.get_score(role_id)
        role_type = role_score.role_type if role_score else "unknown"

        # 计算扣分
        delta = self._calculate_penalty(violation_type, severity, blocked)

        # 创建记录
        record = ViolationRecord(
            timestamp=datetime.now().isoformat(),
            violation_type=violation_type,
            role_id=role_id,
            role_type=role_type,
            action=action,
            reason=reason,
            severity=severity,
            blocked=blocked,
            score_delta=delta,
            suggestion=suggestion,
            context=context,
        )
        self._violations.append(record)

        # 触发积分扣减
        self.score_manager._apply_delta(
            role_id=role_id,
            delta=delta,
            event_type=f"violation:{violation_type}",
            reason=f"[{severity.value}] {action}: {reason}",
        )

        # 通知
        self._notify_violation(record)

        # 持久化
        self._save()

        return record

    def _calculate_penalty(
        self,
        violation_type: str,
        severity: ViolationSeverity,
        blocked: bool,
    ) -> int:
        """计算违规扣分"""
        base_penalty = {
            "boundary_violation": 5,
            "permission_denied": 3,
            "gate_bypass_attempt": 10,
            "unauthorized_code_edit": 15,
            "unauthorized_action": 5,
        }.get(violation_type, 5)

        severity_multiplier = {
            ViolationSeverity.LOW: 0.5,
            ViolationSeverity.MEDIUM: 1.0,
            ViolationSeverity.HIGH: 1.5,
            ViolationSeverity.CRITICAL: 2.0,
        }.get(severity, 1.0)

        penalty = int(base_penalty * severity_multiplier)

        # 被阻止则扣分减半（尝试未成功）
        if blocked:
            penalty = penalty // 2

        return -penalty

    def _notify_violation(self, record: ViolationRecord) -> None:
        """通知违规"""
        try:
            from harnessgenj.notify import get_notifier
            notifier = get_notifier()

            notifier.notify_boundary_violation(
                role_type=record.role_type,
                role_id=record.role_id,
                action=record.action,
                reason=f"{record.reason} (积分: {record.score_delta})",
                suggestion=record.suggestion or "",
            )
        except Exception:
            pass

    def _save(self) -> None:
        """持久化违规记录"""
        try:
            import json
            from pathlib import Path

            audit_path = Path(self.audit_dir) / "violations.json"
            audit_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "violations": [v.model_dump() for v in self._violations],
                "stats": self.get_violation_stats(),
            }

            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_violations_by_role(self, role_id: str) -> list[ViolationRecord]:
        """获取角色的违规记录"""
        return [v for v in self._violations if v.role_id == role_id]

    def get_violation_stats(self) -> dict:
        """获取违规统计"""
        return {
            "total": len(self._violations),
            "blocked": sum(1 for v in self._violations if v.blocked),
            "by_severity": {
                s.value: sum(1 for v in self._violations if v.severity == s)
                for s in ViolationSeverity
            },
            "by_type": self._group_by_type(),
            "total_score_impact": sum(v.score_delta for v in self._violations),
        }

    def _group_by_type(self) -> dict[str, int]:
        """按类型分组"""
        result: dict[str, int] = {}
        for v in self._violations:
            result[v.violation_type] = result.get(v.violation_type, 0) + 1
        return result

    def get_recent_violations(self, limit: int = 50) -> list[ViolationRecord]:
        """获取最近的违规记录"""
        return self._violations[-limit:]


def create_violation_manager(
    score_manager,
    audit_dir: str = ".harnessgenj",
) -> ViolationManager:
    """
    创建违规管理器实例

    Args:
        score_manager: 积分管理器实例
        audit_dir: 审计日志目录

    Returns:
        违规管理器实例
    """
    return ViolationManager(score_manager, audit_dir)


__all__ = [
    "ViolationSeverity",
    "ViolationType",
    "ViolationRecord",
    "ViolationManager",
    "create_violation_manager",
]