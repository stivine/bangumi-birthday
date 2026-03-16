"""
生日查询服务

封装所有与数据库相关的生日查询逻辑，供路由层调用。

Redis 为可选依赖：连接失败时自动降级为直查 MongoDB，
服务始终可用，不会因缓存层故障而返回 500。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from bangumi_birthday.config import get_settings

logger = logging.getLogger(__name__)


class BirthdayService:
    """
    生日查询服务，依赖 Motor（异步 MongoDB）和 Redis（缓存）。
    Redis 不可用时自动降级，不影响核心查询功能。
    """

    def __init__(self, db: Any, redis_client: aioredis.Redis) -> None:
        self._db = db
        self._redis = redis_client
        self._settings = get_settings()

    # ── 缓存辅助方法（所有 Redis 操作集中在此，统一做异常降级） ──────────

    async def _cache_get(self, key: str) -> list[dict[str, Any]] | None:
        """
        从 Redis 读取缓存。
        连接失败或任何 Redis 异常均返回 None（降级为查库），不抛出。
        """
        try:
            raw = await self._redis.get(key)
            if raw:
                logger.debug("缓存命中：%s", key)
                return json.loads(raw)
        except RedisError as exc:
            logger.warning("Redis 读取失败，降级为直查数据库：%s", exc)
        return None

    async def _cache_set(self, key: str, data: list[dict[str, Any]]) -> None:
        """
        写入 Redis 缓存。
        连接失败时静默忽略，不影响已正常返回的查询结果。
        """
        try:
            await self._redis.setex(
                key,
                self._settings.cache_ttl,
                json.dumps(data, ensure_ascii=False),
            )
        except RedisError as exc:
            logger.warning("Redis 写入失败（缓存跳过）：%s", exc)

    # ── 公开查询接口 ──────────────────────────────────────────────────────

    async def get_characters_by_date(
        self,
        birthday: str,
        subject_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        查询指定生日的角色列表。

        Parameters
        ----------
        birthday : str
            "MM-DD" 格式的生日。
        subject_ids : list[int] | None
            若提供，则只返回在这些作品中的角色（用于用户收藏过滤）。

        Returns
        -------
        list[dict]
            角色信息列表（character_id, name, chinese_name, birthday）。
        """
        if subject_ids is not None:
            return await self._query_filtered(birthday, subject_ids)
        return await self._query_all(birthday)

    # ── 私有查询实现 ──────────────────────────────────────────────────────

    async def _query_all(self, birthday: str) -> list[dict[str, Any]]:
        """无用户过滤，查 characters 集合（带 Redis 缓存，不可用时降级）"""
        cache_key = f"birthday:all:{birthday}"

        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        col = self._db[self._settings.col_characters]
        cursor = col.find({"birthday": birthday}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        docs.sort(key=lambda x: x.get("character_id", 0))

        result = [
            {
                "character_id": d.get("character_id"),
                "name": d.get("name", ""),
                "chinese_name": d.get("chinese_name", ""),
                "birthday": d.get("birthday"),
            }
            for d in docs
        ]

        await self._cache_set(cache_key, result)
        return result

    async def _query_filtered(
        self, birthday: str, subject_ids: list[int]
    ) -> list[dict[str, Any]]:
        """
        用户过滤查询：在 date_char_sub 集合中查找用户收藏作品里的生日角色。
        去重后返回角色信息。
        """
        cache_key = f"birthday:user:{birthday}:{hash(tuple(sorted(subject_ids)))}"

        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        col = self._db[self._settings.col_date_char_sub]
        query = {
            "birthday": birthday,
            "subject_id": {"$in": subject_ids},
        }
        cursor = col.find(query, {"_id": 0})
        docs = await cursor.to_list(length=None)

        # 去重（同一角色可能出现在多部作品中）
        seen: set[int] = set()
        result: list[dict[str, Any]] = []
        for d in docs:
            cid = d.get("character_id")
            if cid not in seen:
                seen.add(cid)
                result.append(
                    {
                        "character_id": cid,
                        "name": d.get("name", ""),
                        "chinese_name": d.get("chinese_name", ""),
                        "birthday": d.get("birthday"),
                    }
                )

        result.sort(key=lambda x: x.get("character_id") or 0)

        await self._cache_set(cache_key, result)
        return result
