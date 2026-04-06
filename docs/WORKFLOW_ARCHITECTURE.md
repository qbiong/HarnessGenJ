# HarnessGenJ 工作流系统架构

## 一、工作流总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户请求入口                                        │
│                              ↓                                              │
│                     ┌─────────────────┐                                    │
│                     │  Intent Pipeline │ ← 意图识别入口                      │
│                     │   (意图路由器)    │                                    │
│                     └────────┬────────┘                                    │
│                              │                                              │
│           ┌──────────────────┼──────────────────┐                          │
│           ↓                  ↓                  ↓                          │
│    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                  │
│    │ Development  │   │   BugFix     │   │   Inquiry/   │                  │
│    │   Pipeline   │   │   Pipeline   │   │  Management  │                  │
│    │  (含GAN对抗)  │   │  (含GAN对抗) │   │   Pipeline   │                  │
│    └──────────────┘   └──────────────┘   └──────────────┘                  │
│           │                  │                  │                          │
│           └──────────────────┴──────────────────┘                          │
│                              ↓                                              │
│                     ┌─────────────────┐                                    │
│                     │  Memory Manager  │ ← JVM 分代记忆                     │
│                     └─────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、5 种工作流类型

| 工作流 | 阶段数 | GAN对抗 | 优先级 | 描述 |
|--------|--------|---------|--------|------|
| `intent_pipeline` | 4 | ❌ | - | 意图识别入口，路由分发 |
| `development_pipeline` | 8 | ✅ | P1 | 功能开发（代码变更） |
| `bugfix_pipeline` | 8 | ✅ | P0 | Bug修复（代码变更） |
| `inquiry_pipeline` | 3 | ❌ | P2 | 问题咨询（无代码变更） |
| `management_pipeline` | 3 | ❌ | P2 | 项目管理（无代码变更） |

---

## 三、意图路由规则

```
用户消息                    意图类型           目标工作流            优先级
─────────────────────────────────────────────────────────────────────────
"我需要一个登录功能"    →   DEVELOPMENT   →   development_pipeline  →  P1
"有个bug需要修复"       →   BUGFIX       →   bugfix_pipeline       →  P0
"项目进度如何"          →   MANAGEMENT   →   management_pipeline   →  P2
"什么是JVM记忆管理"     →   INQUIRY      →   inquiry_pipeline      →  P2
```

---

## 四、各工作流详细阶段

### 4.1 Intent Pipeline（意图识别流水线）

```
receive_input ──→ identify_intent ──→ extract_entities ──→ route_workflow
     │                   │                    │                   │
     ↓                   ↓                    ↓                   ↓
 存储消息          识别意图类型          提取实体信息         创建任务并路由
 [Eden区]          [Survivor区]          [Survivor区]         [Survivor区]
```

### 4.2 Development Pipeline（开发流水线）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ requirements│ ──→ │    design   │ ──→ │ development │ ──→ │ adversarial │
│             │     │             │     │             │     │   _review   │
│  需求识别    │     │  架构规划    │     │  代码编写    │     │  对抗审查    │
│ [Old区]     │     │  [Old区]    │     │  [Old区]    │     │  [GAN]      │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    ↓
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│fix_and_opt  │ ──→ │  unit_test  │ ──→ │ integration │ ──→ │  acceptance │
│             │     │             │     │    _test    │     │             │
│  修复优化    │     │  单元测试    │     │  集成测试    │     │  完成验收    │
│ [Old区]     │     │  [Old区]    │     │  [Old区]    │     │  [Old区]    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**阶段角色分配**:

| 阶段 | 角色 | 类型 | 对抗 |
|------|------|------|------|
| requirements | ProductManager | 生成器 | ❌ |
| design | Architect | 生成器 | ❌ |
| development | Developer | 生成器 | ✅ |
| adversarial_review | CodeReviewer | 判别器 | ✅ |
| fix_and_optimize | Developer | 生成器 | ❌ |
| unit_test | Tester | 生成器 | ❌ |
| integration_test | Tester | 生成器 | ❌ |
| acceptance | ProjectManager | 协调者 | ❌ |

