"""
Tests for arsgrammatica/serialization.py's serialize_analyses()/
write_analyses()/read_analyses().

Covers: a full round trip (object equality, and a second write producing
byte-identical output) across sentences with and without citations, every
kind of optional field (None, the 'root' sentinel, the relatedtoken2/
relationship2 overflow slot); every warning write_analyses() can return;
every malformed-file error read_analyses() can raise; that
serialize_analyses() and write_analyses() agree exactly; that
read_analyses() accepts a file with more than one instance of a block
label, merging them in file order; and a round trip built directly from
real gold fixtures for realistic coverage of the scheme's relation shapes.
"""

import pytest

from arsgrammatica.models import Sentence, Token, TokenAnalysis, VerbalExpression
from arsgrammatica.serialization import (
    read_analyses,
    serialize_analyses,
    split_analysis_by_sentence,
    write_analyses,
)
from fixtures.gold_examples import GOLD_EXAMPLES


def _tokengraph_for(slug):
    example = next(e for e in GOLD_EXAMPLES if e.slug == slug)
    return [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]


def _verbalunits_for(slug):
    example = next(e for e in GOLD_EXAMPLES if e.slug == slug)
    return [VerbalExpression(**vu) for vu in example.canned_answer["verbalunits"]]


def _sentence_from_tokengraph(tokengraph, citation=None):
    """Build a single Sentence spanning every token in `tokengraph`, in
    order, with a uniform citation (None by default, matching how the gold
    fixtures -- built directly from canned tokengraphs, not through
    segmentation_dspy.py -- never populate Token.citation)."""
    return Sentence(
        tokens=[Token(id=tok.id, text=tok.token, citation=citation) for tok in tokengraph]
    )


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def _two_sentence_fixture():
    """A hand-built two-sentence, two-citation-state passage covering: a
    citation on every token, a sentence with no citation at all, an
    enclitic with the relatedtoken2/relationship2 coordinating-conjunction
    overflow, the 'root' sentinel, and a dependent verb's ordinary
    relation -- deliberately not reusing a single gold fixture so the test
    also exercises multiple sentences/citations in one file."""
    s1_tokens = [
        Token(id="t0", text="Arma", citation="Aeneid 1.1"),
        Token(id="t1", text="virum", citation="Aeneid 1.1"),
        Token(id="t2", text="que", citation="Aeneid 1.1"),
        Token(id="t3", text="cano", citation="Aeneid 1.1"),
        Token(id="t4", text=".", citation="Aeneid 1.1"),
    ]
    s2_tokens = [
        Token(id="t5", text="Hercules"),
        Token(id="t6", text="cum"),
        Token(id="t7", text="perlustrasset"),
        Token(id="t8", text="pergit"),
        Token(id="t9", text="."),
    ]
    sentences = [Sentence(tokens=s1_tokens), Sentence(tokens=s2_tokens)]

    tokengraph = [
        TokenAnalysis(id="t0", token="Arma", tokentype="lexical", lemma="arma",
                      relatedtoken1="t3", relationship1="direct object"),
        TokenAnalysis(id="t1", token="virum", tokentype="lexical", lemma="vir",
                      relatedtoken1="t3", relationship1="direct object"),
        TokenAnalysis(id="t2", token="que", tokentype="enclitic",
                      relatedtoken1="t0", relationship1="coordinating conjunction",
                      relatedtoken2="t1", relationship2="coordinating conjunction"),
        TokenAnalysis(id="t3", token="cano", tokentype="lexical", lemma="cano",
                      verbalunitid="t3", relatedtoken1="root", relationship1="unit verb"),
        TokenAnalysis(id="t4", token=".", tokentype="punctuation"),
        TokenAnalysis(id="t5", token="Hercules", tokentype="lexical", lemma="Hercules",
                      relatedtoken1="t8", relationship1="subject"),
        TokenAnalysis(id="t6", token="cum", tokentype="lexical", lemma="cum",
                      relatedtoken1="t8", relationship1="subordinating conjunction"),
        TokenAnalysis(id="t7", token="perlustrasset", tokentype="lexical", lemma="perlustro",
                      verbalunitid="t7", relatedtoken1="t6", relationship1="unit verb"),
        TokenAnalysis(id="t8", token="pergit", tokentype="lexical", lemma="pergo",
                      verbalunitid="t8", relatedtoken1="root", relationship1="unit verb"),
        TokenAnalysis(id="t9", token=".", tokentype="punctuation"),
    ]

    verbalunits = [
        VerbalExpression(id="t3", syntactic_type="independent", semantic_type="transitive active"),
        VerbalExpression(id="t7", syntactic_type="dependent", semantic_type="transitive active"),
        VerbalExpression(id="t8", syntactic_type="independent", semantic_type="intransitive"),
    ]
    return sentences, verbalunits, tokengraph


