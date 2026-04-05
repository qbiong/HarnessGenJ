"""
Engine (Harness) Tests - 测试主入口 Harness API

测试覆盖:
- 创建和初始化
- 请求接收
- 任务完成
- 记忆系统
- 状态报告
- 持久化
"""

import pytest
import tempfile
import os
import shutil
from harnessgenj import Harness, create_harness, RoleType


class TestHarnessCreation:
    """测试 Harness 创建"""

    def test_create_default(self):
        """测试默认创建"""
        harness = create_harness(persistent=False)
        assert harness is not None
        assert harness.project_name == "Default Project"

    def test_create_with_name(self):
        """测试带名称创建"""
        harness = Harness("测试项目", persistent=False)
        assert harness.project_name == "测试项目"

    def test_create_persistent(self):
        """测试持久化创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness("持久化项目", persistent=True, workspace=workspace)

            assert harness.project_name == "持久化项目"
            assert os.path.exists(workspace)


class TestRequestHandling:
    """测试请求处理"""

    def test_receive_request_feature(self):
        """测试接收功能请求"""
        harness = Harness(persistent=False)
        result = harness.receive_request("实现用户登录功能", request_type="feature")

        assert result["success"] is True
        assert result["task_id"].startswith("TASK-")
        assert result["priority"] == "P1"
        assert result["category"] == "功能开发"

    def test_receive_request_bug(self):
        """测试接收Bug请求"""
        harness = Harness(persistent=False)
        result = harness.receive_request("登录页面报错", request_type="bug")

        assert result["success"] is True
        assert result["priority"] == "P0"
        assert result["category"] == "Bug修复"

    def test_complete_task(self):
        """测试完成任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness(persistent=True, workspace=workspace)
            result = harness.receive_request("测试功能", request_type="feature")

            success = harness.complete_task(result["task_id"], "功能已完成")
            assert success is True

            status = harness.get_status()
            assert status["project_stats"]["features_completed"] == 1


class TestTeamManagement:
    """测试团队管理"""

    def test_setup_default_team(self):
        """测试默认团队创建"""
        harness = Harness(persistent=False)
        result = harness.setup_team()

        assert result["team_size"] == 6
        assert len(result["members"]) == 6

    def test_setup_custom_team(self):
        """测试自定义团队"""
        harness = Harness(persistent=False)
        result = harness.setup_team({
            "developer": "小李",
            "tester": "小张",
        })

        assert result["team_size"] == 2
        assert len(result["members"]) == 2

    def test_get_team(self):
        """测试获取团队"""
        harness = Harness(persistent=False)
        harness.setup_team()

        team = harness.get_team()
        assert len(team) == 6


class TestMemorySystem:
    """测试记忆系统"""

    def test_remember_and_recall(self):
        """测试记忆和回忆"""
        harness = Harness(persistent=False)

        harness.remember("key1", "内容1")
        harness.remember("key2", "重要内容", important=True)

        assert harness.recall("key1") == "内容1"
        assert harness.recall("key2") == "重要内容"

    def test_record(self):
        """测试记录"""
        harness = Harness(persistent=False)

        success = harness.record("开发日志内容", context="开发过程")
        assert success is True

    def test_get_context_prompt(self):
        """测试获取上下文提示"""
        harness = Harness(persistent=False)
        harness.remember("tech_stack", "Python")

        context = harness.get_context_prompt("developer")

        assert len(context) > 0

    def test_get_minimal_context(self):
        """测试获取最小上下文"""
        harness = Harness(persistent=False)

        context = harness.get_minimal_context()

        assert len(context) > 0


class TestStatusReport:
    """测试状态报告"""

    def test_get_status(self):
        """测试获取状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")
            harness = Harness(persistent=True, workspace=workspace)
            harness.setup_team()
            harness.receive_request("功能1", request_type="feature")

            status = harness.get_status()
            assert status["team"]["size"] == 6
            assert status["project_stats"]["features_total"] == 1

    def test_get_report(self):
        """测试获取报告"""
        harness = Harness("测试项目", persistent=False)
        harness.setup_team()

        report = harness.get_report()
        assert "测试项目" in report


class TestSessionManagement:
    """测试会话管理"""

    def test_chat(self):
        """测试对话"""
        harness = Harness(persistent=False)

        result = harness.chat("你好，我需要一个功能")

        assert result["message_id"] is not None

    def test_switch_session(self):
        """测试切换会话"""
        harness = Harness(persistent=False)

        result = harness.switch_session("development")

        assert result["switched"] is True


class TestPersistence:
    """测试持久化"""

    def test_save_and_reload(self):
        """测试保存和重新加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".harnessgenj")

            # 创建并保存
            harness = Harness("持久化测试", persistent=True, workspace=workspace)
            harness.receive_request("功能1", request_type="feature")
            harness.remember("key1", "value1")
            harness.save()

            # 重新加载
            harness2 = Harness("新项目", persistent=True, workspace=workspace)

            assert harness2.project_name == "持久化测试"
            # 检查知识是否恢复
            recalled = harness2.recall("key1")
            assert recalled == "value1", f"Expected 'value1', got {recalled}"