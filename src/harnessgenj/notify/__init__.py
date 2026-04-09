"""
用户感知通知模块

提供实时状态输出，让用户了解框架运行状态：
- 工作流开始/结束通知
- 阶段执行状态
- 角色任务处理
- GAN 积分变化实时通知
"""

import sys
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class NotifierLevel(Enum):
    """通知级别"""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SCORE = "SCORE"
    DEBUG = "DEBUG"


class VerbosityMode(Enum):
    """详细程度模式"""
    SIMPLE = "simple"      # 只输出关键节点
    DETAILED = "detailed"  # 输出所有信息（默认）
    DEBUG = "debug"        # 包含调试信息


class UserNotifier:
    """
    用户感知通知器

    输出格式示例:
    [HGJ] ═══════════════════════════════════════════════════════
    [HGJ] [12:34:56] 🚀 工作流开始: feature
    [HGJ]    阶段: requirement → design → development → testing
    [HGJ]   ▶ 阶段 'design' 开始
    [HGJ]     角色: architect_1
    [HGJ]    [Architect] architect_1 正在处理: Stage: design
    [HGJ]      📊 [Score] Developer +10 (一轮通过) → 85
    [HGJ]  ✅ 工作流完成: feature (耗时 1.2s)
    [HGJ] ═══════════════════════════════════════════════════════
    """

    PREFIX = "[HGJ]"
    WIDTH = 60
    ICONS = {
        NotifierLevel.INFO: "ℹ️",
        NotifierLevel.SUCCESS: "✅",
        NotifierLevel.WARNING: "⚠️",
        NotifierLevel.ERROR: "❌",
        NotifierLevel.SCORE: "📊",
        NotifierLevel.DEBUG: "🔍",
    }

    def __init__(
        self,
        enabled: bool = True,
        output: Any = None,
        verbosity: VerbosityMode = VerbosityMode.DETAILED,
        on_score_change: Callable | None = None,
    ):
        """
        初始化通知器

        Args:
            enabled: 是否启用通知
            output: 输出目标（默认 stderr）
            verbosity: 详细程度模式
            on_score_change: 积分变化回调（可选）
        """
        self.enabled = enabled
        self._output = output or sys.stderr
        self._verbosity = verbosity
        self._on_score_change = on_score_change
        self._indent = 0
        self._workflow_start_time: datetime | None = None
        self._current_workflow: str = ""
        self._score_changes: list[dict] = []

    def _emit(self, message: str, level: NotifierLevel = NotifierLevel.INFO):
        """输出消息到 stderr"""
        if not self.enabled:
            return

        # 简洁模式下跳过非关键信息
        if self._verbosity == VerbosityMode.SIMPLE:
            if level in (NotifierLevel.INFO, NotifierLevel.DEBUG):
                return

        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = self.ICONS.get(level, "")
        indent = "  " * self._indent

        # 构建消息
        parts = [self.PREFIX, f"[{timestamp}]"]
        if indent:
            parts.append(indent)
        if icon:
            parts.append(icon)
        parts.append(message)

        line = " ".join(parts)
        print(line, file=self._output)

    def notify_workflow_start(self, workflow: str, stages: list[str]):
        """
        通知工作流开始

        Args:
            workflow: 工作流名称
            stages: 阶段列表
        """
        self._current_workflow = workflow
        self._workflow_start_time = datetime.now()
        self._score_changes = []

        self._emit("═" * self.WIDTH)
        self._emit(f"🚀 工作流开始: {workflow}")
        if stages:
            self._emit(f"   阶段: {' → '.join(stages)}")

    def notify_stage_start(self, stage: str, role: str):
        """
        通知阶段开始

        Args:
            stage: 阶段名称
            role: 执行角色
        """
        self._indent = 1
        self._emit(f"▶ 阶段 '{stage}' 开始", NotifierLevel.INFO)
        self._emit(f"角色: {role}", NotifierLevel.INFO)

    def notify_role_task(self, role_type: str, role_id: str, task: str):
        """
        通知角色任务

        Args:
            role_type: 角色类型
            role_id: 角色ID
            task: 任务描述
        """
        self._indent = 1
        task_display = task[:60] if len(task) > 60 else task
        self._emit(f"[{role_type}] {role_id} 正在处理: {task_display}...", NotifierLevel.INFO)

    def notify_role_action(self, role_type: str, action: str, detail: str = ""):
        """
        通知角色动作

        Args:
            role_type: 角色类型
            action: 动作描述
            detail: 详细信息
        """
        self._indent = 2
        msg = f"[{role_type}] {action}"
        if detail:
            detail_display = detail[:80] if len(detail) > 80 else detail
            msg += f": {detail_display}"
        self._emit(msg, NotifierLevel.INFO)

    def notify_file_created(self, file_path: str, lines: int = 0):
        """
        通知文件创建

        Args:
            file_path: 文件路径
            lines: 行数
        """
        self._indent = 2
        if lines > 0:
            self._emit(f"文件: {file_path} ({lines} 行)", NotifierLevel.INFO)
        else:
            self._emit(f"文件: {file_path}", NotifierLevel.INFO)

    def notify_score_change(
        self,
        role_id: str,
        role_type: str,
        delta: int,
        reason: str,
        new_score: int,
    ):
        """
        通知积分变化（立即输出）

        Args:
            role_id: 角色ID
            role_type: 角色类型
            delta: 积分变化量
            reason: 变化原因
            new_score: 新积分
        """
        self._indent = 2

        # 构建积分变化消息
        sign = "+" if delta > 0 else ""
        self._emit(
            f"[Score] {role_type} {sign}{delta} ({reason}) → {new_score}",
            NotifierLevel.SCORE
        )

        # 记录积分变化
        change_record = {
            "role_id": role_id,
            "role_type": role_type,
            "delta": delta,
            "reason": reason,
            "new_score": new_score,
            "timestamp": datetime.now().isoformat(),
        }
        self._score_changes.append(change_record)

        # 触发回调
        if self._on_score_change:
            self._on_score_change(change_record)

    def notify_issues_found(self, issues: list[str], severity: str = "medium"):
        """
        通知发现问题

        Args:
            issues: 问题列表
            severity: 严重程度
        """
        self._indent = 2
        level = NotifierLevel.WARNING if severity in ("medium", "low") else NotifierLevel.ERROR
        self._emit(f"发现 {len(issues)} 个问题 ({severity}):", level)

        self._indent = 3
        for issue in issues[:5]:  # 最多显示5个
            issue_display = issue[:80] if len(issue) > 80 else issue
            self._emit(f"- {issue_display}", level)

        if len(issues) > 5:
            self._emit(f"... 还有 {len(issues) - 5} 个问题", level)

    def notify_issues_fixed(self, count: int):
        """
        通知问题已修复

        Args:
            count: 修复数量
        """
        self._indent = 2
        self._emit(f"已修复 {count} 个问题", NotifierLevel.SUCCESS)

    def notify_stage_complete(self, stage: str, status: str, output: str = ""):
        """
        通知阶段完成

        Args:
            stage: 阶段名称
            status: 状态 (completed/failed)
            output: 输出信息
        """
        self._indent = 1
        icon = "✓" if status == "completed" else "✗"
        level = NotifierLevel.SUCCESS if status == "completed" else NotifierLevel.WARNING
        self._emit(f"{icon} 阶段 '{stage}' {status}", level)

        if output and self._verbosity != VerbosityMode.SIMPLE:
            self._indent = 2
            output_display = output[:100] if len(output) > 100 else output
            self._emit(f"输出: {output_display}", level)

    def notify_workflow_complete(self, workflow: str, success: bool, summary: dict | None = None):
        """
        通知工作流完成

        Args:
            workflow: 工作流名称
            success: 是否成功
            summary: 总结信息
        """
        self._indent = 0

        # 计算耗时
        elapsed = 0.0
        if self._workflow_start_time:
            elapsed = (datetime.now() - self._workflow_start_time).total_seconds()

        status = "完成" if success else "失败"
        icon = "✅" if success else "❌"
        level = NotifierLevel.SUCCESS if success else NotifierLevel.ERROR

        self._emit(f"{icon} 工作流{status}: {workflow} (耗时 {elapsed:.1f}s)", level)

        # 输出积分变化总结
        if self._score_changes and self._verbosity != VerbosityMode.SIMPLE:
            self._emit("积分变化汇总:", NotifierLevel.SCORE)
            self._indent = 1
            for change in self._score_changes:
                sign = "+" if change["delta"] > 0 else ""
                self._emit(
                    f"  {change['role_type']}: {sign}{change['delta']} → {change['new_score']}",
                    NotifierLevel.SCORE
                )
            self._indent = 0

        # 输出其他总结信息
        if summary and self._verbosity == VerbosityMode.DEBUG:
            self._emit(f"详细结果: {summary}", NotifierLevel.DEBUG)

        self._emit("═" * self.WIDTH)

    def notify_task_state(self, task_id: str, old_state: str, new_state: str):
        """
        通知任务状态变化

        Args:
            task_id: 任务ID
            old_state: 旧状态
            new_state: 新状态
        """
        self._indent = 1
        self._emit(f"任务 {task_id[:8]}...: {old_state} → {new_state}", NotifierLevel.INFO)

    def notify_error(self, message: str, detail: str = ""):
        """
        通知错误

        Args:
            message: 错误消息
            detail: 详细信息
        """
        self._emit(f"错误: {message}", NotifierLevel.ERROR)
        if detail and self._verbosity == VerbosityMode.DEBUG:
            self._indent = 1
            self._emit(f"详情: {detail[:200]}", NotifierLevel.DEBUG)

    # ==================== 新增：流程强制执行通知 ====================

    def notify_workflow_stage_required(
        self,
        current_stage: str,
        required_stage: str,
        reason: str,
    ):
        """
        通知必须先完成某个阶段

        Args:
            current_stage: 当前阶段
            required_stage: 需要先完成的阶段
            reason: 原因说明
        """
        self._emit(
            f"⛔ 当前阶段 '{current_stage}' 需要先完成 '{required_stage}'",
            NotifierLevel.ERROR
        )
        self._emit(f"   原因: {reason}", NotifierLevel.INFO)
        self._emit(f"   请执行: harness.run_stage('{required_stage}')", NotifierLevel.INFO)

    def notify_boundary_violation(
        self,
        role_type: str,
        role_id: str,
        action: str,
        reason: str,
        suggestion: str,
    ):
        """
        通知边界违规

        Args:
            role_type: 角色类型
            role_id: 角色ID
            action: 违规行为
            reason: 违规原因
            suggestion: 建议处理方式
        """
        self._emit(
            f"⛔ 角色 [{role_type}] {role_id} 无权执行: {action}",
            NotifierLevel.ERROR
        )
        self._emit(f"   原因: {reason}", NotifierLevel.WARNING)
        if suggestion:
            self._emit(f"   建议: {suggestion}", NotifierLevel.INFO)
        self._emit("📋 违规已记录到审计日志", NotifierLevel.INFO)

    def notify_gate_blocked(
        self,
        gate_name: str,
        reason: str,
    ):
        """
        通知质量门禁被阻止

        Args:
            gate_name: 门禁名称
            reason: 阻止原因
        """
        self._emit(
            f"🚫 质量门禁 '{gate_name}' 未通过",
            NotifierLevel.ERROR
        )
        self._emit(f"   原因: {reason}", NotifierLevel.WARNING)
        self._emit("   流程已暂停，请修复问题后重试", NotifierLevel.INFO)

    def notify_process_guide(
        self,
        current_stage: str,
        next_stages: list[str],
        required_roles: list[str],
    ):
        """
        通知流程指引

        Args:
            current_stage: 当前阶段
            next_stages: 后续阶段列表
            required_roles: 需要的角色列表
        """
        self._emit("📋 流程指引", NotifierLevel.INFO)
        self._emit(f"   当前阶段: {current_stage}", NotifierLevel.INFO)
        if next_stages:
            self._emit(f"   后续阶段: {' → '.join(next_stages)}", NotifierLevel.INFO)
        if required_roles:
            self._emit(f"   需要角色: {', '.join(required_roles)}", NotifierLevel.INFO)

    def notify_bypass_attempt(
        self,
        action: str,
        skip_level: str,
        admin_override: bool,
    ):
        """
        通知跳过尝试

        Args:
            action: 操作类型
            skip_level: 跳过级别
            admin_override: 是否管理员覆盖
        """
        if admin_override:
            self._emit(
                f"⚠️ 管理员覆盖: 跳过 {skip_level} 级别检查 ({action})",
                NotifierLevel.WARNING
            )
            self._emit("   此操作已记录到审计日志", NotifierLevel.INFO)
        elif skip_level != "none":
            self._emit(
                f"📋 跳过级别: {skip_level} ({action})",
                NotifierLevel.INFO
            )

    def notify_score_ranking(self, rankings: list[dict]):
        """
        通知积分排行

        Args:
            rankings: 排行列表，每项包含 role_type, role_id, score, grade
        """
        self._emit("🏆 积分排行:", NotifierLevel.SCORE)
        self._indent = 1
        for i, rank in enumerate(rankings[:5], 1):
            grade_icon = {
                "excellent": "🏆",
                "good": "⭐",
                "pass": "📌",
                "warning": "⚠️",
            }.get(rank.get("grade", ""), "")
            self._emit(
                f"{i}. {grade_icon} [{rank['role_type']}] {rank['role_id']}: {rank['score']}分",
                NotifierLevel.SCORE
            )
        self._indent = 0

    def notify_score_ranking_summary(self, total_roles: int, avg_score: float):
        """
        通知积分排行摘要

        Args:
            total_roles: 总角色数
            avg_score: 平均积分
        """
        self._emit(
            f"📊 团队积分: {total_roles} 个角色, 平均 {avg_score:.1f} 分",
            NotifierLevel.SCORE
        )

    def notify_debug(self, message: str):
        """
        通知调试信息

        Args:
            message: 调试消息
        """
        if self._verbosity == VerbosityMode.DEBUG:
            self._emit(message, NotifierLevel.DEBUG)

    def get_score_changes(self) -> list[dict]:
        """获取本次工作流的积分变化记录"""
        return self._score_changes.copy()

    def reset(self):
        """重置状态"""
        self._indent = 0
        self._workflow_start_time = None
        self._current_workflow = ""
        self._score_changes = []


# ==================== 全局通知器管理 ====================

_notifier: UserNotifier | None = None


def get_notifier() -> UserNotifier:
    """获取全局通知器实例"""
    global _notifier
    if _notifier is None:
        _notifier = UserNotifier(
            enabled=True,
            verbosity=VerbosityMode.DETAILED,
        )
    return _notifier


def set_notifier(notifier: UserNotifier) -> None:
    """设置全局通知器"""
    global _notifier
    _notifier = notifier


def enable_notifier(enabled: bool = True) -> None:
    """启用/禁用通知器"""
    global _notifier
    if _notifier:
        _notifier.enabled = enabled


def set_verbosity(mode: VerbosityMode) -> None:
    """设置详细程度"""
    global _notifier
    if _notifier:
        _notifier._verbosity = mode


# ==================== 导出 ====================

__all__ = [
    "UserNotifier",
    "NotifierLevel",
    "VerbosityMode",
    "get_notifier",
    "set_notifier",
    "enable_notifier",
    "set_verbosity",
]