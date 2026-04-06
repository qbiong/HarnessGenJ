# HarnessGenJ (HGJ) - Harness Engineering with JVM-style Generational Memory

<div align="center">

**Harness Engineering + JVM 分代记忆 + GAN 对抗机制的 AI Agent 协作框架**

通过**角色驱动**和**工作流驱动**实现高效的开发协作

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-660%20passed-green.svg)](tests/)

</div>

---

## 目录

- [核心理念](#核心理念)
- [核心亮点：GAN对抗机制](#核心亮点gan对抗机制)
- [安装方式](#安装方式)
- [首次接入流程](#首次接入流程)
- [快速开始](#快速开始)
- [从现有项目初始化](#从现有项目初始化)
- [核心功能](#核心功能)
- [JVM风格记忆管理](#jvm风格记忆管理)
- [项目结构](#项目结构)
- [更新日志](#更新日志)

---

## 核心理念

### 为什么选择 HarnessGenJ？

HarnessGenJ 将软件工程团队的最佳实践引入 AI Agent 开发，让 AI 像真实团队一样协作：

| 传统方式 | HarnessGenJ 方式 |
|----------|-----------|
| 抽象的 Agent 概念 | 真实团队角色（开发、测试、产品等） |
| 难以追踪的任务 | 完整的工作流和阶段 |
| 混乱的记忆管理 | JVM 风格的分代记忆系统 |
| 复杂的数据库配置 | 轻量化存储，开箱即用 |
| Token 消耗过大 | 渐进式披露，按需加载 |
| 无持久化 | 自动持久化，重启恢复 |
| 质量无法保证 | GAN 对抗机制确保代码质量 |

### 角色驱动协作

每个角色有明确的职责和技能集：

| 角色 | 职责 | 核心技能 | 类型 |
|------|------|----------|------|
| **ProductManager** | 需求管理 | 需求分析、用户故事、验收标准、优先级排序 | 生成器 |
| **Architect** | 架构设计 | 系统设计、技术选型、架构评审、设计模式 | 生成器 |
| **Developer** | 功能开发 | 编码实现、Bug修复、代码重构、代码审查 | 生成器 |
| **Tester** | 质量保证 | 测试编写、测试执行、Bug报告、覆盖率分析 | 生成器 |
| **DocWriter** | 文档管理 | 技术文档、API文档、用户手册、知识库维护 | 生成器 |
| **ProjectManager** | 项目协调 | 任务协调、进度追踪、资源分配、风险管理 | 协调者 |
| **CodeReviewer** | 代码审查 | 代码质量审查、问题检测、规范检查、安全扫描 | 判别器 |
| **BugHunter** | 漏洞猎手 | 漏洞探测、边界攻击、安全测试、负向测试 | 判别器 |

---

## 核心亮点：GAN对抗机制

### 设计理念

借鉴生成对抗网络（GAN）的思想，HarnessGenJ 实现了**生成器-判别器对抗机制**：

```
┌─────────────────────────────────────────────────────────────┐
│                    GAN 对抗审查流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐    产出    ┌──────────┐                      │
│   │  生成器   │ ─────────→ │  判别器   │                      │
│   │ (Developer)│           │(Reviewer)│                      │
│   └──────────┘    问题    └──────────┘                      │
│        ↑                      │                              │
│        │       ┌──────────────┘                              │
│        │       │                                              │
│        └───────┘  修复 & 再审查                               │
│                                                             │
│   多轮对抗直到通过或达到最大轮次                               │
└─────────────────────────────────────────────────────────────┘
```

### 双层对抗架构

**任务级对抗**：单次开发的生成-审查-修复循环

```python
result = harness.adversarial_develop(
    feature_request="实现用户认证模块",
    max_rounds=3,
    intensity="normal",  # 或 "aggressive" 使用 BugHunter
)
# 返回: success, rounds, quality_score, issues_found, issues_fixed
```

**系统级对抗**：跨任务模式识别与持续改进

```python
analysis = harness.get_system_analysis()
# 返回: 
# - generator_weaknesses: 生成器薄弱点
# - discriminator_biases: 判别器偏差
# - system_health_score: 系统健康度
# - improvement_actions: 改进建议
```

### 质量数据驱动记忆管理

对抗审查结果直接影响记忆条目的生命周期：

```
对抗审查完成
    ↓
计算质量分数 (0-100)
    ↓
更新 MemoryEntry:
  - quality_score: 质量分数
  - review_count: 审查次数
  - generator_id: 生成者ID
  - discriminator_id: 审查者ID
    ↓
质量感知 GC:
  - 高质量 (≥70): 优先存活
  - 低质量 (<30): 优先回收
```

### 双向积分激励

公平的积分机制确保生成器和判别器都能发挥作用：

| 行为 | 生成器积分 | 判别器积分 |
|------|-----------|-----------|
| 一轮通过审查 | +10 | - |
| 二轮通过 | +5 | - |
| 发现关键问题 | -10 | +10 |
| 发现中等问题 | -5 | +5 |
| 误报问题 | +3 | -3 |
| 漏掉关键问题 | - | -15 |
| 生产环境 Bug | -20 | - |

---

## 安装方式

```bash
# 从 PyPI 安装（发布后）
pip install harnessgenj

# 从源码安装
git clone https://github.com/qbiong/HarnessGenJ.git
cd harnessgenj
pip install -e .

# 开发模式（包含测试工具）
pip install -e ".[dev]"
```

---

## 首次接入流程

**重要**: 项目首次引入 HarnessGenJ 时，需要通过对话方式完成初始化和角色激活。

### 接入流程概览

```
步骤 1: 启用 HarnessGenJ     →  AI 读取项目文档，完成初始化
步骤 2: 激活项目经理   →  AI 进入项目经理角色
步骤 3: 持续对话推进   →  用户直接对话项目经理推进项目
```

### 步骤 1: 启用 HarnessGenJ

在 Claude Code 对话中发送以下提示词：

```
请启用 HarnessGenJ 框架协助本项目的开发。

执行以下初始化步骤：
1. 读取项目文档（README.md、requirements.md 等）
2. 初始化 HarnessGenJ：
   from harnessgenj import Harness
   harness = Harness.from_project(".")
   print(harness.get_init_prompt())
3. 确认 `.harnessgenj/` 目录已创建

完成后汇报：项目名称、技术栈、已导入文档、当前状态。
```

### 步骤 2: 激活项目经理角色

初始化完成后，发送以下提示词让 AI 进入项目经理角色：

```
我现在要求你按照 HarnessGenJ 框架规范，进入项目经理角色。

作为项目经理，你需要：

【核心职责】
1. 作为用户与开发团队的唯一对接窗口
2. 接收所有用户请求，自动识别意图并分配任务
3. 维护项目文档（requirements、design、development、testing、progress）
4. 调度其他角色（产品经理、架构师、开发者、测试员）执行任务
5. 追踪任务进度，确认任务完成

【工作规范】
- 每次对话开始时，调用 harness.get_init_prompt() 获取上下文
- 用户提出需求 → 调用 harness.receive_request()
- 用户要求开发 → 调用 harness.develop()
- 用户报告 Bug → 调用 harness.fix_bug()
- 用户询问状态 → 调用 harness.get_status()

【回复格式】
每次回复需包含：任务识别、处理动作、任务分配、下一步计划

现在请确认进入项目经理角色，并汇报当前项目状态。
```

### 简化版提示词（快速激活）

| 场景 | 提示词 |
|------|--------|
| 启用 HarnessGenJ | `启用 HarnessGenJ 框架。执行 Harness.from_project(".") 初始化，汇报项目状态。` |
| 激活项目经理 | `进入 HarnessGenJ 项目经理角色。作为用户对接窗口，接收请求、分配任务、调度角色、追踪进度。确认并汇报当前状态。` |

### 持续对话推进

激活项目经理后，用户可直接对话推进项目：

| 用户说 | 项目经理响应 |
|--------|--------------|
| "我需要一个登录功能" | 创建任务 TASK-xxx，分配 P1，负责人 developer |
| "有个 Bug：支付超时" | 创建任务 TASK-xxx，分配 P0，负责人 developer |
| "帮我开发购物车" | 调度开发流程：需求→设计→开发→测试 |
| "项目进展如何" | 汇报当前进度、已完成任务、活动任务 |

详细说明请参阅 [首次接入指南](docs/ONBOARDING_GUIDE.md)。

---

## 快速开始

### 方式一：直接创建（新项目）

```python
from harnessgenj import Harness

# 创建项目（默认持久化到 .harnessgenj/ 目录）
harness = Harness("我的项目")

# 存储核心知识
harness.remember("tech_stack", "Python + FastAPI", important=True)

# 接收需求
result = harness.receive_request("实现用户登录功能")
print(f"任务ID: {result['task_id']}")  # TASK-xxx
print(f"优先级: {result['priority']}")  # P1

# 获取上下文（用于 Claude Code 对话）
context = harness.get_init_prompt()
```

### 方式二：从现有项目初始化（推荐）

如果你已经有项目文档（README.md、requirements.md 等），可以直接导入：

```python
from harnessgenj import Harness

# 从项目目录初始化（自动扫描并导入文档）
harness = Harness.from_project("/path/to/your/project")

# 自动完成：
# - 提取项目名称和描述
# - 识别技术栈
# - 导入需求文档、设计文档等
# - 生成完整的项目上下文

# 获取初始化提示
init_prompt = harness.get_init_prompt()
print(init_prompt)  # 包含：API指南 + 项目信息 + 文档内容 + 当前任务
```

### Claude Code 对话初始化

每次新对话开始时：

```python
from harnessgenj import Harness

# 初始化（自动恢复之前的工作）
harness = Harness("我的项目")

# 获取上下文提示（注入到对话中）
init_prompt = harness.get_init_prompt()

# 之后正常对话
harness.chat("我需要一个购物车功能")  # 自动识别并创建任务
```

### 用户对话自动处理

| 用户说 | AI 调用 | 自动处理 |
|--------|---------|----------|
| "我需要/要/添加功能" | `receive_request("...", "feature")` | 创建任务、分配P1、记录文档 |
| "有bug/问题/错误" | `receive_request("...", "bug")` | 创建任务、分配P0、记录文档 |
| "帮我开发" | `develop("...")` | 执行开发流程 |
| "帮我修复" | `fix_bug("...")` | 执行修复流程 |
| "项目进展如何" | `get_status()` | 返回项目状态 |

---

## 从现有项目初始化

### `Harness.from_project()` 功能

自动扫描项目文档并导入到记忆系统：

```python
harness = Harness.from_project("/path/to/project")
```

### 自动识别的文档

| 文件名 | 导入到 |
|--------|--------|
| README.md | 项目名称、描述、技术栈提取 |
| requirements.md / 需求.md | requirements 文档 |
| design.md / 设计.md | design 文档 |
| development.md / 开发.md | development 文档 |
| testing.md / 测试.md | testing 文档 |
| progress.md / 进度.md | progress 文档 |
| docs/*.md | 核心知识存储 |

### 自动检测的技术栈

- **语言**: Python, Node.js, Go, Rust, Java
- **框架**: FastAPI, Django, Flask, React, Vue
- **数据库**: PostgreSQL, MySQL, MongoDB, Redis
- **部署**: Docker

### 完整示例

```python
# 假设项目目录：
# my-project/
# ├── README.md           # 项目说明
# ├── requirements.md     # 需求文档
# ├── design.md           # 设计文档
# └── pyproject.toml      # Python 配置

from harnessgenj import Harness

# 一行代码完成初始化
harness = Harness.from_project("my-project")

# 查看导入结果
print(harness.project_name)           # 从 README 标题提取
print(harness.recall("tech_stack"))   # 自动检测的技术栈
print(harness.memory.get_document("requirements"))  # 需求文档

# 开始开发
harness.receive_request("实现购物车功能")
```

---

## 核心功能

### 1. 接收用户请求

```python
# 接收功能需求
result = harness.receive_request("实现用户登录功能", request_type="feature")
# 返回: {"task_id": "TASK-xxx", "priority": "P1", "assignee": "developer"}

# 接收 Bug 报告
result = harness.receive_request("登录页面报错", request_type="bug")
# 返回: {"task_id": "TASK-xxx", "priority": "P0", ...}
```

### 2. 记忆管理

```python
# 存储核心知识（Permanent 区，永不回收）
harness.remember("project_goal", "构建电商平台", important=True)

# 回忆知识
goal = harness.recall("project_goal")

# 记录到文档
harness.record("完成了用户认证模块", context="开发进度")
```

### 3. 对话记录

```python
# 用户消息（自动识别需求/Bug）
harness.chat("我需要一个搜索功能")

# AI 回复
harness.chat("好的，我来实现搜索模块", role="assistant")
```

### 4. 任务完成

```python
# 标记任务完成
harness.complete_task("TASK-xxx", "功能已完成，测试通过")
```

### 5. 状态查询

```python
# 获取项目状态
status = harness.get_status()
# 包含：项目信息、团队、统计、记忆状态、当前任务

# 获取项目报告
report = harness.get_report()
```

### 6. 对抗性质量保证（核心特性）

基于 GAN 思想的生成器-判别器对抗机制，**默认启用**：

```python
# 对抗性开发（多轮审查直到通过）
result = harness.adversarial_develop(
    feature_request="实现用户认证模块",
    max_rounds=3,           # 最大对抗轮次
    use_hunter=False,       # 是否使用 BugHunter（激进审查）
)
# 返回: {"success": True, "rounds": 2, "quality_score": 85.0, ...}

# 快速审查（单轮）
passed, issues = harness.quick_review(code)

# 使用 BugHunter 进行激进审查
passed, issues = harness.quick_review(code, use_hunter=True)

# 获取质量报告
report = harness.get_quality_report()
# 包含: 成功率、平均轮次、问题分布、失败模式

# 获取积分排行榜
leaderboard = harness.get_score_leaderboard()

# 系统级分析（跨任务模式识别）
analysis = harness.get_system_analysis()
# 包含: generator_weaknesses, discriminator_biases, improvement_actions
```

### 7. 积分与绩效

双向激励机制确保公平性，详见 [双向积分激励](#双向积分激励) 表格。

```python
# 查看角色积分
score = harness.get_role_score("developer_1")
# {"score": 85, "grade": "B", "success_rate": 0.85}
```

---

## JVM风格记忆管理

### 分代存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                     JVM 风格记忆堆                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Permanent 区（永久代）                      │   │
│  │  项目核心信息、重要知识 - 永不回收                       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Old 区（老年代）                          │   │
│  │  长期存活记忆、设计文档 - Major GC 清理                 │   │
│  │  ★ 质量感知：高质量内容优先存活                         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌───────────────────┐    ┌───────────────────┐           │
│  │   Survivor 区     │ ←→ │   Survivor 区     │           │
│  │  活跃文档、需求    │    │   GC 交换区       │           │
│  └───────────────────┘    └───────────────────┘           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Eden 区（新生代）                        │   │
│  │  新消息、临时内容 - Minor GC 频繁清理                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 质量感知 GC

记忆条目的存活判定考虑质量分数：

- **高质量 (quality_score ≥ 70)**：优先存活
- **中等质量 (30-70)**：综合判定
- **低质量 (< 30)**：优先回收（除非高引用或高重要性）

### 渐进式披露

每个角色只获取最小必要上下文：

```python
# 开发者上下文：项目信息 + 需求摘要 + 设计摘要
dev_context = harness.memory.get_context_for_role("developer")

# 项目经理上下文：所有文档完整内容
pm_context = harness.memory.get_context_for_role("project_manager")

# 代码审查者上下文：开发文档完整 + 质量历史
reviewer_context = harness.memory.get_context_for_role("code_reviewer")
```

---

## 项目结构

```
HarnessGenJ/
├── src/harnessgenj/
│   ├── engine.py              # 主入口 Harness 类
│   ├── session.py             # 多会话管理
│   ├── guide.py               # 首次使用引导
│   │
│   ├── roles/                 # 角色系统
│   │   ├── base.py           # 角色基类 + RoleType 枚举
│   │   ├── developer.py      # 开发者（生成器）
│   │   ├── tester.py         # 测试员（生成器）
│   │   ├── product_manager.py # 产品经理（生成器）
│   │   ├── architect.py      # 架构师（生成器）
│   │   ├── doc_writer.py     # 文档编写者（生成器）
│   │   ├── project_manager.py # 项目经理（协调者）
│   │   ├── code_reviewer.py  # 代码审查者（判别器）
│   │   └── bug_hunter.py     # 漏洞猎手（判别器）
│   │
│   ├── workflow/               # 工作流系统
│   │   ├── pipeline.py       # 流水线定义 + 对抗流水线 + 依赖图集成
│   │   ├── coordinator.py    # 角色调度器
│   │   ├── context.py        # 工作流上下文
│   │   ├── collaboration.py  # 角色协作管理器
│   │   ├── message_bus.py    # 消息传递总线
│   │   ├── dependency.py     # 任务依赖图（循环检测、拓扑排序）
│   │   ├── tdd_workflow.py   # TDD 工作流
│   │   └── requirement_stage.py # 需求检测阶段
│   │
│   ├── memory/                # JVM风格记忆管理
│   │   ├── manager.py        # 记忆管理器 + 质量集成
│   │   ├── heap.py           # 分代堆 + 质量字段
│   │   ├── gc.py             # 垃圾回收 + 质量感知GC
│   │   └── hotspot.py        # 热点检测
│   │
│   ├── maintenance/           # 主动文档维护
│   │   ├── detector.py       # 需求检测器
│   │   ├── confirmation.py   # 确认机制管理器
│   │   └── manager.py        # 文档维护管理器
│   │
│   ├── quality/               # 质量保证系统
│   │   ├── score.py          # 积分管理器
│   │   ├── record.py         # 问题记录、对抗记录
│   │   ├── tracker.py        # 质量追踪、失败模式分析
│   │   ├── task_adversarial.py   # 任务级对抗控制器
│   │   └── system_adversarial.py # 系统级对抗控制器
│   │
│   ├── codegen/               # 代码生成辅助
│   │   ├── templates.py      # 代码模板库
│   │   └── generator.py      # 代码生成器 + 架构约束
│   │
│   ├── sync/                  # 文档同步
│   │   └── doc_sync.py       # 文档版本同步管理
│   │
│   ├── storage/               # 轻量化存储
│   │   ├── json_store.py     # JSON存储
│   │   └── markdown.py       # Markdown存储
│   │
│   └── harness/               # 核心能力
│       ├── human_loop.py     # 人机交互
│       ├── agents_knowledge.py # AGENTS.md
│       ├── hooks.py          # 质量门禁
│       ├── hooks_integration.py # Hooks 集成层
│       └── adversarial.py    # 对抗性工作流
│
└── tests/                     # 测试文件（660个测试用例）
    ├── roles/                 # 角色单元测试
    │   ├── test_product_manager.py
    │   └── test_project_manager.py
    ├── maintenance/           # 维护模块测试
    └── workflow/              # 工作流测试
```

---

## 更新日志

### v0.9.0 (当前版本)

**统一需求检测架构**

将需求检测功能统一到工作流阶段，解决 IntentRouter 与 RequirementDetector 的职责重叠问题。

1. **架构设计统一**
   - IntentRouter：宏观路由决策（走哪个工作流）
   - RequirementDetectionStage：微观需求提取（提取具体需求内容）
   - 避免角色层重复实现需求检测逻辑

2. **RequirementDetectionStage 需求检测阶段**
   - 作为工作流阶段集成到 pipeline
   - 统一管理 RequirementDetector、ConfirmationManager、DocumentMaintenanceManager
   - 支持从用户消息和 AI 分析结果中提取需求
   - 高置信度需求自动确认，低置信度需求请求用户确认

3. **RequirementDetector 需求检测器**
   - 多模式匹配（关键词 + 正则表达式）
   - 置信度评估（0-1范围）
   - 支持多种需求类型：功能、Bug修复、改进、约束、咨询、反馈
   - 支持从代码审查、测试失败结果中检测需求

4. **ConfirmationManager 确认机制**
   - 添加到文档前询问用户确认
   - 高置信度需求自动批准（阈值可配置）
   - 批量确认/拒绝操作

5. **DocumentMaintenanceManager 文档维护管理器**
   - 需求自动添加到文档
   - 团队通知系统（按角色分发）
   - 任务自动创建

6. **API 示例**
   ```python
   from harnessgenj import Harness
   from harnessgenj.workflow.requirement_stage import RequirementDetectionStage

   # 使用需求检测阶段处理用户消息
   harness = Harness("my_project")
   stage = RequirementDetectionStage(harness.memory)

   # 检测需求并询问确认
   result = stage.execute({
       "message": "我需要一个购物车功能",
       "intent_type": "development",
   })

   # result.detected_requirements - 检测到的需求列表
   # result.pending_confirmations - 待确认列表
   # result.confirmed_requirements - 已确认的需求
   # result.created_tasks - 创建的任务

   # 处理用户确认
   if result.pending_confirmations:
       process_result = stage.process_user_confirmation(
           result.pending_confirmations[0].confirmation_id,
           "是",
       )
   ```

7. **测试覆盖**
   - 新增 25 个需求检测阶段测试
   - 新增 90 个维护模块测试
   - 总测试数量：588 个（全部通过）

### v0.8.1

**工作流与记忆管理深度集成**

完善工作流系统与 JVM 分代记忆的映射关系，修复输出键名不一致问题。

1. **Pipeline 与 Memory Mapping 一致性修复**
   - 新增 `OutputTarget.source_key` 字段，支持 Pipeline 输出键到 Memory 存储键的映射
   - 统一所有阶段的输入来源定义，补充缺失的 `user_stories`、`acceptance_criteria` 等输入

2. **完善所有工作流的 Memory Mapping**
   - 新增 `INQUIRY_PIPELINE_MAPPINGS`（3 阶段）
   - 新增 `MANAGEMENT_PIPELINE_MAPPINGS`（3 阶段）
   - 所有 5 种工作流现已完整覆盖 Memory 映射

3. **意图识别增强**
   - 优化 BUGFIX 意图识别，新增关键词："没有正确"、"不正确"、"不对"、"缺少"
   - 增强复杂 Bug 描述的识别准确率

4. **测试覆盖**
   - 新增 54 个工作流相关测试
   - 总测试数量：473 个（全部通过）

### v0.8.0

**意图识别与工作流重构**

重新设计工作流系统，实现智能意图识别和统一的质量保证流程。

1. **意图识别系统**
   - 新增 `IntentRouter` 意图识别路由器
   - 支持多模式匹配（关键词 + 正则表达式）
   - 自动识别：开发、Bug修复、咨询、管理 四种意图
   - 提取关键实体（功能名、模块名、问题描述）
   - 智能路由到对应工作流

2. **工作流重构**
   - **统一开发流水线**：需求识别 → 架构规划 → 代码编写 → **对抗优化** → 单元测试 → 集成测试
   - **Bug修复流水线**：问题分析 → 方案设计 → 代码修复 → **对抗验证** → 回归测试 → 集成验证
   - 所有代码变更强制经过 GAN 对抗审查，保证产出质量

3. **质量门禁系统**
   - 新增 `QualityGate` 质量门禁定义
   - 支持：需求完整性、架构评审、代码审查、单元测试、集成测试、覆盖率阈值
   - 可配置阈值和必需性

4. **工作流类型精简**
   - 从 4 种工作流精简为 5 种明确职责的工作流
   - `intent_pipeline`: 意图识别入口
   - `development_pipeline`: 统一开发（含GAN）
   - `bugfix_pipeline`: Bug修复（含GAN，默认aggressive）
   - `inquiry_pipeline`: 问题咨询
   - `management_pipeline`: 项目管理

5. **工作流记忆映射**
   - 新增 `StageMemoryMapping` 定义阶段产出物到 JVM 记忆区域的映射
   - 新增 `WorkflowExecutor` 执行阶段并自动管理记忆读写
   - 支持 `source_key` 字段实现 Pipeline 输出键与 Memory 存储键的灵活映射

**API 变更**

```python
# 新增：意图识别
from harnessgenj.workflow import identify_intent, IntentType

result = identify_intent("目前项目中文字模式和语音模式的切换AI无法理解")
# result.intent_type = IntentType.BUGFIX
# result.target_workflow = "bugfix_pipeline"
# result.priority = "P0"

# 新增：获取工作流
from harnessgenj.workflow import get_workflow, list_workflows

workflows = list_workflows()  # 列出所有可用工作流
pipeline = get_workflow("development_pipeline", intensity="aggressive")

# 新增：Engine 集成
harness = Harness("my_project")
intent = harness.analyze_intent("我需要一个登录功能")
pipeline = harness.route_to_workflow(intent)
```

### v0.7.0

**框架架构优化与功能增强**

从架构顶层进行全面优化，新增多个核心功能模块，完善集成测试体系。

1. **角色协作机制**
   - 新增 `RoleCollaborationManager` 管理角色协作
   - 新增 `MessageBus` 实现角色间消息传递（优先级队列、广播、订阅）
   - 支持产出物转移和协作快照

2. **任务依赖管理**
   - 新增 `DependencyGraph` 实现任务依赖图
   - 支持 DFS 循环依赖检测
   - 支持拓扑排序确定执行顺序
   - 支持影响分析和 Mermaid 可视化

3. **Hooks 集成层**
   - 新增 `HooksIntegration` 统一管理 Pre/Post Hooks
   - 支持阻塞/非阻塞模式
   - 集成到 `develop()` 和 `fix_bug()` 流程

4. **代码生成辅助**
   - 新增 `CodeGenerator` 代码生成器
   - 内置函数、类、测试、API端点等模板
   - 支持架构约束检查（禁止 eval/exec、硬编码密钥等）
   - 集成到 `Developer` 角色作为辅助工具

5. **文档自动同步**
   - 新增 `DocumentSyncManager` 文档版本同步
   - 支持 MD5/SHA256 版本哈希
   - 支持一致性检查

6. **TDD 工作流**
   - 新增 `TDDWorkflow` 实现 Red-Green-Refactor 循环
   - 支持测试覆盖率追踪
   - 支持失败修复建议

7. **Bug 修复**
   - 修复 `CodeReviewer.role_type` 返回错误类型问题
   - 修复 `BugHunter.role_type` 返回错误类型问题
   - 确保判别器角色可被正确查询

8. **测试体系完善**
   - 新增 45 个全流程集成测试
   - 总测试数量：395 个（全部通过）
   - 覆盖：初始化、角色调度、GAN机制、记忆管理、Hooks、协作、文档同步、代码生成、TDD、依赖管理

**API 变更**

```python
# 新增：角色协作
harness._collaboration.send_message(from_role="pm", to_role="dev", content={})
harness._collaboration.transfer_artifact(from_role="dev", to_role="reviewer", ...)

# 新增：依赖图
pipeline.has_circular_dependency()
pipeline.get_execution_order()
pipeline.to_mermaid()

# 新增：TDD 模式
harness.enable_tdd()
harness.develop("功能", use_tdd=True)

# 新增：代码生成（Developer 角色）
developer.generate_function("calculate_sum", params="a, b", body="return a + b")
developer.generate_class("UserService", init_params="self, db")
developer.generate_test("user_login", arrange="...", act="...", assertion="...")
```

### v0.6.0

**GAN 对抗机制深度融合**

将 GAN 思想的对抗机制深度集成到框架核心，实现质量驱动的开发流程。

1. **对抗机制默认启用**
   - 项目初始化时自动激活对抗系统
   - 无需显式调用 `enable_adversarial_mode()`
   - 质量保证成为开发流程的固有部分

2. **双层对抗架构**
   - **任务级对抗**：`TaskAdversarialController` 管理单次开发的审查-修复循环
   - **系统级对抗**：`SystemAdversarialController` 跨任务识别模式，驱动持续改进
   - 新增 `get_system_analysis()` API 获取系统健康度和改进建议

3. **质量数据驱动记忆管理**
   - `MemoryEntry` 新增质量字段：`quality_score`、`review_count`、`generator_id`、`discriminator_id`
   - `QualityAwareCollector` 实现质量感知 GC
   - 高质量内容优先存活，低质量内容优先回收
   - 对抗审查结果自动更新记忆条目的质量信息

4. **工作流深度集成**
   - 新增 `create_adversarial_pipeline()` 工厂函数
   - `AdversarialStageConfig` 配置对抗阶段参数
   - `StageStatus` 新增 `UNDER_REVIEW`、`REVIEW_FAILED` 状态
   - 判别器角色 (`CodeReviewer`、`BugHunter`) 可被调度器自动调度

5. **角色类型系统扩展**
   - `RoleType` 枚举新增判别器角色
   - `RoleCategory` 区分生成器和判别器
   - `DOCUMENT_OWNERSHIP` 配置判别器角色的文档访问权限

6. **集成测试完善**
   - 新增 16 个集成测试用例
   - 覆盖：完整生命周期、对抗开发、质量数据流、渐进式披露、系统分析、持久化
   - 总测试数量：96 个

**API 变更**

```python
# 新增：系统级分析
analysis = harness.get_system_analysis()

# 新增：健康度趋势
trend = harness.get_health_trend()

# 新增：使用任务级对抗控制器
result = harness.run_task_with_adversarial(
    task={"id": "TASK-001", "description": "..."},
    max_rounds=3,
)

# 废弃：对抗模式现在默认启用
harness.enable_adversarial_mode()  # 弃用，但仍可用
```

**质量数据流**

```
对抗审查 → 计算质量分数 → 更新 MemoryEntry
         ↓
    GC 存活判定
         ↓
    上下文装配（高质量内容优先加载）
```

### v0.5.2

**对抗性质量保证系统**

基于 GAN 思想的生成器-判别器对抗机制，显著提升单次开发成功率。

1. **新增判别器角色**
   - **CodeReviewer**：代码审查者，检测逻辑错误、边界条件、异常处理、安全漏洞、性能问题
   - **BugHunter**：漏洞猎手，采用激进策略（边界攻击、模糊测试、负向测试、安全探测）

2. **对抗工作流**
   - 多轮对抗：开发 → 审查 → 修复 → 再审查，直到通过或达到最大轮次
   - `adversarial_develop()` API 一键执行对抗开发
   - `quick_review()` 快速单轮审查

3. **双向积分系统**
   - 生成器：一轮通过加分，多轮通过递减加分，失败扣分
   - 判别器：发现真实问题加分，漏掉问题扣分，误报扣分
   - 等级评定：A(≥90)、B(70-89)、C(50-69)、D(<50)

4. **质量追踪**
   - 失败模式分析：自动识别常见失败原因
   - 质量报告：成功率、平均轮次、问题分布
   - 积分排行榜：团队绩效可视化

### v0.5.1

**首次接入优化**

1. **首次接入流程** - 新增规范化提示词模板
2. **首次接入指南** - 新增 `docs/ONBOARDING_GUIDE.md`
3. **skills/harnessgenj.md 增强** - 新增首次接入章节

### v0.5.0

**新功能**

1. **`Harness.from_project()`** - 从现有项目目录初始化
2. **`get_init_prompt()`** - 获取完整的初始化提示
3. **任务持久化** - 新增 `current_task.json`
4. **知识持久化** - 新增 `knowledge.json`

**架构重构**

- 删除冗余模块：`kernel/`、`mcp/`、`tools/`、`project/`
- 合并 `project/` 到 `memory/` - `MemoryManager` 成为统一入口

### v0.4.0

- 新增 Harness 6 大核心能力
- 移除 Sandbox 模块

### v0.3.0

- 项目管理与渐进式披露
- JVM 风格分代存储

### v0.2.0

- 角色驱动协作：6 种团队角色
- 工作流驱动开发
- 轻量化存储

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 Star！**

</div>