"""
Tests for arsgrammatica/ctsdata.py's read_ctsdata().

Covers: a basic single-row read (urn used verbatim as CitedText.citation,
text verbatim); multiple rows and multiple '#!ctsdata' blocks merged in
file order (mirroring test_serialization.py's own repeated-block
coverage); a custom delimiter; and every malformed-file error
read_ctsdata() can raise.
"""

import pytest

from arsgrammatica.ctsdata import read_ctsdata
from arsgrammatica.models import CitedText


def _write_raw(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_single_row_uses_the_whole_urn_as_citation(tmp_path):
    content = (
        "#!ctsdata\n"
        "urn|text\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.\n"
    )
    path = _write_raw(tmp_path, "ctsdata.txt", content)
    rows = read_ctsdata(path)
    assert rows == [
        CitedText(
            citation="urn:cts:compnov:bible.genesis.vulgate:45.1",
            text="Non se poterat ultra tenere.",
        )
    ]


def test_multiple_rows_in_one_block_preserve_file_order(tmp_path):
    content = (
        "#!ctsdata\n"
        "urn|text\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.2|Clamavit ergo.\n"
    )
    path = _write_raw(tmp_path, "ctsdata.txt", content)
    rows = read_ctsdata(path)
    assert [r.citation for r in rows] == [
        "urn:cts:compnov:bible.genesis.vulgate:45.1",
        "urn:cts:compnov:bible.genesis.vulgate:45.2",
    ]
    assert [r.text for r in rows] == ["Non se poterat ultra tenere.", "Clamavit ergo."]


def test_repeated_blocks_are_merged_in_file_order(tmp_path):
    """Same convention as serialization.py's read_analyses(): more than one
    '#!ctsdata' block, each with its own header line, concatenates into one
    row list rather than raising or keeping only the first."""
    content = (
        "#!ctsdata\n"
        "urn|text\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.\n"
        "#!ctsdata\n"
        "urn|text\n"
        "urn:cts:compnov:bible.exodus.vulgate:1.1|Haec sunt nomina.\n"
    )
    path = _write_raw(tmp_path, "ctsdata.txt", content)
    rows = read_ctsdata(path)
    assert [r.citation for r in rows] == [
        "urn:cts:compnov:bible.genesis.vulgate:45.1",
        "urn:cts:compnov:bible.exodus.vulgate:1.1",
    ]


def test_blank_lines_between_and_within_blocks_are_ignored(tmp_path):
    content = (
        "\n"
        "#!ctsdata\n"
        "\n"
        "urn|text\n"
        "\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.\n"
        "\n"
    )
    path = _write_raw(tmp_path, "ctsdata.txt", content)
    rows = read_ctsdata(path)
    assert len(rows) == 1


def test_custom_delimiter(tmp_path):
    content = (
        "#!ctsdata\n"
        "urn\ttext\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1\tNon se poterat ultra tenere.\n"
    )
    path = _write_raw(tmp_path, "ctsdata.tsv", content)
    rows = read_ctsdata(path, delimiter="\t")
    assert rows == [
        CitedText(
            citation="urn:cts:compnov:bible.genesis.vulgate:45.1",
            text="Non se poterat ultra tenere.",
        )
    ]


def test_text_may_contain_colons(tmp_path):
    """The delimiter is '|', not ':' -- a passage's own text is free to
    contain colons (e.g. a quoted speech marker) without being mistaken
    for part of the urn column."""
    content = (
        "#!ctsdata\n"
        "urn|text\n"
        "urn:cts:compnov:bible.genesis.vulgate:45.1|Dixit: Non possum.\n"
    )
    path = _write_raw(tmp_path, "ctsdata.txt", content)
    rows = read_ctsdata(path)
    assert rows[0].text == "Dixit: Non possum."


def test_missing_block_raises(tmp_path):
    content = "\n\n"
    path = _write_raw(tmp_path, "missing.txt", content)
    with pytest.raises(ValueError, match="no '#!ctsdata' block"):
        read_ctsdata(path)


def test_data_line_before_any_label_raises(tmp_path):
    content = "urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat.\n#!ctsdata\nurn|text\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="appears before any"):
        read_ctsdata(path)


def test_label_with_no_header_before_next_block_raises(tmp_path):
    content = "#!ctsdata\n#!ctsdata\nurn|text\nurn:cts:compnov:bible.genesis.vulgate:45.1|x\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="label line but no header line"):
        read_ctsdata(path)


def test_label_with_no_header_at_end_of_file_raises(tmp_path):
    content = "#!ctsdata\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="ends too early"):
        read_ctsdata(path)


def test_wrong_header_raises(tmp_path):
    content = "#!ctsdata\ntext|urn\nurn:cts:compnov:bible.genesis.vulgate:45.1|x\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected header"):
        read_ctsdata(path)


def test_wrong_column_count_raises(tmp_path):
    content = "#!ctsdata\nurn|text\nurn:cts:compnov:bible.genesis.vulgate:45.1|extra|columns\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected 2"):
        read_ctsdata(path)


def test_empty_urn_column_raises(tmp_path):
    content = "#!ctsdata\nurn|text\n|Non se poterat ultra tenere.\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="empty urn"):
        read_ctsdata(path)


def test_empty_text_column_raises(tmp_path):
    content = "#!ctsdata\nurn|text\nurn:cts:compnov:bible.genesis.vulgate:45.1|\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="empty text"):
        read_ctsdata(path)


def test_urn_with_wrong_part_count_raises(tmp_path):
    content = "#!ctsdata\nurn|text\nurn:cts:compnov:45.1|Non se poterat ultra tenere.\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="colon-separated part"):
        read_ctsdata(path)


def test_urn_with_empty_final_part_raises(tmp_path):
    content = "#!ctsdata\nurn|text\nurn:cts:compnov:bible.genesis.vulgate:|Non se poterat.\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="empty final"):
        read_ctsdata(path)
