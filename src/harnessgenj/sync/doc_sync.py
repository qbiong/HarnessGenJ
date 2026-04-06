"""
Document Sync - 文档同步管理

提供文档自动同步能力：
- 文档变更监听
- 版本一致性检查
- 增量同步
- 与 Claude Memory 集成

使用示例:
    from harnessgenj.sync import DocumentSyncManager, create_sync_manager

    sync = create_sync_manager(workspace=".harnessgenj")

    # 注册文档
    sync.register_document("progress.md", auto_sync=True)

    # 手动同步
    result = sync.sync_document("progress.md")

    # 检查一致性
    inconsistent = sync.check_consistency()
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import os
import time
import hashlib
import json
import threading
from pathlib import Path


class SyncStatus(Enum):
    """同步状态"""

    SYNCED = "synced"           # 已同步
    PENDING = "pending"         # 待同步
    CONFLICT = "conflict"       # 冲突
    ERROR = "error"             # 错误


class DocumentVersion(BaseModel):
    """文档版本信息"""

    doc_name: str
    version_hash: str
    last_modified: float
    size: int
    sync_status: SyncStatus = SyncStatus.SYNCED
    last_sync_at: float | None = None
    checksum: str = ""


class SyncConfig(BaseModel):
    """同步配置"""

    enabled: bool = Field(default=True, description="是否启用自动同步")
    auto_sync: bool = Field(default=True, description="是否自动同步")
    sync_interval: float = Field(default=60.0, description="同步间隔（秒）")
    check_on_change: bool = Field(default=True, description="变更时检查")
    backup_enabled: bool = Field(default=True, description="是否备份")
    max_backups: int = Field(default=5, description="最大备份数")


class SyncResult(BaseModel):
    """同步结果"""

    doc_name: str
    success: bool
    status: SyncStatus
    message: str = ""
    changes: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class DocumentSyncManager:
    """
    文档同步管理器

    支持:
    1. 文档变更监听
    2. 版本一致性检查
    3. 增量同步
    4. 自动/手动同步
    """

    def __init__(
        self,
        workspace: str,
        memory_manager: Any = None,
        config: SyncConfig | None = None,
    ) -> None:
        """
        初始化文档同步管理器

        Args:
            workspace: 工作空间目录
            memory_manager: MemoryManager 实例（可选）
            config: 同步配置
        """
        self.workspace = Path(workspace)
        self.memory_manager = memory_manager
        self.config = config or SyncConfig()

        self._documents: dict[str, DocumentVersion] = {}
        self._sync_lock = threading.Lock()
        self._last_sync_time: float = 0

        # 统计
        self._stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "conflicts_detected": 0,
        }

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要目录存在"""
        (self.workspace / "documents").mkdir(parents=True, exist_ok=True)
        (self.workspace / "backups").mkdir(parents=True, exist_ok=True)

    # ==================== 文档注册 ====================

    def register_document(
        self,
        doc_name: str,
        doc_path: str | None = None,
        auto_sync: bool = True,
    ) -> bool:
        """
        注册文档到同步管理器

        Args:
            doc_name: 文档名称
            doc_path: 文档路径（可选）
            auto_sync: 是否自动同步

        Returns:
            是否注册成功
        """
        with self._sync_lock:
            if doc_name in self._documents:
                return False

            # 计算初始版本
            version_info = self._calculate_version(doc_name, doc_path)

            self._documents[doc_name] = DocumentVersion(
                doc_name=doc_name,
                version_hash=version_info["hash"],
                last_modified=version_info["modified"],
                size=version_info["size"],
                sync_status=SyncStatus.SYNCED,
                checksum=version_info["checksum"],
            )

            return True

    def unregister_document(self, doc_name: str) -> bool:
        """注销文档"""
        with self._sync_lock:
            if doc_name not in self._documents:
                return False
            del self._documents[doc_name]
            return True

    def list_documents(self) -> list[DocumentVersion]:
        """列出所有注册的文档"""
        return list(self._documents.values())

    # ==================== 同步操作 ====================

    def sync_document(self, doc_name: str) -> SyncResult:
        """
        同步单个文档

        Args:
            doc_name: 文档名称

        Returns:
            SyncResult: 同步结果
        """
        with self._sync_lock:
            if doc_name not in self._documents:
                return SyncResult(
                    doc_name=doc_name,
                    success=False,
                    status=SyncStatus.ERROR,
                    message="Document not registered",
                )

            doc_version = self._documents[doc_name]

            # 检查是否有变更
            current_version = self._calculate_version(doc_name)
            if current_version["hash"] == doc_version.version_hash:
                return SyncResult(
                    doc_name=doc_name,
                    success=True,
                    status=SyncStatus.SYNCED,
                    message="No changes detected",
                )

            # 执行同步
            try:
                # 备份旧版本
                if self.config.backup_enabled:
                    self._backup_document(doc_name)

                # 更新到记忆系统
                if self.memory_manager:
                    content = self._read_document(doc_name)
                    if content:
                        self.memory_manager.store_document(doc_name, content)

                # 更新版本信息
                doc_version.version_hash = current_version["hash"]
                doc_version.last_modified = current_version["modified"]
                doc_version.size = current_version["size"]
                doc_version.checksum = current_version["checksum"]
                doc_version.sync_status = SyncStatus.SYNCED
                doc_version.last_sync_at = time.time()

                self._stats["total_syncs"] += 1
                self._stats["successful_syncs"] += 1

                return SyncResult(
                    doc_name=doc_name,
                    success=True,
                    status=SyncStatus.SYNCED,
                    message="Document synced successfully",
                    changes={
                        "old_hash": doc_version.version_hash,
                        "new_hash": current_version["hash"],
                    },
                )

            except Exception as e:
                self._stats["total_syncs"] += 1
                self._stats["failed_syncs"] += 1

                return SyncResult(
                    doc_name=doc_name,
                    success=False,
                    status=SyncStatus.ERROR,
                    message=str(e),
                )

    def sync_all(self) -> list[SyncResult]:
        """同步所有文档"""
        results = []
        for doc_name in list(self._documents.keys()):
            results.append(self.sync_document(doc_name))
        return results

    def check_consistency(self) -> list[dict[str, Any]]:
        """
        检查所有文档的一致性

        Returns:
            不一致的文档列表
        """
        inconsistent = []
        with self._sync_lock:
            for doc_name, doc_version in self._documents.items():
                current = self._calculate_version(doc_name)
                if current["hash"] != doc_version.version_hash:
                    inconsistent.append({
                        "doc_name": doc_name,
                        "stored_hash": doc_version.version_hash,
                        "current_hash": current["hash"],
                        "last_sync": doc_version.last_sync_at,
                    })
                    doc_version.sync_status = SyncStatus.PENDING
                    self._stats["conflicts_detected"] += 1
        return inconsistent

    # ==================== 变更检测 ====================

    def detect_changes(self, doc_name: str) -> dict[str, Any]:
        """
        检测文档变更

        Args:
            doc_name: 文档名称

        Returns:
            变更信息
        """
        with self._sync_lock:
            if doc_name not in self._documents:
                return {"error": "Document not registered"}

            doc_version = self._documents[doc_name]
            current = self._calculate_version(doc_name)

            return {
                "changed": current["hash"] != doc_version.version_hash,
                "old_size": doc_version.size,
                "new_size": current["size"],
                "old_modified": doc_version.last_modified,
                "new_modified": current["modified"],
                "old_hash": doc_version.version_hash,
                "new_hash": current["hash"],
            }

    def _calculate_version(self, doc_name: str, doc_path: str | None = None) -> dict[str, Any]:
        """计算文档版本信息"""
        doc_path = doc_path or str(self.workspace / "documents" / doc_name)
        path = Path(doc_path)

        if not path.exists():
            # 尝试从记忆系统获取
            if self.memory_manager:
                content = self.memory_manager.get_document(doc_name)
                if content:
                    return {
                        "hash": hashlib.md5(content.encode()).hexdigest(),
                        "modified": time.time(),
                        "size": len(content),
                        "checksum": hashlib.sha256(content.encode()).hexdigest(),
                    }
            return {"hash": "", "modified": 0, "size": 0, "checksum": ""}

        stat = path.stat()
        content = path.read_text(encoding="utf-8")

        return {
            "hash": hashlib.md5(content.encode()).hexdigest(),
            "modified": stat.st_mtime,
            "size": stat.st_size,
            "checksum": hashlib.sha256(content.encode()).hexdigest(),
        }

    def _read_document(self, doc_name: str) -> str | None:
        """读取文档内容"""
        doc_path = self.workspace / "documents" / doc_name
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        return None

    def _backup_document(self, doc_name: str) -> None:
        """备份文档"""
        if not self.config.backup_enabled:
            return

        source = self.workspace / "documents" / doc_name
        if not source.exists():
            return

        backup_dir = self.workspace / "backups"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{doc_name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        # 复制文件
        backup_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        # 清理旧备份
        self._cleanup_backups(doc_name)

    def _cleanup_backups(self, doc_name: str) -> None:
        """清理旧备份"""
        backup_dir = self.workspace / "backups"
        pattern = f"{doc_name}.*.bak"
        backups = sorted(backup_dir.glob(pattern), reverse=True)

        # 保留最新的 N 个备份
        for old_backup in backups[self.config.max_backups:]:
            old_backup.unlink()

    # ==================== 自动同步 ====================

    def start_auto_sync(self) -> None:
        """启动自动同步"""
        if not self.config.auto_sync:
            return

        def sync_loop():
            while self.config.enabled and self.config.auto_sync:
                self.sync_all()
                time.sleep(self.config.sync_interval)

        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()

    def stop_auto_sync(self) -> None:
        """停止自动同步"""
        self.config.auto_sync = False

    # ==================== 状态查询 ====================

    def get_sync_status(self, doc_name: str) -> SyncStatus | None:
        """获取文档同步状态"""
        doc = self._documents.get(doc_name)
        return doc.sync_status if doc else None

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "documents_registered": len(self._documents),
            "auto_sync_enabled": self.config.auto_sync,
            "last_sync_time": self._last_sync_time,
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "conflicts_detected": 0,
        }


# ==================== 便捷函数 ====================

def create_sync_manager(
    workspace: str,
    memory_manager: Any = None,
    config: SyncConfig | None = None,
) -> DocumentSyncManager:
    """
    创建文档同步管理器

    Args:
        workspace: 工作空间目录
        memory_manager: MemoryManager 实例
        config: 同步配置

    Returns:
        DocumentSyncManager 实例
    """
    return DocumentSyncManager(workspace, memory_manager, config)