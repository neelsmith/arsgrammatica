"""
Optimizes latin_syntax_dspy.py's SentenceAnalysis prompt with dspy.GEPA,
using tests/fixtures/gold_examples.py's GOLD_EXAMPLES as the trainset and
arsgrammatica/gepa_metric.py's syntax_metric as the scoring/feedback
function.

This is a LIVE-LM script: unlike the pytest suite (entirely DummyLM-backed,
see TESTING.md), every trial here actually calls the configured task LM, plus
a reflection LM GEPA uses to read the metric's feedback and propose better
instructions. Budget is controlled by --auto (dspy's light/medium/heavy
presets -- default "light", the cheapest) or --max-metric-calls for an
exact call count. Expect this to run up real API usage against the
configured proxy; --auto light is meant as the "does this all work"
starting point before spending more on medium/heavy.

PULLING IN REAL-TEXT EVAL DATA (--eval-file/--eval-dir)
---------------------------------------------------------
tests/fixtures/gold_examples.py's GOLD_EXAMPLES is a small, hand-curated
set built to exercise every documented construction at least once -- great
for regression testing (see test_verbal_units.py etc.), but not the same
thing as a representative sample of real texts. If you've been running
analyze_string()/analyze_sources() over actual passages and saving the
ones you've hand-verified as correct (write_analyses()'s own format -- see
notes/serialization_formats.md), point --eval-file/--eval-dir at those
files to fold them into this script's own pool of examples, on top of
GOLD_EXAMPLES rather than instead of it. See
build_trainset_from_analysis_files()'s own docstring for exactly how a
saved file's sentences become dspy.Example objects.

This is a lower-friction alternative to tests/fixtures/harvest.py's
gold_example_from_analysis()/format_gold_example_source(), which hand-turns
one real analysis into pasteable GOLD_EXAMPLES source -- worth it for a
single fixture you want as a permanent, documented regression example
(with a real slug, tags, and reasoning), but not for folding in dozens or
hundreds of sentences at once just to give GEPA more to train/validate
against.

HOLDING OUT A REAL VALSET (--val-fraction)
---------------------------------------------
Previously, all gold examples were used as the trainset, and (per
dspy.GEPA's own behavior when valset=None) also as the Pareto-tracking
set -- a reasonable stopgap while the only available examples were the 17
in GOLD_EXAMPLES, but it meant GEPA was optimizing directly against the
only examples it was being judged on, with no guarantee the result
generalizes to new sentences. Now that --eval-file/--eval-dir make it easy
to grow the pool past a couple dozen examples, --val-fraction (default
0.2) shuffles the combined GOLD_EXAMPLES + harvested pool with a fixed
--seed and holds out that fraction as a genuine valset, passed to
dspy.GEPA separately from the trainset. Pass --val-fraction 0 to go back
to the old behavior (no held-out valset at all) if your pool is still too
small to split sensibly.

This is a different held-out mechanism from utilities/model_bakeoff.py's
own HELD_OUT_SLUGS: that one is a fixed, hand-picked, stratified slice of
GOLD_EXAMPLES used to compare different task MODELS against each other on
identical held-out sentences run after run; this one is a random split of
whatever pool this particular invocation was given, used only to give this
one GEPA run an honest generalization signal while it optimizes a single
model's prompt. Nothing here reads or writes HELD_OUT_SLUGS.

Usage:
    python utilities/optimize_gepa.py                       # --auto light (default)
    python utilities/optimize_gepa.py --auto medium
    python utilities/optimize_gepa.py --max-metric-calls 40
    python utilities/optimize_gepa.py --skip-baseline        # skip the pre-GEPA scoring pass
    python utilities/optimize_gepa.py --eval-file corpus/livy1.cex corpus/livy2.cex
    python utilities/optimize_gepa.py --eval-dir corpus/ --val-fraction 0.25

Needs the same .env as syntaxer_main.py (API_BASE/MODEL/API_KEY). Optionally
set REFLECTION_MODEL (and REFLECTION_API_BASE/REFLECTION_API_KEY, if they
differ) to use a different model for GEPA's own reflective step -- GEPA's
docs recommend a strong reasoning model specifically for reflection.
Without REFLECTION_MODEL set, the task model doubles as the reflection
model, which is a reasonable default for a first run but not a requirement.
"""

