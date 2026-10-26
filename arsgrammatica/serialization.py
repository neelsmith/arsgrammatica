"""
Deterministic plain-text serialization for a set of analyses, implementing
the format specified in quarto/reference/analysisformat.qmd. It writes and
reads back the three flat lists analyze_sources()/analyze_string() (plus
pipeline.py's combined_tokengraph()) naturally produce across however many
sentences and citation sources were analyzed --

    sentences:  List[Sentence]        (each Sentence.tokens: List[Token])
    verbalunits: List[VerbalExpression]
    tokengraph:  List[TokenAnalysis]

-- to and from one plain-text file, using '|' as the column separator.

write_analyses() writes straight to a file; serialize_analyses() builds
the exact same text and warnings but returns the string instead. The two
share one implementation.

File shape: line-oriented, pipe-delimited blocks, each introduced by a
label line ('#!sentences', '#!verbal_units', '#!tokens') immediately
followed by a fixed header line naming that block's columns, then one data
line per record. Blocks may appear in any order, blank lines between blocks
are ignored, and all three blocks are required. Each label may appear more
than once (e.g. from concatenating several files); read_analyses()
concatenates every block sharing a label, in file order, before parsing.

    #!sentences
    context_begin|first_token|context_end|last_token
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t0|urn:cts:latinLit:phi0690.phi003.omar:1.1|t4

    #!verbal_units
    context|token|syntactic_type
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t3|independent

    #!tokens
    context|id|tokentype|text|lemma|related|relationship
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t0|lexical|arma|arma|t3|direct object
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t1|lexical|virum|vir|t3|direct object
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t2|enclitic|que|que|t0|coordinating word
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t2|enclitic|que|que|t1|coordinating word
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t3|lexical|cano|cano|root|unit verb
    urn:cts:latinLit:phi0690.phi003.omar:1.1|t4|punctuation|.|||

#!tokens: one row per RELATION, not per token. A token with several
relations (TokenAnalysis.relations) has one row for each, all with the same
context/id/tokentype/text/lemma; these rows must be adjacent, but their
order among themselves is unspecified. A token with no relations
(punctuation, normally) has exactly one row with empty related/relationship.
read_analyses() merges each run of same-id rows back into one TokenAnalysis
and raises ValueError if a token's rows are not adjacent or disagree in any
column other than related/relationship.

TokenAnalysis.verbalunitid is not stored in #!tokens; read_analyses()
reconstructs it from #!verbal_units (each verbal expression's anchor token
gets verbalunitid = its own id).

Implied tokens (tokentype in IMPLIED_TOKENTYPES) have empty text. They
have no position in the text, so the format only requires that they appear
between their sentence's first and last token rows. serialize_analyses()
guarantees this: an implied token that falls after its sentence's last real
token in `tokengraph` (e.g. at the very end) is written just before that
last token's rows instead. An implied token's context is the context of the
sentence's first token. Implied tokens are excluded from the reconstructed
Sentence.tokens (they were never part of segmentation's output).

The optional '#!lm' block records, once per sentence, which model produced
that sentence's analysis, the sentence as a range identifier, and the
model's reasoning, each on its own 'KEY=value' line (no header line, not
pipe-delimited):

    #!lm
    MODEL=litellm_proxy/anthropic/Claude Opus 5
    CONTEXT=Aeneid 1.1.t0-Aeneid 1.1.t4
    REASONING=The main verb is "cano" ("I sing")...

serialize_analyses()/write_analyses() only emit it when called with
`reasoning=...`; read_analyses() returns an empty list when it is absent.
CONTEXT= is 'CONTEXT1.ID1-CONTEXT2.ID2' (the sentence's first and last
token's citation and id); REASONING= has internal whitespace collapsed to
single spaces. The legacy label spelling '#!LM' is still accepted on read.

Field encoding: None serializes as an empty field and parses back as None.
The reserved value 'root' is written and read verbatim. No field may
contain '|' or a newline (there is no escaping); this is checked at write
time.

Files in the format used before arsgrammatica's switch to the Quarto
specification (a #!verbal_units block with a semantic_type column, or a
10-column #!tokens block with related1/relationship1/related2/
relationship2) are NOT readable: read_analyses() raises a ValueError saying
so. Re-run the analysis to produce a file in the current format.

read_analyses() is deliberately strict: a missing block, a header that
doesn't match exactly, a wrong column count, a token id referenced by
#!sentences or #!verbal_units but absent from #!tokens, an invalid
tokentype/relationship/syntactic_type value, or a context mismatch all
raise ValueError immediately, naming the line and problem.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from pydantic import ValidationError

from .models import IMPLIED_TOKENTYPES, Relation, Sentence, Token, TokenAnalysis, VerbalExpression

SENTENCES_LABEL = "#!sentences"
VERBAL_UNITS_LABEL = "#!verbal_units"
TOKENS_LABEL = "#!tokens"
LM_LABEL = "#!lm"
# read_analyses() also accepts this exact spelling as a synonym for
# LM_LABEL, and ONLY for reading -- every file written before this label
# was lowercased used '#!LM'; a label line matching either spelling is
# folded into the same LM_LABEL bucket below, and write_analyses()/
# serialize_analyses() always emit LM_LABEL, never this one.
_LM_LABEL_LEGACY = "#!LM"

SENTENCES_HEADER = "context_begin|first_token|context_end|last_token"
VERBAL_UNITS_HEADER = "context|token|syntactic_type"
TOKENS_HEADER = "context|id|tokentype|text|lemma|related|relationship"

# Headers of the format retired with the scheme docs (quarto/concepts/). read_analyses() does
# not read these; it recognizes them only to give a clear error message.
_OLD_VERBAL_UNITS_HEADER = "context|token|syntactic_type|semantic_type"
_OLD_TOKENS_HEADER = (
    "context|id|tokentype|text|lemma|verbalunit|"
    "related1|relationship1|related2|relationship2"
)
_OLD_HEADERS = {_OLD_VERBAL_UNITS_HEADER, _OLD_TOKENS_HEADER}

_EXPECTED_HEADERS = {
    SENTENCES_LABEL: SENTENCES_HEADER,
    VERBAL_UNITS_LABEL: VERBAL_UNITS_HEADER,
    TOKENS_LABEL: TOKENS_HEADER,
}

# '#!lm' has no fixed header line (see the module docstring's "The #!lm
# block") -- each entry is three lines, each introduced by one of these
# inline prefixes instead of a pipe-delimited column.
_LM_MODEL_PREFIX = "MODEL="
_LM_CONTEXT_PREFIX = "CONTEXT="
_LM_REASONING_PREFIX = "REASONING="

_WHITESPACE_RUN = re.compile(r"\s+")


class LMInfo(NamedTuple):
    """One sentence's '#!lm' entry (see the module docstring) -- which
    model produced that sentence's analysis, a sentence-style identifier
    for what it was given to analyze ('CONTEXT1.ID1-CONTEXT2.ID2', its
    first and last token's own citation and id -- see
    `_sentence_context_identifier()`), and its own reasoning. Any of the
    three may be None, the same as an empty column elsewhere in this
    format (e.g. `model` is None whenever serialize_analyses()/
    write_analyses() were called without a `model` argument)."""

    model: Optional[str]
    context: Optional[str]
    reasoning: Optional[str]


def _field(value: Optional[str], *, where: str) -> str:
    """Render one column value: None -> '' (see module docstring), any
    other string verbatim -- after checking it contains neither '|' (this
    format's only column separator, with no escaping) nor a newline,
    either of which would silently corrupt the line-oriented structure."""
    if value is None:
        return ""
    if "|" in value or "\n" in value or "\r" in value:
        raise ValueError(
            f"{where}: value {value!r} contains a '|' or a newline, which "
            "this pipe-delimited format has no way to escape"
        )
    return value


def _parse_optional(value: str) -> Optional[str]:
    """Inverse of `_field` for an optional column: '' -> None, anything
    else verbatim (including the literal string 'root', which is a real
    value, never a stand-in for empty)."""
    return value if value != "" else None


def _lm_field(value: Optional[str], *, where: str) -> str:
    """Render one '#!lm' MODEL=/CONTEXT=/REASONING= value: None -> '', any
    other string verbatim -- after checking it contains no newline. Unlike
    `_field()`, a '|' is not rejected here: a '#!lm' line isn't
    pipe-delimited, so it has no column separator for a stray '|' to
    collide with. A newline is still checked for since this format is
    line-oriented either way (one MODEL=/CONTEXT=/REASONING= value per
    line); in practice REASONING= is already collapsed to a single line
    (see `_collapse_to_single_line()`) before ever reaching here, and
    CONTEXT= (see `_sentence_context_identifier()`) is built from
    citation/id strings that should never contain one either, so this
    should only ever fire for a MODEL= value or an unusually-formed
    citation containing a literal newline."""
    if value is None:
        return ""
    if "\n" in value or "\r" in value:
        raise ValueError(
            f"{where}: value {value!r} contains a newline, which this "
            "format has no way to represent inside a single MODEL=/"
            "CONTEXT=/REASONING= line"
        )
    return value


def _collapse_to_single_line(value: str) -> str:
    """Replace any run of whitespace (including internal newlines/
    paragraph breaks -- free-form reasoning prose can realistically
    contain either) with a single space, and strip the ends. Used for
    '#!lm's REASONING= value, which this format can only store as one
    line."""
    return _WHITESPACE_RUN.sub(" ", value).strip()


def _sentence_context_identifier(sentence: "Sentence") -> str:
    """Build one sentence's '#!lm' CONTEXT= value: a sentence-style
    identifier pairing each boundary token's own citation and id --
    'CONTEXT1.ID1-CONTEXT2.ID2', where CONTEXT1/ID1 are the first
    token's citation and id and CONTEXT2/ID2 are the last token's, e.g.
    'Aeneid 1.1.t0-Aeneid 1.1.t4' -- mirroring the #!sentences block's
    own context_begin/first_token/context_end/last_token fields, rather
    than reconstructing the sentence's surface text. A token with no
    citation renders its half as an empty string before the '.' (e.g.
    '.t5-.t9'), same as an empty column elsewhere in this format.
    Requires `sentence.tokens` to be non-empty (checked by the caller,
    same as every other place this module derives first_token/
    last_token from a sentence)."""
    first_tok = sentence.tokens[0]
    last_tok = sentence.tokens[-1]
    citation_begin = first_tok.citation or ""
    citation_end = last_tok.citation or ""
    return f"{citation_begin}.{first_tok.id}-{citation_end}.{last_tok.id}"


def serialize_analyses(
    sentences: List[Sentence],
    verbalunits: List[VerbalExpression],
    tokengraph: List[TokenAnalysis],
    *,
    model: Optional[str] = None,
    reasoning: Optional[List[Optional[str]]] = None,
) -> Tuple[str, List[str]]:
    """Build the exact text write_analyses() would write to a file, and
    return it directly as `(content, warnings)` instead of writing it
    anywhere -- see the module docstring for why this exists alongside
    write_analyses(). All three positional lists are flat and span however
    many sentences/citation sources were analyzed -- the same shape
    analyze_sources() (for `sentences`) and combined_tokengraph() (for
    `tokengraph`; `verbalunits` needs the analogous concatenation, which
    this function does not do for you) already produce.

    `model`/`reasoning` are optional and control the '#!lm' block (see the
    module docstring's "The #!lm block"): omit both (the default) to skip
    '#!lm' entirely, exactly reproducing this function's pre-'#!lm'
    output. Passing `reasoning` -- one entry per sentence, in the same
    order as `sentences`, each either that sentence's own reasoning text
    or None -- turns it on; `model` is then written as every entry's own
    MODEL= value (typically `os.environ["MODEL"]`, but this module has no
    opinion on where it comes from). `reasoning` must have exactly one
    entry per sentence; a mismatched length raises ValueError immediately,
    before anything is written.

    `content` is the complete file body, including its trailing newline,
    exactly as write_analyses() would have written it. `warnings` is a
    list of warning strings (empty if nothing looks wrong), matching this
    codebase's "degrade visibly, don't raise" convention for warnings
    distinct from hard errors:

    - a tokengraph or verbalunits entry whose id isn't found among any
      given sentence's tokens (so no citation is known for it -- an empty
      context is written, same as a token that legitimately has no
      citation at all, but this case specifically means the id wasn't
      found anywhere in `sentences` -- EXCEPT for an implied token
      (tokentype in IMPLIED_TOKENTYPES), which never appears in any sentence's own
      `tokens` by design, so this warning is suppressed for those
      specifically rather than flagged as an anomaly);
    - a sentence whose own tokens don't form a contiguous, matching-order
      run in `tokengraph`'s given order -- see the module docstring for
      why this matters for read_analyses() to recover sentence boundaries
      correctly.

    Raises ValueError for a sentence with no tokens at all (nothing to
    derive first_token/last_token from, or -- when `reasoning` is given --
    nothing to derive '#!lm's CONTEXT= from either), if any field value
    contains '|' or a newline (see `_field`), or if `reasoning` is given
    with a different number of entries than `sentences`.
    """
    warnings: List[str] = []

    if reasoning is not None and len(reasoning) != len(sentences):
        raise ValueError(
            f"`reasoning` has {len(reasoning)} entr"
            f"{'y' if len(reasoning) == 1 else 'ies'}, but there "
            f"{'is' if len(sentences) == 1 else 'are'} {len(sentences)} "
            "sentence(s) -- '#!lm' needs exactly one reasoning entry per "
            "sentence"
        )

    id_to_citation: Dict[str, Optional[str]] = {}
    for sentence in sentences:
        for tok in sentence.tokens:
            id_to_citation[tok.id] = tok.citation

    for s_idx, sentence in enumerate(sentences):
        if not sentence.tokens:
            raise ValueError(
                f"sentence at index {s_idx} has no tokens -- cannot derive "
                "first_token/last_token for an empty sentence"
            )

    ordered, implied_context, implied_warnings = _place_implied_tokens(sentences, tokengraph)
    warnings.extend(implied_warnings)
    id_to_citation.update(implied_context)
    implied_ids = {tok.id for tok in ordered if tok.tokentype in IMPLIED_TOKENTYPES}

    tg_index = {tok.id: i for i, tok in enumerate(ordered)}

    lines: List[str] = []

    if reasoning is not None:
        lines.append(LM_LABEL)
        for s_idx, sentence in enumerate(sentences):
            where = f"'#!lm' entry for sentence {s_idx}"
            context_value = _sentence_context_identifier(sentence)
            reasoning_value = reasoning[s_idx]
            collapsed_reasoning = (
                _collapse_to_single_line(reasoning_value) if reasoning_value is not None else None
            )
            lines.append(_LM_MODEL_PREFIX + _lm_field(model, where=where))
            lines.append(_LM_CONTEXT_PREFIX + _lm_field(context_value, where=where))
            lines.append(_LM_REASONING_PREFIX + _lm_field(collapsed_reasoning, where=where))
        lines.append("")

    lines.append(SENTENCES_LABEL)
    lines.append(SENTENCES_HEADER)
    for s_idx, sentence in enumerate(sentences):
        first_tok = sentence.tokens[0]
        last_tok = sentence.tokens[-1]

        first_pos = tg_index.get(first_tok.id)
        last_pos = tg_index.get(last_tok.id)
        if first_pos is None or last_pos is None:
            warnings.append(
                f"sentence at index {s_idx} (tokens {first_tok.id!r}.."
                f"{last_tok.id!r}) has a boundary token not present in the "
                "given tokengraph -- reading this file back may not "
                "reconstruct this sentence's tokens correctly"
            )
        else:
            expected_ids = [t.id for t in sentence.tokens]
            actual_ids = [
                tok.id
                for tok in ordered[first_pos : last_pos + 1]
                if tok.tokentype not in IMPLIED_TOKENTYPES
            ]
            if actual_ids != expected_ids:
                warnings.append(
                    f"sentence at index {s_idx} (tokens {first_tok.id!r}.."
                    f"{last_tok.id!r}) is not a contiguous, matching-order "
                    "run in the given tokengraph -- reading this file back "
                    "may not reconstruct this sentence's tokens correctly"
                )

        where = f"#!sentences row for sentence {s_idx}"
        lines.append(
            "|".join(
                [
                    _field(first_tok.citation, where=where),
                    _field(first_tok.id, where=where),
                    _field(last_tok.citation, where=where),
                    _field(last_tok.id, where=where),
                ]
            )
        )

    lines.append("")
    lines.append(VERBAL_UNITS_LABEL)
    lines.append(VERBAL_UNITS_HEADER)
    for vu in verbalunits:
        if vu.id not in id_to_citation and vu.id not in implied_ids:
            warnings.append(
                f"verbal expression {vu.id!r} not found among the given "
                "sentences' tokens -- writing an empty context for it"
            )
        where = f"#!verbal_units row for {vu.id}"
        lines.append(
            "|".join(
                [
                    _field(id_to_citation.get(vu.id), where=where),
                    _field(vu.id, where=where),
                    _field(vu.syntactic_type, where=where),
                ]
            )
        )

    lines.append("")
    lines.append(TOKENS_LABEL)
    lines.append(TOKENS_HEADER)
    for tok in ordered:
        if tok.id not in id_to_citation and tok.id not in implied_ids:
            warnings.append(
                f"token {tok.id!r} not found among the given sentences' "
                "tokens -- writing an empty context for it"
            )
        where = f"#!tokens row for {tok.id}"
        prefix = [
            _field(id_to_citation.get(tok.id), where=where),
            _field(tok.id, where=where),
            _field(tok.tokentype, where=where),
            _field(tok.token, where=where),
            _field(tok.lemma, where=where),
        ]
        relation_pairs = [(r.related, r.relationship) for r in tok.relations] or [(None, None)]
        for related, relationship in relation_pairs:
            lines.append(
                "|".join(
                    prefix
                    + [_field(related, where=where), _field(relationship, where=where)]
                )
            )

    return "\n".join(lines) + "\n", warnings


def _place_implied_tokens(
    sentences: List[Sentence], tokengraph: List[TokenAnalysis]
) -> Tuple[List[TokenAnalysis], Dict[str, Optional[str]], List[str]]:
    """Return `(ordered, implied_context, warnings)`: `tokengraph` with every
    implied token guaranteed to lie between its sentence's first and last
    real token (quarto/reference/analysisformat.qmd), plus each implied
    token's context (its sentence's first token's citation).

    An implied token already inside a sentence's span stays where it is.
    One lying between two sentences' spans (most often: after a sentence's
    last token, e.g. at the very end of `tokengraph`) belongs to the
    PRECEDING sentence and is moved to just before that sentence's last
    real token; one before every sentence's span belongs to the first
    sentence and is moved to just after its first token. An implied token
    that can't be placed (no sentences, or boundary tokens missing from
    `tokengraph`) is left in place, with a warning."""
    warnings: List[str] = []
    position = {tok.id: i for i, tok in enumerate(tokengraph)}
    spans = []
    for sentence in sentences:
        first = position.get(sentence.tokens[0].id)
        last = position.get(sentence.tokens[-1].id)
        if first is not None and last is not None:
            spans.append((first, last, sentence.tokens[0].citation))

    implied_context: Dict[str, Optional[str]] = {}
    move_before_last: Dict[int, List[TokenAnalysis]] = {}
    move_after_first: Dict[int, List[TokenAnalysis]] = {}
    moved = set()
    for i, tok in enumerate(tokengraph):
        if tok.tokentype not in IMPLIED_TOKENTYPES:
            continue
        owner = None
        for s_idx, (first, last, citation) in enumerate(spans):
            if first <= i <= last:
                owner = s_idx
                break
        if owner is not None:
            implied_context[tok.id] = spans[owner][2]
            continue
        preceding = [s_idx for s_idx, (first, last, _) in enumerate(spans) if last < i]
        if preceding:
            owner = max(preceding, key=lambda k: spans[k][1])
            move_before_last.setdefault(owner, []).append(tok)
        elif spans:
            owner = min(range(len(spans)), key=lambda k: spans[k][0])
            move_after_first.setdefault(owner, []).append(tok)
        else:
            warnings.append(
                f"implied token {tok.id!r} could not be assigned to any "
                "sentence -- writing it in place with an empty context"
            )
            continue
        implied_context[tok.id] = spans[owner][2]
        moved.add(id(tok))

    if not moved:
        return list(tokengraph), implied_context, warnings

    first_of = {spans[k][0]: k for k in move_after_first}
    last_of = {spans[k][1]: k for k in move_before_last}
    ordered: List[TokenAnalysis] = []
    for i, tok in enumerate(tokengraph):
        if id(tok) in moved:
            continue
        if i in last_of:
            ordered.extend(move_before_last[last_of[i]])
        ordered.append(tok)
        if i in first_of:
            ordered.extend(move_after_first[first_of[i]])
    return ordered, implied_context, warnings


def write_analyses(
    sentences: List[Sentence],
    verbalunits: List[VerbalExpression],
    tokengraph: List[TokenAnalysis],
    path: str,
    *,
    model: Optional[str] = None,
    reasoning: Optional[List[Optional[str]]] = None,
) -> List[str]:
    """Write `sentences`/`verbalunits`/`tokengraph` to `path` in the format
    this module's docstring describes -- see serialize_analyses() (which
    this is a thin wrapper around) for what's actually written and for the
    full list of warnings this can return. `model`/`reasoning` are passed
    straight through to serialize_analyses() and control the optional
    '#!lm' block exactly as described there -- omit both to skip it.

    Returns a list of warning strings (empty if nothing looks wrong); see
    serialize_analyses()'s docstring for what each one means. Raises
    ValueError for a sentence with no tokens at all (nothing to derive
    first_token/last_token from), if any field value contains '|' or a
    newline (see `_field`), or if `reasoning` is given with a different
    number of entries than `sentences` -- all raised by serialize_analyses()
    before this function ever opens `path`.
    """
    content, warnings = serialize_analyses(
        sentences, verbalunits, tokengraph, model=model, reasoning=reasoning
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return warnings


def read_analyses(
    path: str,
) -> Tuple[List[TokenAnalysis], List[VerbalExpression], List[Sentence], List[LMInfo]]:
    """Read `path` (as written by write_analyses()/serialize_analyses()) and
    reconstruct `(tokengraph, verbalunits, sentences, lm_infos)` -- in that
    order, matching the order these types are usually discussed in this
    codebase (the token-level graph, then the verbal-expression table,
    then the sentence/citation structure that supplies context for both,
    then the optional per-sentence '#!lm' record of what produced them).

    Each of the three required block labels may appear more than once in
    `path` (see the module docstring) -- every instance contributes its
    own rows, in file order, to that label's combined row list, as if the
    file were the concatenation of however many separate write_analyses()/
    serialize_analyses() outputs it actually is. '#!lm' may repeat the
    same way.

    `lm_infos` is `[]` if `path` has no '#!lm' block at all (every file
    written before this block existed, or any file written without
    passing `reasoning` to write_analyses()/serialize_analyses(), reads
    back exactly as before) -- otherwise it's one `LMInfo` per sentence,
    aligned with `sentences` by position, same as `tokengraph`/
    `verbalunits` are conceptually aligned with `sentences` via token ids.

    Raises ValueError, naming the offending line and problem, for anything
    that isn't a faithful, internally-consistent file written by
    write_analyses() -- see this module's own docstring for exactly what's
    checked, including '#!lm's own narrower checks (a line count that
    isn't a multiple of 3, a line missing its expected prefix, or a number
    of entries that doesn't match the number of sentences). This function
    does not accept a file with warnings-worthy inconsistencies silently
    patched over; if write_analyses() returned warnings when the file was
    written, fix the input and re-write it rather than expecting
    read_analyses() to compensate.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    # blocks[label] accumulates (line_no, line) data rows across every
    # instance of that label found in the file, in file order. A label
    # line always starts a new instance and must be immediately followed
    # by that label's header line (`awaiting_header` tracks this) before
    # any more data rows can be appended to it -- this holds per instance,
    # not just for the label's first appearance, so every repeated block
    # must repeat its own header line too. '#!lm' is the one exception: it
    # has no header line at all (see the module docstring), so a '#!lm'
    # label line goes straight to accepting data rows -- `awaiting_header`
    # is never set for it.
    blocks: Dict[str, List[Tuple[int, str]]] = {label: [] for label in _EXPECTED_HEADERS}
    blocks[LM_LABEL] = []
    seen_labels = set()
    current_label: Optional[str] = None
    awaiting_header = False

    for line_no, line in enumerate(raw_lines, start=1):
        if line.strip() == "":
            continue

        if line == LM_LABEL or line == _LM_LABEL_LEGACY or line in _EXPECTED_HEADERS:
            if awaiting_header:
                raise ValueError(
                    f"line {line_no}: block {current_label!r} has a label "
                    "line but no header line before the next block starts"
                )
            # Normalize the legacy '#!LM' spelling to LM_LABEL immediately,
            # so every downstream use of current_label/blocks/seen_labels
            # only ever has to know about the one canonical label -- a file
            # mixing both spellings across its '#!lm' blocks (e.g. from
            # concatenating an old and a new write_analyses() output) still
            # merges into a single entry, the same as two same-spelling
            # blocks already do.
            current_label = LM_LABEL if line == _LM_LABEL_LEGACY else line
            seen_labels.add(current_label)
            awaiting_header = current_label != LM_LABEL
            continue

        if current_label is None:
            raise ValueError(
                f"line {line_no}: data line {line!r} appears before any "
                "'#!' block label"
            )

        if awaiting_header:
            expected = _EXPECTED_HEADERS[current_label]
            if line in _OLD_HEADERS:
                raise ValueError(
                    f"line {line_no}: block {current_label!r} uses the "
                    "pre-1.0 analysis format (with semantic_type, or "
                    "related1/relationship1/related2/relationship2), which "
                    "is no longer supported -- re-run the analysis to write "
                    f"it in the current format (header {expected!r})"
                )
            if line != expected:
                raise ValueError(
                    f"line {line_no}: expected header {expected!r} for "
                    f"block {current_label!r}, got {line!r}"
                )
            awaiting_header = False
            continue

        blocks[current_label].append((line_no, line))

    missing = sorted(set(_EXPECTED_HEADERS) - seen_labels)
    if missing:
        raise ValueError(f"file is missing required block(s): {missing}")
    if awaiting_header:
        raise ValueError(
            f"block {current_label!r} has a label line but no header line "
            "(and no data) -- the file ends too early"
        )

    # --- #!tokens: build the TokenAnalysis list, the id->citation map,
    # and the row-order index sentence reconstruction relies on. ---
    tokengraph: List[TokenAnalysis] = []
    id_to_citation: Dict[str, Optional[str]] = {}
    row_order: List[str] = []
    # (context, tokentype, text, lemma) of the token currently being
    # accumulated, to check that a token's repeated rows agree.
    current_fixed: Optional[Tuple[str, str, str, str]] = None

    for line_no, line in blocks[TOKENS_LABEL]:
        parts = line.split("|")
        if len(parts) != 7:
            raise ValueError(
                f"line {line_no}: #!tokens row has {len(parts)} columns, "
                f"expected 7: {line!r}"
            )
        context, tok_id, tokentype, text, lemma, related, relationship = parts
        if tok_id == "":
            raise ValueError(f"line {line_no}: #!tokens row has an empty id")
        if (related == "") != (relationship == ""):
            raise ValueError(
                f"line {line_no}: #!tokens row for {tok_id!r} has only one of "
                "related/relationship -- both must be given, or both empty"
            )

        fixed = (context, tokentype, text, lemma)
        if tokengraph and tokengraph[-1].id == tok_id:
            # A further relation of the token on the previous row.
            if fixed != current_fixed:
                raise ValueError(
                    f"line {line_no}: repeated #!tokens row for {tok_id!r} "
                    "differs from the token's earlier row in a column other "
                    "than related/relationship"
                )
            tok = tokengraph[-1]
            if related == "" or not tok.relations:
                raise ValueError(
                    f"line {line_no}: repeated #!tokens row for {tok_id!r} "
                    "must give a relation, and so must every other row for "
                    "that token"
                )
        else:
            if tok_id in id_to_citation:
                raise ValueError(
                    f"line {line_no}: token id {tok_id!r} appears in #!tokens "
                    "again after other tokens -- a token's rows must be adjacent"
                )
            try:
                tok = TokenAnalysis(
                    id=tok_id,
                    token=_parse_optional(text),
                    tokentype=tokentype,
                    lemma=_parse_optional(lemma),
                )
            except ValidationError as exc:
                raise ValueError(f"line {line_no}: invalid #!tokens row {line!r}: {exc}") from exc
            tokengraph.append(tok)
            id_to_citation[tok_id] = _parse_optional(context)
            row_order.append(tok_id)
            current_fixed = fixed

        if related != "":
            try:
                tok.relations.append(Relation(related=related, relationship=relationship))
            except ValidationError as exc:
                raise ValueError(
                    f"line {line_no}: invalid relationship {relationship!r} "
                    f"in #!tokens row for {tok_id!r}"
                ) from exc

    id_position = {tid: i for i, tid in enumerate(row_order)}

    # --- #!verbal_units ---
    verbalunits: List[VerbalExpression] = []
    for line_no, line in blocks[VERBAL_UNITS_LABEL]:
        parts = line.split("|")
        if len(parts) != 3:
            raise ValueError(
                f"line {line_no}: #!verbal_units row has {len(parts)} "
                f"columns, expected 3: {line!r}"
            )
        context, vu_id, syntactic_type = parts
        if vu_id == "":
            raise ValueError(f"line {line_no}: #!verbal_units row has an empty token id")
        if vu_id not in id_to_citation:
            raise ValueError(
                f"line {line_no}: #!verbal_units references token id "
                f"{vu_id!r}, which does not appear in the #!tokens block"
            )
        recorded_context = _parse_optional(context)
        expected_context = id_to_citation[vu_id]
        if recorded_context != expected_context:
            raise ValueError(
                f"line {line_no}: #!verbal_units row's context "
                f"{recorded_context!r} for token {vu_id!r} does not match "
                f"the #!tokens block's recorded context {expected_context!r} "
                "for the same id"
            )
        try:
            verbalunits.append(VerbalExpression(id=vu_id, syntactic_type=syntactic_type))
        except ValidationError as exc:
            raise ValueError(
                f"line {line_no}: invalid syntactic_type {syntactic_type!r} "
                f"in #!verbal_units row for {vu_id!r}"
            ) from exc
        # TokenAnalysis.verbalunitid isn't stored in #!tokens: rebuild it.
        tokengraph[id_position[vu_id]].verbalunitid = vu_id

    # --- #!sentences ---
    sentences: List[Sentence] = []
    for line_no, line in blocks[SENTENCES_LABEL]:
        parts = line.split("|")
        if len(parts) != 4:
            raise ValueError(
                f"line {line_no}: #!sentences row has {len(parts)} "
                f"columns, expected 4: {line!r}"
            )
        context_begin, first_id, context_end, last_id = parts
        if first_id == "" or last_id == "":
            raise ValueError(
                f"line {line_no}: #!sentences row is missing first_token "
                f"or last_token: {line!r}"
            )
        if first_id not in id_position or last_id not in id_position:
            raise ValueError(
                f"line {line_no}: #!sentences references a first_token/"
                "last_token id not found in the #!tokens block"
            )

        start = id_position[first_id]
        end = id_position[last_id]
        if start > end:
            raise ValueError(
                f"line {line_no}: #!sentences row's first_token "
                f"{first_id!r} comes after last_token {last_id!r} in the "
                "#!tokens block's row order"
            )

        parsed_begin = _parse_optional(context_begin)
        parsed_end = _parse_optional(context_end)
        if parsed_begin != id_to_citation[first_id]:
            raise ValueError(
                f"line {line_no}: #!sentences row's context_begin "
                f"{parsed_begin!r} does not match the #!tokens block's "
                f"recorded context {id_to_citation[first_id]!r} for token "
                f"{first_id!r}"
            )
        if parsed_end != id_to_citation[last_id]:
            raise ValueError(
                f"line {line_no}: #!sentences row's context_end "
                f"{parsed_end!r} does not match the #!tokens block's "
                f"recorded context {id_to_citation[last_id]!r} for token "
                f"{last_id!r}"
            )

        sentence_ids = [
            tid
            for tid in row_order[start : end + 1]
            if tokengraph[id_position[tid]].tokentype not in IMPLIED_TOKENTYPES
        ]
        sentences.append(
            Sentence(
                tokens=[
                    Token(
                        id=tid,
                        text=tokengraph[id_position[tid]].token,
                        citation=id_to_citation[tid],
                    )
                    for tid in sentence_ids
                ]
            )
        )

    # --- #!lm (optional) ---
    lm_raw = blocks[LM_LABEL]
    lm_infos: List[LMInfo] = []
    if lm_raw:
        if len(lm_raw) % 3 != 0:
            first_line_no = lm_raw[0][0]
            raise ValueError(
                f"line {first_line_no}: '#!lm' block has {len(lm_raw)} "
                "line(s), which is not a multiple of 3 -- each entry needs "
                "exactly a MODEL=, CONTEXT=, and REASONING= line, in that "
                "order"
            )
        for i in range(0, len(lm_raw), 3):
            model_line_no, model_line = lm_raw[i]
            context_line_no, context_line = lm_raw[i + 1]
            reasoning_line_no, reasoning_line = lm_raw[i + 2]
            if not model_line.startswith(_LM_MODEL_PREFIX):
                raise ValueError(
                    f"line {model_line_no}: expected a line starting with "
                    f"{_LM_MODEL_PREFIX!r} in the '#!lm' block, got "
                    f"{model_line!r}"
                )
            if not context_line.startswith(_LM_CONTEXT_PREFIX):
                raise ValueError(
                    f"line {context_line_no}: expected a line starting "
                    f"with {_LM_CONTEXT_PREFIX!r} in the '#!lm' block, got "
                    f"{context_line!r}"
                )
            if not reasoning_line.startswith(_LM_REASONING_PREFIX):
                raise ValueError(
                    f"line {reasoning_line_no}: expected a line starting "
                    f"with {_LM_REASONING_PREFIX!r} in the '#!lm' block, "
                    f"got {reasoning_line!r}"
                )
            lm_infos.append(
                LMInfo(
                    model=_parse_optional(model_line[len(_LM_MODEL_PREFIX):]),
                    context=_parse_optional(context_line[len(_LM_CONTEXT_PREFIX):]),
                    reasoning=_parse_optional(
                        reasoning_line[len(_LM_REASONING_PREFIX):]
                    ),
                )
            )

        if len(lm_infos) != len(sentences):
            raise ValueError(
                f"'#!lm' block has {len(lm_infos)} "
                f"entr{'y' if len(lm_infos) == 1 else 'ies'}, but "
                f"#!sentences reconstructed {len(sentences)} sentence(s) -- "
                "'#!lm' entries are recorded one per sentence, so these "
                "must match"
            )

    return tokengraph, verbalunits, sentences, lm_infos


def split_analysis_by_sentence(
    tokengraph: List[TokenAnalysis],
    verbalunits: List[VerbalExpression],
    sentences: List[Sentence],
) -> List[Tuple[List[TokenAnalysis], List[VerbalExpression]]]:
    """The inverse of what write_analyses()/serialize_analyses() flatten
    together: given the same `(tokengraph, verbalunits, sentences)` triple
    read_analyses() returns (or that analyze_sources()/combined_tokengraph()
    produce before ever being written to a file), split `tokengraph` and
    `verbalunits` back into one slice per sentence.

    Returns a list the same length and order as `sentences` -- entry i is
    `(sentence_tokengraph, sentence_verbalunits)` for `sentences[i]`. Useful
    for anything that wants to review or render one sentence's analysis at
    a time (e.g. a sentence-picker UI, like marimo/latin_syntaxer_review.py)
    without re-running analysis or re-deriving the same id-position
    bookkeeping read_analyses()/write_analyses() already do internally.

    Relies on the same invariant read_analyses() and write_analyses()
    already depend on: a sentence's own tokens form a contiguous,
    matching-order run in `tokengraph` (see this module's own docstring).
    `sentence_tokengraph` is the slice of `tokengraph` between that
    sentence's first and last token's positions, inclusive -- which also
    picks up any implied/elided tokens (tokentype in IMPLIED_TOKENTYPES)
    interspersed within that range, since those were never part of
    `sentence.tokens` to begin with but do belong to that sentence's own
    analysis. `sentence_verbalunits` is every VerbalExpression whose id
    falls within that same slice.

    Implied tokens placed after a sentence's last real token (before the
    next sentence's first token) are included in that sentence's slice, so
    an analysis built in memory with an implied token at the end of its
    sentence splits correctly too.

    Raises ValueError for a sentence with no tokens at all, or whose first
    or last token id isn't present in `tokengraph` -- both should be
    impossible for a triple that actually came from read_analyses(), which
    already guarantees this by construction, but this function checks
    explicitly anyway rather than trusting the caller, since nothing stops
    it being called with a hand-built triple too.
    """
    id_position: Dict[str, int] = {tok.id: i for i, tok in enumerate(tokengraph)}

    result: List[Tuple[List[TokenAnalysis], List[VerbalExpression]]] = []
    for s_idx, sentence in enumerate(sentences):
        if not sentence.tokens:
            raise ValueError(f"sentence at index {s_idx} has no tokens")

        first_id = sentence.tokens[0].id
        last_id = sentence.tokens[-1].id
        if first_id not in id_position or last_id not in id_position:
            raise ValueError(
                f"sentence at index {s_idx} (tokens {first_id!r}.."
                f"{last_id!r}) has a boundary token not present in the "
                "given tokengraph"
            )

        start = id_position[first_id]
        end = id_position[last_id]
        # An implied token placed after the sentence's last real token
        # (before the next sentence) still belongs to this sentence.
        while end + 1 < len(tokengraph) and tokengraph[end + 1].tokentype in IMPLIED_TOKENTYPES:
            end += 1
        sentence_tokengraph = tokengraph[start : end + 1]
        sentence_ids = {tok.id for tok in sentence_tokengraph}
        sentence_verbalunits = [vu for vu in verbalunits if vu.id in sentence_ids]
        result.append((sentence_tokengraph, sentence_verbalunits))

    return result