def test_round_trip_preserves_every_object_exactly(tmp_path):
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    path = tmp_path / "analysis.txt"

    warnings = write_analyses(sentences, verbalunits, tokengraph, str(path))
    assert warnings == []

    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path))
    assert got_tokengraph == tokengraph
    assert got_verbalunits == verbalunits
    assert got_sentences == sentences


def test_round_tripped_data_writes_byte_identical_output(tmp_path):
    """Writing the objects read_analyses() reconstructs should reproduce
    the exact same file -- the whole point of a *deterministic*
    serialization."""
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    path1 = tmp_path / "first.txt"
    path2 = tmp_path / "second.txt"

    write_analyses(sentences, verbalunits, tokengraph, str(path1))
    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path1))
    write_analyses(got_sentences, got_verbalunits, got_tokengraph, str(path2))

    assert path1.read_text() == path2.read_text()


def test_file_contents_match_the_documented_format(tmp_path):
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    path = tmp_path / "analysis.txt"
    write_analyses(sentences, verbalunits, tokengraph, str(path))

    text = path.read_text()
    assert "#!sentences" in text
    assert "#!verbal_units" in text
    assert "#!tokens" in text
    assert "context_begin|first_token|context_end|last_token" in text
    assert "context|token|syntactic_type|semantic_type" in text
    assert (
        "context|id|tokentype|text|lemma|verbalunit|"
        "related1|relationship1|related2|relationship2"
    ) in text
    # The 'root' sentinel is written verbatim, not as an empty field.
    assert "|t3|lexical|cano|cano|t3|root|unit verb||" in text
    # A citation-free sentence's rows have an empty leading context column.
    assert "|t5|lexical|Hercules|Hercules||t8|subject||" in text


# ---------------------------------------------------------------------------
# serialize_analyses() -- same content as write_analyses(), returned as a
# string instead of written to a file
# ---------------------------------------------------------------------------


def test_serialize_analyses_matches_what_write_analyses_writes_to_disk(tmp_path):
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    path = tmp_path / "analysis.txt"

    write_warnings = write_analyses(sentences, verbalunits, tokengraph, str(path))
    content, serialize_warnings = serialize_analyses(sentences, verbalunits, tokengraph)

    assert content == path.read_text()
    assert serialize_warnings == write_warnings


def test_serialize_analyses_content_round_trips_through_read_analyses(tmp_path):
    """serialize_analyses()'s string, written to a file by the caller
    itself (not through write_analyses()), should read back identically to
    a file write_analyses() produced directly."""
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    content, warnings = serialize_analyses(sentences, verbalunits, tokengraph)
    assert warnings == []

    path = tmp_path / "from_string.txt"
    path.write_text(content)

    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path))
    assert got_tokengraph == tokengraph
    assert got_verbalunits == verbalunits
    assert got_sentences == sentences


