"""花卉详细节点的构建。

对应原 ``createKG.py::createFlower``：读取每个 xlsx 二级类别文件，把每条花卉
建为 ``:花卉`` 节点，并与品种、分类、科属节点建立关系。
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from py2neo import Graph

from .entities import PAGE_SIZE

logger = logging.getLogger(__name__)

# 在 Cypher 字面量中需要剔除的特殊字符（与原版一致）
_FORBIDDEN_CHARS: tuple[str, ...] = ("'", ")", "(", "{", "}")

# xlsx 列名（对应 crawler.runner._COLUMNS）
_COL_ID = "id"
_COL_NAME = "flower_name"
_COL_ANOTHER = "another_name"
_COL_IMG = "img_link"
_COL_TYPE = "type"
_COL_BELONG = "belong"
_COL_OPEN = "open_time"
_COL_DESC = "dsc"


def build_flowers(
    graph: Graph,
    data_dir: Path,
    title_classes: list[str],
) -> None:
    """遍历每个二级类别 xlsx，构建花卉节点与关系。"""
    master_path = data_dir / "花卉大全.txt"
    with open(master_path, "r", encoding="utf-8") as f:
        master_lines = f.readlines()

    for ti, title in enumerate(title_classes):
        for j in range(PAGE_SIZE[ti], PAGE_SIZE[ti + 1]):
            tokens = master_lines[j].split()
            if not tokens:
                continue
            class_name = tokens[-1]
            xlsx_path = data_dir / title / f"{class_name}.xlsx"
            if not xlsx_path.exists():
                logger.warning("xlsx 不存在，跳过: %s", xlsx_path)
                continue
            _build_one_category_xlsx(graph, xlsx_path, title, class_name)
            logger.info("xlsx 导入完成: %s", xlsx_path)
        logger.info("一级分类导入完成: %s", title)
    logger.info("花卉构造完成")


def _build_one_category_xlsx(
    graph: Graph,
    xlsx_path: Path,
    title: str,
    class_name: str,
) -> None:
    df = pd.read_excel(xlsx_path)
    for _, row in df.iterrows():
        _build_one_flower(graph, row, title, class_name)


def _build_one_flower(
    graph: Graph,
    row: pd.Series,
    title: str,
    class_name: str,
) -> None:
    raw_belong = str(row.get(_COL_BELONG, "") or "")
    belongs = raw_belong.split()
    if not belongs:
        # 与原版一致：科属为空时跳过该花卉的关系建立
        return
    belong_to = belongs[-1]

    name = _sanitize(str(row.get(_COL_NAME, "") or ""))
    another = _sanitize(str(row.get(_COL_ANOTHER, "") or ""))
    desc = _sanitize(str(row.get(_COL_DESC, "") or ""))
    img = str(row.get(_COL_IMG, "") or "")
    open_time = str(row.get(_COL_OPEN, "") or "")
    type_name = str(row.get(_COL_TYPE, "") or "")

    try:
        flower_id = int(row[_COL_ID])
    except (KeyError, ValueError, TypeError):
        logger.warning("花卉 id 无效，跳过: %s", row.to_dict())
        return

    graph.run(
        f"""
        MERGE (a:花卉 {{id:$id, name:$name, 别名:$another, 图片:$img, 开花季节:$open_time, 简介:$desc}})
        MERGE (b:花卉品种 {{name: $type_name}})
        MERGE (a)-[:归属]-> (b)

        MERGE (c:具体分支 {{name: $belong_to}})
        MERGE (a)-[:属于]-> (c)

        MERGE (d:{title} {{name: $class_name}})
        MERGE (a)-[:归于]-> (d)
        """,
        id=str(flower_id),
        name=name,
        another=another,
        img=img,
        open_time=open_time,
        desc=desc,
        type_name=type_name,
        belong_to=belong_to,
        class_name=class_name,
    )
    _link_taxonomy_chain(graph, belongs)


def _link_taxonomy_chain(graph: Graph, belongs: list[str]) -> None:
    """把 belongs 中相邻两级用 ``:从属`` 关系串起来。"""
    for k in range(1, len(belongs)):
        graph.run(
            """
            MERGE (a:具体分支 {name: $parent})
            MERGE (b:具体分支 {name: $child})
            MERGE (b)-[:从属]-> (a)
            """,
            parent=belongs[k - 1],
            child=belongs[k],
        )


def _sanitize(text: str) -> str:
    """剔除特殊字符（保持与原版完全一致：替换为单空格）。"""
    for ch in _FORBIDDEN_CHARS:
        text = text.replace(ch, " ")
    return text
