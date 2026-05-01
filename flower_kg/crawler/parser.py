"""HTML 解析（纯函数）。

所有正则均直接迁自原 ``crawler/main.py``，未做语义改动；只做了拆分和命名规范化。
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------- 主页解析 ----------------------

_TITLE_PATTERN = re.compile(r'<h2 class="title " title="(.*?)">')
_CATEGORY_PATTERN = re.compile(
    r'<li><a href="(.*?)" class="a " title="(.*?)" target="_self">'
)


def parse_titles(home_html: str) -> tuple[list[str], list[tuple[str, str]]]:
    """解析主页 HTML，返回 (titles, categories)。

    titles : 一级分类列表，例如 ['花卉类别', '花卉功能', ...]
    categories : 每个一级分类下的所有二级类别 [(href, title), ...]
    """
    titles = _TITLE_PATTERN.findall(home_html)
    categories = _CATEGORY_PATTERN.findall(home_html)
    return titles, categories


# ---------------------- 列表页 ----------------------

_NEXT_PAGE_PATTERN = re.compile(r"class='next'>下一页</a></div>")
_DETAIL_LINK_PATTERN = re.compile(
    r'<a class="title" target="_blank" title="(.*?)" href="(.*?)">(.*?)</a>'
)


def is_last_page(page_html: str) -> bool:
    """列表页是否已无「下一页」按钮。"""
    return _NEXT_PAGE_PATTERN.search(page_html) is None


def parse_detail_links(page_html: str) -> list[tuple[str, str, str]]:
    """从列表页提取详情页链接 [(title, href, anchor_text), ...]"""
    return _DETAIL_LINK_PATTERN.findall(page_html)


# ---------------------- 详情页 ----------------------

_ANOTHER_NAME_PATTERN = re.compile(r'<label class="cate">别名：(.*?)</label>')
_IMG_PATTERN = re.compile(
    r'<img width="140" alt="(.*?)" title="(.*?)" src="(.*?)"'
)
_TYPE_PATTERN = re.compile(
    r'<label class="cate">分类：<a href="(.*?)" title="(.*?)" target="_blank">(.*?)</a></label>'
)
_BELONG_PATTERN = re.compile(r'<label class="cate">科属：(.*?)</label>')
_OPEN_TIME_PATTERN = re.compile(
    r'<label class="cate">盛花期：<a title="(.*?)" target="_blank" href="(.*?)">(.*?)</a>'
)
_DESC_PATTERN = re.compile(r'<p class="desc">(.*?)</p>', re.DOTALL)


def parse_detail(html: str) -> dict:
    """从一条花卉详情页 HTML 中提取所有结构化字段。

    缺字段时退化为空字符串或预设默认值，与原版行为一致。
    """
    another_names = _ANOTHER_NAME_PATTERN.findall(html)
    imgs = _IMG_PATTERN.findall(html)
    types = _TYPE_PATTERN.findall(html)
    belongs = _BELONG_PATTERN.findall(html)
    open_times = _OPEN_TIME_PATTERN.findall(html)
    descs = _DESC_PATTERN.findall(html)

    img_link = imgs[0][2] if imgs and len(imgs[0]) >= 3 else "无"
    type_name = types[0][2] if types and len(types[0]) >= 3 else ""
    belong_text = belongs[0] if belongs else ""
    open_time = open_times[0][-1] if open_times else "四季"
    desc = " ".join(descs[0].split()) if descs else "无"

    return {
        "another_name": another_names[0] if another_names else "无",
        "img_link": img_link,
        "type": type_name,
        "belong": belong_text,
        "open_time": open_time,
        "dsc": desc if desc else "无",
    }


# ---------------------- 科属拆分 ----------------------

_LEVEL_SUFFIXES = ("界", "门", "纲", "目", "科", "属", "种")


def parse_belongs(belong_text: str) -> dict[str, list[str]]:
    """把「科属」字段中按空格分隔的多个层级拆分到 7 级桶中。

    返回 ``{'界': [...], '门': [...], ...}``，每个层级最多 1 项（保留原行为）。
    """
    result: dict[str, list[str]] = {s: [] for s in _LEVEL_SUFFIXES}
    if not belong_text:
        return result
    for token in belong_text.split():
        if not token:
            continue
        suffix = token[-1]
        if suffix in result:
            result[suffix].append(token)
    return result


def split_belongs(belong_text: str) -> list[str]:
    """返回「科属」字段中按空格切开的原始 token 列表，保持顺序。"""
    return belong_text.split() if belong_text else []


def last_token(belong_text: str) -> Optional[str]:
    """返回 belong 中的最后一个 token（即最末层），无则 None。"""
    tokens = split_belongs(belong_text)
    return tokens[-1] if tokens else None
