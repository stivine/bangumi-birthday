"""
ETL：将 subject-characters.jsonlines 批量导入 MongoDB。

subject_characters 集合记录了"哪部作品包含哪个角色"。
使用 (subject_id, character_id) 联合唯一索引去重。
"""

from __future__ import annotations

import logging
from typing import Any

from tqdm import tqdm

from bangumi_birthday.config import get_settings
from bangumi_birthday.db.mongo import get_collection
from bangumi_birthday.utils.jsonlines import iter_jsonlines

logger = logging.getLogger(__name__)


def extract_relation_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    """
    从单条 subject-characters.jsonlines 记录中提取所需字段。
    """
    try:
        return {
            "subject_id": int(raw["subject_id"]),
            "character_id": int(raw["character_id"]),
            "type": int(raw.get("type", 0)),
            "order": int(raw.get("order", 0)),
        }
    except (KeyError, TypeError, ValueError) as exc:
        logger.debug("跳过无效关系记录：%s — %s", raw, exc)
        return None


def run(*, batch_size: int = 5000, dry_run: bool = False) -> dict[str, int]:
    """
    执行作品-角色关系导入流程。

    Parameters
    ----------
    batch_size : int
        每批写入文档数量。
    dry_run : bool
        仅统计，不写库。

    Returns
    -------
    dict[str, int]
        {"processed": N, "inserted": N, "modified": N, "skipped": N}
    """
    settings = get_settings()
    col = get_collection(settings.col_subject_characters)

    stats = {"processed": 0, "inserted": 0, "modified": 0, "skipped": 0}
    buffer: list[dict[str, Any]] = []

    logger.info("开始导入作品-角色关系：%s", settings.subject_characters_file)

    for raw in tqdm(
        iter_jsonlines(settings.subject_characters_file),
        desc="导入作品-角色关系",
        unit="条",
    ):
        stats["processed"] += 1

        record = extract_relation_record(raw)
        if record is None:
            stats["skipped"] += 1
            continue

        buffer.append(record)

        if len(buffer) >= batch_size:
            if not dry_run:
                # 使用复合键去重
                ins, mod = _bulk_upsert_relations(col, buffer)
                stats["inserted"] += ins
                stats["modified"] += mod
            buffer.clear()

    if buffer and not dry_run:
        ins, mod = _bulk_upsert_relations(col, buffer)
        stats["inserted"] += ins
        stats["modified"] += mod

    logger.info(
        "关系导入完成：处理 %d，跳过 %d，新增 %d，更新 %d",
        stats["processed"],
        stats["skipped"],
        stats["inserted"],
        stats["modified"],
    )
    return stats


def _bulk_upsert_relations(collection: Any, docs: list[dict[str, Any]]) -> tuple[int, int]:
    """
    使用 (subject_id, character_id) 复合键批量 upsert。
    """
    from pymongo import UpdateOne

    ops = [
        UpdateOne(
            filter={"subject_id": d["subject_id"], "character_id": d["character_id"]},
            update={"$set": d},
            upsert=True,
        )
        for d in docs
    ]
    result = collection.bulk_write(ops, ordered=False)
    return result.upserted_count, result.modified_count
