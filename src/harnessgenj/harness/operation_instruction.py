"""
OperationInstruction - 操作指令协议

框架生成的操作指令，供 AI (Claude Code) 执行。

设计理念：
- 框架负责：流程编排、权限控制、状态管理
- AI 负责：代码生成、文件操作、具体实现
- 通信协议：OperationInstruction 作为桥梁

使用流程：
1. 用户调用 harness.develop("功能描述")
2. 框架创建任务，签发操作许可
3. 框架生成 OperationInstruction
4. AI 读取指令，在许可范围内执行操作
5. AI 报告执行结果给框架
6. 框架验证结果，完成任务

示例：
    # 在 develop() 中
    instruction = OperationInstruction(
        task_id="TASK-xxx",
        operation_type="develop",
        permitted_files=["src/module.py", "tests/test_module.py"],
        instructions=[
            "实现用户登录功能",
            "编写单元测试",
            "确保代码通过质量检查",
        ],
        context={"project_name": "MyApp", "tech_stack": "Python + FastAPI"},
        expected_outputs=["实现代码", "测试代码"],
    )

    # 返回给 AI
    return {
        "status": "awaiting_execution",
        "instruction": instruction.model_dump(),
    }
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class OperationType(str, Enum):
    """操作类型"""
    DEVELOP = "develop"           # 功能开发
    FIX_BUG = "fix_bug"           # Bug修复
    REVIEW = "review"             # 代码审查
    REFACTOR = "refactor"         # 重构
    TEST = "test"                 # 测试编写
    DOCUMENT = "document"         # 文档编写
    ANALYZE = "analyze"           # 分析任务


class InstructionPriority(str, Enum):
    """指令优先级"""
    CRITICAL = "critical"   # 必须立即执行
    HIGH = "high"           # 高优先级
    NORMAL = "normal"       # 正常优先级
    LOW = "low"             # 低优先级


class FilePermission(BaseModel):
    """文件权限详情"""
    path: str = Field(description="文件路径")
    operation: str = Field(default="write", description="允许的操作: read/write/edit")
    reason: str = Field(default="", description="授权原因")


class ExecutionStep(BaseModel):
    """执行步骤"""
    order: int = Field(description="执行顺序")
    description: str = Field(description="步骤描述")
    details: list[str] = Field(default_factory=list, description="详细说明")
    optional: bool = Field(default=False, description="是否可选")


class ExpectedOutput(BaseModel):
    """预期产出"""
    name: str = Field(description="产出名称")
    description: str = Field(description="产出描述")
    required: bool = Field(default=True, description="是否必须")


class OperationInstruction(BaseModel):
    """
    操作指令 - 框架生成的执行指令

    框架通过此协议告诉 AI：
    1. 需要做什么
    2. 可以修改哪些文件
    3. 预期产出什么
    4. 上下文信息

    AI 在收到指令后：
    1. 检查许可范围，只修改 permitted_files 中的文件
    2. 按顺序执行 instructions
    3. 生成预期产出
    4. 报告结果给框架
    """

    # 基本信息
    task_id: str = Field(description="任务ID")
    operation_type: OperationType = Field(description="操作类型")
    priority: InstructionPriority = Field(
        default=InstructionPriority.NORMAL,
        description="指令优先级"
    )

    # 权限控制
    permitted_files: list[FilePermission] = Field(
        default_factory=list,
        description="允许操作的文件列表（许可范围）"
    )

    # 执行指令
    instructions: list[str] = Field(
        default_factory=list,
        description="操作指令列表"
    )
    execution_steps: list[ExecutionStep] = Field(
        default_factory=list,
        description="详细执行步骤"
    )

    # 上下文信息
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="执行上下文（项目信息、技术栈等）"
    )

    # 预期产出
    expected_outputs: list[ExpectedOutput] = Field(
        default_factory=list,
        description="预期产出列表"
    )

    # 质量要求
    quality_requirements: list[str] = Field(
        default_factory=lambda: [
            "代码必须通过静态检查",
            "代码必须通过单元测试",
            "代码必须通过对抗审查",
        ],
        description="质量要求"
    )

    # 元数据
    created_at: float = Field(default_factory=time.time, description="创建时间")
    expires_at: float | None = Field(default=None, description="过期时间")
    session_id: str = Field(default="", description="会话ID")

    def add_permitted_file(
        self,
        path: str,
        operation: str = "write",
        reason: str = ""
    ) -> None:
        """添加允许操作的文件"""
        self.permitted_files.append(FilePermission(
            path=path,
            operation=operation,
            reason=reason,
        ))

    def add_instruction(self, instruction: str, details: list[str] | None = None) -> None:
        """添加执行指令"""
        self.instructions.append(instruction)
        if details:
            self.execution_steps.append(ExecutionStep(
                order=len(self.execution_steps) + 1,
                description=instruction,
                details=details,
            ))

    def add_expected_output(self, name: str, description: str, required: bool = True) -> None:
        """添加预期产出"""
        self.expected_outputs.append(ExpectedOutput(
            name=name,
            description=description,
            required=required,
        ))

    def get_permitted_paths(self) -> list[str]:
        """获取允许操作的文件路径列表"""
        return [fp.path for fp in self.permitted_files]

    def to_prompt(self) -> str:
        """
        转换为 AI 可读的提示词格式

        Returns:
            格式化的提示词，供 AI 理解和执行
        """
        lines = [
            f"# 🎯 操作指令 [任务ID: {self.task_id}]",
            "",
            f"**操作类型**: {self.operation_type.value}",
            f"**优先级**: {self.priority.value}",
            "",
            "## 📁 许可范围",
            "以下文件已被授权操作，请勿修改其他文件：",
            "",
        ]

        for fp in self.permitted_files:
            lines.append(f"- `{fp.path}` ({fp.operation}) {fp.reason and '- ' + fp.reason}")

        lines.extend([
            "",
            "## 📋 执行指令",
            "",
        ])

        for i, instruction in enumerate(self.instructions, 1):
            lines.append(f"{i}. {instruction}")

        if self.execution_steps:
            lines.extend([
                "",
                "### 详细步骤",
                "",
            ])
            for step in self.execution_steps:
                lines.append(f"**步骤 {step.order}**: {step.description}")
                for detail in step.details:
                    lines.append(f"  - {detail}")

        lines.extend([
            "",
            "## 📤 预期产出",
            "",
        ])

        for output in self.expected_outputs:
            required_mark = "✅" if output.required else "📝"
            lines.append(f"- {required_mark} **{output.name}**: {output.description}")

        lines.extend([
            "",
            "## ✅ 质量要求",
            "",
        ])

        for req in self.quality_requirements:
            lines.append(f"- {req}")

        if self.context:
            lines.extend([
                "",
                "## 📊 上下文信息",
                "",
            ])
            for key, value in self.context.items():
                if isinstance(value, dict):
                    lines.append(f"**{key}**:")
                    for k, v in value.items():
                        lines.append(f"  - {k}: {v}")
                elif isinstance(value, list):
                    lines.append(f"**{key}**: {', '.join(map(str, value))}")
                else:
                    lines.append(f"**{key}**: {value}")

        lines.extend([
            "",
            "---",
            f"*指令创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.created_at))}*",
            "",
            "⚠️ **重要提醒**: 完成操作后，请调用 `harness.complete_task(task_id, '摘要')` 报告结果。",
        ])

        return "\n".join(lines)


class ExecutionResult(BaseModel):
    """
    执行结果 - AI 完成操作后报告给框架

    AI 在完成操作指令后，需要生成此结果报告给框架。
    """

    task_id: str = Field(description="关联的任务ID")
    success: bool = Field(description="是否成功")
    summary: str = Field(description="执行摘要")

    # 产出物
    artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="产出物 {名称: 内容/路径}"
    )

    # 修改的文件
    modified_files: list[str] = Field(
        default_factory=list,
        description="实际修改的文件列表"
    )

    # 遇到的问题
    issues: list[str] = Field(
        default_factory=list,
        description="遇到的问题"
    )

    # 建议
    suggestions: list[str] = Field(
        default_factory=list,
        description="改进建议"
    )

    # 元数据
    executed_at: float = Field(default_factory=time.time, description="执行时间")
    duration: float = Field(default=0.0, description="执行耗时(秒)")


# ==================== 便捷函数 ====================

def create_develop_instruction(
    task_id: str,
    feature_request: str,
    permitted_files: list[str],
    context: dict[str, Any] | None = None,
) -> OperationInstruction:
    """
    创建开发操作指令

    Args:
        task_id: 任务ID
        feature_request: 功能需求
        permitted_files: 允许修改的文件
        context: 上下文信息

    Returns:
        操作指令
    """
    instruction = OperationInstruction(
        task_id=task_id,
        operation_type=OperationType.DEVELOP,
        context=context or {},
    )

    # 添加许可文件
    for path in permitted_files:
        instruction.add_permitted_file(path, "write", f"开发: {feature_request[:50]}")

    # 添加执行指令
    instruction.add_instruction(
        f"实现功能: {feature_request}",
        details=[
            "分析需求，设计实现方案",
            "编写核心代码",
            "处理边界情况",
            "添加错误处理",
        ]
    )
    instruction.add_instruction(
        "编写单元测试",
        details=[
            "测试正常流程",
            "测试边界情况",
            "测试错误处理",
        ]
    )
    instruction.add_instruction(
        "确保代码质量",
        details=[
            "运行静态检查",
            "运行单元测试",
            "检查代码风格",
        ]
    )

    # 添加预期产出
    instruction.add_expected_output("实现代码", f"{feature_request} 的实现代码")
    instruction.add_expected_output("测试代码", "对应的单元测试代码")

    return instruction


def create_fix_bug_instruction(
    task_id: str,
    bug_description: str,
    permitted_files: list[str],
    context: dict[str, Any] | None = None,
) -> OperationInstruction:
    """
    创建 Bug 修复操作指令

    Args:
        task_id: 任务ID
        bug_description: Bug 描述
        permitted_files: 允许修改的文件
        context: 上下文信息

    Returns:
        操作指令
    """
    instruction = OperationInstruction(
        task_id=task_id,
        operation_type=OperationType.FIX_BUG,
        priority=InstructionPriority.HIGH,  # Bug 修复高优先级
        context=context or {},
    )

    # 添加许可文件
    for path in permitted_files:
        instruction.add_permitted_file(path, "write", f"修复Bug: {bug_description[:50]}")

    # 添加执行指令
    instruction.add_instruction(
        f"修复Bug: {bug_description}",
        details=[
            "分析问题根因",
            "设计修复方案",
            "实现修复代码",
            "添加回归测试",
        ]
    )
    instruction.add_instruction(
        "验证修复",
        details=[
            "运行相关测试",
            "确认Bug已修复",
            "检查是否引入新问题",
        ]
    )

    # 添加预期产出
    instruction.add_expected_output("修复代码", "Bug 修复代码")
    instruction.add_expected_output("回归测试", "回归测试用例")

    return instruction