def test_serialize_analyses_surfaces_the_same_warnings_and_raises(tmp_path):
    """serialize_analyses() must reproduce write_analyses()'s "degrade
    visibly" warnings (not raise for them) and its hard ValueErrors alike,
    since write_analyses() is now just a thin wrapper around it."""
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    # Detach t9's citation from any sentence, like
    # test_warns_when_a_token_is_not_covered_by_any_sentence below does.
    sentences[1].tokens = sentences[1].tokens[:-1]
    content, warnings = serialize_analyses(sentences, verbalunits, tokengraph)
    assert any("not found among the given sentences' tokens" in w for w in warnings)
    assert isinstance(content, str) and content  # still produced despite the warning

    with pytest.raises(ValueError, match="has no tokens"):
        serialize_analyses([Sentence(tokens=[])], [], [])


@pytest.mark.parametrize(
    "slug",
    [
        "unit_verb_hercules_cum",
        "relative_pronoun_latini_cum_quibus",
        "aside_equidem_pace_dixerim",
        "indirect_statement_facturum_fuisse_dixit",
        "coordinating_conjunction_dedit_et_dixit_esse",
        "depth_taurum_cum_quo_concubuit",
        "indirect_question_theseus_audit_quanta",
        "apposition_neptunus_aegeus_filius",
        "complementary_infinitive_amphion_expugnare_vellet",
        "gerund_ars_bene_disserendi",
    ],
    ids=lambda s: s,
)
def test_round_trip_against_real_gold_fixtures(tmp_path, slug):
    """Realistic coverage: every documented relation shape currently in
    gold_examples.py, run through an actual write/read round trip rather
    than a hand-built minimal example."""
    tokengraph = _tokengraph_for(slug)
    verbalunits = _verbalunits_for(slug)
    sentences = [_sentence_from_tokengraph(tokengraph)]

    path = tmp_path / "analysis.txt"
    warnings = write_analyses(sentences, verbalunits, tokengraph, str(path))
    assert warnings == []

    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path))
    assert got_tokengraph == tokengraph
    assert got_verbalunits == verbalunits
    assert got_sentences == sentences


def test_empty_lists_round_trip_to_an_empty_but_valid_file(tmp_path):
    path = tmp_path / "empty.txt"
    warnings = write_analyses([], [], [], str(path))
    assert warnings == []

    tokengraph, verbalunits, sentences = read_analyses(str(path))
    assert tokengraph == []
    assert verbalunits == []
    assert sentences == []


# ---------------------------------------------------------------------------
# write_analyses() warnings
# ---------------------------------------------------------------------------


def test_warns_when_a_token_is_not_covered_by_any_sentence(tmp_path):
    tokengraph = [
        TokenAnalysis(id="t0", token="foo", tokentype="lexical", verbalunitid="t0",
                      relatedtoken1="root", relationship1="unit verb"),
    ]
    verbalunits = [VerbalExpression(id="t0", syntactic_type="independent", semantic_type="intransitive")]
    path = tmp_path / "uncovered.txt"

    warnings = write_analyses([], verbalunits, tokengraph, str(path))
    assert any("t0" in w and "not found among the given sentences" in w for w in warnings)
    # Still written, with an empty context rather than raising.
    got_tokengraph, got_verbalunits, _ = read_analyses(str(path))
    assert got_tokengraph == tokengraph
    assert got_verbalunits == verbalunits


def test_warns_when_a_sentence_is_not_contiguous_in_the_tokengraph(tmp_path):
    tokengraph = [
        TokenAnalysis(id="t0", token="a", tokentype="lexical"),
        TokenAnalysis(id="t2", token="c", tokentype="lexical"),  # t1 missing here
        TokenAnalysis(id="t1", token="b", tokentype="lexical"),
    ]
    sentences = [Sentence(tokens=[Token(id="t0", text="a"), Token(id="t1", text="b")])]
    path = tmp_path / "noncontiguous.txt"

    warnings = write_analyses(sentences, [], tokengraph, str(path))
    assert any(
        "sentence at index 0" in w and "not a contiguous" in w for w in warnings
    )


