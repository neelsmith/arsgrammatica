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
 
import re
 
import pytest
 
from arsgrammatica.mermaid import tokengraph_to_mermaid
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.rendering import tokengraph_to_text, tokengraph_to_html
from arsgrammatica.verbal_units import _VERBAL_UNIT_PALETTE
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
 
 
def test_only_lexical_tokens_get_wrapped_even_when_others_are_assigned():
    """Punctuation, enclitics, numerals, and praenomens can all be assigned
    a verbal unit by assign_verbal_units() (it assigns every token id), but
    only tokentype == "lexical" should ever get a <span> here."""
    tg = [
        _tok("t0", "M.", "praenomen", relatedtoken1="t2", relationship1="subject"),
        _tok("t1", "que", "enclitic", relatedtoken1="t2", relationship1="subject"),
        _tok("t2", "venit", "lexical", verbalunitid="t2"),
        _tok("t3", "V", "numeral", relatedtoken1="t2", relationship1="adverbial"),
        _tok("t4", ".", "punctuation", relatedtoken1="t2", relationship1="adverbial"),
    ]
    html_out = tokengraph_to_html(tg)
    matches = _SPAN_RE.findall(html_out)
    assert len(matches) == 1
    assert matches[0][2] == "venit"
 
 
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
    """The whole point of this function: whatever fill color a lexical
    token's verbal unit gets in the Mermaid diagram, the same token's <span>
    here must use that exact same fill (and the matching text color) --
    checked against tokengraph_to_mermaid()'s own classDef/class output
    rather than against verbal_units.py internals, so this test would catch
    a real behavioral mismatch between the two renderers, not just a shared
    bug in the code both of them call."""
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
        if tok.tokentype == "lexical" and tok.id in class_of_id
    ]
 
    html_out = tokengraph_to_html(tokengraph)
    actual_fills = [m[0] for m in _SPAN_RE.findall(html_out)]
 
    assert actual_fills == expected_fills, example.slug