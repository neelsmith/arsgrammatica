"""
Tests for arsgrammatica/rendering.py's tokengraph_to_text() and
tokengraph_to_html().
 
Split into parts: targeted unit tests for each join rule (built from small
hand-built TokenAnalysis lists, since the existing gold fixtures use plain
commas as quote-mark stand-ins -- see gold_examples.py's own comments -- and
so don't exercise real quote-pair tokens), a round-trip check against every
gold example's own passage for tokengraph_to_text() (confirming the
existing (quote-free) fixtures reconstruct exactly, punctuation and
enclitics included), and a separate section of tokengraph_to_html() tests
covering verbal-unit span-wrapping, HTML escaping, and cross-checking that
its colors match tokengraph_to_mermaid()'s.
"""
 
import html
import re
 
import pytest
 
from arsgrammatica.mermaid import tokengraph_to_mermaid
from arsgrammatica.models import IMPLIED_TOKENTYPES, TokenAnalysis
from arsgrammatica.rendering import (
    tokengraph_to_text,
    tokengraph_to_html,
    tokengraph_to_depth_html,
)
from arsgrammatica.verbal_units import _VERBAL_UNIT_PALETTE, max_subordination_depth
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def _tok(id, token, tokentype, **kw):
    return TokenAnalysis(id=id, token=token, tokentype=tokentype, **kw)
 
 
def test_plain_lexical_tokens_get_single_spaces():
    tg = [_tok("t0", "arma", "lexical"), _tok("t1", "virum", "lexical")]
    assert tokengraph_to_text(tg) == "arma virum"
 
 
