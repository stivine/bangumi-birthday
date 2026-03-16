"""
生日查询服务

封装所有与数据库相关的生日查询逻辑，供路由层调用。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from bangumi_birthday.config import get_settings

logger = logging.getLogger(__name__)


class BirthdayService:
    """
    生日查询服务，依赖 Motor（异步 MongoDB）和 Redis（缓存）。
    """

    def __init__(self, db: Any, redis_client: aioredis.Redis) -> None:
        self._db = db
        self._redis = redis_client
        self._settings = get_settings()

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
        else:
            return await self._query_all(birthday)

    async def _query_all(self, birthday: str) -> list[dict[str, Any]]:
        """无用户过滤，直接查 characters 集合（带 Redis 缓存）"""
        cache_key = f"birthday:all:{birthday}"

        # 尝试读缓存
        cached = await self._redis.get(cache_key)
        if cached:
            logger.debug("缓存命中：%s", cache_key)
            return json.loads(cached)

        # 查数据库
        col = self._db[self._settings.col_characters]
        cursor = col.find({"birthday": birthday}, {"_id": 0})
        docs = await cursor.to_list(length=None)

        # 按 character_id 排序
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

        # 写缓存
        await self._redis.setex(
            cache_key,
            self._settings.cache_ttl,
            json.dumps(result, ensure_ascii=False),
        )

        return result

    async def _query_filtered(
        self, birthday: str, subject_ids: list[int]
    ) -> list[dict[str, Any]]:
        """
        用户过滤查询：在 date_char_sub 集合中查找用户收藏作品里的生日角色。
        去重后返回角色信息。
        """
        cache_key = f"birthday:user:{birthday}:{hash(tuple(sorted(subject_ids)))}"

        cached = await self._redis.get(cache_key)
        if cached:
            logger.debug("缓存命中（用户过滤）：%s", cache_key)
            return json.loads(cached)

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

        await self._redis.setex(
            cache_key,
            self._settings.cache_ttl,
            json.dumps(result, ensure_ascii=False),
        )

        return result