### 4.3 BugFix Pipeline（Bug修复流水线）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   analysis  │ ──→ │  fix_design │ ──→ │ fix_implem  │ ──> │ adversarial │
│             │     │             │     │             │     │_verification│
│  问题分析    │     │  修复方案    │     │  代码修复    │     │  对抗验证    │
│ [Old区]     │     │  [Old区]    │     │  [Old区]    │     │  [GAN]      │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    ↓
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   edge_fix  │ ──→ │ regression  │ ──→ │ integration │ ──→ fix_completion
│             │     │    _test    │     │_verification│
│  边界修复    │     │  回归测试    │     │  集成验证    │
│ [Old区]     │     │  [Old区]    │     │  [Old区]    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**关键差异**: Bug修复默认使用 `aggressive` 强度的对抗审查，由 BugHunter 执行更激进的探测。

### 4.4 Inquiry Pipeline（咨询流水线）

```
understand_question ──→ retrieve_info ──→ generate_answer
        │                    │                  │
        ↓                    ↓                  ↓
    问题理解            信息检索            答案生成
   [Survivor区]        [Survivor区]        [Eden区]
```

### 4.5 Management Pipeline（管理流水线）

```
collect_status ──→ analyze ──→ decide
      │              │           │
      ↓              ↓           ↓
  状态收集        分析报告      决策建议
 [Survivor区]    [Old区]      [Survivor区]
```

---

## 五、工作流协同方式

### 5.1 数据流协同

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WorkflowExecutor                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐                                                          │
│   │   Stage 1   │ ──outputs──→ ┌─────────────┐                            │
│   │             │              │   Context   │ ← 阶段间数据传递             │
│   └─────────────┘              │   Cache     │                            │
│         │                      └──────┬──────┘                            │
│         │                             │                                    │
│         ↓                             ↓                                    │
│   ┌─────────────┐              ┌─────────────┐                            │
│   │ Memory Map  │ ←─────────── │   Stage 2   │                            │
│   │   Writer    │              │   (load)    │                            │
│   └─────────────┘              └─────────────┘                            │
│         │                                                                   │
│         ↓                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                        Memory Manager                                │ │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │ │
│   │  │ Permanent │ │    Old    │ │ Survivor  │ │   Eden    │           │ │
│   │  │   区      │ │    区     │ │    区     │ │    区     │           │ │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 阶段间数据传递机制

```python
# 1. 阶段执行产生输出
outputs = handler(inputs)  # {"design_doc": "# 设计文档", ...}

# 2. 写入 Memory（根据 Mapping）
executor.write_outputs(stage, outputs, mapping)
# → store_document("design", content)  # 存储到 Old 区

# 3. 同时更新上下文缓存
executor._context["design_doc"] = outputs["design_doc"]

# 4. 下一个阶段加载输入
inputs = executor.load_inputs(next_stage, next_mapping)
# → 从 context 或 memory 获取
```

### 5.3 GAN 对抗机制协同

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GAN 对抗审查流程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐     产出代码      ┌──────────────┐                      │
│   │   Developer  │ ────────────────→ │ CodeReviewer │                      │
│   │   (生成器)    │                   │  (判别器)     │                      │
│   └──────────────┘                   └──────┬───────┘                      │
│         ↑                                   │                              │
│         │              ┌───────────────────┘                              │
│         │              │                                                  │
│         │         审查结果                                                  │
│         │              │                                                  │
│         │    ┌─────────┴─────────┐                                        │
│         │    ↓                   ↓                                        │
│         │  通过               不通过                                       │
│         │    │                   │                                        │
│         │    ↓                   ↓                                        │
│   ┌─────┴────┐         ┌──────────────┐                                   │
│   │ 完成阶段  │         │ fix_and_opt  │ ← 修复问题                        │
│   │          │         │              │                                   │
│   └──────────┘         └──────┬───────┘                                   │
│                               │                                            │
│                               └──────→ 重新提交审查（最多 3 轮）            │
│                                                                             │
│   质量分数 → 更新 MemoryEntry.quality_score → 影响 GC 存活判定             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 六、Memory Mapping 完整映射

### 6.1 开发流水线映射

