# Installing arsgrammatica

`arsgrammatica` is published on PyPI as [`arsgrammatica`](https://pypi.org/project/arsgrammatica/). A git checkout is only needed to develop/test it, or to run the marimo notebooks under `marimo/`.

## Just use the package

```sh
pip install arsgrammatica
```

Need a specific version?

```sh
pip install arsgrammatica==0.11.2
```

A direct-from-git install still works too, if you want an unreleased branch:

```sh
pip install git+https://github.com/neelsmith/arsgrammatica.git@wip
```

### Optional: the `aat` extra

Only needed for `aatgraph()` (`arsgrammatica/aat_bridge.py`), converting an analysis to an Agent-Action-Target graph. `aat` is itself published on PyPI, under the distribution name [`aatgraph`](https://pypi.org/project/aatgraph/) (the *importable* module stays `aat` -- nothing in `aat_bridge.py` or the marimo notebooks needed to change for this):

```sh
pip install "arsgrammatica[aat]"

# or, equivalently, install aatgraph yourself alongside the base package
pip install arsgrammatica aatgraph
```

`aatgraph`'s own base install needs only `pydantic` -- no dspy, no native extensions -- so this extra is WASM-safe too (see `notes/wasm_export.md`).

(If you're setting up a checkout to develop/run the notebooks rather than just using the installed package, don't reach for this section at all -- see "Dev-only tools" below, which already includes `aat` by default.)

## Developing (checkout + tests)

```sh
git clone https://github.com/neelsmith/arsgrammatica.git
cd arsgrammatica
python3 -m venv .venv
source .venv/bin/activate
```

`pytest.ini` sets `pythonpath = .`, so `pytest` and any script run from the repo root already sees `import arsgrammatica` straight from the checkout -- **the package itself doesn't need to be pip-installed to run the test suite.** Install just its runtime dependencies:

```sh
pip install pydantic networkx
```

`dspy` isn't part of the base install any more -- it's its own `llm` extra (see "Dev-only tools" below, which pulls it in). This alone doesn't cover `aatgraph()`/the marimo notebooks either -- see "Dev-only tools" just below for that, regardless of whether you're touching `aat_bridge.py` itself or just running `latin_syntaxer_review.py` as-is.

If you want `import arsgrammatica` to work from *outside* the repo root too (a script elsewhere, a notebook opened from another directory), install the checkout itself as editable instead of just its dependencies:

```sh
pip install -e .
```

For a full first-time setup (including which of the above to run, and using `uv` instead of plain `venv`/`pip`), see `notes/venv_setup.md`.

### Dev-only tools

`pyproject.toml` has a `dev` extra covering all of this in one shot (dspy, pytest, python-dotenv, pdoc, marimo, graphviz, and `aat`/`aatgraph`, needed for the AAT graph in `latin_syntaxer_review.py`) -- combine it with the editable install above:

```sh
pip install -e ".[dev]"
```

Without the editable install, the same tools can still be installed by hand:

```sh
pip install dspy                       # the LM-based analysis pipeline (latin_syntax_dspy.py etc.)
pip install pytest python-dotenv       # running the test suite, .env-based LM config
pip install pdoc                       # regenerating docs/arsgrammatica-api-docs.html
pip install marimo                     # the notebooks in marimo/
pip install graphviz                   # rendering DOT diagrams in marimo/latin_syntaxer_review.py
pip install aatgraph                   # the AAT graph in marimo/latin_syntaxer_review.py (importable as `aat`)
```

Every one of these -- the editable-install extra and the by-hand list alike -- covers `aat` too, on purpose: since the only thing in this repo that actually calls `aatgraph()` is that same notebook, `aat` just comes with the rest of its dependencies (marimo, graphviz) rather than being its own opt-in step.

The `graphviz` *package* is only a subprocess wrapper -- rendering a diagram (not generating its DOT source, which needs no dependency at all) also needs Graphviz's own `dot` executable installed separately and on your PATH (e.g. `brew install graphviz` on macOS, `apt install graphviz` on Linux). See `notes/dot_diagrams.md`.

### Running tests

```sh
pytest                # offline, DummyLM-backed -- see TESTING.md
pytest -m live         # exercises the real configured LM -- needs a working .env
```

### `.env` for live tests / `syntaxer_main.py`

```
API_BASE=https://localmodel/api
MODEL=litellm/modelname
API_KEY=your-key-here
```
