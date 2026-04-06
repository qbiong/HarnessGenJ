# HGJ框架优化需求文档

> 基于OpenClawAndroid项目实际应用情况的框架改进建议
> 
> 日期：2026-04-05

---

## 背景

HarnessGenJ (HGJ) 是一个AI Agent协作框架，采用GAN对抗机制、角色驱动协作和JVM式内存管理。在OpenClawAndroid项目中进行了初步应用，发现了以下可优化的方向。

---

## 当前状态分析

| 指标 | 当前值 | 问题描述 |
|------|--------|----------|
| total_tasks_analyzed | 0 | 无任务历史追踪，GAN机制无法发挥作用 |
| team_size | 0 | 未配置虚拟团队成员，角色协作未激活 |
| knowledge.json | 原始文档 | 缺乏结构化知识条目，检索效率低 |
| API调用 | 手动 | 需要开发者主动调用，集成便利性不足 |

---

## 优化需求清单

### 1. 任务分析追踪机制

**问题描述**：
框架没有建立任务历史追踪，导致GAN对抗机制无法学习判断任务完成质量。

**需求规格**：

任务完成时自动记录决策链，包含：
- 任务唯一标识
- 任务执行结果
- 关键决策列表（rationale, choice, alternatives）
- 结果质量评估
- 触发Discriminator学习

**验收标准**：
- 任务完成后自动记录决策链
- total_tasks_analyzed 随任务完成递增
- Discriminator能够基于历史任务提供质量评估

---

### 2. 知识库结构化改造

**问题描述**：
当前 knowledge.json 仅存储原始文档内容，缺乏可检索的结构化条目。

**需求规格**：

知识库条目应包含结构化字段：
- id: 唯一标识（如 voice-fix-001）
- type: 条目类型
- problem:问题描述
- solution: 解决方案
- code_location: 文件路径和行号
- tags: 分类标签
- created_at/updated_at: 时间戳
- verified: 验证状态

**条目类型定义**：

| 类型 | 字段要求 | 用途 |
|------|----------|------|
| bug_fix | problem, solution, code_location | 问题修复记录 |
| decision_pattern | rationale, choice, alternatives | 决策模式沉淀 |
| architecture_change | before, after, reason | 架构演进追踪 |
| test_case | scenario, expected, actual | 测试用例库 |
| security_issue | vulnerability, severity, fix | 安全问题追踪 |

**验收标准**：
- 知识库条目包含结构化字段
- 支持按标签、类型、文件路径检索
- recall(query) API能返回相关条目

---

### 3. 团队角色自动激活

**问题描述**：
虚拟团队成员未配置，角色驱动的对抗协作机制未生效。

**需求规格**：

默认团队配置：
- CodeReviewer: code_quality, security, best_practices | 触发：code_change, pre_commit
- BugHunter: edge_case_analysis, race_condition, resource_leak | 触发：feature_complete
- Tester: test_generation, coverage_analysis | 触发：feature_complete

**触发机制**：

| 事件 | 触发角色 | 执行动作 |
|------|----------|----------|
| code_change | CodeReviewer | 审查代码质量、安全风险 |
| feature_complete | BugHunter + Tester | 搜索边界问题、生成测试 |
| pre_commit | CodeReviewer | 最终审查确认 |

**验收标准**：
- 项目初始化时自动配置默认团队
- team_size > 0
- 代码变更触发CodeReviewer自动审查

---

### 4. API集成便利性增强

**问题描述**：
需要手动调用框架API，增加了开发者的使用负担。

**需求规格**：

提供装饰器模式：
- @trace_decision(category, auto_log=True) - 自动记录决策

提供生命周期钩子：
- on_task_complete - 任务完成时触发BugHunter和Tester
- on_issue_found - 发现问题时触发Discriminator评估

**API简化对比**：

