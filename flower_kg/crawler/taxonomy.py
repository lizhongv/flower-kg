"""生物学 7 级分类（界门纲目科属种）的累积器。

替代原 ``crawler/main.py`` 中的 7 个全局可变列表
（Kingdom/Phylum/Class/Order/Family/Genus/Species），消除全局状态。
"""

from __future__ import annotations

from pathlib import Path

LEVELS: tuple[str, ...] = ("界", "门", "纲", "目", "科", "属", "种")


class TaxonomyCollector:
    """跨花卉去重地累积 7 级分类，最后写出 7 个 ``<level>.txt`` 文件。"""

    def __init__(self) -> None:
        # 用 dict 保留插入顺序，同时 O(1) 去重
        self._buckets: dict[str, dict[str, None]] = {lvl: {} for lvl in LEVELS}

    def add(self, parsed: dict[str, list[str]]) -> None:
        """累加一条已经按层级拆好的分类记录。"""
        for level, items in parsed.items():
            if level not in self._buckets:
                continue
            for item in items:
                self._buckets[level].setdefault(item, None)

    def items(self, level: str) -> list[str]:
        """返回某一级分类的累计列表（保持插入顺序）。"""
        return list(self._buckets.get(level, {}).keys())

    def write_to(self, data_dir: Path) -> None:
        """将每一级分类写入 ``data_dir/<level>.txt``。"""
        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        for level in LEVELS:
            path = data_dir / f"{level}.txt"
            with open(path, "w", encoding="utf-8") as fw:
                for item in self.items(level):
                    fw.write(item + "\n")
