"""
Codegen Module - 代码生成模块

提供代码生成辅助能力：
- 模板代码库
- 变量替换生成
- 架构约束检查
- 代码片段复用
"""

from harnessgenj.codegen.templates import (
    CodeTemplate,
    TemplateRegistry,
    TemplateType,
)
from harnessgenj.codegen.generator import (
    CodeGenerator,
    GeneratorConfig,
    GenerationResult,
    create_code_generator,
)

__all__ = [
    # Templates
    "CodeTemplate",
    "TemplateRegistry",
    "TemplateType",
    # Generator
    "CodeGenerator",
    "GeneratorConfig",
    "GenerationResult",
    "create_code_generator",
]