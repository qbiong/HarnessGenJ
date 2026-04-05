"""
Human-in-the-loop - 人机交互节点

Harness 内置能力之一:
- 执行审批
- 用户输入获取
- 决策确认
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid


class ApprovalStatus(Enum):
    """审批状态"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest(BaseModel):
    """审批请求"""

    request_id: str = Field(..., description="请求ID")
    action: str = Field(..., description="需要审批的操作")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="状态")
    timeout: int = Field(default=300, description="超时时间(秒)")
    created_at: float = Field(default=0.0, description="创建时间")


class ApprovalResponse(BaseModel):
    """审批响应"""

    request_id: str = Field(..., description="请求ID")
    approved: bool = Field(..., description="是否批准")
    feedback: str | None = Field(default=None, description="反馈信息")
    responded_at: float = Field(..., description="响应时间")


class HumanLoop:
    """
    人机交互循环 - 提供审批和交互能力

    核心功能:
    1. 操作审批
    2. 用户输入获取
    3. 决策确认
    4. 超时处理

    审批模式:
    - auto: 自动批准（默认，用于测试环境）
    - manual: 手动批准（需要用户确认）
    - callback: 回调批准（通过回调函数处理）
    """

    def __init__(
        self,
        default_timeout: int = 300,
        approval_mode: str = "auto",
        approval_callback: Callable[[ApprovalRequest], bool] | None = None,
    ) -> None:
        """
        初始化人机交互循环

        Args:
            default_timeout: 默认超时时间（秒）
            approval_mode: 审批模式 (auto/manual/callback)
            approval_callback: 审批回调函数（用于 callback 模式）
        """
        self.default_timeout = default_timeout
        self.approval_mode = approval_mode
        self.approval_callback = approval_callback
        self._pending_requests: dict[str, ApprovalRequest] = {}
        self._responses: dict[str, ApprovalResponse] = {}
        self._stats = {
            "total_requests": 0,
            "approved": 0,
            "rejected": 0,
            "timeout": 0,
        }

    def request_approval_sync(
        self,
        action: str,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ApprovalRequest:
        """
        同步审批请求（阻塞直到获得响应）

        Args:
            action: 需要审批的操作描述
            context: 上下文信息
            timeout: 超时时间

        Returns:
            ApprovalRequest: 审批请求（包含最终状态）
        """
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            action=action,
            context=context or {},
            timeout=timeout or self.default_timeout,
            created_at=time.time(),
            status=ApprovalStatus.PENDING,
        )
        self._pending_requests[request.request_id] = request
        self._stats["total_requests"] += 1

        # 根据审批模式处理
        if self.approval_mode == "auto":
            # 自动批准
            request.status = ApprovalStatus.APPROVED
            self._stats["approved"] += 1

        elif self.approval_mode == "callback" and self.approval_callback:
            # 通过回调处理
            try:
                approved = self.approval_callback(request)
                request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
                if approved:
                    self._stats["approved"] += 1
                else:
                    self._stats["rejected"] += 1
            except Exception:
                request.status = ApprovalStatus.REJECTED
                self._stats["rejected"] += 1

        elif self.approval_mode == "manual":
            # 手动审批模式：尝试从控制台获取输入
            try:
                print(f"\n[审批请求] {action}")
                if context:
                    print(f"上下文: {context}")
                print("批准? (y/n): ", end="", flush=True)

                # 非阻塞检查超时
                start_time = time.time()
                import select
                import sys

                while time.time() - start_time < request.timeout:
                    # 检查是否有输入（Unix 系统）
                    if sys.platform != 'win32':
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            response = sys.stdin.readline().strip().lower()
                            break
                    else:
                        # Windows 系统：简化处理，默认批准
                        response = 'y'
                        break
                else:
                    # 超时
                    request.status = ApprovalStatus.TIMEOUT
                    self._stats["timeout"] += 1
                    return request

                if response in ('y', 'yes', '是'):
                    request.status = ApprovalStatus.APPROVED
                    self._stats["approved"] += 1
                else:
                    request.status = ApprovalStatus.REJECTED
                    self._stats["rejected"] += 1

            except Exception:
                # 控制台输入失败，默认批准
                request.status = ApprovalStatus.APPROVED
                self._stats["approved"] += 1

        else:
            # 未知模式，默认批准
            request.status = ApprovalStatus.APPROVED
            self._stats["approved"] += 1

        return request

    async def request_approval(
        self,
        action: str,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ApprovalRequest:
        """
        异步审批请求

        Args:
            action: 需要审批的操作描述
            context: 上下文信息
            timeout: 超时时间

        Returns:
            ApprovalRequest: 审批请求
        """
        # 使用同步实现
        return self.request_approval_sync(action, context, timeout)

    def respond_approval(self, request_id: str, approved: bool, feedback: str | None = None) -> ApprovalResponse:
        """
        响应审批请求

        Args:
            request_id: 请求ID
            approved: 是否批准
            feedback: 反馈信息

        Returns:
            ApprovalResponse: 审批响应
        """
        request = self._pending_requests.get(request_id)
        if request is None:
            raise ValueError(f"Request not found: {request_id}")

        response = ApprovalResponse(
            request_id=request_id,
            approved=approved,
            feedback=feedback,
            responded_at=time.time(),
        )
        self._responses[request_id] = response

        # 更新请求状态
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED

        return response

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """获取审批请求"""
        return self._pending_requests.get(request_id)

    def get_response(self, request_id: str) -> ApprovalResponse | None:
        """获取审批响应"""
        return self._responses.get(request_id)

    async def wait_for_approval(self, request_id: str) -> ApprovalResponse:
        """
        等待审批结果

        Args:
            request_id: 请求ID

        Returns:
            ApprovalResponse: 审批响应
        """
        import asyncio

        request = self.get_request(request_id)
        if request is None:
            raise ValueError(f"Request not found: {request_id}")

        # 检查是否已有响应
        start_time = time.time()
        while time.time() - start_time < request.timeout:
            response = self.get_response(request_id)
            if response is not None:
                return response

            # 检查请求是否已有状态
            if request.status != ApprovalStatus.PENDING:
                return ApprovalResponse(
                    request_id=request_id,
                    approved=request.status == ApprovalStatus.APPROVED,
                    feedback=f"Status: {request.status.value}",
                    responded_at=time.time(),
                )

            await asyncio.sleep(0.5)

        # 超时
        request.status = ApprovalStatus.TIMEOUT
        self._stats["timeout"] += 1
        return ApprovalResponse(
            request_id=request_id,
            approved=False,
            feedback="Approval timeout",
            responded_at=time.time(),
        )

    def list_pending(self) -> list[ApprovalRequest]:
        """列出所有待审批请求"""
        return [
            r for r in self._pending_requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def get_stats(self) -> dict[str, int]:
        """获取审批统计"""
        return self._stats.copy()

    def set_approval_mode(self, mode: str, callback: Callable[[ApprovalRequest], bool] | None = None) -> None:
        """
        设置审批模式

        Args:
            mode: 审批模式 (auto/manual/callback)
            callback: 回调函数（仅 callback 模式需要）
        """
        self.approval_mode = mode
        if callback:
            self.approval_callback = callback