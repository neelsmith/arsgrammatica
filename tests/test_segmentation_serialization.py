"""
Tests for arsgrammatica/segmentation_serialization.py's
serialize_segmentation()/write_segmentation()/read_segmentation().

Covers: exact serialized text for a small, hand-traced example; a full
write-then-read round trip; every malformed-input error
serialize_segmentation() can raise; and every malformed-file error
read_segmentation() can raise, including the cross-checks between its two
blocks that have no counterpart in the plain #!ctsdata/#!tokens shape
alone.
"""

import pytest

from arsgrammatica.models import Sentence, Token
from arsgrammatica.segmentation_serialization import (
    TOKENS_HEADER,
    TOKENS_LABEL,
    read_segmentation,
    serialize_segmentation,
    write_segmentation,
)
from arsgrammatica.serialization import SENTENCES_HEADER, SENTENCES_LABEL


def _write_raw(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


# ---------------------------------------------------------------------------
# serialize_segmentation()
# ---------------------------------------------------------------------------


def test_serialize_a_single_sentence():
    sentences = [
        Sentence(
            tokens=[
                Token(id="t0", text="Arma", citation="Aeneid 1.1"),
                Token(id="t1", text="virumque", citation="Aeneid 1.1"),
            ]
        )
    ]
    content = serialize_segmentation(sentences)
    assert content == (
        "#!sentences\n"
        "context_begin|first_token|context_end|last_token\n"
        "Aeneid 1.1|t0|Aeneid 1.1|t1\n"
        "\n"
        "#!tokens\n"
        "context|sentence_index|id|text\n"
        "Aeneid 1.1|0|t0|Arma\n"
        "Aeneid 1.1|0|t1|virumque\n"
    )


def test_serialize_multiple_sentences_numbers_sentence_index_across_the_whole_file():
    sentences = [
        Sentence(tokens=[Token(id="t0", text="Arma", citation="ex.1")]),
        Sentence(tokens=[Token(id="t1", text="cano", citation="ex.2")]),
    ]
    content = serialize_segmentation(sentences)
    assert "ex.1|0|t0|Arma" in content
    assert "ex.2|1|t1|cano" in content


def test_serialize_token_with_no_citation_writes_empty_field():
    sentences = [Sentence(tokens=[Token(id="t0", text="foo", citation=None)])]
    content = serialize_segmentation(sentences)
    assert "|t0|foo" in content
    assert "\n|t0|" in content  # sentences row: empty context_begin/context_end


def test_serialize_empty_sentence_raises():
    with pytest.raises(ValueError, match="no tokens"):
        serialize_segmentation([Sentence(tokens=[])])


def test_serialize_pipe_in_field_raises():
    sentences = [Sentence(tokens=[Token(id="t0", text="a|b", citation="ex.1")])]
    with pytest.raises(ValueError, match="cannot represent|has no way to escape|escape"):
        serialize_segmentation(sentences)


def test_serialize_newline_in_field_raises():
    sentences = [Sentence(tokens=[Token(id="t0", text="a\nb", citation="ex.1")])]
    with pytest.raises(ValueError):
        serialize_segmentation(sentences)


# ---------------------------------------------------------------------------
# write_segmentation() / read_segmentation(): round trip
# ---------------------------------------------------------------------------


def test_round_trip_write_then_read(tmp_path):
    sentences = [
        Sentence(
            tokens=[
                Token(id="t0", text="Arma", citation="Aeneid 1.1"),
                Token(id="t1", text="virumque", citation="Aeneid 1.1"),
                Token(id="t2", text="cano", citation="Aeneid 1.1"),
            ]
        ),
        Sentence(
            tokens=[
                Token(id="t3", text="Italiam", citation="Aeneid 1.2"),
                Token(id="t4", text="venit", citation="Aeneid 1.2"),
            ]
        ),
    ]
    path = str(tmp_path / "segmented.txt")
    write_segmentation(sentences, path)
    result = read_segmentation(path)
    assert result == sentences


def test_round_trip_with_no_citation(tmp_path):
    sentences = [Sentence(tokens=[Token(id="t0", text="foo", citation=None)])]
    path = str(tmp_path / "segmented.txt")
    write_segmentation(sentences, path)
    assert read_segmentation(path) == sentences


def test_blank_lines_between_blocks_are_ignored(tmp_path):
    content = (
        "\n"
        "#!sentences\n"
        "context_begin|first_token|context_end|last_token\n"
        "ex.1|t0|ex.1|t0\n"
        "\n"
        "#!tokens\n"
        "context|sentence_index|id|text\n"
        "ex.1|0|t0|foo\n"
        "\n"
    )
    path = _write_raw(tmp_path, "segmented.txt", content)
    result = read_segmentation(path)
    assert result == [Sentence(tokens=[Token(id="t0", text="foo", citation="ex.1")])]


def test_blocks_may_appear_in_either_order(tmp_path):
    content = (
        "#!tokens\n"
        "context|sentence_index|id|text\n"
        "ex.1|0|t0|foo\n"
        "\n"
        "#!sentences\n"
        "context_begin|first_token|context_end|last_token\n"
        "ex.1|t0|ex.1|t0\n"
    )
    path = _write_raw(tmp_path, "segmented.txt", content)
    result = read_segmentation(path)
    assert result == [Sentence(tokens=[Token(id="t0", text="foo", citation="ex.1")])]


# ---------------------------------------------------------------------------
# read_segmentation(): malformed-file errors
# ---------------------------------------------------------------------------


def test_missing_sentences_block_raises(tmp_path):
    content = "#!tokens\ncontext|sentence_index|id|text\nex.1|0|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match=r"missing required block.*#!sentences"):
        read_segmentation(path)


def test_missing_tokens_block_raises(tmp_path):
    content = "#!sentences\ncontext_begin|first_token|context_end|last_token\nex.1|t0|ex.1|t0\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match=r"missing required block.*#!tokens"):
        read_segmentation(path)


def test_repeated_block_raises(tmp_path):
    content = (
        "#!sentences\n"
        "context_begin|first_token|context_end|last_token\n"
        "ex.1|t0|ex.1|t0\n"
        "#!sentences\n"
        "context_begin|first_token|context_end|last_token\n"
        "ex.2|t1|ex.2|t1\n"
        "#!tokens\n"
        "context|sentence_index|id|text\n"
        "ex.1|0|t0|foo\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="appears more than once"):
        read_segmentation(path)


def test_label_with_no_header_before_next_block_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="label line but no header line"):
        read_segmentation(path)


def test_label_with_no_header_at_end_of_file_raises(tmp_path):
    content = f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n{SENTENCES_LABEL}\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="ends too early"):
        read_segmentation(path)