def test_raises_on_an_empty_sentence(tmp_path):
    with pytest.raises(ValueError, match="no tokens"):
        write_analyses([Sentence(tokens=[])], [], [], str(tmp_path / "bad.txt"))


def test_raises_on_a_pipe_character_in_a_field(tmp_path):
    tokengraph = [TokenAnalysis(id="t0", token="a|b", tokentype="lexical")]
    with pytest.raises(ValueError, match=r"\|"):
        write_analyses([], [], tokengraph, str(tmp_path / "bad.txt"))


def test_raises_on_a_newline_in_a_field(tmp_path):
    tokengraph = [TokenAnalysis(id="t0", token="a", tokentype="lexical", lemma="a\nb")]
    with pytest.raises(ValueError, match="newline"):
        write_analyses([], [], tokengraph, str(tmp_path / "bad.txt"))


# ---------------------------------------------------------------------------
# read_analyses() errors
# ---------------------------------------------------------------------------

_TOKENS_HEADER = (
    "context|id|tokentype|text|lemma|verbalunit|"
    "related1|relationship1|related2|relationship2"
)


def _write_raw(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_missing_block_raises(tmp_path):
    content = f"#!tokens\n{_TOKENS_HEADER}\nctx|t0|lexical|a||||||\n"
    path = _write_raw(tmp_path, "missing.txt", content)
    with pytest.raises(ValueError, match="missing required block"):
        read_analyses(path)


def test_repeated_block_labels_are_merged_in_file_order(tmp_path):
    """Each of the three labels may appear more than once (see the module
    docstring) -- this is what makes a file built by literally
    concatenating two separate write_analyses() outputs (each a complete,
    self-contained trio of blocks) read back as one combined analysis,
    rather than raising or silently keeping only one instance."""
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\n"
        "Aeneid 1.1|t0|lexical|foo||t0|root|unit verb||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "Aeneid 1.1|t0|independent|intransitive\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "Aeneid 1.1|t0|Aeneid 1.1|t0\n"
        # A second, self-contained trio of blocks -- same labels, repeated.
        f"#!tokens\n{_TOKENS_HEADER}\n"
        "Aeneid 1.2|t1|lexical|bar||t1|root|unit verb||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "Aeneid 1.2|t1|independent|intransitive\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "Aeneid 1.2|t1|Aeneid 1.2|t1\n"
    )
    path = _write_raw(tmp_path, "repeated.txt", content)
    tokengraph, verbalunits, sentences = read_analyses(path)

    assert [tok.id for tok in tokengraph] == ["t0", "t1"]
    assert [vu.id for vu in verbalunits] == ["t0", "t1"]
    assert len(sentences) == 2
    assert sentences[0].tokens == [Token(id="t0", text="foo", citation="Aeneid 1.1")]
    assert sentences[1].tokens == [Token(id="t1", text="bar", citation="Aeneid 1.2")]


def test_block_label_without_its_own_header_raises(tmp_path):
    """A label line must be immediately followed by ITS OWN header line,
    even on a repeat instance -- jumping straight to the next block's
    label is malformed, not a zero-row instance of the first block."""
    content = (
        "#!tokens\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
    )
    path = _write_raw(tmp_path, "noheader.txt", content)
    with pytest.raises(ValueError, match="label line but no header line"):
        read_analyses(path)


def test_wrong_header_raises(tmp_path):
    content = (
        "#!tokens\nwrong|header\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
    )
    path = _write_raw(tmp_path, "badheader.txt", content)
    with pytest.raises(ValueError, match="expected header"):
        read_analyses(path)


def test_wrong_column_count_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\nctx|t0|lexical|a\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
    )
    path = _write_raw(tmp_path, "badcols.txt", content)
    with pytest.raises(ValueError, match="expected 10"):
        read_analyses(path)