import argparse
import random
import sys
from pathlib import Path

import dspy

# utilities/ isn't the repo root -- add the root to sys.path (not just
# ".parent", now that this script itself lives one level deeper) so
# "import syntaxer_main" and "from arsgrammatica import ..." below resolve
# the same way they do for a script run straight from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))
# Reuse syntaxer_main.py's own .env-loading + LM-config helpers rather than
# duplicating them.
from syntaxer_main import _configure_lm, _env  # noqa: E402

# tests/ isn't an installed package -- add it to sys.path the same way
# pytest does (see pytest.ini's own comment about this) so
# "from fixtures.gold_examples import GOLD_EXAMPLES" and
# "from conftest import tokens_from_canned_answer" resolve the same way
# they do under pytest, without duplicating either helper here.
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from conftest import tokens_from_canned_answer  # noqa: E402
from fixtures.gold_examples import GOLD_EXAMPLES  # noqa: E402

from arsgrammatica.gepa_metric import syntax_metric
from arsgrammatica.latin_syntax_dspy import analyze
from arsgrammatica.models import TokenAnalysis, VerbalExpression
from arsgrammatica.rendering import tokengraph_to_text
from arsgrammatica.serialization import read_analyses, split_analysis_by_sentence


def build_trainset():
    """Turn every GoldExample in GOLD_EXAMPLES into a dspy.Example GEPA can
    train against: `passage`/`tokens` as inputs (matching SentenceAnalysis's
    own InputFields), `verbalunits`/`tokengraph` as the gold outputs
    arsgrammatica.gepa_metric.syntax_metric compares predictions to."""
    trainset = []
    for example in GOLD_EXAMPLES:
        tokens = tokens_from_canned_answer(example.canned_answer)
        verbalunits = [VerbalExpression(**vu) for vu in example.canned_answer["verbalunits"]]
        tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
        trainset.append(
            dspy.Example(
                passage=example.passage,
                tokens=tokens,
                verbalunits=verbalunits,
                tokengraph=tokengraph,
            ).with_inputs("passage", "tokens")
        )
    return trainset


def build_trainset_from_analysis_files(paths):
    """Load additional dspy.Example training/eval data from one or more
    saved analysis files (write_analyses()'s own pipe-delimited format --
    see notes/serialization_formats.md) of real texts you've analyzed and
    hand-verified as correct, to fold in alongside build_trainset()'s own
    GOLD_EXAMPLES-derived examples.

    Each file is read with read_analyses()/split_analysis_by_sentence() --
    the same machinery marimo/latin_syntaxer_review.py and
    utilities/analyses_to_dot_pngs.py already use to browse a saved
    analysis one sentence at a time -- rather than anything new. For each
    sentence: its own Sentence.tokens (the pre-analysis token list;
    implied/elided tokens were never part of it to begin with -- see
    serialization.py's own docstring) becomes the `tokens` input field
    directly, and `passage` is reconstructed from that sentence's own
    tokengraph slice via rendering.tokengraph_to_text() -- the same
    reconstruction tests/fixtures/harvest.py's gold_example_from_analysis()
    defaults to when no explicit passage is given.

    This does NOT verify a file's analyses are actually correct -- same
    caveat as gold_example_from_analysis()'s own docstring: judging that is
    still on you, before you ever save the file. It only checks that the
    file parses and each sentence's graph is well-formed enough to split.
    A file that fails either check is skipped, with a message on stderr,
    rather than aborting the whole run -- one bad file shouldn't cost you
    every other one.
    """
    examples = []
    for path in paths:
        try:
            tokengraph, verbalunits, sentences, _lm_infos = read_analyses(path)
        except (ValueError, OSError) as e:
            print(f"Skipping {path!r}: could not read it as a saved analysis: {e}", file=sys.stderr)
            continue

        try:
            sentence_slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)
        except ValueError as e:
            print(f"Skipping {path!r}: could not split it by sentence: {e}", file=sys.stderr)
            continue

        # zip() stops at whichever list is shorter -- same defensive
        # convention analyses_to_dot_pngs.py's own loop uses -- so a
        # split_analysis_by_sentence() result shorter than `sentences`
        # can't produce a mismatched pairing here.
        for sentence, (sentence_tokengraph, sentence_verbalunits) in zip(sentences, sentence_slices):
            if not sentence_tokengraph:
                continue
            examples.append(
                dspy.Example(
                    passage=tokengraph_to_text(sentence_tokengraph),
                    tokens=list(sentence.tokens),
                    verbalunits=sentence_verbalunits,
                    tokengraph=sentence_tokengraph,
                ).with_inputs("passage", "tokens")
            )
    return examples


