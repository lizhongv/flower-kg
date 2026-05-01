"""图谱构建编排：清空 → 建实体骨架 → 建花卉。"""

from __future__ import annotations

import logging

from ..config import AppConfig
from .connection import clear_all, connect
from .entities import (
    build_flower_types,
    build_root_categories,
    build_taxonomy_branches,
    build_taxonomy_leaves,
)
from .flowers import build_flowers

logger = logging.getLogger(__name__)

# 与原 createKG.py 的 title_class 保持一致
TITLE_CLASSES: list[str] = [
    "花卉类别",
    "花卉功能",
    "应用环境",
    "盛花期_习性",
    "养护难度",
]


def run(cfg: AppConfig) -> None:
    """图谱构建主入口。"""
    graph = connect(cfg.neo4j)
    clear_all(graph)
    build_root_categories(graph, cfg.data_dir, TITLE_CLASSES)
    build_flower_types(graph, cfg.data_dir)
    build_taxonomy_branches(graph)
    build_taxonomy_leaves(graph, cfg.data_dir)
    build_flowers(graph, cfg.data_dir, TITLE_CLASSES)
    logger.info("Neo4j 图谱构建完成")


def clear_graph_only(cfg: AppConfig) -> None:
    """仅清空图（运维用）。"""
    graph = connect(cfg.neo4j)
    clear_all(graph)
