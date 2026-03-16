"""统一配置管理，使用 pydantic-settings 读取环境变量 / .env 文件"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 数据文件 ────────────────────────────────────────────────
    bgm_data_dir: Path = Path("/home/tengjun/code/bangumi")

    @property
    def character_file(self) -> Path:
        return self.bgm_data_dir / "character.jsonlines"

    @property
    def person_file(self) -> Path:
        return self.bgm_data_dir / "person.jsonlines"

    @property
    def subject_characters_file(self) -> Path:
        return self.bgm_data_dir / "subject-characters.jsonlines"

    @property
    def person_characters_file(self) -> Path:
        return self.bgm_data_dir / "person-characters.jsonlines"

    @property
    def subject_file(self) -> Path:
        return self.bgm_data_dir / "subject.jsonlines"

    # ── MongoDB ─────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_db: str = "hbd2waifu"

    # MongoDB 集合名称
    col_characters: str = "characters"
    col_subject_characters: str = "subject_characters"
    col_date_char_sub: str = "date_char_sub"

    # ── Redis ───────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600  # 秒

    # ── 浏览器（CLI 可选） ─────────────────────────────────────
    browser_path: str | None = None

    # ── 日志 ────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Bangumi API ─────────────────────────────────────────────
    bgm_api_base: str = "https://api.bgm.tv/v0"
    bgm_user_agent: str = "stivine/bangumi-birthday/1.0 (https://github.com/stivine/bangumi-birthday)"

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level 必须是 {allowed} 之一")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局单例 Settings 对象（进程内缓存）"""
    return Settings()
