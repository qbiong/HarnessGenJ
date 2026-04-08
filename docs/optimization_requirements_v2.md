# HGJ框架优化需求文档 (v2.0)

> 基于OpenClawAndroid项目实际应用的深度审计与改进建议
> 
> 审计日期：2026-04-06
> 项目版本：v1.6.1

---

## 一、执行摘要

### 审计结论：**对抗审查机制完全未生效**

| 维度 | 状态 | 影响等级 |
|------|------|----------|
| Hooks集成 | ❌ 未配置 | **阻断级** |
| 角色协作 | ❌ 空转 | **阻断级** |
| 积分系统 | ❌ 无数据 | **阻断级** |
| 知识库 | ⚠️ 未结构化 | **降效级** |
| 技术适配 | ❌ 模板未适配 | **降效级** |
| 工具链 | ❌ 未集成 | **缺失级** |

**核心问题**：GAN对抗机制设计精良，但实际落地时因Hooks未配置导致整个流程无法启动。

---

## 二、问题清单（按阻断优先级排序）

### P0 - 阻断级问题

#### 2.1 Hooks未集成到Claude Code

| 项目 | 详情 |
|------|------|
| **文件位置** | `.claude/settings.json` |
| **问题描述** | 缺少 PreToolUse/PostToolUse hooks 配置，代码写入前后不会自动触发审查 |
| **影响** | GAN对抗审查入口被阻断，CodeReviewer/BugHunter无法介入 |
| **修复方案** | 在settings.json添加hooks配置 |

```json
// 需添加的配置
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": ["python .claude/pyha_hook.py --pre"]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": ["python .claude/pyha_hook.py --post"]
      }
    ]
  }
}
```

---

#### 2.2 包名引用过期

| 项目 | 详情 |
|------|------|
| **文件位置** | `.claude/pyha_hook.py:21-23` |
| **问题描述** | 框架已更名为 `HarnessGenJ`，但hooks脚本仍引用旧包名 `py_ha` |
| **影响** | Hooks执行时ImportError，无法加载框架模块 |

```python
# 当前代码（错误）
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "py_ha" / "src"))
from py_ha.harness.hooks import ...

# 应改为
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "harnessgenj" / "src"))
from harnessgenj.harness.hooks import ...
```

---

#### 2.3 积分系统空转

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/scores.json` |
| **问题描述** | 所有角色统计数据为0，events数组为空 |
| **影响** | GAN对抗的双向积分激励机制从未执行，无质量数据驱动记忆管理 |

```json
// 当前状态 - 所有数据为空
{
  "scores": {
    "developer_1": { "total_tasks": 0, "issues_found": 0 },
    "code_reviewer_1": { "total_tasks": 0, "issues_found": 0 },
    "bug_hunter_1": { "total_tasks": 0, "issues_found": 0 }
  },
  "events": []  // 无积分变动记录
}
```

---

### P1 - 降效级问题

#### 2.4 技术栈模板未适配

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/agents/tech.md`, `.harnessgenj/agents/conventions.md` |
| **问题描述** | 模板针对Python项目（PEP 8），但OpenClawAndroid是Java/Android项目 |
| **影响** | 角色读取错误规范，审查建议不适用 |

```markdown
// 当前 tech.md（错误）
## 主要技术
- 

## 依赖管理
- 使用 pip 或 poetry

// 当前 conventions.md（错误）
## 编码风格
- 遵循 PEP 8
- 类型注解

// 应改为（适配Android）
## 主要技术
- Java 17
- Android SDK 34
- Material Design 3

## 编码风格
- 遵循 Java 命名规范
- 使用松耦合设计
- 完善的异常处理
```

---

#### 2.5 知识库未结构化

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/knowledge.json` |
| **问题描述** | 仅存储原始文档内容（README、工具清单等），缺乏可检索的结构化条目 |
| **影响** | 无法快速检索问题解决方案，每次需解析完整文档 |

**当前结构问题**：
- 条目无唯一ID，无法引用
- 无类型分类（bug_fix/decision_pattern等）
- 无代码位置索引
- 无时间戳追踪

---

#### 2.6 任务pending未启动

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/current_task.json` |
| **问题描述** | 存在pending任务"记忆架构修改代码审查"，但未启动执行 |
| **影响** | 任务管理流程中断，无任务追踪数据 |

---