def split_train_val(pool, val_fraction, seed):
    """Shuffle a COPY of `pool` deterministically (via `seed`) and split
    off `val_fraction` of it as a held-out valset -- the remainder is the
    trainset GEPA's reflective updates actually train against. Returns
    (trainset, valset).

    val_fraction=0 returns (list(pool), []) unchanged -- main() treats an
    empty valset as "pass valset=None to gepa.compile()", i.e. today's
    original behavior (GEPA reuses the whole trainset for Pareto tracking
    too). round(), not int(), so a small pool with a modest val_fraction
    still holds out its rounded share rather than truncating to zero
    whenever len(pool) * val_fraction isn't a whole number.

    This is an ordinary random split, not utilities/model_bakeoff.py's
    HELD_OUT_SLUGS (a fixed, hand-picked, stratified slice of GOLD_EXAMPLES
    used to keep cross-model comparisons apples-to-apples) -- see this
    script's own module docstring for why they're different mechanisms for
    different jobs.
    """
    if not 0.0 <= val_fraction < 1.0:
        raise ValueError(f"--val-fraction must be in [0, 1); got {val_fraction}")
    shuffled = list(pool)
    random.Random(seed).shuffle(shuffled)
    n_val = round(len(shuffled) * val_fraction)
    return shuffled[n_val:], shuffled[:n_val]


def _configure_reflection_lm(task_lm):
    """Build the LM GEPA uses to read syntax_metric's feedback and propose
    better instructions. Defaults to `task_lm` itself unless REFLECTION_MODEL
    is set in .env, in which case a separate dspy.LM is built for it (same
    API_BASE/API_KEY unless REFLECTION_API_BASE/REFLECTION_API_KEY override
    those too)."""
    reflection_model = _env("REFLECTION_MODEL", "REFLECTION_MODEL", None)
    if not reflection_model:
        return task_lm

    api_base = _env("REFLECTION_API_BASE", "REFLECTION_API_BASE", None) or _env(
        "API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm"
    )
    api_key = _env("REFLECTION_API_KEY", "REFLECTION_API_KEY", None) or _env("API_KEY", "API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key for the reflection LM. Set REFLECTION_API_KEY or API_KEY in .env."
        )
    return dspy.LM(model=reflection_model, api_base=api_base, api_key=api_key)


def _evaluate(program, dataset, label):
    """Run `program` over every example in `dataset`, score each with
    syntax_metric, and print a min/mean/max summary. Returns the list of
    per-example scores (not currently used by the caller beyond that
    summary, but handy to have if you want to inspect which sentences score
    worst). Prints a "(nothing to evaluate)" line instead of dividing by
    zero when `dataset` is empty -- e.g. an empty valset when
    --val-fraction 0."""
    if not dataset:
        print(f"{label}: (nothing to evaluate -- empty dataset)")
        return []
    scores = []
    for example in dataset:
        pred = program(passage=example.passage, tokens=example.tokens)
        scores.append(syntax_metric(example, pred).score)
    mean = sum(scores) / len(scores)
    print(f"{label}: mean={mean:.3f}  min={min(scores):.3f}  max={max(scores):.3f}  (n={len(scores)})")
    return scores


