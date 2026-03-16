"""
主 CLI 入口，注册所有子命令。

用法：
    bgm-birthday --help
    bgm-birthday search --date 03-17
    bgm-birthday top-chars --person-id 32253 --build-cache
    bgm-birthday output-gen --excel /path/to/data.xlsm
"""

from __future__ import annotations

import logging

import click

from bangumi_birthday.cli.birthday_search import search_cmd
from bangumi_birthday.cli.output_gen import output_gen_cmd
from bangumi_birthday.cli.top_chars import top_chars_cmd


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="日志级别",
)
@click.version_option(version="1.0.0", prog_name="bgm-birthday")
def cli(log_level: str) -> None:
    """🎂 Bangumi Birthday — 二次元角色生日追踪工具"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


cli.add_command(search_cmd)
cli.add_command(top_chars_cmd)
cli.add_command(output_gen_cmd)


if __name__ == "__main__":
    cli()
