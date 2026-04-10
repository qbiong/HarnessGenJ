# 代码约定

> 此文件由 HarnessGenJ 自动生成，根据技术栈自动适配
> 请遵循项目既有的代码风格

## 编码风格

- 遵循 PEP 8 规范
- 使用类型注解（Type Hints）
- 函数名使用 snake_case
- 类名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE

## 代码组织

- 使用模块化设计
- 每个 module 应有明确的职责
- 使用 `__init__.py` 导出公共 API

## 文档

- 函数必须有文档字符串（docstring）
- 使用 Google 或 NumPy 风格的 docstring
- 复杂逻辑需要注释说明

## 类型检查

- 推荐使用 mypy 进行静态类型检查
- 使用 `typing` 模块的泛型类型

## 测试约定

- 所有新功能需要添加测试
- 测试文件放在 `test/` 或 `tests/` 目录
- 测试函数名应描述测试场景
- 使用 AAA 模式（Arrange-Act-Assert）

推荐使用: pytest
