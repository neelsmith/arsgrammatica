# Switch to the quarto/concepts specification: remaining questions

Date: 2026-10-24, on `wip`. Companion to `notes/model_switch_changes.md`. Questions are in rough order of urgency.

## A. Will break or mislead until dealt with

1. **Saved analyses are in the old format and can no longer be read.** As agreed, `read_analyses()` now rejects them. Affected files:
   - `data/vulgate/*.cex` (13 files)
   - `data/livy/livy_1_57_1_*.cex`
   - `quarto/sample_data/vulgate_genesis_tokenized_42_27.cex`
   - `quarto/sample_data/rosa.cex`

   Four Quarto pages read these files in live code cells: `guides/mermaid.qmd`, `guides/texthiliting.qmd`, `guides/graphmetrics.qmd` and `guides/saving-loading.qmd`. They will fail to render until the files are regenerated. The marimo notebooks will fail the same way if pointed at these files.

   There are two ways to fix this:
   - Re-run the analyses.
   - Ask me for a one-off converter. It would only rename labels and reshape columns; it would *not* add the new annotations (gerundive verbal expressions, circumstantial-participle types, relations for formerly unrelated tokens), so a re-run gives better data.

2. **The GEPA-optimized program `optimized/optimized_opus_5_ag_0_7_0_vulgate.json` is stale.** Its demos and instructions use the old schema, so loading it (e.g. from `marimo/latin_syntaxer_ctsdata.py`) would mix old-schema examples into the prompt. Re-optimize with `utilities/optimize_gepa.py` or stop using it.

3. **The `max_tokens` calibration may now be too low.** The output is larger: each relation is a nested object, there are more relations per sentence, and every token must now be related. `token_budget.py`'s fit (and any `token_budget_calibration.json`) predates this. Re-run `utilities/calibrate_max_tokens.py`. `analyze_with_retry()` will retry when output is truncated, but each retry costs a call.

4. **The new prompt has not been run against a live LM.** Only the DummyLM suite was run. Before relying on it, try a few passages with `pytest -m live` or a notebook. Things to watch:
   - **Multiple relations:** does the model produce `relations` lists correctly?
   - **Unrelated tokens:** does it now relate every token?
   - **New constructions:** does it use the new types and labels (parataxis, gerundive, agent-dative, predicate uses 3–4)?

5. **Neel's Quarto pages that still describe the old fields or labels:**
   - `tutorials/cli.qmd`
   - `guides/gold.qmd`
   - `guides/extendingscheme.qmd`
   - `guides/bakeoff.qmd`
   - `reference/relationshipvalues.qmd` (it flags itself as out of date)
   - `guides/graphmetrics.qmd`, `concepts/complete_examples.qmd` and `concepts/models.qmd` (mentions of old field or label names)

   Also, `docs/arsgrammatica-api-docs.html` should be regenerated with `utilities/build_api_docs.py` once you're happy with the code.

6. **Release:** this is a breaking change to the Python API and the file format. `pyproject.toml` is still at 0.12.0. Should this be 1.0.0, to match "the 1.0 schema" that `relationshipvalues.qmd` mentions? Should `releases.md` get an entry, and should `syntax_model.md` be deleted?

## B. Inferences the code makes that the scheme doesn't settle

