"""
Tests for Code Templates Module

测试代码模板功能:
- 模板创建
- 变量替换
- 模板注册
- 输出验证
"""

import pytest
from harnessgenj.codegen.templates import (
    CodeTemplate,
    TemplateRegistry,
    TemplateType,
    create_template_registry,
)


class TestTemplateType:
    """测试模板类型枚举"""

    def test_function_type(self):
        """函数模板类型"""
        assert TemplateType.FUNCTION.value == "function"

    def test_class_type(self):
        """类模板类型"""
        assert TemplateType.CLASS.value == "class"

    def test_test_type(self):
        """测试模板类型"""
        assert TemplateType.TEST.value == "test"

    def test_api_endpoint_type(self):
        """API 端点模板类型"""
        assert TemplateType.API_ENDPOINT.value == "api_endpoint"

    def test_model_type(self):
        """模型模板类型"""
        assert TemplateType.MODEL.value == "model"

    def test_config_type(self):
        """配置模板类型"""
        assert TemplateType.CONFIG.value == "config"


class TestCodeTemplate:
    """测试代码模板"""

    def test_create_template(self):
        """创建模板"""
        template = CodeTemplate(
            name="simple_template",
            template_type=TemplateType.FUNCTION,
            template="def ${function_name}():\n    pass",
            variables={"function_name": "my_func"},
            required_vars=["function_name"],
        )
        assert template.name == "simple_template"
        assert template.template_type == TemplateType.FUNCTION

    def test_render_template(self):
        """渲染模板"""
        template = CodeTemplate(
            name="func_template",
            template="def ${function_name}():\n    pass",
            variables={"function_name": "default_name"},
        )
        result = template.render({"function_name": "hello_world"})
        assert "hello_world" in result

    def test_render_with_default_values(self):
        """使用默认值渲染"""
        template = CodeTemplate(
            name="func_template",
            template="def ${function_name}():\n    pass",
            variables={"function_name": "default_func"},
        )
        result = template.render()  # 不提供变量
        assert "default_func" in result

    def test_render_with_double_braces(self):
        """双花括号格式"""
        template = CodeTemplate(
            name="test_template",
            template="def {{function_name}}():\n    pass",
            variables={"function_name": "test"},
        )
        result = template.render({"function_name": "my_func"})
        assert "my_func" in result

    def test_render_missing_required_vars(self):
        """缺少必需变量"""
        template = CodeTemplate(
            name="test_template",
            template="def ${function_name}():\n    pass",
            required_vars=["function_name"],
        )
        with pytest.raises(ValueError):
            template.render()

    def test_validate_output_valid(self):
        """验证有效输出"""
        template = CodeTemplate(
            name="test_template",
            template="def ${function_name}():\n    pass",
            language="python",
        )
        output = "def my_function():\n    pass"
        valid, errors = template.validate_output(output)
        assert valid is True
        assert len(errors) == 0

    def test_validate_output_unresolved_vars(self):
        """验证未替换变量"""
        template = CodeTemplate(
            name="test_template",
            template="def ${function_name}():\n    pass",
            language="python",
        )
        output = "def ${function_name}():\n    pass"  # 变量未替换
        valid, errors = template.validate_output(output)
        assert len(errors) > 0

    def test_validate_output_syntax_error(self):
        """验证语法错误"""
        template = CodeTemplate(
            name="test_template",
            template="def ${function_name}():\n    pass",
            language="python",
        )
        output = "def my_func():\n    pass"  # Python语法错误
        valid, errors = template.validate_output("def broken():::\n")
        assert valid is False


