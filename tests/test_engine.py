"""
Engine (Harness) Tests - 测试主入口 Harness API

测试覆盖:
- 团队管理
- 快速开发
- 工作流执行
- 记忆系统
"""

import pytest
import tempfile
import os
from py_ha import Harness, create_harness, RoleType


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

    def test_add_role(self):
        """测试添加角色"""
        harness = Harness(persistent=False)
        harness.add_role("developer", "新开发")

        team = harness.get_team()
        assert len(team) == 1
        assert team[0]["name"] == "新开发"


class TestQuickDevelopment:
    """测试快速开发"""

    def test_develop_feature(self):
        """测试功能开发"""
        harness = Harness(persistent=False)
        result = harness.develop("实现用户登录功能")

        assert result["status"] == "completed"
        assert result["stages_completed"] == 3

    def test_fix_bug(self):
        """测试Bug修复"""
        harness = Harness(persistent=False)
        result = harness.fix_bug("登录页面报错")

        assert result["status"] == "completed"
        assert result["stages_completed"] == 3


class TestAnalyzeAndDesign:
    """测试分析和设计"""

    def test_analyze(self):
        """测试需求分析"""
        harness = Harness(persistent=False)
        harness.setup_team()

        result = harness.analyze("用户需要一个仪表盘")
        assert "analysis" in result

    def test_design(self):
        """测试架构设计"""
        harness = Harness(persistent=False)
        harness.setup_team()

        result = harness.design("微服务架构系统")
        assert "design" in result


class TestMemorySystem:
    """测试记忆系统"""

    def test_remember_and_recall(self):
        """测试记忆和回忆"""
        harness = Harness(persistent=False)

        harness.remember("key1", "内容1")
        harness.remember("key2", "重要内容", important=True)

        assert harness.recall("key1") == "内容1"
        assert harness.recall("key2") == "重要内容"


class TestStatusReport:
    """测试状态报告"""

    def test_get_status(self):
        """测试获取状态"""
        harness = Harness(persistent=False)
        harness.setup_team()
        harness.develop("功能1")

        status = harness.get_status()
        assert status["team"]["size"] == 6
        assert status["stats"]["features_developed"] == 1

    def test_get_report(self):
        """测试获取报告"""
        harness = Harness("测试项目", persistent=False)
        harness.setup_team()
        harness.develop("功能1")
        harness.fix_bug("Bug1")

        report = harness.get_report()
        assert "测试项目" in report


class TestPipelineStatus:
    """测试工作流状态"""

    def test_pipeline_status(self):
        """测试工作流状态"""
        harness = Harness(persistent=False)
        harness.setup_team()

        status = harness.get_pipeline_status()
        assert "stats" in status
        assert "coordinator_stats" in status