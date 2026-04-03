"""
生日查询相关路由

GET /api/today           — 今日生日的所有角色
GET /api/date/<mm-dd>    — 指定日期生日的所有角色
GET /api/hbd2waifu       — 用户收藏中，指定日期生日的角色
  ?userid=xxx            必须；Bangumi 用户名或 ID
  &date=MM-DD            可选；默认今日
  &subject_type=2        可选；Bangumi 条目类型（1=书, 2=动画, 4=游戏 等）
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date

import httpx
from quart import Blueprint, current_app, jsonify, request
from web.backend.services.birthday_svc import (
    UserSubjectLookupBusyError,
    UserSubjectLookupTimeoutError,
)

logger = logging.getLogger(__name__)

birthday_bp = Blueprint("birthday", __name__, url_prefix="/api")


def _today_str() -> str:
    return date.today().strftime("%m-%d")


@birthday_bp.route("/")
async def health() -> tuple:
    return jsonify({"status": "ok", "service": "bangumi-birthday"}), 200


@birthday_bp.route("/today")
async def today_birthday() -> tuple:
    """返回今日生日的所有角色（全站）"""
    svc = current_app.extensions["birthday_svc"]
    today = _today_str()
    characters = await svc.get_characters_by_date(today)
    return jsonify(characters), 200


@birthday_bp.route("/date/<string:date_str>")
async def date_birthday(date_str: str) -> tuple:
    """
    返回指定日期生日的所有角色（全站）。
    date_str: MM-DD 格式
    """
    if not re.fullmatch(r"\d{2}-\d{2}", date_str):
        return jsonify({"error": "日期格式不正确，应为 MM-DD"}), 400

    svc = current_app.extensions["birthday_svc"]
    characters = await svc.get_characters_by_date(date_str)
    return jsonify(characters), 200


@birthday_bp.route("/hbd2waifu")
async def user_birthday() -> tuple:
    """
    返回用户收藏作品中，指定日期生日的角色。

    Query params:
        userid (required): Bangumi 用户名或 ID
        date (optional, default=today): MM-DD 格式
        subject_type (optional): Bangumi 条目类型
    """
    t0 = time.monotonic()

    userid = request.args.get("userid", "").strip()
    if not userid:
        return jsonify({"error": "缺少参数：userid"}), 400

    date_str = request.args.get("date", _today_str()).strip()
    if not re.fullmatch(r"\d{2}-\d{2}", date_str):
        return jsonify({"error": "date 格式不正确，应为 MM-DD"}), 400

    subject_type_raw = request.args.get("subject_type")
    subject_type = int(subject_type_raw) if subject_type_raw else None

    logger.info("hbd2waifu  user=%-20s  date=%s", userid, date_str)

    http_client: httpx.AsyncClient = current_app.extensions["http_client"]
    svc = current_app.extensions["birthday_svc"]

    try:
        subject_ids = await svc.get_user_subject_ids(
            userid,
            http_client=http_client,
            subject_type=subject_type,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return jsonify({"error": f"用户 {userid!r} 不存在"}), 404
        logger.error("Bangumi API 请求失败：%s", exc)
        return jsonify({"error": "获取用户收藏失败，请稍后重试"}), 502
    except httpx.PoolTimeout as exc:
        logger.warning("Bangumi API 连接池繁忙：%s", exc)
        return jsonify({"error": "上游服务繁忙，请稍后重试"}), 503
    except httpx.RequestError as exc:
        logger.error("Bangumi API 网络异常：%s", exc)
        return jsonify({"error": "上游服务暂时不可用，请稍后重试"}), 503
    except UserSubjectLookupBusyError:
        return jsonify({"error": "当前查询过多，请稍后重试"}), 503
    except UserSubjectLookupTimeoutError:
        return jsonify({"error": "查询上游收藏超时，请稍后重试"}), 504
    except Exception as exc:
        logger.exception("未知错误：%s", exc)
        return jsonify({"error": "服务器内部错误"}), 500

    characters = await svc.get_characters_by_date(date_str, subject_ids=subject_ids)

    elapsed = time.monotonic() - t0
    logger.info(
        "hbd2waifu  user=%-20s  date=%s  subjects=%d  results=%d  total=%.2fs",
        userid, date_str, len(subject_ids), len(characters), elapsed,
    )

    return jsonify(characters), 200
