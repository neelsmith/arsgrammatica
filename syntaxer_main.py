"""
A runnable script to run the syntaxer module.
"""
 
# ---------------------------------------------------------------------------
# LM configuration
# ---------------------------------------------------------------------------
import argparse
from pathlib import Path
import os
 
import dspy
from dotenv import load_dotenv
 
 
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
 
 
def _env(name: str, fallback_name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    value = os.getenv(fallback_name)
    if value:
        return value
    return default
 
def _configure_lm():
    api_base = _env("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
    model = _env("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")

    # Distinguish "API_KEY isn't in .env at all" (a likely oversight -- keep
    # raising) from "API_KEY= is there but deliberately empty" (fine for a
    # local, unauthenticated model like Ollama -- see model_bakeoff.py's own
    # "ollama: no API key needed" comment for the same convention). _env()'s
    # own truthiness check can't tell these apart (both look like "falsy"),
    # so this checks os.environ directly instead.
    if "API_KEY" not in os.environ:
        raise RuntimeError(
            "Missing API key. Set API_KEY in your .env file -- an empty "
            "value (API_KEY=) is fine for a local model that doesn't need "
            "one, e.g. Ollama; this only checks that the line exists at all."
        )
    api_key = os.environ["API_KEY"]

    # Only pass api_key through when it's actually non-empty. dspy.LM/litellm
    # don't need one at all for a local Ollama daemon -- passing api_key=""
    # explicitly is unnecessary and, depending on the provider, can behave
    # differently than omitting it outright.
    lm_kwargs = dict(model=model, api_base=api_base)
    if api_key:
        lm_kwargs["api_key"] = api_key

    # Anthropic prompt caching: SyntaxAnalysis's system message (its own
    # instructions plus the TokenAnalysis/VerbalExpression field
    # descriptions) runs ~40K characters and is byte-identical on every
    # single call -- only the per-sentence user message actually changes.
    # Marking it with an ephemeral cache_control breakpoint lets a repeat
    # call within Anthropic's cache TTL reuse that whole block at ~10% of
    # its normal input-token price instead of paying full price every time
    # (see VISUALIZATION.md-adjacent discussion in the project chat history
    # -- there's no dedicated caching doc yet). litellm (which dspy.LM
    # forwards arbitrary kwargs to) applies cache_control_injection_points
    # provider-agnostically based solely on the param's presence, so this
    # is gated on the model actually being Anthropic-routed -- a MODEL
    # override pointing at Ollama/OpenAI/etc. would otherwise just carry an
    # inert, unrecognized field. There are no few-shot demos attached to
    # `analyze` today, so one breakpoint on the system message covers the
    # whole static prefix; if a compiled/optimized program with demos is
    # ever loaded here, add a second point, {"location": "message", "index":
    # -2}, to fold the demo turns into the same cached prefix too (the
    # real, always-different input is always the last message, so -2 is
    # "whatever precedes it," demos or not).
    if "anthropic" in model.lower():
        lm_kwargs["cache_control_injection_points"] = [
            {"location": "message", "role": "system"}
        ]

    lm = dspy.LM(**lm_kwargs)
    dspy.configure(lm=lm)
    return lm
 
 
 
from arsgrammatica import print_analysis, analyze_passage
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Latin syntax analysis.")
    parser.add_argument(
        "--passage",
        default="arma virumque cano.",
        help="Latin passage to analyze (defaults to the built-in sample).",
    )
    parser.add_argument(
        "--citation",
        default="",
        help="Optional citation label for the passage (e.g. 'urn:cts:latinLit:phi0690:1.1'), "
             "recorded on every token via Token.citation. Defaults to no citation.",
    )
    args = parser.parse_args()

    _configure_lm()
    #loadollama()
    sentences, results = analyze_passage(args.passage, citation=args.citation)
 
    for i, (sentence, result) in enumerate(zip(sentences, results), start=1):
        if len(sentences) > 1:
            print(f"\n=== Sentence {i} ===")
        print_analysis(sentence.tokens, result)
 
 
 
 
    #diagram, mermaid_warnings = tokengraph_to_mermaid(res.tokengraph)
    #print("\nMermaid diagram:")
    #print(diagram)
    #for w in mermaid_warnings:
    #    print(f"  warning: {w}")