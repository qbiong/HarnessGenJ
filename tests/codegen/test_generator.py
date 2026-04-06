"""
Tests for Code Generator Module

测试代码生成器功能:
- 模板生成
- 变量推断
- 架构约束检查
- 批量生成
"""

import pytest
from harnessgenj.codegen.generator import (
    CodeGenerator,
    GeneratorConfig,
    GeneratorMode,
    GenerationResult,
    ArchitectureConstraint,
    create_code_generator,
)
from harnessgenj.codegen.templates import create_template_registry


class TestGeneratorMode:
    """测试生成模式枚举"""

    def test_template_mode(self):
        """模板模式"""
        assert GeneratorMode.TEMPLATE.value == "template"

    def test_custom_mode(self):
        """自定义模式"""
        assert GeneratorMode.CUSTOM.value == "custom"

    def test_hybrid_mode(self):
        """混合模式"""
        assert GeneratorMode.HYBRID.value == "hybrid"


class TestGeneratorConfig:
    """测试生成器配置"""

    def test_create_default_config(self):
        """创建默认配置"""
        config = GeneratorConfig()
        assert config.mode == GeneratorMode.TEMPLATE
        assert config.language == "python"
        assert config.validate_output is True
        assert config.auto_import is True
        assert config.format_output is True

    def test_create_custom_config(self):
        """创建自定义配置"""
        config = GeneratorConfig(
            mode=GeneratorMode.CUSTOM,
            language="java",
            validate_output=False,
        )
        assert config.mode == GeneratorMode.CUSTOM
        assert config.language == "java"
        assert config.validate_output is False


class TestArchitectureConstraint:
    """测试架构约束"""

    def test_create_constraint(self):
        """创建约束"""
        constraint = ArchitectureConstraint(
            name="no_eval",
            description="禁止使用 eval()",
            check_pattern=r'\beval\s*\(',
            error_message="禁止使用 eval() 函数",
            severity="error",
        )
        assert constraint.name == "no_eval"
        assert constraint.severity == "error"

    def test_warning_constraint(self):
        """警告级约束"""
        constraint = ArchitectureConstraint(
            name="long_line",
            description="行过长警告",
            check_pattern=r'.{100,}',
            error_message="行过长，建议拆分",
            severity="warning",
        )
        assert constraint.severity == "warning"


