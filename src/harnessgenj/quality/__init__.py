"""
Quality Module - 质量保证系统

包含：
- 积分系统（ScoreManager）
- 对抗记录（AdversarialRecord）
- 质量追踪（QualityTracker）
- 任务级对抗控制器（TaskAdversarialController）
- 系统级对抗控制器（SystemAdversarialController）
"""

from harnessgenj.quality.score import ScoreManager, RoleScore, ScoreEvent
from harnessgenj.quality.record import AdversarialRecord, IssueRecord
from harnessgenj.quality.tracker import QualityTracker, FailurePattern
from harnessgenj.quality.task_adversarial import (
    TaskAdversarialController,
    TaskAdversarialConfig,
    TaskAdversarialResult,
    create_task_adversarial,
)
from harnessgenj.quality.system_adversarial import (
    SystemAdversarialController,
    SystemAnalysisResult,
    WeaknessPattern,
    BiasPattern,
    ImprovementAction,
    create_system_adversarial,
)

__all__ = [
    "ScoreManager",
    "RoleScore",
    "ScoreEvent",
    "AdversarialRecord",
    "IssueRecord",
    "QualityTracker",
    "FailurePattern",
    # 任务级对抗
    "TaskAdversarialController",
    "TaskAdversarialConfig",
    "TaskAdversarialResult",
    "create_task_adversarial",
    # 系统级对抗
    "SystemAdversarialController",
    "SystemAnalysisResult",
    "WeaknessPattern",
    "BiasPattern",
    "ImprovementAction",
    "create_system_adversarial",
]