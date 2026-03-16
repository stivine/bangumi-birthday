"""
CLI 命令：从 Excel 数据生成论坛格式的生日榜单。

用法：
    bgm-birthday output-gen --excel /path/to/hbd2waifu.xlsm --date 03-17
    bgm-birthday output-gen --excel /path/to/hbd2waifu.xlsm --date today
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import click

logger = logging.getLogger(__name__)


def _date_to_chinese(date_str: str) -> str:
    """将 MM-DD 格式转换为中文 N月N日，去掉前导零"""
    month, day = date_str.split("-")
    return f"{int(month)}月{int(day)}日"


def _popularity_score(comment: float, favorite: float) -> float:
    return comment * 1.0 + favorite * 0.3


def _image_urls_from_cell(cell_value: object) -> list[str]:
    """将单元格中的逗号分隔 ID 转换为图片 URL 列表"""
    raw = str(cell_value) if cell_value is not None else ""
    ids = [x.strip() for x in raw.split(",") if x.strip() and x.strip() != "nan"]
    return [f"https://api.bgm.tv/v0/characters/{cid}/image?type=medium" for cid in ids]


@click.command("output-gen")
@click.option(
    "--excel",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Excel 数据文件路径（.xlsm 或 .xlsx）",
)
@click.option(
    "--output",
    default="output.txt",
    show_default=True,
    type=click.Path(path_type=Path),
    help="输出文本文件路径",
)
@click.option(
    "--date",
    "target_date",
    default="today",
    show_default=True,
    help="目标日期，格式 MM-DD 或 'today'",
)
@click.option("--top-anime", default=1000, show_default=True, help="动画榜 Top N")
@click.option("--top-gal", default=40, show_default=True, help="Galgame 榜 Top N")
@click.option("--top-fangwen", default=30, show_default=True, help="芳文社榜 Top N")
@click.option(
    "--popularity-threshold",
    default=0.0,
    show_default=True,
    help="人气分数最低门槛",
)
def output_gen_cmd(
    excel: Path,
    output: Path,
    target_date: str,
    top_anime: int,
    top_gal: int,
    top_fangwen: int,
    popularity_threshold: float,
) -> None:
    """根据 Excel 数据生成论坛格式的角色生日榜单"""
    try:
        import pandas as pd
    except ImportError:
        raise click.ClickException("请先安装 pandas：pip install pandas openpyxl")

    # 解析日期
    if target_date.lower() == "today":
        today = date.today()
        target_date = today.strftime("%m-%d")

    date_chinese = _date_to_chinese(target_date)
    click.echo(f"目标日期：{date_chinese}（{target_date}）")

    # 读取 Excel
    click.echo(f"读取 Excel：{excel}")
    df = pd.read_excel(excel, engine="openpyxl", header=0)
    df.iloc[:, 0] = df.iloc[:, 0].astype(str)

    # 按生日过滤（J 列，第 10 列，0-indexed = 9）
    df = df[df.iloc[:, 9] == date_chinese]
    if df.empty:
        click.echo(f"⚠️  未找到生日为 {date_chinese} 的角色")
        return

    click.echo(f"找到 {len(df)} 条匹配记录，开始生成榜单...")

    anime_list: list[dict] = []
    gal_list: list[dict] = []
    fangwen_list: list[dict] = []

    for _, row in df.iterrows():
        char_id_cell = row.iloc[0]   # A 列：character_id
        c_type = row.iloc[2]         # C 列：类型（0=动画, 1=Galgame）
        h_type = row.iloc[7]         # H 列：子类型（3=Gal改动画）
        is_fangwen = row.iloc[10]    # K 列：是否芳文社
        output_text = row.iloc[12]   # M 列：输出文本
        comment = row.iloc[14]       # O 列：评论数
        favorite = row.iloc[15]      # P 列：收藏数

        import pandas as _pd
        if _pd.isna(comment) or _pd.isna(favorite):
            continue

        score = _popularity_score(float(comment), float(favorite))
        if score < popularity_threshold:
            continue

        entry = {
            "score": score,
            "output": str(output_text) if not _pd.isna(output_text) else "",
            "images": _image_urls_from_cell(char_id_cell),
        }

        if c_type == 0:
            anime_list.append(entry)

        if c_type == 1 or (c_type == 0 and h_type == 3):
            gal_list.append(entry)

        if is_fangwen == 1:
            fangwen_list.append(entry)

    # 排序 & Top-N
    anime_list = sorted(anime_list, key=lambda x: x["score"], reverse=True)[:top_anime]
    gal_list = sorted(gal_list, key=lambda x: x["score"], reverse=True)[:top_gal]
    fangwen_list = sorted(fangwen_list, key=lambda x: x["score"], reverse=True)[:top_fangwen]

    # 生成输出文本
    output_lines: list[str] = []

    def write_section(title: str, items: list[dict]) -> None:
        if not items:
            return
        output_lines.append(f"{date_chinese}{title}：\n")
        for item in items:
            output_lines.append(item["output"])
            for img in item["images"]:
                output_lines.append(f"[image]{img}[/image]")
            output_lines.append("")

    write_section("生日的人气动画角色", anime_list)
    write_section("生日的人气Galgame角色", gal_list)
    write_section("生日的芳文社人气角色", fangwen_list)

    text = "\n".join(output_lines)
    output.write_text(text, encoding="utf-8")

    click.echo(f"\n✅ 已生成榜单：{output}")
    click.echo(f"   动画榜：{len(anime_list)} 个角色")
    click.echo(f"   Galgame 榜：{len(gal_list)} 个角色")
    click.echo(f"   芳文社榜：{len(fangwen_list)} 个角色")
