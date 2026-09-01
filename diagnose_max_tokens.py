"""
One-off diagnostic: does explicitly passing max_tokens to the configured LM
reproduce the "405 Method Not Allowed" error, or does even a max_tokens-free
call fail the same way?

Run this from the arsgrammatica folder with your .venv active:

    python3 diagnose_max_tokens.py

Paste back the full output. Whichever of the two calls below fails (one,
both, or neither) tells us where to look next:
  - Only the max_tokens call fails -> the proxy doesn't like an explicit
    max_tokens in the request; token_budget.py needs to stop sending one on
    the first attempt.
  - Both calls fail the same way -> unrelated to max_tokens at all (proxy
    down, MODEL/API_BASE/API_KEY issue, or a litellm/openai version quirk on
    this machine) -- worth checking API_BASE reachability and the MODEL
    string separately.
  - Neither fails -> something else about the real SentenceAnalysis call
    (prompt size, the `config=` plumbing through dspy.Predict) is the
    trigger, not a bare max_tokens value.
"""

import os
from importlib.metadata import version, PackageNotFoundError

import dspy
from dotenv import load_dotenv

load_dotenv()


def _pkg_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed?"


print(f"dspy {_pkg_version('dspy')} / litellm {_pkg_version('litellm')} / openai {_pkg_version('openai')}")

api_base = os.getenv("API_BASE")
model = os.getenv("MODEL")
api_key = os.getenv("API_KEY")
print(f"MODEL={model!r}  API_BASE={api_base!r}  API_KEY={'set' if api_key else 'MISSING'}")

lm = dspy.LM(model=model, api_base=api_base, api_key=api_key)

print("\n--- call WITHOUT max_tokens ---")
try:
    result = lm(messages=[{"role": "user", "content": "Say hi in one word."}])
    print("OK:", result)
except Exception as exc:
    print(f"FAILED: {exc.__class__.__name__}: {exc}")

print("\n--- call WITH max_tokens=500 ---")
try:
    result = lm(messages=[{"role": "user", "content": "Say hi in one word."}], max_tokens=500)
    print("OK:", result)
except Exception as exc:
    print(f"FAILED: {exc.__class__.__name__}: {exc}")
