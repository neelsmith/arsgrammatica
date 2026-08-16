"""
Compares SyntaxAnalysis's performance across several candidate task models
-- by default, a spread of openly-licensed, open-weight models available on
Hugging Face -- to help decide which ones (if any) could realistically
replace the Claude Opus model this program was developed against.

WHY THIS SCRIPT EXISTS
-----------------------
"Can model X run this program" is really two separate questions, and this
script tries to answer both, per candidate:

  1. Zero-shot: does the model do anything useful with the SAME
     instructions (SyntaxAnalysis's docstring) that were written and tuned
     against Opus, with no optimization of its own?
  2. Optimized: if GEPA is allowed to rewrite the instructions specifically
     for this model, how much of the gap (if any) closes?

A model that's mediocre at (1) but closes most of the gap at (2) is a much
better candidate than one that's mediocre at both -- the latter suggests a
real capability ceiling, not just a prompting mismatch. Skip (2) entirely
with --skip-gepa for a much cheaper first pass across every candidate
before spending a GEPA budget on any of them.

HELD-OUT EVALUATION
--------------------
optimize_gepa.py trains (and, since it passes no valset, also does Pareto
tracking) against ALL of tests/fixtures/gold_examples.py's GOLD_EXAMPLES --
a reasonable choice for tuning one model, but it makes cross-model
comparison unreliable: a model's post-GEPA score would partly reflect how
well its own optimized prompt fits the very examples it's judged on. This
script instead holds out a fixed slice (HELD_OUT_SLUGS below) that NO
candidate's GEPA run ever trains against -- every candidate is optimized
against the same remaining trainset and scored against the same untouched
held-out set, so scores are actually comparable across models. The
held-out slice is deliberately stratified: a plain independent clause, a
subordinating-conjunction and a relative-pronoun dependent clause, a
coordinated-verb pair, an indirect statement, a circumstantial participle,
a depth-2 nesting case, and the three newest relations (apposition,
indirect question, complementary infinitive) -- so a low held-out score
can be traced to a specific construction, not just "worse overall."

SUB-SCORES, NOT JUST THE BLENDED NUMBER
-----------------------------------------
arsgrammatica.gepa_metric.syntax_metric() returns a single blended score,
but also (see that module) the three dimensions it blends: field_score
(tokentype/lemma/verbalunitid), relation_score (the actual dependency
relations -- weighted highest, 0.5, since they're the heart of the
scheme), and vu_score (verbal-expression classification). This script
reports all three per candidate, since a model that nails field_score but
collapses on relation_score is failing at multi-hop structural reasoning
specifically -- a different (and probably less prompt-fixable) problem
than a model that's just generally worse across the board.

WHAT THIS SCRIPT DOES NOT DO
------------------------------
- It doesn't check malformed-output rate (validate() / the
  find_unanchored_coordinated_verbs() heuristic) -- a model that frequently
  produces referentially-broken output (invented ids, reused 'root', etc.)
  will already show up as a low relation_score/field_score here, but if you
  want the malformed-output rate as its own number, run validate() over
  each candidate's raw predictions yourself; it wasn't folded in here to
  keep this script's scope to "what does syntax_metric already measure."
- It doesn't tune the CANDIDATES list to whatever's cheapest or fastest --
  see the CANDIDATES section below for what's included and why, and treat
  it as a starting point, not a fixed roster.

CANDIDATE MODELS
-----------------
Every candidate below is specified as a litellm-style model string using
the "huggingface/<org>/<repo>" convention (see
https://docs.litellm.ai/docs/providers/huggingface and
https://huggingface.co/docs/inference-providers) -- this routes through
Hugging Face's own Inference Providers layer (which in turn dispatches to
whichever backend -- Together, Fireworks, Sambanova, etc. -- actually
serves that checkpoint), authenticated with a Hugging Face access token
that has Inference Providers access. That's a DIFFERENT credential from
the API_KEY/API_BASE this repo's other scripts use for the school's
litellm proxy -- see HUGGINGFACE_API_KEY below.

Model availability on Hugging Face's open-weight side moves fast (new
generations supersede old ones every few months), and not every model
listed on the Hub is actually being served by a free/serverless Inference
Provider at any given moment -- treat CANDIDATES as a snapshot worth
checking against https://huggingface.co/docs/inference-providers and each
model's own Hub page before a real run, not a guarantee. Some entries
below may need an explicit provider suffix
("huggingface/together/org/repo") or a dedicated Inference Endpoint (set
via that candidate's own api_base_env) instead of the bare "huggingface/"
form, depending on how that checkpoint is currently being served.

Swap CANDIDATES for whatever's actually available and worth testing when
you run this -- newer generations (e.g. later Qwen, Gemma, or DeepSeek
releases than what's listed here) may well have shipped by the time you
read this file.

ENVIRONMENT
------------
Needs a Hugging Face access token in .env:

    HUGGINGFACE_API_KEY=hf_...

(a token with Inference Providers access -- see
https://huggingface.co/settings/tokens). Some candidates may specify their
own api_key_env/api_base_env if they need a different credential or a
dedicated endpoint instead.

GEPA's reflection model (the LM that reads syntax_metric's feedback and
proposes better instructions) is kept FIXED across every candidate --
defaulting to this repo's already-configured main model (Opus, via
API_BASE/MODEL/API_KEY, same as optimize_gepa.py), not each small
candidate reflecting on its own mistakes. The question this script answers
is "can a good optimizer lift this model's score," not "can this model
optimize itself" -- and GEPA's own docs recommend a strong reasoning model
for reflection regardless of the task model being tuned. Override with
REFLECTION_MODEL (and REFLECTION_API_BASE/REFLECTION_API_KEY if they
differ), exactly like optimize_gepa.py.

USAGE
------
    python model_bakeoff.py --skip-gepa                  # cheap first pass: zero-shot only, every candidate
    python model_bakeoff.py                               # zero-shot + --auto light GEPA pass, every candidate
    python model_bakeoff.py --auto medium
    python model_bakeoff.py --max-metric-calls 40
    python model_bakeoff.py --candidates "llama-3.1-8b" "gpt-oss-20b"   # only these candidates
    python model_bakeoff.py --min-baseline-to-optimize 0.3   # skip GEPA for candidates that can't clear 0.3 zero-shot
    python model_bakeoff.py --out results.csv

Expect this to make real API calls against whatever provider serves each
candidate, plus the reflection model's calls (unless --skip-gepa). Start
with --skip-gepa and a couple of candidates before running the full
roster with GEPA enabled.
"""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import dspy
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# Reuse syntaxer_main.py's own .env-reading helper rather than duplicating it.
sys.path.insert(0, str(Path(__file__).parent))
from syntaxer_main import _env  # noqa: E402

