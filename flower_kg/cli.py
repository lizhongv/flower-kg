"""命令行入口：``python -m flower_kg`` 或安装后的 ``flower-kg`` 可执行命令。

子命令：
    crawl   爬取 aihuhua.com 的花卉数据并落盘
    build   读取 data/ 下产物，构建 Neo4j 知识图谱
    clear   仅清空 Neo4j 图（运维用）
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import ConfigError, load_config
from .logging_setup import setup as setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flower-kg",
        description="花卉知识图谱：爬取数据并构建 Neo4j 图谱",
    )
    parser.add_argument("--version", action="version", version=f"flower-kg {__version__}")
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )

    subs = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    subs.add_parser("crawl", help="爬取花卉数据")
    subs.add_parser("build", help="构建 Neo4j 知识图谱")
    subs.add_parser("clear", help="清空 Neo4j 图")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = load_config(Path(args.config))
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 2

    setup_logging(cfg.logging)

    try:
        if args.command == "crawl":
            from .crawler.runner import run as crawl_run

            crawl_run(cfg)
        elif args.command == "build":
            from .builder.runner import run as build_run

            build_run(cfg)
        elif args.command == "clear":
            from .builder.runner import clear_graph_only

            clear_graph_only(cfg)
        else:
            parser.error(f"未知命令: {args.command}")
            return 2
    except KeyboardInterrupt:
        logger.warning("用户中断")
        return 130
    except Exception:
        logger.exception("命令执行失败")
        return 1
    return 0
