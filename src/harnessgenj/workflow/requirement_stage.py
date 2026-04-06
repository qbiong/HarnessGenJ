"""
Requirement Detection Stage - 需求检测阶段

作为工作流阶段集成到 pipeline 中，与 IntentRouter 配合使用：
- IntentRouter：路由决策（走哪个工作流）
- RequirementDetectionStage：需求提取（提取具体需求内容）

职责：
1. 从用户消息中提取具体需求
2. 调用确认机制
3. 更新文档和创建任务
"""

from typing import Any
from pydantic import BaseModel, Field
import time

from harnessgenj.maintenance.detector import (
    RequirementDetector,
    DetectedRequirement,
    RequirementType,
    DetectionSource,
)
from harnessgenj.maintenance.confirmation import (
    ConfirmationManager,
    ConfirmationStatus,
    PendingConfirmation,
)
from harnessgenj.maintenance.manager import DocumentMaintenanceManager


class RequirementDetectionResult(BaseModel):
    """需求检测结果"""

    detected_requirements: list[DetectedRequirement] = Field(
        default_factory=list, description="检测到的需求列表"
    )
    pending_confirmations: list[PendingConfirmation] = Field(
        default_factory=list, description="待确认列表"
    )
    confirmed_requirements: list[DetectedRequirement] = Field(
        default_factory=list, description="已确认的需求"
    )
    created_tasks: list[dict[str, Any]] = Field(
        default_factory=list, description="创建的任务"
    )
    needs_user_input: bool = Field(default=False, description="是否需要用户输入")
    summary: str = Field(default="", description="检测摘要")


