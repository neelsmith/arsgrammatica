# Review of `quarto/` content: stale or inaccurate material

Requested review of everything under `quarto/` for content that's gone stale or doesn't match the current codebase. This is a report only -- nothing in `quarto/` was touched (it's Neel's, per `CLAUDE.md`). Delete this file once you've folded whatever's useful into the real pages.

Checked against the current `wip` working tree (`arsgrammatica/` source, `pyproject.toml`, `notes/*.md`), not just against itself, so some of this is "doesn't match the code" rather than "internally inconsistent."

Organized roughly most-to-least confident/important within each group.

## Confirmed bugs (would mislead or fail if followed literally)

**`quarto/guides/aat.qmd`** -- calls the AAT-graph function `attgraph` throughout ("construct an `AATGraph` ... with the `attgraph` function", `from arsgrammatica import attgraph`, `graph, warnings = attgraph(sentences, results)`). The real function is `aatgraph` -- confirmed in `arsgrammatica/aat_bridge.py` (`def aatgraph(...)`), in `__init__.py`'s exports, and correctly named in `quarto/concepts/aat.qmd`'s own callout box ("a function `aatgraph`"). Copy-pasting this guide's example raises `ImportError: cannot import name 'attgraph'`.


**`quarto/tutorials/quick.qmd`** -- imports and calls `analyze_passage`, which doesn't exist anywhere in the package. The real function for a single string is `analyze_string` (used correctly in `quarto/guides/analysis.qmd`). This is the "quick start" page, so it's the first code a new user is likely to try verbatim.


**`quarto/guides/texthiliting.qmd`**, "Limiting display by syntactic depth" -- "Both `tokengraph_to_html` and `tokengraph_to_depth_html` accept an optional `depth` parameter. `tokengraph_to_html` will highlight only tokens at or below the specified syntactic depth; `tokengraph_to_html` entirely omits tokens above the cutoff depth." The second sentence names `tokengraph_to_html` twice -- the second occurrence should be `tokengraph_to_depth_html`. Confirmed against both functions' docstrings in `arsgrammatica/rendering.py`: `tokengraph_to_html`'s `depth` only limits *highlighting* (every token still renders, per its own docstring: "never affects which tokens appear"); `tokengraph_to_depth_html`'s `depth` actually *drops* out-of-depth blocks ("a block deeper than that is dropped entirely"). As written, the guide claims the first function does the dropping, which is backwards.

**`quarto/reference/vuvalues.qmd`**, "Syntactic type" -- says "For participles: `circumstantial participle`". `VerbalExpression.syntactic_type`'s actual allowed values (`arsgrammatica/models.py`) are exactly `"independent", "dependent", "direct quote", "aside", "indirect statement"` -- there is no `"circumstantial participle"` syntactic_type. The model's own docstring spells out the real convention: "For a predicate-sense participle: `dependent` (this codebase's convention; syntax_model.md doesn't specify)." `circumstantial participle` is a *relationship* label (in `RelationLabel`, correctly listed in `reference/relationshipvalues.qmd`), not a verbal-expression syntactic type -- this page conflates the two.

**`quarto/reference/tokentypes.qmd`** -- lists only `punctuation`, `enclitic`, `lexical`, `praenomen`, `abbreviation`, `numeral`. `TokenAnalysis.tokentype`'s actual `Literal` (`arsgrammatica/models.py`) also includes three more values: `implied sum`, `continued discourse`, `implied subject` (the `IMPLIED_TOKENTYPES` set, used for elided/understood tokens -- `sum` in compound perfects, understood repeated verbs, implied subjects). These are a real, documented part of the scheme (`syntax_model.md`'s "understood or implied verbal expressions" section, per several source docstrings) and are missing from this reference page entirely.