def main():
    parser = argparse.ArgumentParser(description="Optimize SentenceAnalysis's prompt with GEPA.")
    budget = parser.add_mutually_exclusive_group()
    budget.add_argument(
        "--auto",
        choices=["light", "medium", "heavy"],
        default="light",
        help="dspy's auto budget preset (default: %(default)s -- fewest LM calls).",
    )
    budget.add_argument(
        "--max-metric-calls",
        type=int,
        default=None,
        help="Exact LM-call budget instead of an --auto preset.",
    )
    parser.add_argument(
        "--out",
        default="optimized_syntax_analysis.json",
        help="Where to save the optimized program (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the pre-GEPA scoring pass (saves one live LM call per example).",
    )
    parser.add_argument(
        "--eval-file",
        nargs="+",
        default=[],
        metavar="PATH",
        help="Path(s) to saved analysis file(s) (write_analyses()'s own format) of "
             "real, hand-verified-correct text -- folded in alongside GOLD_EXAMPLES "
             "via build_trainset_from_analysis_files(). See this script's own module "
             "docstring.",
    )
    parser.add_argument(
        "--eval-dir",
        default=None,
        metavar="DIR",
        help="Directory of saved analysis files (every file directly in it, "
             "non-recursive) -- loaded the same way as --eval-file. Combine both if "
             "you like; both add to the same pool.",
    )
    parser.add_argument(
        "--val-fraction",
        type=float,
        default=0.2,
        help="Fraction of the combined GOLD_EXAMPLES + --eval-file/--eval-dir pool to "
             "hold out as a genuine valset passed to dspy.GEPA, split off with "
             "--seed (default: %(default)s). Pass 0 to go back to the old "
             "no-separate-valset behavior.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for the --val-fraction train/val split, so repeated runs "
             "over the same pool get the same split (default: %(default)s).",
    )
    args = parser.parse_args()

    task_lm = _configure_lm()
    reflection_lm = _configure_reflection_lm(task_lm)

    pool = build_trainset()
    print(f"Built {len(pool)} example(s) from tests/fixtures/gold_examples.py's GOLD_EXAMPLES.")

    eval_paths = list(args.eval_file)
    if args.eval_dir:
        eval_dir = Path(args.eval_dir)
        eval_paths += sorted(str(p) for p in eval_dir.iterdir() if p.is_file())
    if eval_paths:
        harvested = build_trainset_from_analysis_files(eval_paths)
        print(f"Loaded {len(harvested)} additional example(s) from {len(eval_paths)} --eval-file/--eval-dir file(s).")
        pool += harvested

    trainset, valset = split_train_val(pool, val_fraction=args.val_fraction, seed=args.seed)
    if valset:
        print(
            f"Split into {len(trainset)} trainset / {len(valset)} valset example(s) "
            f"(--val-fraction {args.val_fraction}, --seed {args.seed})."
        )
    else:
        print(
            f"No separate valset (--val-fraction {args.val_fraction}) -- GEPA will use "
            "the trainset for both reflective updates and Pareto-score tracking. See "
            "this script's module docstring for why that's no longer the only option."
        )

    if not args.skip_baseline:
        print()
        _evaluate(analyze, trainset, "Baseline (before GEPA), trainset")
        if valset:
            _evaluate(analyze, valset, "Baseline (before GEPA), valset")

    optimizer_kwargs = dict(
        metric=syntax_metric,
        reflection_lm=reflection_lm,
        track_stats=True,
        # gepa_logs/ stays at the repo root (matching .gitignore's own
        # "gepa_logs/" entry and model_bakeoff.py's identical convention),
        # not inside utilities/ -- .parent.parent, not .parent, now that
        # this script lives one level deeper.
        log_dir=str(Path(__file__).parent.parent / "gepa_logs"),
    )
    if args.max_metric_calls is not None:
        optimizer_kwargs["max_metric_calls"] = args.max_metric_calls
    else:
        optimizer_kwargs["auto"] = args.auto

    gepa = dspy.GEPA(**optimizer_kwargs)

    print("\nRunning GEPA -- this makes many real LM calls through the configured proxy.")
    optimized = gepa.compile(student=analyze, trainset=trainset, valset=valset or None)

    print()
    _evaluate(optimized, trainset, "Optimized (after GEPA), trainset")
    if valset:
        _evaluate(optimized, valset, "Optimized (after GEPA), valset")

    optimized.save(args.out)
    print(f"\nSaved the optimized program to {args.out}.")
    print(
        "To use it, right after `from arsgrammatica.latin_syntax_dspy import analyze`, call:\n"
        f"    analyze.load({args.out!r})\n"
        "before running analyze_string()/analyze_sources() -- see "
        "OPTIMIZING.md."
    )


if __name__ == "__main__":
    main()
