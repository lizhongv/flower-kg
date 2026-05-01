"""根实体与分类骨架的构建。

对应原 ``createKG.py::createEntity0`` 的 step 0–4，按职责拆为 4 个函数。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from py2neo import Graph

logger = logging.getLogger(__name__)

# 与爬虫保持同源
PAGE_SIZE: tuple[int, ...] = (0, 12, 20, 34, 42, 46)
TAXONOMY_LEVELS: tuple[str, ...] = ("界", "门", "纲", "目", "科", "属", "种")


def build_root_categories(
    graph: Graph,
    data_dir: Path,
    title_classes: list[str],
) -> None:
    """构建根节点 ``花卉大全`` 与 5 个一级分类节点，并连接二级分类。

    对应原 step 0 + step 1。
    """
    graph.run("CREATE (:花卉大全 {id: '0', name: '花卉大全'})")
    for i, c in enumerate(title_classes):
        graph.run(
            """
            MERGE (a {name: '花卉大全'})
            MERGE (b:花卉大全 {id:$id, name:$name})
            MERGE (a)-[:划分]-> (b)
            """,
            id=str(i + 1),
            name=c,
        )
    logger.info("step 0 完成：根节点 + 一级分类")

    master_path = data_dir / "花卉大全.txt"
    with open(master_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i in range(5):
        for j in range(PAGE_SIZE[i], PAGE_SIZE[i + 1]):
            tokens = lines[j].split()
            if not tokens:
                continue
            sub_class = tokens[-1]
            graph.run(
                f"""
                MERGE (a {{name: $title}})
                MERGE (b:{title_classes[i]} {{id:$id, name:$name}})
                MERGE (a)-[:划分]-> (b)
                """,
                title=title_classes[i],
                id=str(j),
                name=sub_class,
            )
    logger.info("step 1 完成：二级分类")


def build_flower_types(graph: Graph, data_dir: Path) -> None:
    """构建 ``花卉品种`` 中心节点及其下所有品种。对应原 step 2。"""
    graph.run("CREATE (:花卉品种 {id:'0', name:'花卉品种'})")
    types_path = data_dir / "种类.txt"
    with open(types_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if not line:
                continue
            graph.run(
                """
                MERGE (a {name: '花卉品种'})
                MERGE (b:花卉品种 {id:$id, name:$name})
                MERGE (a)-[:划分]-> (b)
                """,
                id=str(i + 1),
                name=line,
            )
    logger.info("step 2 完成：花卉品种")


def build_taxonomy_branches(graph: Graph) -> None:
    """构建生物学 7 级分类骨架（界→门→纲→目→科→属→种）。对应原 step 3。"""
    for i, name in enumerate(TAXONOMY_LEVELS):
        graph.run(
            "CREATE (:生物学分支 {id:$id, name:$name})",
            id=str(i),
            name=name,
        )
        if i > 0:
            graph.run(
                """
                MERGE (a {name: $parent})
                MERGE (b {name: $child})
                MERGE (a)-[:划分]-> (b)
                """,
                parent=TAXONOMY_LEVELS[i - 1],
                child=TAXONOMY_LEVELS[i],
            )
    logger.info("step 3 完成：分类骨架")


def build_taxonomy_leaves(graph: Graph, data_dir: Path) -> None:
    """从 ``data/<level>.txt`` 读取每一级的具体分支并挂到对应骨架。对应原 step 4。

    注：原 ``createKG.py`` 在此处使用了不存在的子目录 ``科属/``，导致 step 4 实际未生效。
    本版本修复该路径 bug。
    """
    leaf_id = 0
    for level in TAXONOMY_LEVELS:
        path = data_dir / f"{level}.txt"
        if not path.exists():
            logger.warning("分类层级文件缺失，跳过: %s", path)
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 末位字符必须等于当前 level，过滤异常数据
                if line[-1] != level:
                    continue
                graph.run(
                    """
                    MERGE (a:具体分支 {id:$id, name:$name})
                    MERGE (b {name: $level})
                    MERGE (a)-[:属于]-> (b)
                    """,
                    id=str(leaf_id),
                    name=line,
                    level=level,
                )
                leaf_id += 1
    logger.info("step 4 完成：%d 个具体分支节点", leaf_id)
