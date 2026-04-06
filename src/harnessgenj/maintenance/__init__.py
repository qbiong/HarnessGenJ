"""
Maintenance Module - 主动文档维护模块

提供自动检测需求和维护文档的能力：
- RequirementDetector: 从用户消息中提取潜在需求
- DocumentMaintenanceManager: 管理文档更新和团队通知
- ConfirmationManager: 确认机制，添加前询问用户
"""

from harnessgenj.maintenance.detector import (
    RequirementDetector,
    DetectedRequirement,
    RequirementType,
    DetectionSource,
)
from harnessgenj.maintenance.manager import (
    DocumentMaintenanceManager,
    DocumentUpdate,
    TeamNotification,
)
from harnessgenj.maintenance.confirmation import (
    ConfirmationManager,
    ConfirmationStatus,
    PendingConfirmation,
)

__all__ = [
    # Detector
    "RequirementDetector",
    "DetectedRequirement",
    "RequirementType",
    "DetectionSource",
    # Manager
    "DocumentMaintenanceManager",
    "DocumentUpdate",
    "TeamNotification",
    # Confirmation
    "ConfirmationManager",
    "ConfirmationStatus",
    "PendingConfirmation",
]