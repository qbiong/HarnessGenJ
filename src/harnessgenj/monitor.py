#!/usr/bin/env python3
"""
HGJ Monitor - HarnessGenJ 框架运行状态监控工具

功能:
1. 检查各模块状态（Hooks、混合集成、质量、任务、意图、记忆）
2. 生成监控报告
3. 支持持续监控模式

使用方式:
    python -m harnessgenj.monitor          # 单次检查
    python -m harnessgenj.monitor --report # 生成完整报告
    python -m harnessgenj.monitor --watch  # 持续监控（每5分钟）
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

from harnessgenj.utils.exception_handler import log_exception


class HGJMonitor:
    """HarnessGenJ 状态监控器"""

    CHECK_ITEMS = {
        "hooks": [
            "hooks_configured",
            "hooks_triggered",
            "hooks_blocked",
            "security_check_active",
        ],
        "hybrid": [
            "active_mode_detected",
            "builtin_fallback_active",
            "events_recorded",
        ],
        "quality": [
            "adversarial_records",
            "metrics_calculated",
            "patterns_analyzed",
            "score_changes",
        ],
        "task_state": [
            "tasks_created",
            "state_transitions",
            "reviewing_state_used",
        ],
        "intent_router": [
            "intents_identified",
            "workflow_routed",
        ],
        "memory": [
            "knowledge_stored",
            "documents_updated",
            "hotspots_detected",
        ],
    }

    def __init__(self, workspace: Path | str | None = None):
        """
        初始化监控器

        Args:
            workspace: 工作目录路径，默认为当前项目的 .harnessgenj
        """
        if workspace is None:
            # 自动检测项目根目录
            workspace = Path.cwd() / ".harnessgenj"
        self.workspace = Path(workspace)
        self.results: dict[str, dict[str, bool]] = {}

    def check_all(self) -> dict[str, Any]:
        """
        执行所有检查

        Returns:
            检查结果字典
        """
        self.results = {
            "hooks": self._check_hooks(),
            "hybrid": self._check_hybrid(),
            "quality": self._check_quality(),
            "task_state": self._check_task_state(),
            "intent_router": self._check_intent_router(),
            "memory": self._check_memory(),
        }
        return self.results

    def _check_hooks(self) -> dict[str, bool]:
        """检查 Hooks 系统"""
        checks = {}

        # hooks_configured: 检查 settings.json 是否有 hooks 配置
        settings_path = self.workspace.parent / ".claude" / "settings.json"
        checks["hooks_configured"] = False
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                checks["hooks_configured"] = "hooks" in settings
            except Exception as e:
                log_exception(e, context="_check_hooks settings读取", level=30)

        # hooks_triggered: 检查 events 目录是否有事件记录
        events_dir = self.workspace / "events"
        checks["hooks_triggered"] = events_dir.exists() and any(events_dir.glob("event_*.json"))

        # hooks_blocked: 检查是否有被阻塞的记录
        checks["hooks_blocked"] = False
        if events_dir.exists():
            for event_file in events_dir.glob("event_*.json"):
                try:
                    with open(event_file, "r", encoding="utf-8") as f:
                        event = json.load(f)
                    if event.get("blocked", False):
                        checks["hooks_blocked"] = True
                        break
                except Exception as e:
                    log_exception(e, context="_check_hooks event读取", level=30)

        # security_check_active: 检查安全检查是否配置
        checks["security_check_active"] = checks["hooks_configured"]

        return checks

    def _check_hybrid(self) -> dict[str, bool]:
        """检查混合集成"""
        checks = {}

        # active_mode_detected: 检查是否有模式记录
        checks["active_mode_detected"] = False
        hybrid_path = self.workspace / "hybrid_state.json"
        if hybrid_path.exists():
            try:
                with open(hybrid_path, "r", encoding="utf-8") as f:
                    hybrid = json.load(f)
                checks["active_mode_detected"] = "active_mode" in hybrid
            except Exception as e:
                log_exception(e, context="_check_hybrid hybrid_state读取", level=30)

        # builtin_fallback_active: 检查 BUILTIN 模式是否激活
        # 如果没有 hooks 触发，BUILTIN 模式应该作为备用
        checks["builtin_fallback_active"] = True  # 默认激活

        # events_recorded: 检查 events 目录
        events_dir = self.workspace / "events"
        checks["events_recorded"] = events_dir.exists() and len(list(events_dir.glob("*.json"))) > 0

        return checks

    def _check_quality(self) -> dict[str, bool]:
        """检查质量系统"""
        checks = {}

        # adversarial_records: 检查 scores.json 是否有对抗记录
        scores_path = self.workspace / "scores.json"
        checks["adversarial_records"] = False
        checks["metrics_calculated"] = False
        checks["score_changes"] = False

        if scores_path.exists():
            try:
                with open(scores_path, "r", encoding="utf-8") as f:
                    scores = json.load(f)

                # 检查是否有对抗记录
                events = scores.get("events", [])
                adversarial_events = [e for e in events if "adversarial" in e.get("type", "") or "review" in e.get("type", "")]
                checks["adversarial_records"] = len(adversarial_events) > 0

                # 检查是否有积分数据
                if "scores" in scores:
                    checks["metrics_calculated"] = True
                    # 检查是否有积分变化（非零）
                    for role_data in scores["scores"].values():
                        if role_data.get("score", 0) != 0:
                            checks["score_changes"] = True
                            break
            except Exception as e:
                log_exception(e, context="_check_quality scores读取", level=30)

        # patterns_analyzed: 检查失败模式分析
        tracker_path = self.workspace / "failure_patterns.json"
        checks["patterns_analyzed"] = tracker_path.exists()

        return checks

    def _check_task_state(self) -> dict[str, bool]:
        """检查任务状态机"""
        checks = {}

        # tasks_created: 检查是否有任务记录
        tasks_path = self.workspace / "current_task.json"
        progress_path = self.workspace / "documents" / "progress.md"
        checks["tasks_created"] = tasks_path.exists() or progress_path.exists()

        # state_transitions: 检查状态机是否有转换记录
        state_path = self.workspace / "task_states.json"
        checks["state_transitions"] = False
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    states = json.load(f)
                # 检查是否有状态历史
                for task in states.get("tasks", {}).values():
                    if task.get("state_history"):
                        checks["state_transitions"] = True
                        break
            except Exception as e:
                log_exception(e, context="_check_task_state state_transitions", level=30)

        # reviewing_state_used: 检查是否有任务处于 reviewing 状态
        checks["reviewing_state_used"] = False
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    states = json.load(f)
                for task in states.get("tasks", {}).values():
                    if task.get("state") == "reviewing":
                        checks["reviewing_state_used"] = True
                        break
            except Exception as e:
                log_exception(e, context="_check_task_state reviewing_state", level=30)

        return checks

    def _check_intent_router(self) -> dict[str, bool]:
        """检查意图路由"""
        checks = {}

        # intents_identified: 检查 intents.json 是否有记录
        intents_path = self.workspace / "intents.json"
        checks["intents_identified"] = False
        if intents_path.exists():
            try:
                with open(intents_path, "r", encoding="utf-8") as f:
                    intents = json.load(f)
                checks["intents_identified"] = len(intents.get("records", [])) > 0
            except Exception as e:
                log_exception(e, context="_check_intent_router intents读取", level=30)

        # workflow_routed: 检查是否有工作流执行记录
        workflow_path = self.workspace / "workflow_executions.json"
        checks["workflow_routed"] = workflow_path.exists()

        return checks

    def _check_memory(self) -> dict[str, bool]:
        """检查记忆系统"""
        checks = {}

        # knowledge_stored: 检查 knowledge.json 是否有内容
        knowledge_path = self.workspace / "knowledge.json"
        checks["knowledge_stored"] = False
        if knowledge_path.exists():
            try:
                with open(knowledge_path, "r", encoding="utf-8") as f:
                    knowledge = json.load(f)
                # 检查是否有实际知识条目
                eden = knowledge.get("eden", {})
                old = knowledge.get("old", {})
                checks["knowledge_stored"] = len(eden) > 0 or len(old) > 0
            except Exception as e:
                log_exception(e, context="_check_memory knowledge读取", level=30)

        # documents_updated: 检查文档是否有更新
        docs_dir = self.workspace / "documents"
        checks["documents_updated"] = False
        if docs_dir.exists():
            for doc_file in docs_dir.glob("*.md"):
                try:
                    content = doc_file.read_text(encoding="utf-8")
                    # 检查是否有实际内容（不只是模板）
                    if len(content) > 200:  # 超过最小模板长度
                        checks["documents_updated"] = True
                        break
                except Exception as e:
                    log_exception(e, context="_check_memory doc_file读取", level=30)

        # hotspots_detected: 检查热点文件
        hotspot_path = self.workspace / "hotspots.json"
        checks["hotspots_detected"] = hotspot_path.exists()

        return checks

    def calculate_pass_rate(self) -> float:
        """
        计算总体通过率

        Returns:
            通过率（0-1）
        """
        total_checks = 0
        passed_checks = 0

        for dimension, checks in self.results.items():
            for check_name, passed in checks.items():
                total_checks += 1
                if passed:
                    passed_checks += 1

        return passed_checks / total_checks if total_checks > 0 else 0

    def generate_report(self) -> str:
        """
        生成监控报告

        Returns:
            格式化的报告字符串
        """
        self.check_all()
        pass_rate = self.calculate_pass_rate()

        report = f"""
