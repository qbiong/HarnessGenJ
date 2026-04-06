"""
Tests for Document Sync Module

测试文档同步功能:
- 文档变更监听
- 版本一致性检查
- 增量同步
- 同步状态
"""

import pytest
import tempfile
import os
from pathlib import Path
from harnessgenj.sync.doc_sync import (
    DocumentSyncManager,
    SyncConfig,
    SyncStatus,
    DocumentVersion,
    SyncResult,
    create_sync_manager,
)


class TestSyncConfig:
    """测试同步配置"""

    def test_create_default_config(self):
        """创建默认配置"""
        config = SyncConfig()
        assert config.enabled is True
        assert config.auto_sync is True
        assert config.sync_interval == 60.0

    def test_create_custom_config(self):
        """创建自定义配置"""
        config = SyncConfig(
            enabled=False,
            auto_sync=False,
            sync_interval=30.0,
            backup_enabled=False,
        )
        assert config.enabled is False
        assert config.sync_interval == 30.0
        assert config.backup_enabled is False

    def test_config_max_backups(self):
        """最大备份数配置"""
        config = SyncConfig(max_backups=10)
        assert config.max_backups == 10


class TestSyncStatus:
    """测试同步状态"""

    def test_synced_status(self):
        """Synced 状态"""
        assert SyncStatus.SYNCED.value == "synced"

    def test_pending_status(self):
        """Pending 状态"""
        assert SyncStatus.PENDING.value == "pending"

    def test_conflict_status(self):
        """Conflict 状态"""
        assert SyncStatus.CONFLICT.value == "conflict"

    def test_error_status(self):
        """Error 状态"""
        assert SyncStatus.ERROR.value == "error"


class TestDocumentVersion:
    """测试文档版本"""

    def test_create_version(self):
        """创建版本"""
        version = DocumentVersion(
            doc_name="README.md",
            version_hash="abc123",
            last_modified=100.0,
            size=1000,
        )
        assert version.doc_name == "README.md"
        assert version.version_hash == "abc123"
        assert version.sync_status == SyncStatus.SYNCED

    def test_version_with_checksum(self):
        """带校验和的版本"""
        version = DocumentVersion(
            doc_name="test.md",
            version_hash="hash",
            last_modified=100.0,
            size=500,
            checksum="sha256hash",
        )
        assert version.checksum == "sha256hash"

    def test_version_sync_status(self):
        """版本同步状态"""
        version = DocumentVersion(
            doc_name="test.md",
            version_hash="hash",
            last_modified=100.0,
            size=500,
            sync_status=SyncStatus.PENDING,
        )
        assert version.sync_status == SyncStatus.PENDING

    def test_version_last_sync_at(self):
        """最后同步时间"""
        version = DocumentVersion(
            doc_name="test.md",
            version_hash="hash",
            last_modified=100.0,
            size=500,
            last_sync_at=150.0,
        )
        assert version.last_sync_at == 150.0


class TestSyncResult:
    """测试同步结果"""

    def test_success_result(self):
        """成功结果"""
        result = SyncResult(
            doc_name="test.md",
            success=True,
            status=SyncStatus.SYNCED,
        )
        assert result.success is True
        assert result.status == SyncStatus.SYNCED

    def test_failure_result(self):
        """失败结果"""
        result = SyncResult(
            doc_name="test.md",
            success=False,
            status=SyncStatus.ERROR,
            message="Document not found",
        )
        assert result.success is False
        assert result.message == "Document not found"

    def test_result_with_changes(self):
        """带变更信息的结果"""
        result = SyncResult(
            doc_name="test.md",
            success=True,
            status=SyncStatus.SYNCED,
            changes={"old_hash": "abc", "new_hash": "def"},
        )
        assert result.changes["old_hash"] == "abc"