def test_enclitic_attaches_directly_no_space():
    tg = [
        _tok("t0", "arma", "lexical"),
        _tok("t1", "virum", "lexical"),
        _tok("t2", "que", "enclitic"),
        _tok("t3", "cano", "lexical"),
        _tok("t4", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "arma virumque cano."
 
 
def test_period_comma_semicolon_hyphen_are_left_joining():
    tg = [
        _tok("t0", "foo", "lexical"),
        _tok("t1", ",", "punctuation"),
        _tok("t2", "bar", "lexical"),
        _tok("t3", ";", "punctuation"),
        _tok("t4", "baz", "lexical"),
        _tok("t5", "-", "punctuation"),
        _tok("t6", "qux", "lexical"),
        _tok("t7", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "foo, bar; baz- qux."
 
 
def test_opening_bracket_is_right_joining_closing_is_left_joining():
    tg = [
        _tok("t0", "bar", "lexical"),
        _tok("t1", "(", "punctuation"),
        _tok("t2", "foo", "lexical"),
        _tok("t3", ")", "punctuation"),
        _tok("t4", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "bar (foo)."
 
 
def test_square_and_curly_brackets_too():
    tg = [
        _tok("t0", "bar", "lexical"),
        _tok("t1", "[", "punctuation"),
        _tok("t2", "foo", "lexical"),
        _tok("t3", "]", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "bar [foo]"
 
    tg2 = [
        _tok("t0", "bar", "lexical"),
        _tok("t1", "{", "punctuation"),
        _tok("t2", "foo", "lexical"),
        _tok("t3", "}", "punctuation"),
    ]
    assert tokengraph_to_text(tg2) == "bar {foo}"
 
 
def test_double_quote_pair_first_right_second_left():
    tg = [
        _tok("t0", '"', "punctuation"),
        _tok("t1", "Tuum", "lexical"),
        _tok("t2", "est", "lexical"),
        _tok("t3", '"', "punctuation"),
        _tok("t4", "inquit", "lexical"),
        _tok("t5", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == '"Tuum est" inquit.'
 
 
def test_two_separate_double_quote_spans_alternate_correctly():
    """A third and fourth occurrence of the same quote character must
    resume the open/close alternation (open again, then close), not stay
    "closed" forever."""
    tg = [
        _tok("t0", '"', "punctuation"),
        _tok("t1", "a", "lexical"),
        _tok("t2", '"', "punctuation"),
        _tok("t3", "b", "lexical"),
        _tok("t4", '"', "punctuation"),
        _tok("t5", "c", "lexical"),
        _tok("t6", '"', "punctuation"),
    ]
    assert tokengraph_to_text(tg) == '"a" b "c"'
 
 
def test_single_and_double_quotes_are_tracked_independently():
    tg = [
        _tok("t0", '"', "punctuation"),
        _tok("t1", "a", "lexical"),
        _tok("t2", "'", "punctuation"),
        _tok("t3", "b", "lexical"),
        _tok("t4", "'", "punctuation"),
        _tok("t5", "c", "lexical"),
        _tok("t6", '"', "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "\"a 'b' c\""
 
 
def test_praenomen_and_numeral_get_normal_spacing():
    tg = [
        _tok("t0", "M.", "praenomen"),
        _tok("t1", "Tullius", "lexical"),
        _tok("t2", "XXV", "numeral"),
        _tok("t3", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "M. Tullius XXV."


def test_abbreviation_gets_normal_spacing():
    """"abbreviation" (distinct from "praenomen" -- see syntax_model.md's
    tokenization section, e.g. "f." for filius, "cos." for consul) gets the
    same normal spacing as any other non-enclitic, non-punctuation token."""
    tg = [
        _tok("t0", "M.", "praenomen"),
        _tok("t1", "Agrippa", "lexical"),
        _tok("t2", "L.", "praenomen"),
        _tok("t3", "f.", "abbreviation"),
        _tok("t4", "cos.", "abbreviation"),
        _tok("t5", "fecit", "lexical"),
        _tok("t6", ".", "punctuation"),
    ]
    assert tokengraph_to_text(tg) == "M. Agrippa L. f. cos. fecit."
 
 
def test_empty_tokengraph_returns_empty_string():
    assert tokengraph_to_text([]) == ""
 
 
def test_single_token():
    assert tokengraph_to_text([_tok("t0", "cano", "lexical")]) == "cano"
 
 
def test_right_joining_token_first_gets_no_leading_space():
    tg = [_tok("t0", "(", "punctuation"), _tok("t1", "foo", "lexical")]
    assert tokengraph_to_text(tg) == "(foo"
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_round_trips_gold_example_passages(example):
    """Every existing gold fixture's tokengraph -- none of which currently
    contain real quote-pair tokens (see gold_examples.py's own notes on
    substituting commas) -- should reconstruct its exact original passage
    string via ordinary punctuation/enclitic spacing rules alone."""
    tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
    assert tokengraph_to_text(tokengraph) == example.passage
 
 
# ---------------------------------------------------------------------------
# tokengraph_to_html()
# ---------------------------------------------------------------------------
 
_SPAN_RE = re.compile(
    r'<span style="background-color: (#[0-9a-fA-F]{6}); color: (#[0-9a-fA-F]{6});">'
    r"(.*?)</span>"
)
 
 
def test_no_verbal_units_leaves_plain_spacing_and_no_spans():
    """With no verbalunitid/relation fields set at all, every token is
    unassigned -- so tokengraph_to_html() should produce exactly the same
    string as tokengraph_to_text() (escaped, but nothing here needs
    escaping), with no <span> tags at all."""
    tg = [_tok("t0", "arma", "lexical"), _tok("t1", "virum", "lexical")]
    assert tokengraph_to_html(tg) == "arma virum"
    assert "<span" not in tokengraph_to_html(tg)
 
 
def test_single_verbal_unit_wraps_its_lexical_tokens():
    tg = [
        _tok("t0", "arma", "lexical", relatedtoken1="t2", relationship1="direct object"),
        _tok("t1", "virum", "lexical", relatedtoken1="t2", relationship1="direct object"),
        _tok("t2", "cano", "lexical", verbalunitid="t2"),
        _tok("t3", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == f"{span('arma')} {span('virum')} {span('cano')}."
 
 
def test_multiple_verbal_units_get_distinct_first_appearance_colors():
    """Two independent verbal units, anchored by t1 ("videt") and t4
    ("venit"), each colored per _VERBAL_UNIT_PALETTE's order of first
    non-punctuation appearance -- t0 (unit "t1") appears before t3 (unit
    "t4"), so "t1" gets palette slot 0 and "t4" gets slot 1, matching
    tokengraph_to_mermaid()'s own ordering rule exactly."""
    tg = [
        _tok("t0", "puer", "lexical", relatedtoken1="t1", relationship1="subject"),
        _tok("t1", "videt", "lexical", verbalunitid="t1"),
        _tok("t2", ",", "punctuation"),
        _tok("t3", "puella", "lexical", relatedtoken1="t4", relationship1="subject"),
        _tok("t4", "venit", "lexical", verbalunitid="t4"),
        _tok("t5", ".", "punctuation"),
    ]
    fill0, _s0, text0 = _VERBAL_UNIT_PALETTE[0]
    fill1, _s1, text1 = _VERBAL_UNIT_PALETTE[1]
    span0 = lambda word: f'<span style="background-color: {fill0}; color: {text0};">{word}</span>'
    span1 = lambda word: f'<span style="background-color: {fill1}; color: {text1};">{word}</span>'
    expected = (
        f"{span0('puer')} {span0('videt')}, {span1('puella')} {span1('venit')}."
    )
    assert tokengraph_to_html(tg) == expected
 
 
def test_only_lexical_praenomen_and_numeral_tokens_get_wrapped_even_when_others_are_assigned():
    """Punctuation, enclitics, and abbreviations can all be assigned a
    verbal unit by assign_verbal_units() (it assigns every token id), but
    none of these particular ones is a coordinating conjunction (their own
    relationship1 is "subject" or "adverbial") -- so only tokentype ==
    "lexical", "praenomen", or "numeral" gets a <span> here. This praenomen
    token ("M.") and this numeral token ("V") are each given
    relationship1="subject"/"adverbial" -- NOT praenomen's usual
    "praenomen" relation -- specifically to isolate that
    tokengraph_to_html() wraps them because of their tokentype, not because
    of which relation they happen to carry (see
    test_enclitic_coordinating_conjunction_gets_wrapped_too for the
    corresponding relationship-keyed carve-out, and
    test_praenomen_token_gets_wrapped_too/test_numeral_token_gets_wrapped_too
    below for the normal case)."""
    tg = [
        _tok("t0", "M.", "praenomen", relatedtoken1="t2", relationship1="subject"),
        _tok("t1", "que", "enclitic", relatedtoken1="t2", relationship1="subject"),
        _tok("t2", "venit", "lexical", verbalunitid="t2"),
        _tok("t3", "V", "numeral", relatedtoken1="t2", relationship1="adverbial"),
        _tok("t4", "f.", "abbreviation", relatedtoken1="t2", relationship1="adverbial"),
        _tok("t5", ".", "punctuation", relatedtoken1="t2", relationship1="adverbial"),
    ]
    html_out = tokengraph_to_html(tg)
    matches = _SPAN_RE.findall(html_out)
    assert len(matches) == 3
    assert matches[0][2] == "M."
    assert matches[1][2] == "venit"
    assert matches[2][2] == "V"
    # same verbal unit -> same fill color, for all three wrapped tokens
    assert matches[0][0] == matches[1][0] == matches[2][0]


def test_praenomen_token_gets_wrapped_too():
    """The fix this test guards: "M." in "M. Agrippa..." is tokentype
    "praenomen", not "lexical", but syntax_model.md's "Praenomina" section
    gives it a real relation (relatedtoken1 -> the lexical name it
    precedes, relationship1 = "praenomen") that assign_verbal_units()
    resolves like any other -- so it must get the SAME colored span as the
    rest of its verbal unit, not be left plain like other non-lexical,
    non-praenomen, non-numeral tokentypes (abbreviations, punctuation)."""
    tg = [
        _tok("t0", "M.", "praenomen", relatedtoken1="t1", relationship1="praenomen"),
        _tok("t1", "Agrippa", "lexical", relatedtoken1="t2", relationship1="subject"),
        _tok("t2", "venit", "lexical", verbalunitid="t2"),
        _tok("t3", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == f"{span('M.')} {span('Agrippa')} {span('venit')}."


def test_numeral_token_gets_wrapped_too():
    """The fix this test guards (the reported bug): "XII" in "Fratres
    Joseph XII venerunt." is tokentype "numeral", not "lexical", but
    syntax_model.md's numeral-vs-lexical clarification makes clear a
    numeral is otherwise an ordinary participant in the clause, able to
    carry a real relation (here relatedtoken1 -> "Fratres", relationship1
    = "adjectival") that assign_verbal_units() resolves like any other --
    so it must get the SAME colored span as the rest of its verbal unit,
    matching what tokengraph_to_mermaid() already did before this fix (see
    also test_html_colors_match_mermaid_colors_for_every_gold_example)."""
    tg = [
        _tok("t0", "Fratres", "lexical", relatedtoken1="t3", relationship1="subject"),
        _tok("t1", "Joseph", "lexical", relatedtoken1="t0", relationship1="genitive"),
        _tok("t2", "XII", "numeral", relatedtoken1="t0", relationship1="adjectival"),
        _tok("t3", "venerunt", "lexical", verbalunitid="t3"),
        _tok("t4", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == (
        f"{span('Fratres')} {span('Joseph')} {span('XII')} {span('venerunt')}."
    )


def test_enclitic_coordinating_conjunction_gets_wrapped_too():
    """The fix this test guards: an enclitic coordinating conjunction (e.g.
    "-que" in "arma virumque cano") is not tokentype "lexical", but
    assign_verbal_units() still resolves it to one of the units it
    coordinates -- so it should get the SAME colored span as that unit's
    other tokens, not be left plain like other non-lexical tokentypes."""
    tg = [
        _tok("t0", "arma", "lexical", relatedtoken1="t3", relationship1="direct object"),
        _tok("t1", "virum", "lexical", relatedtoken1="t3", relationship1="direct object"),
        _tok(
            "t2", "que", "enclitic",
            relatedtoken1="t0", relationship1="coordinating conjunction",
            relatedtoken2="t1", relationship2="coordinating conjunction",
        ),
        _tok("t3", "cano", "lexical", verbalunitid="t3"),
        _tok("t4", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == f"{span('arma')} {span('virum')}{span('que')} {span('cano')}."


def test_series_coordinating_conjunctions_all_get_wrapped():
    """A repeated ("et...et...et") series connector still gets the SAME
    treatment as the ordinary pairwise case: _tokens_to_html()'s wrapping
    check only looks at relationship1/relationship2 == "coordinating
    conjunction" (see rendering.py), which every connector in a series
    still sets, regardless of relatedtoken2 chaining between neighboring
    connectors instead of pairing two conjuncts. All three "et"s here
    should get the same colored span as the ablatives they introduce and
    the verb they all ultimately resolve to."""
    tg = [
        _tok("t0", "et", "lexical",
             relatedtoken1="t1", relationship1="coordinating conjunction",
             relatedtoken2="t2", relationship2="coordinating conjunction"),
        _tok("t1", "assiduitate", "lexical", relatedtoken1="t6", relationship1="ablative"),
        _tok("t2", "et", "lexical",
             relatedtoken1="t3", relationship1="coordinating conjunction",
             relatedtoken2="t0", relationship2="coordinating conjunction"),
        _tok("t3", "varietate", "lexical", relatedtoken1="t6", relationship1="ablative"),
        _tok("t4", "et", "lexical",
             relatedtoken1="t5", relationship1="coordinating conjunction",
             relatedtoken2="t2", relationship2="coordinating conjunction"),
        _tok("t5", "magnificentia", "lexical", relatedtoken1="t6", relationship1="ablative"),
        _tok("t6", "antecessit", "lexical", verbalunitid="t6"),
        _tok("t7", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == (
        f"{span('et')} {span('assiduitate')} {span('et')} {span('varietate')} "
        f"{span('et')} {span('magnificentia')} {span('antecessit')}."
    )


def test_implied_tokens_are_omitted_from_html_entirely():
    """An implied/elided token (models.py's IMPLIED_TOKENTYPES) has no
    surface text of its own (tok.token is always None) -- tokengraph_to_html()
    omits it entirely, same as tokengraph_to_text() does, rather than
    inventing placeholder text for it. tokengraph_to_mermaid() is the one
    place these ARE shown (see test_mermaid_coloring.py) -- inserting
    placeholder text into reconstructed HTML prose would misrepresent what
    the passage actually says."""
    tg = [
        _tok("t0", "Omnia", "lexical", relatedtoken1="t0_implied", relationship1="subject"),
        _tok(
            "t0_implied", None, "implied sum",
            verbalunitid="t0_implied", relatedtoken1="root", relationship1="unit verb",
        ),
        _tok("t1", "rara", "lexical", relatedtoken1="t0_implied", relationship1="predicate"),
        _tok("t2", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    html_out = tokengraph_to_html(tg)
    assert html_out == f"{span('Omnia')} {span('rara')}."
    assert "implied" not in html_out


def test_lexical_token_with_no_verbal_unit_is_unwrapped():
    tg = [
        _tok("t0", "cano", "lexical", verbalunitid="t0"),
        _tok("t1", "heus", "lexical"),  # unrelated interjection, no relation at all
    ]
    html_out = tokengraph_to_html(tg)
    matches = _SPAN_RE.findall(html_out)
    assert len(matches) == 1
    assert matches[0][2] == "cano"
    assert "heus" in html_out
    assert "<span" not in html_out.split("heus")[0].split("</span>")[-1]
 
 
def test_html_special_characters_are_escaped():
    tg = [
        _tok("t0", "Tu", "lexical", verbalunitid="t0"),
        _tok("t1", "<3", "lexical"),
        _tok("t2", "&", "punctuation"),
    ]
    html_out = tokengraph_to_html(tg)
    assert "<3" not in html_out
    assert "&lt;3" in html_out
    assert "&amp;" in html_out
 
 
def test_quote_pair_tokens_still_join_correctly_around_spans():
    tg = [
        _tok("t0", '"', "punctuation"),
        _tok("t1", "Tuum", "lexical", verbalunitid="t1"),
        _tok("t2", "est", "lexical", relatedtoken1="t1", relationship1="predicate"),
        _tok("t3", '"', "punctuation"),
        _tok("t4", "inquit", "lexical"),
        _tok("t5", ".", "punctuation"),
    ]
    fill, _stroke, text_color = _VERBAL_UNIT_PALETTE[0]
    span = lambda word: (
        f'<span style="background-color: {fill}; color: {text_color};">{word}</span>'
    )
    assert tokengraph_to_html(tg) == f'&quot;{span("Tuum")} {span("est")}&quot; inquit.'
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_html_colors_match_mermaid_colors_for_every_gold_example(example):
    """The whole point of this function: whatever fill color a token's
    verbal unit gets in the Mermaid diagram, the same token's <span> here
    must use that exact same fill (and the matching text color) -- checked
    against tokengraph_to_mermaid()'s own classDef/class output rather than
    against verbal_units.py internals, so this test would catch a real
    behavioral mismatch between the two renderers, not just a shared bug in
    the code both of them call. Covers every wrapped token, not just
    lexical ones -- a coordinating conjunction (e.g. an enclitic "-que"),
    a praenomen (e.g. "Sex."), or a numeral (e.g. "XII") gets wrapped here
    too (see tokengraph_to_html()'s own docstring), and the Mermaid diagram
    colors it via the same assign_verbal_units() assignment, so both should
    agree there as well. An implied token is
    excluded from this comparison entirely: tokengraph_to_html() omits it
    (see test_implied_tokens_are_omitted_from_html_entirely), while the
    Mermaid diagram shows it in its own dedicated `implied` class -- the
    two renderers deliberately disagree here by design, so this token
    naturally never satisfies the `tok.tokentype == "lexical" or ...`
    filter below and is skipped on both sides."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph

    diagram, _warnings = tokengraph_to_mermaid(tokengraph)
    fill_of_class = dict(
        re.findall(r"classDef (vu\d+) fill:(#[0-9a-fA-F]{6}),", diagram)
    )
    class_of_id = {}
    for ids, class_name in re.findall(r"class ([\w,]+) (vu\d+);", diagram):
        for tid in ids.split(","):
            class_of_id[tid] = class_name

    expected_fills = [
        fill_of_class[class_of_id[tok.id]]
        for tok in tokengraph
        if (
            tok.tokentype in ("lexical", "praenomen", "numeral")
            or tok.relationship1 == "coordinating conjunction"
            or tok.relationship2 == "coordinating conjunction"
        )
        and tok.id in class_of_id
    ]

    html_out = tokengraph_to_html(tokengraph)
    actual_fills = [m[0] for m in _SPAN_RE.findall(html_out)]

    assert actual_fills == expected_fills, example.slug



# ---------------------------------------------------------------------------
# tokengraph_to_depth_html()
# ---------------------------------------------------------------------------

_DIV_RE = re.compile(
    r'<div style="margin-left: ([0-9.]+)em; margin-bottom: 0\.35em;">(.*?)</div>'
)


def _tokengraph(slug):
    example = next(e for e in GOLD_EXAMPLES if e.slug == slug)
    return [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]


def test_depth_html_taurum_example_produces_three_blocks_at_expected_depths():
    """The user's own worked example: taurum (level 0), cum quo Pasiphae
    concubuit (level 1), ex Creta insula Mycenis uiuum adduxit (level 0) --
    exactly three blocks, indented 0/1/0 levels."""
    tokengraph = _tokengraph("depth_taurum_cum_quo_concubuit")
    html_out, warnings = tokengraph_to_depth_html(tokengraph)
    assert warnings == []

    blocks = _DIV_RE.findall(html_out)
    assert len(blocks) == 3

    margins = [float(m) for m, _content in blocks]
    assert margins == [0.0, 2.0, 0.0]

    assert "Taurum" in blocks[0][1]
    assert "adduxit" not in blocks[0][1]

    for word in ("cum", "quo", "Pasiphae", "concubuit"):
        assert word in blocks[1][1], word
    assert "Taurum" not in blocks[1][1]
    assert "adduxit" not in blocks[1][1]

    for word in ("ex", "Creta", "insula", "Mycenis", "uiuum", "adduxit"):
        assert word in blocks[2][1], word
    assert "concubuit" not in blocks[2][1]


def test_depth_html_enclitic_never_starts_a_new_block():
    """"-que" in Hermionenque resolves (per assign_verbal_units()) to
    noluit's verbal unit -- a DIFFERENT unit than Hermionen, which resolves
    to adduxit's -- since que's own relation joins the two verbs, not the
    noun it's glued to. Splitting the orthographic word "Hermionenque"
    across two <div>s would be wrong, so the enclitic must stay in
    whichever block "Hermionen" opened -- even though, as a coordinating
    conjunction, it now gets its OWN color span there (noluit's color, not
    Hermionen/adduxit's), immediately adjacent with no space, per
    tokengraph_to_html()'s coordinating-conjunction carve-out."""
    tokengraph = _tokengraph("coordinating_conjunction_verbs_ille_hermionenque")
    html_out, warnings = tokengraph_to_depth_html(tokengraph)
    assert warnings == []

    blocks = _DIV_RE.findall(html_out)
    assert len(blocks) == 2

    hermionen_block = next(content for _m, content in blocks if "Hermionen" in content)
    assert "que" in hermionen_block
    # Two adjacent, differently-colored spans -- Hermionen's (adduxit's
    # unit) immediately followed, with no space and no other markup
    # between them, by que's own (noluit's unit).
    assert "Hermionen</span><span" in hermionen_block
    matches = _SPAN_RE.findall(hermionen_block)
    words = [m[2] for m in matches]
    fills = [m[0] for m in matches]
    hermionen_index = words.index("Hermionen")
    assert words[hermionen_index + 1] == "que"
    assert fills[hermionen_index] != fills[hermionen_index + 1]


def test_depth_html_depth_cap_drops_deeper_blocks_entirely():
    """Same fixture as test_depth_html_taurum_example_produces_three_blocks_
    at_expected_depths (three blocks at depths 0/1/0): passing depth=0
    must drop the middle (depth-1) block ENTIRELY -- not render it empty
    or grayed out -- leaving only the two depth-0 blocks; passing depth=1
    (>= the passage's own max) must show all three, identical to leaving
    `depth` unset."""
    tokengraph = _tokengraph("depth_taurum_cum_quo_concubuit")

    html_out, warnings = tokengraph_to_depth_html(tokengraph, depth=0)
    assert warnings == []  # depth filtering must not itself produce warnings
    blocks = _DIV_RE.findall(html_out)
    assert len(blocks) == 2
    assert "Taurum" in blocks[0][1]
    assert "adduxit" in blocks[1][1]
    assert "concubuit" not in html_out  # the depth-1 block is gone, not just emptied

    html_out_1, _warnings = tokengraph_to_depth_html(tokengraph, depth=1)
    html_out_none, _warnings = tokengraph_to_depth_html(tokengraph, depth=None)
    assert html_out_1 == html_out_none
    assert len(_DIV_RE.findall(html_out_1)) == 3


def test_depth_html_negative_depth_raises():
    tokengraph = _tokengraph("depth_taurum_cum_quo_concubuit")
    with pytest.raises(ValueError, match="depth must be >= 0"):
        tokengraph_to_depth_html(tokengraph, depth=-1)


def test_max_subordination_depth_matches_the_deepest_resolved_anchor():
    """max_subordination_depth() is just the max of compute_subordination_
    depths()'s own resolved values -- checked against two fixtures whose
    depths are already pinned down elsewhere (test_verbal_units.py): one
    that bottoms out at depth 1 (taurum), and one that reaches depth 2
    (the cum-sciret-peccavisse-doluit nesting case)."""
    tokengraph = _tokengraph("depth_taurum_cum_quo_concubuit")
    assert max_subordination_depth(tokengraph) == 1

    tokengraph = _tokengraph("depth_two_cum_sciret_peccavisse_doluit")
    assert max_subordination_depth(tokengraph) == 2


def test_max_subordination_depth_none_when_no_verbal_expressions():
    assert max_subordination_depth([]) is None
    tg = [_tok("t0", "heus", "lexical")]  # no verb at all -- no anchors
    assert max_subordination_depth(tg) is None


def test_depth_html_custom_indent_scales_margins():
    tokengraph = _tokengraph("unit_verb_hercules_cum")
    html_out, _warnings = tokengraph_to_depth_html(tokengraph, indent_em=1.5)
    blocks = _DIV_RE.findall(html_out)
    margins = sorted({float(m) for m, _content in blocks})
    assert margins == [0.0, 1.5]


def test_depth_html_colors_match_tokengraph_to_html_for_the_same_passage():
    """Splitting into per-block <div>s must not change which color a given
    lexical token gets -- the whole point of sharing one precomputed
    assignment/colors mapping (via _tokens_to_html()) between this function
    and tokengraph_to_html()."""
    tokengraph = _tokengraph("aside_equidem_pace_dixerim")
    whole_html = tokengraph_to_html(tokengraph)
    depth_html, _warnings = tokengraph_to_depth_html(tokengraph)

    whole_fills = [m[0] for m in _SPAN_RE.findall(whole_html)]
    depth_fills = [m[0] for m in _SPAN_RE.findall(depth_html)]
    assert depth_fills == whole_fills


def test_depth_html_leading_unassigned_token_opens_a_placeholder_depth_zero_block():
    tg = [
        _tok("t0", "unrelated", "lexical"),
        _tok("t1", "puer", "lexical", relatedtoken1="t2", relationship1="subject"),
        _tok("t2", "venit", "lexical", verbalunitid="t2", relatedtoken1="root", relationship1="unit verb"),
    ]
    html_out, warnings = tokengraph_to_depth_html(tg)
    assert warnings == []
    blocks = _DIV_RE.findall(html_out)
    assert len(blocks) == 2
    assert blocks[0][0] == "0.0"
    assert "unrelated" in blocks[0][1]
    assert "puer" in blocks[1][1] and "venit" in blocks[1][1]


def test_depth_html_trailing_unassigned_token_folds_into_open_block():
    tg = [
        _tok("t0", "puer", "lexical", relatedtoken1="t1", relationship1="subject"),
        _tok("t1", "venit", "lexical", verbalunitid="t1", relatedtoken1="root", relationship1="unit verb"),
        _tok("t2", "heus", "lexical"),
    ]
    html_out, warnings = tokengraph_to_depth_html(tg)
    assert warnings == []
    blocks = _DIV_RE.findall(html_out)
    assert len(blocks) == 1
    assert "heus" in blocks[0][1]


def test_depth_html_empty_tokengraph_returns_empty_string():
    html_out, warnings = tokengraph_to_depth_html([])
    assert html_out == ""
    assert warnings == []


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_depth_html_never_warns_and_covers_every_token_for_every_gold_example(example):
    """Structural check across the whole fixture set, mirroring
    test_html_colors_match_mermaid_colors_for_every_gold_example above:
    every gold fixture should render with no warnings, and every token's
    surface text (once HTML-escaped) should appear somewhere in the
    output -- confirming no token silently gets dropped while blocks are
    assembled."""
    tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
    html_out, warnings = tokengraph_to_depth_html(tokengraph)
    assert warnings == [], f"{example.slug}: {warnings}"
    for tok in tokengraph:
        if tok.tokentype in IMPLIED_TOKENTYPES:
            # An implied/elided token (models.py's TokenAnalysis,
            # IMPLIED_TOKENTYPES) has no surface text at all --
            # tokengraph_to_depth_html() deliberately renders nothing for
            # it (see rendering.py's skip logic), so there is no escaped
            # text to look for here.
            continue
        assert html.escape(tok.token) in html_out, f"{example.slug}: missing {tok.id}"