def test_wrong_sentences_header_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\nwrong|header\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected header"):
        read_segmentation(path)


def test_wrong_tokens_header_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\nwrong|header\nex.1|0|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected header"):
        read_segmentation(path)


def test_tokens_row_wrong_column_count_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo|extra\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected 4"):
        read_segmentation(path)


def test_sentences_row_wrong_column_count_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="expected 4"):
        read_segmentation(path)


def test_empty_token_id_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1||ex.1|\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0||foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="empty id"):
        read_segmentation(path)


def test_duplicate_token_id_raises(tmp_path):
    content = (
        f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n"
        f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\nex.1|0|t0|bar\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="duplicate token id"):
        read_segmentation(path)


def test_non_integer_sentence_index_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|zero|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="not an integer"):
        read_segmentation(path)


def test_negative_sentence_index_raises(tmp_path):
    content = f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|-1|t0|foo\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="negative"):
        read_segmentation(path)


def test_sentence_index_gap_raises(tmp_path):
    content = (
        f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\nex.2|t1|ex.2|t1\n"
        f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\nex.2|2|t1|bar\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="contiguous"):
        read_segmentation(path)


def test_sentence_count_mismatch_raises(tmp_path):
    content = (
        f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\nex.2|t1|ex.2|t1\n"
        f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="these must match"):
        read_segmentation(path)


def test_sentences_row_first_token_mismatch_raises(tmp_path):
    content = (
        f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t99|ex.1|t0\n"
        f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="names first_token/last_token"):
        read_segmentation(path)


def test_sentences_row_context_begin_mismatch_raises(tmp_path):
    content = (
        f"{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nwrong.context|t0|ex.1|t0\n"
        f"{TOKENS_LABEL}\n{TOKENS_HEADER}\nex.1|0|t0|foo\n"
    )
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="context_begin"):
        read_segmentation(path)


def test_data_line_before_any_label_raises(tmp_path):
    content = f"ex.1|0|t0|foo\n{SENTENCES_LABEL}\n{SENTENCES_HEADER}\nex.1|t0|ex.1|t0\n{TOKENS_LABEL}\n{TOKENS_HEADER}\n"
    path = _write_raw(tmp_path, "bad.txt", content)
    with pytest.raises(ValueError, match="appears before any"):
        read_segmentation(path)