#### 2.7 会话消息为空

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/sessions.json` |
| **问题描述** | messages数组为空，会话无内容记录 |
| **影响** | 角色协作消息总线未使用，无协作历史可追溯 |

---

### P2 - 缺失级问题

#### 2.8 文档驱动未执行

| 项目 | 详情 |
|------|------|
| **文件位置** | `.harnessgenj/documents/*.md` |
| **问题描述** | 存在模板文件（design.md、requirements.md等），但无实际内容 |
| **影响** | 文档驱动开发理念未落地 |

---

#### 2.9 工具链集成缺失

| 集成项 | 状态 | 影响 |
|--------|------|------|
| Git pre-commit | ❌ | 提交前无自动审查 |
| Git post-commit | ❌ | 提交不关联知识条目 |
| IDE插件 | ❌ | 无VSCode/JetBrains集成 |
| 构建系统 | ❌ | 测试失败无回溯 |

---

#### 2.10 JVM内存管理未生效

| 项目 | 详情 |
|------|------|
| **问题描述** | JVM式内存管理（Permanent/Survivor/Old）仅为概念设计，未实际运行 |
| **影响** | 无质量数据驱动的GC策略，记忆管理效率低下 |

---

## 三、架构设计层面问题

### 3.1 单一入口缺失

**问题**：框架API需手动调用（`harness.receive_request()`），无统一入口拦截用户请求。

**改进方案**：
```
用户请求 → 自动识别意图 → 路由到工作流 → 执行Pipeline → 触发对抗审查
```

### 3.2 角色协作被动触发

**问题**：角色需外部主动调用，无自动触发机制。

**改进方案**：
| 事件 | 自动触发角色 |
|------|-------------|
| Write/Edit完成 | CodeReviewer |
| 任务完成 | BugHunter + Tester |
| 发现问题 | Discriminator评估 |

### 3.3 状态持久化滞后

**问题**：状态只在会话结束时更新，可能丢失关键信息。

**改进方案**：
```python
# 关键操作后立即持久化
ON_TASK_COMPLETE → flush_state()
ON_ISSUE_FOUND → flush_state()
ON_DECISION_MADE → flush_state()
```

---

## 四、修复方案

### 4.1 Phase 1 - 阻断修复（立即执行）

| 任务 | 文件 | 工时 |
|------|------|------|
| 配置Hooks | `.claude/settings.json` | 30min |
| 更新包名引用 | `.claude/pyha_hook.py` | 15min |
| 适配技术栈模板 | `.harnessgenj/agents/*.md` | 1h |
| 初始化知识库结构 | `.harnessgenj/knowledge.json` | 2h |

**预期效果**：Hooks生效后，GAN对抗机制可启动运行。

---

### 4.2 Phase 2 - 流程激活（Week 1）

| 任务 | 描述 | 工时 |
|------|------|------|
| 启动pending任务 | 执行"记忆架构修改代码审查" | 2h |
| 触发对抗审查 | 对审查结果运行CodeReviewer/BugHunter | 自动 |
| 建立积分记录 | 首次积分变动写入scores.json | 自动 |
| 完善会话消息 | 记录角色协作过程 | 自动 |

**预期效果**：完整运行一个任务周期，验证GAN机制有效性。

---

### 4.3 Phase 3 - 架构增强（Week 2-3）

| 任务 | 描述 | 工时 |
|------|------|------|
| 单一入口设计 | 自动意图识别 + 工作流路由 | 2天 |
| 角色自动触发 | 事件驱动角色激活机制 | 2天 |
| 状态实时持久化 | 关键操作后立即flush | 1天 |
| 工具链集成 | Git hooks + IDE插件 | 5天 |

---

## 五、知识库结构化Schema

### 5.1 条目定义

```json
{
  "id": "bug-shell-injection-001",
  "type": "security_issue",
  "problem": "ShellTool命令注入风险，管道和重定向可被绕过",
  "solution": "使用命令白名单模式，禁用管道和重定向",
  "code_location": {
    "file": "app/src/main/java/com/uvm/android/tools/builtin/ShellTool.java",
    "lines": [93, 118]
  },
  "severity": "critical",
  "tags": ["security", "shell", "injection"],
  "created_at": "2026-04-06T10:00:00Z",
  "verified": false,
  "verification_notes": ""
}
```

### 5.2 类型分类

| 类型 | 必填字段 | 用途 |
|------|----------|------|
| `bug_fix` | problem, solution, code_location | 问题修复记录 |
| `decision_pattern` | rationale, choice, alternatives | 决策模式沉淀 |
| `architecture_change` | before, after, reason | 架构演进追踪 |
| `security_issue` | vulnerability, severity, fix | 安全问题追踪 |
| `test_case` | scenario, expected, actual | 测试用例库 |

---

## 六、验收标准

### 6.1 Phase 1验收

| 标准 | 验证方法 |
|------|----------|
| Hooks生效 | 执行Write操作，检查审查日志 |
| 包名正确 | 运行pyha_hook.py无ImportError |
| 技术栈适配 | tech.md包含Java/Android规范 |
| 知识库结构化 | 可按ID检索条目 |

### 6.2 Phase 2验收

| 标准 | 验证方法 |
|------|----------|
| 任务执行完成 | current_task.json status = completed |
| 积分有变动 | scores.json events数组非空 |
| 会话有记录 | sessions.json messages数组非空 |

### 6.3 Phase 3验收

| 标准 | 验证方法 |
|------|----------|
| 意图自动识别 | 用户请求无需手动调用API |
| 角色自动触发 | Write完成后CodeReviewer自动审查 |
| Git集成 | pre-commit触发审查阻断 |

---

## 七、预期效果

### 实施后对比

| 指标 | 当前 | 目标 |
|------|------|------|
| Hooks生效 | ❌ | ✅ |
| 积分变动记录 | 0 | >10/周 |
| 知识库条目 | 文档堆砌 | 结构化可检索 |
| 角色协作 | 手动调用 | 自动触发 |
| API手动调用 | 100% | <20% |
| 技术栈适配 | Python模板 | Java/Android |

---

## 八、附录

### A. Hooks完整配置

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/pyha_hook.py --pre \"$FILE_PATH\" \"$CONTENT\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/pyha_hook.py --post \"$FILE_PATH\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/pyha_hook.py --flush-state"
          }
        ]
      }
    ]
  }
}
```

### B. 角色触发矩阵

| 事件 | CodeReviewer | BugHunter | Tester | Architect |
|------|--------------|-----------|--------|-----------|
| Write完成 | ✅ | - | - | - |
| Edit完成 | ✅ | - | - | - |
| 任务完成 | - | ✅ | ✅ | - |
| 架构变更 | - | - | - | ✅ |
| 发现安全问题 | ✅ | ✅ | - | - |

### C. 状态持久化触发点

```python
PERSISTENCE_TRIGGERS = [
    "task_complete",
    "issue_found",
    "decision_made",
    "knowledge_entry_added",
    "role_action_completed",
    "score_changed",
    "session_message_added"
]
```

---

*文档版本：v2.0*
*创建日期：2026-04-06*
*下次审计建议：Phase 1修复完成后验证*