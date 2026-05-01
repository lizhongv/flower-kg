"""爬虫编排：抓主页 → 建索引 → 遍历每个 title/category/page/flower → 落 xlsx。

逻辑等价于原 ``crawler/main.py`` 的 ``main`` + ``construct_title_class`` +
``crawl_page_content`` + ``save_pd``，仅做职责拆分与日志规范化。
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from ..config import AppConfig
from .client import HttpClient
from .parser import (
    parse_detail,
    parse_detail_links,
    parse_belongs,
    parse_titles,
    is_last_page,
)
from .taxonomy import TaxonomyCollector

logger = logging.getLogger(__name__)

# 与原版严格一致：每个一级分类下二级类别的索引切片
# 索引：花卉类别(0:12) / 花卉功能(12:20) / 应用环境(20:34) / 盛花期_习性(34:42) / 养护难度(42:46)
PAGE_SIZE: tuple[int, ...] = (0, 12, 20, 34, 42, 46)

# Excel 输出列定义
_COLUMNS: tuple[str, ...] = (
    "id",
    "flower_name",
    "another_name",
    "img_link",
    "type",
    "belong",
    "open_time",
    "dsc",
)

_HOME_CACHE_FILENAME = "home.html"


@dataclass
class _CategoryRef:
    """二级类别的引用：(在花卉大全文件中的 id, 详情列表 URL, 类别名)。"""

    id: int
    url: str
    name: str


def run(cfg: AppConfig) -> None:
    """爬虫主入口。"""
    data_dir: Path = cfg.data_dir
    cache_dir: Path = cfg.crawler.cache_dir
    home_url = cfg.crawler.base_url + cfg.crawler.home_path

    client = HttpClient(headers=cfg.crawler.headers, timeout=cfg.crawler.request_timeout)

    home_html = _load_or_fetch_home(client, home_url, cache_dir)
    titles, categories = parse_titles(home_html)
    titles = [t.replace(" / ", "_") for t in titles]  # 盛花期 / 习性 → 盛花期_习性

    _reset_data_dir(data_dir, keep=[cache_dir])
    _write_master_index(data_dir, titles, categories, cfg.crawler.base_url)

    flower_types: list[str] = []
    taxonomy = TaxonomyCollector()

    refs = _load_category_refs(data_dir)
    _crawl_all(refs, titles, data_dir, client, flower_types, taxonomy)

    _save_flower_types(data_dir, flower_types)
    taxonomy.write_to(data_dir)
    logger.info("爬取流程完成")


# ---------------------- 主页加载 ----------------------

def _load_or_fetch_home(client: HttpClient, home_url: str, cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / _HOME_CACHE_FILENAME
    if cache_path.exists():
        logger.info("加载缓存的主页源码: %s", cache_path)
        return cache_path.read_text(encoding="utf-8")

    logger.info("爬取主页源码: %s", home_url)
    text = client.get_text(home_url)
    if text is None:
        raise RuntimeError(f"主页爬取失败: {home_url}")
    cache_path.write_text(text, encoding="utf-8")
    return text


# ---------------------- 数据目录准备 ----------------------

def _reset_data_dir(data_dir: Path, keep: Iterable[Path]) -> None:
    """清空 data_dir，保留 keep 中列出的目录（用于 cache_dir）。"""
    keep_resolved = {p.resolve() for p in keep}
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("创建数据目录: %s", data_dir)
        return

    for entry in data_dir.iterdir():
        if entry.resolve() in keep_resolved:
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    logger.info("数据目录已清空（保留缓存）")


def _write_master_index(
    data_dir: Path,
    titles: list[str],
    categories: list[tuple[str, str]],
    base_url: str,
) -> None:
    """写出 ``花卉大全.txt`` 总索引，并为每个一级分类创建对应子目录。"""
    master_path = data_dir / "花卉大全.txt"
    with open(master_path, "w", encoding="utf-8") as fw:
        idx = 0
        for i, title in enumerate(titles):
            (data_dir / title).mkdir(parents=True, exist_ok=True)
            for j in range(PAGE_SIZE[i], PAGE_SIZE[i + 1]):
                href, name = categories[j]
                fw.write(f"{idx}\t{base_url + href}\t{name}\n")
                idx += 1
    logger.info("一级分类索引文件已写入: %s", master_path)


def _load_category_refs(data_dir: Path) -> list[_CategoryRef]:
    refs: list[_CategoryRef] = []
    with open(data_dir / "花卉大全.txt", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 3:
                continue
            refs.append(_CategoryRef(int(parts[0]), parts[1], parts[2]))
    return refs


# ---------------------- 主循环 ----------------------

def _crawl_all(
    refs: list[_CategoryRef],
    titles: list[str],
    data_dir: Path,
    client: HttpClient,
    flower_types: list[str],
    taxonomy: TaxonomyCollector,
) -> None:
    flower_id = 0
    for ti, title in enumerate(titles):
        logger.info("开始爬取一级分类: %s", title)
        for j in range(PAGE_SIZE[ti], PAGE_SIZE[ti + 1]):
            ref = refs[j]
            logger.info("开始爬取二级类别: %s", ref.name)
            examples, flower_id = _crawl_category(
                ref, client, flower_id, flower_types, taxonomy
            )
            _save_category(data_dir, title, ref.name, examples)
            logger.info("二级类别完成: %s（%d 条）", ref.name, len(examples))
        logger.info("一级分类完成: %s", title)


def _crawl_category(
    ref: _CategoryRef,
    client: HttpClient,
    start_id: int,
    flower_types: list[str],
    taxonomy: TaxonomyCollector,
) -> tuple[list[dict], int]:
    """循环爬取该类别下的所有列表页直到末页。"""
    examples: list[dict] = []
    flower_id = start_id
    for page_html in _iter_pages(ref.url, client):
        for example in _iter_details(page_html, client):
            example["id"] = str(flower_id)
            flower_id += 1
            _track_meta(example, flower_types, taxonomy)
            examples.append(example)
    return examples, flower_id


def _iter_pages(category_url: str, client: HttpClient) -> Iterator[str]:
    page_idx = 1
    while True:
        page_url = f"{category_url}page-{page_idx}.html"
        page_html = client.get_text(page_url)
        if page_html is None:
            logger.warning("列表页爬取失败，终止该类别: %s", page_url)
            break
        logger.info("列表页爬取成功: %s", page_url)
        yield page_html
        if is_last_page(page_html):
            break
        page_idx += 1


def _iter_details(page_html: str, client: HttpClient) -> Iterator[dict]:
    for flower_title, detail_url, _anchor in parse_detail_links(page_html):
        text = client.get_text(detail_url)
        if text is None:
            logger.warning("详情页爬取失败: %s", flower_title)
            continue
        logger.debug("详情页爬取成功: %s", flower_title)
        example = parse_detail(text)
        example["flower_name"] = flower_title
        yield example


def _track_meta(
    example: dict,
    flower_types: list[str],
    taxonomy: TaxonomyCollector,
) -> None:
    type_name = example.get("type", "")
    if type_name and type_name not in flower_types:
        flower_types.append(type_name)

    belong_text = example.get("belong", "")
    if belong_text:
        taxonomy.add(parse_belongs(belong_text))


# ---------------------- 落盘 ----------------------

def _save_category(
    data_dir: Path,
    title: str,
    name: str,
    examples: list[dict],
) -> None:
    """把一个二级类别下的全部花卉写到 xlsx 文件。"""
    if not examples:
        logger.warning("二级类别为空，跳过保存: %s/%s", title, name)
        return
    df = pd.DataFrame({col: [d.get(col, "") for d in examples] for col in _COLUMNS})
    out_path = data_dir / title / f"{name}.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path)
    logger.info("xlsx 已保存: %s", out_path)


def _save_flower_types(data_dir: Path, flower_types: list[str]) -> None:
    out_path = data_dir / "种类.txt"
    with open(out_path, "w", encoding="utf-8") as fw:
        for t in flower_types:
            fw.write(t + "\n")
    logger.info("花卉种类已保存: %s", out_path)
