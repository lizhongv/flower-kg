"""Neo4j 连接与全图清空。"""

from __future__ import annotations

import logging

from py2neo import Graph

from ..config import Neo4jConfig

logger = logging.getLogger(__name__)


def connect(cfg: Neo4jConfig) -> Graph:
    """根据配置返回一个 ``py2neo.Graph`` 连接。"""
    logger.info("连接 Neo4j: %s (user=%s)", cfg.uri, cfg.user)
    return Graph(cfg.uri, auth=(cfg.user, cfg.password))


def clear_all(graph: Graph) -> None:
    """清空整个图（节点 + 关系）。"""
    graph.run("MATCH (n) DETACH DELETE n")
    logger.info("Neo4j 图已清空")