# tests/ isn't an installed package -- add it to sys.path the same way
# pytest and optimize_gepa.py do, so "from fixtures.gold_examples import
# GOLD_EXAMPLES" and "from conftest import tokens_from_canned_answer"
# resolve the same way they do everywhere else in this repo.
sys.path.insert(0, str(Path(__file__).parent / "tests"))
from conftest import tokens_from_canned_answer  # noqa: E402
from fixtures.gold_examples import GOLD_EXAMPLES  # noqa: E402

from arsgrammatica.gepa_metric import syntax_metric
from arsgrammatica.latin_syntax_dspy import SyntaxAnalysis
from arsgrammatica.models import TokenAnalysis, VerbalExpression


# ---------------------------------------------------------------------------
# Candidate models
# ---------------------------------------------------------------------------
#
# label            -- short name used in output and --candidates filtering
# model             -- litellm-style model string
# family / tier     -- for grouping/reading the report, not used functionally
# notes             -- why this one's here
# api_key_env       -- env var holding this candidate's API key (default:
#                      HUGGINGFACE_API_KEY); override per-candidate if a
#                      given checkpoint needs a different provider/token
# api_base_env      -- optional env var for a custom api_base (a specific
#                      Inference Providers route, or a dedicated Inference
#                      Endpoint URL); omitted entries let litellm resolve
#                      "huggingface/..." on its own
#
# Chosen to span roughly 4B to 120B+ across several major open-weight
# families, plus one reasoning-distilled model at the same size as its
# plain counterpart (deepseek-r1-distill-llama-8b vs. llama-3.1-8b) to see
# whether chain-of-thought distillation specifically helps on this kind of
# multi-hop structural-reasoning task. Left out for now, but worth adding
# once you've confirmed current Inference Providers availability: newer
# generations in each family (e.g. later Qwen/Gemma/Mistral/DeepSeek
# releases) that may have shipped since this file was written, and very
# large frontier-scale open-weight MoE models (Llama 4 Maverick, DeepSeek
# V3-class, Kimi K2-class, GLM-4-class) -- those are less "smaller model
# I could plausibly self-host or run cheaply" and more "another frontier
# lab's model," which is a different question than the one this script is
# built to answer.
CANDIDATES = [
    dict(
        label="phi-4-mini",
        model="huggingface/microsoft/Phi-4-mini-instruct",
        family="Microsoft Phi",
        tier="~4B",
        notes="Smallest candidate here -- a floor for 'can a tiny model do this at all'.",
    ),
    dict(
        label="llama-3.2-3b",
        model="huggingface/meta-llama/Llama-3.2-3B-Instruct",
        family="Meta Llama",
        tier="~3B",
        notes="Even smaller than phi-4-mini; mainly useful to confirm the floor rather than as a serious candidate.",
    ),
    dict(
        label="llama-3.1-8b",
        model="huggingface/meta-llama/Llama-3.1-8B-Instruct",
        family="Meta Llama",
        tier="~8B",
        notes="Widely used small-model baseline; lots of prior art on its structured-output behavior elsewhere.",
    ),
    dict(
        label="deepseek-r1-distill-llama-8b",
        model="huggingface/deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        family="DeepSeek (R1 distill)",
        tier="~8B",
        notes="Same size as llama-3.1-8b -- a direct test of whether reasoning-distillation "
              "specifically helps a multi-hop structural task like this one.",
    ),
    dict(
        label="qwen-8b",
        model="huggingface/Qwen/Qwen2.5-7B-Instruct",
        family="Alibaba Qwen",
        tier="~7B",
        notes="A third distinct family at the same rough tier as the two Llama-based 8B entries. "
              "Check for a newer Qwen generation at this size before running -- Qwen's release "
              "cadence is fast and this may already be superseded.",
    ),
    dict(
        label="gpt-oss-20b",
        model="huggingface/openai/gpt-oss-20b",
        family="OpenAI (open weights)",
        tier="~20B",
        notes="Apache-2.0, native reasoning-effort control -- worth comparing against the "
              "8B reasoning distill above to see whether the jump in size matters more than "
              "the distillation did.",
    ),
    dict(
        label="mistral-small-24b",
        model="huggingface/mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        family="Mistral AI",
        tier="~24B",
        notes="A fourth family, at a size tier between gpt-oss-20b and the 70B-class entries below.",
    ),
    dict(
        label="llama-3.3-70b",
        model="huggingface/meta-llama/Llama-3.3-70B-Instruct",
        family="Meta Llama",
        tier="~70B",
        notes="The largest dense (non-MoE) open-weight Llama generation available at this "
              "writing; the natural 'how far does more scale get you' data point.",
    ),
    dict(
        label="deepseek-r1-distill-llama-70b",
        model="huggingface/deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        family="DeepSeek (R1 distill)",
        tier="~70B",
        notes="Reasoning distillation at 70B -- pairs with deepseek-r1-distill-llama-8b to "
              "separate 'does distillation help' from 'does scale help'.",
    ),
    dict(
        label="gpt-oss-120b",
        model="huggingface/openai/gpt-oss-120b",
        family="OpenAI (open weights)",
        tier="~120B",
        notes="Largest candidate here. If even this doesn't close the gap with Opus on "
              "relation_score specifically, the ceiling is probably multi-hop structural "
              "reasoning depth, not raw parameter count within the 'openly available' range.",
    ),
]


