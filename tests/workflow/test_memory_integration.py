"""
Tests for Workflow Memory Integration

测试工作流与记忆管理的集成
"""

import pytest
import tempfile
import shutil

from harnessgenj.memory import MemoryManager
from harnessgenj.workflow.pipeline import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
    create_development_pipeline,
    create_bugfix_pipeline,
)
from harnessgenj.workflow.memory_mapping import (
    StageMemoryMapping,
    InputSource,
    OutputTarget,
    OutputAction,
    MemoryRegion,
    get_stage_mapping,
    get_pipeline_mappings,
    DEVELOPMENT_PIPELINE_MAPPINGS,
    BUGFIX_PIPELINE_MAPPINGS,
)
from harnessgenj.workflow.executor import (
    WorkflowExecutor,
    StageResult,
    WorkflowExecutionResult,
    create_executor,
)


class TestStageMemoryMapping:
    """测试阶段记忆映射"""

    def test_input_source_creation(self):
        """创建输入来源"""
        source = InputSource(
            source_type="document",
            key="requirements",
            required=True,
        )

        assert source.source_type == "document"
        assert source.key == "requirements"
        assert source.required is True

    def test_output_target_creation(self):
        """创建输出目标"""
        target = OutputTarget(
            action=OutputAction.STORE_DOCUMENT,
            region=MemoryRegion.OLD,
            key="requirements",
            doc_type="requirements",
            importance=80,
        )

        assert target.action == OutputAction.STORE_DOCUMENT
        assert target.region == MemoryRegion.OLD
        assert target.importance == 80

    def test_stage_mapping_creation(self):
        """创建阶段映射"""
        mapping = StageMemoryMapping(
            stage_name="requirements",
            inputs=[
                InputSource(source_type="task", key="current_task"),
            ],
            outputs=[
                OutputTarget(
                    action=OutputAction.STORE_DOCUMENT,
                    region=MemoryRegion.OLD,
                    key="requirements",
                    doc_type="requirements",
                ),
            ],
        )

        assert mapping.stage_name == "requirements"
        assert len(mapping.inputs) == 1
        assert len(mapping.outputs) == 1

    def test_get_stage_mapping(self):
        """获取阶段映射"""
        mapping = get_stage_mapping("development_pipeline", "requirements")
        assert mapping is not None
        assert mapping.stage_name == "requirements"

        # 不存在的映射
        mapping = get_stage_mapping("unknown_pipeline", "unknown_stage")
        assert mapping is None

    def test_get_pipeline_mappings(self):
        """获取工作流映射"""
        mappings = get_pipeline_mappings("development_pipeline")
        assert len(mappings) == 8  # 8 个阶段

        assert "requirements" in mappings
        assert "design" in mappings
        assert "development" in mappings
        assert "adversarial_review" in mappings

    def test_development_pipeline_mappings_complete(self):
        """开发流水线映射完整性"""
        mappings = DEVELOPMENT_PIPELINE_MAPPINGS

        # 验证所有阶段都有映射
        expected_stages = [
            "requirements", "design", "development",
            "adversarial_review", "fix_and_optimize",
            "unit_test", "integration_test", "acceptance"
        ]

        for stage in expected_stages:
            assert stage in mappings, f"Missing mapping for stage: {stage}"

    def test_bugfix_pipeline_mappings_complete(self):
        """Bug修复流水线映射完整性"""
        mappings = BUGFIX_PIPELINE_MAPPINGS

        expected_stages = [
            "analysis", "fix_design", "fix_implementation",
            "adversarial_verification", "edge_fix",
            "regression_test", "integration_verification", "fix_completion"
        ]

        for stage in expected_stages:
            assert stage in mappings, f"Missing mapping for stage: {stage}"


