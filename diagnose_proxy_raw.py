"""
Bypasses litellm/dspy/the openai SDK entirely -- a raw HTTP request straight
to your litellm proxy using only Python's stdlib urllib -- to tell "client
library issue" apart from "server/proxy issue" for the 405 seen in
diagnose_max_tokens.py.

(A shell/curl version of this was the first draft, but MODEL is
"litellm_proxy/anthropic/Claude Opus 5" -- the value has spaces in it, which
breaks naive shell .env-sourcing tricks. Doing this in Python with
python-dotenv, the same library syntaxer_main.py already uses, avoids that
entirely.)

Run from the arsgrammatica folder with your .venv active:

    python3 diagnose_proxy_raw.py

What to look for:
  - HTTP 200 with a real completion -> the proxy itself is fine; something
    in the Python client stack (litellm 1.96.2 / openai 2.54.0 in your
    venv) is shaping the request in a way the proxy doesn't like.
  - HTTP 405 here too -> confirmed server/proxy-side, not fixable from this
    codebase at all -- next step is contacting whoever administers
    suarezai.holycross.edu/litellm (Holy Cross' AI/IT services), or
    checking for an announced maintenance window / model deprecation.
  - A different error (connection refused, DNS failure, 401/403) -> a
    different, more specific problem (reachability or the key itself), not
    the same 405 the other diagnostic reported.
"""

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

api_base = os.getenv("API_BASE")
model = os.getenv("MODEL")
api_key = os.getenv("API_KEY")
print(f"API_BASE={api_base!r}")
print(f"MODEL={model!r}")
print(f"API_KEY={'set' if api_key else 'MISSING'}")

if not (api_base and model and api_key):
    raise SystemExit(
        "Missing API_BASE/MODEL/API_KEY -- run this from the arsgrammatica "
        "folder (the one with .env in it), e.g. `cd ~/Desktop/arsgrammatica "
        "&& python3 diagnose_proxy_raw.py`."
    )

# "litellm_proxy/anthropic/Claude Opus 5" -> the proxy itself expects the
# part after "litellm_proxy/" as its own model name.
proxy_model = model.split("litellm_proxy/", 1)[-1] if model else model


def _post(path, payload):
    url = api_base.rstrip("/") + path
    print(f"\n--- POST {url} (model={proxy_model!r}) ---")
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"HTTP status: {resp.status}")
            print(resp.read().decode("utf-8", errors="replace")[:2000])
    except urllib.error.HTTPError as exc:
        print(f"HTTP status: {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:2000])
    except urllib.error.URLError as exc:
        print(f"Connection/network error (not an HTTP response at all): {exc}")


def _get(path):
    url = api_base.rstrip("/") + path
    print(f"\n--- GET {url} ---")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"HTTP status: {resp.status}")
            print(resp.read().decode("utf-8", errors="replace")[:2000])
    except urllib.error.HTTPError as exc:
        print(f"HTTP status: {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:2000])
    except urllib.error.URLError as exc:
        print(f"Connection/network error (not an HTTP response at all): {exc}")


_post(
    "/chat/completions",
    {"model": proxy_model, "messages": [{"role": "user", "content": "Say hi in one word."}]},
)

# Sanity check: is the proxy reachable/listing models at all, independent
# of the chat-completions route specifically?
_get("/models")
