# Grouping passages by sentence boundary (`passage_grouping.py`)

`group_passages_by_sentence_boundary()` groups a `List[CitedText]` (`models.py`) into the smallest possible runs of consecutive passages that each begin and end on a sentence boundary -- e.g. to find out which individual lines of poetry can be diagrammed/reviewed on their own, versus which ones only make sense together because a sentence spans more than one of them.

No LM access needed, unlike `segmentation_dspy.py`'s own sentence segmentation (used inside `analyze_sources()`) -- this is a plain, fast, offline heuristic, not the same thing. See "Accuracy" below for the trade-off.

## Usage

```python
from arsgrammatica import group_passages_by_sentence_boundary, read_ctsdata

cited_texts = read_ctsdata("aeneid_1.ctsdata")
groups, warnings = group_passages_by_sentence_boundary(cited_texts)
```

`groups` is a list of passage-id lists (each id is a `CitedText.citation`), one list per group, in `cited_texts`' own order, covering every passage exactly once. Two examples:

- Every passage has exactly one complete sentence of its own -> one singleton group per passage: `[[id0], [id1], [id2]]`.
- Three lines of poetry contain two sentences that begin in line 1 and end at the end of line 3, with a sentence boundary in the middle of line 2 -> a single group of all three: `[[id1, id2, id3]]`.

`warnings` is non-empty only if the LAST group's final passage doesn't itself end at a sentence boundary -- there was nothing left to close it (e.g. `cited_texts` is a truncated excerpt of a longer text). That group is still returned; there's nowhere else to put those ids.

## The heuristic, and what it gets wrong

A passage is treated as ending at a sentence boundary if its own raw `text`, after stripping trailing whitespace and any trailing closing quote/parenthesis characters, ends in `.`, `?`, or `!`. This is a plain per-passage text check -- no cross-passage reasoning, and critically, no abbreviation handling.

`segmentation_dspy.SegmentPassage`'s own rule (used by the real, LM-driven segmentation) is: split at sentence-ending punctuation, *except* a period after a praenomen (e.g. "M.") or another abbreviation (e.g. "f.", "cos.") is NOT a sentence boundary. This module's heuristic can't tell an abbreviation's period from a real one, and always treats a trailing period as terminal -- so a passage ending in an abbreviation will be (mis)grouped as its own complete sentence. Use `analyze_sources()`/`segment_sources()` instead wherever that distinction actually matters; use this module where a fast, LM-free grouping is good enough (e.g. to offer only "safe" groupings in a UI before any LM call happens at all).

## Tests

`tests/test_passage_grouping.py` covers both worked examples above, plus: empty input, a single terminated passage (no warning), a single unterminated passage (warns, still returns it as its own group), an unterminated final group following a complete one, a trailing closing quote after terminal punctuation, and `?`/`!` as terminators.

## `utilities/group_ctsdata_by_sentence.py`

A command-line counterpart, for the common case of a `#!ctsdata` (CEX) source file rather than an in-memory `CitedText` list: reads the whole file with `read_ctsdata()`, groups it with `group_passages_by_sentence_boundary()`, and writes the result to stdout -- one line per group, that group's passage ids (each row's own CTS URN) joined by a single space by default, in the source file's own order:

```sh
python utilities/group_ctsdata_by_sentence.py source.cex > groups.txt
python utilities/group_ctsdata_by_sentence.py --delimiter ';' source.cex
python utilities/group_ctsdata_by_sentence.py source.cex --output-delimiter '|'
```

No LM access needed, unlike its sibling `utilities/tokenize_ctsdata.py` (which reads the same kind of source file but calls the real, LM-driven `segment_sources()`) -- this script never configures an LM or touches `.env`. Two independent delimiters: `--delimiter` controls the SOURCE file's own column delimiter (passed through to `read_ctsdata()`); `--output-delimiter` controls what joins a group's ids on this script's own output line, a single space by default -- deliberately NOT `|` like every other serialized format in this codebase, specifically so a line of output can be pasted directly into `marimo/latin_syntaxer_selected_ids.py`'s own passage-id text box, which splits on whitespace (see that notebook's own `parse_passage_ids()`, in `notes/passage_selection.md`). Pass `--output-delimiter '|'` to get the old `|`-joined behavior back. Any warning `group_passages_by_sentence_boundary()` returns goes to stderr, not stdout, so piping/redirecting stdout stays clean -- same convention as `analysis_to_dot.py`. A bad path or malformed `#!ctsdata` file surfaces `read_ctsdata()`'s own exception as-is (no try/except wrapping), matching `tokenize_ctsdata.py`'s own precedent for a single-file, non-batch script. No dedicated test file, same reasoning as `analysis_to_dot.py` and `tokenize_ctsdata.py`: it's a thin wrapper around `read_ctsdata()` and `group_passages_by_sentence_boundary()`, which are both already covered.
