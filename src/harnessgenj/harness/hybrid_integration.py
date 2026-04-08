"""
Hybrid Integration - Hooks + MCP 双轨集成层

设计原则：
1. 优先使用 Hooks（轻量级，无需额外服务）
2. 当 Hooks 无效时自动切换到内置触发
3. 支持 MCP Server 扩展（预留接口）
4. 对用户透明，自动降级

使用示例:
    from harnessgenj.harness.hybrid_integration import HybridIntegration, create_hybrid_integration

    # 创建混合集成层
    integration = create_hybrid_integration(harness)

    # 自动选择最佳方式触发
    integration.trigger_on_write_complete(file_path, content)

    # 检测当前使用的模式
    mode = integration.get_active_mode()  # "hooks" | "builtin" | "mcp"
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
from pathlib import Path
import os
import json
import time
import threading

from harnessgenj.harness.hooks_integration import (
    HooksIntegration,
    HooksConfig,
    HooksResult,
)
from harnessgenj.quality.score import ScoreManager
from harnessgenj.quality.tracker import QualityTracker
from harnessgenj.harness.adversarial import AdversarialWorkflow
from harnessgenj.harness.event_triggers import TriggerManager, TriggerEvent


class IntegrationMode(str, Enum):
    """集成模式"""
    HOOKS = "hooks"          # Claude Code Hooks（优先）
    BUILTIN = "builtin"      # 内置触发（降级方案）
    MCP = "mcp"              # MCP Server（未来扩展）


class HybridConfig(BaseModel):
    """混合集成配置"""
    preferred_mode: IntegrationMode = Field(
        default=IntegrationMode.HOOKS,
        description="首选集成模式"
    )
    auto_fallback: bool = Field(
        default=True,
        description="自动降级到内置模式"
    )
    hooks_timeout_seconds: float = Field(
        default=5.0,
        description="Hooks 检测超时时间"
    )
    mcp_server_url: str | None = Field(
        default=None,
        description="MCP Server URL（可选）"
    )
    persist_events: bool = Field(
        default=True,
        description="是否持久化事件"
    )


class EventRecord(BaseModel):
    """事件记录"""
    event_type: str
    timestamp: float = Field(default_factory=time.time)
    mode: IntegrationMode
    data: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class HybridIntegration:
    """
    混合集成层 - Hooks + MCP 双轨并存

    核心功能：
    1. 自动检测 Hooks 是否生效
    2. 无效时自动切换到内置触发
    3. 统一的事件接口
    4. 支持未来 MCP Server 扩展

    设计哲学：
    - 优雅降级：Hooks 失效不影响功能
    - 用户无感：自动选择最佳模式
    - 可扩展性：支持未来新增集成方式
    """

    def __init__(
        self,
        config: HybridConfig,
        hooks_integration: HooksIntegration,
        trigger_manager: TriggerManager | None = None,
        score_manager: ScoreManager | None = None,
        quality_tracker: QualityTracker | None = None,
        adversarial_workflow: AdversarialWorkflow | None = None,
        workspace: str = ".harnessgenj",
    ) -> None:
        """
        初始化混合集成层

        Args:
            config: 混合配置
            hooks_integration: Hooks 集成实例
            trigger_manager: 事件触发管理器
            score_manager: 积分管理器
            quality_tracker: 质量追踪器
            adversarial_workflow: 对抗工作流
            workspace: 工作空间路径
        """
        self.config = config
        self._hooks = hooks_integration
        self._trigger_manager = trigger_manager
        self._score_manager = score_manager
        self._quality_tracker = quality_tracker
        self._adversarial = adversarial_workflow
        self._workspace = workspace

        # 当前活跃模式
        self._active_mode = config.preferred_mode

        # Hooks 有效性状态
        self._hooks_effective: bool | None = None  # None = 未检测
        self._hooks_check_time: float = 0

        # 事件历史
        self._events: list[EventRecord] = []
        self._events_lock = threading.Lock()

        # 内置触发器回调
        self._builtin_callbacks: dict[str, list[Callable]] = {
            "on_write_complete": [],
            "on_edit_complete": [],
            "on_task_complete": [],
            "on_issue_found": [],
            "on_security_issue": [],
        }

        # 统计
        self._stats = {
            "hooks_success": 0,
            "hooks_failure": 0,
            "builtin_triggers": 0,
            "mcp_triggers": 0,
            "events_persisted": 0,
        }

        # 初始化时检测 Hooks
        if config.auto_fallback:
            self._check_hooks_effectiveness()

    # ==================== 模式检测 ====================

    def _check_hooks_effectiveness(self) -> bool:
        """
        检测 Hooks 是否生效

        检测方法：
        1. 检查 .claude/settings.json 是否存在并配置正确
        2. 检查最近是否有 Hooks 触发的事件记录
        3. 尝试触发测试 Hook（可选）

        Returns:
            Hooks 是否有效
        """
        # 如果最近检测过，使用缓存结果
        if self._hooks_effective is not None:
            if time.time() - self._hooks_check_time < 60:  # 1分钟缓存
                return self._hooks_effective

        self._hooks_check_time = time.time()

        # 方法1: 检查配置文件
        hooks_configured = self._check_hooks_config()

        # 方法2: 检查事件文件（Hooks 触发会写入事件文件）
        events_dir = Path(self._workspace) / "events"
        has_recent_events = False

        if events_dir.exists():
            try:
                # 检查最近5分钟内是否有 Hooks 触发的事件
                event_files = list(events_dir.glob("event_*.json"))
                now = time.time()
                for event_file in event_files[-10:]:  # 只检查最近10个
                    try:
                        mtime = event_file.stat().st_mtime
                        if now - mtime < 300:  # 5分钟内
                            with open(event_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if data.get("triggered_by") == "hooks":
                                has_recent_events = True
                                break
                    except Exception:
                        pass
            except Exception:
                pass

        # 判断 Hooks 是否有效
        # 如果配置了 hooks 且最近有事件，则认为有效
        effective = hooks_configured and (has_recent_events or self._hooks_effective is True)

        # 更新状态
        self._hooks_effective = effective

        # 如果 Hooks 无效，切换到内置模式
        if not effective and self.config.auto_fallback:
            self._active_mode = IntegrationMode.BUILTIN

        return effective

    def _check_hooks_config(self) -> bool:
        """检查 Hooks 配置是否存在"""
        settings_path = Path(".claude") / "settings.json"

        if not settings_path.exists():
            return False

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})
            post_hooks = hooks.get("PostToolUse", [])

            # 检查是否包含 harnessgenj_hook.py
            for hook_config in post_hooks:
                for hook in hook_config.get("hooks", []):
                    command = hook.get("command", "")
                    if "harnessgenj_hook.py" in command:
                        return True

            return False
        except Exception:
            return False

    def get_active_mode(self) -> IntegrationMode:
        """获取当前活跃模式"""
        if self.config.auto_fallback:
            self._check_hooks_effectiveness()
        return self._active_mode

    def force_mode(self, mode: IntegrationMode) -> None:
        """强制使用指定模式"""
        self._active_mode = mode
        self._hooks_effective = mode == IntegrationMode.HOOKS

    # ==================== 事件触发 ====================

    def trigger_on_write_complete(
        self,
        file_path: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> EventRecord:
        """
        触发 Write 完成事件

        根据当前模式选择触发方式：
        - Hooks: 由 Claude Code 自动调用（此方法作为备用）
        - Builtin: 记录事件，由 TriggerManager 分发
        - MCP: 调用 MCP Server

        注意：此方法只负责事件记录和分发，不直接执行对抗审查。
        对抗审查由 TriggerManager 统一分发到对应角色执行。

        Args:
            file_path: 文件路径
            content: 文件内容
            metadata: 元数据

        Returns:
            事件记录
        """
        data = {
            "file_path": file_path,
            "content_length": len(content),
            "content": content,  # 传递内容供 TriggerManager 使用
            "metadata": metadata or {},
        }

        event = self._create_event("on_write_complete", data)

        try:
            if self._active_mode == IntegrationMode.HOOKS:
                # Hooks 模式：记录事件，并触发 TriggerManager 执行角色审查
                event.mode = IntegrationMode.HOOKS
                self._stats["hooks_success"] += 1
                # 关键修复：Hooks 模式下也需要触发 TriggerManager 激活角色
                if self._trigger_manager:
                    self._trigger_manager.trigger(
                        TriggerEvent.ON_WRITE_COMPLETE,
                        {"file_path": file_path, "content": content, "metadata": metadata or {}},
                    )

            elif self._active_mode == IntegrationMode.BUILTIN:
                # 内置模式：记录事件，并通过 TriggerManager 分发对抗审查
                event.mode = IntegrationMode.BUILTIN
                self._stats["builtin_triggers"] += 1
                # 调用 TriggerManager 触发对抗审查
                if self._trigger_manager:
                    self._trigger_manager.trigger(
                        TriggerEvent.ON_WRITE_COMPLETE,
                        {"file_path": file_path, "content": content, "metadata": metadata or {}},
                    )

            elif self._active_mode == IntegrationMode.MCP:
                # MCP 模式：调用 MCP Server（未来实现）
                event.mode = IntegrationMode.MCP
                self._stats["mcp_triggers"] += 1

            event.success = True

        except Exception as e:
            event.success = False
            event.error = str(e)

            # 如果 Hooks 失败且允许降级
            if self._active_mode == IntegrationMode.HOOKS and self.config.auto_fallback:
                self._stats["hooks_failure"] += 1
                self._active_mode = IntegrationMode.BUILTIN

        self._record_event(event)
        return event

    def trigger_on_task_complete(
        self,
        task_id: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> EventRecord:
        """
        触发任务完成事件

        注意：此方法只负责事件记录，不直接更新积分。
        积分更新应由 engine.py 在调用此方法后显式调用 ScoreManager，
        或由 TriggerManager 分发到对应角色执行。

        Args:
            task_id: 任务ID
            summary: 完成摘要
            metadata: 元数据

        Returns:
            事件记录
        """
        data = {
            "task_id": task_id,
            "summary": summary,
            "metadata": metadata or {},
        }

        event = self._create_event("on_task_complete", data)

        try:
            # 记录事件，不直接更新积分
            if self._active_mode == IntegrationMode.BUILTIN:
                self._execute_builtin("on_task_complete", data)
                self._stats["builtin_triggers"] += 1

            event.success = True

        except Exception as e:
            event.success = False
            event.error = str(e)

        self._record_event(event)
        return event

    def trigger_on_issue_found(
        self,
        generator_id: str,
        discriminator_id: str,
        severity: str,
        description: str,
        task_id: str | None = None,
    ) -> EventRecord:
        """
        触发问题发现事件

        注意：此方法只负责事件记录，不直接更新积分。
        积分更新应由 AdversarialWorkflow 或 engine.py 统一处理。

        Args:
            generator_id: 生成者ID
            discriminator_id: 判别者ID
            severity: 严重程度
            description: 问题描述
            task_id: 任务ID

        Returns:
            事件记录
        """
        data = {
            "generator_id": generator_id,
            "discriminator_id": discriminator_id,
            "severity": severity,
            "description": description,
            "task_id": task_id,
        }

        event = self._create_event("on_issue_found", data)
        event.success = True
        self._record_event(event)
        return event

    # ==================== 内置触发执行 ====================

    def _execute_builtin(self, event_type: str, data: dict[str, Any]) -> None:
        """
        执行内置触发回调

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        callbacks = self._builtin_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(data)
            except Exception:
                pass  # 忽略回调错误，继续执行其他回调

    def register_builtin_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        注册内置触发回调

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._builtin_callbacks:
            self._builtin_callbacks[event_type].append(callback)

    # ==================== 事件记录 ====================

    def _create_event(self, event_type: str, data: dict[str, Any]) -> EventRecord:
        """创建事件记录"""
        return EventRecord(
            event_type=event_type,
            mode=self._active_mode,
            data=data,
        )

    def _record_event(self, event: EventRecord) -> None:
        """记录事件"""
        with self._events_lock:
            self._events.append(event)

            # 保留最近100个事件
            if len(self._events) > 100:
                self._events = self._events[-100:]

        # 持久化事件
        if self.config.persist_events:
            self._persist_event(event)

    def _persist_event(self, event: EventRecord) -> None:
        """持久化事件到文件"""
        try:
            events_dir = Path(self._workspace) / "events"
            events_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            event_file = events_dir / f"event_{timestamp}_{event.event_type}.json"

            with open(event_file, "w", encoding="utf-8") as f:
                json.dump(event.model_dump(), f, ensure_ascii=False, indent=2)

            self._stats["events_persisted"] += 1
        except Exception:
            pass

    # ==================== 统计和状态 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "active_mode": self._active_mode.value,
            "hooks_effective": self._hooks_effective,
            "events_count": len(self._events),
        }

    def get_recent_events(self, limit: int = 20) -> list[EventRecord]:
        """获取最近的事件"""
        with self._events_lock:
            return self._events[-limit:]

    def diagnose(self) -> dict[str, Any]:
        """
        诊断集成状态

        Returns:
            诊断结果，包含建议
        """
        result = {
            "active_mode": self._active_mode.value,
            "hooks_configured": self._check_hooks_config(),
            "hooks_effective": self._hooks_effective,
            "recommendations": [],
        }

        if not result["hooks_configured"]:
            result["recommendations"].append(
                "建议运行 auto_setup_hooks() 配置 Hooks"
            )

        if result["hooks_configured"] and not self._hooks_effective:
            result["recommendations"].append(
                "Hooks 配置存在但未检测到触发。已自动切换到内置模式。"
            )
            result["recommendations"].append(
                "如需使用 Hooks，请重启 Claude Code 会话。"
            )

        if self._active_mode == IntegrationMode.BUILTIN:
            result["recommendations"].append(
                "当前使用内置触发模式，功能正常。"
            )

        return result


