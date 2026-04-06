"""
Workflow Executor - 工作流执行器

负责执行工作流阶段并管理记忆读写。

核心功能：
1. 根据映射定义从 MemoryManager 读取输入
2. 执行阶段处理逻辑
3. 根据映射定义将输出写入 MemoryManager
4. 处理质量分数更新

使用现有 MemoryManager API，不修改其实现。
"""

from typing import Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import time
import json

from harnessgenj.memory import MemoryManager
from harnessgenj.workflow.pipeline import (
    WorkflowPipeline,
    WorkflowStage,
    StageStatus,
)
from harnessgenj.workflow.memory_mapping import (
    StageMemoryMapping,
    InputSource,
    OutputTarget,
    OutputAction,
    MemoryRegion,
    get_stage_mapping,
    get_pipeline_mappings,
)


class StageResult(BaseModel):
    """阶段执行结果"""

    stage_name: str
    status: StageStatus
    inputs_loaded: dict[str, Any] = Field(default_factory=dict)
    outputs_produced: dict[str, Any] = Field(default_factory=dict)
    memory_writes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration: float = 0.0


class WorkflowExecutionResult(BaseModel):
    """工作流执行结果"""

    pipeline_name: str
    stages_completed: int = 0
    stages_failed: int = 0
    stage_results: list[StageResult] = Field(default_factory=list)
    total_duration: float = 0.0
    final_artifacts: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutor:
    """
    工作流执行器 - 执行阶段并管理记忆

    工作流程：
    1. 获取待执行阶段
    2. 从 MemoryManager 读取输入（根据映射定义）
    3. 执行阶段处理器
    4. 将输出写入 MemoryManager（根据映射定义）
    5. 更新质量分数（如果是对抗审查阶段）
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        pipeline: WorkflowPipeline,
        pipeline_name: str = "",
    ) -> None:
        """
        初始化执行器

        Args:
            memory_manager: 记忆管理器实例
            pipeline: 工作流流水线
            pipeline_name: 工作流名称（用于获取映射）
        """
        self.memory = memory_manager
        self.pipeline = pipeline
        self.pipeline_name = pipeline_name or pipeline.name

        # 阶段处理器注册表
        self._stage_handlers: dict[str, Callable] = {}

        # 执行上下文（阶段间传递的临时数据）
        self._context: dict[str, Any] = {}

    def register_handler(self, stage_name: str, handler: Callable) -> None:
        """
        注册阶段处理器

        Args:
            stage_name: 阶段名称
            handler: 处理函数，签名为 (inputs: dict) -> dict
        """
        self._stage_handlers[stage_name] = handler

    def load_inputs(
        self,
        stage: WorkflowStage,
        mapping: StageMemoryMapping | None,
    ) -> dict[str, Any]:
        """
        从 MemoryManager 加载输入

        Args:
            stage: 工作流阶段
            mapping: 记忆映射

        Returns:
            加载的输入数据
        """
        inputs = {}

        # 首先从阶段定义的 inputs 加载
        for input_name in stage.inputs:
            # 尝试从上下文获取
            if input_name in self._context:
                inputs[input_name] = self._context[input_name]
                continue

            # 尝试从 Memory 获取
            value = self._load_from_memory(input_name)
            if value is not None:
                inputs[input_name] = value

        # 根据映射定义加载额外输入
        if mapping:
            for input_source in mapping.inputs:
                if input_source.key in inputs:
                    continue  # 已加载

                value = self._load_input_from_source(input_source)
                if value is None and input_source.required:
                    # 必需输入缺失，尝试使用默认值
                    value = input_source.default

                if value is not None:
                    inputs[input_source.key] = value

        return inputs

    def _load_input_from_source(self, source: InputSource) -> Any:
        """根据来源类型加载输入"""
        if source.source_type == "document":
            return self.memory.get_document(source.key)
        elif source.source_type == "knowledge":
            return self.memory.get_knowledge(source.key)
        elif source.source_type == "task":
            if source.key == "current_task":
                return self.memory.get_current_task()
            return self.memory.get_task(source.key)
        elif source.source_type == "message":
            # 从 Eden 区获取最近消息
            # 使用 MemoryManager 的公开 API
            stats = self.memory.get_stats()
            eden_size = stats.get("memory", {}).get("eden_size", 0)
            return {"eden_size": eden_size}  # 简化返回
        return None

    def _load_from_memory(self, key: str) -> Any:
        """通用记忆加载"""
        # 尝试作为文档加载
        doc = self.memory.get_document(key)
        if doc:
            return doc

        # 尝试作为知识加载
        knowledge = self.memory.get_knowledge(key)
        if knowledge:
            return knowledge

        # 尝试作为任务加载
        task = self.memory.get_task(key)
        if task:
            return task

        return None

    def write_outputs(
        self,
        stage: WorkflowStage,
        outputs: dict[str, Any],
        mapping: StageMemoryMapping | None,
    ) -> list[str]:
        """
        将输出写入 MemoryManager

        Args:
            stage: 工作流阶段
            outputs: 阶段产出的数据
            mapping: 记忆映射

        Returns:
            写入操作的描述列表
        """
        writes = []

        # 根据映射定义写入
        if mapping:
            for output_target in mapping.outputs:
                # 支持从 source_key 或 key 获取值
                source_key = output_target.source_key or output_target.key
                if source_key not in outputs:
                    continue

                value = outputs[source_key]
                if value is None:
                    continue

                write_desc = self._write_to_memory(output_target, value, stage.role)
                if write_desc:
                    writes.append(write_desc)

        # 同时更新上下文，供后续阶段使用
        for key, value in outputs.items():
            if value is not None:
                self._context[key] = value

        return writes

    def _write_to_memory(
        self,
        target: OutputTarget,
        value: Any,
        role: str,
    ) -> str | None:
        """根据目标定义写入记忆"""
        action = target.action
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

        try:
            if action == OutputAction.STORE_DOCUMENT:
                # 存储文档到 Old 区
                doc_type = target.doc_type or target.key
                self.memory.store_document(
                    doc_type=doc_type,
                    content=content,
                    generator_id=target.generator_role or role,
                    importance=target.importance,
                )
                return f"document:{doc_type} -> Old区"

            elif action == OutputAction.STORE_KNOWLEDGE:
                # 存储知识（根据区域决定存储位置）
                if target.region == MemoryRegion.PERMANENT:
                    self.memory.store_knowledge(
                        key=target.key,
                        content=content,
                        importance=target.importance,
                    )
                    return f"knowledge:{target.key} -> Permanent区"
                else:
                    # 其他区域也用 store_knowledge（会自动进入 Permanent）
                    self.memory.store_knowledge(
                        key=target.key,
                        content=content,
                        importance=target.importance,
                    )
                    return f"knowledge:{target.key} -> 记忆系统"

            elif action == OutputAction.STORE_TASK:
                # 存储任务到 Survivor 区
                task_id = f"TASK-{int(time.time() % 1000000)}"
                if isinstance(value, dict):
                    self.memory.store_task(
                        task_id=task_id,
                        task_info=value,
                        generator_id=target.generator_role or role,
                    )
                else:
                    self.memory.store_task(
                        task_id=task_id,
                        task_info={"data": value},
                        generator_id=target.generator_role or role,
                    )
                return f"task:{task_id} -> Survivor区"

            elif action == OutputAction.UPDATE_QUALITY:
                # 更新质量分数
                update_target = target.update_quality_target
                if update_target and isinstance(value, dict):
                    quality_score = value.get("quality_score")
                    review_result = value.get("review_result")

                    if quality_score is not None:
                        # 使用 MemoryManager 的质量更新能力
                        # 注意：需要通过获取条目并更新的方式
                        entry = self.memory.get_document_entry(update_target)
                        if entry:
                            entry.update_quality(
                                quality_score=quality_score,
                                review_result=review_result,
                                generator_id=value.get("generator_id"),
                                discriminator_id=value.get("discriminator_id"),
                            )
                            # 重新存储以更新
                            self.memory.store_document(
                                doc_type=update_target,
                                content=entry.content,
                                generator_id=entry.generator_id,
                                importance=entry.importance,
                            )
                            return f"quality_update:{update_target} -> {quality_score}"
                return None

            elif action == OutputAction.STORE_MESSAGE:
                # 存储消息到 Eden 区
                self.memory.store_message(
                    message=content,
                    role="user",
                    importance=target.importance,
                )
                return f"message -> Eden区"

            elif action == OutputAction.STORE_ARTIFACT:
                # 存储到流水线的产出物
                self.pipeline.store_artifact(target.key, value)
                return f"artifact:{target.key} -> Pipeline"

        except Exception as e:
            return f"error: {str(e)}"

        return None

    def execute_stage(
        self,
        stage: WorkflowStage,
        custom_handler: Callable | None = None,
    ) -> StageResult:
        """
        执行单个阶段

        Args:
            stage: 工作流阶段
            custom_handler: 自定义处理器（覆盖注册的处理器）

        Returns:
            StageResult: 执行结果
        """
        start_time = time.time()
        result = StageResult(
            stage_name=stage.name,
            status=StageStatus.PENDING,
        )

        # 获取记忆映射
        mapping = get_stage_mapping(self.pipeline_name, stage.name)

        try:
            # 1. 加载输入
            inputs = self.load_inputs(stage, mapping)
            result.inputs_loaded = inputs

            # 2. 执行阶段处理
            stage.start()
            result.status = StageStatus.RUNNING

            handler = custom_handler or self._stage_handlers.get(stage.name)
            outputs = {}

            if handler:
                # 调用自定义处理器
                outputs = handler(inputs)
            else:
                # 默认处理：简单传递
                outputs = {out: inputs.get(out) for out in stage.outputs if out in inputs}

            # 3. 写入输出到记忆
            writes = self.write_outputs(stage, outputs, mapping)
            result.outputs_produced = outputs
            result.memory_writes = writes

            # 4. 完成阶段
            stage.complete({"outputs": outputs, "writes": writes})
            result.status = StageStatus.COMPLETED

        except Exception as e:
            stage.fail(str(e))
            result.status = StageStatus.FAILED
            result.errors.append(str(e))

        result.duration = time.time() - start_time
        return result

    def execute_pipeline(
        self,
        handlers: dict[str, Callable] | None = None,
        stop_on_failure: bool = True,
    ) -> WorkflowExecutionResult:
        """
        执行整个工作流

        Args:
            handlers: 阶段处理器映射
            stop_on_failure: 是否在失败时停止

        Returns:
            WorkflowExecutionResult: 执行结果
        """
        start_time = time.time()
        result = WorkflowExecutionResult(pipeline_name=self.pipeline_name)

        # 注册处理器
        if handlers:
            for name, handler in handlers.items():
                self.register_handler(name, handler)

        # 获取执行顺序
        execution_order = self.pipeline.get_execution_order()

        for stage_name in execution_order:
            stage = self.pipeline.get_stage(stage_name)
            if not stage:
                continue

            # 执行阶段
            stage_result = self.execute_stage(stage)
            result.stage_results.append(stage_result)

            if stage_result.status == StageStatus.COMPLETED:
                result.stages_completed += 1
            else:
                result.stages_failed += 1
                if stop_on_failure:
                    break

        # 收集最终产出物
        result.final_artifacts = dict(self.pipeline._artifacts)
        result.total_duration = time.time() - start_time

        return result

    def get_context(self) -> dict[str, Any]:
        """获取当前执行上下文"""
        return self._context.copy()

    def set_context(self, key: str, value: Any) -> None:
        """设置执行上下文"""
        self._context[key] = value

    def clear_context(self) -> None:
        """清空执行上下文"""
        self._context.clear()


# ==================== 便捷函数 ====================

def create_executor(
    memory_manager: MemoryManager,
    pipeline: WorkflowPipeline,
    pipeline_name: str = "",
) -> WorkflowExecutor:
    """
    创建工作流执行器

    Args:
        memory_manager: 记忆管理器
        pipeline: 工作流流水线
        pipeline_name: 工作流名称

    Returns:
        WorkflowExecutor 实例
    """
    return WorkflowExecutor(
        memory_manager=memory_manager,
        pipeline=pipeline,
        pipeline_name=pipeline_name,
    )