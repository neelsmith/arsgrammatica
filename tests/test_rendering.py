"""
Tests for arsgrammatica/rendering.py's tokengraph_to_text().
 
Split into two parts: targeted unit tests for each join rule (built from
small hand-built TokenAnalysis lists, since the existing gold fixtures use
plain commas as quote-mark stand-ins -- see gold_examples.py's own
comments -- and so don't exercise real quote-pair tokens), and a
round-trip check against every gold example's own passage, confirming the
existing (quote-free) fixtures reconstruct exactly, punctuation and
enclitics included.
"""
 
import pytest
 
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.rendering import tokengraph_to_text
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
 