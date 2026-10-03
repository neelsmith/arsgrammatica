# Building quarto web site




Preview: from `quarto` directory:

`quarto preview`

Build: from repository root:

`quarto render`

Test output: from reepository root:

`python3 -m http.server -d quarto/quarto-build`


---

One-time setup before a page with a `jupyter: <name>` front-matter key (e.g. `guides/texthiliting.qmd`) will actually execute and show real output, not just source: register `.venv` as a named kernel (`python -m ipykernel install --user --name arsgrammatica --display-name "arsgrammatica (.venv)"`), and make sure Quarto's own driver script runs under THAT Python too (activate `.venv` before `quarto render`/`quarto preview`, or set `export QUARTO_PYTHON=/full/path/to/.venv/bin/python3` to stop depending on shell state). Full gotcha + the exact traceback this throws when skipped (`ModuleNotFoundError: No module named 'nbformat'`): `notes/venv_setup.md`.
