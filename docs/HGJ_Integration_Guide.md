# HGJ 模块引入指南

**版本**: v1.4.4  
**日期**: 2026-04-11

---

## 一、新项目如何正确高效引入 HGJ 模块

### 1. 安装方式

```bash
# 方式一：从 GitHub 安装（推荐）
pip install git+https://github.com/qbiong/HarnessGenJ.git

# 方式二：本地安装
git clone https://github.com/qbiong/HarnessGenJ.git
cd HarnessGenJ
pip install -e .
```

### 2. 新项目引入步骤

#### Step 1: 创建项目目录结构

```bash
mkdir my_project
cd my_project

# 创建 HGJ 工作目录
mkdir -p .harnessgenj/documents
mkdir -p .harnessgenj/agents
mkdir -p .harnessgenj/knowledge
```

#### Step 2: 创建 CLAUDE.md（项目级指令）

```markdown
# My Project 开发规范

> 此文件为 Claude Code 项目级指令

## 🎯 HGJ 框架触发词

当用户消息包含以下触发词时，必须立即执行框架初始化：

| 触发词 | 立即执行 |
|--------|----------|
| "使用HGJ框架" | ✅ 初始化框架 |
| "HGJ开发" | ✅ 初始化框架 |
| "HGJ修复" | ✅ 初始化框架 |

## 🚀 框架初始化代码

```python
from harnessgenj import Harness

# 初始化框架
harness = Harness.from_project(".")

# 显示状态
status = harness.get_status()
print(f"项目: {status['project']}")
print(f"团队: {status['team']['size']} 个角色")
```

## ⚠️ 强制规则

**所有代码修改必须通过框架执行：**

```python
# 开发功能
result = harness.develop("功能描述")
harness.complete_task(result['task_id'], "摘要")

# 修复 Bug
result = harness.fix_bug("问题描述")
harness.complete_task(result['task_id'], "摘要")
```

**禁止跳过框架直接编码**
```

#### Step 3: 创建 .harnessgenj/project.json

```json
{
  "name": "my_project",
  "description": "项目描述",
  "workspace": ".",
  "tech_stack": ["Python", "FastAPI"],
  "team": {
    "size": 8,
    "roles": ["developer", "code_reviewer", "bug_hunter", "tester", "project_manager"]
  }
}
```

#### Step 4: 初始化框架（首次运行）

```python
from harnessgenj import Harness

# 方式一：从项目目录初始化（推荐）
harness = Harness.from_project(".")

# 方式二：手动创建
harness = Harness(
    project_name="my_project",
    workspace_path=".",
    tech_stack=["Python", "FastAPI"],
)

# 初始化 Hooks（可选，用于强制阻止未授权操作）
harness.setup_hooks()
```

---

## 二、HGJ 与 Claude Code 原生多智能体模块的关系

### 核心结论：**无冲突，互补增强**

| 特性 | HGJ 模块 | Claude Code 原生 | 关系 |
|------|----------|------------------|------|
| **Agent 概念** | 角色（Developer/Reviewer 等） | Agent 类型（general-purpose 等） | HGJ 提供更细粒度角色 |
| **上下文隔离** | Python contextvars | TypeScript AsyncLocalStorage | 技术栈不同，不冲突 |
| **协作模式** | 工作流驱动 + GAN 对抗 | 直接 Agent 调用 | HGJ 提供结构化流程 |
| **记忆管理** | JVM 分代记忆 | 内存/Session | HGJ 提供持久化 |
| **质量保证** | GAN 对抗 + 积分激励 | 无内置机制 | HGJ 提供质量门禁 |

### 详细对比分析

#### 1. 架构层面：互补而非冲突

**HGJ 是 Claude Code 的增强层**，而非替代：

