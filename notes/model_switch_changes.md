# Switch to the quarto/concepts specification: what changed

Date: 2026-10-24, on `wip`. Nothing is committed.

The code and tests now implement the scheme in Neel's Quarto pages:

- `quarto/concepts/tokens.qmd`
- `quarto/concepts/verbalunits.qmd`
- `quarto/concepts/syntactic-analysis.qmd`
- `quarto/reference/analysisformat.qmd` (the file format)

`syntax_model.md` is no longer referenced by any code or test, but the file itself has not been deleted.

Three design choices were Neel's, made before the work started:

- a token's relations are a list;
- the reader accepts the new file format only;
- the LM prompt is a hand-written docstring.

Test suite: 2089 passed, 2 skipped. Before the switch it was 1854 passed. The extra tests come from the new gold examples (many tests run once per gold example) and from the new tests listed below. Nothing was run against a live LM.

## Data model (`arsgrammatica/models.py`)

### Relations

- **New `Relation` model**: `related` (a token id, an implied token's id, or `'root'`) and `relationship` (a label).
- **`TokenAnalysis.relations: List[Relation]`** replaces `relatedtoken1`/`relationship1`/`relatedtoken2`/`relationship2`. A token can have any number of relations, and their order carries no meaning.
- **Helper methods** on `TokenAnalysis`: `related_ids(label=None)`, `relationships()`, `has_relationship(*labels)`, `first_related(*labels)`, `add_relation()`.
- **Module-level helpers**: `rel(related, relationship)` and `iter_edges(tokengraph)`.

### Vocabulary

**`RelationLabel`** now has 28 values, taken from `syntactic-analysis.qmd`:

| Change | Labels |
|---|---|
| New | `parataxis`, `gerundive`, `agent-dative` |
| Renamed | `agent` → `agent-ablative` |
| Renamed | `coordinating conjunction` → `coordinating word` |
| Renamed | `subordinating conjunction` → `subordinating word` |
| Removed (merged) | `attributive` → `adjectival` |

**`SyntacticType`**, a new named `Literal`:

- `independent`
- `dependent`
- `direct quote`
- `aside`
- `parataxis` (new)
- `indirect statement`
- `circumstantial participle` (new)
- `gerundive` (new)

**`VerbalExpression.semantic_type` is removed.**

**`TokenType`**: the implied types are now `implied sum`, `implied verb` (formerly `continued discourse`) and `implied substantive` (formerly `implied subject`).

- `IMPLIED_TOKENTYPES` is updated to match.
- New `IMPLIED_VERBAL_TOKENTYPES` (implied sum and implied verb) lists the implied types that can anchor a verbal expression.

### Unchanged

- `TokenAnalysis.verbalunitid` is kept. It is not stored in the file format, so the reader rebuilds it.
- `CitedText`, `Token` and `Sentence` are unchanged.
- The new names are exported from `arsgrammatica/__init__.py`.

## LM prompt (`latin_syntax_dspy.py`)

### `SentenceAnalysis` docstring

The docstring was rewritten by hand from the three Concepts pages. It covers:

- **Verbal expressions:** the four constructions and the eight syntactic types.
- **Relations:** every relation label, grouped as on the syntactic-analysis page, with the pages' own examples.
- **Implied tokens:** the three kinds, and the `_implied` id convention.
- **Token types.**
- **Ambiguity:** the existing instruction to flag genuinely ambiguous readings is kept.

The output field `tokengraph` now carries a `relations` list.

### `validate()`

`validate()` now checks every relation of every token, not just the first two. It also reports `'root'` used with any label other than `unit verb`.

### `print_analysis()`

`print_analysis()` prints all of a token's relations and no longer prints a semantic type.

## Segmentation prompt (`segmentation_dspy.py`)

The enclitic rule now follows `tokens.qmd`:

- `-dum` (e.g. "vixdum") and an enclitic `-cum` (e.g. "nobiscum") are added as enclitics.
- These words stay as single tokens, because the enclitic is part of the word: quisque and its forms, plerusque, neque, atque, itaque, denique, undique.

## Serialization (`serialization.py`)

The module implements `analysisformat.qmd`.

### File format

- **`#!verbal_units` header:** `context|token|syntactic_type`.
- **`#!tokens` header:** `context|id|tokentype|text|lemma|related|relationship`.
- **One row per relation.** A token with several relations gets several adjacent rows, identical except for `related`/`relationship`. A token with no relations gets one row with both fields empty.

### Reading (`read_analyses()`)

- Merges each run of same-id rows back into one token.
- Raises an error if a token's rows are not adjacent or disagree in another column, or if a row has only one of `related`/`relationship`.
- Rebuilds `verbalunitid` from `#!verbal_units`.
- Validates labels and types through pydantic and reports bad values as `ValueError`.
- **Old files are rejected.** The pre-1.0 headers (a `semantic_type` column, or the 10-column token header) raise a `ValueError` saying the format is no longer supported.

### Implied tokens

- **Writing:** the format requires an implied token to sit between its sentence's first and last token rows. The writer moves any implied token outside every sentence's span (e.g. at the very end) to just before its sentence's last token. Its context is its sentence's first token's citation.
- **Splitting:** `split_analysis_by_sentence()` now includes, in a sentence's slice, implied tokens that come after that sentence's last real token. This fixes a limitation that was documented and tested before.
- **Round trip:** reading a file back can change the position of an implied token in `tokengraph`, but never its content.

### Unchanged

The `#!lm` block is unchanged, including the legacy `#!LM` label.

`notes/serialization_formats.md` is updated to match.

## Consumers

Code that used to read `relatedtoken1` and fall back to `relatedtoken2` now uses the relation list.

### New helpers in `verbal_units.py`

- **`chase_order(tok, position)`** gives the order in which to follow a token's relations when chasing through the graph. A 'relative pronoun' relation (to the antecedent) comes first; other relations follow in the document order of their targets. This replaces the old "slot 1 first" rule, which no longer exists because relations are unordered.
- **`is_root_verb(tok)`** tests for a 'unit verb' relation to 'root'.

### Changes by module

- **`verbal_units.py`:**
  - `assign_verbal_units`, `find_governing_verbal_expression` and `compute_subordination_depths` use `chase_order`.
  - `find_unanchored_coordinated_verbs` looks for tokens with exactly two `coordinating word` relations.
- **`dot.py`:** `compute_graph_depths` picks a token's parent with `chase_order`.
- **Drawing relations:** `mermaid.py`, `graphs.py`, `displacy_viz.py` and `rendering.py` iterate over all of a token's relations.
  - `rendering.tokengraph_relationship_types()` collects labels from every relation.
  - `rendering.relationship_edges()` returns one edge per relation.
- **Colored HTML spans:** `rendering.tokengraph_to_html()` (and the depth and relationship variants) now also colors `abbreviation` tokens, since abbreviations now have relations (e.g. *f.* and *cos.* in apposition). Tokens with a `coordinating word` relation are colored as before.
- **Mermaid labels:** an implied sum is labelled "elided sum"; the other two implied types show their type name.
- **`aat_bridge.py`:** agent and target now follow the voice-based rules on the syntactic-analysis page.
  - Voice is inferred, since semantic types are gone. The heuristics are documented in the module and listed in the questions note.
  - Supports `agent-ablative` and `agent-dative`.
  - `predicate` is a target only after a linking verb (use 1) or a passive verb (use 4).
- **`gepa_metric.py`:**
  - Relations are compared as an unordered set of triples.
  - The verbal-expression score covers `syntactic_type` only.
- **Comments and docstrings** in the package, utilities and tests now refer to the Concepts pages (or "the scheme docs") instead of `syntax_model.md`, and use the new field names and labels.

## Gold examples (`tests/fixtures/gold_examples.py`)

Each canned answer was converted to `relations` lists with the new labels, and `semantic_type` was removed.

### Re-annotated for the new scheme

**Circumstantial participles** now have syntactic type `circumstantial participle` (formerly `dependent`):

- regnante, advenientem, cognita, moriens, tinctas, Recordatus;
- the implied participles of *sum* in *consulibus* and *inscio Collatino*.

**Tokens that were left unrelated now have relations**, because the new docs say every non-punctuation token gets one:

| Token | New relation |
|---|---|
| proximam | `adjectival` |
| L. | `genitive` → f. |
| f., cos. | `apposition` → Agrippa |
| tertium | `adverbial` → cos. |
| passuum | `genitive` |
| XXV | `adjectival` |
| Albanorum | `genitive` |
| ea | `adjectival` |
| quoque | `adverbial` |
| rei | `genitive` |
| publicae | `adjectival` |
| Romam, Collatiam | `accusative` |
| enim, autem | `coordinating word` |
| nos (and eos reinterpreted) | subject and predicate of *esse* |
| heres | `predicate`, use 2 |
| que (in ferro flammaque) | `coordinating word` |
| ne | `adverbial` |
| fidem, suam, infirmare (in *Hermionenque*) | direct object, adjectival, complementary infinitive |
| Mycenis | `ablative` |
| quoque, fili (in *Tu quoque, Brute*) | `adverbial`, `apposition` |

**Gerundive and participle changes** (the participle row is not a gerundive):

- *faciendum* is now a `gerundive` verbal expression, related to its noun as `gerundive`.
- *exceptum* is now a circumstantial participle, as `verbalunits.qmd` directs for this exact sentence.

**Implied-token changes:**

- *Agrippa* in *Agrippa Menenio* is now tokentype `praenomen`.
- The *consulibus* ablative absolute is restructured: the implied participle relates to both names, both names are `ablative absolute` → moritur, and *consulibus* is the predicate of the implied participle.
- *inscio* is now the predicate of its implied participle, by analogy with *consulibus*.
- *omnia praeclara rara* now follows the syntactic-analysis page's table: *omnia* is adjectival to *praeclara*, which is the subject.
- Implied *sum* tokens now have lemma `sum`.

**Comments and reasoning:** for these 23 examples, the comment blocks and `reasoning` strings were rewritten to describe the new annotation. Other examples had their vocabulary updated. Tags naming retired semantic types were dropped.

### New examples

Six were added so the coverage test passes and the new constructions are exercised:

- `parataxis_precor_eam_videam`
- `agent_dative_caesari_omnia_agenda`
- `predicate_of_object_ciceronem_consulem` (predicate use 3)
- `predicate_passive_cicero_consul_creatus` (predicate use 4)
- `implied_substantive_quem_dii_amant`
- `passive_periphrastic_carthago_delenda_est`

`tests/fixtures/harvest.py` now emits `relations` and no semantic type.

## Tests

### Converted mechanically

- Old keyword arguments became `relations=[rel(...)]`.
- Old dict keys became `"relations"` lists.
- Hand-written file contents in `test_serialization.py` were rewritten in the new format.

### Updated for real behavior changes

- Tokens newly related in the gold examples now get verbal units, colors and depths.
- *exceptum* is a new depth-1 anchor.
- The implied *t8_implied* is now linked in displaCy.
- Abbreviations are now colored.
- Implied tokens can be repositioned on a round trip.
- Gerundives are now anchors.

### New tests

- **`tests/test_serialization.py`:** multi-relation rows round-trip; non-adjacent duplicate ids are rejected; disagreeing repeated rows are rejected; a half-filled relation is rejected; unknown labels are rejected; old-format files are rejected; a trailing implied token is included by `split_analysis_by_sentence()`.
- **`tests/test_validate.py`:** 'root' used with a label other than 'unit verb'; a bad id in any of a token's relations.
- **`tests/test_aat_bridge.py`:** agent and target by voice, for agent-dative, passive periphrastic, predicate uses 1–4 and a deponent lemma.
- **New file `tests/test_prompt_vocabulary.py`:** checks that the prompt names every relation label, syntactic type and token type in quotes, and never quotes a retired label.

## Not changed (see the questions note)

- **Neel's read-only files:** `quarto/` (including guide and tutorial pages with old field names, and `reference/relationshipvalues.qmd`), `README.md`, `releases.md`.
- **Generated docs:** `docs/`, not regenerated.
- **Version:** `pyproject.toml`, still 0.12.0.
- **Saved analyses** in `data/` and `quarto/sample_data/`, which are in the old format.
- **Stale optimizer output:** the GEPA-optimized program in `optimized/`.
- **`syntax_model.md`** itself.