# ==================== 便捷函数 ====================

def create_hybrid_integration(
    workspace: str = ".harnessgenj",
    trigger_manager: TriggerManager | None = None,
    score_manager: ScoreManager | None = None,
    quality_tracker: QualityTracker | None = None,
    adversarial_workflow: AdversarialWorkflow | None = None,
    auto_fallback: bool = True,
    preferred_mode: IntegrationMode = IntegrationMode.HOOKS,
) -> HybridIntegration:
    """
    创建混合集成实例

    Args:
        workspace: 工作空间路径
        trigger_manager: 事件触发管理器
        score_manager: 积分管理器
        quality_tracker: 质量追踪器
        adversarial_workflow: 对抗工作流
        auto_fallback: 是否自动降级
        preferred_mode: 首选模式

    Returns:
        HybridIntegration 实例
    """
    config = HybridConfig(
        preferred_mode=preferred_mode,
        auto_fallback=auto_fallback,
    )

    hooks_integration = HooksIntegration(
        config=HooksConfig(enabled=True, blocking_mode=False),
    )

    return HybridIntegration(
        config=config,
        hooks_integration=hooks_integration,
        trigger_manager=trigger_manager,
        score_manager=score_manager,
        quality_tracker=quality_tracker,
        adversarial_workflow=adversarial_workflow,
        workspace=workspace,
    )