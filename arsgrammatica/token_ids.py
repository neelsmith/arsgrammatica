"""
Rewrites Token ids so they're stable and unique per SOURCE PASSAGE (a
CitedText's own citation), rather than merely unique within whatever one
`segment_sources()` call happened to produce them.

Why this exists: `segment_sources()`'s own ids are only "global" WITHIN one
call (see `segmentation_dspy.SegmentPassage`'s own docstring) -- they always
start back at `t0` for a fresh call. That's fine as long as every sentence
in a corpus goes through exactly one `segment_sources()` call, but as soon
as a corpus is split into smaller per-group calls (see
`passage_grouping.group_passages_by_sentence_boundary()` and its callers,
`utilities/tokenize_ctsdata.py` and `utilities/analyze_ctsdata_to_files.py`),
the SAME passage can end up with different ids depending purely on which
other passages happened to be grouped alongside it in that particular run --
which breaks DSPy's own LM response cache (the rendered prompt, ids and all,
is part of the cache key), so the same sentence analyzed two different ways
pays for two independent LM calls instead of sharing one cached result.

`assign_passage_scoped_ids()` fixes this by giving each citation its own
locally-numbered id sequence (t0, t1, t2, ... restarting at 0 for every
citation) and then baking that citation into the id string itself, so the
result is unique across the whole run (regardless of grouping) while still
being deterministic and IDENTICAL for a given passage no matter what run
produced it or what else was grouped with it.

For a citation shaped like a 5-part CTS URN
(`urn:cts:<textgroup>:<work>:<passage>`, the only shape `ctsdata.py`'s
`read_ctsdata()` ever accepts), the composite id is `f"{passage}.t{n}"` --
e.g. citation `urn:cts:latinLit:phi0474.phi016.omar:1` gives ids `1.t0`,
`1.t1`, .... This is deliberately just the URN's OWN final (passage)
segment, not the whole URN, on the assumption that every passage sharing one
run/corpus is drawn from the same work -- the whole point of trading the
earlier "globally unique across the corpus" renumbering scheme for this
shorter one. That assumption is checked, not just hoped for: if the same
passage segment ever turns up under two DIFFERENT work prefixes (the one
case where reusing just the final segment would silently collide), this
raises ValueError immediately rather than producing two different tokens
that quietly share an id.

A token whose citation ISN'T a 5-part CTS URN (including a citation-free
token, e.g. from `analyze_string()`'s single hand-typed passage with no
CitedText source at all) is left completely alone -- its id passes through
unchanged. There's no passage-scoped key to build for it, and since these
callers only ever have one passage in play at a time, the collision this
function exists to prevent can't arise for them anyway.
"""

from typing import Dict, List, Optional, Tuple

from .models import Sentence


def _cts_passage_key(citation: Optional[str]) -> Optional[Tuple[str, str]]:
    """Return `(work_prefix, passage)` if `citation` is a 5-part CTS URN
    (`urn:cts:<textgroup>:<work>:<passage>`, `ctsdata.py`'s own required
    shape) with a non-empty final segment, else None. `work_prefix` is the
    first four colon-separated parts joined back together (e.g.
    `urn:cts:latinLit:phi0474.phi016.omar`); `passage` is the fifth."""
    if citation is None:
        return None
    parts = citation.split(":")
    if len(parts) != 5 or parts[0] != "urn" or parts[1] != "cts":
        return None
    passage = parts[4]
    if passage == "":
        return None
    return ":".join(parts[:4]), passage


def assign_passage_scoped_ids(sentences: List[Sentence]) -> List[Sentence]:
    """Return a copy of `sentences` with every CTS-URN-citation token's `id`
    replaced by a passage-scoped composite id (`f"{passage}.t{n}"` -- see
    this module's own docstring), and every other token's id left exactly
    as it was.

    Each distinct passage segment gets its own `t0, t1, t2, ...` counter,
    assigned in the order that passage's tokens are first encountered
    across ALL of `sentences` (not per-sentence -- a passage whose text
    turns out to span more than one sentence keeps counting up rather than
    restarting). Two different tokens can therefore never collide: either
    they're in different passages (different composite id prefix) or the
    same passage (same prefix, but a strictly increasing local index).

    Raises ValueError, naming both work prefixes involved, if the same
    passage segment is ever seen under two different CTS works -- the one
    case where taking just a citation's final URN segment as the whole key
    would silently produce a real collision instead of a stable id. This
    checks the actual input rather than assuming every passage shares one
    work.

    `text` and `citation` are copied unchanged; only `id` changes, and only
    for tokens whose citation is a 5-part CTS URN.
    """
    work_by_passage: Dict[str, str] = {}
    next_index_by_passage: Dict[str, int] = {}

    renumbered: List[Sentence] = []
    for sentence in sentences:
        new_tokens = []
        for tok in sentence.tokens:
            key = _cts_passage_key(tok.citation)
            if key is None:
                new_tokens.append(tok)
                continue

            work_prefix, passage = key
            seen_work = work_by_passage.get(passage)
            if seen_work is None:
                work_by_passage[passage] = work_prefix
            elif seen_work != work_prefix:
                raise ValueError(
                    f"passage {passage!r} appears under two different CTS "
                    f"works ({seen_work!r} and {work_prefix!r}) -- "
                    "assign_passage_scoped_ids() assumes every passage in "
                    "one run belongs to the same work, so a passage's own "
                    "final URN segment can be trusted as its unique key; "
                    "that assumption doesn't hold here"
                )

            local_index = next_index_by_passage.get(passage, 0)
            next_index_by_passage[passage] = local_index + 1
            new_tokens.append(tok.model_copy(update={"id": f"{passage}.t{local_index}"}))

        renumbered.append(Sentence(tokens=new_tokens))

    return renumbered
