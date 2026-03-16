"""
CLI 命令：在本地 JSONLINES 文件中搜索指定日期生日的角色/人物。

用法：
    bgm-birthday search --date 03-17
    bgm-birthday search --date today --chars-only
    bgm-birthday search --date 12-25 --min-comments 5 --open
"""

from __future__ import annotations

import logging
import subprocess
import time
from datetime import date
from typing import Any

import click

from bangumi_birthday.config import get_settings
from bangumi_birthday.utils.date_utils import extract_birthday_from_infobox
from bangumi_birthday.utils.jsonlines import iter_jsonlines

logger = logging.getLogger(__name__)


def _open_url(url: str, browser_path: str | None) -> None:
    """在系统浏览器中打开 URL"""
    if browser_path:
        try:
            subprocess.Popen([browser_path, url])
        except Exception as exc:
            logger.warning("无法打开浏览器：%s", exc)
    else:
        import webbrowser
        webbrowser.open(url)


def search_birthday(
    file_path: Any,
    target_date: str,
    base_url: str,
    *,
    min_comments: int = 0,
    min_id: int | None = None,
    max_id: int | None = None,
    open_browser: bool = False,
    browser_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    从 JSONLINES 文件中搜索指定日期生日的角色/人物。

    Parameters
    ----------
    file_path : Path
        JSONLINES 数据文件路径。
    target_date : str
        目标日期，"MM-DD" 格式。
    base_url : str
        Bangumi 页面基础 URL（角色或人物）。
    min_comments : int
        最低评论数门槛。
    min_id, max_id : int | None
        ID 范围过滤。
    open_browser : bool
        是否在浏览器中打开匹配结果的页面。
    browser_path : str | None
        浏览器可执行路径（None 则使用系统默认）。

    Returns
    -------
    list[dict]
        匹配结果列表，每项包含 id, name, comments, collects, birthday。
    """
    results: list[dict[str, Any]] = []

    for raw in iter_jsonlines(file_path):
        try:
            item_id = int(raw.get("id", 0))
        except (ValueError, TypeError):
            continue

        if min_id is not None and item_id < min_id:
            continue
        if max_id is not None and item_id > max_id:
            continue

        infobox = raw.get("infobox", "")
        birthday = extract_birthday_from_infobox(infobox)
        if birthday != target_date:
            continue

        comments = int(raw.get("comments", 0))
        if comments < min_comments:
            continue

        entry = {
            "id": item_id,
            "name": raw.get("name", ""),
            "comments": comments,
            "collects": int(raw.get("collects", 0)),
            "birthday": birthday,
        }
        results.append(entry)

        if open_browser:
            _open_url(f"{base_url}{item_id}", browser_path)
            time.sleep(0.2)  # 避免瞬间打开太多标签

    return results


def _print_results(results: list[dict[str, Any]], title: str) -> None:
    """格式化输出搜索结果"""
    if not results:
        click.echo(f"{title}：无匹配结果")
        return

    # 按评论数降序排列
    sorted_results = sorted(results, key=lambda x: x["comments"], reverse=True)

    click.echo(f"\n{'─' * 50}")
    click.echo(f"{title}（共 {len(results)} 个）")
    click.echo(f"{'─' * 50}")

    for r in sorted_results:
        click.echo(f"  [{r['id']:>7}] {r['name']:<30}  评论:{r['comments']:>5}  收藏:{r['collects']:>6}")

    if sorted_results:
        top = sorted_results[0]
        click.echo(f"\n  ★ 评论最多：{top['name']} ({top['id']})  评论数 {top['comments']}")

    by_collects = sorted(results, key=lambda x: x["collects"], reverse=True)
    if by_collects:
        top_c = by_collects[0]
        click.echo(f"  ★ 收藏最多：{top_c['name']} ({top_c['id']})  收藏数 {top_c['collects']}")


@click.command("search")
@click.option(
    "--date",
    "target_date",
    default="today",
    show_default=True,
    help="目标生日，格式 MM-DD，或 'today'",
)
@click.option("--min-comments", default=0, show_default=True, help="最低评论数")
@click.option("--min-char-id", default=None, type=int, help="角色 ID 下限")
@click.option("--max-char-id", default=None, type=int, help="角色 ID 上限")
@click.option("--min-person-id", default=None, type=int, help="人物 ID 下限")
@click.option("--max-person-id", default=None, type=int, help="人物 ID 上限")
@click.option("--chars-only", is_flag=True, help="只搜索角色，跳过人物")
@click.option("--persons-only", is_flag=True, help="只搜索人物，跳过角色")
@click.option("--open", "open_browser", is_flag=True, help="在浏览器中打开匹配结果")
@click.option(
    "--person-comment-threshold",
    default=3,
    show_default=True,
    help="人物最低评论数（通常比角色更严格）",
)
def search_cmd(
    target_date: str,
    min_comments: int,
    min_char_id: int | None,
    max_char_id: int | None,
    min_person_id: int | None,
    max_person_id: int | None,
    chars_only: bool,
    persons_only: bool,
    open_browser: bool,
    person_comment_threshold: int,
) -> None:
    """在本地 JSONLINES 中搜索指定生日的角色/人物"""
    settings = get_settings()

    # 解析日期
    if target_date.lower() == "today":
        today = date.today()
        target_date = today.strftime("%m-%d")

    click.echo(f"\n🔍 搜索日期：{target_date}")

    browser_path = settings.browser_path

    if not persons_only:
        char_file = settings.character_file
        if not char_file.exists():
            click.echo(f"⚠️  角色数据文件不存在：{char_file}", err=True)
        else:
            click.echo(f"\n读取角色数据：{char_file}")
            char_results = search_birthday(
                char_file,
                target_date,
                base_url="https://bgm.tv/character/",
                min_comments=min_comments,
                min_id=min_char_id,
                max_id=max_char_id,
                open_browser=open_browser,
                browser_path=browser_path,
            )
            _print_results(char_results, f"{target_date} 生日角色")

    if not chars_only:
        person_file = settings.person_file
        if not person_file.exists():
            click.echo(f"⚠️  人物数据文件不存在：{person_file}", err=True)
        else:
            click.echo(f"\n读取人物数据：{person_file}")
            person_results = search_birthday(
                person_file,
                target_date,
                base_url="https://bgm.tv/person/",
                min_comments=max(min_comments, person_comment_threshold),
                min_id=min_person_id,
                max_id=max_person_id,
                open_browser=open_browser,
                browser_path=browser_path,
            )
            _print_results(person_results, f"{target_date} 生日人物（声优/创作者）")
