"""
Turn a real analysis -- the same `sentences`/`verbalunits`/`tokengraph`
triple serialize_analyses()/write_analyses() take (arsgrammatica/
serialization.py) -- into a `GoldExample` (see gold_examples.py), instead
of hand-writing a `canned_answer` dict from scratch the way every existing
GOLD_EXAMPLES entry so far has been written.

Intended workflow: run analyze_string()/analyze_sources() over new
passages, read over each result by hand, and for the ones that come out
correct, call gold_example_from_analysis() on that sentence's own
`sentences`/`result.verbalunits`/`result.tokengraph` to get a `GoldExample`
-- then format_gold_example_source() renders it as ready-to-paste Python
source in the same `_SOME_ANSWER = {...}` / `GoldExample(...)` shape every
other block in gold_examples.py already uses.

STRATEGIC NOTE -- trainset or held-out eval? See
gold_example_from_analysis()'s own docstring for the full argument; short
version: a *correct* analysis is, by definition, something the current
model/prompt already gets right, so harvesting it straight into
optimize_gepa.py's trainset (all of GOLD_EXAMPLES today, with no held-out
split at all) mostly just dilutes that trainset with an easy case GEPA
gets to self-grade against -- it doesn't teach the optimizer anything new.
Adding the harvested example to GOLD_EXAMPLES *and* to model_bakeoff.py's
HELD_OUT_SLUGS (or some other held-out set optimize_gepa.py comes to
respect) is the better default for most harvested examples: it grows a
real regression corpus that catches a future prompt/model change breaking
something that currently works, without inflating GEPA's own self-graded
trainset. The exception is a rare construction the model only sometimes
gets right, where locking in a good demonstration of a correct case IS
useful training signal -- that's exactly what BootstrapFewShot-style
training (model_bakeoff.py's "bootstrap" stage) already does on purpose.
"""

from typing import List, Optional

import dspy

from arsgrammatica.latin_syntax_dspy import validate
from arsgrammatica.models import Sentence, TokenAnalysis, VerbalExpression
from arsgrammatica.rendering import tokengraph_to_text

from .gold_examples import GoldExample

_PLACEHOLDER_REASONING = (
    "(reasoning not supplied to gold_example_from_analysis() -- fill in a "
    "real explanation of this analysis before treating this as more than "
    "a draft fixture)"
)


def _verbalunit_to_dict(vu: VerbalExpression) -> dict:
    """VerbalExpression has exactly 3 required fields, none optional -- so
    this is just an ordinary full dump, matching every existing
    canned_answer['verbalunits'] entry in gold_examples.py."""
    return {
        "id": vu.id,
        "syntactic_type": vu.syntactic_type,
        "semantic_type": vu.semantic_type,
    }


def _tokenanalysis_to_dict(tok: TokenAnalysis) -> dict:
    """TokenAnalysis -> the raw-dict shape gold_examples.py's
    canned_answer['tokengraph'] entries use: 'id'/'token'/'tokentype' are
    always present -- including 'token': None for an implied token
    (tokentype in IMPLIED_TOKENTYPES), which is a meaningful value, not an
    absent one -- but every other optional field (lemma, verbalunitid,
    relatedtoken1/2, relationship1/2) is OMITTED entirely when None,
    matching how every hand-written entry in gold_examples.py already
    looks (e.g. a bare punctuation token is just {"id": ..., "token":
    ..., "tokentype": "punctuation"}, never lemma=None etc. spelled out).
    """
    entry = {"id": tok.id, "token": tok.token, "tokentype": tok.tokentype}
    for field in (
        "lemma",
        "verbalunitid",
        "relatedtoken1",
        "relationship1",
        "relatedtoken2",
        "relationship2",
    ):
        value = getattr(tok, field)
        if value is not None:
            entry[field] = value
    return entry


