# AI Agent Harness 框架设计文档

> 基于 JVM 设计理念构建的 Python AI Agent Harness 框架

## 项目概述

### 基本信息
- **项目名称**: HarnessGenJ (Python Harness for AI Agents)
- **Python版本**: 3.13.12
- **设计理念**: 参考 JVM 架构，构建分层、可插拔、规范的 AI Agent 执行引擎

---

## Harness Engineering 概念定义

### 三层架构对比

| 层级 | JVM类比 | 关注点 | 说明 |
|------|---------|--------|------|
| **Framework** | Java语言规范 | 抽象与集成 | 提供基础接口和组件连接 |
| **Runtime** | JVM运行时 | 持久执行与状态 | 可恢复、可持久化的执行引擎 |
| **Harness** | JDK内置工具 | 预定义能力 | "内置电池"、开箱即用的工具集 |

### Harness 核心能力清单

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Harness                            │
├─────────────────────────────────────────────────────────────┤
│  🎯 Planning        - 多任务规划与Todo追踪                  │
│  🔄 Task Delegation - Subagent委托与上下文隔离              │
│  📁 Virtual FS      - 可插拔存储后端                        │
│  🧠 Token Manager   - 历史摘要与大结果驱逐                  │
│  ⚡ Code Execution  - 沙箱代码执行                          │
│  👤 Human Loop      - 人机交互节点                          │
└─────────────────────────────────────────────────────────────┘
```

---

## JVM 设计理念借鉴

### JVM 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                      JVM 架构                               │
├─────────────────────────────────────────────────────────────┤
│  Class Loader       → 动态加载、链接、初始化                │
│  Runtime Data Area  → 方法区、堆、栈、程序计数器            │
│  Execution Engine   → 解释器、JIT编译器、GC                 │
│  Native Interface   → JNI调用本地方法                       │
│  Bytecode Spec      → 统一中间表示，跨平台                  │
└─────────────────────────────────────────────────────────────┘
```

### 映射到 Agent Harness

| JVM组件 | Harness对应 | 设计目标 |
|---------|-------------|----------|
| **Bytecode规范** | Agent指令规范 | 定义统一的Agent行为描述语言 |
| **Class Loader** | Agent Loader | 动态加载Agent定义和工具模块 |
| **Runtime Data Area** | Context Memory | Agent执行上下文、对话历史、状态存储 |
| **Execution Engine** | Task Orchestrator | 任务编排、调度、执行策略 |
| **GC** | Context Eviction | 上下文压缩、历史摘要、内存优化 |
| **JNI** | Tool Bridge | 外部工具/API集成接口 |

---

## 框架核心架构草案

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户层 (User API)                        │
│  - 高级DSL定义Agent                                         │
│  - 预置Agent模板                                            │
├─────────────────────────────────────────────────────────────┤
│                    Harness层 (Built-in)                     │
│  - Planning Tools                                           │
│  - Subagent Manager                                         │
│  - Virtual Filesystem                                       │
│  - Token Optimizer                                          │
│  - Code Sandbox                                             │
│  - Human-in-the-loop                                        │
├─────────────────────────────────────────────────────────────┤
│                    Runtime层 (Execution)                    │
│  - Task Orchestrator                                        │
│  - Context Manager                                          │
│  - State Persistence                                        │
│  - Execution Strategies                                     │
├─────────────────────────────────────────────────────────────┤
│                    Core层 (Foundation)                      │
│  - Agent Specification (类似字节码规范)                     │
│  - Agent Loader                                             │
│  - Tool Bridge                                              │
│  - Memory Model                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 下一步工作

1. ✅ 完成核心架构设计细化
2. ⬜ 定义 Agent Specification 规范
3. ⬜ 设计 Core 层接口
4. ⬜ 实现 Runtime 层原型
5. ⬜ 构建 Harness 内置能力

---

## 参考资料

- [LangChain Agent Harness 概念](https://docs.langchain.com/oss/javascript/concepts)
- [Deep Agents Architecture](https://docs.langchain.com/oss/python/deepagents/frontend/overview)
- [JVM Specification](https://docs.oracle.com/javase/specs/)