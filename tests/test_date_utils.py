"""
tests/test_date_utils.py

日期解析工具单元测试
"""

import pytest

from bangumi_birthday.utils.date_utils import (
    extract_birthday_from_infobox,
    extract_chinese_name_from_infobox,
    extract_month_day,
)


class TestExtractMonthDay:
    """测试 extract_month_day 函数"""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # 日文格式
            ("12月5日", "12-05"),
            ("1月1日", "01-01"),
            ("10月10日", "10-10"),
            # ISO 格式
            ("2024-01-01", "01-01"),
            ("1990-12-05", "12-05"),
            # 带年份中文
            ("1990年12月5日", "12-05"),
            ("2000年3月17日", "03-17"),
            # 斜杠
            ("12/25", "12-25"),
            # 带年份 + 斜杠
            ("1995/6/15", "06-15"),
            # 带前置零
            ("03-17", "03-17"),
            ("07月04日", "07-04"),
        ],
    )
    def test_valid_dates(self, raw: str, expected: str) -> None:
        assert extract_month_day(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            None,
            "U.C.0055",
            "未知",
            "N/A",
            "123456",           # 连续数字，无分隔符
            "0月0日",           # 非法月日
            "13月1日",          # 月份超出范围
            "2月30日",          # 日期超出范围
        ],
    )
    def test_invalid_dates(self, raw) -> None:
        assert extract_month_day(raw) is None

    def test_prevent_false_positive_from_long_number(self) -> None:
        """不应从"123456"中提取出"23-45"之类的误匹配"""
        assert extract_month_day("123456") is None

    def test_partial_match_in_sentence(self) -> None:
        """能从句子中提取日期"""
        result = extract_month_day("她的生日是3月17日，非常特别")
        assert result == "03-17"


class TestExtractBirthdayFromInfobox:
    """测试 extract_birthday_from_infobox 函数"""

    def test_typical_infobox(self) -> None:
        infobox = "{{Infobox Crt\n|简体中文名= 示例\n|生日= 3月17日\n|性别= 女\n}}"
        assert extract_birthday_from_infobox(infobox) == "03-17"

    def test_infobox_with_year(self) -> None:
        infobox = "{{Infobox\n|生日= 1990年12月5日\n}}"
        assert extract_birthday_from_infobox(infobox) == "12-05"

    def test_infobox_no_birthday(self) -> None:
        infobox = "{{Infobox Crt\n|简体中文名= 示例\n|性别= 男\n}}"
        assert extract_birthday_from_infobox(infobox) is None

    def test_empty_infobox(self) -> None:
        assert extract_birthday_from_infobox("") is None
        assert extract_birthday_from_infobox(None) is None  # type: ignore[arg-type]


class TestExtractChineseName:
    """测试 extract_chinese_name_from_infobox 函数"""

    def test_typical(self) -> None:
        infobox = "|简体中文名= 鲁路修\n|生日= 12月5日"
        assert extract_chinese_name_from_infobox(infobox) == "鲁路修"

    def test_with_trailing_space(self) -> None:
        infobox = "|简体中文名=  水树奈奈  \n|生日= 1月21日"
        assert extract_chinese_name_from_infobox(infobox) == "水树奈奈"

    def test_pipe_prefix_returns_empty(self) -> None:
        """以'|'开头的值应被丢弃"""
        infobox = "|简体中文名= |无效\n"
        assert extract_chinese_name_from_infobox(infobox) == ""

    def test_no_field(self) -> None:
        assert extract_chinese_name_from_infobox("{{Infobox}}") == ""

    def test_empty(self) -> None:
        assert extract_chinese_name_from_infobox("") == ""