# ---------------------------------------------------------------------------
# Held-out evaluation set
# ---------------------------------------------------------------------------

HELD_OUT_SLUGS = [
    "unit_verb_hercules_cum",                              # baseline: independent + one dependent clause
    "relative_pronoun_latini_cum_quibus",                  # relative pronoun + relatedtoken2 overflow
    "coordinating_conjunction_verbs_ille_hermionenque",    # paired verbs, word-order mismatch
    "indirect_statement_facturum_fuisse_dixit",            # indirect statement + auxiliary
    "circumstantial_participle_eum_advenientem",           # circumstantial participle
    "depth_two_cum_sciret_peccavisse_doluit",              # depth-2 nesting
    "coordinating_conjunction_dedit_et_dixit_esse",        # hardest regression fixture: 6 verbal expressions
    "apposition_neptunus_aegeus_filius",                   # newest relation: apposition
    "indirect_question_theseus_audit_quanta",              # newest relation: interrogative reuse of subordinating conjunction
    "complementary_infinitive_amphion_expugnare_vellet",   # newest relation: complementary infinitive
]


def _example_from(gold_example):
    tokens = tokens_from_canned_answer(gold_example.canned_answer)
    verbalunits = [VerbalExpression(**vu) for vu in gold_example.canned_answer["verbalunits"]]
    tokengraph = [TokenAnalysis(**tok) for tok in gold_example.canned_answer["tokengraph"]]
    return dspy.Example(
        slug=gold_example.slug,
        passage=gold_example.passage,
        tokens=tokens,
        verbalunits=verbalunits,
        tokengraph=tokengraph,
    ).with_inputs("passage", "tokens")