def test_data_before_any_block_label_raises(tmp_path):
    content = "some stray line\n#!tokens\n" + _TOKENS_HEADER + "\n"
    path = _write_raw(tmp_path, "stray.txt", content)
    with pytest.raises(ValueError, match="before any"):
        read_analyses(path)


def test_verbal_units_referencing_unknown_token_id_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\nctx|t0|lexical|a||||||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "ctx|t99|independent|intransitive\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
    )
    path = _write_raw(tmp_path, "unknownvu.txt", content)
    with pytest.raises(ValueError, match="t99"):
        read_analyses(path)


def test_sentences_referencing_unknown_token_id_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\nctx|t0|lexical|a||||||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "ctx|t0|ctx|t99\n"
    )
    path = _write_raw(tmp_path, "unknownsent.txt", content)
    with pytest.raises(ValueError, match="not found in the #!tokens block"):
        read_analyses(path)


def test_sentence_context_mismatch_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\nAeneid 1.1|t0|lexical|a||||||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "WRONG|t0|Aeneid 1.1|t0\n"
    )
    path = _write_raw(tmp_path, "mismatch.txt", content)
    with pytest.raises(ValueError, match="does not match"):
        read_analyses(path)


def test_sentence_first_after_last_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\n"
        "ctx|t0|lexical|a||||||\n"
        "ctx|t1|lexical|b||||||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "ctx|t1|ctx|t0\n"
    )
    path = _write_raw(tmp_path, "reversed.txt", content)
    with pytest.raises(ValueError, match="comes after"):
        read_analyses(path)


def test_duplicate_token_id_raises(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\n"
        "ctx|t0|lexical|a||||||\n"
        "ctx|t0|lexical|b||||||\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
    )
    path = _write_raw(tmp_path, "dupid.txt", content)
    with pytest.raises(ValueError, match="duplicate token id"):
        read_analyses(path)


def test_blocks_may_appear_in_any_order(tmp_path):
    content = (
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "Aeneid 1.1|t0|independent|intransitive\n"
        "#!tokens\n" + _TOKENS_HEADER + "\n"
        "Aeneid 1.1|t0|lexical|foo||t0|root|unit verb||\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "Aeneid 1.1|t0|Aeneid 1.1|t0\n"
    )
    path = _write_raw(tmp_path, "reordered.txt", content)
    tokengraph, verbalunits, sentences = read_analyses(path)
    assert len(tokengraph) == 1
    assert len(verbalunits) == 1
    assert len(sentences) == 1
    assert sentences[0].tokens == [Token(id="t0", text="foo", citation="Aeneid 1.1")]


def test_blank_lines_between_blocks_are_tolerated(tmp_path):
    content = (
        f"#!tokens\n{_TOKENS_HEADER}\n"
        "Aeneid 1.1|t0|lexical|foo||t0|root|unit verb||\n"
        "\n\n"
        "#!verbal_units\ncontext|token|syntactic_type|semantic_type\n"
        "Aeneid 1.1|t0|independent|intransitive\n"
        "\n"
        "#!sentences\ncontext_begin|first_token|context_end|last_token\n"
        "Aeneid 1.1|t0|Aeneid 1.1|t0\n"
    )
    path = _write_raw(tmp_path, "blank.txt", content)
    tokengraph, verbalunits, sentences = read_analyses(path)
    assert len(tokengraph) == 1
    assert len(verbalunits) == 1
    assert len(sentences) == 1


# ---------------------------------------------------------------------------
# Implied/elided tokens (tokentype='implied sum'/'continued discourse'; see
# models.py's TokenAnalysis and IMPLIED_TOKENTYPES)
# ---------------------------------------------------------------------------
#
# An implied token was never part of the original per-sentence `tokens`
# list segmentation produced -- it's synthesized by analysis itself -- so
# it needs two things this format didn't need before: its `token`/text
# column (empty, like any other None field) must round-trip back to None
# rather than "" (see read_analyses()'s _parse_optional(text) fix), and it
# must be excluded from the sentence it sits inside of when reconstructing
# that sentence's own `tokens` list, even though it occupies a real
# position in #!tokens' row order between two of that sentence's real
# tokens.


