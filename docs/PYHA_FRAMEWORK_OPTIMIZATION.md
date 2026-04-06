# PYHA 框架优化需求文档

## 文档概述

本文档记录了 PYHA (Python Harness Agent) 框架在 HOMEMANNAGER_bg 项目使用过程中发现的优化需求，旨在提升框架利用率从当前的 40% 到 80% 以上。

---

## 1. 框架概述与当前使用分析

### 1.1 PYHA 框架核心组件

| 组件 | 文件路径 | 当前使用状态 |
|------|----------|--------------|
| Harness (主入口) | `py_ha/engine.py` | ✅ 已使用 |
| MemoryManager | `py_ha/memory/manager.py` | ⚠️ 部分使用 (约30%) |
| WorkflowCoordinator | `py_ha/workflow/coordinator.py` | ⚠️ 基础使用 |
| Roles (6个角色) | `py_ha/roles/*.py` | ❌ 未激活协作 |
| Hooks (质量门控) | `py_ha/harness/hooks.py` | ❌ 未使用 |
| MCP Server | 未集成 | ❌ 缺失 |

### 1.2 利用率分析

```
组件利用率:
├── Harness 核心流程: 70% (receive_request, complete_task)
├── MemoryManager: 30% (仅文档存储, 未用区域管理)
├── WorkflowCoordinator: 40% (单任务执行, 无流水线)
├── Roles 协作: 0% (单角色运行)
├── Hooks 系统: 0% (完全未启用)
└── MCP 集成: 0% (待开发)
────────────────────────────
总体利用率: ≈ 40%
```

---

## 2. 发现的问题清单

### 问题 1: 缺少 MCP Server 集成

**描述**: PYHA 框架与 Claude Code CLI 之间通过文件系统交互,缺乏 MCP (Model Context Protocol) 协议支持,导致:
- 无法实时获取 Claude Code 工具调用能力
- 文档同步依赖手动触发
- 无法利用 Claude Code 的代码分析能力

**影响范围**: MemoryManager、Harness
**严重程度**: P1 (高)

### 问题 2: 任务依赖管理缺失

**描述**: 当前 `complete_task()` 串行执行任务,不支持:
- 任务依赖声明 (前置任务)
- 依赖图构建与验证
- 受影响任务自动标记

**影响范围**: Harness、WorkflowCoordinator
**严重程度**: P1 (高)

### 问题 3: Hooks 能力未激活

**描述**: `py_ha/harness/hooks.py` 定义了完整的 Hooks 系统,但未在 Harness 中启用:
- CodeLintHook: 代码风格检查
- SecurityHook: 安全扫描
- ValidationHook: 输入验证
- TestPassHook: 测试通过检查

**影响范围**: Harness
**严重程度**: P2 (中)

### 问题 4: 角色协作机制未启用

**描述**: 框架定义了 6 个角色 (PM, ProductManager, Architect, Developer, Tester, DocWriter),但当前仅单角色执行,缺少:
- 多角色并行协作
- 角色间消息传递
- 角色产出物流转

**影响范围**: WorkflowCoordinator、Roles
**严重程度**: P2 (中)

### 问题 5: 文档自动同步机制缺失

**描述**: `.py_ha/documents/` 与 Claude Code memory 之间需手动同步:
- `progress.md` 更新需人工干预
- 无法自动触发 memory 更新
- 文档版本不一致风险

**影响范围**: MemoryManager
**严重程度**: P3 (低)

### 问题 6: 代码生成辅助不足

**描述**: 框架未提供代码生成辅助能力:
- 无模板代码生成
- 无代码片段复用机制
- 无架构约束检查

**影响范围**: Developer Role
**严重程度**: P3 (低)

### 问题 7: TDD 工作流未支持

**描述**: 缺少测试驱动开发 (TDD) 工作流支持:
- 无"先写测试"流程引导
- 无测试覆盖率追踪
- 无测试结果反馈闭环

**影响范围**: Tester Role、Hooks
**严重程度**: P3 (低)

---

## 3. 优化任务清单

### TASK-PYHA-001: MCP Server 集成

**优先级**: P1  
**预估工期**: 3 天  
**依赖**: 无

#### 任务描述

将 PYHA 框架注册为 Claude Code MCP Server,实现:
1. Claude Code 可调用 PYHA 工具
2. PYHA 可访问 Claude Code 能力
3. 双向消息传递通道

#### 验收标准

- [ ] Claude Code 可通过 `mcp__pyha-server__pyha_create_task` 创建任务
- [ ] Claude Code 可通过 `mcp__pyha-server__pyha_get_progress` 获取进度
- [ ] MCP 工具调用响应时间 < 500ms
- [ ] 错误处理完善,异常信息可读

---

### TASK-PYHA-002: 任务依赖管理

**优先级**: P1  
**预估工期**: 2 天  
**依赖**: 无

#### 任务描述

实现任务依赖图管理,支持:
1. 任务前置依赖声明
2. 依赖关系验证 (禁止循环依赖)
3. 状态变更传播 (完成任务自动解锁后继)
4. 影响分析 (修改任务时标记受影响任务)

#### 验收标准

- [ ] 可声明任务依赖关系
- [ ] 循环依赖检测生效
- [ ] 完成任务自动解锁后继
- [ ] 影响分析功能可用
- [ ] 依赖图可视化 Markdown 输出

---

### TASK-PYHA-003: Hooks 能力增强

**优先级**: P2  
**预估工期**: 2 天  
**依赖**: TASK-PYHA-001

#### 任务描述

