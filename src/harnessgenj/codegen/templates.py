"""
Code Templates - 代码模板库

提供代码模板定义和管理：
- 预定义模板
- 变量替换
- 模板注册
- 自定义模板
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import re


class TemplateType(Enum):
    """模板类型"""

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    TEST = "test"
    API_ENDPOINT = "api_endpoint"
    MODEL = "model"
    CONFIG = "config"
    CUSTOM = "custom"


class CodeTemplate(BaseModel):
    """代码模板"""

    name: str = Field(..., description="模板名称")
    template_type: TemplateType = Field(default=TemplateType.CUSTOM, description="模板类型")
    description: str = Field(default="", description="模板描述")
    template: str = Field(..., description="模板内容")
    variables: dict[str, str] = Field(default_factory=dict, description="变量定义 {变量名: 默认值}")
    required_vars: list[str] = Field(default_factory=list, description="必需变量")
    tags: list[str] = Field(default_factory=list, description="标签")
    language: str = Field(default="python", description="编程语言")

    def render(self, variables: dict[str, Any] | None = None) -> str:
        """
        渲染模板

        Args:
            variables: 变量值字典

        Returns:
            渲染后的代码
        """
        variables = variables or {}

        # 合并默认值
        final_vars = {**self.variables, **variables}

        # 检查必需变量
        missing = [v for v in self.required_vars if v not in final_vars]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # 执行替换
        result = self.template
        for var_name, var_value in final_vars.items():
            # 支持 ${var} 和 {{var}} 两种格式
            result = result.replace(f"${{{var_name}}}", str(var_value))
            result = result.replace(f"{{{{{var_name}}}}}", str(var_value))

        return result

    def validate_output(self, output: str) -> tuple[bool, list[str]]:
        """
        验证输出代码

        Args:
            output: 生成的代码

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 检查是否还有未替换的变量
        remaining_vars = re.findall(r'\$\{(\w+)\}|\{\{(\w+)\}\}', output)
        if remaining_vars:
            errors.append(f"Unresolved variables: {remaining_vars}")

        # 基本语法检查（对于 Python）
        if self.language == "python":
            try:
                compile(output, "<template>", "exec")
            except SyntaxError as e:
                errors.append(f"Syntax error: {e.msg}")

        return len(errors) == 0, errors