def build_split():
    """Partition GOLD_EXAMPLES into (trainset, heldout) by slug membership
    in HELD_OUT_SLUGS. Every candidate's GEPA run trains only on trainset;
    every candidate (baseline AND optimized) is scored only on heldout, so
    scores are comparable across candidates rather than each reflecting how
    well it memorized its own training slice."""
    held_out = set(HELD_OUT_SLUGS)
    known = {e.slug for e in GOLD_EXAMPLES}
    missing = held_out - known
    if missing:
        raise RuntimeError(
            f"HELD_OUT_SLUGS names slug(s) not found in GOLD_EXAMPLES: {sorted(missing)} "
            "-- gold_examples.py may have been renamed/removed since this list was written."
        )
    trainset, heldout = [], []
    for example in GOLD_EXAMPLES:
        bucket = heldout if example.slug in held_out else trainset
        bucket.append(_example_from(example))
    return trainset, heldout


# ---------------------------------------------------------------------------
# LM configuration
# ---------------------------------------------------------------------------

def _configure_candidate_lm(candidate):
    """Build a dspy.LM for one candidate. Resolves the API key from the env
    var the candidate names (default HUGGINGFACE_API_KEY), and an optional
    api_base override from the env var its api_base_env names, if any --
    letting litellm resolve the "huggingface/..." model string on its own
    otherwise."""
    api_key_env = candidate.get("api_key_env", "HUGGINGFACE_API_KEY")
    api_key = _env(api_key_env, api_key_env)
    if not api_key:
        raise RuntimeError(
            f"missing API key: set {api_key_env} in .env (a Hugging Face access token with "
            "Inference Providers access -- see https://huggingface.co/settings/tokens)"
        )
    kwargs = dict(model=candidate["model"], api_key=api_key)
    api_base_env = candidate.get("api_base_env")
    if api_base_env:
        api_base = _env(api_base_env, api_base_env)
        if api_base:
            kwargs["api_base"] = api_base
    return dspy.LM(**kwargs)


