"""
JSONLINES 流式读取工具

提供懒加载生成器，避免将大文件（数百 MB）一次性加载进内存。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def iter_jsonlines(path: Path | str) -> Generator[dict[str, Any], None, None]:
    """
    逐行读取 JSONLINES 文件，以生成器方式产出每行解析后的字典。

    Parameters
    ----------
    path : Path | str
        JSONLINES 文件路径。

    Yields
    ------
    dict[str, Any]
        每行对应的 JSON 对象。

    Raises
    ------
    FileNotFoundError
        文件不存在时抛出。
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("第 %d 行 JSON 解析失败: %s", lineno, exc)


def count_lines(path: Path | str) -> int:
    """
    快速统计 JSONLINES 文件的有效行数（用于 tqdm 进度条）。

    Parameters
    ----------
    path : Path | str
        文件路径。

    Returns
    -------
    int
        有效（非空）行数。
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    count = 0
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def iter_jsonlines_with_progress(
    path: Path | str,
    desc: str = "",
    total: int | None = None,
) -> Iterator[dict[str, Any]]:
    """
    带 tqdm 进度条的 JSONLINES 迭代器。

    Parameters
    ----------
    path : Path | str
        文件路径。
    desc : str
        进度条描述文字。
    total : int | None
        总行数（若 None 则自动统计，会额外扫描一次文件）。

    Yields
    ------
    dict[str, Any]
        每行对应的 JSON 对象。
    """
    try:
        from tqdm import tqdm
    except ImportError:
        # tqdm 不可用时降级为普通迭代器
        yield from iter_jsonlines(path)
        return

    if total is None:
        total = count_lines(path)

    with tqdm(total=total, desc=desc or str(path)) as bar:
        for item in iter_jsonlines(path):
            yield item
            bar.update(1)
