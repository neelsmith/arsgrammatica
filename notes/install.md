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

Only needed for `attgraph()` (`arsgrammatica/aat_bridge.py`), converting an analysis to an Agent-Action-Target graph. The separate `aat` package isn't on PyPI either, so pick one:

```sh
# simplest -- just install aat directly
pip install git+https://github.com/neelsmith/aat.git

# or, pull it in via arsgrammatica's own "aat" extra (same effect)
pip install "arsgrammatica[aat] @ git+https://github.com/neelsmith/arsgrammatica.git"
```

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

Add `[aat]` too if you're touching `aat_bridge.py` or its tests:

```sh
pip install "aat @ git+https://github.com/neelsmith/aat.git"
```

If you want `import arsgrammatica` to work from *outside* the repo root too (a script elsewhere, a notebook opened from another directory), install the checkout itself as editable instead of just its dependencies:

```sh
pip install -e .
# or, with the aat extra:
pip install -e ".[aat]"
```

### Dev-only tools

`pyproject.toml` has a `dev` extra covering all of this in one shot (pytest, python-dotenv, pdoc, marimo) -- combine it with the editable install above:

```sh
pip install -e ".[dev]"
# or, with the aat extra too:
pip install -e ".[dev,aat]"
```

Without the editable install, the same tools can still be installed by hand:

```sh
pip install pytest python-dotenv       # running the test suite, .env-based LM config
pip install pdoc                       # regenerating docs/arsgrammatica-api-docs.html
pip install marimo                     # the notebooks in marimo/
```

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
