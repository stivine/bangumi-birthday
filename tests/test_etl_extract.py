"""
tests/test_etl_extract.py

ETL 提取逻辑单元测试（不依赖真实 MongoDB）
"""

import pytest

from bangumi_birthday.etl.extract_chars import extract_character_record
from bangumi_birthday.etl.extract_relations import extract_relation_record


class TestExtractCharacterRecord:
    def test_full_record(self) -> None:
        raw = {
            "id": "12345",
            "name": "レム",
            "infobox": "|简体中文名= 蕾姆\n|生日= 2月2日\n",
            "comments": 500,
            "collects": 8000,
        }
        result = extract_character_record(raw)
        assert result is not None
        assert result["character_id"] == 12345
        assert result["name"] == "レム"
        assert result["chinese_name"] == "蕾姆"
        assert result["birthday"] == "02-02"

    def test_no_birthday_returns_none(self) -> None:
        raw = {
            "id": "1",
            "name": "Unknown",
            "infobox": "|简体中文名= 某某\n|性别= 男\n",
        }
        assert extract_character_record(raw) is None

    def test_invalid_birthday_returns_none(self) -> None:
        raw = {
            "id": "2",
            "name": "Test",
            "infobox": "|生日= U.C.0055\n",
        }
        assert extract_character_record(raw) is None

    def test_no_chinese_name(self) -> None:
        raw = {
            "id": "3",
            "name": "テスト",
            "infobox": "|生日= 3月17日\n",
        }
        result = extract_character_record(raw)
        assert result is not None
        assert result["chinese_name"] == ""
        assert result["birthday"] == "03-17"

    def test_id_is_integer(self) -> None:
        raw = {
            "id": 999,
            "name": "Test",
            "infobox": "|生日= 12月25日\n",
        }
        result = extract_character_record(raw)
        assert result is not None
        assert isinstance(result["character_id"], int)


class TestExtractRelationRecord:
    def test_valid_record(self) -> None:
        raw = {"subject_id": "100", "character_id": "200", "type": "1", "order": "2"}
        result = extract_relation_record(raw)
        assert result is not None
        assert result["subject_id"] == 100
        assert result["character_id"] == 200
        assert result["type"] == 1
        assert result["order"] == 2

    def test_missing_field_returns_none(self) -> None:
        raw = {"subject_id": "100"}  # 缺少 character_id
        assert extract_relation_record(raw) is None

    def test_default_order(self) -> None:
        raw = {"subject_id": 1, "character_id": 2, "type": 0}
        result = extract_relation_record(raw)
        assert result is not None
        assert result["order"] == 0
