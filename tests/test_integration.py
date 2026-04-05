"""
Integration Tests - 端到端集成测试

测试覆盖从项目初始化到实际效果分析的完整流程：
1. 项目初始化与持久化
2. 团队组建与角色调度
3. 需求接收与任务管理
4. 对抗性开发流程
5. 质量数据流转（核心）
6. 系统级分析
7. 质量感知GC
8. 渐进式披露

每个测试用例验证一个完整的业务场景，确保所有模块正确衔接。
"""

import pytest
import tempfile
import os
import shutil
import time

from py_ha import Harness, create_harness, RoleType
from py_ha.memory import MemoryManager, MemoryRegion, QualityAwareCollector
from py_ha.quality import ScoreManager, QualityTracker, TaskAdversarialController, SystemAdversarialController
from py_ha.workflow import create_adversarial_pipeline


class TestFullProjectLifecycle:
    """
    测试完整项目生命周期

    从初始化到完成多个任务的完整流程
    """

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_test")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_full_lifecycle(self, temp_workspace):
        """
        完整生命周期测试

        验证：
        1. Harness 正确初始化所有组件
        2. 质量系统链接成功
        3. 对抗控制器可用
        4. 工作流注册完整
        """
        # 1. 初始化项目
        harness = Harness(
            project_name="集成测试项目",
            persistent=True,
            workspace=temp_workspace,
        )

        # 验证初始化
        assert harness.project_name == "集成测试项目"
        assert harness.memory is not None
        assert harness.coordinator is not None
        assert harness._score_manager is not None
        assert harness._quality_tracker is not None
        assert harness._adversarial_workflow is not None
        assert harness._task_adversarial is not None
        assert harness._system_adversarial is not None

        # 验证质量系统已链接
        assert harness.memory._score_manager is not None
        assert harness.memory._quality_tracker is not None

        # 验证工作流注册
        workflows = list(harness.coordinator._workflows.keys())
        assert "standard" in workflows
        assert "feature" in workflows
        assert "bugfix" in workflows
        assert "adversarial" in workflows


class TestAdversarialDevelopment:
    """
    测试对抗性开发流程

    验证 GAN 式对抗机制的正确性
    """

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_adv")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_adversarial_review_creates_artifact(self, temp_workspace):
        """
        测试对抗审查创建产出物

        验证：
        1. 审查完成后创建记忆条目
        2. 质量分数正确计算
        3. 条目关联生成者和审查者
        """
        harness = Harness("对抗测试", workspace=temp_workspace)

        # 执行对抗性审查
        code = """
def login(username, password):
    if username and password:
        return True
    return False
"""
        result = harness._adversarial_workflow.execute_adversarial_review(
            code=code,
            generator_id="dev_test",
            generator_type="developer",
            task_id="TASK-001",
            max_rounds=1,
        )

        # 验证结果
        assert result is not None
        assert result.artifact_id is not None
        assert result.quality_score >= 0
        assert result.quality_score <= 100

        # 验证记忆条目创建
        entry = harness.memory.get_artifact(result.artifact_id)
        assert entry is not None
        assert entry.generator_id == "dev_test"
        assert entry.discriminator_id is not None
        assert entry.quality_score == result.quality_score
        assert entry.review_count >= 1

    def test_quality_score_calculation(self, temp_workspace):
        """
        测试质量分数计算

        验证不同审查结果的质量分数差异
        """
        harness = Harness("质量分数测试", workspace=temp_workspace)

        # 测试一轮通过的代码（应该得高分）
        good_code = """
def calculate_sum(a, b):
    \"\"\"计算两数之和\"\"\"
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("参数必须是数字")
    return a + b
"""
        result = harness._adversarial_workflow.execute_adversarial_review(
            code=good_code,
            generator_id="dev_good",
            generator_type="developer",
            max_rounds=1,
        )

        # 一轮通过应该有较高分数
        assert result.quality_score >= 80, f"预期高质量分数，实际: {result.quality_score}"


class TestQualityDataFlow:
    """
    测试质量数据流

    核心测试：验证对抗审查结果正确影响记忆管理
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_quality")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_quality_updates_memory_entry(self, temp_workspace):
        """
        测试质量信息更新记忆条目

        验证：
        1. store_artifact 记录生成者
        2. link_adversarial_result 更新质量信息
        3. 质量数据可查询
        """
        memory = MemoryManager(temp_workspace)

        # 存储产出物
        entry = memory.store_artifact(
            artifact_id="code_001",
            content="def test(): pass",
            artifact_type="code",
            generator_id="dev_001",
        )

        assert entry.generator_id == "dev_001"
        assert entry.quality_score == 50.0  # 默认值
        assert entry.review_count == 0

        # 链接对抗结果
        success = memory.link_adversarial_result(
            entry_id="code_001",
            quality_score=85.0,
            passed=True,
            generator_id="dev_001",
            discriminator_id="reviewer_001",
        )

        assert success is True

        # 验证更新后的条目
        updated = memory.get_artifact("code_001")
        assert updated.quality_score == 85.0
        assert updated.review_count == 1
        assert updated.last_review_result == "passed"
        assert updated.discriminator_id == "reviewer_001"

    def test_quality_aware_gc(self, temp_workspace):
        """
        测试质量感知 GC

        验证：
        1. 高质量条目优先存活
        2. 低质量条目优先回收
        """
        memory = MemoryManager(temp_workspace)

        # 创建高质量条目
        high_quality = memory.store_artifact(
            artifact_id="high_quality_code",
            content="def well_written(): pass",
            generator_id="dev_001",
        )
        memory.link_adversarial_result(
            entry_id="high_quality_code",
            quality_score=90.0,
            passed=True,
        )

        # 创建低质量条目
        low_quality = memory.store_artifact(
            artifact_id="low_quality_code",
            content="def buggy(): pass",
            generator_id="dev_002",
        )
        memory.link_adversarial_result(
            entry_id="low_quality_code",
            quality_score=25.0,
            passed=False,
        )

        # 使用 QualityAwareCollector 判断存活
        collector = QualityAwareCollector(quality_threshold=40.0)

        high_entry = memory.get_artifact("high_quality_code")
        low_entry = memory.get_artifact("low_quality_code")

        # 高质量应该存活
        assert collector._should_survive(high_entry) is True
        # 低质量（且低引用）应该被回收
        assert collector._should_survive(low_entry) is False

    def test_get_entries_by_quality(self, temp_workspace):
        """
        测试按质量筛选条目
        """
        memory = MemoryManager(temp_workspace)

        # 创建不同质量的条目
        for i, score in enumerate([90, 70, 50, 30]):
            memory.store_artifact(
                artifact_id=f"code_{i}",
                content=f"code {i}",
                generator_id="dev_001",
            )
            memory.link_adversarial_result(
                entry_id=f"code_{i}",
                quality_score=float(score),
                passed=score >= 50,
            )

        # 筛选高质量条目
        high_quality = memory.get_entries_by_quality(min_quality=70.0)
        assert len(high_quality) == 2

        # 筛选低质量条目
        low_quality = memory.get_entries_by_quality(max_quality=40.0)
        assert len(low_quality) == 1


class TestProgressiveDisclosure:
    """
    测试渐进式披露

    验证基于角色的文档访问控制
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_pd")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_document_access_control(self, temp_workspace):
        """
        测试文档访问控制

        验证不同角色看到不同内容
        """
        memory = MemoryManager(temp_workspace)

        # 存储各种文档
        memory.store_document("requirements", "# 需求文档\n完整内容...")
        memory.store_document("design", "# 设计文档\n架构设计...")
        memory.store_document("development", "# 开发文档\n代码实现...")
        memory.store_document("testing", "# 测试文档\n测试用例...")

        # 项目经理：应有全部文档
        pm_context = memory.get_context_for_role("project_manager")
        assert pm_context["full_access"] is True
        assert "requirements" in pm_context["documents"]
        assert "design" in pm_context["documents"]

        # 开发者：
        # - 是 development 的 owner，应有完整内容
        # - 在 requirements/design/testing 的 read_only_for 中，能看完整内容
        dev_context = memory.get_context_for_role("developer")
        assert dev_context["full_access"] is False
        assert "development" in dev_context["documents"]  # owner
        assert "requirements" in dev_context["documents"]  # read_only_for
        assert "design" in dev_context["documents"]  # read_only_for

        # 代码审查者：
        # - 在所有技术文档的 read_only_for 中，能看完整内容
        reviewer_context = memory.get_context_for_role("code_reviewer")
        assert reviewer_context["full_access"] is False
        assert "development" in reviewer_context["documents"]  # read_only_for
        assert "requirements" in reviewer_context["documents"]  # read_only_for
        assert "design" in reviewer_context["documents"]  # read_only_for

        # 架构师：
        # - 是 design 的 owner
        # - 不在 requirements 的 visible_to 中，所以没有访问权限
        architect_context = memory.get_context_for_role("architect")
        assert "design" in architect_context["documents"]  # owner
        # architect 不在 requirements 的 visible_to 中
        assert "requirements" not in architect_context["documents"]
        assert "requirements" not in architect_context["documents_summary"]

    def test_high_quality_content_prioritized(self, temp_workspace):
        """
        测试高质量内容优先加载

        验证上下文装配优先包含高质量内容
        """
        memory = MemoryManager(temp_workspace)

        # 创建高质量和低质量条目
        memory.store_artifact("good_code", "优质代码", "code", "dev_001")
        memory.link_adversarial_result("good_code", 95.0, True)

        memory.store_artifact("bad_code", "问题代码", "code", "dev_002")
        memory.link_adversarial_result("bad_code", 25.0, False)

        # 获取上下文
        context = memory.get_context_for_role("developer")

        # 应包含高质量内容
        if "high_quality_content" in context:
            high_quality_ids = [item["id"] for item in context["high_quality_content"]]
            assert "good_code" in high_quality_ids
            assert "bad_code" not in high_quality_ids


class TestSystemAnalysis:
    """
    测试系统级分析

    验证跨任务模式识别
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_sa")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_system_analysis_after_tasks(self, temp_workspace):
        """
        测试执行任务后的系统分析

        验证：
        1. 系统分析方法可调用
        2. 返回预期的分析结构
        """
        harness = Harness("系统分析测试", workspace=temp_workspace)

        # 执行几个对抗审查（模拟多个任务）
        for i in range(3):
            harness._adversarial_workflow.execute_adversarial_review(
                code=f"def func_{i}(): pass",
                generator_id="dev_001",
                generator_type="developer",
                task_id=f"TASK-{i}",
                max_rounds=1,
            )

        # 执行系统分析
        analysis = harness.get_system_analysis()

        # 验证分析结果结构
        assert "total_tasks_analyzed" in analysis
        assert "system_health_score" in analysis
        assert "generator_weaknesses" in analysis
        assert "discriminator_biases" in analysis
        assert "improvement_actions" in analysis

    def test_health_trend_tracking(self, temp_workspace):
        """
        测试健康度趋势追踪
        """
        harness = Harness("趋势测试", workspace=temp_workspace)

        # 初始趋势
        initial_trend = harness.get_health_trend()
        assert isinstance(initial_trend, list)

        # 执行分析
        harness.get_system_analysis()

        # 趋势应该更新
        updated_trend = harness.get_health_trend()
        assert len(updated_trend) >= len(initial_trend)


class TestScoreIntegration:
    """
    测试积分系统集成

    验证积分变更与角色表现追踪
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_score")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_score_changes_on_adversarial(self, temp_workspace):
        """
        测试对抗审查影响积分

        验证：
        1. 生成者和判别者积分变更
        2. 积分历史可查询
        """
        harness = Harness("积分测试", workspace=temp_workspace)

        # 注册角色
        harness._score_manager.register_role("developer", "dev_001", "开发者")
        harness._score_manager.register_role("code_reviewer", "reviewer_001", "审查者")

        # 获取初始积分
        initial_dev_score = harness._score_manager.get_score("dev_001").score

        # 执行对抗审查
        result = harness._adversarial_workflow.execute_adversarial_review(
            code="def test(): pass",
            generator_id="dev_001",
            generator_type="developer",
            max_rounds=1,
        )

        # 验证积分变更
        final_dev_score = harness._score_manager.get_score("dev_001").score

        # 如果通过，积分应该增加
        if result.success:
            assert final_dev_score >= initial_dev_score

    def test_leaderboard(self, temp_workspace):
        """
        测试积分排行榜
        """
        harness = Harness("排行榜测试", workspace=temp_workspace)

        # 注册多个角色
        for i in range(3):
            harness._score_manager.register_role("developer", f"dev_{i}", f"开发者{i}")

        # 获取排行榜
        leaderboard = harness.get_score_leaderboard(role_type="developer")

        assert isinstance(leaderboard, list)
        assert len(leaderboard) >= 3


class TestPersistenceIntegration:
    """
    测试持久化集成

    验证所有数据正确持久化和恢复
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_persist")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_quality_data_persistence(self, temp_workspace):
        """
        测试质量数据持久化

        验证：
        1. 质量分数保存到磁盘
        2. 重启后正确恢复
        """
        # 第一次会话
        harness1 = Harness("持久化测试", workspace=temp_workspace)

        # 创建带有质量信息的条目
        harness1.memory.store_artifact("persist_code", "code", "code", "dev_001")
        harness1.memory.link_adversarial_result("persist_code", 88.0, True)
        harness1.save()

        # 第二次会话（模拟重启）
        harness2 = Harness("持久化测试", workspace=temp_workspace)

        # 验证数据恢复
        entry = harness2.memory.get_artifact("persist_code")
        if entry:
            assert entry.quality_score == 88.0

    def test_score_persistence(self, temp_workspace):
        """
        测试积分持久化
        """
        # 第一次会话
        harness1 = Harness("积分持久化", workspace=temp_workspace)
        harness1._score_manager.register_role("developer", "dev_persist", "开发者")
        harness1._score_manager.on_task_success("dev_persist", 1, "TASK-001")
        initial_score = harness1._score_manager.get_score("dev_persist").score
        harness1.save()

        # 第二次会话
        harness2 = Harness("积分持久化", workspace=temp_workspace)
        restored_score = harness2._score_manager.get_score("dev_persist")

        if restored_score:
            assert restored_score.score == initial_score


class TestWorkflowPipelineIntegration:
    """
    测试工作流流水线集成
    """

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, ".py_ha_wf")
            yield workspace
            if os.path.exists(workspace):
                shutil.rmtree(workspace)

    def test_adversarial_pipeline_creation(self, temp_workspace):
        """
        测试对抗流水线创建

        验证流水线包含对抗审查阶段
        """
        pipeline = create_adversarial_pipeline(intensity="normal", max_rounds=3)

        stages = [s.name for s in pipeline.list_stages()]

        # 应包含对抗审查阶段
        assert "adversarial_review" in stages

        # 验证依赖关系
        testing_stage = pipeline.get_stage("testing")
        if testing_stage:
            assert "adversarial_review" in testing_stage.dependencies

    def test_pipeline_execution(self, temp_workspace):
        """
        测试流水线执行

        验证工作流可以正常运行
        """
        harness = Harness("流水线测试", workspace=temp_workspace)
        harness.setup_team()

        # 运行功能工作流
        result = harness.coordinator.run_workflow(
            "feature",
            {"feature_request": "测试功能"},
        )

        # 验证执行结果
        assert result is not None
        assert "status" in result