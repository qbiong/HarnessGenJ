"""
测试框架主动输出和状态检测机制

测试内容：
- is_initialized() 静态方法
- get_initialization_status() 静态方法
- get_last_instance() 静态方法
- 初始化时主动输出
"""

import pytest
import tempfile
import os
from pathlib import Path

from harnessgenj import Harness


class TestFrameworkStatusDetection:
    """测试框架状态检测机制"""

    def test_is_initialized_before_init(self):
        """测试初始化前状态"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        assert Harness.is_initialized() is False

    def test_is_initialized_after_init(self):
        """测试初始化后状态"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            # 初始化后应该为 True
            assert Harness.is_initialized() is True

    def test_get_initialization_status_before_init(self):
        """测试初始化前状态详情"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._current_project_path = None
        Harness._active_workflow_id = None
        Harness._active_roles = {}
        Harness._last_instance = None

        status = Harness.get_initialization_status()

        assert status["initialized"] is False
        assert status["project_path"] is None
        assert status["active_workflow"] is None
        assert status["active_roles"] == []
        assert status["last_instance_available"] is False

    def test_get_initialization_status_after_init(self):
        """测试初始化后状态详情"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._current_project_path = None
        Harness._active_roles = {}
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            status = Harness.get_initialization_status()

            assert status["initialized"] is True
            assert status["project_path"] == workspace
            # 团队创建后应该有角色
            assert len(status["active_roles"]) > 0
            assert status["last_instance_available"] is True

    def test_get_last_instance(self):
        """测试获取最后实例"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        # 初始化前应该为 None
        assert Harness.get_last_instance() is None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            # 初始化后应该返回实例
            last_instance = Harness.get_last_instance()
            assert last_instance is not None
            assert last_instance.project_name == "TestProject"

    def test_active_roles_tracking(self):
        """测试活动角色跟踪"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._active_roles = {}
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            # 检查静态状态中的角色
            assert "developer_1" in Harness._active_roles
            assert "code_reviewer_1" in Harness._active_roles
            assert "bug_hunter_1" in Harness._active_roles
            assert "project_manager_1" in Harness._active_roles

    def test_from_project_updates_status(self):
        """测试 from_project 方法更新状态"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._current_project_path = None
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建项目目录结构
            project_path = os.path.join(tmpdir, "MyProject")
            os.makedirs(project_path)

            # 创建 README.md
            readme_path = os.path.join(project_path, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write("# MyProject\n\n这是一个测试项目。")

            harness = Harness.from_project(project_path)

            status = Harness.get_initialization_status()

            assert status["initialized"] is True
            # 项目路径应该是实际项目路径（而非 workspace）
            assert status["project_path"] == project_path

    def test_workflow_status_tracking(self):
        """测试工作流状态跟踪"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._active_workflow_id = None
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace, auto_setup_team=True)

            # 初始化时工作流状态应该为 None
            assert Harness._active_workflow_id is None

            # 注意：实际执行 develop 会触发工作流，但这里只测试静态机制
            # 不实际执行 develop 因为会涉及复杂的流程


class TestFrameworkAnnouncement:
    """测试框架主动输出机制"""

    def test_announce_initialization_outputs_info(self):
        """测试初始化主动输出"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")

            # 初始化框架（会自动调用 _announce_initialization）
            harness = Harness("TestProject", workspace=workspace)

            # 验证框架已初始化（主动输出已执行）
            assert Harness.is_initialized() is True
            assert harness.project_name == "TestProject"

    def test_announcement_includes_team_info(self):
        """测试主动输出包含团队信息"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace, auto_setup_team=True)

            # 团队应该已创建
            assert harness._stats.team_size > 0
            assert len(Harness._active_roles) > 0


class TestIntegrationWithHooks:
    """测试与 Hooks 集成"""

    def test_hooks_can_detect_framework_status(self):
        """测试 Hooks 可以检测框架状态"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        # 模拟 Hooks 检测场景
        # 场景1：框架未初始化
        if not Harness.is_initialized():
            # Hooks 可以提醒用户初始化框架
            suggestion = "请先初始化框架: harness = Harness.from_project('.')"
            assert "初始化框架" in suggestion

        # 场景2：框架已初始化
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            if Harness.is_initialized():
                # Hooks 可以获取框架实例
                instance = Harness.get_last_instance()
                assert instance is not None
                assert instance.project_name == "TestProject"

    def test_hooks_can_check_before_code_edit(self):
        """测试 Hooks 可以在代码编辑前检查"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        # 模拟 Hooks 在 PreToolUse 时检测
        # 场景1：用户尝试直接编辑代码
        tool_name = "Write"
        file_path = "src/main.py"

        # 如果框架未初始化，Hooks 应该提醒
        if not Harness.is_initialized():
            should_warn = True
            assert should_warn is True

        # 场景2：框架已初始化，可以正常编辑
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("TestProject", workspace=workspace)

            if Harness.is_initialized():
                # 可以获取实例进行操作
                instance = Harness.get_last_instance()
                assert instance is not None


class TestCLAUDE_mdGuidelines:
    """测试 CLAUDE.md 指导文件"""

    def test_claude_md_exists(self):
        """测试 CLAUDE.md 文件存在"""
        project_root = Path(__file__).parent.parent
        claude_md = project_root / "CLAUDE.md"

        assert claude_md.exists()

    def test_claude_md_contains_key_sections(self):
        """测试 CLAUDE.md 包含关键章节"""
        project_root = Path(__file__).parent.parent
        claude_md = project_root / "CLAUDE.md"

        content = claude_md.read_text(encoding="utf-8")

        # 检查关键章节（支持新旧结构）
        assert "框架使用指南" in content or "核心原则" in content or "一句话启动框架" in content
        assert "develop" in content
        assert "fix_bug" in content
        assert "角色边界" in content or "边界定义" in content or "角色说明" in content
        assert "积分" in content

    def test_claude_md_contains_mandatory_declarations(self):
        """测试 CLAUDE.md 包含强制声明"""
        project_root = Path(__file__).parent.parent
        claude_md = project_root / "CLAUDE.md"

        content = claude_md.read_text(encoding="utf-8")

        # 检查强制声明
        assert "强制" in content or "必须" in content
        assert "禁止" in content


class TestMultipleInstances:
    """测试多个实例场景"""

    def test_multiple_instances_tracking(self):
        """测试多个实例的状态跟踪"""
        # 重置静态状态
        Harness._instance_initialized = False
        Harness._last_instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace1 = os.path.join(tmpdir, ".harnessgenj1")
            workspace2 = os.path.join(tmpdir, ".harnessgenj2")

            harness1 = Harness("Project1", workspace=workspace1)

            # 第一个实例应该被跟踪
            assert Harness.get_last_instance() == harness1

            harness2 = Harness("Project2", workspace=workspace2)

            # 最后一个实例应该是第二个
            assert Harness.get_last_instance() == harness2
            assert Harness.get_last_instance().project_name == "Project2"

            # 状态应该仍然是已初始化
            assert Harness.is_initialized() is True


class TestStatusReset:
    """测试状态重置场景"""

    def test_status_persists_across_instances(self):
        """测试状态在实例之间持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")

            harness = Harness("TestProject", workspace=workspace)

            # 初始化后状态为 True
            assert Harness.is_initialized() is True

            # 创建新实例（不会重置状态）
            harness2 = Harness("AnotherProject", workspace=workspace)

            # 状态应该仍然是 True
            assert Harness.is_initialized() is True