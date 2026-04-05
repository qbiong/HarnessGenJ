"""
Workflow Context - 工作流上下文

存储工作流执行过程中的:
- 项目信息
- 角色实例
- 交付物
- 执行历史
"""

from typing import Any
from pydantic import BaseModel, Field
import time


class WorkflowContext(BaseModel):
    """
    工作流上下文 - 执行环境

    包含:
    - 项目基本信息
    - 角色映射
    - 交付物存储
    - 执行历史
    """

    project_id: str = Field(..., description="项目ID")
    project_name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目描述")

    # 角色
    roles: dict[str, str] = Field(default_factory=dict, description="角色ID映射")

    # 交付物
    artifacts: dict[str, Any] = Field(default_factory=dict, description="交付物")

    # 执行历史
    history: list[dict[str, Any]] = Field(default_factory=list, description="执行历史")

    # 元数据
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")

    def add_artifact(self, name: str, content: Any, stage: str = "") -> None:
        """添加交付物"""
        self.artifacts[name] = {
            "content": content,
            "stage": stage,
            "created_at": time.time(),
        }
        self.updated_at = time.time()

    def get_artifact(self, name: str) -> Any | None:
        """获取交付物"""
        artifact = self.artifacts.get(name)
        return artifact["content"] if artifact else None

    def record_event(self, event_type: str, details: dict[str, Any]) -> None:
        """记录事件"""
        self.history.append({
            "type": event_type,
            "details": details,
            "timestamp": time.time(),
        })
        self.updated_at = time.time()

    def get_summary(self) -> dict[str, Any]:
        """获取摘要"""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "roles_count": len(self.roles),
            "artifacts_count": len(self.artifacts),
            "events_count": len(self.history),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }