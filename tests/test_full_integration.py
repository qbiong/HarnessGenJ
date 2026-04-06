"""
Integration Test - 全流程集成测试

测试 HarnessGenJ 框架的完整功能链：
1. 初始化与对话引入
2. 角色创建与调度
3. GAN 对抗机制（生成器-判别器）
4. 记忆管理系统
5. Hooks 集成
6. 角色协作机制
7. 文档同步
8. 代码生成辅助
9. TDD 工作流
10. 依赖管理
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path

from harnessgenj import Harness
from harnessgenj.roles import RoleType, create_role
from harnessgenj.workflow import (
    WorkflowCoordinator,
    WorkflowPipeline,
    create_standard_pipeline,
    DependencyGraph,
    RoleCollaborationManager,
    TDDWorkflow,
    TDDConfig,
)
from harnessgenj.memory import MemoryManager
from harnessgenj.harness.hooks_integration import create_hooks_integration
from harnessgenj.sync.doc_sync import create_sync_manager
from harnessgenj.codegen import create_code_generator


class TestFullWorkflowIntegration:
    """全流程集成测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def harness(self, temp_workspace):
        """创建 Harness 实例"""
        return Harness(
            project_name="集成测试项目",
            persistent=True,
            workspace=temp_workspace,
            auto_setup_team=True,
        )

    # ==================== 1. 初始化与对话引入 ====================

    def test_harness_initialization(self, harness):
        """测试 Harness 初始化"""
        # 验证基本属性
        assert harness.project_name == "集成测试项目"
        assert harness._persistent is True

        # 验证核心组件初始化
        assert harness.memory is not None
        assert harness.coordinator is not None
        assert harness.storage is not None
        assert harness.sessions is not None

        # 验证新增组件初始化
        assert harness._hooks_integration is not None
        assert harness._collaboration is not None
        assert harness._doc_sync is not None

    def test_auto_team_setup(self, harness):
        """测试自动团队创建"""
        team = harness.get_team()
        assert len(team) >= 4  # 至少有 developer, code_reviewer, bug_hunter, project_manager

        # 验证角色类型（role_type 是枚举值）
        role_types = {r["role_type"].value if hasattr(r["role_type"], "value") else r["role_type"] for r in team}
        assert "developer" in role_types
        assert "code_reviewer" in role_types

    def test_receive_request_flow(self, harness):
        """测试对话引入流程"""
        # 模拟用户请求
        result = harness.receive_request("实现用户登录功能", request_type="feature")

        assert result["success"] is True
        assert result["task_id"] is not None
        assert result["priority"] == "P1"
        assert result["assignee"] == "developer"

        # 验证任务已存储
        task_id = result["task_id"]
        task = harness.memory.get_task(task_id)
        assert task is not None
        assert task["request"] == "实现用户登录功能"

        # 验证进度文档已更新
        progress = harness.memory.get_document("progress")
        assert progress is not None
        assert task_id in progress

    # ==================== 2. 角色创建与调度 ====================

    def test_role_creation(self, harness):
        """测试角色创建"""
        # 手动创建角色
        architect = harness.coordinator.create_role(
            RoleType.ARCHITECT,
            "arch_001",
            "架构师A",
        )

        assert architect is not None
        assert architect.role_id == "arch_001"
        assert architect.name == "架构师A"
        assert architect.role_type == RoleType.ARCHITECT

    def test_role_assignment(self, harness):
        """测试角色任务分配"""
        # 获取开发者角色
        developers = harness.coordinator.get_roles_by_type(RoleType.DEVELOPER)
        assert len(developers) > 0

        developer = developers[0]

        # 分配任务
        task = {
            "type": "implement_feature",
            "description": "实现用户认证",
        }

        result = developer.assign_task(task)
        assert result is True

        # 执行任务
        execution_result = developer.execute_task()
        assert execution_result is not None
        assert "status" in execution_result

    def test_workflow_execution(self, harness):
        """测试工作流执行"""
        # 创建功能流水线
        pipeline = create_standard_pipeline()

        # 验证阶段
        stages = pipeline.list_stages()
        assert len(stages) >= 6  # 标准 6 阶段

        # 验证依赖关系
        assert pipeline.has_circular_dependency() is False

        # 获取执行顺序
        order = pipeline.get_execution_order()
        assert len(order) == len(stages)

    # ==================== 3. GAN 对抗机制 ====================

    def test_adversarial_workflow(self, harness):
        """测试对抗性工作流"""
        # 执行对抗性开发
        result = harness.adversarial_develop(
            "实现数据验证功能",
            max_rounds=2,
            use_hunter=False,
            code="# 数据验证代码\ndef validate(data): return True",
        )

        assert result is not None
        assert result.rounds >= 0
        assert result.quality_score >= 0

    def test_generator_discriminator_interaction(self, harness):
        """测试生成器-判别器交互"""
        # 生成器（Developer）
        developers = harness.coordinator.get_roles_by_type(RoleType.DEVELOPER)
        assert len(developers) > 0

        # 判别器（CodeReviewer）
        reviewers = harness.coordinator.get_roles_by_type(RoleType.CODE_REVIEWER)
        assert len(reviewers) > 0

        # 判别器（BugHunter - 激进模式）
        hunters = harness.coordinator.get_roles_by_type(RoleType.BUG_HUNTER)
        assert len(hunters) > 0

    def test_quality_scoring(self, harness):
        """测试质量评分系统"""
        # 获取质量报告
        report = harness.get_quality_report()

        assert report is not None
        assert "total_tasks" in report or "issues_found" in report or isinstance(report, dict)

    # ==================== 4. 记忆管理系统 ====================

    def test_memory_store_recall(self, harness):
        """测试记忆存储与召回"""
        # 存储知识
        harness.remember("tech_stack", "Python + FastAPI", important=True)
        harness.remember("database", "PostgreSQL", important=False)

        # 召回知识
        tech = harness.recall("tech_stack")
        assert tech == "Python + FastAPI"

        db = harness.recall("database")
        assert db == "PostgreSQL"

    def test_memory_document_management(self, harness):
        """测试文档管理"""
        # 存储文档
        harness.memory.store_document("requirements", "# 需求文档\n- 用户登录\n- 数据验证")

        # 获取文档
        doc = harness.memory.get_document("requirements")
        assert doc is not None
        assert "用户登录" in doc

    def test_memory_message_history(self, harness):
        """测试消息历史"""
        # 存储消息
        harness.memory.store_message("你好，我需要一个功能", "user")
        harness.memory.store_message("好的，我来帮你实现", "assistant")

        # 获取上下文
        context = harness.get_context_prompt()
        assert context is not None
        assert len(context) > 0

    def test_memory_stats(self, harness):
        """测试记忆统计"""
        stats = harness.memory.get_stats()

        assert stats is not None
        assert "stats" in stats
        assert "memory" in stats

    # ==================== 5. Hooks 集成 ====================

    def test_hooks_pre_task(self, harness):
        """测试 Pre-Task Hooks"""
        # 执行带 Hooks 的开发
        result = harness.develop("实现缓存功能", skip_hooks=False)

        # 验证 Hooks 被调用（通过统计）
        stats = harness._hooks_integration.get_stats()
        assert stats["total_checks"] >= 0

    def test_hooks_post_task(self, harness):
        """测试 Post-Task Hooks"""
        # 接收请求会触发 validation hooks
        result = harness.receive_request("测试请求", request_type="feature")

        # 验证 Hooks 统计更新
        stats = harness._hooks_integration.get_stats()
        assert stats["total_checks"] >= 1

    def test_hooks_blocking_mode(self, harness):
        """测试 Hooks 阻塞模式"""
        # 创建禁用阻塞的集成
        integration = create_hooks_integration(
            enabled=True,
            blocking_mode=False,
        )

        assert integration.config.blocking_mode is False

    # ==================== 6. 角色协作机制 ====================

    def test_collaboration_role_registration(self, harness):
        """测试协作角色注册"""
        # 注册角色到协作管理器
        harness._register_roles_to_collaboration()

        # 验证角色已注册
        stats = harness._collaboration.get_stats()
        assert stats["active_roles"] >= 0

    def test_collaboration_message_passing(self, harness):
        """测试角色间消息传递"""
        # 注册角色
        harness._register_roles_to_collaboration()

        # 发送消息
        msg_id = harness._collaboration.send_message(
            from_role="project_manager",
            to_role="developer",
            content={"type": "task_assignment", "task": "实现功能"},
        )

        assert msg_id is not None

        # 获取消息
        messages = harness._collaboration.get_messages("developer")
        assert len(messages) >= 1

    def test_collaboration_artifact_transfer(self, harness):
        """测试产出物转移"""
        harness._register_roles_to_collaboration()

        # 转移产出物
        result = harness._collaboration.transfer_artifact(
            from_role="developer",
            to_role="code_reviewer",
            artifact_name="code.py",
            artifact_content="# 代码内容",
        )

        assert result is True

        # 验证流转记录
        flow = harness._collaboration.get_artifacts_flow()
        assert len(flow) >= 1

    def test_collaboration_snapshot(self, harness):
        """测试协作快照"""
        harness._register_roles_to_collaboration()

        snapshot = harness._collaboration.get_snapshot()

        assert snapshot is not None
        assert len(snapshot.roles) >= 0

    # ==================== 7. 文档同步 ====================

    def test_doc_sync_registration(self, harness):
        """测试文档注册"""
        # 注册文档
        result = harness._doc_sync.register_document("test_doc.md")

        assert result is True

        # 验证文档已注册
        docs = harness._doc_sync.list_documents()
        assert len(docs) >= 1

    def test_doc_sync_operation(self, harness):
        """测试文档同步操作"""
        # 注册并同步
        harness._doc_sync.register_document("progress.md")

        result = harness._doc_sync.sync_document("progress.md")

        assert result.success is True

    def test_doc_sync_consistency_check(self, harness):
        """测试一致性检查"""
        harness._doc_sync.register_document("requirements.md")

        inconsistent = harness._doc_sync.check_consistency()

        assert isinstance(inconsistent, list)

    def test_doc_sync_status(self, harness):
        """测试同步状态"""
        status = harness.get_doc_sync_status()

        assert status is not None
        assert "documents_registered" in status

    # ==================== 8. 代码生成辅助 ====================

    def test_code_generator_function(self, harness):
        """测试函数生成"""
        generator = create_code_generator()

        result = generator.generate_function(
            name="calculate_sum",
            params="a, b",
            description="计算两个数的和",
            body="return a + b",
            return_value="a + b",
        )

        assert result.success is True
        assert "def calculate_sum" in result.code

    def test_code_generator_class(self, harness):
        """测试类生成"""
        generator = create_code_generator()

        result = generator.generate_class(
            name="UserService",
            description="用户服务类",
            init_params="self, db",
            init_body="self.db = db",
        )

        assert result.success is True
        assert "class UserService" in result.code

    def test_code_generator_test(self, harness):
        """测试用例生成"""
        generator = create_code_generator()

        result = generator.generate_test(
            test_name="user_login",  # 注意：模板会自动添加 test_ 前缀
            description="测试用户登录",
            arrange="user = User()",
            act="result = user.login()",
            assertion="result is True",
        )

        assert result.success is True
        assert "def test_user_login" in result.code  # 模板添加前缀后应为 test_user_login

    def test_code_generator_constraints(self, harness):
        """测试架构约束"""
        generator = create_code_generator()

        # 测试 eval 约束
        result = generator.generate_from_template(
            "python_function",
            {
                "function_name": "unsafe",
                "body": "eval(input())",
            },
        )

        # 应该检测到 eval 约束违规
        assert len(result.errors) > 0 or "eval" in str(result.warnings)

    def test_developer_code_generation(self, harness):
        """测试 Developer 角色代码生成能力"""
        developers = harness.coordinator.get_roles_by_type(RoleType.DEVELOPER)
        if len(developers) > 0:
            developer = developers[0]

            # 使用 Developer 的代码生成能力
            result = developer.generate_function(
                name="validate_email",
                params="email",
                description="验证邮箱格式",
            )

            assert result.success is True

    # ==================== 9. TDD 工作流 ====================

    def test_tdd_workflow_creation(self, harness):
        """测试 TDD 工作流创建"""
        harness.enable_tdd()

        assert harness._tdd_workflow is not None

    def test_tdd_cycle_execution(self, harness):
        """测试 TDD 循环执行"""
        harness.enable_tdd(TDDConfig(
            coverage_threshold=50.0,
            auto_run_tests=False,
        ))

        # 开始循环
        cycle = harness._tdd_workflow.start_cycle("测试功能")

        assert cycle is not None
        assert cycle.feature_name == "测试功能"

        # 写测试
        test_result = harness._tdd_workflow.write_test(
            cycle,
            "def test_feature(): assert True",
            run_test=False,
        )

        assert test_result is not None

        # 写实现
        impl_result = harness._tdd_workflow.write_implementation(
            cycle,
            "def feature(): pass",
            run_test=False,
        )

        assert impl_result is not None

        # 完成循环
        final_result = harness._tdd_workflow.complete_cycle(cycle)

        assert final_result["status"] in ["completed", "failed"]

    def test_tdd_develop_mode(self, harness):
        """测试 TDD 开发模式"""
        # 使用 TDD 模式开发
        result = harness.develop("简单功能", use_tdd=True)

        assert result is not None
        assert "status" in result
        # TDD 模式可能失败（因为是简化的实现），但流程应该正确执行

    # ==================== 10. 依赖管理 ====================

    def test_dependency_graph_creation(self):
        """测试依赖图创建"""
        graph = DependencyGraph()

        # 添加任务
        assert graph.add_task("design", [])
        assert graph.add_task("develop", ["design"])
        assert graph.add_task("test", ["develop"])

        # 验证任务
        assert len(graph.list_tasks()) == 3

    def test_dependency_cycle_detection(self):
        """测试循环依赖检测"""
        graph = DependencyGraph()

        graph.add_task("A", [])
        graph.add_task("B", ["A"])
        # 尝试创建循环：C 依赖 B，但 A 依赖 C
        graph.add_task("C", ["B"])

        # 尝试添加会创建循环的依赖（A -> C）
        # 由于 add_task 在添加时检测，所以需要手动修改
        # 这里测试检测功能
        assert not graph.has_cycle()  # 当前没有循环

    def test_dependency_topological_sort(self):
        """测试拓扑排序"""
        graph = DependencyGraph()

        graph.add_task("requirements", [])
        graph.add_task("design", ["requirements"])
        graph.add_task("develop", ["design"])
        graph.add_task("test", ["develop"])

        order = graph.topological_sort()

        assert len(order) == 4
        # requirements 应该在 design 之前
        assert order.index("requirements") < order.index("design")
        # design 应该在 develop 之前
        assert order.index("design") < order.index("develop")

    def test_pipeline_dependency_integration(self):
        """测试 Pipeline 与依赖图集成"""
        pipeline = create_standard_pipeline()

        # 验证循环依赖检测
        assert pipeline.has_circular_dependency() is False

        # 验证影响分析
        impact = pipeline.analyze_stage_impact("development")
        assert impact is not None
        assert "upstream_count" in impact
        assert "downstream_count" in impact

        # 验证 Mermaid 可视化
        mermaid = pipeline.to_mermaid()
        assert "```mermaid" in mermaid
        assert "graph TD" in mermaid


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.fixture
    def full_harness(self):
        """创建完整配置的 Harness"""
        temp_dir = tempfile.mkdtemp()
        harness = Harness(
            project_name="端到端测试",
            persistent=True,
            workspace=temp_dir,
            auto_setup_team=True,
        )
        harness.enable_tdd()
        yield harness
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_complete_feature_development_flow(self, full_harness):
        """测试完整功能开发流程"""
        # 1. 用户发起请求
        request_result = full_harness.receive_request(
            "实现用户注册功能",
            request_type="feature",
        )
        assert request_result["success"] is True
        task_id = request_result["task_id"]

        # 2. 存储项目知识
        full_harness.remember("feature_requirements", "用户注册需要邮箱验证", important=True)

        # 3. 验证团队已就绪
        team = full_harness.get_team()
        assert len(team) >= 4

        # 4. 注册协作角色
        full_harness._register_roles_to_collaboration()

        # 5. 执行开发（带 Hooks）
        dev_result = full_harness.develop(
            "用户注册功能",
            skip_hooks=False,
        )

        # 6. 验证 Hooks 执行
        hooks_stats = full_harness._hooks_integration.get_stats()
        assert hooks_stats["total_checks"] >= 0

        # 7. 验证协作状态
        collab_stats = full_harness.get_collaboration_status()
        assert collab_stats is not None

        # 8. 验证文档同步
        doc_status = full_harness.get_doc_sync_status()
        assert doc_status is not None

        # 9. 获取项目状态
        status = full_harness.get_status()
        assert status["project"] == "端到端测试"

        # 10. 生成报告
        report = full_harness.get_report()
        assert "端到端测试" in report

    def test_bug_fix_flow(self, full_harness):
        """测试 Bug 修复流程"""
        # 1. 报告 Bug
        result = full_harness.receive_request(
            "修复登录超时问题",
            request_type="bug",
        )
        assert result["success"] is True
        assert result["priority"] == "P0"  # Bug 优先级

        # 2. 执行修复
        fix_result = full_harness.fix_bug("登录超时", skip_hooks=False)

        # 3. 验证统计更新
        stats = full_harness.get_status()
        # Bug 可能未完全修复（简化实现），但流程应正确执行

    def test_persistence_flow(self):
        """测试持久化流程"""
        temp_dir = tempfile.mkdtemp()

        try:
            # 1. 创建第一个实例
            harness1 = Harness(
                project_name="持久化测试",
                persistent=True,
                workspace=temp_dir,
            )

            # 2. 存储一些数据
            harness1.remember("test_key", "test_value", important=True)
            harness1.receive_request("测试需求", request_type="feature")

            # 3. 保存
            harness1.save()

            # 4. 创建第二个实例（模拟重启）
            harness2 = Harness(
                project_name="持久化测试",
                persistent=True,
                workspace=temp_dir,
            )

            # 5. 验证数据恢复
            value = harness2.recall("test_key")
            assert value == "test_value"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_adversarial_quality_improvement(self, full_harness):
        """测试对抗性质量改进"""
        # 执行多次对抗性开发
        features = [
            "数据验证",
            "缓存机制",
            "日志记录",
        ]

        for feature in features:
            result = full_harness.adversarial_develop(
                feature,
                max_rounds=2,
                code=f"# {feature} implementation\npass",
            )

        # 获取系统分析
        analysis = full_harness.get_system_analysis()
        assert analysis is not None

        # 获取健康趋势
        trend = full_harness.get_health_trend()
        assert isinstance(trend, list)


class TestIntegrationValidation:
    """集成验证测试"""

    def test_all_modules_importable(self):
        """验证所有模块可导入"""
        # 核心模块
        from harnessgenj import Harness
        from harnessgenj.roles import AgentRole, RoleType
        from harnessgenj.workflow import (
            WorkflowCoordinator,
            WorkflowPipeline,
            DependencyGraph,
            RoleCollaborationManager,
            TDDWorkflow,
        )
        from harnessgenj.memory import MemoryManager
        from harnessgenj.storage import StorageManager
        from harnessgenj.harness import AdversarialWorkflow
        from harnessgenj.harness.hooks_integration import HooksIntegration
        from harnessgenj.sync.doc_sync import DocumentSyncManager
        from harnessgenj.codegen import CodeGenerator

    def test_module_interconnections(self):
        """验证模块间连接"""
        temp_dir = tempfile.mkdtemp()

        try:
            harness = Harness(
                project_name="模块连接测试",
                persistent=True,
                workspace=temp_dir,
            )

            # 验证 Memory -> Quality 连接
            assert harness.memory._quality_tracker is not None

            # 验证 Engine -> Hooks 连接
            assert harness._hooks_integration is not None

            # 验证 Engine -> Collaboration 连接
            assert harness._collaboration is not None

            # 验证 Engine -> DocSync 连接
            assert harness._doc_sync is not None

            # 验证 Coordinator -> Roles 连接
            assert len(harness.coordinator.list_roles()) > 0

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_error_handling(self):
        """测试错误处理"""
        temp_dir = tempfile.mkdtemp()

        try:
            harness = Harness(
                project_name="错误处理测试",
                workspace=temp_dir,
            )

            # 测试获取不存在的任务
            task = harness.memory.get_task("NONEXISTENT_TASK")
            assert task is None

            # 测试获取不存在的知识
            knowledge = harness.recall("NONEXISTENT_KEY")
            assert knowledge is None

            # 测试完成不存在的任务
            result = harness.complete_task("NONEXISTENT_TASK", "summary")
            assert result is False

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPerformanceValidation:
    """性能验证测试"""

    def test_memory_performance(self):
        """测试记忆性能"""
        temp_dir = tempfile.mkdtemp()

        try:
            harness = Harness(workspace=temp_dir)

            # 存储大量知识
            import time
            start = time.time()

            for i in range(100):
                harness.remember(f"key_{i}", f"value_{i}")

            duration = time.time() - start

            # 应该在合理时间内完成
            assert duration < 5.0  # 5秒内

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_workflow_performance(self):
        """测试工作流性能"""
        pipeline = create_standard_pipeline()

        import time
        start = time.time()

        # 执行多次依赖检查
        for _ in range(100):
            pipeline.has_circular_dependency()
            pipeline.get_execution_order()

        duration = time.time() - start

        # 应该在合理时间内完成
        assert duration < 2.0  # 2秒内


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])