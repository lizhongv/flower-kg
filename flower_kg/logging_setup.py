"""统一的日志初始化。

所有模块通过 ``logging.getLogger(__name__)`` 拿 logger，根 logger 由本模块配置。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import LoggingConfig

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup(cfg: LoggingConfig | None = None) -> logging.Logger:
    """根据配置初始化根 logger，并返回 ``flower_kg`` 顶层 logger。"""
    cfg = cfg or LoggingConfig()
    level = getattr(logging, cfg.level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()  # 避免重复初始化时累加 handler

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if cfg.log_file is not None:
        cfg.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(cfg.log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return logging.getLogger("flower_kg")
