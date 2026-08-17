"""
Tests for validate() itself -- proving it actually catches bad output, as
opposed to test_gold_examples.py, which checks that well-formed gold
answers pass cleanly. Reuses a gold example as a convenient base to mutate
rather than defining its own fixture.
"""
 
import dspy
from dspy.utils.dummies import DummyLM
 
from arsgrammatica import analyze, validate
from conftest import tokens_from_canned_answer
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)
 
 
def test_bad_answer_is_caught():
    """A response that refers to a nonexistent token id should be flagged
    by validate(), not silently accepted."""
    base = _example("unit_verb_hercules_cum")
 
    # Copy before mutating -- GOLD_EXAMPLES is shared across the whole
    # suite, so this must not touch the original dict or list in place.
    bad_answer = dict(base.canned_answer)
    bad_answer["tokengraph"] = list(base.canned_answer["tokengraph"])
    bad_answer["tokengraph"][0] = {
        **base.canned_answer["tokengraph"][0],
        "relatedtoken1": "t99",  # does not exist
    }
 
    dspy.configure(lm=DummyLM([bad_answer]))
    tokens = tokens_from_canned_answer(base.canned_answer)
    result = analyze(passage=base.passage, tokens=tokens)
 
    problems = validate(tokens, result)
    assert problems, "expected validate() to catch the bogus id 't99', but it found nothing"
 

# ---------------------------------------------------------------------------
# Implied/elided tokens (tokentype='implied sum'/'continued discourse'; see
# models.py's TokenAnalysis and IMPLIED_TOKENTYPES)
# ---------------------------------------------------------------------------
#
# These run validate() directly against hand-built tokens/result objects
# (rather than through analyze()+DummyLM like test_bad_answer_is_caught
# above) since the point here is validate()'s own acceptance/rejection
# logic for the implied-token fields specifically, not the whole pipeline --
# the gold-example-backed tests (test_gold_examples.py's
# test_gold_example_validates) already cover the well-formed case for all
# four implied_* fixtures end to end.

from arsgrammatica.models import Token, TokenAnalysis, VerbalExpression


def _result(tokengraph, verbalunits=()):
    return dspy.Prediction(tokengraph=list(tokengraph), verbalunits=list(verbalunits))


def _well_formed_implied_case():
    """"Rara [sunt]." -- a minimal well-formed implied-token case: t0 is
    the real token, t0_implied is the new implied one anchoring it."""
    tokens = [Token(id="t0", text="Rara")]
    tokengraph = [
        TokenAnalysis(id="t0", token="Rara", tokentype="lexical",
                      relatedtoken1="t0_implied", relationship1="predicate"),
        TokenAnalysis(id="t0_implied", token=None, tokentype="implied sum",
                      verbalunitid="t0_implied", relatedtoken1="root", relationship1="unit verb"),
    ]
    verbalunits = [VerbalExpression(id="t0_implied", syntactic_type="independent", semantic_type="linking verb")]
    return tokens, tokengraph, verbalunits


def test_well_formed_implied_token_is_accepted():
    """The baseline well-formed case must NOT be flagged -- a new id, not
    in `tokens`, with token=None, is exactly what an implied entry is
    supposed to look like."""
    tokens, tokengraph, verbalunits = _well_formed_implied_case()
    problems = validate(tokens, _result(tokengraph, verbalunits))
    assert not problems, problems


def test_implied_token_reusing_a_real_id_is_caught():
    """An implied entry (tokentype='implied sum' or 'continued discourse')
    must use a NEW id -- reusing one already in `tokens` (as if it were
    describing that real token) is malformed, not a legitimate implied
    token."""
    tokens, tokengraph, verbalunits = _well_formed_implied_case()
    tokengraph[1] = TokenAnalysis(
        id="t0", token=None, tokentype="implied sum",  # reuses t0's own id
        verbalunitid="t0", relatedtoken1="root", relationship1="unit verb",
    )
    tokengraph[0].relatedtoken1 = "t0"
    verbalunits[0].id = "t0"
    problems = validate(tokens, _result(tokengraph, verbalunits))
    assert problems, "expected validate() to catch an implied entry reusing a real token's id"
    assert any("reuses an id" in p for p in problems), problems


def test_implied_token_with_real_text_is_caught():
    """tokentype='implied sum'/'continued discourse' with a non-None
    `token` value contradicts itself -- an implied token is defined by
    having NO surface text."""
    tokens, tokengraph, verbalunits = _well_formed_implied_case()
    tokengraph[1].token = "sunt"  # should have stayed None
    problems = validate(tokens, _result(tokengraph, verbalunits))
    assert problems, "expected validate() to catch an implied entry with real token text"
    assert any("non-None token value" in p for p in problems), problems


def test_non_implied_token_with_none_text_is_caught():
    """The inverse case: a token that ISN'T marked with one of the implied
    tokentypes must not have token=None -- only 'implied sum'/'continued
    discourse' may omit real surface text."""
    tokens, tokengraph, verbalunits = _well_formed_implied_case()
    tokengraph[0].token = None  # t0 is tokentype='lexical', not implied
    problems = validate(tokens, _result(tokengraph, verbalunits))
    assert problems, "expected validate() to catch a non-implied token with token=None"
    assert any("may omit surface text" in p for p in problems), problems
