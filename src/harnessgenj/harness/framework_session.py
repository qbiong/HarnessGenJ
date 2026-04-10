"""
FrameworkSession - 框架会话状态管理

确保所有代码修改操作都经过框架许可。

设计理念：
- 框架是操作的"签证官"
- AI必须在获得许可后才能执行操作
- 所有操作都有审计记录

使用示例：
    # 在 develop() 开始时
    session = FrameworkSession.get_instance()
    session.grant_permission(task_id, ["src/module.py"])

    # 在 Hooks PreToolUse 时
    if not session.check_permission(file_path):
        return "❌ 未获得操作许可，请先通过框架创建任务"
"""

import os
import json
import time
from typing import Any
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, PrivateAttr
from enum import Enum


class OperationMode(str, Enum):
    """操作模式"""
    FRAMEWORK = "framework"  # 框架控制模式 - 有许可
    DIRECT = "direct"         # 直接模式 - 无许可（记录违规）
    ADMIN = "admin"           # 管理员模式 - 绕过检查


class PermissionRecord(BaseModel):
    """操作许可记录"""
    file_path: str = Field(description="文件路径")
    granted_at: float = Field(default_factory=time.time, description="许可时间")
    operation: str = Field(default="write", description="允许的操作类型")
    reason: str = Field(default="", description="许可原因")


# 模块级单例存储（避免 Pydantic 私有属性问题）
_session_instance: "FrameworkSession | None" = None
_session_file: Path | None = None


class FrameworkSession(BaseModel):
    """框架会话状态"""

    session_id: str = Field(default="", description="会话ID")
    active_task_id: str | None = Field(default=None, description="当前活动任务ID")
    permitted_files: dict[str, PermissionRecord] = Field(
        default_factory=dict,
        description="允许修改的文件列表 {file_path: PermissionRecord}"
    )
    operation_mode: OperationMode = Field(
        default=OperationMode.DIRECT,
        description="当前操作模式"
    )
    created_at: float = Field(default_factory=time.time, description="会话创建时间")
    updated_at: float = Field(default_factory=time.time, description="最后更新时间")

    # 审计记录
    operations_log: list[dict[str, Any]] = Field(
        default_factory=list,
        description="操作审计日志"
    )

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def get_instance(cls, workspace: str | None = None) -> "FrameworkSession":
        """获取会话单例"""
        global _session_instance, _session_file

        if _session_instance is not None:
            return _session_instance

        if workspace is None:
            workspace = os.environ.get("HGJ_WORKSPACE", ".harnessgenj")

        _session_file = Path(workspace) / "session_state.json"

        # 尝试从文件加载
        if _session_file.exists():
            try:
                with open(_session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _session_instance = cls(**data)
            except Exception:
                _session_instance = cls(session_id=f"session_{int(time.time())}")
        else:
            _session_instance = cls(session_id=f"session_{int(time.time())}")

        return _session_instance

    def grant_permission(
        self,
        task_id: str,
        file_paths: list[str],
        operation: str = "write",
        reason: str = ""
    ) -> None:
        """
        签发操作许可

        Args:
            task_id: 关联的任务ID
            file_paths: 允许操作的文件列表
            operation: 操作类型
            reason: 许可原因
        """
        self.active_task_id = task_id
        self.operation_mode = OperationMode.FRAMEWORK

        for file_path in file_paths:
            self.permitted_files[file_path] = PermissionRecord(
                file_path=file_path,
                operation=operation,
                reason=reason or f"Task: {task_id}"
            )

        self.updated_at = time.time()
        self._save()

        # 记录审计日志
        self._log_operation("grant_permission", {
            "task_id": task_id,
            "files": file_paths,
            "operation": operation
        })

    def check_permission(self, file_path: str, operation: str = "write") -> bool:
        """
        检查是否有操作许可

        Args:
            file_path: 要操作的文件路径
            operation: 操作类型

        Returns:
            是否有许可
        """
        # 管理员模式始终允许
        if self.operation_mode == OperationMode.ADMIN:
            return True

        # 检查文件是否在许可列表中
        # 支持目录匹配：如果许可了 src/，则 src/xxx.py 也允许
        normalized_path = os.path.normpath(file_path)

        for permitted_path, record in self.permitted_files.items():
            normalized_permitted = os.path.normpath(permitted_path)

            # 精确匹配
            if normalized_path == normalized_permitted:
                return True

            # 目录前缀匹配
            if normalized_path.startswith(normalized_permitted + os.sep):
                return True

        # 记录未授权操作尝试
        self._log_operation("unauthorized_attempt", {
            "file_path": file_path,
            "operation": operation
        })

        return False

    def revoke_permission(self, file_path: str | None = None) -> None:
        """
        撤销操作许可

        Args:
            file_path: 要撤销的文件路径，None则撤销所有
        """
        if file_path:
            self.permitted_files.pop(file_path, None)
        else:
            self.permitted_files.clear()
            self.active_task_id = None
            self.operation_mode = OperationMode.DIRECT

        self.updated_at = time.time()
        self._save()

    def complete_task(self, task_id: str) -> None:
        """
        完成任务，清理许可
        """
        if self.active_task_id == task_id:
            self._log_operation("task_completed", {"task_id": task_id})
            self.revoke_permission()

    def get_permission_hint(self, file_path: str) -> str:
        """
        获取权限提示信息

        Args:
            file_path: 尝试操作的文件

        Returns:
            提示信息
        """
        return f"""
[HGJ 权限检查] 未获得操作许可

文件: {file_path}

要获得操作许可，请先通过框架创建任务：
  - harness.develop("功能描述")
  - harness.fix_bug("问题描述")
  - MCP工具: task_develop / task_fix_bug

当前会话状态:
  - 任务ID: {self.active_task_id or "无"}
  - 操作模式: {self.operation_mode.value}
  - 已许可文件数: {len(self.permitted_files)}
"""

    def _log_operation(self, operation: str, details: dict[str, Any]) -> None:
        """记录操作审计日志"""
        self.operations_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        })

        # 保持日志在合理大小
        if len(self.operations_log) > 1000:
            self.operations_log = self.operations_log[-500:]

        self._save()

    def _save(self) -> None:
        """保存会话状态"""
        global _session_file
        if _session_file:
            try:
                _session_file.parent.mkdir(parents=True, exist_ok=True)
                with open(_session_file, "w", encoding="utf-8") as f:
                    json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 保存失败不影响主要功能

    def get_status(self) -> dict[str, Any]:
        """获取会话状态摘要"""
        return {
            "session_id": self.session_id,
            "active_task_id": self.active_task_id,
            "operation_mode": self.operation_mode.value,
            "permitted_files_count": len(self.permitted_files),
            "permitted_files": list(self.permitted_files.keys()),
            "operations_count": len(self.operations_log),
        }


# ==================== 便捷函数 ====================

def get_session() -> FrameworkSession:
    """获取当前会话"""
    return FrameworkSession.get_instance()


def grant_permission(task_id: str, files: list[str], reason: str = "") -> None:
    """签发操作许可"""
    session = get_session()
    session.grant_permission(task_id, files, reason=reason)


def check_permission(file_path: str) -> bool:
    """检查操作许可"""
    session = get_session()
    return session.check_permission(file_path)


def revoke_permission(file_path: str | None = None) -> None:
    """撤销操作许可"""
    session = get_session()
    session.revoke_permission(file_path)