7. **Voice for the A-A-T mapping (`aat_bridge.py`).** The docs define agent and target by voice (active/deponent vs. passive), but the analysis no longer records voice or semantic type. `_voice()` infers it, checking in this order:
   1. an `agent-ablative`/`agent-dative` dependent → passive;
   2. a gerundive anchor (syntactic type `gerundive`, or a form ending in *-nd-*) → passive;
   3. a lemma ending in *-or* (a deponent) → active;
   4. an `auxiliary` dependent, or a form ending in *-tur*/*-ntur* → passive;
   5. anything else → active.

   **Where these guesses fail:**
   - a simple passive with no agent and an unusual ending (*amamur*, *amaris*);
   - a deponent whose lemma isn't given in the *-or* form;
   - semi-deponents.

   Possible fixes:
   - add a `voice` field to `VerbalExpression` (cheap for the LM, exact for AAT);
   - or accept the heuristic.

8. **What counts as a linking verb for AAT.** `_is_linking()` is true for lemma *sum* or *fio*, or an implied *sum*. Should *videor*, *maneo*, *evado*, etc. count? (This only affects whether a use-1 predicate becomes an AAT target.)

9. **`verbalunitid` is redundant.** It duplicates `verbalunits`, the format doesn't store it, and the LM still has to produce it. Options:
   - drop it from the LM's output schema and derive it after analysis (fewer output tokens, no chance of the two disagreeing);
   - or keep it as-is.

10. **The order of a token's relations.** The format says a token's relations are unordered, so code that used to prefer `relatedtoken1` now uses `chase_order()`:
    - the 'relative pronoun' relation first;
    - then relations in the document order of their targets.

    One visible consequence: a coordinating word that joins two verbs now always belongs to the verbal unit of the *earlier* verb. Before, it belonged to whichever verb was in its first slot.

11. **The "every token has a relation" rule is not enforced.** `syntactic-analysis.qmd` says every non-punctuation token is related, but `validate()` doesn't check this, because some sentences can't satisfy it. For example, in the verbless *Tu quoque, Brute, fili mi, et tu?*, *Tu*, *Brute* and the final *tu* have nothing to relate to, and a `vocative` must relate to a verb. Should `validate()` warn about unrelated tokens? And how should verbless sentences be treated: an implied verb, or no relation?

12. **Implied tokens move on a round trip.** The writer moves an implied token that lies outside its sentence's span. That keeps the file valid, but reading it back changes the token's position in `tokengraph`. Is that acceptable? The alternative is to raise an error and require callers to place implied tokens correctly.

13. **Token ids.** `analysisformat.qmd` says ids must be unique "across the current sentence". The code's passage-scoped ids (e.g. `1.t0`) are unique across a whole run, and the `_implied` suffix convention keeps implied ids unique too. Nothing checks for clashes when files are concatenated.

## C. Annotation judgment calls in the gold examples (please review)

14. **The *consulibus* ablative absolute** (`implied_participle_of_sum_consulibus`). No page gives a table for this example. The annotation I chose:
    - the implied participle relates to *Menenio* and *Postumio* as `circumstantial participle`;
    - both names → *moritur* as `ablative absolute`;
    - *consulibus* → the implied participle as `predicate`.

    By analogy, in *inscio Collatino* (`praenomen_sex_tarquinius_venit`), *inscio* is now the `predicate` of the implied participle; it was previously `adjectival` → *Collatino*.

15. ***eos nos ... esse spero*** (`aside_equidem_pace_dixerim`): *nos* is now the subject of *esse* and *eos* its predicate. Before, *eos* was the subject and *nos* was unrelated. The reverse reading is also possible.

16. **Connectives not on the page's list.** *enim* (`indirect_statement_facturum_fuisse_dixit`) and *autem* are treated as `coordinating word` → verb, like *nam*/*autem* on the page. *quoque* is `adverbial` to the word it follows (*ea*; *Tu*).

17. **Smaller annotation choices:**

    | Token | Annotation | Note |
    |---|---|---|
    | *ne* (interrogative enclitic) | `adverbial` → the verb | The docs give no relation for it. |
    | *Mycenis* | `ablative` → *adduxit* | Could be read as locative. |
    | *L.* in *L. f.* | stays tokentype `praenomen` | It has a `genitive` relation, following `tokens.qmd` and the syntactic-analysis page. |

18. **Lemmas of implied tokens.** Implied *sum* tokens get lemma `sum`. Implied verbs and implied substantives get no lemma. Should an implied verb of speaking get a lemma (e.g. *dico*)?

19. **Gold slugs that name retired concepts.** `semantic_type_transitive_passive_urbs_condita` and `semantic_type_linking_verb_etruria_vicina` keep their slugs, because `utilities/model_bakeoff.py`'s `HELD_OUT_SLUGS` and some tests refer to them. Rename them?

20. **No gold example yet for the understood repeated verb in an *ut*-clause** (*...exspectationem ipsius adventus admiratioque superaret*). The prompt tells the model that the implied verb is `dependent` and relates to *ut* as `unit verb`, so *ut* would have two `unit verb` dependents. Is that the intended structure? If so, it's worth adding as a gold example.

## D. Small documentation slips noticed while implementing

- `verbalunits.qmd`: "*conveniat* ... will be classifed as as `subordinate`". This should be `dependent`, and there are two typos ("classifed", "as as").
- `syntactic-analysis.qmd`, A-A-T paragraph: "If a linking verb (copula) has a substantive `predicate`, the predicate is the target. Note that non-nominative predicates ... are not treated as targets." I implemented "predicate of a linking verb (use 1) or of a passive verb (use 4) is a target, uses 2 and 3 are not". Please confirm that is the intent.
- `analysisformat.qmd`: the implied-token example uses context `sample:1` and IDs like `t2_implied`. The code writes the sentence's first token's citation as the context, which matches the page's "first or last context value".