**Missing `utilities/` prefix on script invocations** -- several pages give a bare script name where the script actually lives in `utilities/`, so the command as written fails with "can't find file" from a repo-root shell:
  - `quarto/guides/budgetingtokens.qmd`: `python3 calibrate_max_tokens.py` -> should be `python3 utilities/calibrate_max_tokens.py`.
  - `quarto/reference/managing_prompt_size.qmd`: same, `python3 calibrate_max_tokens.py`.
  - `quarto/guides/optimizing.qmd`: the *first* code block gives `python3 optimize_gepa.py` (five times, every flag example) with no prefix; the page then switches to the correct `python3 utilities/optimize_gepa.py --eval-file ...` / `--eval-dir ...` further down -- so the page is internally inconsistent, and the first, most-likely-to-be-copied block is the wrong one.
  - `quarto/tutorials/batch-images.qmd`: `python3 analyses_to_dot_pngs.py ...` -> should be `python3 utilities/analyses_to_dot_pngs.py ...` (confirmed: the script is at `utilities/analyses_to_dot_pngs.py`, not repo root).

  For contrast, `quarto/guides/bakeoff.qmd`, `quarto/guides/gold.qmd`, `quarto/guides/batch-texts.qmd`, and `quarto/tutorials/corpus.qmd`/`diagrams.qmd` all correctly include the `utilities/` prefix throughout -- so this looks like drift from an earlier layout (or copy-paste from those correct pages, minus the prefix) rather than a deliberate choice.

## Install instructions: predate the PyPI release

**`quarto/guides/install.md`** -- currently says nothing but git installs (`pip install git+https://github.com/neelsmith/arsgrammatica.git`, with `@wip`/`@v0.5.0` pinned examples). `arsgrammatica` is now on PyPI (`pip install arsgrammatica`, currently at `0.11.2`) -- see `notes/pypi_release.md` for the whole publishing story. Also: the pinned-tag example uses `v0.5.0`, many releases behind current (`0.11.2` per `pyproject.toml`/`releases.md`). Same issue existed in `notes/install.md` before this session's earlier pass fixed it there; this is the same content, unfixed, on the `quarto` side.

**`quarto/tutorials/index.qmd`** and **`quarto/guides/aat.qmd`** also only give the git-install form (`pip install git+https://github.com/neelsmith/arsgrammatica.git`) rather than pointing at PyPI -- same underlying staleness, smaller scope.

**`quarto/guides/aat.qmd`** doesn't mention that `aatgraph()`/the `aat` package needs the optional `aat` extra (`pip install "arsgrammatica[aat]"`, now backed by the real `aatgraph` PyPI package) -- someone following just this page would hit the "aatgraph() needs the separate 'aat' package... isn't installed" error with no pointer to the fix.

## `quarto/_quarto.yml`

- `version: "0.11.0"` in the project config, used in the page-footer ("Documentation for release version **0.11.0**") -- stale; `pyproject.toml`/`releases.md` are at `0.11.2` now.

## `quarto/guides/index.qmd` ("Recipes" landing page)

- `guides/batch-texts.qmd` exists, is a real, finished page, and is in the sidebar nav (`_quarto.yml`), but isn't linked anywhere in this landing page's own curated list of guides (the "Analyzing Latin texts" section lists only `install.md`, `analysis.qmd`, `saving-loading.qmd`). Worth adding a line for it there.

## `quarto/concepts/syntactic-analysis.qmd` -- the main "how the graph works" page, unfinished in several places

This is one of the more heavily-used pages (linked from `concepts/index.qmd` as *the* explanation of the `TokenAnalysis` class), but several sections still look like an outline that never got turned into prose, unlike the rest of the page (which has full prose + worked Latin examples + tables for each relation):

