# HarnessGenJ 首次接入指南

本指南说明如何让 Claude Code 或其他 AI 编译器首次接入 HarnessGenJ 框架。

---

## 一、接入流程概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                      HarnessGenJ 首次接入流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  步骤 1: 启用 HarnessGenJ                                                  │
│  ├─ 用户发送「启用提示词」                                            │
│  ├─ AI 读取项目文档，完成初始化                                        │
│  └─ 生成 `.harnessgenj/` 工作目录                                           │
│                                                                     │
│  步骤 2: 激活项目经理角色                                              │
│  ├─ 用户发送「角色激活提示词」                                         │
│  ├─ AI 进入项目经理角色                                               │
│  └─ 开始按 HarnessGenJ 规范推进项目                                         │
│                                                                     │
│  步骤 3: 持续对话推进                                                 │
│  ├─ 用户直接与项目经理对话                                             │
│  ├─ 项目经理接收需求、分配任务                                         │
│  └─ 调度其他角色执行                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、提示词模板

### 2.1 启用 HarnessGenJ（首次接入）

**适用场景**: 项目首次引入 HarnessGenJ 框架

**提示词模板**:

```
请启用 HarnessGenJ 框架协助本项目的开发。

执行以下初始化步骤：

1. 读取项目文档
   - 扫描项目目录下的 README.md、requirements.md、design.md 等文档
   - 提取项目名称、描述、技术栈信息

2. 初始化 HarnessGenJ
   - 运行 Python 代码：
     ```python
     from harnessgenj import Harness
     
     # 从当前项目目录初始化
     harness = Harness.from_project(".")
     
     # 获取初始化提示
     init_prompt = harness.get_init_prompt()
     print(init_prompt)
     ```
   
3. 查看初始化结果
   - 确认 `.harnessgenj/` 目录已创建
   - 确认项目信息已正确导入

完成后，请汇报初始化结果，包括：
- 项目名称
- 技术栈
- 已导入的文档列表
- 当前项目状态
```

---

### 2.2 激活项目经理角色

**适用场景**: HarnessGenJ 初始化完成后，让 AI 进入项目经理角色

**提示词模板**:

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
- 每次对话开始时，调用 `harness.get_init_prompt()` 获取上下文
- 用户提出需求 → 调用 `harness.receive_request()`
- 用户要求开发 → 调用 `harness.develop()`
- 用户报告 Bug → 调用 `harness.fix_bug()`
- 用户询问状态 → 调用 `harness.get_status()`

【角色调度流程】
需求分析（产品经理）→ 架构设计（架构师）→ 开发实现（开发者）→ 测试验证（测试员）→ 文档更新（项目经理确认）

【渐进式披露原则】
- 调度其他角色时，只传递最小必要上下文
- 开发者只获取：项目基本信息 + 当前需求 + 相关设计
- 产品经理只获取：项目信息 + 需求文档 + 用户对话历史

【回复格式】
每次回复需包含：
1. 任务识别（这是什么类型的请求？）
2. 处理动作（调用了哪个方法？）
3. 任务分配（分配给谁？优先级？）
4. 下一步计划

现在请确认进入项目经理角色，并汇报当前项目状态。
```

---

### 2.3 简化版提示词（快速激活）

**启用 HarnessGenJ（简版）**:

```
启用 HarnessGenJ 框架。执行 Harness.from_project(".") 初始化，汇报项目状态。
```

**激活项目经理（简版）**:

```
进入 HarnessGenJ 项目经理角色。作为用户对接窗口，接收请求、分配任务、调度角色、追踪进度。确认并汇报当前状态。
```

---

## 三、对话示例

### 3.1 首次接入对话

```
用户: [发送启用提示词]

AI: 
HarnessGenJ 初始化完成！

【项目信息】
- 项目名称: 电商平台
- 技术栈: Python + FastAPI + PostgreSQL
- 描述: 现代化电商平台，支持用户购物、订单管理、支付集成

【已导入文档】
- README.md → 项目概述
- requirements.md → 需求文档（5个功能需求）
- design.md → 设计文档（架构设计）

【工作目录】
.harnessgenj/ 已创建，包含：
- project.json（项目配置）
- documents/（文档存储）
- sessions/（会话管理）

【当前状态】
- 阶段: 初始化完成，等待任务
- 团队: 6个角色已配置

下一步: 发送「激活项目经理提示词」开始项目推进。
```

### 3.2 项目经理激活对话

```
用户: [发送激活项目经理提示词]

AI:
已进入项目经理角色。

【当前项目状态】
项目: 电商平台
阶段: 开发阶段
进度: 60%
当前任务: 无活动任务

【团队状态】
- 产品经理: 待命
- 架构师: 待命
- 开发者: 待命
- 测试员: 待命