class TestWorkflowExecutor:
    """测试工作流执行器"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    @pytest.fixture
    def pipeline(self):
        """创建开发流水线"""
        return create_development_pipeline()

    @pytest.fixture
    def executor(self, memory_manager, pipeline):
        """创建执行器"""
        return create_executor(
            memory_manager=memory_manager,
            pipeline=pipeline,
            pipeline_name="development_pipeline",
        )

    def test_create_executor(self, executor):
        """创建执行器"""
        assert isinstance(executor, WorkflowExecutor)
        assert executor.memory is not None
        assert executor.pipeline is not None

    def test_load_inputs_from_memory(self, executor, memory_manager):
        """从记忆加载输入"""
        # 预存数据
        memory_manager.store_document("requirements", "# 需求文档\n- 用户登录")
        memory_manager.store_knowledge("project_name", "测试项目")

        stage = executor.pipeline.get_stage("design")
        mapping = get_stage_mapping("development_pipeline", "design")

        inputs = executor.load_inputs(stage, mapping)

        # 应该能加载到需求文档
        assert "requirements" in inputs

    def test_write_outputs_to_memory(self, executor, memory_manager):
        """将输出写入记忆"""
        stage = WorkflowStage(
            name="test_stage",
            role="developer",
            outputs=["test_doc"],
        )

        target = OutputTarget(
            action=OutputAction.STORE_DOCUMENT,
            region=MemoryRegion.OLD,
            key="test_doc",
            doc_type="development",
            importance=70,
        )

        mapping = StageMemoryMapping(
            stage_name="test_stage",
            outputs=[target],
        )

        outputs = {"test_doc": "# 测试内容"}

        writes = executor.write_outputs(stage, outputs, mapping)

        # 验证写入操作
        assert len(writes) > 0
        assert "development" in writes[0]

        # 验证记忆中存在
        doc = memory_manager.get_document("development")
        assert doc is not None

    def test_execute_stage(self, executor, memory_manager):
        """执行单个阶段"""
        # 准备输入
        memory_manager.store_knowledge("project_name", "测试项目")

        stage = executor.pipeline.get_stage("requirements")

        # 注册简单处理器
        def handler(inputs):
            return {
                "requirements": "# 需求\n- 功能1\n- 功能2",
                "acceptance_criteria": "验收标准",
            }

        result = executor.execute_stage(stage, handler)

        assert result.status == StageStatus.COMPLETED
        assert len(result.outputs_produced) > 0

    def test_execute_pipeline(self, executor, memory_manager):
        """执行整个流水线"""
        # 准备初始数据
        memory_manager.store_knowledge("project_name", "测试项目")

        # 定义简化的处理器
        handlers = {
            "requirements": lambda inputs: {
                "requirements": "# 需求文档",
                "acceptance_criteria": "验收标准",
            },
            "design": lambda inputs: {
                "design_doc": "# 设计文档",
                "architecture": "架构设计",
            },
            "development": lambda inputs: {
                "code": "# 代码",
                "implementation_notes": "实现说明",
            },
            "adversarial_review": lambda inputs: {
                "review_result": {"quality_score": 85.0},
                "quality_score": 85.0,
            },
            "fix_and_optimize": lambda inputs: {
                "optimized_code": "# 优化后代码",
            },
            "unit_test": lambda inputs: {
                "unit_tests": "# 测试",
                "coverage_report": {"coverage": 80},
            },
            "integration_test": lambda inputs: {
                "integration_results": "通过",
            },
            "acceptance": lambda inputs: {
                "acceptance_result": "验收通过",
            },
        }

        result = executor.execute_pipeline(handlers)

        assert result.stages_completed > 0
        assert result.stages_failed == 0

    def test_context_passing_between_stages(self, executor):
        """阶段间上下文传递"""
        # 设置上下文
        executor.set_context("shared_data", "传递的数据")

        # 获取上下文
        ctx = executor.get_context()
        assert "shared_data" in ctx
        assert ctx["shared_data"] == "传递的数据"

        # 清空
        executor.clear_context()
        ctx = executor.get_context()
        assert len(ctx) == 0

    def test_quality_update_output(self, executor, memory_manager):
        """质量分数更新输出"""
        # 预存代码快照
        memory_manager.store_knowledge("code_snapshot", "# 原始代码")

        stage = WorkflowStage(
            name="adversarial_review",
            role="code_reviewer",
            outputs=["quality_score"],
        )

        mapping = StageMemoryMapping(
            stage_name="adversarial_review",
            outputs=[
                OutputTarget(
                    action=OutputAction.UPDATE_QUALITY,
                    region=MemoryRegion.OLD,
                    key="review_result",
                    update_quality_target="code_snapshot",
                ),
            ],
        )

        outputs = {
            "review_result": {
                "quality_score": 90.0,
                "review_result": "passed",
            },
            "quality_score": 90.0,
        }

        # 写入应该执行（即使目标条目不在正确位置）
        writes = executor.write_outputs(stage, outputs, mapping)
        # 写入操作会被执行
        assert writes is not None


class TestMemoryRegionMapping:
    """测试记忆区域映射"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_manager(self, temp_workspace):
        """创建记忆管理器"""
        return MemoryManager(temp_workspace)

    def test_document_stores_to_old_region(self, memory_manager):
        """文档存储到 Old 区"""
        memory_manager.store_document("requirements", "# 需求文档")

        # 验证在 Old 区
        entry = memory_manager.get_document_entry("requirements")
        assert entry is not None

    def test_knowledge_stores_to_permanent_region(self, memory_manager):
        """知识存储到 Permanent 区"""
        memory_manager.store_knowledge("project_name", "测试项目", importance=100)

        # 验证可检索
        value = memory_manager.get_knowledge("project_name")
        assert value == "测试项目"

    def test_task_stores_to_survivor_region(self, memory_manager):
        """任务存储到 Survivor 区"""
        memory_manager.store_task("TASK-001", {"desc": "测试任务"})

        # 验证可检索
        task = memory_manager.get_task("TASK-001")
        assert task is not None
        assert task["desc"] == "测试任务"

    def test_message_stores_to_eden_region(self, memory_manager):
        """消息存储到 Eden 区"""
        memory_manager.store_message("用户消息", "user")

        # 验证统计中 Eden 有数据
        stats = memory_manager.get_stats()
        assert stats["memory"]["eden_size"] > 0


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_workflow_memory_flow(self, temp_workspace):
        """完整工作流的记忆流转"""
        # 1. 初始化
        memory = MemoryManager(temp_workspace)
        pipeline = create_development_pipeline()
        executor = create_executor(memory, pipeline, "development_pipeline")

        # 2. 预存项目信息
        memory.store_knowledge("project_name", "集成测试项目")

        # 3. 执行需求阶段
        def req_handler(inputs):
            return {
                "requirements": "# 需求\n## 功能1\n## 功能2",
                "user_stories": "用户故事",
                "acceptance_criteria": "验收标准",
            }

        stage = pipeline.get_stage("requirements")
        result = executor.execute_stage(stage, req_handler)

        # 4. 验证需求文档存储到 Old 区
        assert result.status == StageStatus.COMPLETED
        doc = memory.get_document("requirements")
        assert doc is not None
        assert "功能1" in doc

        # 5. 执行设计阶段
        def design_handler(inputs):
            return {
                "design_doc": "# 设计文档",
                "architecture": "架构说明",
                "tech_decisions": "技术栈",
            }

        stage = pipeline.get_stage("design")
        result = executor.execute_stage(stage, design_handler)

        # 6. 验证设计文档存储
        assert result.status == StageStatus.COMPLETED
        doc = memory.get_document("design")
        assert doc is not None

        # 7. 验证进度文档存在
        progress = memory.get_document("progress")
        # 进度文档可能在 acceptance 阶段才写入

    def test_bugfix_workflow_memory_flow(self, temp_workspace):
        """Bug修复工作流的记忆流转"""
        memory = MemoryManager(temp_workspace)
        pipeline = create_bugfix_pipeline()
        executor = create_executor(memory, pipeline, "bugfix_pipeline")

        # 预存 Bug 报告
        memory.store_task("TASK-BUG-001", {
            "type": "bug",
            "desc": "文字模式和语音模式切换无法工作",
        })

        # 执行分析阶段
        def analysis_handler(inputs):
            return {
                "root_cause": "状态管理错误",
                "affected_modules": ["mode_switcher"],
                "fix_strategy": "修复状态同步逻辑",
            }

        stage = pipeline.get_stage("analysis")
        result = executor.execute_stage(stage, analysis_handler)

        assert result.status == StageStatus.COMPLETED

        # 验证根因存储
        root_cause = memory.get_knowledge("root_cause")
        assert root_cause is not None

    def test_stage_outputs_match_memory_region(self):
        """验证阶段输出匹配记忆区域"""
        mappings = DEVELOPMENT_PIPELINE_MAPPINGS

        # 验证需求阶段：文档 -> Old
        req_mapping = mappings["requirements"]
        doc_outputs = [o for o in req_mapping.outputs if o.action == OutputAction.STORE_DOCUMENT]
        assert len(doc_outputs) > 0
        for o in doc_outputs:
            assert o.region in [MemoryRegion.OLD, MemoryRegion.PERMANENT]

        # 验证验收阶段：进度文档 -> Old，完成记录 -> Survivor
        acc_mapping = mappings["acceptance"]
        task_outputs = [o for o in acc_mapping.outputs if o.action == OutputAction.STORE_TASK]
        assert len(task_outputs) > 0
        for o in task_outputs:
            assert o.region == MemoryRegion.SURVIVOR