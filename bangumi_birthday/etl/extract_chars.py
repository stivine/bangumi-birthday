"""
ETL：从 character.jsonlines 提取角色生日数据并写入 MongoDB。

每条记录提取：
  - character_id
  - name（原始日文名）
  - chinese_name（简体中文名，可能为空）
  - birthday（MM-DD 格式，无法解析则跳过）
"""

from __future__ import annotations

import logging
from typing import Any

from tqdm import tqdm

from bangumi_birthday.config import get_settings
from bangumi_birthday.db.mongo import bulk_upsert, get_collection
from bangumi_birthday.utils.date_utils import (
    extract_birthday_from_infobox,
    extract_chinese_name_from_infobox,
)
from bangumi_birthday.utils.jsonlines import iter_jsonlines

logger = logging.getLogger(__name__)


def extract_character_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    """
    从单条 character.jsonlines 记录中提取所需字段。

    Parameters
    ----------
    raw : dict
        原始 JSON 对象。

    Returns
    -------
    dict | None
        提取后的文档，若无生日信息则返回 None。
    """
    infobox = raw.get("infobox", "")
    birthday = extract_birthday_from_infobox(infobox)
    if birthday is None:
        return None

    chinese_name = extract_chinese_name_from_infobox(infobox)

    return {
        "character_id": int(raw["id"]),
        "name": raw.get("name", ""),
        "chinese_name": chinese_name,
        "birthday": birthday,
    }


def run(*, batch_size: int = 2000, dry_run: bool = False) -> dict[str, int]:
    """
    执行角色生日提取流程。

    Parameters
    ----------
    batch_size : int
        每批写入 MongoDB 的文档数量。
    dry_run : bool
        若为 True，只统计不写库。

    Returns
    -------
    dict[str, int]
        {"processed": N, "inserted": N, "modified": N, "skipped": N}
    """
    settings = get_settings()
    col = get_collection(settings.col_characters)

    stats = {"processed": 0, "inserted": 0, "modified": 0, "skipped": 0}
    buffer: list[dict[str, Any]] = []

    logger.info("开始提取角色生日数据：%s", settings.character_file)

    for raw in tqdm(iter_jsonlines(settings.character_file), desc="提取角色生日", unit="条"):
        stats["processed"] += 1

        record = extract_character_record(raw)
        if record is None:
            stats["skipped"] += 1
            continue

        buffer.append(record)

        if len(buffer) >= batch_size:
            if not dry_run:
                ins, mod = bulk_upsert(col, buffer, "character_id")
                stats["inserted"] += ins
                stats["modified"] += mod
            buffer.clear()

    # 写入剩余记录
    if buffer and not dry_run:
        ins, mod = bulk_upsert(col, buffer, "character_id")
        stats["inserted"] += ins
        stats["modified"] += mod

    logger.info(
        "角色生日提取完成：处理 %d 条，跳过 %d 条，新增 %d，更新 %d",
        stats["processed"],
        stats["skipped"],
        stats["inserted"],
        stats["modified"],
    )
    return stats