激活并增强 Hooks 系统:
1. 在 Harness 流程中集成 Hooks
2. 添加 Hook 执行结果反馈
3. 支持 Hook 配置 (启用/禁用、阈值)
4. 新增代码质量 Hook (复杂度、重复率)

#### 验收标准

- [ ] Hooks 在任务完成时自动执行
- [ ] 复杂度检查 Hook 生效
- [ ] 重复度检查 Hook 生效
- [ ] 失败 Hook 阻断流程
- [ ] Hook 报告 Markdown 输出

---

### TASK-PYHA-004: 角色协作激活

**优先级**: P2  
**预估工期**: 3 天  
**依赖**: TASK-PYHA-002

#### 任务描述

激活多角色协作机制:
1. 实现角色间消息传递通道
2. 实现产出物流转机制
3. 支持角色并行执行
4. 实现角色协作流水线

#### 验收标准

- [ ] 角色间消息传递可用
- [ ] 产出物流转机制生效
- [ ] 协作流水线可执行
- [ ] 评审流程可用
- [ ] 协作状态可视化

---

### TASK-PYHA-005: 文档自动同步

**优先级**: P3  
**预估工期**: 2 天  
**依赖**: TASK-PYHA-001

#### 任务描述

实现 PYHA 文档与 Claude Memory 自动同步:
1. 文档变更时自动触发同步
2. 版本一致性检查
3. 差异检测与增量同步

#### 验收标准

- [ ] 文档变更自动检测
- [ ] 同步触发机制可用
- [ ] 版本一致性检查生效
- [ ] 同步状态可视化

---

### TASK-PYHA-006: 代码生成辅助

**优先级**: P3  
**预估工期**: 3 天  
**依赖**: TASK-PYHA-004

#### 任务描述

增强 Developer 角色的代码生成能力:
1. 提供模板代码库
2. 支持代码片段复用
3. 架构约束检查
4. 代码生成建议

#### 验收标准

- [ ] 模板代码库可用
- [ ] 变量替换生成正确
- [ ] 架构约束检查生效
- [ ] 模板推荐功能可用

---

### TASK-PYHA-007: TDD 工作流支持

**优先级**: P3  
**预估工期**: 2 天  
**依赖**: TASK-PYHA-003, TASK-PYHA-004

#### 任务描述

实现测试驱动开发工作流支持:
1. "先写测试"流程引导
2. 测试覆盖率追踪
3. 测试结果反馈闭环
4. 测试失败自动修复建议

#### 验收标准

- [ ] TDD 循环流程可执行
- [ ] 测试覆盖率追踪可用
- [ ] 测试失败修复建议生成
- [ ] 覆盖率阈值检查生效

---

## 4. 任务优先级矩阵

| 任务编号 | 任务名称 | 优先级 | 工期 | 依赖 | ROI |
|----------|----------|--------|------|------|-----|
| PYHA-001 | MCP Server 集成 | P1 | 3天 | 无 | 高 |
| PYHA-002 | 任务依赖管理 | P1 | 2天 | 无 | 高 |
| PYHA-003 | Hooks 能力增强 | P2 | 2天 | PYHA-001 | 中 |
| PYHA-004 | 角色协作激活 | P2 | 3天 | PYHA-002 | 中 |
| PYHA-005 | 文档自动同步 | P3 | 2天 | PYHA-001 | 低 |
| PYHA-006 | 代码生成辅助 | P3 | 3天 | PYHA-004 | 低 |
| PYHA-007 | TDD 工作流支持 | P3 | 2天 | PYHA-003, PYHA-004 | 低 |

---

## 5. 实施计划

### 5.1 时间线 (17 天)

```
Week 1: P1 任务
├── Day 1-3: PYHA-001 MCP Server 集成
└── Day 4-5: PYHA-002 任务依赖管理

Week 2: P2 任务
├── Day 6-7: PYHA-003 Hooks 能力增强
└── Day 8-10: PYHA-004 角色协作激活

Week 3: P3 任务
├── Day 11-12: PYHA-005 文档自动同步
├── Day 13-15: PYHA-006 代码生成辅助
└── Day 16-17: PYHA-007 TDD 工作流支持
```

### 5.2 预期收益

- **MCP 集成**: 框架利用率 +20%
- **任务依赖**: 开发效率 +15%
- **Hooks**: 代码质量 +25%
- **角色协作**: 产出完整性 +30%
- **文档同步**: 维护成本 -10%
- **代码生成**: 开发速度 +20%
- **TDD 支持**: 测试覆盖率 +40%

**总体目标**: 框架利用率从 40% 提升至 80%+

---

## 6. 附录

### A. 文件结构变更

```
py_ha/
├── mcp/
│   └── server.py          # 新增: MCP Server
├── workflow/
│   ├── dependency.py      # 新增: 任务依赖图
│   ├── role_collaboration.py  # 新增: 角色协作
│   └── tdd_workflow.py    # 新增: TDD 工作流
├── harness/
│   └── hooks_integration.py  # 新增: Hooks 集成
├── memory/
│   └ doc_sync.py          # 新增: 文档同步
└── codegen/
    └── generator.py       # 新增: 代码生成
```

### B. 配置变更

```json
// .claude/settings.json 新增
{
  "mcpServers": {
    "pyha-server": {
      "command": "python",
      "args": ["-m", "py_ha.mcp.server"],
      "env": {}
    }
  }
}
```

---

*文档版本: 1.0.0*  
*创建日期: 2026-04-05*  
*作者: Claude Code Assistant*
