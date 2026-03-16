"""
Pydantic 数据模型

定义数据库文档与 API 响应的数据结构，提供类型安全和验证。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CharacterRecord(BaseModel):
    """characters 集合文档"""

    character_id: int = Field(..., description="Bangumi character ID")
    name: str = Field(..., description="原始名称（通常为日文）")
    chinese_name: str = Field(default="", description="简体中文名")
    birthday: str | None = Field(default=None, description="生日，MM-DD 格式")

    @field_validator("birthday")
    @classmethod
    def _validate_birthday(cls, v: str | None) -> str | None:
        if v is None:
            return None
        import re
        if not re.fullmatch(r"\d{2}-\d{2}", v):
            raise ValueError(f"birthday 必须为 MM-DD 格式，得到: {v!r}")
        return v


class SubjectCharacterRecord(BaseModel):
    """subject_characters 集合文档（来自 subject-characters.jsonlines）"""

    subject_id: int
    character_id: int
    type: int = Field(description="角色类型（主角/配角等）")
    order: int = Field(default=0, description="排序权重")


class DateCharSubRecord(BaseModel):
    """date_char_sub 集合文档（合并后的主表）"""

    birthday: str | None
    character_id: int
    subject_id: int
    type: int
    order: int
    name: str
    chinese_name: str = ""


# ── API 响应模型 ─────────────────────────────────────────────────────────────


class CharacterResponse(BaseModel):
    """向前端返回的角色卡片数据"""

    character_id: int
    name: str
    chinese_name: str = ""
    birthday: str | None = None


class BirthdayQueryResult(BaseModel):
    """生日查询结果"""

    date: str
    total: int
    characters: list[CharacterResponse]