class TestDocumentSyncManager:
    """测试文档同步管理器"""

    def test_create_manager(self):
        """创建管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            assert isinstance(manager, DocumentSyncManager)
            assert manager.config.enabled is True

    def test_create_manager_with_config(self):
        """创建带配置的管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SyncConfig(enabled=False)
            manager = create_sync_manager(tmpdir, config=config)
            assert manager.config.enabled is False

    def test_ensure_directories(self):
        """确保目录存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            assert (Path(tmpdir) / "documents").exists()
            assert (Path(tmpdir) / "backups").exists()

    def test_register_document(self):
        """注册文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            # 创建测试文档
            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Test content")

            result = manager.register_document("test.md")
            assert result is True

            # 检查文档已注册
            docs = manager.list_documents()
            assert len(docs) == 1

    def test_register_document_twice(self):
        """重复注册"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            result = manager.register_document("test.md")
            assert result is False  # 不能重复注册

    def test_unregister_document(self):
        """注销文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            result = manager.unregister_document("test.md")
            assert result is True

            docs = manager.list_documents()
            assert len(docs) == 0

    def test_unregister_nonexistent(self):
        """注销不存在文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            result = manager.unregister_document("nonexistent.md")
            assert result is False

    def test_list_documents(self):
        """列出文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            for name in ["doc1.md", "doc2.md", "doc3.md"]:
                doc_path = Path(tmpdir) / "documents" / name
                doc_path.write_text(f"Content of {name}")
                manager.register_document(name)

            docs = manager.list_documents()
            assert len(docs) == 3

    def test_sync_document_new(self):
        """同步新文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Initial content")

            manager.register_document("test.md")
            result = manager.sync_document("test.md")

            assert result.success is True
            assert result.status == SyncStatus.SYNCED

    def test_sync_document_no_change(self):
        """同步无变更文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            # 第一次同步
            manager.sync_document("test.md")
            # 第二次同步（无变更）
            result = manager.sync_document("test.md")

            assert result.success is True
            assert "No changes detected" in result.message

    def test_sync_document_with_change(self):
        """同步变更文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Original content")

            manager.register_document("test.md")
            manager.sync_document("test.md")

            # 修改文档
            doc_path.write_text("Updated content with more text")
            result = manager.sync_document("test.md")

            assert result.success is True
            # 检查有变更信息
            assert "changes" in result.model_dump()

    def test_sync_nonexistent_document(self):
        """同步不存在文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            result = manager.sync_document("nonexistent.md")

            assert result.success is False
            assert result.status == SyncStatus.ERROR
            assert "not registered" in result.message

    def test_sync_all(self):
        """同步所有文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            for name in ["doc1.md", "doc2.md"]:
                doc_path = Path(tmpdir) / "documents" / name
                doc_path.write_text(f"Content of {name}")
                manager.register_document(name)

            results = manager.sync_all()
            assert len(results) == 2
            assert all(r.success for r in results)

    def test_detect_changes(self):
        """检测变更"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Original")

            manager.register_document("test.md")
            manager.sync_document("test.md")

            # 无变更时检测
            changes = manager.detect_changes("test.md")
            assert changes["changed"] is False

            # 修改后检测
            doc_path.write_text("Modified")
            changes = manager.detect_changes("test.md")
            assert changes["changed"] is True

    def test_detect_changes_nonexistent(self):
        """检测不存在文档变更"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            changes = manager.detect_changes("nonexistent.md")
            assert "error" in changes

    def test_check_consistency(self):
        """检查一致性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Original")

            manager.register_document("test.md")
            manager.sync_document("test.md")

            # 无变更时检查
            inconsistent = manager.check_consistency()
            assert len(inconsistent) == 0

            # 修改后检查
            doc_path.write_text("Modified")
            inconsistent = manager.check_consistency()
            assert len(inconsistent) == 1

    def test_get_sync_status(self):
        """获取同步状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            status = manager.get_sync_status("test.md")
            assert status == SyncStatus.SYNCED

    def test_get_sync_status_nonexistent(self):
        """获取不存在文档状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            status = manager.get_sync_status("nonexistent.md")
            assert status is None

    def test_get_stats(self):
        """获取统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")
            manager.register_document("test.md")
            manager.sync_document("test.md")

            stats = manager.get_stats()
            assert stats["documents_registered"] == 1
            # 检查有同步统计
            assert "total_syncs" in stats

    def test_reset_stats(self):
        """重置统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")
            manager.register_document("test.md")
            manager.sync_document("test.md")

            manager.reset_stats()
            stats = manager.get_stats()
            assert stats["total_syncs"] == 0

    def test_backup_document(self):
        """备份文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SyncConfig(backup_enabled=True, max_backups=3)
            manager = create_sync_manager(tmpdir, config=config)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            manager.sync_document("test.md")

            # 修改并同步多次
            for i in range(5):
                doc_path.write_text(f"Content v{i}")
                manager.sync_document("test.md")

            # 检查备份数量不超过 max_backups
            backup_dir = Path(tmpdir) / "backups"
            backups = list(backup_dir.glob("test.md.*.bak"))
            assert len(backups) <= config.max_backups

    def test_backup_disabled(self):
        """禁用备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SyncConfig(backup_enabled=False)
            manager = create_sync_manager(tmpdir, config=config)

            doc_path = Path(tmpdir) / "documents" / "test.md"
            doc_path.write_text("Content")

            manager.register_document("test.md")
            manager.sync_document("test.md")

            backup_dir = Path(tmpdir) / "backups"
            backups = list(backup_dir.glob("*.bak"))
            assert len(backups) == 0

    def test_stop_auto_sync(self):
        """停止自动同步"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            manager.stop_auto_sync()
            assert manager.config.auto_sync is False


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_sync_manager(self):
        """创建同步管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_sync_manager(tmpdir)
            assert isinstance(manager, DocumentSyncManager)

    def test_create_with_config(self):
        """创建带配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SyncConfig(sync_interval=30.0)
            manager = create_sync_manager(tmpdir, config=config)
            assert manager.config.sync_interval == 30.0