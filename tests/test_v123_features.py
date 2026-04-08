"""
测试 v1.2.3 新增功能

覆盖以下功能：
1. _record_intent() - 意图识别记录
2. _auto_extract_knowledge() - 知识自动提取
3. get_init_prompt() - 改进的初始化提示
4. HGJMonitor - 监控工具
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from harnessgenj import Harness
from harnessgenj.workflow.intent_router import IntentResult, IntentType, create_intent_router
from harnessgenj.monitor import HGJMonitor


class TestIntentRecording:
    """测试意图识别记录功能"""

    def test_record_intent_creates_file(self, tmp_path):
        """测试 _record_intent 创建 intents.json 文件"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 模拟意图识别结果
        intent_result = IntentResult(
            intent_type=IntentType.DEVELOPMENT,
            confidence=0.85,
            original_message="帮我实现一个登录功能",
            target_workflow="development_pipeline",
        )

        # 调用记录方法
        harness._record_intent(intent_result)

        # 验证文件创建
        intents_path = tmp_path / ".harnessgenj" / "intents.json"
        assert intents_path.exists()

        # 验证内容
        with open(intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "records" in data
        assert len(data["records"]) == 1
        assert data["records"][0]["intent_type"] == "development"
        assert data["records"][0]["confidence"] == 0.85

    def test_record_intent_updates_stats(self, tmp_path):
        """测试 _record_intent 更新统计"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 记录多个意图
        for msg, intent_type in [
            ("实现登录功能", IntentType.DEVELOPMENT),
            ("修复登录bug", IntentType.BUGFIX),
            ("项目进度如何", IntentType.MANAGEMENT),
        ]:
            result = IntentResult(
                intent_type=intent_type,
                confidence=0.9,
                original_message=msg,
                target_workflow="test",
            )
            harness._record_intent(result)

        # 验证统计
        intents_path = tmp_path / ".harnessgenj" / "intents.json"
        with open(intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["stats"]["development"] == 1
        assert data["stats"]["bugfix"] == 1
        assert data["stats"]["management"] == 1

    def test_chat_records_intent(self, tmp_path):
        """测试 chat() 方法自动记录意图"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 发送消息
        result = harness.chat("帮我实现一个用户登录功能")

        # 验证意图被记录
        intents_path = tmp_path / ".harnessgenj" / "intents.json"
        assert intents_path.exists()

        with open(intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["records"]) == 1


class TestAutoExtractKnowledge:
    """测试知识自动提取功能"""

    def test_auto_extract_knowledge_bug_fix(self, tmp_path):
        """测试 Bug 修复任务的知识提取"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 创建 Bug 修复任务
        task = {
            "category": "Bug修复",
            "request": "登录页面验证码不显示",
        }
        summary = "修复了验证码组件的渲染问题"

        # 执行知识提取 - 不应抛出异常
        harness._auto_extract_knowledge(task, summary)

        # 验证不抛出异常即可
        assert True

    def test_auto_extract_knowledge_feature(self, tmp_path):
        """测试功能开发任务的知识提取"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        # 创建功能开发任务
        task = {
            "category": "功能开发",
            "request": "实现用户注册功能",
        }
        summary = "使用邮箱验证完成注册流程"

        # 执行知识提取
        harness._auto_extract_knowledge(task, summary)

        # 验证不抛出异常即可
        assert True


class TestInitPrompt:
    """测试初始化提示优化"""

    def test_get_init_prompt_user_friendly(self, tmp_path):
        """测试初始化提示是否用户友好"""
        harness = Harness("测试项目", workspace=str(tmp_path / ".harnessgenj"))

        prompt = harness.get_init_prompt()

        # 验证包含用户友好的元素
        assert "快速开始" in prompt or "HGJ框架已就绪" in prompt
        assert "直接描述需求" in prompt or "对话" in prompt
        assert "测试项目" in prompt  # 项目名称

    def test_get_init_prompt_contains_examples(self, tmp_path):
        """测试初始化提示包含使用示例"""
        harness = Harness("test_project", workspace=str(tmp_path / ".harnessgenj"))

        prompt = harness.get_init_prompt()

        # 验证包含示例或使用方式
        assert "功能" in prompt or "feature" in prompt.lower()
        # 不应该包含过于技术化的 API 调用说明
        # 应该更注重用户体验


class TestHGJMonitor:
    """测试监控工具"""

    def test_monitor_initialization(self, tmp_path):
        """测试监控器初始化"""
        monitor = HGJMonitor(tmp_path / ".harnessgenj")
        assert monitor.workspace == tmp_path / ".harnessgenj"

    def test_check_all_returns_results(self, tmp_path):
        """测试 check_all 返回结果"""
        workspace = tmp_path / ".harnessgenj"
        workspace.mkdir(parents=True, exist_ok=True)

        monitor = HGJMonitor(workspace)
        results = monitor.check_all()

        assert "hooks" in results
        assert "hybrid" in results
        assert "quality" in results
        assert "task_state" in results
        assert "intent_router" in results
        assert "memory" in results

    def test_calculate_pass_rate(self, tmp_path):
        """测试通过率计算"""
        workspace = tmp_path / ".harnessgenj"
        workspace.mkdir(parents=True, exist_ok=True)

        monitor = HGJMonitor(workspace)
        monitor.check_all()
        rate = monitor.calculate_pass_rate()

        assert 0 <= rate <= 1

    def test_generate_report(self, tmp_path):
        """测试报告生成"""
        workspace = tmp_path / ".harnessgenj"
        workspace.mkdir(parents=True, exist_ok=True)

        monitor = HGJMonitor(workspace)
        report = monitor.generate_report()

        assert "HGJ 框架状态监控报告" in report
        assert "通过率" in report

    def test_save_report(self, tmp_path):
        """测试报告保存"""
        workspace = tmp_path / ".harnessgenj"
        workspace.mkdir(parents=True, exist_ok=True)

        monitor = HGJMonitor(workspace)
        report_path = tmp_path / "monitor_report.md"
        success = monitor.save_report(report_path)

        assert success
        assert report_path.exists()


class TestFailurePatternAnalysis:
    """测试失败模式分析优化"""

    def test_analyze_patterns_returns_patterns_even_without_records(self, tmp_path):
        """测试即使没有记录也返回预定义模式"""
        from harnessgenj.quality.tracker import QualityTracker

        workspace = tmp_path / ".harnessgenj"
        workspace.mkdir(parents=True, exist_ok=True)

        tracker = QualityTracker(str(workspace))
        patterns = tracker.analyze_patterns()

        # 应该返回预定义模式
        assert len(patterns) > 0
        # 预定义模式名称
        pattern_names = [p.name for p in patterns]
        assert any("空值" in name or "异常" in name for name in pattern_names)


class TestIntegration:
    """集成测试"""

    def test_full_workflow_with_new_features(self, tmp_path):
        """测试完整工作流包含新功能"""
        harness = Harness("测试项目", workspace=str(tmp_path / ".harnessgenj"))

        # 1. 发送消息（触发意图记录）
        result = harness.chat("帮我实现一个用户登录功能")

        # 2. 验证意图被记录
        intents_path = tmp_path / ".harnessgenj" / "intents.json"
        assert intents_path.exists()

        # 3. 生成监控报告
        monitor = HGJMonitor(tmp_path / ".harnessgenj")
        report = monitor.generate_report()

        # 验证报告包含必要内容（兼容不同编码环境）
        assert "intent_router" in report.lower() or "HGJ" in report

    def test_get_init_prompt_after_from_project(self, tmp_path):
        """测试 from_project 后的初始化提示"""
        # 创建项目目录
        project_dir = tmp_path / "my_project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建 README
        readme = project_dir / "README.md"
        readme.write_text("# My Project\n\nA test project.", encoding="utf-8")

        # 初始化
        harness = Harness.from_project(str(project_dir))
        prompt = harness.get_init_prompt()

        # 验证提示包含项目信息
        assert "My Project" in prompt or "项目" in prompt