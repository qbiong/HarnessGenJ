# HarnessGenJ 架构重构方案

## 一、问题诊断

### 1.1 冗余代码统计

| 模块 | 代码量 | 状态 | 决策 |
|------|--------|------|------|
| kernel/* | ~2250行 | 完全未使用 | 删除 |
| mcp/server.py | 620行 | 完全未使用 | 删除 |
| tools/* | ~400行 | 完全未使用 | 删除 |
| harness/context_engine.py | 533行 | 未使用(有context_assembler) | 删除 |
| harness/filesystem.py | ~200行 | 完全未使用 | 删除 |
| harness/planning.py | ~200行 | 完全未使用 | 删除 |
| harness/subagent.py | ~200行 | 完全未使用 | 删除 |

**冗余代码总计**: ~4400行 (31%)

### 1.2 核心问题：数据流割裂

```
当前状态：

project/state.py ←→ engine.py ←→ memory/manager.py
      ↑                              ↑
   文档管理                      会话存储
   任务统计                      (仅基础功能)
   
两者互不连通！
```

**JVM 设计理念未被实现**：
- `memory/heap.py` 的分代分配从未被调用
- `memory/gc.py` 的垃圾回收从未被触发
- `memory/hotspot.py` 的热点检测从未被使用

## 二、重构方案

### 2.1 统一数据流架构

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────┐
│                  Harness                     │
│  (统一入口，~400行)                          │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │          MemoryManager               │   │
│  │  (核心调度器，整合所有数据)           │   │
│  ├─────────────────────────────────────┤   │
│  │  Permanent (项目知识)                │   │
│  │  - AGENTS.md                        │   │
│  │  - 项目配置                         │   │
│  │  - 角色定义                         │   │
│  │                                     │   │
│  │  Old (文档资产)                      │   │
│  │  - requirements.md                  │   │
│  │  - design.md                        │   │
│  │  - progress.md                      │   │
│  │                                     │   │
│  │  Survivor (当前任务)                 │   │
│  │  - 活跃任务上下文                    │   │
│  │  - 任务依赖关系                      │   │
│  │                                     │   │
│  │  Eden (会话消息)                     │   │
│  │  - 用户对话                         │   │
│  │  - AI响应                          │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌───────────────┐  ┌───────────────┐      │
│  │  GC (回收)    │  │ Hotspot (热点) │      │
│  │  - 文档压缩   │  │  - 任务频率   │      │
│  │  - 会话清理   │  │  - 知识热度   │      │
│  └───────────────┘  └───────────────┘      │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │       ContextAssembler              │   │
│  │  (上下文装配，按需从Memory提取)       │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │          Workflow                    │   │
│  │  (工作流，驱动角色协作)               │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 2.2 文件结构（精简后）

```
src/HarnessGenJ/
├── __init__.py          # 导出
├── engine.py            # Harness 入口 (~400行)
│
├── memory/              # 核心记忆系统
│   ├── __init__.py
│   ├── manager.py       # MemoryManager (整合调度)
│   ├── heap.py          # 分代堆 (保留，改造)
│   ├── gc.py            # 垃圾回收 (保留，激活)
│   └── hotspot.py       # 热点检测 (保留，激活)
│
├── context.py           # 上下文装配 (合并 context_assembler)
│
├── project.py           # 项目实体 (简化自 project/)
│
├── roles/               # 角色系统
│   ├── __init__.py
│   ├── base.py          # 基类
│   ├── developer.py
│   ├── tester.py
│   ├── product_manager.py
│   ├── architect.py
│   ├── doc_writer.py
│   └── project_manager.py
│
├── workflow/            # 工作流
│   ├── __init__.py
│   ├── pipeline.py      # 流水线定义
│   └── coordinator.py   # 协调器
│
├── storage/             # 存储后端
│   ├── __init__.py
│   ├── markdown.py      # Markdown存储
│   └── memory.py        # 内存存储
│
├── hooks.py             # 质量门禁
├── session.py           # 会话管理
├── guide.py             # 引导系统
└── cli.py               # 命令行
```

### 2.3 核心改造：MemoryManager

```python
class MemoryManager:
    """
    统一记忆管理器 - 整合项目文档和会话消息
    
    数据分层:
    - Permanent: 项目知识 (AGENTS.md, 角色定义)
    - Old: 文档资产 (requirements, design, progress)
    - Survivor: 当前任务上下文
    - Eden: 会话消息
    
    调度策略:
    - GC: 自动清理过期数据，压缩文档
    - Hotspot: 检测高频访问，优化装配
    """
    
    def __init__(self, workspace: str = ".HarnessGenJ"):
        self.heap = MemoryHeap()
        self.gc = GarbageCollector()
        self.hotspot = HotspotDetector()
        
        # 加载持久化数据
        self._load_from_disk(workspace)
    
    # === 统一存储接口 ===
    
    def store_knowledge(self, key: str, content: str) -> None:
        """存储核心知识 → Permanent"""
        self.heap.permanent.store_knowledge(key, content)
    
    def store_document(self, doc_type: str, content: str) -> None:
        """存储项目文档 → Old"""
        self.heap.old.put(MemoryEntry(
            id=doc_type,
            content=content,
            importance=70,
        ))
    
    def store_message(self, message: str, role: str) -> None:
        """存储会话消息 → Eden"""
        self.heap.allocate(message, importance=50)
    
    def store_task(self, task_id: str, task_info: dict) -> None:
        """存储当前任务 → Survivor"""
        self.heap.get_active_survivor().put(MemoryEntry(
            id=task_id,
            content=json.dumps(task_info),
            importance=80,
        ))
    
    # === 统一检索接口 ===
    
    def get_context_for_llm(self, role: str, max_tokens: int) -> str:
        """
        为 LLM 装配上下文 (渐进式披露)
        
        流程:
        1. Permanent 全量注入
        2. Old 按相关性摘要注入
        3. Survivor 当前任务注入
        4. Eden 最近 N 条注入
        """
        sections = []
        tokens = 0
        
        # 1. Permanent (必须)
        for entry in self.heap.permanent.list_entries():
            sections.append(entry.content)
            tokens += self._estimate_tokens(entry.content)
        
        # 2. Survivor (当前任务)
        for entry in self.heap.get_active_survivor().list_entries():
            if tokens < max_tokens * 0.7:
                sections.append(entry.content)
                tokens += self._estimate_tokens(entry.content)
        
        # 3. Old (按需)
        if tokens < max_tokens * 0.8:
            hotspots = self.hotspot.detect_hotspots()
            for hotspot in hotspots[:3]:
                doc = self.heap.old.get(hotspot.name)
                if doc:
                    sections.append(doc.content[:500])  # 摘要
        
        # 4. Eden (最近)
        if tokens < max_tokens * 0.9:
            for entry in self.heap.eden.list_entries()[-5:]:
                sections.append(entry.content)
        
        return "\n\n".join(sections)
    
    # === 调度机制 ===
    
    def on_access(self, key: str) -> None:
        """访问时记录热点"""
        self.hotspot.record_knowledge_reference(key)
    
    def on_store(self) -> None:
        """存储时检查是否需要 GC"""
        if self.heap.eden.is_full():
            self.gc.minor_gc(self.heap)
        if self.heap.old.is_full():
            self.gc.major_gc(self.heap)
```

### 2.4 engine.py 改造

```python
class Harness:
    def __init__(self, project_name: str, workspace: str = ".HarnessGenJ"):
        # 核心组件：统一记忆管理
        self.memory = MemoryManager(workspace)
        self.memory.store_knowledge("project_name", project_name)
        
        # 工作流协调
        self.coordinator = WorkflowCoordinator()
        
        # 会话
        self.session = SessionManager()
    
    # === 用户接口 ===
    
    def receive_request(self, request: str, request_type: str = "feature") -> dict:
        """接收用户请求"""
        task_id = self._generate_task_id()
        
        # 存储到 Survivor (当前任务)
        self.memory.store_task(task_id, {
            "request": request,
            "type": request_type,
            "status": "pending",
        })
        
        # 存储到 Eden (会话记录)
        self.memory.store_message(request, role="user")
        
        # 触发 GC 检查
        self.memory.on_store()
        
        return {"task_id": task_id, "status": "received"}
    
    def complete_task(self, task_id: str, summary: str) -> bool:
        """完成任务"""
        # 更新任务状态
        self.memory.store_task(task_id, {"status": "completed", "summary": summary})
        
        # 记录到 Old (进度文档)
        progress = self.memory.heap.old.get("progress")
        updated = (progress.content if progress else "") + f"\n- {task_id}: {summary}"
        self.memory.store_document("progress", updated)
        
        # 清理 Survivor
        self.memory.heap.get_active_survivor().remove(task_id)
        
        return True
    
    def get_context_prompt(self, role: str = "developer") -> str:
        """获取上下文提示 (用于 LLM)"""
        # 记录访问热点
        self.memory.on_access(f"context_for_{role}")
        
        # 装配上下文
        return self.memory.get_context_for_llm(role, max_tokens=4000)
```

## 三、执行步骤

### Phase 1: 删除冗余代码

删除以下模块:
- `kernel/` 整个目录
- `mcp/` 整个目录
- `tools/` 整个目录
- `harness/context_engine.py`
- `harness/filesystem.py`
- `harness/planning.py`
- `harness/subagent.py`

### Phase 2: 合并 project/ 到 memory/

- `project/state.py` → `memory/manager.py` 整合
- `project/document.py` → `memory/heap.py` 的 Old 区

### Phase 3: 合并 context_assembler.py

- `harness/context_assembler.py` → `context.py`
- 作为 MemoryManager 的视图层

### Phase 4: 激活 JVM 功能

- 在 MemoryManager 中启用 GC
- 在 MemoryManager 中启用 Hotspot
- 实现渐进式披露的数据流

### Phase 5: 精简 engine.py

- 移除冗余逻辑
- 统一通过 MemoryManager 操作

## 四、预期效果

| 指标 | 当前 | 重构后 |
|------|------|--------|
| 代码量 | ~14200行 | ~8000行 |
| 模块数 | 35+ | 15 |
| 数据入口 | 3个(project/memory/engine) | 1个(memory) |
| JVM功能激活 | 0% | 100% |