- **No prose/table at all, just a leftover numbered fragment** (looks like carried over from an earlier flat list of the ~26 relation labels that was being expanded section-by-section, and these six never got expanded): "Ablative absolute" (`22. **ablative absolute** -- **Anco** in ...`), "Subordinating word" (`2. **subordinating conjunction** -- **cum** in ...`), "Relative pronoun" (`3. **relative pronoun** -- **quibus** in ...`), "Object of preposition" (`9. **object of preposition** -- **Romulo** in ...`), "Apposition" (`24. **apposition** -- **filius** in ...`), and the whole "Adverbial and attributive expressions" section (three numbered one-liners for `adverbial`/`attributive`/`adjectival`, no tables). The "Dative" section is a hybrid: real prose + example sentence, but then also still has the leftover line `14. **dative** -- **mortalibus** in ...` directly under it.
- **Draft/TODO notes left in the visible text**: the "Coordinating word" section reads, in full: "Use example like autem... / Expand on double inks iwth et (aut) / 23. **coordinating conjunction** -- **que** in *arma virumque cano*." -- these read as notes-to-self, not finished content (also two typos: "inks" -> "links", "iwth" -> "with").
- **Final section is a placeholder**: "## A note on two-way linking" is followed only by "Conjunction and relation" -- no actual explanation, even though the two-way-relationship concept is real and documented elsewhere (`reference/relationshipvalues.qmd`'s "Two-way relationships" section: `relative pronoun` and `coordinating conjunction`).
- **Stale terminology**: the "Circumstantial participle" section's table has a row `(`elided sum`) | *excepti* | `auxiliary``. The actual tokentype (per `arsgrammatica/models.py`'s `IMPLIED_TOKENTYPES`) is `implied sum`, not `elided sum` -- this looks like an earlier name for the same concept that didn't get updated everywhere.
- **Typo in a link's visible text**: "on elided tokens, see [tokes](./tokens.qmd)" -- should read "tokens". (The link target is fine; the label text is misspelled.)
- Separately, not a typo but worth flagging: that link's destination, `concepts/tokens.qmd`, is itself still a `*TBA*` stub (see below) -- so the cross-reference currently points at a page that doesn't yet explain what it's linked for.

## Placeholder ("*TBA*") pages

**`quarto/concepts/tokens.qmd`** and **`quarto/concepts/verbalunits.qmd`** are both still explicitly marked `*TBA*`, with only a few bare bullet points in `tokens.qmd`'s case. `concepts/index.qmd` links to both as if they were finished ("[Tokenization of a passage](./tokens.qmd) (the `Token` class)", "AAT anchor points: [verbal units](./verbalunits.qmd)"), and (per the point just above) `syntactic-analysis.qmd` sends readers to `tokens.qmd` specifically to learn about elided tokens, which it doesn't yet cover.

## Minor wording issues (not wrong, just rough)

- `quarto/tutorials/index.qmd`: "Configure your language model in a `.env` file **ilke** this" -- typo for "like".
- `quarto/guides/gold.qmd`: "Run `analysis_to_gold_example -h`" -- every other invocation of this script in the same page is `python3 utilities/analysis_to_gold_example.py ...`; this one line drops all three (the `python3`, the `utilities/` path, and the `.py` extension), reading like a installed-console-script name rather than the actual script.
- Several pages mix `python` and `python3` for otherwise-identical invocations (e.g. `guides/batch-texts.qmd` uses bare `python`, `guides/budgetingtokens.qmd`/`tutorials/*` use `python3`) -- harmless, but inconsistent.

## Checked and found accurate (no action needed)

For what it's worth, since this review also cross-checked these against the source, in case it saves you re-verifying: `reference/relationshipvalues.qmd`'s 26 relation labels match `RelationLabel` in `models.py` exactly; `concepts/complete_examples.qmd`'s relationship-category table also matches the same 26 labels; `guides/saving-loading.qmd`'s and `guides/analysis.qmd`'s and `guides/mermaid.qmd`'s function signatures/return-value shapes (`write_analyses`, `read_analyses`, `split_analysis_by_sentence`, `analyze_string`, `analyze_sources`, `tokengraph_to_mermaid`, `save_mermaid`) all match the current code exactly, including argument order and optional-parameter defaults; `guides/bakeoff.qmd`'s CLI-flag reference matches `model_bakeoff.py`'s actual flags as far as this review checked.
