# Installing arsgrammatica

Not on PyPI -- every install here is a direct git reference. Two cases: using the package as-is, or checking it out to develop/test it.

## Just use the package

```sh
pip install git+https://github.com/neelsmith/arsgrammatica.git
```

Pin to a branch or tag if you don't want `main`:

```sh
pip install git+https://github.com/neelsmith/arsgrammatica.git@wip
pip install git+https://github.com/neelsmith/arsgrammatica.git@v0.5.0
```

### Optional: the `aat` extra

Only needed for `aatgraph()` (`arsgrammatica/aat_bridge.py`), converting an analysis to an Agent-Action-Target graph. The separate `aat` package isn't on PyPI either, so pick one:

```sh
# simplest -- just install aat directly
pip install git+https://github.com/neelsmith/aat.git

# or, pull it in via arsgrammatica's own "aat" extra (same effect)
pip install "arsgrammatica[aat] @ git+https://github.com/neelsmith/arsgrammatica.git"
```

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
pip install dspy pydantic networkx
```

This alone doesn't cover `aatgraph()`/the marimo notebooks -- see "Dev-only tools" just below for that, regardless of whether you're touching `aat_bridge.py` itself or just running `latin_syntaxer_review.py` as-is.

If you want `import arsgrammatica` to work from *outside* the repo root too (a script elsewhere, a notebook opened from another directory), install the checkout itself as editable instead of just its dependencies:

```sh
pip install -e .
```

### Dev-only tools

`pyproject.toml` has a `dev` extra covering all of this in one shot (pytest, python-dotenv, pdoc, marimo, graphviz, and `aat`, needed for the AAT graph in `latin_syntaxer_review.py`) -- combine it with the editable install above:

```sh
pip install -e ".[dev]"
```

Without the editable install, the same tools can still be installed by hand:

```sh
pip install pytest python-dotenv       # running the test suite, .env-based LM config
pip install pdoc                       # regenerating docs/arsgrammatica-api-docs.html
pip install marimo                     # the notebooks in marimo/
pip install graphviz                   # rendering DOT diagrams in marimo/latin_syntaxer_review.py
pip install "aat @ git+https://github.com/neelsmith/aat.git"  # the AAT graph in marimo/latin_syntaxer_review.py
```

Every one of these -- the editable-install extra and the by-hand list alike -- covers `aat` now too, on purpose: it used to be a separate thing to remember (`[aat]`, or its own `pip install`), easy to skip since nothing else in a normal dev setup needed it, which is exactly how a checkout can end up running `latin_syntaxer_review.py` without it and hitting its "the `aat` package isn't installed" warning. Since the only thing in this repo that actually calls `aatgraph()` is that same notebook, `aat` now just comes with the rest of its dependencies (marimo, graphviz) rather than being its own opt-in step.

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
