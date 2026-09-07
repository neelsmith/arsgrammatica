"""
Tests for passage_grouping.py's group_passages_by_sentence_boundary() --
a pure-Python (no LM), text-ending heuristic for grouping CitedText passages
into the smallest runs that each begin and end on a sentence boundary. See
passage_grouping.py's own module docstring for how this differs from
segmentation_dspy.py's LM-driven segmentation (no abbreviation handling).

Covers the two worked examples the function was specified against, plus the
edge cases those examples don't exercise: empty input, a single passage
(terminated and unterminated), and an unterminated final group's warning.
"""

from arsgrammatica import group_passages_by_sentence_boundary
from arsgrammatica.models import CitedText


def test_empty_input_returns_no_groups_and_no_warnings():
    groups, warnings = group_passages_by_sentence_boundary([])
    assert groups == []
    assert warnings == []


def test_every_passage_with_exactly_one_sentence_returns_one_group_per_passage():
    # "If every passage in a text has exactly one sentence, then this
    # would return the list of every passage id" -- one singleton group
    # per passage.
    cited_texts = [
        CitedText(citation="l1", text="Prima sententia."),
        CitedText(citation="l2", text="Secunda sententia."),
        CitedText(citation="l3", text="Tertia sententia."),
    ]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["l1"], ["l2"], ["l3"]]
    assert warnings == []


def test_sentence_spanning_three_lines_returns_a_single_group():
    # "If three lines of poetry included two sentences that began in line
    # 1 and ended at the end of line 3, with a sentence end/beginning in
    # the middle of line 2, ... the function would find a single group and
    # return a single list of the three ids." Neither line 1's nor line
    # 2's own raw text ends in terminal punctuation (the mid-line boundary
    # is invisible to this per-passage heuristic) -- only line 3's does.
    cited_texts = [
        CitedText(citation="line1", text="Arma virumque cano Troiae qui primus ab oris"),
        CitedText(citation="line2", text="Italiam. Fato profugus Laviniaque venit"),
        CitedText(citation="line3", text="litora, multum ille et terris iactatus et alto."),
    ]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["line1", "line2", "line3"]]
    assert warnings == []


def test_single_terminated_passage_is_its_own_group_with_no_warning():
    cited_texts = [CitedText(citation="only", text="Una sententia.")]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["only"]]
    assert warnings == []


def test_single_unterminated_passage_is_its_own_group_with_a_warning():
    cited_texts = [CitedText(citation="only", text="Sententia incompleta")]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["only"]]
    assert len(warnings) == 1
    assert "only" in warnings[0]


def test_unterminated_final_group_after_a_complete_one_still_warns_and_groups():
    cited_texts = [
        CitedText(citation="a", text="Complete est."),
        CitedText(citation="b", text="Incompleta"),
        CitedText(citation="c", text="adhuc incompleta"),
    ]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["a"], ["b", "c"]]
    assert len(warnings) == 1
    assert "b" in warnings[0] and "c" in warnings[0]


def test_trailing_closing_quote_after_terminal_punctuation_still_counts():
    # A closing quote/paren after the sentence-ending punctuation shouldn't
    # defeat the check -- e.g. the end of a quoted sentence.
    cited_texts = [CitedText(citation="q", text='"Vale," inquit.\'')]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["q"]]
    assert warnings == []


def test_question_and_exclamation_marks_also_count_as_terminal():
    cited_texts = [
        CitedText(citation="q1", text="Quis venit?"),
        CitedText(citation="q2", text="Vale!"),
    ]

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)

    assert groups == [["q1"], ["q2"]]
    assert warnings == []
