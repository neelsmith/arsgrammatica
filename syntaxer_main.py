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
    api_key = _env("API_KEY", "API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
        )

    lm = dspy.LM(model=model, api_base=api_base, api_key=api_key)
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
    args = parser.parse_args()

    _configure_lm()
    #loadollama()
    toks, res = analyze_passage(args.passage)


    print_analysis(toks, res)




    #diagram, mermaid_warnings = tokengraph_to_mermaid(res.tokengraph)
    #print("\nMermaid diagram:")
    #print(diagram)
    #for w in mermaid_warnings:
    #    print(f"  warning: {w}")