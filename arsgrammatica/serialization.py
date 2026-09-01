"""
Deterministic plain-text serialization for a set of analyses: writes and
reads back the three flat lists analyze_sources()/analyze_passage() (plus
pipeline.py's combined_tokengraph()) naturally produce across however many
sentences and citation sources were analyzed --

    sentences:  List[Sentence]        (each Sentence.tokens: List[Token])
    verbalunits: List[VerbalExpression]
    tokengraph:  List[TokenAnalysis]

-- to and from one plain-text file, using '|' as the column separator, so
an analysis can be saved, diffed, hand-edited, or loaded back into exactly
the same three Python types without needing a database or a pickle file.

write_analyses() writes straight to a file; serialize_analyses() builds
the exact same text and warnings but returns the string instead of
writing it anywhere -- useful whenever the caller wants to embed this
format in something else (a log, a prompt, another file's contents, an
in-memory test fixture) rather than write a standalone file. The two
share one implementation: write_analyses() is a thin wrapper that calls
serialize_analyses() and writes its result to `path`.

File shape: three line-oriented, pipe-delimited blocks, each introduced by
a label line (one of '#!sentences', '#!verbal_units', '#!tokens' alone on
its own line) immediately followed by a fixed header line naming that
block's columns, then one data line per record. Blocks may appear in any
order (the label is what identifies a block, not its position), blank
lines between blocks are ignored, and all three blocks are required.

A fourth, OPTIONAL block, '#!LM', records what produced an analysis --
see "The #!LM block" below for its shape and why it doesn't follow the
label+header+pipe-rows pattern the other three do.

Each of the three labels may also appear MORE THAN ONCE -- e.g. several
'#!tokens' blocks, each with its own repeated header line, scattered
anywhere in the file. read_analyses() concatenates every block sharing a
label into that label's single combined row list, in file order, before
doing anything else with it -- so a file built by literally concatenating
several write_analyses()/serialize_analyses() outputs (each a complete,
self-contained trio of blocks) reads back exactly as if all their
sentences/verbalunits/tokengraph rows had been passed to a single
write_analyses() call to begin with. write_analyses() itself still only
ever emits one instance of each block; multiple instances are something
read_analyses() accepts, not something this module produces.

    #!sentences
    context_begin|first_token|context_end|last_token
    Aeneid 1.1|t0|Aeneid 1.1|t9

    #!verbal_units
    context|token|syntactic_type|semantic_type
    Aeneid 1.1|t5|independent|transitive active

    #!tokens
    context|id|tokentype|text|lemma|verbalunit|related1|relationship1|related2|relationship2
    Aeneid 1.1|t0|lexical|Arma|arma|||||

The #!LM block: unlike the three blocks above, '#!LM' has no header line
and isn't pipe-delimited -- it records, once per sentence, which model
produced that sentence's analysis, what it was given to analyze, and its
own reasoning, each on its own 'KEY=value' line, three lines per sentence,
in the same order as `sentences` itself:

    #!LM
    MODEL=litellm_proxy/anthropic/Claude Opus 5
    CONTEXT=Aeneid 1.1.t0-Aeneid 1.1.t4
    REASONING=The main verb is "cano" ("I sing"), independent and transitive active...

When present, '#!LM' is written as a single contiguous section, entirely
before '#!sentences'/'#!verbal_units'/'#!tokens' (for a human reader
skimming top-to-bottom -- the discursive record before the structural
tables), holding all of one serialize_analyses()/write_analyses() call's
per-sentence entries back to back: sentence 0's MODEL=/CONTEXT=/REASONING=
trio, then sentence 1's, and so on, with no blank line or repeated label
between entries. It's optional at both ends: serialize_analyses()/
write_analyses() only emit it when called with `reasoning=...` (see their
own docstrings), and read_analyses() accepts a file with none at all,
handing back an empty list rather than requiring it -- every file written
before this block existed still reads back exactly as before, with an
empty fourth return value. Like the other three, '#!LM' may itself be
repeated (e.g. from concatenating two write_analyses() outputs); every
instance's lines are concatenated in file order before being split back
into per-sentence trios, the same merge-by-label convention the other
three blocks use.

MODEL= is a single value for the whole call, written on every sentence's
own entry rather than once for the file, since '#!LM' entries are only
ever grouped by sentence, not by call. CONTEXT= is a sentence-style
identifier, not the sentence's surface text: 'CONTEXT1.ID1-CONTEXT2.ID2',
where CONTEXT1/ID1 are the sentence's first token's own citation and id
and CONTEXT2/ID2 are its last token's -- e.g. 'Aeneid 1.1.t0-Aeneid
1.1.t4' -- the same first_token/last_token pair #!sentences itself
records for that sentence, just spelled as one dash-joined string instead
of two separate pipe-delimited columns; a token with no citation renders
its half with an empty string before the '.' (e.g. '.t5-.t9'). REASONING=
is that sentence's own reasoning text, with any internal newlines/
repeated whitespace collapsed to single spaces before writing, since
(like every other field in this format) a single '#!LM' line can't
itself contain one. Unlike the pipe-delimited blocks' `_field()` check,
a MODEL=/CONTEXT=/REASONING= line has nowhere to put a literal '|'
either way, so '|' is not rejected here -- only a literal newline is
(and REASONING='s own collapsing means one should never actually reach
that check in practice).

Why sentences/verbalunits/tokengraph aren't each self-contained: neither
VerbalExpression nor TokenAnalysis carries its own citation (only the
pre-analysis Token does -- see models.py's own note on why), and token ids
are global across a whole multi-sentence, multi-citation passage rather
than restarting per sentence. So `sentences` is what actually supplies
"context" (Token.citation) for a given token id, plus each sentence's own
boundaries; write_analyses() looks up every tokengraph/verbalunits row's
context by matching its id against `sentences`' own tokens, rather than
requiring TokenAnalysis/VerbalExpression to carry a redundant copy.

Round-tripping sentence boundaries back out of the file relies on one
invariant: the #!tokens block's row order is the same overall reading
order `sentences` implies when its tokens are read sentence-by-sentence,
token-by-token (exactly what combined_tokengraph() already assumes when
concatenating multiple sentences' tokengraphs -- see pipeline.py). Given
that, a sentence's tokens are recovered by finding its first_token/
last_token ids' *positions* in that row order and slicing between them,
rather than by parsing or sorting id strings -- ids are treated as opaque,
matching how models.py itself only guarantees they're "stable" and
"globally unique", not that they follow any particular numbering scheme.
write_analyses() checks this invariant itself and returns a warning (not
an error -- the file is still written) for any sentence whose own token
ids don't form a contiguous, matching-order run in the given tokengraph;
a file written with such a warning may not round-trip its sentence
boundaries correctly through read_analyses().

Field encoding: None serializes as an empty field (two adjacent '|'s, or
an empty field at the start/end of a line) and parses back as None --
this is the normal case for many fields (e.g. Token.citation is None for
any citation-free caller, and most tokens have no lemma/verbalunitid/
relatedtoken*/relationship* at all, per syntax_model.md's "Incomplete
status"). The literal sentinel string 'root' (an independent verb's own
relatedtoken1, per syntax_model.md) is written and read back verbatim,
like any other non-None string value -- it is never confused with an
empty/None field. Every field value is validated at write time to
contain neither '|' nor a newline (this format has no escaping mechanism
for either); Latin surface text/lemmas are not expected to ever contain
either character, so this is a defensive check, not an expected case.

Implied/elided tokens (tokentype in IMPLIED_TOKENTYPES -- 'implied sum',
'continued discourse', or 'implied subject'; see models.py's TokenAnalysis)
round-trip like any other #!tokens row -- their `text` column is empty,
same as any other None field, and reads back as None (not ''), same as
every other optional column. But they're excluded from a sentence's own
reconstructed `tokens` list in both directions: write_analyses() ignores
them when checking a sentence's tokens form a contiguous run in
`tokengraph`, and read_analyses() skips them when rebuilding each
Sentence's `tokens` -- since an implied token was never part of the
original per-sentence token list segmentation produced, only something
the analysis stage added afterward.

read_analyses() is deliberately strict, not "degrade visibly" like
tokengraph_to_mermaid()'s or compute_subordination_depths()'s warnings-
returning functions: a missing block, a header line that doesn't match
exactly, a wrong column count, a token id referenced by #!sentences or
#!verbal_units but absent from #!tokens, or a #!sentences/#!verbal_units
row whose own context column disagrees with what #!tokens recorded for
that same id, all raise ValueError immediately rather than silently
reconstructing something partial or wrong. '#!LM' shares this strictness
where it applies -- a line count that isn't a multiple of 3, a line
missing its expected MODEL=/CONTEXT=/REASONING= prefix, or a number of
entries that doesn't match the number of reconstructed sentences, all
raise -- but being entirely optional is itself not an error: zero '#!LM'
blocks in the file is valid and reads back as an empty list, not a
missing-block error like the other three would give (see "The #!LM
block" above). read_analyses() does not, however, cross-check a '#!LM'
entry's own CONTEXT= against the tokens/citations #!tokens and
#!sentences already establish -- it's read back verbatim, trusted as a
human/log-facing record rather than validated structural data. The whole
point of this format
is a faithful round trip; a malformed file should fail loudly and
specifically (naming the line and the problem) rather than hand back
subtly incorrect objects.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from .models import IMPLIED_TOKENTYPES, Sentence, Token, TokenAnalysis, VerbalExpression

SENTENCES_LABEL = "#!sentences"
VERBAL_UNITS_LABEL = "#!verbal_units"
TOKENS_LABEL = "#!tokens"
LM_LABEL = "#!LM"

SENTENCES_HEADER = "context_begin|first_token|context_end|last_token"
VERBAL_UNITS_HEADER = "context|token|syntactic_type|semantic_type"
TOKENS_HEADER = (
    "context|id|tokentype|text|lemma|verbalunit|"
    "related1|relationship1|related2|relationship2"
)

_EXPECTED_HEADERS = {
    SENTENCES_LABEL: SENTENCES_HEADER,
    VERBAL_UNITS_LABEL: VERBAL_UNITS_HEADER,
    TOKENS_LABEL: TOKENS_HEADER,
}

# '#!LM' has no fixed header line (see the module docstring's "The #!LM
# block") -- each entry is three lines, each introduced by one of these
# inline prefixes instead of a pipe-delimited column.
_LM_MODEL_PREFIX = "MODEL="
_LM_CONTEXT_PREFIX = "CONTEXT="
_LM_REASONING_PREFIX = "REASONING="

_WHITESPACE_RUN = re.compile(r"\s+")


class LMInfo(NamedTuple):
    """One sentence's '#!LM' entry (see the module docstring) -- which
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
    """Render one '#!LM' MODEL=/CONTEXT=/REASONING= value: None -> '', any
    other string verbatim -- after checking it contains no newline. Unlike
    `_field()`, a '|' is not rejected here: a '#!LM' line isn't
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
    '#!LM's REASONING= value, which this format can only store as one
    line."""
    return _WHITESPACE_RUN.sub(" ", value).strip()