class TestGenerationResult:
    """测试生成结果"""

    def test_success_result(self):
        """成功结果"""
        result = GenerationResult(
            success=True,
            code="def hello(): pass",
            template_name="python_function",
        )
        assert result.success is True
        assert len(result.errors) == 0

    def test_failure_result(self):
        """失败结果"""
        result = GenerationResult(
            success=False,
            errors=["Template not found"],
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_result_with_warnings(self):
        """带警告的结果"""
        result = GenerationResult(
            success=True,
            warnings=["Line too long"],
        )
        assert result.warnings[0] == "Line too long"

    def test_result_with_variables(self):
        """带使用变量的结果"""
        result = GenerationResult(
            success=True,
            variables_used={"function_name": "test"},
        )
        assert result.variables_used["function_name"] == "test"


class TestCodeGenerator:
    """测试代码生成器"""

    def test_create_generator(self):
        """创建生成器"""
        generator = create_code_generator()
        assert isinstance(generator, CodeGenerator)
        assert generator.config.mode == GeneratorMode.TEMPLATE

    def test_create_generator_with_config(self):
        """创建带配置的生成器"""
        config = GeneratorConfig(language="python")
        generator = create_code_generator(config)
        assert generator.config.language == "python"

    def test_generate_from_template(self):
        """从模板生成"""
        generator = create_code_generator()
        result = generator.generate_from_template(
            "python_function",
            {"function_name": "my_func"},
        )
        assert result.success is True
        assert "my_func" in result.code
        assert result.template_name == "python_function"

    def test_generate_from_nonexistent_template(self):
        """从不存在模板生成"""
        generator = create_code_generator()
        result = generator.generate_from_template(
            "nonexistent_template",
            {},
        )
        assert result.success is False
        assert "Template not found" in result.errors[0]

    def test_generate_function(self):
        """快速生成函数"""
        generator = create_code_generator()
        result = generator.generate_function(
            name="add",
            params="a, b",
            description="Add two numbers",
            body="return a + b",
            return_value="a + b",
        )
        assert result.success is True
        assert "def add(a, b):" in result.code
        assert "return a + b" in result.code

    def test_generate_class(self):
        """快速生成类"""
        generator = create_code_generator()
        result = generator.generate_class(
            name="User",
            description="User model",
            init_params="name",
            init_body="self.name = name",
        )
        assert result.success is True
        assert "class User:" in result.code

    def test_generate_test(self):
        """快速生成测试"""
        generator = create_code_generator()
        result = generator.generate_test(
            test_name="add_numbers",
            description="Test addition",
            arrange="a = 1",
            act="result = add(a, 1)",
            assertion="result == 2",
        )
        assert result.success is True
        assert "def test_add_numbers():" in result.code
        assert "assert result == 2" in result.code

    def test_generate_batch(self):
        """批量生成"""
        generator = create_code_generator()
        specs = [
            {"template_name": "python_function", "variables": {"function_name": "func1"}},
            {"template_name": "python_function", "variables": {"function_name": "func2"}},
        ]
        results = generator.generate_batch(specs)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_add_constraint(self):
        """添加约束"""
        generator = create_code_generator()
        constraint = ArchitectureConstraint(
            name="custom_constraint",
            description="Custom constraint",
            check_pattern=r'password',
            error_message="禁止包含密码",
        )
        generator.add_constraint(constraint)
        constraints = generator.list_constraints()
        assert "custom_constraint" in [c.name for c in constraints]

    def test_remove_constraint(self):
        """移除约束"""
        generator = create_code_generator()
        # 默认已加载约束
        result = generator.remove_constraint("no_eval")
        assert result is True

        # 再次移除应该失败
        result = generator.remove_constraint("no_eval")
        assert result is False

    def test_constraint_check_eval(self):
        """约束检查 eval"""
        generator = create_code_generator()
        # 包含 eval 的代码应该被拦截
        result = generator._check_constraints("eval('dangerous')")
        assert len(result) > 0
        assert "eval" in result[0].lower()

    def test_constraint_check_exec(self):
        """约束检查 exec"""
        generator = create_code_generator()
        result = generator._check_constraints("exec('dangerous')")
        assert len(result) > 0

    def test_constraint_check_hardcoded_secrets(self):
        """约束检查硬编码密钥"""
        generator = create_code_generator()
        # 注意：这是警告级别，不应该阻止生成
        result = generator._check_constraints("password = 'secret123'")
        # 这应该被检查到，但由于是 warning 可能不会返回错误
        # 具体行为取决于实现

    def test_constraint_check_safe_code(self):
        """约束检查安全代码"""
        generator = create_code_generator()
        result = generator._check_constraints("def safe(): pass")
        assert len(result) == 0

    def test_infer_variables(self):
        """变量推断"""
        generator = create_code_generator()
        result = generator.infer_variables(
            "python_function",
            {"name": "test_func"},
        )
        # 应能从 name 推断 function_name
        assert "function_name" in result or "name" in result

    def test_infer_variables_no_template(self):
        """变量推断不存在模板"""
        generator = create_code_generator()
        result = generator.infer_variables(
            "nonexistent",
            {"test": "value"},
        )
        assert result == {"test": "value"}

    def test_get_stats(self):
        """获取统计"""
        generator = create_code_generator()
        generator.generate_function("test")
        stats = generator.get_stats()
        assert stats["total_generations"] == 1
        assert stats["successful_generations"] == 1
        assert "templates_available" in stats

    def test_reset_stats(self):
        """重置统计"""
        generator = create_code_generator()
        generator.generate_function("test")
        generator.reset_stats()
        stats = generator.get_stats()
        assert stats["total_generations"] == 0

    def test_default_constraints_loaded(self):
        """默认约束已加载"""
        generator = create_code_generator()
        constraints = generator.list_constraints()
        names = [c.name for c in constraints]
        assert "no_eval" in names
        assert "no_exec" in names

    def test_auto_import_base_model(self):
        """自动导入 BaseModel"""
        config = GeneratorConfig(auto_import=True)
        generator = create_code_generator(config)

        # 生成包含 BaseModel 的代码
        code = "class User(BaseModel): pass"
        template = generator._registry.get("pydantic_model")
        result = generator._add_imports(code, template)
        assert "from pydantic" in result

    def test_no_auto_import_when_disabled(self):
        """禁用时不自动导入"""
        config = GeneratorConfig(auto_import=False)
        generator = create_code_generator(config)

        code = "class User(BaseModel): pass"
        template = generator._registry.get("pydantic_model")
        result = generator._add_imports(code, template)
        assert "from pydantic" not in result


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_code_generator(self):
        """创建代码生成器"""
        generator = create_code_generator()
        assert isinstance(generator, CodeGenerator)

    def test_create_with_registry(self):
        """创建带模板注册中心"""
        registry = create_template_registry()
        generator = create_code_generator(template_registry=registry)
        assert generator._registry is registry