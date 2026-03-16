"""
MongoDB 连接与操作封装

同时提供同步（pymongo）和异步（motor）两种访问方式：
- 同步版本用于 ETL 脚本、CLI 工具
- 异步版本用于 Quart Web API
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)


# ── 同步客户端（ETL / CLI） ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_sync_db() -> Database:
    """返回同步 MongoDB 数据库对象（单例）"""
    from bangumi_birthday.config import get_settings

    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongodb_uri)
    return client[settings.mongodb_db]


def get_collection(name: str) -> Collection:
    """返回指定名称的同步集合"""
    return get_sync_db()[name]


def bulk_upsert(
    collection: Collection,
    documents: list[dict[str, Any]],
    key_field: str,
    batch_size: int = 1000,
) -> tuple[int, int]:
    """
    批量 upsert 文档到 MongoDB。

    Parameters
    ----------
    collection : Collection
        目标集合。
    documents : list[dict]
        待写入的文档列表。
    key_field : str
        用于唯一匹配的字段名（如 "character_id"）。
    batch_size : int
        每次批量写入的大小，默认 1000。

    Returns
    -------
    tuple[int, int]
        (inserted_count, modified_count)
    """
    inserted = 0
    modified = 0

    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        ops = [
            UpdateOne(
                filter={key_field: doc[key_field]},
                update={"$set": doc},
                upsert=True,
            )
            for doc in batch
        ]
        result = collection.bulk_write(ops, ordered=False)
        inserted += result.upserted_count
        modified += result.modified_count

    return inserted, modified


def ensure_indexes(db: Database) -> None:
    """
    在所有集合上创建必要的索引（幂等操作）。
    """
    from bangumi_birthday.config import get_settings

    settings = get_settings()

    # characters 集合
    db[settings.col_characters].create_index("character_id", unique=True)
    db[settings.col_characters].create_index("birthday")

    # subject_characters 集合
    db[settings.col_subject_characters].create_index(
        [("subject_id", 1), ("character_id", 1)], unique=True
    )

    # date_char_sub 集合
    db[settings.col_date_char_sub].create_index("birthday")
    db[settings.col_date_char_sub].create_index("character_id")
    db[settings.col_date_char_sub].create_index("subject_id")
    db[settings.col_date_char_sub].create_index(
        [("subject_id", 1), ("birthday", 1)]
    )

    logger.info("MongoDB 索引初始化完成")


# ── 异步客户端（Quart Web API） ──────────────────────────────────────────────

_async_client: Any = None
_async_db: Any = None


async def get_async_db() -> Any:
    """
    返回异步 motor 数据库对象（延迟初始化单例）。
    """
    global _async_client, _async_db

    if _async_db is not None:
        return _async_db

    try:
        from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("请先安装 motor: pip install motor") from exc

    from bangumi_birthday.config import get_settings

    settings = get_settings()
    _async_client = AsyncIOMotorClient(settings.mongodb_uri)
    _async_db = _async_client[settings.mongodb_db]
    logger.info("AsyncIO Motor 客户端已连接")
    return _async_db


async def close_async_db() -> None:
    """关闭异步 MongoDB 客户端（在应用关闭时调用）"""
    global _async_client, _async_db
    if _async_client is not None:
        _async_client.close()
        _async_client = None
        _async_db = None
        logger.info("AsyncIO Motor 客户端已关闭")
