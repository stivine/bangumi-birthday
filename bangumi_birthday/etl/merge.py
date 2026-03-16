"""
ETL：合并 characters 与 subject_characters 两张表，生成 date_char_sub 主表。

date_char_sub 是 Web API 的核心查询表，索引为 (birthday, subject_id)。
合并逻辑：
  对每条 subject_characters 记录，查找对应 character 的生日，
  将两者的字段合并写入 date_char_sub。
"""

from __future__ import annotations

import logging
from typing import Any

from tqdm import tqdm

from bangumi_birthday.config import get_settings
from bangumi_birthday.db.mongo import get_sync_db

logger = logging.getLogger(__name__)


def run(*, batch_size: int = 2000) -> dict[str, int]:
    """
    执行合并流程：characters + subject_characters → date_char_sub。

    先将 characters 集合完全加载到内存字典（约数百万条，几十 MB）；
    然后流式遍历 subject_characters 集合，逐批写入 date_char_sub。

    Returns
    -------
    dict[str, int]
        {"processed": N, "inserted": N, "modified": N, "skipped": N}
    """
    settings = get_settings()
    db = get_sync_db()

    char_col = db[settings.col_characters]
    sc_col = db[settings.col_subject_characters]
    target_col = db[settings.col_date_char_sub]

    # ── Step 1：加载 characters 到内存字典 ────────────────────────────────
    logger.info("加载 characters 集合到内存字典...")
    characters: dict[int, dict[str, Any]] = {}
    for doc in tqdm(char_col.find({}, {"_id": 0}), desc="加载角色", unit="条"):
        cid = doc.get("character_id")
        if cid is not None:
            characters[int(cid)] = doc

    logger.info("共加载 %d 个角色", len(characters))

    # ── Step 2：清空目标集合 ──────────────────────────────────────────────
    logger.info("清空 date_char_sub 集合...")
    target_col.delete_many({})

    # ── Step 3：遍历 subject_characters，逐批插入 ─────────────────────────
    stats = {"processed": 0, "inserted": 0, "modified": 0, "skipped": 0}
    buffer: list[dict[str, Any]] = []

    total_sc = sc_col.count_documents({})
    logger.info("开始合并 %d 条作品-角色关系...", total_sc)

    for sc_doc in tqdm(sc_col.find({}, {"_id": 0}), total=total_sc, desc="合并关系", unit="条"):
        stats["processed"] += 1

        cid = int(sc_doc.get("character_id", -1))
        char_info = characters.get(cid)
        if char_info is None:
            stats["skipped"] += 1
            continue

        merged: dict[str, Any] = {
            "birthday": char_info.get("birthday"),
            "character_id": cid,
            "subject_id": int(sc_doc.get("subject_id", 0)),
            "type": int(sc_doc.get("type", 0)),
            "order": int(sc_doc.get("order", 0)),
            "name": char_info.get("name", ""),
            "chinese_name": char_info.get("chinese_name", ""),
        }
        buffer.append(merged)

        if len(buffer) >= batch_size:
            target_col.insert_many(buffer, ordered=False)
            stats["inserted"] += len(buffer)
            buffer.clear()

    if buffer:
        target_col.insert_many(buffer, ordered=False)
        stats["inserted"] += len(buffer)

    logger.info(
        "合并完成：处理 %d，跳过 %d，写入 %d",
        stats["processed"],
        stats["skipped"],
        stats["inserted"],
    )
    return stats