def _sentence_with_implied_token_fixture():
    """"Rara [sunt]." -- one sentence, one real token (t0) plus one implied
    token (t0_implied) anchoring its own linking-verb verbal expression."""
    sentences = [Sentence(tokens=[Token(id="t0", text="Rara", citation="Livy 1.1")])]
    tokengraph = [
        TokenAnalysis(id="t0", token="Rara", tokentype="lexical",
                      relatedtoken1="t0_implied", relationship1="predicate"),
        TokenAnalysis(id="t0_implied", token=None, tokentype="implied sum",
                      verbalunitid="t0_implied", relatedtoken1="root", relationship1="unit verb"),
    ]
    verbalunits = [
        VerbalExpression(id="t0_implied", syntactic_type="independent", semantic_type="linking verb"),
    ]
    return sentences, verbalunits, tokengraph


def test_implied_token_round_trips_with_none_text_not_empty_string(tmp_path):
    sentences, verbalunits, tokengraph = _sentence_with_implied_token_fixture()
    path = tmp_path / "implied.txt"

    warnings = write_analyses(sentences, verbalunits, tokengraph, str(path))
    assert warnings == [], (
        "an implied token sitting inside a sentence's own token range should "
        "not trigger the 'not a contiguous run' warning"
    )

    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path))
    assert got_tokengraph == tokengraph
    assert got_verbalunits == verbalunits

    implied = next(tok for tok in got_tokengraph if tok.id == "t0_implied")
    assert implied.token is None, (
        f"expected the implied token's text to round-trip as None, got {implied.token!r}"
    )


def test_implied_token_is_excluded_from_its_sentences_reconstructed_tokens(tmp_path):
    sentences, verbalunits, tokengraph = _sentence_with_implied_token_fixture()
    path = tmp_path / "implied.txt"
    write_analyses(sentences, verbalunits, tokengraph, str(path))

    _got_tokengraph, _got_verbalunits, got_sentences = read_analyses(str(path))
    assert len(got_sentences) == 1
    # Only t0 (the real token) belongs in the reconstructed sentence -- the
    # implied token was never part of the original pre-analysis token list.
    assert got_sentences[0].tokens == [Token(id="t0", text="Rara", citation="Livy 1.1")]


# ---------------------------------------------------------------------------
# split_analysis_by_sentence()
# ---------------------------------------------------------------------------


def test_split_returns_one_slice_per_sentence_in_order():
    sentences, verbalunits, tokengraph = _two_sentence_fixture()

    slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

    assert len(slices) == 2
    s1_tokengraph, s1_verbalunits = slices[0]
    s2_tokengraph, s2_verbalunits = slices[1]

    assert [tok.id for tok in s1_tokengraph] == ["t0", "t1", "t2", "t3", "t4"]
    assert [tok.id for tok in s2_tokengraph] == ["t5", "t6", "t7", "t8", "t9"]

    # t3 (cano) anchors sentence 1's own verbal unit; t7/t8 anchor
    # sentence 2's two.
    assert [vu.id for vu in s1_verbalunits] == ["t3"]
    assert [vu.id for vu in s2_verbalunits] == ["t7", "t8"]


def test_split_round_trips_through_a_written_and_reread_file(tmp_path):
    """The realistic path: write a multi-sentence analysis, read it back,
    then split it -- rather than splitting the in-memory objects directly."""
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    path = tmp_path / "analysis.txt"
    write_analyses(sentences, verbalunits, tokengraph, str(path))

    got_tokengraph, got_verbalunits, got_sentences = read_analyses(str(path))
    slices = split_analysis_by_sentence(got_tokengraph, got_verbalunits, got_sentences)

    assert len(slices) == 2
    assert [tok.id for tok in slices[0][0]] == ["t0", "t1", "t2", "t3", "t4"]
    assert [tok.id for tok in slices[1][0]] == ["t5", "t6", "t7", "t8", "t9"]