class RequirementDetectionStage:
    """
    需求检测阶段

    作为工作流阶段使用，与 IntentRouter 配合：
    - IntentRouter 已完成意图路由（如 development_pipeline）
    - 本阶段负责从消息中提取具体需求内容

    使用示例:
        stage = RequirementDetectionStage(memory_manager)

        # 在工作流中执行
        result = stage.execute({
            "message": "我需要一个购物车功能",
            "intent_type": "development",
            "auto_confirm_threshold": 0.9,
        })
    """

    def __init__(
        self,
        memory_manager: Any,
        auto_confirm_threshold: float = 0.9,
        enable_confirmation: bool = True,
    ) -> None:
        """
        初始化需求检测阶段

        Args:
            memory_manager: MemoryManager 实例
            auto_confirm_threshold: 自动确认阈值（置信度高于此值自动确认）
            enable_confirmation: 是否启用确认机制
        """
        self.memory = memory_manager
        self.detector = RequirementDetector()
        self.confirmation_manager = ConfirmationManager(
            auto_approve_threshold=auto_confirm_threshold
        )
        self.maintenance_manager = DocumentMaintenanceManager(memory_manager)
        self.enable_confirmation = enable_confirmation
        self.auto_confirm_threshold = auto_confirm_threshold

    def execute(
        self,
        inputs: dict[str, Any],
        auto_create_task: bool = True,
    ) -> RequirementDetectionResult:
        """
        执行需求检测

        Args:
            inputs: 输入数据，包含：
                - message: 用户消息
                - intent_type: 意图类型（可选，用于优化检测）
                - context: 上下文信息（可选）
            auto_create_task: 是否自动创建任务

        Returns:
            RequirementDetectionResult: 检测结果
        """
        message = inputs.get("message", "")
        intent_type = inputs.get("intent_type", "")
        context = inputs.get("context", {})

        result = RequirementDetectionResult()

        # 1. 检测需求
        requirements = self.detector.detect_from_message(message, context)
        result.detected_requirements = requirements

        if not requirements:
            result.summary = "未检测到明确需求"
            return result

        # 2. 处理每个需求
        for req in requirements:
            # 高置信度自动确认
            if req.confidence >= self.auto_confirm_threshold:
                req_dict = req.to_dict()
                pending = self.confirmation_manager.add_pending(req_dict)
                pending.status = ConfirmationStatus.AUTO_APPROVED
            elif self.enable_confirmation:
                # 需要用户确认
                req_dict = req.to_dict()
                pending = self.confirmation_manager.add_pending(req_dict)
                result.pending_confirmations.append(pending)
                result.needs_user_input = True
                continue
            else:
                # 禁用确认机制，直接确认
                req.confidence = self.auto_confirm_threshold

            # 3. 添加到文档
            self._add_requirement_to_document(req)

            # 4. 创建任务
            if auto_create_task:
                task = self._create_task(req)
                if task:
                    result.created_tasks.append(task)

            result.confirmed_requirements.append(req)

        # 生成摘要
        result.summary = self._generate_summary(result)

        return result

    def process_user_confirmation(
        self,
        confirmation_id: str,
        response: str,
        modification: str | None = None,
        auto_create_task: bool = True,
    ) -> dict[str, Any]:
        """
        处理用户确认

        Args:
            confirmation_id: 确认ID
            response: 用户响应
            modification: 修改内容
            auto_create_task: 是否创建任务

        Returns:
            处理结果
        """
        result = {
            "success": False,
            "requirement": None,
            "task": None,
        }

        pending = self.confirmation_manager.process_response(
            confirmation_id, response, modification
        )

        if not pending or pending.status not in [
            ConfirmationStatus.APPROVED,
            ConfirmationStatus.MODIFIED,
        ]:
            return result

        # 从 pending 数据重构需求对象
        from harnessgenj.maintenance.detector import DetectedRequirement, DetectionSource
        requirement = DetectedRequirement(
            req_id=pending.requirement_id,
            title=pending.title,
            description=pending.modification_notes or pending.description,
            req_type=RequirementType(pending.req_type),
            source=DetectionSource.USER_MESSAGE,
            confidence=pending.confidence,
            original_message=pending.original_message or "",
            context=pending.context,
        )

        # 添加到文档
        self._add_requirement_to_document(requirement)

        # 创建任务
        if auto_create_task:
            task = self._create_task(requirement)
            result["task"] = task

        result["success"] = True
        result["requirement"] = requirement.to_dict()

        return result

    def detect_from_ai_analysis(
        self,
        analysis_result: dict[str, Any],
        auto_create_task: bool = True,
    ) -> RequirementDetectionResult:
        """
        从AI分析结果检测需求

        Args:
            analysis_result: AI分析结果（代码审查、测试失败等）
            auto_create_task: 是否创建任务

        Returns:
            检测结果
        """
        result = RequirementDetectionResult()

        # 从AI分析检测
        requirements = self.detector.detect_from_analysis(analysis_result)

        for req in requirements:
            # AI发现的问题通常置信度高，直接确认
            if req.confidence >= 0.7:
                self._add_requirement_to_document(req)

                if auto_create_task:
                    task = self._create_task(req)
                    if task:
                        result.created_tasks.append(task)

                result.confirmed_requirements.append(req)

        result.summary = self._generate_summary(result)
        return result

    # ==================== 内部方法 ====================

    def _add_requirement_to_document(self, req: DetectedRequirement) -> bool:
        """将需求添加到文档"""
        requirement = {
            "req_id": req.req_id,
            "title": req.title,
            "description": req.description,
            "req_type": req.req_type.value,
            "confidence": req.confidence,
            "suggested_priority": req.suggested_priority,
        }

        notify_roles = self._get_notify_roles(req.req_type)

        try:
            self.maintenance_manager.add_requirement_to_document(
                requirement=requirement,
                document_type="requirements",
                notify_roles=notify_roles,
            )
            return True
        except Exception:
            return False

    def _create_task(self, req: DetectedRequirement) -> dict[str, Any] | None:
        """创建任务"""
        try:
            task = self.maintenance_manager.create_task_from_requirement(
                requirement={
                    "req_id": req.req_id,
                    "title": req.title,
                    "description": req.description,
                    "req_type": req.req_type.value,
                    "suggested_priority": req.suggested_priority,
                    "suggested_assignee": req.suggested_assignee,
                },
                assignee=req.suggested_assignee,
            )
            return task
        except Exception:
            return None

    def _get_notify_roles(self, req_type: RequirementType) -> list[str]:
        """获取需要通知的角色"""
        mapping = {
            RequirementType.FEATURE: ["developer", "architect"],
            RequirementType.BUG_FIX: ["developer", "tester"],
            RequirementType.IMPROVEMENT: ["developer", "architect"],
            RequirementType.CONSTRAINT: ["architect"],
            RequirementType.QUESTION: [],
            RequirementType.FEEDBACK: ["product_manager"],
        }
        return mapping.get(req_type, ["developer"])

    def _generate_summary(self, result: RequirementDetectionResult) -> str:
        """生成检测摘要"""
        parts = []

        if result.detected_requirements:
            parts.append(f"检测到 {len(result.detected_requirements)} 个需求")

        if result.confirmed_requirements:
            parts.append(f"已确认 {len(result.confirmed_requirements)} 个")

        if result.pending_confirmations:
            parts.append(f"待确认 {len(result.pending_confirmations)} 个")

        if result.created_tasks:
            parts.append(f"创建 {len(result.created_tasks)} 个任务")

        return "，".join(parts) if parts else "无需求检测"


def create_requirement_detection_stage(
    memory_manager: Any,
    auto_confirm_threshold: float = 0.9,
    enable_confirmation: bool = True,
) -> RequirementDetectionStage:
    """创建需求检测阶段"""
    return RequirementDetectionStage(
        memory_manager=memory_manager,
        auto_confirm_threshold=auto_confirm_threshold,
        enable_confirmation=enable_confirmation,
    )