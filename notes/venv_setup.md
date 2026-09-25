# Setting up (and keeping in sync) a dev venv after a fresh clone

Complements `notes/install.md` (which covers *what* to install and why) with just the venv lifecycle itself: first setup after `git clone`, and staying in sync as `pyproject.toml` changes over time on later pulls.

## First time, after cloning

```sh
git clone https://github.com/neelsmith/arsgrammatica.git
cd arsgrammatica
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

`uv` (<https://docs.astral.sh/uv/>) is a drop-in-faster replacement for `python3 -m venv` + `pip` -- if it isn't installed, the plain equivalent is `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`. Either way, `.venv/` at the repo root is already in `.gitignore`.

`-e ".[dev]"` is the one command that covers everything a normal dev checkout needs: the package itself (editable, so `import arsgrammatica` sees code edits immediately, no reinstall), `dspy` (via the `llm` extra `dev` now depends on -- see `notes/wasm_export.md` for why `dspy` moved out of the base install), `aat` (a git dependency -- this step needs network access to GitHub), and `pytest`/`marimo`/`graphviz`/`pdoc`/`python-dotenv`. Narrower installs, if you don't want all of that:

- `uv pip install -e .` -- just the package and its two base dependencies (`pydantic`, `networkx`). No `dspy`, so `analyze()`/`segment_sources()`/etc. raise a clear `ImportError` if called, but everything in the read/render/serialize half (`read_analyses()`, `tokengraph_to_html()`, ...) works.
- `uv pip install -e ".[llm]"` -- adds `dspy` on top of the base, without the rest of `dev`'s notebook/test tooling.

Verify with:

```sh
pytest -q
```

Should report something like `1826 passed, 2 skipped, 7 deselected` (skip count may drift as the suite grows; `pytest -m live` separately exercises a real configured LM -- needs a working `.env`, see `notes/install.md`).

## Keeping it in sync on later pulls

There's no lockfile here (no `uv.lock`/`requirements.txt` pinning exact versions) -- this is a plain editable install, not a `uv`-managed project synced from a lockfile. Two consequences:

- **Your own code edits, and anyone else's, need nothing re-run** -- the editable install already points at the checkout, so `git pull`ing changes to `arsgrammatica/*.py` (or `marimo/*.py`, `tests/*.py`, ...) is picked up immediately.
- **Only a `pyproject.toml` change** (a new dependency, a version floor bump, a new extra) needs anything redone -- re-run the same install command:

  ```sh
  git pull
  uv pip install -e ".[dev]"
  ```

  Safe and cheap to just always run this after a pull if you're not sure whether `pyproject.toml` changed -- `uv` (and plain `pip`) only actually reinstalls what's different.

## One gotcha, hit while setting this up

If `.venv` ends up somewhere `uv` can't hardlink into from its cache (this came up once inside a sandboxed/managed folder during this session), `uv pip install` fails with `Operation not permitted` partway through. Fix: `export UV_LINK_MODE=copy` before the install (slightly slower, always works) -- not needed in a normal local checkout, just worth knowing the fix if it ever shows up.

## A second gotcha: a venv isn't portable, including across a Claude session's own sandbox

A `.venv` is never something to sync or hand off between machines -- it's a set of interpreter symlinks and compiled wheels tied to the exact OS/architecture it was built on, meant to be thrown away and recreated in seconds, never copied. This bit once (2026-09-25): a Claude Cowork session, working through its remote-device bridge, deleted the real `.venv` at the repo root and rebuilt it for its own verification -- but that bridge runs commands inside its own sandboxed Linux VM on the user's machine, not the user's own native shell, so the venv it built pointed at a Linux-only Python interpreter (a symlink into that session's own ephemeral `/sessions/.../uv/python/...` path). Activating that `.venv` from an ordinary local Terminal afterward couldn't find anything in it -- not because a package was missing, but because the interpreter itself couldn't run there at all.

Lesson for next time (Claude or otherwise): never rebuild the project's real `.venv` from inside a remote/sandboxed tool session -- use a separately-named, `.gitignore`d scratch venv there instead (and clean it up afterward), and leave the real `.venv` at the repo root for the user to (re)create themselves, from their own shell, with the commands above. If `.venv` ever behaves like this again -- activates fine, but every command in it fails to run or resolve -- the fix is simply to delete it and redo "First time, after cloning" above, from your own terminal.
