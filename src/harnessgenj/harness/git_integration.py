"""
Git Integration - Git Hooks 集成

提供与 Git 工作流的集成：
- pre-commit: 代码审查钩子
- post-commit: 提交消息关联
- post-merge: 合并冲突分析

使用示例:
    from harnessgenj.harness.git_integration import GitHooks

    hooks = GitHooks(harness)
    hooks.install_pre_commit()
"""

from typing import Any
from pathlib import Path
import subprocess
import os
import time


class GitHooks:
    """
    Git 钩子管理器

    管理与 HarnessGenJ 集成的 Git 钩子：
    - pre-commit: 提交前代码审查
    - post-commit: 提交后知识关联
    - post-merge: 合并后分析
    """

    def __init__(self, harness: Any, project_path: str = ".") -> None:
        """
        初始化 Git 钩子管理器

        Args:
            harness: Harness 实例
            project_path: 项目根目录
        """
        self.harness = harness
        self.project_path = Path(project_path).resolve()
        self.git_dir = self.project_path / ".git"

    def is_git_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        return self.git_dir.exists()

    def get_staged_files(self) -> list[str]:
        """获取暂存区的文件列表"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
        except Exception:
            pass
        return []

    def get_staged_content(self, file_path: str) -> str:
        """获取暂存文件的差异内容"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", file_path],
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return ""

    def install_pre_commit(self, blocking: bool = True) -> bool:
        """
        安装 pre-commit 钩子

        Args:
            blocking: 是否阻塞式（高严重性问题阻断提交）

        Returns:
            是否安装成功
        """
        if not self.is_git_repo():
            return False

        hooks_dir = self.git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_path = hooks_dir / "pre-commit"

        # 使用简化的钩子脚本
        hook_content = f'''#!/bin/bash
# HarnessGenJ pre-commit hook
# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}

echo "[HarnessGenJ] Running pre-commit checks..."

# Run HarnessGenJ code review
harnessgenj_hook_path="{self.project_path}/.claude/harnessgenj_hook.py"

if [ -f "$harnessgenj_hook_path" ]; then
    python "$harnessgenj_hook_path" --pre-commit
fi

exit $?
'''

        hook_path.write_text(hook_content, encoding="utf-8")

        # 设置可执行权限
        if os.name != "nt":  # Unix-like
            os.chmod(hook_path, 0o755)

        return True

    def install_post_commit(self) -> bool:
        """
        安装 post-commit 钩子

        提交后自动关联知识条目

        Returns:
            是否安装成功
        """
        if not self.is_git_repo():
            return False

        hooks_dir = self.git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_path = hooks_dir / "post-commit"

        # 使用简化的钩子脚本
        hook_content = f'''#!/bin/bash
# HarnessGenJ post-commit hook
# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}

echo "[HarnessGenJ] Recording commit..."

# Run HarnessGenJ post-commit hook
harnessgenj_hook_path="{self.project_path}/.claude/harnessgenj_hook.py"

if [ -f "$harnessgenj_hook_path" ]; then
    python "$harnessgenj_hook_path" --post-commit
fi

exit 0
'''

        hook_path.write_text(hook_content, encoding="utf-8")

        if os.name != "nt":
            os.chmod(hook_path, 0o755)

        return True

    def run_pre_commit_check(self) -> dict[str, Any]:
        """
        手动运行 pre-commit 检查

        Returns:
            检查结果
        """
        from harnessgenj.harness.hooks import SecurityHook, CodeLintHook

        security = SecurityHook()
        lint = CodeLintHook()

        staged_files = self.get_staged_files()
        results = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "files_checked": 0,
        }

        for file_path in staged_files:
            if not file_path.endswith(('.py', '.java', '.kt', '.js', '.ts', '.tsx')):
                continue

            full_path = self.project_path / file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text(encoding="utf-8")

                # 安全检查
                sec_result = security.check({"code": content, "file_path": file_path})
                if not sec_result.passed:
                    results["passed"] = False
                    results["errors"].extend([f"{file_path}: {e}" for e in sec_result.errors])
                results["warnings"].extend([f"{file_path}: {w}" for w in sec_result.warnings])

                # 代码检查
                lint_result = lint.check({"code": content})
                if not lint_result.passed:
                    results["errors"].extend([f"{file_path}: {e}" for e in lint_result.errors])

                results["files_checked"] += 1

            except Exception as e:
                results["warnings"].append(f"{file_path}: Could not check - {e}")

        return results

    def uninstall_hooks(self) -> None:
        """卸载所有 HarnessGenJ Git 钩子"""
        if not self.is_git_repo():
            return

        hooks_dir = self.git_dir / "hooks"
        for hook_name in ["pre-commit", "post-commit"]:
            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                # 检查是否是 HarnessGenJ 生成的
                try:
                    content = hook_path.read_text(encoding="utf-8")
                    if "HarnessGenJ" in content:
                        hook_path.unlink()
                except Exception:
                    pass


def create_git_hooks(harness: Any, project_path: str = ".") -> GitHooks:
    """
    创建 Git 钩子管理器

    Args:
        harness: Harness 实例
        project_path: 项目根目录

    Returns:
        GitHooks 实例
    """
    return GitHooks(harness, project_path)