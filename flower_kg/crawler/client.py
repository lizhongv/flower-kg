"""HTTP 客户端封装。

仅做最小的请求 + 异常包装：失败统一返回 ``None``，让调用方决定 retry / 跳过 / 终止。
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class HttpClient:
    """封装 ``requests.get``，统一注入 headers 与超时。"""

    def __init__(self, headers: dict[str, str], timeout: int = 15):
        self._session = requests.Session()
        self._session.headers.update(headers)
        self._timeout = timeout

    def get_text(self, url: str) -> Optional[str]:
        """抓取并返回响应文本。失败时记录 warning 并返回 ``None``。"""
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.RequestException as e:
            logger.warning("请求异常 %s: %s", url, e)
            return None
        if resp.status_code != 200:
            logger.warning("HTTP %s: %s", resp.status_code, url)
            return None
        return resp.text
