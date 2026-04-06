"""
Code Generator - 代码生成器

提供代码生成能力：
- 模板渲染
- 变量推断
- 架构约束检查
- 批量生成
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time

from harnessgenj.codegen.templates import (
    CodeTemplate,
    TemplateRegistry,
    TemplateType,
    create_template_registry,
)


class GeneratorMode(Enum):
    """生成模式"""

    TEMPLATE = "template"       # 模板模式
    CUSTOM = "custom"           # 自定义模式
    HYBRID = "hybrid"           # 混合模式


class GeneratorConfig(BaseModel):
    """生成器配置"""

    mode: GeneratorMode = Field(default=GeneratorMode.TEMPLATE, description="生成模式")
    language: str = Field(default="python", description="目标语言")
    validate_output: bool = Field(default=True, description="是否验证输出")
    auto_import: bool = Field(default=True, description="自动添加导入")
    format_output: bool = Field(default=True, description="格式化输出")
    strict_variables: bool = Field(default=False, description="严格变量检查")


class GenerationResult(BaseModel):
    """生成结果"""

    success: bool
    code: str = ""
    template_name: str | None = None
    variables_used: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration: float = 0.0


class ArchitectureConstraint(BaseModel):
    """架构约束"""

    name: str
    description: str
    check_pattern: str
    error_message: str
    severity: str = "error"  # error | warning


class CodeGenerator:
    """
    代码生成器

    支持:
    1. 基于模板生成
    2. 变量推断
    3. 架构约束检查
    4. 批量生成
    """

    def __init__(
        self,
        config: GeneratorConfig | None = None,
        template_registry: TemplateRegistry | None = None,
    ) -> None:
        """
        初始化代码生成器

        Args:
            config: 生成器配置
            template_registry: 模板注册中心
        """
        self.config = config or GeneratorConfig()
        self._registry = template_registry or create_template_registry()
        self._constraints: list[ArchitectureConstraint] = []
        self._stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "constraint_violations": 0,
        }

        # 加载默认约束
        self._load_default_constraints()

    def _load_default_constraints(self) -> None:
        """加载默认架构约束"""
        # 安全约束
        self.add_constraint(ArchitectureConstraint(
            name="no_eval",
            description="禁止使用 eval()",
            check_pattern=r'\beval\s*\(',
            error_message="禁止使用 eval() 函数，存在安全风险",
            severity="error",
        ))

        self.add_constraint(ArchitectureConstraint(
            name="no_exec",
            description="禁止使用 exec()",
            check_pattern=r'\bexec\s*\(',
            error_message="禁止使用 exec() 函数，存在安全风险",
            severity="error",
        ))

        # 代码风格约束
        self.add_constraint(ArchitectureConstraint(
            name="no_hardcoded_secrets",
            description="禁止硬编码密钥",
            check_pattern=r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']',
            error_message="禁止硬编码敏感信息",
            severity="warning",
        ))

    # ==================== 模板生成 ====================

    def generate_from_template(
        self,
        template_name: str,
        variables: dict[str, Any] | None = None,
    ) -> GenerationResult:
        """
        从模板生成代码

        Args:
            template_name: 模板名称
            variables: 变量值

        Returns:
            GenerationResult: 生成结果
        """
        start_time = time.time()
        self._stats["total_generations"] += 1

        warnings = []
        errors = []

        # 获取模板
        template = self._registry.get(template_name)
        if not template:
            self._stats["failed_generations"] += 1
            return GenerationResult(
                success=False,
                template_name=template_name,
                errors=[f"Template not found: {template_name}"],
                duration=time.time() - start_time,
            )

        try:
            # 渲染模板
            code = template.render(variables)

            # 验证输出
            if self.config.validate_output:
                valid, template_errors = template.validate_output(code)
                if not valid:
                    errors.extend(template_errors)

            # 架构约束检查
            constraint_errors = self._check_constraints(code)
            errors.extend(constraint_errors)

            # 自动添加导入
            if self.config.auto_import and template.language == "python":
                code = self._add_imports(code, template)

            if errors:
                self._stats["failed_generations"] += 1
                return GenerationResult(
                    success=False,
                    code=code,
                    template_name=template_name,
                    variables_used=variables or {},
                    warnings=warnings,
                    errors=errors,
                    duration=time.time() - start_time,
                )

            self._stats["successful_generations"] += 1
            return GenerationResult(
                success=True,
                code=code,
                template_name=template_name,
                variables_used=variables or {},
                warnings=warnings,
                duration=time.time() - start_time,
            )

        except Exception as e:
            self._stats["failed_generations"] += 1
            return GenerationResult(
                success=False,
                template_name=template_name,
                errors=[str(e)],
                duration=time.time() - start_time,
            )

    def generate_function(
        self,
        name: str,
        params: str = "",
        description: str = "",
        body: str = "pass",
        return_value: str = "None",
    ) -> GenerationResult:
        """快速生成函数"""
        return self.generate_from_template("python_function", {
            "function_name": name,
            "params": params,
            "description": description or f"{name} 函数",
            "args_doc": "",
            "return_doc": "返回值",
            "body": body,
            "return_value": return_value,
        })

    def generate_class(
        self,
        name: str,
        description: str = "",
        init_params: str = "",
        init_body: str = "pass",
    ) -> GenerationResult:
        """快速生成类"""
        return self.generate_from_template("python_class", {
            "class_name": name,
            "description": description or f"{name} 类",
            "init_params": init_params,
            "init_body": init_body,
        })

    def generate_test(
        self,
        test_name: str,
        description: str = "",
        arrange: str = "# 准备",
        act: str = "# 执行",
        assertion: str = "True",
    ) -> GenerationResult:
        """快速生成测试"""
        return self.generate_from_template("pytest_test", {
            "test_name": test_name,
            "description": description or f"测试 {test_name}",
            "arrange": arrange,
            "act": act,
            "assertion": assertion,
        })

    # ==================== 批量生成 ====================

    def generate_batch(
        self,
        specs: list[dict[str, Any]],
    ) -> list[GenerationResult]:
        """
        批量生成代码

        Args:
            specs: 生成规格列表，每个包含 template_name 和 variables

        Returns:
            生成结果列表
        """
        results = []
        for spec in specs:
            template_name = spec.get("template_name")
            variables = spec.get("variables", {})
            result = self.generate_from_template(template_name, variables)
            results.append(result)
        return results

    # ==================== 约束管理 ====================

    def add_constraint(self, constraint: ArchitectureConstraint) -> None:
        """添加架构约束"""
        self._constraints.append(constraint)

    def remove_constraint(self, name: str) -> bool:
        """移除架构约束"""
        for i, c in enumerate(self._constraints):
            if c.name == name:
                self._constraints.pop(i)
                return True
        return False

    def list_constraints(self) -> list[ArchitectureConstraint]:
        """列出所有约束"""
        return self._constraints.copy()

    def _check_constraints(self, code: str) -> list[str]:
        """检查架构约束"""
        import re
        errors = []
        for constraint in self._constraints:
            if re.search(constraint.check_pattern, code):
                self._stats["constraint_violations"] += 1
                if constraint.severity == "error":
                    errors.append(constraint.error_message)
        return errors

    # ==================== 辅助功能 ====================

    def _add_imports(self, code: str, template: CodeTemplate) -> str:
        """自动添加导入"""
        # 如果禁用了自动导入，直接返回原代码
        if not self.config.auto_import:
            return code

        imports = []

        # 检测需要的导入
        if "BaseModel" in code:
            imports.append("from pydantic import BaseModel, Field")

        if "BaseModel" in code and "Field" not in code:
            imports.append("from pydantic import BaseModel")

        if "@router" in code:
            imports.append("from fastapi import APIRouter, HTTPException")
            imports.append("router = APIRouter()")

        if "pytest" in template.tags or "test" in template.tags:
            imports.append("import pytest")

        if imports:
            import_block = "\n".join(imports) + "\n\n"
            return import_block + code

        return code

    def infer_variables(self, template_name: str, partial_vars: dict[str, Any]) -> dict[str, Any]:
        """
        推断变量值

        Args:
            template_name: 模板名称
            partial_vars: 部分变量值

        Returns:
            完整变量字典
        """
        template = self._registry.get(template_name)
        if not template:
            return partial_vars

        # 合并默认值
        result = {**template.variables, **partial_vars}

        # 推断常见变量
        if "function_name" in template.variables and "function_name" not in partial_vars:
            if "name" in partial_vars:
                result["function_name"] = partial_vars["name"]

        if "class_name" in template.variables and "class_name" not in partial_vars:
            if "name" in partial_vars:
                result["class_name"] = partial_vars["name"]

        return result

    # ==================== 统计 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "templates_available": len(self._registry.list_templates()),
            "constraints_count": len(self._constraints),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "constraint_violations": 0,
        }


# ==================== 便捷函数 ====================

def create_code_generator(
    config: GeneratorConfig | None = None,
    template_registry: TemplateRegistry | None = None,
) -> CodeGenerator:
    """创建代码生成器"""
    return CodeGenerator(config, template_registry)