class TemplateRegistry:
    """
    模板注册中心

    管理所有代码模板
    """

    def __init__(self) -> None:
        self._templates: dict[str, CodeTemplate] = {}
        self._by_type: dict[TemplateType, list[str]] = {t: [] for t in TemplateType}

        # 加载默认模板
        self._load_defaults()

    def _load_defaults(self) -> None:
        """加载默认模板"""
        # Python 函数模板
        self.register(CodeTemplate(
            name="python_function",
            template_type=TemplateType.FUNCTION,
            description="Python 函数模板",
            template='''def ${function_name}(${params}):
    """
    ${description}

    Args:
        ${args_doc}

    Returns:
        ${return_doc}
    """
    ${body}
    return ${return_value}
''',
            variables={
                "function_name": "my_function",
                "params": "",
                "description": "函数描述",
                "args_doc": "",
                "return_doc": "返回值",
                "body": "pass",
                "return_value": "None",
            },
            required_vars=["function_name"],
            tags=["python", "function"],
            language="python",
        ))

        # Python 类模板
        self.register(CodeTemplate(
            name="python_class",
            template_type=TemplateType.CLASS,
            description="Python 类模板",
            template='''class ${class_name}:
    """
    ${description}
    """

    def __init__(self${init_params}):
        """初始化"""
        ${init_body}

    def ${method_name}(self${method_params}):
        """${method_description}"""
        ${method_body}
''',
            variables={
                "class_name": "MyClass",
                "description": "类描述",
                "init_params": "",
                "init_body": "pass",
                "method_name": "my_method",
                "method_params": "",
                "method_description": "方法描述",
                "method_body": "pass",
            },
            required_vars=["class_name"],
            tags=["python", "class"],
            language="python",
        ))

        # FastAPI 端点模板
        self.register(CodeTemplate(
            name="fastapi_endpoint",
            template_type=TemplateType.API_ENDPOINT,
            description="FastAPI API 端点模板",
            template='''@router.${method}("${path}")
async def ${function_name}(${params}):
    """
    ${description}
    """
    ${body}
    return ${return_value}
''',
            variables={
                "method": "get",
                "path": "/api/v1/resource",
                "function_name": "get_resource",
                "params": "",
                "description": "API 端点描述",
                "body": "# 实现逻辑",
                "return_value": '{"status": "ok"}',
            },
            required_vars=["path", "function_name"],
            tags=["python", "fastapi", "api"],
            language="python",
        ))

        # Pydantic 模型模板
        self.register(CodeTemplate(
            name="pydantic_model",
            template_type=TemplateType.MODEL,
            description="Pydantic 数据模型模板",
            template='''class ${model_name}(BaseModel):
    """
    ${description}
    """

    ${fields}

    class Config:
        ${config}
''',
            variables={
                "model_name": "MyModel",
                "description": "数据模型描述",
                "fields": "id: int = Field(..., description='ID')",
                "config": "from_attributes = True",
            },
            required_vars=["model_name"],
            tags=["python", "pydantic", "model"],
            language="python",
        ))

        # 测试模板
        self.register(CodeTemplate(
            name="pytest_test",
            template_type=TemplateType.TEST,
            description="Pytest 测试函数模板",
            template='''def test_${test_name}(${params}):
    """
    ${description}
    """
    # Arrange
    ${arrange}

    # Act
    ${act}

    # Assert
    assert ${assertion}
''',
            variables={
                "test_name": "my_feature",
                "params": "",
                "description": "测试描述",
                "arrange": "# 准备测试数据",
                "act": "# 执行被测试的操作",
                "assertion": "True",
            },
            required_vars=["test_name"],
            tags=["python", "pytest", "test"],
            language="python",
        ))

        # 配置文件模板
        self.register(CodeTemplate(
            name="yaml_config",
            template_type=TemplateType.CONFIG,
            description="YAML 配置文件模板",
            template='''# ${config_name} Configuration

app:
  name: ${app_name}
  version: ${version}
  debug: ${debug}

database:
  host: ${db_host}
  port: ${db_port}
  name: ${db_name}

logging:
  level: ${log_level}
  format: ${log_format}
''',
            variables={
                "config_name": "Application",
                "app_name": "my_app",
                "version": "1.0.0",
                "debug": "false",
                "db_host": "localhost",
                "db_port": "5432",
                "db_name": "mydb",
                "log_level": "INFO",
                "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            required_vars=["app_name"],
            tags=["yaml", "config"],
            language="yaml",
        ))

    def register(self, template: CodeTemplate) -> bool:
        """注册模板"""
        if template.name in self._templates:
            return False

        self._templates[template.name] = template
        self._by_type[template.template_type].append(template.name)
        return True

    def unregister(self, name: str) -> bool:
        """注销模板"""
        if name not in self._templates:
            return False

        template = self._templates[name]
        self._by_type[template.template_type].remove(name)
        del self._templates[name]
        return True

    def get(self, name: str) -> CodeTemplate | None:
        """获取模板"""
        return self._templates.get(name)

    def list_templates(
        self,
        template_type: TemplateType | None = None,
        tags: list[str] | None = None,
    ) -> list[CodeTemplate]:
        """列出模板"""
        if template_type:
            names = self._by_type.get(template_type, [])
            templates = [self._templates[n] for n in names if n in self._templates]
        else:
            templates = list(self._templates.values())

        # 标签过滤
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        return templates

    def render(self, name: str, variables: dict[str, Any] | None = None) -> str:
        """渲染模板"""
        template = self.get(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        return template.render(variables)


# ==================== 便捷函数 ====================

def create_template_registry() -> TemplateRegistry:
    """创建模板注册中心"""
    return TemplateRegistry()