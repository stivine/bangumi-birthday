"""
ETL 命令行入口（Click）

用法：
    bgm-etl run          # 执行完整流水线
    bgm-etl characters   # 仅提取角色生日
    bgm-etl relations    # 仅导入作品-角色关系
    bgm-etl merge        # 仅执行合并
    bgm-etl indexes      # 仅创建索引
"""

from __future__ import annotations

import logging
import time

import click

from bangumi_birthday.db.mongo import ensure_indexes, get_sync_db

logger = logging.getLogger(__name__)


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="日志级别",
)
def cli(log_level: str) -> None:
    """Bangumi Birthday ETL 工具"""
    _setup_logging(log_level)


# ── 子命令 ───────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--batch-size", default=2000, show_default=True, help="每批写入文档数")
@click.option("--dry-run", is_flag=True, help="仅统计，不写库")
def characters(batch_size: int, dry_run: bool) -> None:
    """提取角色生日并写入 MongoDB characters 集合"""
    from bangumi_birthday.etl import extract_chars

    t0 = time.perf_counter()
    stats = extract_chars.run(batch_size=batch_size, dry_run=dry_run)
    elapsed = time.perf_counter() - t0
    click.echo(f"完成（{elapsed:.1f}s）：{stats}")


@cli.command()
@click.option("--batch-size", default=5000, show_default=True, help="每批写入文档数")
@click.option("--dry-run", is_flag=True)
def relations(batch_size: int, dry_run: bool) -> None:
    """导入 subject-characters 关系到 MongoDB"""
    from bangumi_birthday.etl import extract_relations

    t0 = time.perf_counter()
    stats = extract_relations.run(batch_size=batch_size, dry_run=dry_run)
    elapsed = time.perf_counter() - t0
    click.echo(f"完成（{elapsed:.1f}s）：{stats}")


@cli.command()
@click.option("--batch-size", default=2000, show_default=True)
def merge(batch_size: int) -> None:
    """合并 characters 与 subject_characters，生成 date_char_sub"""
    from bangumi_birthday.etl import merge as merge_mod

    t0 = time.perf_counter()
    stats = merge_mod.run(batch_size=batch_size)
    elapsed = time.perf_counter() - t0
    click.echo(f"完成（{elapsed:.1f}s）：{stats}")


@cli.command()
def indexes() -> None:
    """在所有集合上创建索引"""
    db = get_sync_db()
    ensure_indexes(db)
    click.echo("索引创建完成")


@cli.command()
@click.option("--batch-size-chars", default=2000, show_default=True)
@click.option("--batch-size-rels", default=5000, show_default=True)
@click.option("--skip-chars", is_flag=True, help="跳过角色提取步骤")
@click.option("--skip-relations", is_flag=True, help="跳过关系导入步骤")
@click.option("--skip-merge", is_flag=True, help="跳过合并步骤")
def run(
    batch_size_chars: int,
    batch_size_rels: int,
    skip_chars: bool,
    skip_relations: bool,
    skip_merge: bool,
) -> None:
    """执行完整 ETL 流水线（characters → relations → merge → indexes）"""
    from bangumi_birthday.etl import extract_chars, extract_relations
    from bangumi_birthday.etl import merge as merge_mod

    total_start = time.perf_counter()

    click.echo("═" * 60)
    click.echo("Bangumi Birthday ETL 流水线")
    click.echo("═" * 60)

    if not skip_chars:
        click.echo("\n[1/4] 提取角色生日...")
        t0 = time.perf_counter()
        stats = extract_chars.run(batch_size=batch_size_chars)
        click.echo(f"      完成（{time.perf_counter()-t0:.1f}s）：{stats}")
    else:
        click.echo("\n[1/4] 跳过角色提取")

    if not skip_relations:
        click.echo("\n[2/4] 导入作品-角色关系...")
        t0 = time.perf_counter()
        stats = extract_relations.run(batch_size=batch_size_rels)
        click.echo(f"      完成（{time.perf_counter()-t0:.1f}s）：{stats}")
    else:
        click.echo("\n[2/4] 跳过关系导入")

    if not skip_merge:
        click.echo("\n[3/4] 合并数据...")
        t0 = time.perf_counter()
        stats = merge_mod.run()
        click.echo(f"      完成（{time.perf_counter()-t0:.1f}s）：{stats}")
    else:
        click.echo("\n[3/4] 跳过合并")

    click.echo("\n[4/4] 创建索引...")
    db = get_sync_db()
    ensure_indexes(db)
    click.echo("      索引创建完成")

    total_elapsed = time.perf_counter() - total_start
    click.echo(f"\n✅ 全部完成，总耗时 {total_elapsed:.1f}s")


if __name__ == "__main__":
    cli()
