"""
Bangumi API 客户端（异步版本）

封装与 Bangumi API v0 的交互，支持并发分页获取用户收藏。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BGM_API_BASE = "https://api.bgm.tv/v0"
USER_AGENT = "stivine/bangumi-birthday/1.0 (https://github.com/stivine/bangumi-birthday)"
PAGE_SIZE = 100


async def fetch_user_subject_ids(
    username: str,
    *,
    client: httpx.AsyncClient,
    subject_type: int | None = None,
    collection_type: int | None = None,
) -> list[int]:
    """
    并发分页获取用户所有收藏条目的 subject_id 列表。

    Parameters
    ----------
    username : str
        Bangumi 用户名或 ID。
    client : httpx.AsyncClient
        复用的 HTTP 客户端。
    subject_type : int | None
        条目类型过滤（1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元）。
    collection_type : int | None
        收藏状态过滤（1=想看, 2=看过, 3=在看, 4=搁置, 5=抛弃）。

    Returns
    -------
    list[int]
        用户所有匹配的 subject_id 列表。

    Raises
    ------
    httpx.HTTPStatusError
        API 请求失败时。
    """
    url = f"{BGM_API_BASE}/users/{username}/collections"
    params: dict[str, Any] = {"limit": PAGE_SIZE, "offset": 0}
    if subject_type is not None:
        params["subject_type"] = subject_type
    if collection_type is not None:
        params["type"] = collection_type

    t0 = time.monotonic()

    # ── 第一页：获取总数 ─────────────────────────────────────────────────
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    first_data = resp.json()

    total: int = first_data.get("total", 0)
    all_ids: list[int] = [item["subject_id"] for item in first_data.get("data", [])]

    if total <= PAGE_SIZE:
        elapsed = time.monotonic() - t0
        logger.info(
            "Bangumi API  user=%-20s  total=%d  fetched=%d  pages=1  %.2fs",
            username, total, len(all_ids), elapsed,
        )
        return all_ids

    # ── 并发获取剩余页 ────────────────────────────────────────────────────
    offsets = range(PAGE_SIZE, total, PAGE_SIZE)

    async def _fetch_page(offset: int) -> list[int]:
        page_params = {**params, "offset": offset}
        r = await client.get(url, params=page_params)
        if r.status_code != 200:
            logger.warning("获取 offset=%d 失败：HTTP %d", offset, r.status_code)
            return []
        return [item["subject_id"] for item in r.json().get("data", [])]

    pages = await asyncio.gather(*[_fetch_page(o) for o in offsets])
    for page in pages:
        all_ids.extend(page)

    elapsed = time.monotonic() - t0
    n_pages = 1 + len(list(offsets))
    logger.info(
        "Bangumi API  user=%-20s  total=%d  fetched=%d  pages=%d  %.2fs",
        username, total, len(all_ids), n_pages, elapsed,
    )
    return all_ids
