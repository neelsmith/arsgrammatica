"""
Tests for validate() itself -- proving it actually catches bad output, as
opposed to test_gold_examples.py, which checks that well-formed gold
answers pass cleanly. Reuses a gold example as a convenient base to mutate
rather than defining its own fixture.
"""
 
import dspy
from dspy.utils.dummies import DummyLM
 
from arsgrammatica import analyze, validate, tokenize
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
    tokens = tokenize(base.passage)
    result = analyze(passage=base.passage, tokens=tokens)
 
    problems = validate(tokens, result)
    assert problems, "expected validate() to catch the bogus id 't99', but it found nothing"
