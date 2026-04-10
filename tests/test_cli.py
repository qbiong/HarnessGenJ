"""
CLI Tests - 测试命令行接口

测试覆盖:
- version 命令
- init 命令
- setup-hooks 命令
- welcome 命令
- develop 命令
- fix 命令
- team 命令
- status 命令
- sync 命令
- 主入口参数解析
"""

import pytest
import tempfile
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from harnessgenj.cli import (
    main,
    cmd_version,
    cmd_init,
    cmd_setup_hooks,
    cmd_welcome,
    cmd_develop,
    cmd_fix,
    cmd_team,
    cmd_status,
    cmd_sync,
)
from harnessgenj import __version__


class TestCmdVersion:
    """测试 version 命令"""

    def test_version_output(self, capsys):
        """测试版本输出"""
        args = MagicMock()
        cmd_version(args)
        captured = capsys.readouterr()
        assert __version__ in captured.out
        assert "HarnessGenJ" in captured.out

    def test_version_contains_python(self, capsys):
        """测试版本信息包含 Python 字样"""
        args = MagicMock()
        cmd_version(args)
        captured = capsys.readouterr()
        assert "Python" in captured.out


class TestCmdInit:
    """测试 init 命令"""

    def test_init_with_project(self):
        """测试带项目路径初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = MagicMock()
            args.project = tmpdir

            # Mock Harness 和 start_onboarding 避免交互式输入
            with patch('harnessgenj.cli.Harness') as MockHarness:
                mock_instance = MagicMock()
                MockHarness.return_value = mock_instance
                cmd_init(args)
                MockHarness.assert_called_once_with(tmpdir)
                mock_instance.start_onboarding.assert_called_once()

    def test_init_without_project(self):
        """测试不带项目路径初始化"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            MockHarness.return_value = mock_instance
            cmd_init(args)
            MockHarness.assert_called_once_with("")


class TestCmdSetupHooks:
    """测试 setup-hooks 命令"""

    def test_setup_hooks_creates_files(self):
        """测试创建 hooks 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = MagicMock()
            args.project_dir = tmpdir

            cmd_setup_hooks(args)

            claude_dir = Path(tmpdir) / ".claude"
            hook_script = claude_dir / "harnessgenj_hook.py"
            settings_path = claude_dir / "settings.json"

            assert hook_script.exists()
            assert settings_path.exists()

            # 验证 hook 脚本内容
            hook_content = hook_script.read_text(encoding="utf-8")
            assert "handle_post_tool_use" in hook_content
            assert "handle_pre_tool_use_security" in hook_content

            # 验证 settings.json 结构
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            assert "hooks" in settings
            assert "PreToolUse" in settings["hooks"]
            assert "PostToolUse" in settings["hooks"]

    def test_setup_hooks_output(self, capsys):
        """测试 setup-hooks 输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = MagicMock()
            args.project_dir = tmpdir

            cmd_setup_hooks(args)
            captured = capsys.readouterr()

            assert "Hooks" in captured.out


class TestCmdWelcome:
    """测试 welcome 命令"""

    def test_welcome_output(self, capsys):
        """测试欢迎信息输出"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.welcome.return_value = "Welcome to HarnessGenJ!"
            MockHarness.return_value = mock_instance

            cmd_welcome(args)
            captured = capsys.readouterr()

            assert "Welcome to HarnessGenJ!" in captured.out


class TestCmdDevelop:
    """测试 develop 命令"""

    def test_develop_feature(self, capsys):
        """测试开发功能"""
        args = MagicMock()
        args.project = None
        args.feature = "实现用户登录"

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.develop.return_value = {
                'status': 'completed',
                'stages_completed': 4,
                'artifacts': ['code', 'tests']
            }
            MockHarness.return_value = mock_instance

            cmd_develop(args)
            captured = capsys.readouterr()

            assert "实现用户登录" in captured.out
            assert "completed" in captured.out

    def test_develop_with_project(self):
        """测试带项目名的开发"""
        args = MagicMock()
        args.project = "MyProject"
        args.feature = "测试功能"

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.develop.return_value = {
                'status': 'pending',
                'stages_completed': 0,
                'artifacts': []
            }
            MockHarness.return_value = mock_instance

            cmd_develop(args)
            MockHarness.assert_called_once_with("MyProject")


class TestCmdFix:
    """测试 fix 命令"""

    def test_fix_bug(self, capsys):
        """测试修复 Bug"""
        args = MagicMock()
        args.project = None
        args.bug = "登录页面报错"

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.fix_bug.return_value = {
                'status': 'fixed',
                'stages_completed': 3
            }
            MockHarness.return_value = mock_instance

            cmd_fix(args)
            captured = capsys.readouterr()

            assert "登录页面报错" in captured.out


class TestCmdTeam:
    """测试 team 命令"""

    def test_team_display(self, capsys):
        """测试团队显示"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.get_team.return_value = [
                {'name': 'Alice', 'role_type': 'developer'},
                {'name': 'Bob', 'role_type': 'tester'}
            ]
            MockHarness.return_value = mock_instance

            cmd_team(args)
            captured = capsys.readouterr()

            assert "2" in captured.out  # 团队规模
            assert "Alice" in captured.out
            assert "developer" in captured.out


