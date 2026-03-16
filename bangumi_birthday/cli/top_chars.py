"""
CLI 命令：查找声优/人物的代表角色 Top-K（按评论数排名）。

用法：
    bgm-birthday top-chars --person-id 32253
    bgm-birthday top-chars --person-id 32253 --top 20 --open
"""

from __future__ import annotations

import heapq
import json
import logging
from pathlib import Path
from typing import Any

import click
from tqdm import tqdm

from bangumi_birthday.config import get_settings
from bangumi_birthday.utils.jsonlines import iter_jsonlines

logger = logging.getLogger(__name__)

# 缓存文件名
_CACHE_PERSON = "person_entries.json"
_CACHE_CHAR = "character_entries.json"


class TopK:
    """最小堆实现的 Top-K 维护器，内存高效。"""

    def __init__(self, k: int) -> None:
        self.k = k
        self._heap: list[tuple[int, int, str]] = []  # (comments, char_id, name)

    def push(self, comments: int, char_id: int, name: str) -> None:
        entry = (comments, char_id, name)
        if len(self._heap) < self.k:
            heapq.heappush(self._heap, entry)
        elif comments > self._heap[0][0]:
            heapq.heapreplace(self._heap, entry)

    def results(self) -> list[tuple[int, int, str]]:
        """返回降序排列的 Top-K 列表"""
        return sorted(self._heap, key=lambda x: x[0], reverse=True)


def _build_cache(settings: Any, *, cache_dir: Path) -> None:
    """扫描 JSONLINES 文件，构建声优→角色列表 和 角色→评论数 的 JSON 缓存。"""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ── 声优-角色映射 ─────────────────────────────────────────────────────
    person_to_chars: dict[str, list[int]] = {}

    for entry in tqdm(
        iter_jsonlines(settings.person_characters_file),
        desc="构建声优-角色缓存",
        unit="条",
    ):
        pid = str(entry.get("person_id", ""))
        cid = int(entry.get("character_id", 0))
        if pid not in person_to_chars:
            person_to_chars[pid] = []
        if cid not in person_to_chars[pid]:
            person_to_chars[pid].append(cid)

    with (cache_dir / _CACHE_PERSON).open("w", encoding="utf-8") as f:
        json.dump(person_to_chars, f, ensure_ascii=False)
    logger.info("声优-角色缓存已保存：%s", cache_dir / _CACHE_PERSON)

    # ── 角色评论数映射 ────────────────────────────────────────────────────
    char_info: dict[str, list[Any]] = {}  # char_id_str → [comments, name]

    for entry in tqdm(
        iter_jsonlines(settings.character_file),
        desc="构建角色评论缓存",
        unit="条",
    ):
        cid = str(entry.get("id", ""))
        char_info[cid] = [int(entry.get("comments", 0)), entry.get("name", "")]

    with (cache_dir / _CACHE_CHAR).open("w", encoding="utf-8") as f:
        json.dump(char_info, f, ensure_ascii=False)
    logger.info("角色评论缓存已保存：%s", cache_dir / _CACHE_CHAR)


def _load_cache(cache_dir: Path) -> tuple[dict[str, list[int]], dict[str, list[Any]]]:
    """加载缓存文件，返回 (person_to_chars, char_info)。"""
    p_path = cache_dir / _CACHE_PERSON
    c_path = cache_dir / _CACHE_CHAR

    if not p_path.exists() or not c_path.exists():
        raise FileNotFoundError(
            f"缓存文件不存在，请先执行 `bgm-birthday top-chars --build-cache`\n"
            f"  预期路径：{cache_dir}"
        )

    with p_path.open("r", encoding="utf-8") as f:
        person_to_chars: dict[str, list[int]] = json.load(f)

    with c_path.open("r", encoding="utf-8") as f:
        char_info: dict[str, list[Any]] = json.load(f)

    return person_to_chars, char_info


@click.command("top-chars")
@click.option("--person-id", required=True, type=str, help="声优/人物的 Bangumi ID")
@click.option("--top", "k", default=15, show_default=True, help="返回前 K 个角色")
@click.option("--build-cache", is_flag=True, help="重新构建本地缓存（首次运行须加此参数）")
@click.option(
    "--cache-dir",
    default=".",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="缓存文件存放目录",
)
@click.option("--open", "open_browser", is_flag=True, help="在浏览器中打开 Top-K 角色页面")
def top_chars_cmd(
    person_id: str,
    k: int,
    build_cache: bool,
    cache_dir: Path,
    open_browser: bool,
) -> None:
    """查找某声优的代表角色 Top-K（按评论数）"""
    settings = get_settings()

    if build_cache:
        click.echo("构建缓存（首次约需数分钟）...")
        _build_cache(settings, cache_dir=cache_dir)
        click.echo("缓存构建完成")

    click.echo(f"加载缓存（目录：{cache_dir}）...")
    try:
        person_to_chars, char_info = _load_cache(cache_dir)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    chars = person_to_chars.get(person_id)
    if not chars:
        raise click.ClickException(f"未找到 person_id={person_id!r} 的角色数据")

    top_k = TopK(k)
    for cid in chars:
        info = char_info.get(str(cid))
        if info:
            top_k.push(info[0], cid, info[1])

    results = top_k.results()

    click.echo(f"\n声优 {person_id} 的 Top-{k} 代表角色：")
    click.echo("─" * 50)
    for rank, (comments, cid, name) in enumerate(results, 1):
        click.echo(f"  {rank:>2}. [{cid:>7}] {name:<30}  评论：{comments}")
        if open_browser:
            import subprocess, time
            bp = settings.browser_path
            url = f"https://bgm.tv/character/{cid}"
            if bp:
                subprocess.Popen([bp, url])
            else:
                import webbrowser
                webbrowser.open(url)
            time.sleep(0.3)
