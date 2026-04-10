# 技术栈 - HarnessGenJ 项目

> 此文件由 HarnessGenJ 自动检测和维护

## 主要语言

- **Python 3.11+**

## 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Pydantic | 2.x | 数据验证和模型定义 |
| pytest | 8.x | 测试框架 |
| pytest-cov | 5.x | 测试覆盖率 |

## 架构模式

### 分层架构

```
┌─────────────────────────────────────┐
│           Engine (入口)              │
├─────────────────────────────────────┤
│  Roles │ Workflow │ Memory │ Quality │
├─────────────────────────────────────┤
│           Harness Core               │
├─────────────────────────────────────┤
│   MCP Server │ Notify │ Storage      │
└─────────────────────────────────────┘
```

### 核心模块

1. **engine.py** - 主入口，Harness 类
2. **roles/** - 角色定义（Developer、CodeReviewer、BugHunter 等）
3. **workflow/** - 工作流系统（Pipeline、Coordinator）
4. **memory/** - JVM 风格分代记忆管理
5. **quality/** - 质量保证（积分、对抗审查）
6. **harness/** - 框架核心组件
7. **mcp/** - MCP Server 实现
8. **notify/** - 用户通知模块

## 关键设计模式

### GAN 对抗机制

```
Developer (生成器) → CodeReviewer/BugHunter (判别器) → 反馈修复
```

### JVM 风格记忆管理

```
Eden (短期) → Survivor (中期) → Old (长期) → Permanent (永久)
```

### 操作指令协议

```
harness.develop() → OperationInstruction → AI 执行 → complete_task()
```

## 开发环境

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 类型检查
mypy src/harnessgenj/

# 代码格式化
ruff format src/
```

## 版本管理

- 遵循语义化版本（SemVer）
- 版本号存储位置：
  - `pyproject.toml`: `version = "x.y.z"`
  - `src/harnessgenj/__init__.py`: `__version__ = "x.y.z"`
- 每次发布更新 `CHANGELOG.md`

---
*此文件由 HarnessGenJ 自动维护 - 自举模式*