class TestTemplateRegistry:
    """测试模板注册中心"""

    def test_create_registry(self):
        """创建注册中心"""
        registry = create_template_registry()
        assert isinstance(registry, TemplateRegistry)

    def test_registry_has_defaults(self):
        """注册中心有默认模板"""
        registry = create_template_registry()
        templates = registry.list_templates()
        # 应有预定义模板
        assert len(templates) > 0

    def test_get_template(self):
        """获取模板"""
        registry = create_template_registry()
        template = registry.get("python_function")
        assert template is not None
        assert template.name == "python_function"

    def test_get_nonexistent_template(self):
        """获取不存在模板"""
        registry = create_template_registry()
        template = registry.get("nonexistent")
        assert template is None

    def test_register_template(self):
        """注册模板"""
        registry = create_template_registry()
        template = CodeTemplate(
            name="custom_template",
            template_type=TemplateType.CUSTOM,
            template="custom code",
        )
        result = registry.register(template)
        assert result is True
        assert registry.get("custom_template") is not None

    def test_register_duplicate(self):
        """注册重复模板"""
        registry = create_template_registry()
        template1 = CodeTemplate(name="duplicate", template="code1")
        template2 = CodeTemplate(name="duplicate", template="code2")

        registry.register(template1)
        result = registry.register(template2)
        assert result is False

    def test_unregister_template(self):
        """注销模板"""
        registry = create_template_registry()
        template = CodeTemplate(name="to_remove", template="code")
        registry.register(template)

        result = registry.unregister("to_remove")
        assert result is True
        assert registry.get("to_remove") is None

    def test_unregister_nonexistent(self):
        """注销不存在模板"""
        registry = create_template_registry()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_list_by_type(self):
        """按类型列出模板"""
        registry = create_template_registry()
        templates = registry.list_templates(template_type=TemplateType.FUNCTION)
        for t in templates:
            assert t.template_type == TemplateType.FUNCTION

    def test_list_by_tags(self):
        """按标签列出模板"""
        registry = create_template_registry()
        templates = registry.list_templates(tags=["python"])
        for t in templates:
            assert "python" in t.tags

    def test_render_template(self):
        """渲染模板"""
        registry = create_template_registry()
        result = registry.render("python_function", {"function_name": "test_func"})
        assert "test_func" in result

    def test_render_nonexistent_raises(self):
        """渲染不存在模板抛出异常"""
        registry = create_template_registry()
        with pytest.raises(ValueError):
            registry.render("nonexistent", {})

    def test_get_python_function_template(self):
        """获取 Python 函数模板"""
        registry = create_template_registry()
        template = registry.get("python_function")
        assert template.template_type == TemplateType.FUNCTION
        assert "function_name" in template.required_vars

    def test_get_python_class_template(self):
        """获取 Python 类模板"""
        registry = create_template_registry()
        template = registry.get("python_class")
        assert template.template_type == TemplateType.CLASS
        assert "class_name" in template.required_vars

    def test_get_fastapi_endpoint_template(self):
        """获取 FastAPI 端点模板"""
        registry = create_template_registry()
        template = registry.get("fastapi_endpoint")
        assert template.template_type == TemplateType.API_ENDPOINT
        assert "path" in template.required_vars

    def test_get_pytest_test_template(self):
        """获取 Pytest 测试模板"""
        registry = create_template_registry()
        template = registry.get("pytest_test")
        assert template.template_type == TemplateType.TEST
        assert "test_name" in template.required_vars

    def test_get_pydantic_model_template(self):
        """获取 Pydantic 模型模板"""
        registry = create_template_registry()
        template = registry.get("pydantic_model")
        assert template.template_type == TemplateType.MODEL

    def test_get_yaml_config_template(self):
        """获取 YAML 配置模板"""
        registry = create_template_registry()
        template = registry.get("yaml_config")
        assert template.template_type == TemplateType.CONFIG
        assert template.language == "yaml"


class TestDefaultTemplates:
    """测试预定义模板"""

    def test_python_function_rendering(self):
        """Python 函数模板渲染"""
        registry = create_template_registry()
        result = registry.render("python_function", {
            "function_name": "add_numbers",
            "params": "a, b",
            "description": "Add two numbers",
            "args_doc": "a: First number\nb: Second number",
            "return_doc": "Sum of a and b",
            "body": "return a + b",
            "return_value": "a + b",
        })
        assert "def add_numbers(a, b):" in result
        assert "Add two numbers" in result
        assert "return a + b" in result

    def test_python_class_rendering(self):
        """Python 类模板渲染"""
        registry = create_template_registry()
        result = registry.render("python_class", {
            "class_name": "User",
            "description": "User class",
            "init_params": ", name, age",
            "init_body": "        self.name = name\n        self.age = age",
        })
        assert "class User:" in result
        assert "User class" in result
        assert "def __init__(self, name, age):" in result

    def test_fastapi_endpoint_rendering(self):
        """FastAPI 端点模板渲染"""
        registry = create_template_registry()
        result = registry.render("fastapi_endpoint", {
            "method": "get",
            "path": "/api/v1/users/{user_id}",
            "function_name": "get_user",
            "params": "user_id: str",
            "description": "Get user by ID",
            "body": "# Retrieve user",
            "return_value": '{"user": user_data}',
        })
        assert "@router.get" in result
        assert "/api/v1/users/{user_id}" in result
        assert "def get_user(user_id: str):" in result

    def test_pytest_test_rendering(self):
        """Pytest 测试模板渲染"""
        registry = create_template_registry()
        result = registry.render("pytest_test", {
            "test_name": "add_numbers",
            "params": "",
            "description": "Test addition",
            "arrange": "a = 1\nb = 2",
            "act": "result = add_numbers(a, b)",
            "assertion": "result == 3",
        })
        assert "def test_add_numbers():" in result
        assert "# Arrange" in result
        assert "# Act" in result
        assert "# Assert" in result
        assert "assert result == 3" in result


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_template_registry(self):
        """创建模板注册中心"""
        registry = create_template_registry()
        assert isinstance(registry, TemplateRegistry)