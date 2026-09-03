"""
Groups a sequence of CitedText passages (models.py) into the SMALLEST
possible runs that each begin and end on a sentence boundary -- e.g. so a
caller can find which individual lines of poetry can be diagrammed/reviewed
on their own, versus which ones only make sense analyzed together because a
sentence spans more than one of them.

No LM access needed, unlike analyze_sources()/segment_sources()
(segmentation_dspy.py), which is the only other place in this codebase that
identifies sentence boundaries. This module trades that accuracy for speed
and offline use: it approximates a sentence boundary as "this passage's own
raw text ends in sentence-ending punctuation (. ? !)", a plain per-passage
text check with no cross-passage reasoning and no abbreviation handling --
segmentation_dspy.SegmentPassage's own docstring documents the one case this
simple rule gets wrong that an LM wouldn't: a period after a praenomen (e.g.
"M.") or another abbreviation (e.g. "f.", "cos.") is NOT a sentence
boundary, but this module's heuristic has no way to tell those apart from a
real one and always treats a trailing period as terminal. Use
analyze_sources()/segment_sources() instead of this module wherever that
distinction matters; use this module where a fast, LM-free grouping is
enough (e.g. to offer only "safe" groupings of passages in a UI before any
LM call happens at all).
"""

from typing import List, Tuple

from .models import CitedText

# Sentence-ending punctuation this module's heuristic looks for, matching
# segmentation_dspy.SegmentPassage's own rule ("sentence-ending punctuation
# (. ? !)") minus its abbreviation exception, which a plain per-passage text
# check can't reproduce -- see this module's own docstring.
_SENTENCE_END_CHARS = ".?!"

# Trailing closing-quote/parenthesis characters to look past when checking
# for a sentence-ending character -- e.g. a passage ending "...inquit."'"
# (a closing single quote after the period) should still count as ending at
# a sentence boundary, not be rejected for not literally ending in one of
# _SENTENCE_END_CHARS.
_TRAILING_CLOSERS = "\"')]’”"


def _ends_at_sentence_boundary(text: str) -> bool:
    """Whether `text` (one CitedText's own raw text) looks like it ends at a
    sentence boundary: strip trailing whitespace, then strip any trailing
    closing quote/parenthesis characters (_TRAILING_CLOSERS), then check
    whether what's left ends in one of _SENTENCE_END_CHARS. See this
    module's own docstring for what this heuristic gets wrong (the
    abbreviation exception) compared to segmentation_dspy.py's LM-driven
    segmentation."""
    stripped = text.rstrip().rstrip(_TRAILING_CLOSERS)
    return stripped.endswith(tuple(_SENTENCE_END_CHARS))


def group_passages_by_sentence_boundary(
    cited_texts: List[CitedText],
) -> Tuple[List[List[str]], List[str]]:
    """Group `cited_texts` (in their own given order) into the SMALLEST
    possible runs of consecutive passages that each begin and end on a
    sentence boundary, per this module's own text-ending heuristic (see
    module docstring) -- NOT segmentation_dspy.py's LM-driven segmentation.

    A passage whose own text ends at a sentence boundary closes the group
    it's in (which may be just itself); a passage that doesn't ends up
    grouped together with however many following passages it takes to reach
    one that does. Two worked examples (the ones this function was
    specified against):

    - every passage in a text has exactly one complete sentence (each one's
      own text ends in terminal punctuation) -> one singleton group per
      passage, e.g. [[id0], [id1], [id2]].
    - three lines of poetry contain two sentences that begin in line 1 and
      end at the end of line 3, with a sentence end/beginning in the middle
      of line 2 (so neither line 1's nor line 2's own text ends in terminal
      punctuation -- only line 3's does) -> a single group of all three:
      [[id1, id2, id3]].

    Returns (groups, warnings): `groups` is a list of passage-id lists, one
    list per group, in `cited_texts`' own order, using each CitedText's
    `citation` as its id -- covering every passage in `cited_texts` exactly
    once. `warnings` names the one situation this function flags rather
    than silently guessing: if the LAST group's own final passage doesn't
    end at a sentence boundary (there was nothing left to close it), that
    group is still returned (there's nowhere else to put those ids), but a
    warning is added noting it may be an incomplete sentence -- e.g. because
    `cited_texts` itself is a truncated excerpt of a longer text. An empty
    `cited_texts` returns ([], []).
    """
    groups: List[List[str]] = []
    current: List[str] = []
    warnings: List[str] = []

    for cited_text in cited_texts:
        current.append(cited_text.citation)
        if _ends_at_sentence_boundary(cited_text.text):
            groups.append(current)
            current = []

    if current:
        warnings.append(
            f"the final group {current!r} doesn't end at a sentence "
            "boundary -- its last passage's text has no closing "
            "sentence-ending punctuation, so the sentence it ends with "
            "may be incomplete"
        )
        groups.append(current)

    return groups, warnings