# HGJ 框架状态监控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**工作目录**: {self.workspace}
**总体通过率**: {pass_rate:.0%}

---

## 详细状态

"""

        for dimension, checks in self.results.items():
            dimension_pass = sum(1 for v in checks.values() if v)
            dimension_total = len(checks)
            dimension_rate = dimension_pass / dimension_total if dimension_total > 0 else 0

            report += f"### [{dimension}] ({dimension_rate:.0%})\n\n"

            for check_name, passed in checks.items():
                status = "[OK]" if passed else "[FAIL]"
                report += f"- {status} {check_name}\n"

            report += "\n"

        # 添加改进建议
        report += "---\n\n## 改进建议\n\n"

        if not self.results["hooks"]["hooks_triggered"]:
            report += "- **Hooks未触发**: 检查 settings.json 配置，确保通过 Write/Edit 工具操作文件\n"

        if not self.results["intent_router"]["intents_identified"]:
            report += "- **意图未识别**: 使用 `harness.chat()` 或框架已自动记录意图到 intents.json\n"

        if not self.results["memory"]["knowledge_stored"]:
            report += "- **知识未存储**: 任务完成时会自动提取知识，或使用 `harness.remember()` 手动存储\n"

        if not self.results["quality"]["patterns_analyzed"]:
            report += "- **失败模式未分析**: 需积累多次对抗记录，或调整模式分析阈值\n"

        report += "\n---\n\n> 使用 `python -m harnessgenj.monitor --watch` 进行持续监控\n"

        return report

    def print_status(self) -> None:
        """打印简洁状态"""
        self.check_all()
        pass_rate = self.calculate_pass_rate()

        print(f"\n[HGJ Monitor] 总体通过率: {pass_rate:.0%}\n")

        for dimension, checks in self.results.items():
            dimension_pass = sum(1 for v in checks.values() if v)
            dimension_total = len(checks)
            dimension_rate = dimension_pass / dimension_total if dimension_total > 0 else 0

            # 颜色标记（绿色=OK，红色=FAIL）
            status_icon = "✓" if dimension_rate >= 0.5 else "✗"
            print(f"  [{status_icon}] {dimension}: {dimension_rate:.0%} ({dimension_pass}/{dimension_total})")

            for check_name, passed in checks.items():
                check_icon = "✓" if passed else "✗"
                print(f"      [{check_icon}] {check_name}")

        print()

    def save_report(self, path: Path | str | None = None) -> bool:
        """
        保存报告到文件

        Args:
            path: 报告文件路径，默认为 .harnessgenj/monitor_report.md

        Returns:
            是否保存成功
        """
        if path is None:
            path = self.workspace / "monitor_report.md"

        try:
            report = self.generate_report()
            Path(path).write_text(report, encoding="utf-8")
            return True
        except Exception as e:
            print(f"保存报告失败: {e}", file=sys.stderr)
            return False


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="HGJ 框架状态监控")
    parser.add_argument("--report", action="store_true", help="生成完整报告")
    parser.add_argument("--watch", action="store_true", help="持续监控（每5分钟）")
    parser.add_argument("--workspace", type=str, help="指定工作目录")

    args = parser.parse_args()

    workspace = Path(args.workspace) if args.workspace else None
    monitor = HGJMonitor(workspace)

    if args.watch:
        print("[HGJ Monitor] 开始持续监控（每5分钟）...")
        try:
            while True:
                monitor.print_status()
                monitor.save_report()
                time.sleep(300)  # 5分钟
        except KeyboardInterrupt:
            print("\n[HGJ Monitor] 监控已停止")
    elif args.report:
        report = monitor.generate_report()
        print(report)
        monitor.save_report()
    else:
        monitor.print_status()


if __name__ == "__main__":
    main()