| 阶段 | 输入来源 | 输出目标 | 记忆区域 |
|------|----------|----------|----------|
| requirements | task, knowledge | document(requirements), knowledge(acceptance_criteria) | Old, Permanent |
| design | document(requirements), knowledge(user_stories) | document(design), knowledge(tech_stack) | Old, Permanent |
| development | document(design, requirements) | document(development), knowledge(code_snapshot) | Old |
| adversarial_review | knowledge(code_snapshot), document(development) | UPDATE_QUALITY, knowledge(last_review_issues) | Old |
| fix_and_optimize | knowledge(code_snapshot, last_review_issues) | document(development) | Old |
| unit_test | document(development), knowledge(acceptance_criteria) | document(testing), knowledge(coverage_report) | Old |
| integration_test | document(development), knowledge(coverage_report) | document(testing) | Old |
| acceptance | document(testing), knowledge(coverage_report, quality_score) | document(progress), task(completion_record) | Old, Survivor |

### 6.2 JVM 分代存储规则

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          JVM 分代记忆堆                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Permanent 区（永久代）                             │   │
│  │  • 项目核心知识 (project_name, tech_stack)                           │   │
│  │  • 验收标准 (acceptance_criteria)                                    │   │
│  │  • 经验总结 (lessons_learned)                                        │   │
│  │  → 永不回收                                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Old 区（老年代）                                │   │
│  │  • 需求文档 (requirements)                                           │   │
│  │  • 设计文档 (design)                                                 │   │
│  │  • 开发文档 (development)                                            │   │
│  │  • 测试报告 (testing)                                                │   │
│  │  • 进度文档 (progress)                                               │   │
│  │  → Major GC 清理，质量感知：高质量优先存活                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────┐    ┌─────────────────────────┐               │
│  │     Survivor 区         │    │     Survivor 区         │               │
│  │  • 当前任务             │    │     GC 交换区           │               │
│  │  • 意图结果             │    │                         │               │
│  │  • 完成记录             │    │                         │               │
│  └─────────────────────────┘    └─────────────────────────┘               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Eden 区（新生代）                                │   │
│  │  • 用户消息                                                           │   │
│  │  • 会话内容                                                           │   │
│  │  → Minor GC 频繁清理                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、典型工作流执行示例

### 示例 1: 功能开发

```
用户: "我需要一个用户登录功能"
  │
  ↓
Intent Pipeline:
  1. receive_input: 存储 "我需要一个用户登录功能"
  2. identify_intent: 识别为 DEVELOPMENT
  3. extract_entities: 提取 feature_name="登录功能"
  4. route_workflow: 创建 TASK-xxx, 路由到 development_pipeline
  │
  ↓
Development Pipeline:
  1. requirements: 产出需求文档 → Old区
  2. design: 产出设计文档 → Old区
  3. development: 产出代码 → Old区
  4. adversarial_review: 对抗审查 → 质量分数 85
  5. fix_and_optimize: 优化代码 → Old区
  6. unit_test: 测试报告 → Old区
  7. integration_test: 集成报告 → Old区
  8. acceptance: 验收通过 → Old区(progress)
```

### 示例 2: Bug 修复

```
用户: "订单支付后状态没有正确更新"
  │
  ↓
Intent Pipeline:
  1. identify_intent: 识别为 BUGFIX (优先级 P0)
  2. route_workflow: 路由到 bugfix_pipeline
  │
  ↓
BugFix Pipeline:
  1. analysis: 定位根因 → knowledge(root_cause)
  2. fix_design: 设计方案 → knowledge(fix_plan)
  3. fix_implementation: 修复代码 → Old区(development)
  4. adversarial_verification: BugHunter 激进审查 → 质量分数
  5. edge_fix: 边界修复 → Old区
  6. regression_test: 回归测试 → Old区(testing)
  7. integration_verification: 集成验证 → Old区
  8. fix_completion: 经验总结 → Permanent区(lessons_learned)
```

---

## 八、关键设计原则

1. **所有代码变更必经 GAN 对抗审查**
   - Development Pipeline: normal 强度 (CodeReviewer)
   - BugFix Pipeline: aggressive 强度 (BugHunter)

2. **渐进式披露**
   - 每个角色只获取最小必要上下文
   - 项目经理: 完整文档
   - 开发者: 需求摘要 + 设计摘要
   - 审查者: 代码 + 质量历史

3. **质量数据驱动**
   - 对抗审查结果 → 更新 MemoryEntry.quality_score
   - 质量分数 → 影响 GC 存活判定
   - 高质量内容优先加载到上下文

4. **双向积分激励**
   - 生成器: 一轮通过 +10, 发现问题 -5
   - 判别器: 发现问题 +10, 误报 -3