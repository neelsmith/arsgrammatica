"""
Tests for lm_cost.py's summarize_lm_cost()/format_lm_cost() -- see that
module's own docstring for why it exists: every marimo notebook that
displayed "cost" had converged on a pattern (`lm.history[-1].get('cost')`)
that crashed on an empty history and only ever looked at the single last
call, understating a multi-sentence analysis's real cost.

No dspy involved here at all -- these functions only care that `history`
is a list of dict-like entries with a `cost` key, exactly the shape
dspy.LM's own `.history` has (see lm_cost.py's module docstring), so gold
fixtures are just hand-built dicts rather than anything DummyLM-driven.
"""

from arsgrammatica import LMCostSummary, format_lm_cost, summarize_lm_cost


def test_empty_history_has_no_cost_and_no_calls():
    summary = summarize_lm_cost([])
    assert summary == LMCostSummary(total_cost=None, priced_calls=0, uncosted_calls=0)
    assert summary.total_calls == 0
    assert format_lm_cost(summary) == "no LM calls yet"


def test_all_cache_hits_have_no_cost_but_are_counted():
    history = [{"cost": None}, {"cost": None}]
    summary = summarize_lm_cost(history)
    assert summary.total_cost is None
    assert summary.priced_calls == 0
    assert summary.uncosted_calls == 2
    assert summary.total_calls == 2
    message = format_lm_cost(summary)
    assert "2 calls" in message
    assert "cache" in message
    assert "None" not in message  # never surface a bare, unexplained "None"


def test_single_cache_hit_uses_singular_wording():
    summary = summarize_lm_cost([{"cost": None}])
    message = format_lm_cost(summary)
    assert "1 call," in message
    assert "1 calls" not in message


def test_every_call_priced_sums_correctly():
    history = [{"cost": 0.01}, {"cost": 0.0234}, {"cost": 0.005}]
    summary = summarize_lm_cost(history)
    assert summary.priced_calls == 3
    assert summary.uncosted_calls == 0
    assert round(summary.total_cost, 4) == round(0.01 + 0.0234 + 0.005, 4)
    message = format_lm_cost(summary)
    assert message.startswith("$0.0384")
    assert "3 calls" in message
    assert "cache" not in message


def test_single_priced_call_uses_singular_wording():
    summary = summarize_lm_cost([{"cost": 0.01}])
    message = format_lm_cost(summary)
    assert "1 call" in message
    assert "1 calls" not in message


def test_mixed_priced_and_cached_calls_notes_the_excluded_ones():
    # The realistic case for a multi-sentence analyze_sources() run: a
    # segmentation call plus one SentenceAnalysis call per sentence, where
    # a repeat run might replay some (but not all) sentences from cache.
    history = [
        {"cost": 0.02},   # segmentation
        {"cost": 0.05},   # sentence 1
        {"cost": None},   # sentence 2, served from cache
        {"cost": 0.03},   # sentence 3
    ]
    summary = summarize_lm_cost(history)
    assert summary.priced_calls == 3
    assert summary.uncosted_calls == 1
    assert round(summary.total_cost, 4) == round(0.02 + 0.05 + 0.03, 4)
    assert summary.total_calls == 4
    message = format_lm_cost(summary)
    assert message.startswith("$0.1000")
    assert "3 calls" in message
    assert "1 more call" in message
    assert "cache" in message


def test_entries_missing_a_cost_key_entirely_count_as_uncosted():
    # A defensive case: an entry with no 'cost' key at all should behave
    # exactly like one with cost=None, not raise a KeyError.
    history = [{"prompt": "..."}, {"cost": 0.01}]
    summary = summarize_lm_cost(history)
    assert summary.priced_calls == 1
    assert summary.uncosted_calls == 1
    assert summary.total_cost == 0.01


def test_attribute_style_entries_are_read_defensively():
    # Every entry dspy.LM itself produces today is a plain dict (see
    # lm_cost.py's own docstring), but summarize_lm_cost() reads a `cost`
    # attribute too, in case some future dspy version represents an entry
    # as an object instead of a dict.
    class _FakeEntry:
        def __init__(self, cost):
            self.cost = cost

    history = [_FakeEntry(0.02), _FakeEntry(None)]
    summary = summarize_lm_cost(history)
    assert summary.priced_calls == 1
    assert summary.uncosted_calls == 1
    assert summary.total_cost == 0.02


def test_zero_cost_call_is_still_a_priced_call_not_an_uncosted_one():
    # A real (non-cached) call that happened to cost exactly $0 (e.g. a
    # free local model) should NOT be lumped in with cache hits -- cost=0
    # is a known value, unlike cost=None.
    summary = summarize_lm_cost([{"cost": 0.0}])
    assert summary.priced_calls == 1
    assert summary.uncosted_calls == 0
    assert summary.total_cost == 0.0
    assert format_lm_cost(summary) == "$0.0000 across 1 call"
