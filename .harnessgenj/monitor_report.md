
# HGJ 框架状态监控报告

**生成时间**: 2026-04-11 11:20:56
**工作目录**: C:\Users\biong\Desktop\HarnessGenJ\.harnessgenj
**总体通过率**: 53%

---

## 详细状态

### [hooks] (75%)

- [OK] hooks_configured
- [OK] hooks_triggered
- [FAIL] hooks_blocked
- [OK] security_check_active

### [hybrid] (67%)

- [FAIL] active_mode_detected
- [OK] builtin_fallback_active
- [OK] events_recorded

### [quality] (50%)

- [FAIL] adversarial_records
- [OK] metrics_calculated
- [OK] score_changes
- [FAIL] patterns_analyzed

### [task_state] (33%)

- [OK] tasks_created
- [FAIL] state_transitions
- [FAIL] reviewing_state_used

### [intent_router] (50%)

- [OK] intents_identified
- [FAIL] workflow_routed

### [memory] (33%)

- [FAIL] knowledge_stored
- [OK] documents_updated
- [FAIL] hotspots_detected

---

## 改进建议

- **知识未存储**: 任务完成时会自动提取知识，或使用 `harness.remember()` 手动存储
- **失败模式未分析**: 需积累多次对抗记录，或调整模式分析阈值

---

> 使用 `python -m harnessgenj.monitor --watch` 进行持续监控