def _configure_reflection_lm():
    """The LM GEPA uses to read syntax_metric's feedback and propose better
    instructions -- fixed across every candidate (see this file's module
    docstring for why). Mirrors optimize_gepa.py's own
    _configure_reflection_lm() exactly, defaulting to this repo's main
    configured model (API_BASE/MODEL/API_KEY) unless REFLECTION_MODEL (and
    optionally REFLECTION_API_BASE/REFLECTION_API_KEY) override it."""
    reflection_model = _env("REFLECTION_MODEL", "REFLECTION_MODEL", None) or _env("MODEL", "MODEL")
    api_base = _env("REFLECTION_API_BASE", "REFLECTION_API_BASE", None) or _env(
        "API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm"
    )
    api_key = _env("REFLECTION_API_KEY", "REFLECTION_API_KEY", None) or _env("API_KEY", "API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key for the reflection LM. Set REFLECTION_API_KEY or API_KEY in .env."
        )
    return dspy.LM(model=reflection_model, api_base=api_base, api_key=api_key)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_program(program, examples, lm):
    """Run `program` over every example under `lm` (scoped via
    dspy.context, not a global dspy.configure(), so looping over many
    candidates in one process never leaks one candidate's LM into the
    next), scoring each with syntax_metric(). Returns aggregate stats:
    mean/min/max of the blended score, the mean of each of the three
    sub-scores, total wall-clock seconds, how many LM calls this made, and
    total cost across those calls (None if the configured provider doesn't
    report per-call cost -- not every litellm provider does).

    A call that raises outright (a real model can fail a request entirely
    -- rate limit, timeout, output DSPy can't parse into the signature's
    fields at all) is scored as a flat zero across every dimension rather
    than crashing the whole bakeoff; which example failed and why is
    recorded in the returned "problems" dict for the caller to print or
    inspect.
    """
    scores, field_scores, relation_scores, vu_scores = [], [], [], []
    problems = {}
    start = time.perf_counter()
    history_start = len(lm.history)
    with dspy.context(lm=lm):
        for example in examples:
            try:
                pred = program(passage=example.passage, tokens=example.tokens)
                result = syntax_metric(example, pred)
            except Exception as exc:  # noqa: BLE001 -- a live LM call can fail in many ways; that's data, not a bug here
                scores.append(0.0)
                field_scores.append(0.0)
                relation_scores.append(0.0)
                vu_scores.append(0.0)
                problems[example.slug] = f"{type(exc).__name__}: {exc}"
                continue
            scores.append(result.score)
            field_scores.append(result.field_score)
            relation_scores.append(result.relation_score)
            vu_scores.append(result.vu_score)
    elapsed = time.perf_counter() - start

    calls = lm.history[history_start:]
    costs = [c.get("cost") for c in calls if isinstance(c, dict) and c.get("cost") is not None]
    total_cost = sum(costs) if costs else None

    return dict(
        n=len(examples),
        mean=statistics.fmean(scores),
        min=min(scores),
        max=max(scores),
        field_mean=statistics.fmean(field_scores),
        relation_mean=statistics.fmean(relation_scores),
        vu_mean=statistics.fmean(vu_scores),
        elapsed_s=elapsed,
        n_calls=len(calls),
        total_cost=total_cost,
        problems=problems,
    )


def _format_stats_line(stats):
    cost = f", ${stats['total_cost']:.4f}" if stats["total_cost"] is not None else ""
    return (
        f"mean={stats['mean']:.3f}  min={stats['min']:.3f}  max={stats['max']:.3f}  "
        f"fields={stats['field_mean']:.3f}  relations={stats['relation_mean']:.3f}  "
        f"verbal-expr={stats['vu_mean']:.3f}  ({stats['elapsed_s']:.1f}s, {stats['n_calls']} calls{cost})"
    )


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "label", "model", "family", "tier", "stage",
    "n", "mean", "min", "max", "field_mean", "relation_mean", "vu_mean",
    "elapsed_s", "n_calls", "total_cost", "error",
]