| 操作 | 当前方式 | 优化后 |
|------|----------|--------|
| 记录决策 | knowledge.add_entry(...) | @trace_decision 装饰器 |
| 触发审查 | code_reviewer.review(...) | 自动（代码变更时） |
| 搜索问题 | bug_hunter.search(...) | 自动（任务完成时） |

**验收标准**：
- 提供 @trace_decision 装饰器
- 提供 on_task_complete 等生命周期钩子
- 关键操作无需手动调用API

---

### 5. 开发工具链集成

**问题描述**：
框架与Git、IDE、构建系统等工具链缺乏集成。

**需求规格**：

#### Git集成

- pre-commit: CodeReviewer审查staged changes，高严重性问题阻断提交
- post-commit: 提交消息自动关联知识条目
- post-merge: 分析合并冲突，审查解决方案

#### IDE集成（VSCode插件）

- 命令：显示相关决策历史、快速代码审查
- 编辑器右键菜单集成

#### 构建系统集成

- 测试失败时自动回溯相关修改
- 失败关联知识库条目

**验收标准**：
- Git pre-commit自动触发代码审查
- 提交消息自动关联知识条目
- IDE插件可显示相关决策历史
- 测试失败时自动回溯相关修改

---

### 6. 状态持久化优化

**问题描述**：
状态只在会话结束时更新，可能丢失关键信息。

**需求规格**：

关键操作持久化点：
- task_complete
- issue_found
- decision_made
- knowledge_entry_added
- team_member_action

增量更新机制：
- mark_dirty(field, value) 标记待更新
- 达到阈值时立即flush持久化
- 异常退出不丢失数据

健康评分动态计算：
- 任务成功率 (权重0.3)
- 问题修复速度 (权重0.25)
- 代码审查通过率 (权重0.25)
- 测试覆盖率变化 (权重0.2)

**验收标准**：
- 关键操作后立即持久化状态
- 健康评分基于实际指标动态计算
- 异常退出时不丢失状态信息

---

## 实施优先级

| 需求 | 优先级 | 估算工作量 | 依赖项 |
|------|--------|------------|--------|
| 任务分析追踪机制 | P0 | 2天 | 无 |
| 知识库结构化改造 | P0 | 3天 | 无 |
| 团队角色自动激活 | P1 | 1天 | 任务追踪 |
| API集成便利性 | P1 | 2天 | 知识库改造 |
| 开发工具链集成 | P2 | 5天 | API增强 |
| 状态持久化优化 | P1 | 1天 | 无 |

**建议实施顺序**：
1. Phase 1 (Week 1): 任务追踪 + 知识库改造 + 状态持久化
2. Phase 2 (Week 2): 团队激活 + API便利性
3. Phase 3 (Week 3-4): 工具链集成（Git → IDE → 构建系统）

---

## 附录

### A. 知识库条目完整Schema

字段定义：
- id: 字符串，格式 [类型]-[模块]-[编号]
- type: bug_fix / decision_pattern / architecture_change / test_case / security_issue
- created_at / updated_at: ISO 8601时间格式
- verified: boolean
- tags: 字符串数组

### B. 团队角色技能矩阵

| 角色 | 核心技能 | 辅助技能 | 触发频率 |
|------|----------|----------|----------|
| CodeReviewer | code_quality, security | style_consistency, documentation | 高（每次变更） |
| BugHunter | edge_case_analysis, race_condition | resource_leak, concurrency | 中（任务完成） |
| Tester | test_generation, coverage_analysis | regression_detection | 中（任务完成） |
| Architect | design_patterns, scalability | maintainability, performance | 低（架构决策） |

### C. 预期效果

实施后预期达到：

| 指标 | 当前 | 目标 |
|------|------|------|
| total_tasks_analyzed | 0 | > 10/周 |
| team_size | 0 | 3-4 |
| 知识检索命中率 | N/A | > 80% |
| API调用次数（手动） | 100% | < 20% |
| 健康评分准确性 | 静态 | 动态更新 |

---

*文档版本：v1.0*
*创建日期：2026-04-05*
