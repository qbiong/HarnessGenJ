"""
JSON Storage - 使用JSON文件存储结构化数据

轻量化存储，无需数据库:
- 任务状态
- 执行上下文
- 配置信息
"""

from pathlib import Path
from typing import Any
import json
import time


class JsonStorage:
    """
    JSON存储 - 轻量化文件存储

    特点:
    - 结构化数据存储
    - 原子写入
    - 自动备份
    - 无需数据库
    """

    def __init__(self, base_path: Path | str = ".harnessgenj/data") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """获取文件路径"""
        return self.base_path / f"{key}.json"

    def save(self, key: str, data: dict[str, Any]) -> bool:
        """
        保存数据

        Args:
            key: 数据键名
            data: 数据内容

        Returns:
            是否保存成功
        """
        file_path = self._get_file_path(key)

        # 添加元数据
        data["_meta"] = {
            "saved_at": time.time(),
            "version": 1,
        }

        # 原子写入 (先写临时文件，再重命名)
        temp_path = file_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.rename(file_path)

        return True

    def load(self, key: str) -> dict[str, Any] | None:
        """
        加载数据

        Args:
            key: 数据键名

        Returns:
            数据内容
        """
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return None

    def delete(self, key: str) -> bool:
        """删除数据"""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查数据是否存在"""
        return self._get_file_path(key).exists()

    def list_keys(self) -> list[str]:
        """列出所有键"""
        return [p.stem for p in self.base_path.glob("*.json")]

    def clear_all(self) -> int:
        """清空所有数据"""
        count = 0
        for file in self.base_path.glob("*.json"):
            file.unlink()
            count += 1
        return count

    def get_size(self) -> int:
        """获取存储大小 (字节)"""
        total = 0
        for file in self.base_path.glob("*.json"):
            total += file.stat().st_size
        return total


class TaskStateStorage(JsonStorage):
    """
    任务状态存储 - 专门存储任务状态

    用于持久化任务队列状态
    """

    def __init__(self, base_path: Path | str = ".harnessgenj/data/tasks") -> None:
        super().__init__(base_path)

    def save_task_state(self, task_id: str, state: dict[str, Any]) -> bool:
        """保存任务状态"""
        return self.save(f"task_{task_id}", state)

    def load_task_state(self, task_id: str) -> dict[str, Any] | None:
        """加载任务状态"""
        return self.load(f"task_{task_id}")

    def list_task_ids(self) -> list[str]:
        """列出所有任务ID"""
        keys = self.list_keys()
        return [k.replace("task_", "") for k in keys if k.startswith("task_")]

    def save_queue_snapshot(self, queue_data: dict[str, Any]) -> bool:
        """保存队列快照"""
        return self.save("queue_snapshot", queue_data)

    def load_queue_snapshot(self) -> dict[str, Any] | None:
        """加载队列快照"""
        return self.load("queue_snapshot")


class ContextStorage(JsonStorage):
    """
    上下文存储 - 存储执行上下文

    用于持久化Agent执行上下文
    """

    def __init__(self, base_path: Path | str = ".harnessgenj/data/contexts") -> None:
        super().__init__(base_path)

    def save_context(self, context_id: str, context: dict[str, Any]) -> bool:
        """保存上下文"""
        return self.save(f"ctx_{context_id}", context)

    def load_context(self, context_id: str) -> dict[str, Any] | None:
        """加载上下文"""
        return self.load(f"ctx_{context_id}")

    def list_context_ids(self) -> list[str]:
        """列出所有上下文ID"""
        keys = self.list_keys()
        return [k.replace("ctx_", "") for k in keys if k.startswith("ctx_")]