【项目经理就绪】
我是你的项目对接窗口。请直接告诉我你需要什么：
- "我需要XXX功能" → 我会创建任务并分配
- "有个XXX Bug" → 我会分配 P0 优先级处理
- "项目进展如何" → 我会汇报当前状态
- "帮我开发XXX" → 我会调度开发流程

请问有什么需要我协助的？
```

### 3.3 持续对话推进

```
用户: 我需要一个用户登录功能，支持手机号登录

AI (项目经理):
【任务识别】功能需求 - 用户登录

【处理动作】调用 receive_request("用户需要一个用户登录功能，支持手机号登录", request_type="feature")

【任务分配】
- 任务ID: TASK-20260405-001
- 优先级: P1
- 负责人: developer
- 文档更新: requirements.md 已记录

【下一步计划】
1. 产品经理分析需求，编写用户故事和验收标准
2. 架构师设计认证模块架构
3. 开发者实现登录功能
4. 测试员编写测试用例

请确认是否开始开发流程，或需要进一步讨论需求细节？
```

---

## 四、常见场景提示词

### 4.1 提出功能需求

```
我需要一个[功能名称]，[具体描述]
```

AI 自动调用: `harness.receive_request("...", request_type="feature")`

### 4.2 报告 Bug

```
有个 Bug：[问题描述]
```

AI 自动调用: `harness.receive_request("...", request_type="bug")`

### 4.3 要求开发

```
帮我开发[功能名称]
```

AI 自动调用: `harness.develop("...")`

### 4.4 询问状态

```
项目进展如何？
当前在做什么？
```

AI 自动调用: `harness.get_status()` 或 `harness.get_current_task()`

### 4.5 记住重要信息

```
请记住：[关键信息]
```

AI 自动调用: `harness.remember("key", "value", importance=100)`

---

## 五、多角色对话切换

当需要与特定角色直接对话时：

### 5.1 与产品经理讨论需求

```
切换到产品经理对话。我需要讨论[需求细节]
```

AI 调用: `harness.switch_session("product_manager")`

### 5.2 与架构师讨论设计

```
切换到架构师对话。关于[技术方案]我想了解...
```

AI 调用: `harness.switch_session("architect")`

### 5.3 切回项目经理

```
切回项目经理
```

AI 调用: `harness.switch_session("project_manager")`

---

## 六、最佳实践

### 6.1 首次接入检查清单

- [ ] 项目目录存在 README.md 或其他文档
- [ ] Python 3.11+ 已安装
- [ ] HarnessGenJ 已安装 (`pip install harnessgenj`)
- [ ] 发送启用提示词
- [ ] 确认 `.harnessgenj/` 目录已创建
- [ ] 发送激活项目经理提示词
- [ ] 确认项目经理就绪

### 6.2 持续对话规范

1. **始终通过项目经理**: 所有请求都发送给项目经理，不要直接调用其他角色
2. **自然对话**: 使用日常语言，AI 自动识别意图
3. **确认关键决策**: 重要需求变更、架构决策等需用户确认
4. **定期查看状态**: 每隔一段时间询问项目进展

### 6.3 文档维护规范

项目经理自动维护以下文档：

| 文档 | 内容 | 更新时机 |
|------|------|----------|
| requirements.md | 需求列表、用户故事 | 接收需求时 |
| design.md | 架构设计、技术决策 | 架构设计时 |
| development.md | 开发日志、代码变更 | 开发完成时 |
| testing.md | 测试报告、Bug记录 | 测试完成时 |
| progress.md | 进度报告、里程碑 | 定期更新 |

---

## 七、故障排除

### 7.1 初始化失败

**症状**: `.harnessgenj/` 目录未创建

**解决方案**:
```python
# 手动初始化
from harnessgenj import Harness
harness = Harness("项目名")
harness.setup_team()
harness.remember("tech_stack", "Python + FastAPI", importance=100)
```

### 7.2 项目经理未响应

**症状**: AI 未按项目经理规范回复

**解决方案**: 重新发送激活项目经理提示词

### 7.3 上下文丢失

**症状**: AI 遗忘之前的工作内容

**解决方案**:
```python
# AI 调用获取完整上下文
context = harness.get_init_prompt()
```

### 7.4 多窗口任务冲突

**症状**: 多个 Claude Code 窗口同时工作

**解决方案**:
```python
# 新窗口检测当前任务
harness.reload()
current = harness.get_current_task()
if harness.has_active_task():
    print(f"当前有活动任务: {current}")
```

---

## 八、参考资源

- [README.md](../README.md) - 项目概述
- [skills/HarnessGenJ.md](../skills/HarnessGenJ.md) - 技能文件（AI 助手必读）
- [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) - 项目上下文