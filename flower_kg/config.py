"""配置加载模块。

负责从 ``config.yaml`` 与 ``.env`` 读取配置，并组装成不可变的 dataclass。
敏感字段（如 NEO4J_PASSWORD、AIHUHUA_COOKIE）一律走环境变量，避免明文入库。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """配置缺失或非法时抛出。"""


@dataclass(frozen=True)
class CrawlerConfig:
    """爬虫相关配置。"""

    base_url: str
    home_path: str
    headers: dict[str, str]
    request_timeout: int
    page_sleep_seconds: float
    cache_dir: Path


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j 连接配置。"""

    uri: str
    user: str
    password: str


@dataclass(frozen=True)
class LoggingConfig:
    """日志相关配置。"""

    level: str = "INFO"
    log_file: Path | None = None


@dataclass(frozen=True)
class AppConfig:
    """整个应用的顶层配置。"""

    data_dir: Path
    crawler: CrawlerConfig
    neo4j: Neo4jConfig
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(path: Path | str = "config.yaml") -> AppConfig:
    """加载配置文件并注入 .env 中的敏感字段。

    参数
    ----
    path : 配置文件路径，默认为当前目录下的 ``config.yaml``。

    抛出
    ----
    ConfigError : 配置文件不存在、必填字段缺失或敏感环境变量未设置。
    """
    load_dotenv()  # .env 不存在也不会报错
    path = Path(path)

    if not path.exists():
        raise ConfigError(
            f"未找到配置文件: {path}。请先复制模板：cp config.yaml.example {path}"
        )

    raw = _read_yaml(path)
    return _build_app_config(raw)


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件根节点必须是映射: {path}")
    return data


def _build_app_config(raw: dict[str, Any]) -> AppConfig:
    crawler = _build_crawler(raw.get("crawler", {}))
    neo4j = _build_neo4j(raw.get("neo4j", {}))
    logging_cfg = _build_logging(raw.get("logging", {}))
    data_dir = Path(raw.get("data_dir", "./data")).resolve()
    return AppConfig(
        data_dir=data_dir,
        crawler=crawler,
        neo4j=neo4j,
        logging=logging_cfg,
    )


def _build_crawler(raw: dict[str, Any]) -> CrawlerConfig:
    headers = dict(raw.get("headers", {}))
    cookie = os.getenv("AIHUHUA_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie
    cache_dir = Path(raw.get("cache_dir", "./data/cache")).resolve()
    return CrawlerConfig(
        base_url=_require(raw, "base_url", "crawler.base_url"),
        home_path=raw.get("home_path", "/hua/"),
        headers=headers,
        request_timeout=int(raw.get("request_timeout", 15)),
        page_sleep_seconds=float(raw.get("page_sleep_seconds", 0.5)),
        cache_dir=cache_dir,
    )


def _build_neo4j(raw: dict[str, Any]) -> Neo4jConfig:
    password = os.getenv("NEO4J_PASSWORD", "").strip()
    if not password:
        raise ConfigError(
            "NEO4J_PASSWORD 未配置：请在 .env 文件中填写 Neo4j 数据库密码"
        )
    return Neo4jConfig(
        uri=raw.get("uri", "http://localhost:7474/"),
        user=raw.get("user", "neo4j"),
        password=password,
    )


def _build_logging(raw: dict[str, Any]) -> LoggingConfig:
    log_file = raw.get("log_file")
    return LoggingConfig(
        level=str(raw.get("level", "INFO")).upper(),
        log_file=Path(log_file).resolve() if log_file else None,
    )


def _require(raw: dict[str, Any], key: str, full_path: str) -> Any:
    if key not in raw or raw[key] in (None, ""):
        raise ConfigError(f"缺少必填配置项: {full_path}")
    return raw[key]
