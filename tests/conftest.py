"""
Shared test helpers.
 
Kept deliberately small: every DummyLM-backed test reconfigures
dspy.settings.lm before it runs, so there's no cross-test state to tear
down here (yet). If that changes, this is the place for a pytest fixture
that resets dspy.settings between tests.
"""
 
import dspy
from dspy.utils.dummies import DummyLM
 
from arsgrammatica import analyze, tokenize
 
 
def run_gold_example(example):
    """Run a GoldExample's passage through analyze(), with DummyLM standing
    in for the real LM and returning that example's canned_answer.
 
    Returns (tokens, result) -- the same pair analyze_passage() returns.
    """
    dspy.configure(lm=DummyLM([example.canned_answer]))
    tokens = tokenize(example.passage)
    result = analyze(passage=example.passage, tokens=tokens)
    return tokens, result