def _write_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in _CSV_FIELDS})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare SyntaxAnalysis across candidate task models on a held-out gold-example slice."
    )
    parser.add_argument(
        "--candidates", nargs="*", default=None, metavar="LABEL",
        help="Only run candidates with these labels (default: every entry in CANDIDATES).",
    )
    parser.add_argument(
        "--skip-gepa", action="store_true",
        help="Only run the zero-shot baseline pass for every candidate -- a much cheaper first "
             "filter before spending a GEPA budget on any of them.",
    )
    budget = parser.add_mutually_exclusive_group()
    budget.add_argument(
        "--auto", choices=["light", "medium", "heavy"], default="light",
        help="dspy.GEPA's auto budget preset, applied per candidate (default: %(default)s). Ignored with --skip-gepa.",
    )
    budget.add_argument(
        "--max-metric-calls", type=int, default=None,
        help="Exact per-candidate GEPA call budget instead of --auto. Ignored with --skip-gepa.",
    )
    parser.add_argument(
        "--min-baseline-to-optimize", type=float, default=0.0,
        help="Skip a candidate's GEPA pass (but still report its baseline) if its zero-shot mean "
             "score on the held-out set is below this threshold -- avoids spending a GEPA budget "
             "on a model that can't even follow the output contract. Default: 0.0 (never skip).",
    )
    parser.add_argument(
        "--out", default="model_bakeoff_results.csv",
        help="Where to write the full results table (default: %(default)s).",
    )
    args = parser.parse_args()

    trainset, heldout = build_split()
    print(
        f"{len(trainset)} training fixtures, {len(heldout)} held-out fixtures "
        "(never used for any candidate's GEPA run).\n"
    )

    candidates = CANDIDATES
    if args.candidates:
        wanted = set(args.candidates)
        candidates = [c for c in CANDIDATES if c["label"] in wanted]
        unknown = wanted - {c["label"] for c in candidates}
        if unknown:
            raise SystemExit(
                f"Unknown candidate label(s): {sorted(unknown)} -- see CANDIDATES in this file "
                "for valid labels."
            )

    reflection_lm = None if args.skip_gepa else _configure_reflection_lm()

    rows = []
    for candidate in candidates:
        print(f"=== {candidate['label']} ({candidate['model']}) ===")
        try:
            task_lm = _configure_candidate_lm(candidate)
        except RuntimeError as exc:
            print(f"  skipped: {exc}\n")
            rows.append(dict(candidate, stage="skipped", error=str(exc)))
            continue

        baseline_program = dspy.ChainOfThought(SyntaxAnalysis)
        baseline = _score_program(baseline_program, heldout, task_lm)
        print(f"  baseline (zero-shot): {_format_stats_line(baseline)}")
        for slug, problem in baseline["problems"].items():
            print(f"    {slug}: {problem}")
        rows.append(dict(candidate, stage="baseline", **{k: v for k, v in baseline.items() if k != "problems"}))

        if args.skip_gepa:
            print()
            continue

        if baseline["mean"] < args.min_baseline_to_optimize:
            print(
                f"  baseline below --min-baseline-to-optimize ({args.min_baseline_to_optimize}) "
                "-- skipping GEPA for this candidate.\n"
            )
            continue

        optimizer_kwargs = dict(
            metric=syntax_metric,
            reflection_lm=reflection_lm,
            track_stats=True,
            log_dir=str(Path(__file__).parent / "gepa_logs" / candidate["label"]),
        )
        if args.max_metric_calls is not None:
            optimizer_kwargs["max_metric_calls"] = args.max_metric_calls
        else:
            optimizer_kwargs["auto"] = args.auto
        gepa = dspy.GEPA(**optimizer_kwargs)

        # A fresh ChainOfThought instance per candidate -- NOT the shared
        # module-level `analyze` from latin_syntax_dspy.py -- so optimizing
        # one candidate's prompt never clobbers another's, and this script
        # never mutates the shared instance the rest of the package uses.
        optimize_program = dspy.ChainOfThought(SyntaxAnalysis)
        print("  running GEPA -- this makes many real LM calls (task + reflection model)...")
        with dspy.context(lm=task_lm):
            optimized = gepa.compile(student=optimize_program, trainset=trainset)

        optimized_stats = _score_program(optimized, heldout, task_lm)
        print(f"  after GEPA: {_format_stats_line(optimized_stats)}")
        for slug, problem in optimized_stats["problems"].items():
            print(f"    {slug}: {problem}")
        rows.append(
            dict(candidate, stage="optimized", **{k: v for k, v in optimized_stats.items() if k != "problems"})
        )

        out_path = Path(__file__).parent / f"optimized_{candidate['label']}.json"
        optimized.save(str(out_path))
        print(f"  saved optimized program to {out_path.name}\n")

    _write_csv(rows, args.out)
    print(f"Full results written to {args.out}")


if __name__ == "__main__":
    main()
