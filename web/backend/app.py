"""
Quart Web 应用工厂

架构特点：
- 使用 app factory 模式，便于测试和多环境部署
- Motor（异步 MongoDB）替代 pymongo 的同步阻塞
- Redis 仅在运行时初始化，支持优雅关闭
- 所有路由模块化注册
- httpx.AsyncClient 在应用生命周期内复用，避免每次请求创建新连接
- CORS 由上游 nginx 统一处理，应用层不重复注入
"""

from __future__ import annotations

import logging
import sys

import httpx
import redis.asyncio as aioredis
from quart import Quart

from web.backend.routes.birthday import birthday_bp

logger = logging.getLogger(__name__)


def create_app() -> Quart:
    """
    创建并配置 Quart 应用实例。

    Returns
    -------
    Quart
        配置好的 Quart 应用。
    """
    # ── 日志配置（输出到终端，与 uvicorn 格式保持一致） ──────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,          # 覆盖 uvicorn 已设置的 root handler
    )
    # 压低第三方库的噪音日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    app = Quart(__name__)

    # ── 加载配置 ─────────────────────────────────────────────────────────
    sys.path.insert(0, str(__file__).rsplit("/web/", 1)[0])

    try:
        from bangumi_birthday.config import get_settings
        settings = get_settings()
    except Exception:
        # 如果包未安装，使用默认值
        class _Settings:
            mongodb_uri = "mongodb://localhost:27017/"
            mongodb_db = "hbd2waifu"
            redis_url = "redis://localhost:6379/0"
            cache_ttl = 3600
            bgm_user_agent = "stivine/bangumi-birthday/1.0"
            col_characters = "characters"
            col_date_char_sub = "date_char_sub"
            cors_allow_origin = "*"
        settings = _Settings()  # type: ignore[assignment]

    # ── 生命周期钩子 ──────────────────────────────────────────────────────
    @app.before_serving
    async def startup() -> None:
        # Motor 异步 MongoDB
        from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]

        mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
        db = mongo_client[settings.mongodb_db]
        app.extensions["mongo_client"] = mongo_client
        app.extensions["db"] = db

        # Redis
        redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        app.extensions["redis"] = redis_client

        # httpx 异步 HTTP 客户端（复用连接池）
        http_client = httpx.AsyncClient(
            headers={"User-Agent": settings.bgm_user_agent},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        app.extensions["http_client"] = http_client

        # 生日查询服务
        from web.backend.services.birthday_svc import BirthdayService

        app.extensions["birthday_svc"] = BirthdayService(db, redis_client)
        app.extensions["settings"] = settings

        logger.info("服务启动完成")

    @app.after_serving
    async def shutdown() -> None:
        if http_client := app.extensions.get("http_client"):
            await http_client.aclose()
        if redis_client := app.extensions.get("redis"):
            await redis_client.aclose()
        if mongo_client := app.extensions.get("mongo_client"):
            mongo_client.close()
        logger.info("服务已关闭")

    # ── 注册蓝图 ──────────────────────────────────────────────────────────
    app.register_blueprint(birthday_bp)

    # ── 全局错误处理 ──────────────────────────────────────────────────────
    @app.errorhandler(404)
    async def not_found(exc: Exception):  # type: ignore[return]
        from quart import jsonify
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(500)
    async def server_error(exc: Exception):  # type: ignore[return]
        logger.exception("未处理异常：%s", exc)
        from quart import jsonify
        return jsonify({"error": "Internal Server Error"}), 500

    return app


# ── 应用实例（供 uvicorn 直接使用） ────────────────────────────────────────
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
    )
