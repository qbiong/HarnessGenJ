"""
Memory Storage - 内存存储 (默认，无需任何配置)

最快的存储方式，适合临时使用或测试
"""

from typing import Any
from copy import deepcopy


class MemoryStorage:
    """
    内存存储 - 默认存储方式

    特点:
    - 无需配置
    - 最快速度
    - 进程内共享
    - 重启后清空

    适用场景:
    - 临时存储
    - 测试环境
    - 短期任务
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._stats = {
            "reads": 0,
            "writes": 0,
            "deletes": 0,
        }

    def save(self, key: str, data: Any) -> bool:
        """保存数据"""
        self._data[key] = deepcopy(data)
        self._stats["writes"] += 1
        return True

    def load(self, key: str) -> Any | None:
        """加载数据"""
        self._stats["reads"] += 1
        if key in self._data:
            return deepcopy(self._data[key])
        return None

    def delete(self, key: str) -> bool:
        """删除数据"""
        if key in self._data:
            del self._data[key]
            self._stats["deletes"] += 1
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查数据是否存在"""
        return key in self._data

    def list_keys(self) -> list[str]:
        """列出所有键"""
        return list(self._data.keys())

    def clear(self) -> int:
        """清空所有数据"""
        count = len(self._data)
        self._data.clear()
        return count

    def size(self) -> int:
        """获取数据条目数"""
        return len(self._data)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "size": self.size(),
        }


class MemoryKnowledgeBase:
    """
    内存知识库 - 默认知识存储

    无需配置，直接使用
    """

    def __init__(self) -> None:
        self._knowledge: dict[str, dict[str, Any]] = {}

    def save(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
        """保存知识"""
        self._knowledge[key] = {
            "content": content,
            "metadata": metadata or {},
        }
        return True

    def load(self, key: str) -> str | None:
        """加载知识"""
        if key in self._knowledge:
            return self._knowledge[key]["content"]
        return None

    def delete(self, key: str) -> bool:
        """删除知识"""
        if key in self._knowledge:
            del self._knowledge[key]
            return True
        return False

    def search(self, query: str) -> list[dict[str, Any]]:
        """搜索知识"""
        results = []
        query_lower = query.lower()
        for key, data in self._knowledge.items():
            if query_lower in key.lower() or query_lower in data["content"].lower():
                results.append({
                    "key": key,
                    "content": data["content"][:200] + "...",
                })
        return results

    def list_all(self) -> list[str]:
        """列出所有知识键"""
        return list(self._knowledge.keys())