def gold_example_from_analysis(
    slug: str,
    tags: List[str],
    sentences: List[Sentence],
    verbalunits: List[VerbalExpression],
    tokengraph: List[TokenAnalysis],
    *,
    passage: Optional[str] = None,
    reasoning: Optional[str] = None,
    skip_validation: bool = False,
) -> GoldExample:
    """Build a GoldExample from a real analysis's own objects -- the exact
    `sentences`/`verbalunits`/`tokengraph` triple serialize_analyses()/
    write_analyses() take, as produced by analyze_string()/
    analyze_sources() (+ combined_tokengraph(), and concatenating every
    result.verbalunits, if the passage was more than one sentence).

    `slug`/`tags` are yours to choose -- see gold_examples.py's own
    convention (a slug like "circumstantial_participle_eum_advenientem",
    tags naming the specific constructions this example is meant to
    cover).

    `passage` defaults to reconstructing the surface text directly from
    `tokengraph` via rendering.tokengraph_to_text() -- pass an explicit
    string instead if you'd rather preserve the exact original
    wording/whitespace you fed to analyze_string() than its
    reconstruction.

    `reasoning` defaults to an obvious placeholder string if omitted --
    canned_answer['reasoning'] is documentation for a human reader (it
    isn't consumed by optimize_gepa.py's or model_bakeoff.py's
    build_trainset()/build_split(), which read only verbalunits/
    tokengraph -- see conftest.py's tokens_from_canned_answer()), but
    every existing fixture has a real one; don't ship the placeholder in
    anything you actually add to GOLD_EXAMPLES.

    Unless `skip_validation` is True, this calls latin_syntax_dspy.
    validate() against every token in `sentences` before returning --
    the same referential-integrity check analyze_sources() runs on a live
    result -- and raises ValueError if it finds anything wrong, so a
    malformed analysis can't quietly become a fixture. This does NOT
    check the analysis is *correct* (validate() never does -- see its own
    docstring); that's still on you to judge before calling this at all,
    per "successful analyses" in the sense you already mean it.

    `sentences` is used only for that validation and (when `passage` is
    omitted) is not otherwise consulted -- this function does NOT split a
    multi-sentence `sentences` list into multiple GoldExamples; call it
    once per sentence yourself first if that's what you want
    (analyze_sources() already hands you sentences/results one per
    sentence).
    """
    tokengraph = list(tokengraph)
    verbalunits = list(verbalunits)

    if not tokengraph:
        raise ValueError("gold_example_from_analysis() needs a non-empty tokengraph")

    if not skip_validation:
        all_tokens = [tok for sentence in sentences for tok in sentence.tokens]
        problems = validate(
            all_tokens, dspy.Prediction(tokengraph=tokengraph, verbalunits=verbalunits)
        )
        if problems:
            raise ValueError(
                "gold_example_from_analysis(): validate() found problems with "
                "this analysis -- fix them (or pass skip_validation=True if "
                f"you really mean to harvest it anyway): {problems}"
            )

    resolved_passage = passage if passage is not None else tokengraph_to_text(tokengraph)

    canned_answer = {
        "reasoning": reasoning if reasoning is not None else _PLACEHOLDER_REASONING,
        "verbalunits": [_verbalunit_to_dict(vu) for vu in verbalunits],
        "tokengraph": [_tokenanalysis_to_dict(tok) for tok in tokengraph],
    }

    return GoldExample(
        slug=slug, passage=resolved_passage, tags=list(tags), canned_answer=canned_answer
    )


def _pylit(value) -> str:
    """A Python source literal for `value` -- prefers double quotes for
    strings (matching gold_examples.py's own style), falling back to
    single quotes or repr() only if the string itself needs it."""
    if value is None:
        return "None"
    if isinstance(value, str):
        if '"' not in value:
            return f'"{value}"'
        if "'" not in value:
            return f"'{value}'"
        return repr(value)
    return repr(value)


def _dict_literal(d: dict) -> str:
    return "{" + ", ".join(f"{_pylit(k)}: {_pylit(v)}" for k, v in d.items()) + "}"


def _list_literal(items) -> str:
    return "[" + ", ".join(_pylit(item) for item in items) + "]"


def format_gold_example_source(example: GoldExample, answer_var_name: str) -> str:
    """Render `example` as ready-to-paste Python source: a `_SOME_ANSWER =
    {...}` module-level dict literal, followed by the `GoldExample(...)`
    entry that references it -- the exact two-part shape every existing
    block in gold_examples.py already uses, so a harvested, hand-reviewed
    GoldExample can be pasted straight into that file (inside
    GOLD_EXAMPLES's own `[...]`, plus its own `_ANSWER` block above it)
    rather than transcribed by hand.

    `answer_var_name` is the module-level constant name to give the
    canned_answer dict (by convention, ALL_CAPS ending in `_ANSWER`, e.g.
    "_IMPLIED_SUM_OMNIA_PRAECLARA_ANSWER") -- this function doesn't
    enforce that convention, just uses whatever string you pass verbatim.

    This is a convenience for a human pasting/reviewing the result, not a
    guarantee of gold_examples.py's exact hand-wrapped formatting (long
    'reasoning' strings especially) -- re-read the pasted block once it's
    in gold_examples.py and re-wrap/word it by hand as needed, the same as
    any other fixture in that file.
    """
    answer_lines = [f"{answer_var_name} = {{"]
    answer_lines.append(f'    "reasoning": {_pylit(example.canned_answer["reasoning"])},')
    answer_lines.append('    "verbalunits": [')
    for vu in example.canned_answer["verbalunits"]:
        answer_lines.append(f"        {_dict_literal(vu)},")
    answer_lines.append("    ],")
    answer_lines.append('    "tokengraph": [')
    for tok in example.canned_answer["tokengraph"]:
        answer_lines.append(f"        {_dict_literal(tok)},")
    answer_lines.append("    ],")
    answer_lines.append("}")

    example_lines = [
        "GoldExample(",
        f"    slug={_pylit(example.slug)},",
        f"    passage={_pylit(example.passage)},",
        f"    tags={_list_literal(example.tags)},",
        f"    canned_answer={answer_var_name},",
        "),",
    ]

    return "\n".join(answer_lines) + "\n\n\n" + "\n".join(example_lines) + "\n"