class TestCmdStatus:
    """测试 status 命令"""

    def test_status_display(self, capsys):
        """测试状态显示"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.get_report.return_value = "Project Status: OK"
            MockHarness.return_value = mock_instance

            cmd_status(args)
            captured = capsys.readouterr()

            assert "Project Status: OK" in captured.out


class TestCmdSync:
    """测试 sync 命令"""

    def test_sync_with_knowledge_manager(self, capsys):
        """测试知识同步"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance._agents_knowledge = MagicMock()
            mock_instance._agents_knowledge.sync_all_knowledge.return_value = {
                'updated': ['tech.md', 'conventions.md'],
                'errors': []
            }
            MockHarness.return_value = mock_instance

            cmd_sync(args)
            captured = capsys.readouterr()

            assert "2" in captured.out  # 更新文件数

    def test_sync_without_knowledge_manager(self, capsys):
        """测试无知识管理器时的同步"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance._agents_knowledge = None
            MockHarness.return_value = mock_instance

            cmd_sync(args)
            captured = capsys.readouterr()

            assert "未初始化" in captured.out or "not initialized" in captured.out.lower()


class TestMainFunction:
    """测试 main 函数"""

    def test_main_no_args(self, capsys):
        """测试无参数时的帮助输出"""
        with patch('sys.argv', ['harnessgenj']):
            main()
            captured = capsys.readouterr()
            # 无参数时应显示帮助
            assert "usage:" in captured.out.lower() or "harnessgenj" in captured.out.lower()

    def test_main_version_flag(self, capsys):
        """测试 --version 标志"""
        with patch('sys.argv', ['harnessgenj', '--version']):
            main()
            captured = capsys.readouterr()
            assert __version__ in captured.out

    def test_main_version_command(self, capsys):
        """测试 version 命令"""
        with patch('sys.argv', ['harnessgenj', 'version']):
            main()
            captured = capsys.readouterr()
            assert __version__ in captured.out

    def test_main_help(self, capsys):
        """测试帮助输出"""
        with patch('sys.argv', ['harnessgenj', '--help']):
            with pytest.raises(SystemExit):
                main()
            captured = capsys.readouterr()
            assert "HarnessGenJ" in captured.out

    def test_main_develop_command(self):
        """测试 develop 命令行"""
        with patch('sys.argv', ['harnessgenj', 'develop', '测试功能']):
            with patch('harnessgenj.cli.Harness') as MockHarness:
                mock_instance = MagicMock()
                mock_instance.develop.return_value = {
                    'status': 'completed',
                    'stages_completed': 4,
                    'artifacts': []
                }
                MockHarness.return_value = mock_instance
                main()
                MockHarness.assert_called()

    def test_main_fix_command(self):
        """测试 fix 命令行"""
        with patch('sys.argv', ['harnessgenj', 'fix', 'Bug描述']):
            with patch('harnessgenj.cli.Harness') as MockHarness:
                mock_instance = MagicMock()
                mock_instance.fix_bug.return_value = {
                    'status': 'fixed',
                    'stages_completed': 3
                }
                MockHarness.return_value = mock_instance
                main()
                mock_instance.fix_bug.assert_called_once_with("Bug描述")


class TestCLIEdgeCases:
    """测试 CLI 边界情况"""

    def test_develop_empty_feature(self, capsys):
        """测试空功能描述"""
        args = MagicMock()
        args.project = None
        args.feature = ""

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance.develop.return_value = {
                'status': 'error',
                'stages_completed': 0,
                'artifacts': []
            }
            MockHarness.return_value = mock_instance

            # 不应抛出异常
            cmd_develop(args)

    def test_setup_hooks_with_existing_settings(self):
        """测试已存在 settings.json 时的更新"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建已存在的 settings.json
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir(parents=True)
            settings_path = claude_dir / "settings.json"

            existing_settings = {
                "existing_key": "existing_value"
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(existing_settings, f)

            args = MagicMock()
            args.project_dir = tmpdir

            cmd_setup_hooks(args)

            # 验证现有配置被保留
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

            assert "existing_key" in settings
            assert settings["existing_key"] == "existing_value"
            assert "hooks" in settings

    def test_sync_with_errors(self, capsys):
        """测试同步有错误的情况"""
        args = MagicMock()
        args.project = None

        with patch('harnessgenj.cli.Harness') as MockHarness:
            mock_instance = MagicMock()
            mock_instance._agents_knowledge = MagicMock()
            mock_instance._agents_knowledge.sync_all_knowledge.return_value = {
                'updated': ['tech.md'],
                'errors': ['Error syncing conventions.md']
            }
            MockHarness.return_value = mock_instance

            cmd_sync(args)
            captured = capsys.readouterr()

            assert "Error" in captured.out or "错误" in captured.out