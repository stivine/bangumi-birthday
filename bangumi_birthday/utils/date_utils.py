"""
日期解析工具

支持从 Bangumi infobox 的"生日"字段中提取月-日，
兼容多种格式：
  - 日文：12月5日、01月01日
  - ISO：1990-12-05、2024/01/01
  - 带年中文：1990年12月5日
  - 仅月日中文：12月5日
  - 混合：U.C.0055（忽略）
"""

from __future__ import annotations

import re
from datetime import date

# 正则模式（按优先级排列）
# Group 命名：(?P<month>...)  (?P<day>...)
_PATTERNS: list[re.Pattern[str]] = [
    # 有年份：1990年12月5日 / 1990-12-05 / 1990/12/05
    re.compile(
        r"(?:(?:\d{2,4})[年\-/.])"
        r"(?P<month>\d{1,2})[月\-/.]"
        r"(?P<day>\d{1,2})日?"
    ),
    # 仅月日：12月5日 / 12-05 / 12/05
    re.compile(r"(?P<month>\d{1,2})[月\-/.](?P<day>\d{1,2})日?"),
]


def extract_month_day(raw: str) -> str | None:
    """
    从任意含日期信息的字符串中提取"MM-DD"格式的月日。

    Parameters
    ----------
    raw : str
        从 infobox 或其他字段取出的原始日期字符串。

    Returns
    -------
    str | None
        "MM-DD" 格式字符串，无法解析则返回 None。
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()

    for pattern in _PATTERNS:
        m = pattern.search(raw)
        if not m:
            continue

        month_str = m.group("month")
        day_str = m.group("day")

        # 防止误匹配连续数字（如 "12345" 中的 "23-45"）
        match_start = m.start()
        if match_start > 0 and raw[match_start - 1].isdigit():
            continue

        try:
            month = int(month_str)
            day = int(day_str)
            # 利用 date 对象验证日期合法性（不接受 0月、32日 等）
            date(1900, month, day)
            return f"{month:02d}-{day:02d}"
        except ValueError:
            continue

    return None


def extract_birthday_from_infobox(infobox: str) -> str | None:
    """
    从 Bangumi infobox 字符串中找到"生日= ..."字段，返回 MM-DD。

    Parameters
    ----------
    infobox : str
        角色/人物的完整 infobox 字符串。

    Returns
    -------
    str | None
        "MM-DD" 格式字符串，或 None。
    """
    if not infobox:
        return None

    # 提取 "生日= ..." 字段值（到换行 \r\n 或 \n 为止）
    m = re.search(r"生日\s*=\s*([^\r\n}]+)", infobox)
    if not m:
        return None

    raw_birthday = m.group(1).strip()
    return extract_month_day(raw_birthday)


def extract_chinese_name_from_infobox(infobox: str) -> str:
    """
    从 infobox 中提取"简体中文名"字段值。

    Parameters
    ----------
    infobox : str
        角色 infobox 字符串。

    Returns
    -------
    str
        简体中文名，无法提取时返回空字符串。
    """
    if not infobox:
        return ""

    m = re.search(r"简体中文名\s*=\s*([^\r\n}|]+)", infobox)
    if not m:
        return ""

    name = m.group(1).strip()
    # 去掉以 "|" 开头的异常值（数据格式错误）
    if name.startswith("|"):
        return ""
    return name


def parse_infobox_names(infobox: str) -> dict[str, object]:
    """
    从 infobox 中提取所有名称字段，供 id_match 使用。

    Returns
    -------
    dict 包含：
        simplified_cn: str
        second_cn: str
        japanese: str
        aliases: list[str]
        birthday_raw: str
    """
    result: dict[str, object] = {
        "simplified_cn": "",
        "second_cn": "",
        "japanese": "",
        "aliases": [],
        "birthday_raw": "",
    }

    if not infobox:
        return result

    def _extract(field: str) -> str:
        m = re.search(rf"{field}\s*=\s*([^\r\n}}|]+)", infobox)
        return m.group(1).strip() if m else ""

    result["simplified_cn"] = _extract("简体中文名")
    result["second_cn"] = _extract("第二中文名")
    result["japanese"] = _extract("日文名")

    # 提取生日原始文本
    bm = re.search(r"生日\s*=\s*([^\r\n}]+)", infobox)
    result["birthday_raw"] = bm.group(1).strip() if bm else ""

    # 提取别名列表 { [xxx] }
    aliases: list[str] = []
    alias_block = re.search(r"别名\s*=\s*\{\s*([^}]+)\}", infobox, re.DOTALL)
    if alias_block:
        for line in alias_block.group(1).splitlines():
            line = line.strip()
            if not line:
                continue
            # 去掉 [英文名|实际名] 格式的标签包装
            content = re.sub(r"^\[+|\]+$", "", line).strip()
            if "|" in content:
                _, name_part = content.split("|", 1)
                content = name_part.strip()
            if content:
                aliases.append(content)
    result["aliases"] = aliases

    return result