def _sentence_context_identifier(sentence: "Sentence") -> str:
    """Build one sentence's '#!LM' CONTEXT= value: a sentence-style
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

    `model`/`reasoning` are optional and control the '#!LM' block (see the
    module docstring's "The #!LM block"): omit both (the default) to skip
    '#!LM' entirely, exactly reproducing this function's pre-'#!LM'
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
    nothing to derive '#!LM's CONTEXT= from either), if any field value
    contains '|' or a newline (see `_field`), or if `reasoning` is given
    with a different number of entries than `sentences`.
    """
    warnings: List[str] = []

    if reasoning is not None and len(reasoning) != len(sentences):
        raise ValueError(
            f"`reasoning` has {len(reasoning)} entr"
            f"{'y' if len(reasoning) == 1 else 'ies'}, but there "
            f"{'is' if len(sentences) == 1 else 'are'} {len(sentences)} "
            "sentence(s) -- '#!LM' needs exactly one reasoning entry per "
            "sentence"
        )

    id_to_citation: Dict[str, Optional[str]] = {}
    for sentence in sentences:
        for tok in sentence.tokens:
            id_to_citation[tok.id] = tok.citation

    # Implied tokens (tokentype in IMPLIED_TOKENTYPES) never appear in any sentence's
    # own `tokens` list by design (see the module docstring's note above)
    # -- so having no recorded citation is expected and correct for them,
    # not the kind of anomaly the "not found among the given sentences'
    # tokens" warning below exists to flag.
    implied_ids = {tok.id for tok in tokengraph if tok.tokentype in IMPLIED_TOKENTYPES}

    tg_index = {tok.id: i for i, tok in enumerate(tokengraph)}

    lines: List[str] = []

    if reasoning is not None:
        lines.append(LM_LABEL)
        for s_idx, sentence in enumerate(sentences):
            if not sentence.tokens:
                raise ValueError(
                    f"sentence at index {s_idx} has no tokens -- cannot "
                    "derive the '#!LM' block's CONTEXT= for an empty "
                    "sentence"
                )
            where = f"'#!LM' entry for sentence {s_idx}"
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
        if not sentence.tokens:
            raise ValueError(
                f"sentence at index {s_idx} has no tokens -- cannot derive "
                "first_token/last_token for an empty sentence"
            )
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
            # Implied tokens (tokentype in IMPLIED_TOKENTYPES) were never part of the
            # original per-sentence `tokens` list -- they're synthesized by
            # analysis itself -- so exclude them here before comparing, or
            # every sentence containing one would spuriously warn.
            actual_ids = [
                tok.id
                for tok in tokengraph[first_pos : last_pos + 1]
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
                    _field(vu.semantic_type, where=where),
                ]
            )
        )

    lines.append("")
    lines.append(TOKENS_LABEL)
    lines.append(TOKENS_HEADER)
    for tok in tokengraph:
        if tok.id not in id_to_citation and tok.id not in implied_ids:
            warnings.append(
                f"token {tok.id!r} not found among the given sentences' "
                "tokens -- writing an empty context for it"
            )
        where = f"#!tokens row for {tok.id}"
        lines.append(
            "|".join(
                [
                    _field(id_to_citation.get(tok.id), where=where),
                    _field(tok.id, where=where),
                    _field(tok.tokentype, where=where),
                    _field(tok.token, where=where),
                    _field(tok.lemma, where=where),
                    _field(tok.verbalunitid, where=where),
                    _field(tok.relatedtoken1, where=where),
                    _field(tok.relationship1, where=where),
                    _field(tok.relatedtoken2, where=where),
                    _field(tok.relationship2, where=where),
                ]
            )
        )

    return "\n".join(lines) + "\n", warnings


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
    '#!LM' block exactly as described there -- omit both to skip it.

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
    then the optional per-sentence '#!LM' record of what produced them).

    Each of the three required block labels may appear more than once in
    `path` (see the module docstring) -- every instance contributes its
    own rows, in file order, to that label's combined row list, as if the
    file were the concatenation of however many separate write_analyses()/
    serialize_analyses() outputs it actually is. '#!LM' may repeat the
    same way.

    `lm_infos` is `[]` if `path` has no '#!LM' block at all (every file
    written before this block existed, or any file written without
    passing `reasoning` to write_analyses()/serialize_analyses(), reads
    back exactly as before) -- otherwise it's one `LMInfo` per sentence,
    aligned with `sentences` by position, same as `tokengraph`/
    `verbalunits` are conceptually aligned with `sentences` via token ids.

    Raises ValueError, naming the offending line and problem, for anything
    that isn't a faithful, internally-consistent file written by
    write_analyses() -- see this module's own docstring for exactly what's
    checked, including '#!LM's own narrower checks (a line count that
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
    # must repeat its own header line too. '#!LM' is the one exception: it
    # has no header line at all (see the module docstring), so a '#!LM'
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

        if line == LM_LABEL or line in _EXPECTED_HEADERS:
            if awaiting_header:
                raise ValueError(
                    f"line {line_no}: block {current_label!r} has a label "
                    "line but no header line before the next block starts"
                )
            current_label = line
            seen_labels.add(line)
            awaiting_header = line != LM_LABEL
            continue

        if current_label is None:
            raise ValueError(
                f"line {line_no}: data line {line!r} appears before any "
                "'#!' block label"
            )

        if awaiting_header:
            expected = _EXPECTED_HEADERS[current_label]
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

    for line_no, line in blocks[TOKENS_LABEL]:
        parts = line.split("|")
        if len(parts) != 10:
            raise ValueError(
                f"line {line_no}: #!tokens row has {len(parts)} columns, "
                f"expected 10: {line!r}"
            )
        (
            context,
            tok_id,
            tokentype,
            text,
            lemma,
            verbalunit,
            related1,
            relationship1,
            related2,
            relationship2,
        ) = parts
        if tok_id == "":
            raise ValueError(f"line {line_no}: #!tokens row has an empty id")
        if tok_id in id_to_citation:
            raise ValueError(f"line {line_no}: duplicate token id {tok_id!r} in #!tokens")

        tokengraph.append(
            TokenAnalysis(
                id=tok_id,
                token=_parse_optional(text),
                tokentype=tokentype,
                lemma=_parse_optional(lemma),
                verbalunitid=_parse_optional(verbalunit),
                relatedtoken1=_parse_optional(related1),
                relationship1=_parse_optional(relationship1),
                relatedtoken2=_parse_optional(related2),
                relationship2=_parse_optional(relationship2),
            )
        )
        id_to_citation[tok_id] = _parse_optional(context)
        row_order.append(tok_id)

    id_position = {tid: i for i, tid in enumerate(row_order)}

    # --- #!verbal_units ---
    verbalunits: List[VerbalExpression] = []
    for line_no, line in blocks[VERBAL_UNITS_LABEL]:
        parts = line.split("|")
        if len(parts) != 4:
            raise ValueError(
                f"line {line_no}: #!verbal_units row has {len(parts)} "
                f"columns, expected 4: {line!r}"
            )
        context, vu_id, syntactic_type, semantic_type = parts
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

        verbalunits.append(
            VerbalExpression(
                id=vu_id,
                syntactic_type=syntactic_type,
                semantic_type=semantic_type,
            )
        )

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

    # --- #!LM (optional) ---
    lm_raw = blocks[LM_LABEL]
    lm_infos: List[LMInfo] = []
    if lm_raw:
        if len(lm_raw) % 3 != 0:
            first_line_no = lm_raw[0][0]
            raise ValueError(
                f"line {first_line_no}: '#!LM' block has {len(lm_raw)} "
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
                    f"{_LM_MODEL_PREFIX!r} in the '#!LM' block, got "
                    f"{model_line!r}"
                )
            if not context_line.startswith(_LM_CONTEXT_PREFIX):
                raise ValueError(
                    f"line {context_line_no}: expected a line starting "
                    f"with {_LM_CONTEXT_PREFIX!r} in the '#!LM' block, got "
                    f"{context_line!r}"
                )
            if not reasoning_line.startswith(_LM_REASONING_PREFIX):
                raise ValueError(
                    f"line {reasoning_line_no}: expected a line starting "
                    f"with {_LM_REASONING_PREFIX!r} in the '#!LM' block, "
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
                f"'#!LM' block has {len(lm_infos)} "
                f"entr{'y' if len(lm_infos) == 1 else 'ies'}, but "
                f"#!sentences reconstructed {len(sentences)} sentence(s) -- "
                "'#!LM' entries are recorded one per sentence, so these "
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

    One consequence of using [first, last] *real* token positions as the
    slice boundary, shared with read_analyses()'s own sentence
    reconstruction: an implied token placed AFTER a sentence's last real
    token (rather than nested between two real tokens) falls just outside
    that slice, since there's no further real token of the same sentence
    to bound it from above -- e.g. a one-real-token sentence like "Rara
    [sunt]." (see tests/test_serialization.py's
    test_split_excludes_a_trailing_implied_token_past_the_sentences_last_real_token).
    An implied token nested between two real tokens of the same sentence
    is included as expected; only this specific trailing case isn't.

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
        sentence_tokengraph = tokengraph[start : end + 1]
        sentence_ids = {tok.id for tok in sentence_tokengraph}
        sentence_verbalunits = [vu for vu in verbalunits if vu.id in sentence_ids]
        result.append((sentence_tokengraph, sentence_verbalunits))

    return result
