# HarnessGenJ 项目开发规范

> 此文件为 Claude Code 项目级指令，确保 AI 在开发过程中主动使用框架功能

## 核心原则

**⚠️ 强制要求：所有开发任务必须通过 HarnessGenJ 框架执行**

## MCP Server 集成（v1.3.0+）

HarnessGenJ 现已支持 MCP (Model Context Protocol)，可通过 MCP 工具直接调用框架功能。

### 可用 MCP 工具 (21个)

| 类别 | 工具 | 用途 |
|------|------|------|
| **内存** | `memory_store` | 存储内容到记忆系统 |
| | `memory_retrieve` | 从记忆系统检索内容 |
| | `memory_status` | 获取记忆系统状态 |
| | `memory_gc` | 触发垃圾回收 |
| | `memory_store_document` | 存储文档 |
| | `memory_get_document` | 获取文档 |
| **任务** | `task_create` | 创建新任务 |
| | `task_complete` | 完成任务 |
| | `task_develop` | 开发功能（完整工作流） |
| | `task_fix_bug` | 修复 Bug（完整工作流） |
| | `task_status` | 查询任务状态 |
| | `task_history` | 任务执行历史 |
| **系统** | `system_status` | 系统状态 |
| | `system_health` | 健康报告 |
| | `system_scoreboard` | 积分排行 |
| | `system_report` | 项目报告 |
| | `system_review` | 代码审查 |
| **存储** | `storage_save` | 保存数据 |
| | `storage_load` | 加载数据 |
| | `storage_save_knowledge` | 保存知识 |
| | `storage_search` | 搜索知识库 |

### MCP 工具调用示例

```
# 开发新功能
task_develop(feature_request="实现用户登录功能")

# 修复 Bug  
task_fix_bug(bug_description="首页加载缓慢问题")

# 存储重要知识
memory_store(key="架构决策", content="使用JWT认证")

# 查看积分排行
system_scoreboard()
```

## 框架使用指南

### 1. 初始化框架（每次对话开始时执行）

```python
from harnessgenj import Harness

# 创建框架实例
harness = Harness.from_project(".")  # 从当前项目初始化

# 查看框架状态
status = harness.get_status()
print(status)
```

### 2. 开发功能时（必须使用）

**❌ 禁止直接编写代码而不经过框架**

**✅ 正确做法：**

```python
# 开发新功能
result = harness.develop("实现用户登录功能")

# 修复 Bug
result = harness.fix_bug("首页加载缓慢问题")

# 对抗性开发（多轮审查）
result = harness.adversarial_develop("实现支付功能", max_rounds=3)
```

### 3. 任务完成后（必须更新文档）

```python
# 完成任务并更新文档
harness.complete_task(task_id, "功能已完成，通过所有测试")

# 记录关键信息
harness.remember("key_decision", "选择 JWT 作为认证方案", important=True)

# 更新开发日志
harness.record("实现了用户认证模块", context="功能开发", doc_type_hint="development")
```

### 4. 获取上下文提示

```python
# 获取当前项目的上下文（用于理解项目状态）
context = harness.get_context_prompt(role="developer")

# 获取最小上下文
minimal = harness.get_minimal_context()
```

### 5. 代码审查（强制执行）

```python
# 快速代码审查
passed, issues = harness.quick_review(code, use_hunter=True)

# 查看质量报告
report = harness.get_quality_report()

# 查看积分排行
leaderboard = harness.get_score_leaderboard()
```

## 工作流程强制要求

### 功能开发流程

1. **需求接收** → `harness.receive_request("需求描述")`
2. **开发执行** → `harness.develop("需求描述")`
3. **对抗审查** → 自动执行（框架强制）
4. **文档更新** → 自动执行（框架强制）
5. **任务完成** → `harness.complete_task(task_id, "摘要")`

### Bug 修复流程

1. **问题接收** → `harness.receive_request("问题描述", request_type="bug")`
2. **修复执行** → `harness.fix_bug("问题描述")`
3. **对抗审查** → 自动执行（框架强制）
4. **文档更新** → 自动执行（框架强制）

## 角色边界定义

| 角色 | 权限 | 禁止行为 |
|------|------|----------|
| Developer | 编辑代码、运行终端 | 修改架构设计、修改需求 |
| CodeReviewer | 只读、搜索代码 | 直接修改代码 |
| ProjectManager | 编辑文档、协调任务 | 修改代码、做技术决策 |
| Architect | 编辑文档 | 直接修改代码实现 |

## 违规后果

- **边界违规**: 积分 -5 ~ -15
- **跳过质量门禁**: 积分 -10
- **未授权修改代码**: 积分 -15

## 积分排行

```
🏆 优秀: 90+ 分 - 团队核心成员
⭐ 良好: 70-89 分 - 稳定贡献者
📌 合格: 50-69 分 - 需要提升
⚠️ 警告: <50 分 - 可能被降级
```

## 框架 API 速查

| 方法 | 用途 | 是否强制 |
|------|------|----------|
| `Harness.from_project(".")` | 初始化框架 | 每次对话开始 |
| `harness.develop()` | 开发功能 | 必须使用 |
| `harness.fix_bug()` | 修复Bug | 必须使用 |
| `harness.complete_task()` | 完成任务 | 必须使用 |
| `harness.quick_review()` | 代码审查 | 必须使用 |
| `harness.get_context_prompt()` | 获取上下文 | 建议使用 |
| `harness.remember()` | 存储知识 | 建议使用 |
| `harness.record()` | 记录日志 | 建议使用 |

## 开发检查清单

每次开发任务开始前，确认：

- [ ] 已初始化 Harness 实例
- [ ] 已获取项目上下文 `harness.get_context_prompt()`
- [ ] 使用 `harness.develop()` 或 `harness.fix_bug()` 而非直接编码
- [ ] 任务完成后调用 `harness.complete_task()`
- [ ] 代码已通过对抗审查（自动）

## 常见错误

### ❌ 错误：直接编写代码

```python
# 错误示例：直接使用 Write 工具写代码
# 这会跳过框架的质量保证流程
```

### ✅ 正确：通过框架开发

```python
# 正确示例：通过框架开发
result = harness.develop("实现功能")
# 框架会自动：
# 1. 执行工作流
# 2. 进行对抗审查
# 3. 更新文档
# 4. 更新积分
```

---

**记住：高积分 = 高职业信誉 = 团队核心成员**