```
┌─────────────────────────────────────────────────────┐
│                 Claude Code 原生                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│   │  Agent   │  │  Tools   │  │  Hooks   │         │
│   └──────────┘  └──────────┘  └──────────┘         │
│                        ↓                             │
│   ┌─────────────────────────────────────────┐       │
│   │           HGJ Enhancement Layer          │       │
│   ├─────────────────────────────────────────┤       │
│   │ • 角色驱动协作（8个角色）                 │       │
│   │ • JVM 分代记忆管理                       │       │
│   │ • GAN 对抗质量保证                       │       │
│   │ • 工作流驱动执行                         │       │
│   │ • Hooks 强制权限检查                     │       │
│   └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

#### 2. 技术层面：独立运行

| 层面 | HGJ | Claude Code | 交互方式 |
|------|-----|-------------|----------|
| **语言** | Python | TypeScript/Node | 通过 MCP Server 通信 |
| **运行环境** | Python 进程 | Node 进程 | 独立进程，不冲突 |
| **数据存储** | `.harnessgenj/` | `.claude/` | 不同目录，不冲突 |
| **Hooks** | `.claude/hooks/` | 原生 Hooks | HGJ 挂载到原生 Hooks |

#### 3. 功能层面：增强而非覆盖

**HGJ 不覆盖 Claude Code 原生功能**：

- Claude Code 原生 Agent：用于通用任务（搜索、读取、写入）
- HGJ 角色：用于开发特定任务（编码、审查、测试）

**协同工作示例**：

```python
# Claude Code 原生 Agent 执行基础操作
# HGJ 角色执行开发任务

# 1. HGJ 签发操作许可
result = harness.develop("实现用户登录")

# 2. Claude Code 原生 Agent 在许可范围内执行
# （通过 MCP 工具或直接 Python 调用）

# 3. HGJ 执行质量检查
harness.complete_task(result['task_id'], "摘要")
```

---

## 三、高效引入最佳实践

### 推荐流程

```
┌──────────────────────────────────────────────────────────┐
│ Step 1: 项目初始化                                        │
│   • 创建 .harnessgenj/ 目录                               │
│   • 创建 CLAUDE.md（项目级指令）                           │
│   • 创建 project.json（项目配置）                          │
├──────────────────────────────────────────────────────────┤
│ Step 2: 框架初始化                                        │
│   • Harness.from_project(".")                            │
│   • setup_hooks()（可选，强制权限检查）                    │
├──────────────────────────────────────────────────────────┤
│ Step 3: 开发工作流                                        │
│   • harness.develop("描述") → 签发许可                    │
│   • 执行指令 → 编写代码                                   │
│   • harness.complete_task() → 质量检查                   │
├──────────────────────────────────────────────────────────┤
│ Step 4: 持续使用                                          │
│   • 会话恢复时自动加载框架状态                             │
│   • Hooks 自动检查权限                                    │
│   • 积分系统持续激励                                       │
└──────────────────────────────────────────────────────────┘
```

### 一句话启动模板

**用户只需说**："使用HGJ框架"

**AI 自动执行**：

```python
from harnessgenj import Harness

harness = Harness.from_project(".")
status = harness.get_status()

print(f"""
✅ HGJ框架已就绪
   项目: {status['project']}
   团队: {status['team']['size']} 个角色

📋 您可以直接说：
   - "实现XXX功能"
   - "修复XXX问题"

💡 框架会自动：
   - 签发操作许可
   - 执行质量检查
""")
```

---

## 四、冲突风险评估

### ✅ 无冲突场景

| 场景 | 说明 |
|------|------|
| HGJ + Claude Code 原生 Agent | 互补增强，不冲突 |
| HGJ Hooks + Claude Code Hooks | HGJ 挂载到原生 Hooks，协同工作 |
| HGJ MCP Server + Claude Code MCP | 可以同时使用多个 MCP Server |
| HGJ 角色 + Claude Code Agent 类型 | 不同抽象层次，不冲突 |

### ⚠️ 需注意场景

| 场景 | 说明 | 建议 |
|------|------|------|
| 同时使用多个框架 | 可能混淆 | 在 CLAUDE.md 中明确指定优先级 |
| Hooks 返回值冲突 | 多个 Hooks 可能冲突 | HGJ Hooks 返回 1 时阻止，其他 Hooks 应返回 0 |
| 会话压缩后状态丢失 | 可能忘记框架 | HGJ 使用 framework_state.md 持久化 |

---

## 五、总结

### 核心结论

1. **HGJ 可以正确高效引入新项目**：
   - 创建 `.harnessgenj/` 目录
   - 创建 CLAUDE.md（项目级指令）
   - 一句话启动："使用HGJ框架"

2. **HGJ 与 Claude Code 原生多智能体模块无冲突**：
   - HGJ 是增强层，而非替代
   - 技术栈独立（Python vs TypeScript）
   - 功能互补而非覆盖

3. **推荐使用方式**：
   - HGJ 用于开发任务（编码、审查、测试）
   - Claude Code 原生 Agent 用于通用任务（搜索、读取）
   - Hooks 协同工作（HGJ 挂载到原生 Hooks）

---

**文档版本**: v1.4.4  
**更新日期**: 2026-04-11