def _sentence_with_medial_implied_token_fixture():
    """Two real tokens (t0, t1) with an implied token (t0_implied) sitting
    *between* them in tokengraph's own order -- "Puella [est] pulchra."
    Unlike _sentence_with_implied_token_fixture()'s single-real-token case
    (where the implied token trails the sentence's only real token, with
    nothing to bound it from above), this exercises an implied token
    genuinely nested inside a sentence's own [first, last] real-token
    range."""
    sentences = [Sentence(tokens=[Token(id="t0", text="Puella"), Token(id="t1", text="pulchra")])]
    tokengraph = [
        TokenAnalysis(id="t0", token="Puella", tokentype="lexical",
                      relatedtoken1="t0_implied", relationship1="subject"),
        TokenAnalysis(id="t0_implied", token=None, tokentype="implied sum",
                      verbalunitid="t0_implied", relatedtoken1="root", relationship1="unit verb"),
        TokenAnalysis(id="t1", token="pulchra", tokentype="lexical",
                      relatedtoken1="t0_implied", relationship1="predicate"),
    ]
    verbalunits = [
        VerbalExpression(id="t0_implied", syntactic_type="independent", semantic_type="linking verb"),
    ]
    return sentences, verbalunits, tokengraph


def test_split_includes_an_implied_token_nested_within_a_sentences_range():
    """An implied token positioned between two of a sentence's own real
    tokens belongs in that sentence's slice, even though it was never part
    of sentence.tokens -- it's part of the analysis, just with no surface
    realization."""
    sentences, verbalunits, tokengraph = _sentence_with_medial_implied_token_fixture()

    slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

    assert len(slices) == 1
    sentence_tokengraph, sentence_verbalunits = slices[0]
    assert [tok.id for tok in sentence_tokengraph] == ["t0", "t0_implied", "t1"]
    assert [vu.id for vu in sentence_verbalunits] == ["t0_implied"]


def test_split_excludes_a_trailing_implied_token_past_the_sentences_last_real_token():
    """A known, pre-existing limitation shared with read_analyses()'s own
    sentence reconstruction: an implied token placed AFTER a sentence's
    last real token (rather than nested between two real tokens) falls
    outside the [first, last] real-token range this function -- like
    read_analyses() -- uses to slice a sentence's own tokengraph.
    _sentence_with_implied_token_fixture()'s single-real-token "Rara
    [sunt]." case is exactly this: the implied token trails t0 with no
    further real token of the same sentence to bound it from above, so it
    isn't included here (matching read_analyses()'s own
    test_implied_token_is_excluded_from_its_sentences_reconstructed_tokens,
    which excludes it from the reconstructed Sentence for the same
    positional reason)."""
    sentences, verbalunits, tokengraph = _sentence_with_implied_token_fixture()

    slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

    assert len(slices) == 1
    sentence_tokengraph, sentence_verbalunits = slices[0]
    assert [tok.id for tok in sentence_tokengraph] == ["t0"]
    assert sentence_verbalunits == []


def test_split_rejects_a_sentence_with_no_tokens():
    _sentences, verbalunits, tokengraph = _two_sentence_fixture()

    with pytest.raises(ValueError, match="no tokens"):
        split_analysis_by_sentence(tokengraph, verbalunits, [Sentence(tokens=[])])


def test_split_rejects_a_boundary_token_missing_from_tokengraph():
    sentences, verbalunits, tokengraph = _two_sentence_fixture()
    # Drop t9 (sentence 2's own last token) from the tokengraph entirely.
    truncated_tokengraph = [tok for tok in tokengraph if tok.id != "t9"]

    with pytest.raises(ValueError, match="not present in the given tokengraph"):
        split_analysis_by_sentence(truncated_tokengraph, verbalunits, sentences)
