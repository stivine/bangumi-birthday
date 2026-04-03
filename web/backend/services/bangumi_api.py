"""
Bangumi API 客户端（异步版本）

封装与 Bangumi API v0 的交互，支持并发分页获取用户收藏。
"""

from __future__ import annotations

import asyncio
import logging
import time
from itertools import islice
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BGM_API_BASE = "https://api.bgm.tv/v0"
USER_AGENT = "stivine/bangumi-birthday/1.0 (https://github.com/stivine/bangumi-birthday)"
PAGE_SIZE = 100
MAX_OUTBOUND_CONCURRENCY = 20
PAGE_FETCH_BATCH_SIZE = 5
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 0.3

_BGM_REQUEST_SEM = asyncio.Semaphore(MAX_OUTBOUND_CONCURRENCY)
_ACTIVE_BGM_REQUESTS = 0


def _iter_batches(values: range, size: int) -> Any:
    """将偏移量按固定大小分批，避免一次性创建过多等待任务。"""
    iterator = iter(values)
    while batch := list(islice(iterator, size)):
        yield batch


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any],
    request_id: str = "-",
) -> httpx.Response:
    """
    Bangumi API GET 请求包装：
    - 全局并发限流，避免连接池被瞬时打满
    - 对连接池等待超时等暂时性错误做有限重试
    """
    global _ACTIVE_BGM_REQUESTS
    for attempt in range(MAX_RETRIES + 1):
        started_at = time.monotonic()
        try:
            async with _BGM_REQUEST_SEM:
                _ACTIVE_BGM_REQUESTS += 1
                logger.info(
                    "Bangumi API GET start request_id=%s offset=%s attempt=%d active=%d",
                    request_id,
                    params.get("offset"),
                    attempt,
                    _ACTIVE_BGM_REQUESTS,
                )
                try:
                    response = await client.get(url, params=params)
                finally:
                    _ACTIVE_BGM_REQUESTS -= 1

                logger.info(
                    "Bangumi API GET done request_id=%s offset=%s status=%d elapsed=%.2fs active=%d",
                    request_id,
                    params.get("offset"),
                    response.status_code,
                    time.monotonic() - started_at,
                    _ACTIVE_BGM_REQUESTS,
                )
                return response
        except (httpx.PoolTimeout, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            if attempt >= MAX_RETRIES:
                raise
            sleep_s = RETRY_BACKOFF_BASE * (2 ** attempt)
            logger.warning(
                "Bangumi API 临时失败（%s），%.1fs 后重试 %d/%d",
                exc.__class__.__name__,
                sleep_s,
                attempt + 1,
                MAX_RETRIES,
            )
            logger.warning(
                "Bangumi API retry request_id=%s offset=%s active=%d reason=%s",
                request_id,
                params.get("offset"),
                _ACTIVE_BGM_REQUESTS,
                exc.__class__.__name__,
            )
            await asyncio.sleep(sleep_s)


async def fetch_user_subject_ids(
    username: str,
    *,
    client: httpx.AsyncClient,
    subject_type: int | None = None,
    collection_type: int | None = None,
    request_id: str = "-",
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
    logger.info(
        "Bangumi API collections start request_id=%s user=%s subject_type=%s collection_type=%s",
        request_id,
        username,
        subject_type,
        collection_type,
    )

    resp = await _get_with_retry(client, url, params=params, request_id=request_id)
    resp.raise_for_status()
    first_data = resp.json()

    total: int = first_data.get("total", 0)
    all_ids: list[int] = [item["subject_id"] for item in first_data.get("data", [])]

    if total <= PAGE_SIZE:
        elapsed = time.monotonic() - t0
        logger.info(
            "Bangumi API collections done request_id=%s user=%-20s total=%d fetched=%d pages=1 elapsed=%.2fs",
            request_id,
            username,
            total,
            len(all_ids),
            elapsed,
        )
        return all_ids

    # ── 分批获取剩余页，避免一次性在事件循环里堆积大量等待任务 ───────────
    offsets = range(PAGE_SIZE, total, PAGE_SIZE)

    async def _fetch_page(offset: int) -> list[int]:
        page_params = {**params, "offset": offset}
        r = await _get_with_retry(client, url, params=page_params, request_id=request_id)
        if r.status_code != 200:
            logger.warning(
                "Bangumi API page failed request_id=%s offset=%d status=%d",
                request_id,
                offset,
                r.status_code,
            )
            return []
        return [item["subject_id"] for item in r.json().get("data", [])]

    for batch in _iter_batches(offsets, PAGE_FETCH_BATCH_SIZE):
        pages = await asyncio.gather(*(_fetch_page(offset) for offset in batch))
        for page in pages:
            all_ids.extend(page)

    elapsed = time.monotonic() - t0
    n_pages = 1 + len(list(offsets))
    logger.info(
        "Bangumi API collections done request_id=%s user=%-20s total=%d fetched=%d pages=%d elapsed=%.2fs",
        request_id,
        username,
        total,
        len(all_ids),
        n_pages,
        elapsed,
    )
    return all_ids
