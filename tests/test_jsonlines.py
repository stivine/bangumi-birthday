"""
tests/test_jsonlines.py

JSONLINES 读取工具单元测试
"""

import json
import tempfile
from pathlib import Path

import pytest

from bangumi_birthday.utils.jsonlines import count_lines, iter_jsonlines


def _make_jsonlines(records: list[dict], *, add_empty_lines: bool = False) -> Path:
    """创建临时 JSONLINES 文件，返回 Path"""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonlines", delete=False, encoding="utf-8"
    )
    for i, record in enumerate(records):
        tmp.write(json.dumps(record, ensure_ascii=False) + "\n")
        if add_empty_lines and i % 2 == 0:
            tmp.write("\n")
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


class TestIterJsonlines:
    def test_basic(self, tmp_path: Path) -> None:
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        path = _make_jsonlines(records)
        result = list(iter_jsonlines(path))
        assert result == records
        path.unlink()

    def test_skips_empty_lines(self) -> None:
        records = [{"id": i} for i in range(5)]
        path = _make_jsonlines(records, add_empty_lines=True)
        result = list(iter_jsonlines(path))
        assert result == records
        path.unlink()

    def test_unicode(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonlines"
        path.write_text('{"name": "水树奈奈"}\n{"name": "花泽香菜"}\n', encoding="utf-8")
        result = list(iter_jsonlines(path))
        assert result[0]["name"] == "水树奈奈"
        assert result[1]["name"] == "花泽香菜"

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            list(iter_jsonlines("/nonexistent/path.jsonlines"))

    def test_invalid_json_line_is_skipped(self, tmp_path: Path, caplog) -> None:
        path = tmp_path / "test.jsonlines"
        path.write_text('{"id": 1}\nNOT_JSON\n{"id": 3}\n', encoding="utf-8")
        import logging
        with caplog.at_level(logging.WARNING):
            result = list(iter_jsonlines(path))
        # 只有合法行被解析
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3


class TestCountLines:
    def test_count(self) -> None:
        records = [{"id": i} for i in range(10)]
        path = _make_jsonlines(records)
        assert count_lines(path) == 10
        path.unlink()

    def test_count_with_empty_lines(self) -> None:
        records = [{"id": i} for i in range(5)]
        path = _make_jsonlines(records, add_empty_lines=True)
        # 空行不计入
        assert count_lines(path) == 5
        path.unlink()

    def test_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            count_lines("/no/such/file.jsonlines")
