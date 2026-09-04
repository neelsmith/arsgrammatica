# Lewis & Short lookup (`arsgrammatica.lewis_short`)

Loads Lewis & Short's *A Latin Dictionary* from the delimited-text edition published at <https://shot.holycross.edu/lexica/ls-articles.cex>, and looks articles up by headword (`key` in that file -- called `lemma` here, matching `models.TokenAnalysis.lemma`'s own name for "dictionary headword, for lexical tokens").

## The file itself isn't in this repo

Like every other CEX corpus this codebase reads (`read_ctsdata()`'s own source files, saved analyses, ...), ls-articles.cex is supplied externally -- it isn't checked into the repo. It's also considerably bigger than anything else this codebase reads: 51,596 articles, ~28MB. Neel keeps a local copy in the git-ignored `scratch/` directory for local testing/use; pass its path to `LewisShortLexicon.from_file()`. `LewisShortLexicon.from_url()` (below) is the alternative for an environment with no local copy at all.

One practical note from building this: this sandbox's own network access couldn't reach `shot.holycross.edu` directly (a `curl`/`urllib` request there gets a 403 from the egress proxy, both from the cloud container and from the linked device's own shell), and the Chrome browser-automation extension wasn't connected either -- all three fetch paths were tried and failed before Neel just uploaded the file directly, the first time this module was built. That sandbox limitation is still in effect: `read_lewis_short_from_url()`/`LewisShortLexicon.from_url()` (below) are implemented and unit-tested against a mocked HTTP response, not verified end-to-end against the real endpoint from here -- see their own "Fetching from the stable URL" section for what to run yourself to close that gap.

## File shape (verified directly against the real file, not assumed)

A single header line

```
seq|urn|key|entry
```

immediately followed by one data row per article, four `|`-delimited columns -- no repeated header/block-label lines anywhere (unlike `ctsdata.py`'s own `#!ctsdata` block format), no blank lines in the middle. Confirmed by direct inspection of the real 51,597-line file: exactly one header occurrence, every one of the 51,596 data rows has exactly 4 columns, and no row has a blank `key` or `entry`.

- `seq`: a 1-based integer id. In the file as published it also happens to equal the row's own position, but `read_lewis_short()` doesn't require that -- only that it parses as an int.
- `urn`: a CITE2 urn (`urn:cite2:hmt:ls.markdown:n<seq-1>`), not a CTS urn like `ctsdata.py`'s own `urn` column -- so it gets no 5-part-colon-separated validation the way `read_ctsdata()` validates its own urns.
- `key`: the headword.
- `entry`: the article's full text, in Lewis & Short's own lightweight markup (backtick-quoted section labels like `` `I` ``/`` `I.A` ``, asterisk-wrapped Latin/italicized words like `*littera*`) -- left exactly as written, unparsed. Rendering that markup is a separate concern this module doesn't address.

### The homonym wrinkle in `key`

About 4,200 of the 51,596 keys (~8%) end in a digit -- Lewis & Short's own disambiguation for a headword they split into more than one article (e.g. `abdico1`/`abdico2`, two entirely different words that happen to be spelled alike). Verified directly: there is no *bare* `abdico` key alongside them -- only the numbered forms exist once a headword has more than one article, and every key in the file (numbered or not) is unique (zero exact duplicates across all 51,596). A caller looking up the bare lemma therefore gets no exact hit on a homonym-bearing headword at all -- see "Homonyms" under `lookup()` below for how that surfaces.

Keys are otherwise plain: no macrons or other diacritics anywhere in `key` (verified: zero non-ASCII characters across all keys), and zero case-insensitive collisions (no two distinct keys become equal when case-folded) -- both facts `_normalize_lemma()`'s own design leans on directly (see below).

## `LewisShortEntry`

```python
class LewisShortEntry(NamedTuple):
    seq: int
    urn: str
    key: str
    entry: str
```

A plain `NamedTuple`, not a pydantic model -- matching this codebase's existing convention for a data record nothing asks DSPy to generate or validate (see `GraphMetrics` in `graphs.py`, `LMCostSummary` in `lm_cost.py`), rather than `models.py`'s pydantic `BaseModel` subclasses, which are reserved for structures `dspy.Predict` itself produces.

## `read_lewis_short(path, delimiter="|")` / `read_lewis_short_from_url(url=LEWIS_SHORT_URL, *, delimiter="|", timeout=60.0)`

Two readers sharing one validator: `read_lewis_short()` opens a local file, `read_lewis_short_from_url()` fetches `url` over HTTP (`urllib.request.urlopen()`, stdlib only) -- both split the result into lines and hand them to the same private `_parse_lewis_short_lines()`, so there's exactly one place that knows the file's shape, not two copies that could drift apart. Either way the result is a flat `List[LewisShortEntry]`, in file order.

Validation (shared, so identical either way): raises `ValueError`, naming the offending line, for a missing/mismatched header, a row that isn't exactly 4 columns, a blank `key`/`entry`, or a `seq` that doesn't parse as an int; raises (rather than returning `[]`) if the source is empty or has a header but no data rows at all. Neither reader enforces one key per entry -- that's a lookup-index concern, not a row-well-formedness one (see `LewisShortLexicon.__init__()` below).

`read_lewis_short_from_url()` defaults to `LEWIS_SHORT_URL` (the module-level constant for the published location) and decodes the response body as UTF-8, matching the published file's own encoding (verified directly -- Lewis & Short's Greek quotations round-trip correctly under plain UTF-8 decoding, no `latin-1`/`cp1252` guessing needed). `timeout` (default 60s) is a socket timeout passed straight to `urlopen()`, sized generously for the file's real size (~28MB) rather than because the endpoint itself is slow. Network failures (`urllib.error.HTTPError` for a bad status, `urllib.error.URLError` for anything that never got an HTTP response at all) are NOT caught or translated -- they propagate as-is, so a caller already handling those two doesn't need a third exception type just for this function.

**Not verified against the real endpoint from this sandbox**: this sandbox's own network access (and the linked device's) both get a 403 from their egress proxy trying to reach `shot.holycross.edu` directly -- the same restriction noted above under "The file itself isn't in this repo". `read_lewis_short_from_url()` is implemented and unit-tested against a *mocked* `urlopen()` (`tests/test_lewis_short.py` monkeypatches it to return canned bytes, and checks the default url/timeout are actually used, a custom url/timeout are passed through, and malformed fetched content raises the same `ValueError`s the file-based reader would) -- but the real HTTP round-trip itself hasn't been exercised from here. One test, `test_network_fetch_of_the_real_dictionary`, is marked `@pytest.mark.network` (skipped by default -- see "Tests" below) and hits the real URL; running `pytest -m network` once from a network that can actually reach the endpoint is the way to close that gap. (Confirmed the marker itself is wired correctly by running it here anyway: it fails with exactly the expected `urllib.error.URLError: <urlopen error Tunnel connection failed: 403 Forbidden>` -- the sandbox's own known restriction, not a bug in the function.)

## `LewisShortLexicon`

```python
from arsgrammatica import LewisShortLexicon

lex = LewisShortLexicon.from_file("scratch/ls-articles.cex")   # or LewisShortLexicon(entries)
lex = LewisShortLexicon.from_url()                             # fetches LEWIS_SHORT_URL instead
len(lex)          # 51596
list(lex)          # every LewisShortEntry, in file order
```

Builds two indexes once, at construction: a literal `key -> entry` dict (for `get()`) and a normalized-key `-> [entries]` dict (for `lookup()`'s exact phase and as the fuzzy-matching candidate pool). Loading the real file takes about 1.5s.

`LewisShortLexicon.__init__()` raises `ValueError` if two entries share the same literal `key` -- naming both `seq` values -- since that would silently break `get()`'s one-key-one-entry contract. Never happens with the real file (verified: zero duplicate keys), but `read_lewis_short()` itself doesn't guard against it, so this is where it's actually caught.

### `get(key)`: literal, exact-only

```python
lex.get("amo")       # -> LewisShortEntry(key="amo", ...)
lex.get("abdico")    # -> None (no bare "abdico" key exists)
lex.get("AMO")       # -> None (get() is case-sensitive)
```

For a caller that already has an exact `key` string in hand (e.g. from a citation index, or from a previous `lookup()`'s own `match.entry.key`) and wants zero normalization or fuzzy fallback.

### `lookup(lemma, *, limit=5, cutoff=0.6)`: the general case

This is the "match and retrieve articles based on the headword" function Neel asked for: prefer an exact match, fall back to a ranked fuzzy match when there isn't one.

```python
lex.lookup("amo")     # -> [LewisShortMatch(entry=<amo>, score=1.0)]
lex.lookup("Amo")     # -> [LewisShortMatch(entry=<amo>, score=1.0)]  -- still exact
lex.lookup("amō")     # -> [LewisShortMatch(entry=<amo>, score=1.0)]  -- still exact
lex.lookup("amoo")    # -> [LewisShortMatch(entry=<amodo>, score=0.89), LewisShortMatch(entry=<amo>, score=0.86), ...]
lex.lookup("abdico")  # -> [LewisShortMatch(entry=<abdico1>, score=0.92), LewisShortMatch(entry=<abdico2>, score=0.92)]
```

Returns `List[LewisShortMatch]` -- `(entry, score)` pairs, `score` in `[0.0, 1.0]` -- always exactly `1.0` for an exact match and a genuine `difflib.SequenceMatcher` ratio (strictly `< 1.0`) for a fuzzy one. **Never a mix within one call**: an exact hit short-circuits fuzzy matching entirely, so a caller can tell which branch fired from `len(matches) == 1 and matches[0].score == 1.0` without a separate flag.

#### What counts as "exact"

Case- and diacritic-insensitive, via `_normalize_lemma()` (casefold + Unicode NFKD-decompose-and-drop-combining-marks) applied to both `lemma` and every `key` once, at construction. Two reasons this still counts as *exact* rather than a fuzzy tier of its own:

- Published `key` values contain no diacritics at all, so a query like `"amō"` has zero chance of a literal string match against `"amo"` even though it's unambiguously the same headword -- normalizing is what makes the obviously-right answer reachable at all, not a precision compromise.
- Casefolding never collides two different keys in the real data (verified: zero case-insensitive collisions across all 51,596 keys), so there's no precision actually lost by comparing case-insensitively.

If a caller genuinely wants literal, unnormalized matching, `get()` is there for that.

#### Fuzzy fallback

Without an exact match, `lemma` is ranked against every OTHER normalized key using stdlib `difflib` -- `get_close_matches()` for the fast initial pass, `SequenceMatcher.ratio()` to attach a real score to each of its (score-blind) results -- returning at most `limit` results scoring `>= cutoff`, highest first, ties broken by key for a deterministic order. An empty list means nothing cleared `cutoff` -- not an error.

No new dependency: stdlib `difflib` only, matching this codebase's minimal-dependency ethos (the only required dependencies are `dspy`, `pydantic`, `networkx`). Benchmarked directly against the real 51,596-key vocabulary: `get_close_matches()` alone runs in ~0.07-0.12s per query; scoring the returned handful of candidates afterward is effectively free. (A full unoptimized `SequenceMatcher.ratio()` pass over all 51,596 keys, with no `get_close_matches()` pre-filtering step, was also benchmarked for comparison -- about 0.45-0.5s per query -- which is why `lookup()` uses `get_close_matches()` for selection and only re-scores the small returned set, rather than scoring everything directly.)

#### Homonyms

A headword Lewis & Short split into homonyms (e.g. `abdico1`/`abdico2`) has no bare-lemma exact match at all, so looking it up lands in the fuzzy branch, where both numbered forms score identically (only the trailing digit differs from the query) and come back tied for first place. That's the correct, honest answer -- Lewis & Short's own spelling gives no way to prefer one over the other from the lemma alone -- not a bug to work around. A caller that wants a single answer regardless needs its own disambiguation on top (surrounding context, part of speech, ...); this module doesn't guess.

#### Blank lemma

`lookup("")` (or whitespace-only) raises `ValueError` -- nothing to match against.

## Fetching from the stable URL

`LewisShortLexicon.from_url(url=LEWIS_SHORT_URL, *, delimiter="|", timeout=60.0)` is `from_file()`'s sibling: `read_lewis_short_from_url(url, ...)` followed by `LewisShortLexicon(...)`, for loading straight from the published URL instead of a local file -- useful for an environment with no local copy of ls-articles.cex at all (unlike Neel's own `scratch/` copy). Same parameters, same exceptions, and the same "not verified against the real endpoint from this sandbox" caveat as `read_lewis_short_from_url()` itself (see above).

`LEWIS_SHORT_URL` (`"https://shot.holycross.edu/lexica/ls-articles.cex"`) is exported from the top-level package too, for a caller that wants to name/log/compare against it without reaching into a function signature's default.

## Tests

`tests/test_lewis_short.py` uses a small, hand-built 5-row fixture shaped like the real file (same convention `test_ctsdata.py` uses -- a hand-built fixture, not a real downloaded corpus) covering: a basic read in file order; every malformed-file error `read_lewis_short()` can raise (empty file, wrong/missing header, header with no data rows, wrong column count, blank key, blank entry, non-integer seq); a custom delimiter; `LewisShortLexicon.__init__()`'s duplicate-key check; `get()`'s literal-only behavior (case-sensitive, no homonym-bare-lemma match); and `lookup()`'s three real behaviors -- exact-match short-circuiting, case/diacritic-insensitive matching still counting as exact, and the fuzzy-ranked fallback including the homonym-tie case -- plus `limit`, the empty-result case, and the blank-lemma error.

`read_lewis_short_from_url()`/`from_url()` get their own four tests, all against a mocked `urllib.request.urlopen()` (a small `_FakeResponse` context-manager stand-in, `monkeypatch`ed in): the default `url`/`timeout` actually reach `urlopen()`, a custom `url`/`timeout` are passed through, malformed fetched content raises the same `ValueError` the file-based reader would, and `LewisShortLexicon.from_url()` itself builds a working lexicon from the mocked fetch. A fifth test, `test_network_fetch_of_the_real_dictionary`, is marked `@pytest.mark.network` and hits the real published URL -- skipped by default (`pytest.ini` now has `addopts = -m "not live and not network"`, a new `network` marker alongside the existing `live` one, since a real network fetch isn't "the real configured LM" `live` is specifically documented as) -- run it with `pytest -m network` from a network that can actually reach `shot.holycross.edu` to verify what the mocked tests can't.

24 tests total (20 + 4 mocked; the 5th, network-marked, is skipped by default), all passing; full suite at 1197 (1193 + 4, with 7 deselected -- 6 `live` + 1 `network`), no regressions. Re-ran the file-based reader against the real 51,596-entry file after refactoring `read_lewis_short()`/`read_lewis_short_from_url()` to share one `_parse_lewis_short_lines()` validator, to confirm the refactor changed nothing observable for the existing path.

## `marimo/lewis_short_lookup.py`

A no-LM notebook UI for `LewisShortLexicon`/`lookup()`: browse for a copy of `ls-articles.cex` (same `mo.ui.file_browser` single-file pattern every other notebook in this codebase uses, e.g. `latin_syntaxer_review.py`'s `analysis_file_browser`), type a headword into a single-line `mo.ui.text` box (mirroring `latin_syntaxer_workflow.py`'s own `urnbase`/`citation_context` inputs), and see the result. No `limit`/`cutoff` tuning UI -- `lookup()`'s own defaults (`limit=5, cutoff=0.6`) are used as-is, a deliberate scope decision matching this codebase's convention against adding UI for parameters nobody's asked to tune yet.

The file is only re-read/re-indexed when the file_browser's own selection changes, never on a headword lookup -- loading the real ~28MB/51,596-entry file takes about 1.5s, and that cost is paid once per file choice, not per keystroke or per lookup.

Three display states, matching `lookup()`'s own three outcomes:

- **Exact match** (`len(matches) == 1 and matches[0].score == 1.0`): the article is shown directly, no extra click needed.
- **Fuzzy fallback** (`len(matches) > 1`): a `mo.ui.dropdown` is built fresh from the ranked candidates (`"{key} (score {score:.2f})"` labels), with the top-ranked candidate preselected as `value` -- unlike e.g. `latin_syntaxer_review.py`'s own `sentence_dropdown` (which starts unselected), a lookup tool's whole point is showing its own best guess immediately rather than making the user re-click it. This is also what a homonym tie (`abdico1`/`abdico2` tied at the top for a bare `"abdico"` query) looks like: both show up as separate dropdown options at the same score, with the alphabetically-first one preselected -- the honest answer, since Lewis & Short's own spelling gives no way to prefer one over the other (see `lookup()`'s own "Homonyms" section above).
- **No match**: a `mo.callout(kind="warn")` naming the query, since nothing cleared `cutoff`.

The article itself is rendered via `mo.md()`, not escaped plain text -- Lewis & Short's own lightweight markup (backtick-quoted section labels like `` `I` ``/`` `I.A` ``, asterisk-wrapped Latin/italicized words) is already markdown-shaped (the CITE2 urn for the collection is even named `ls.markdown`), so `mo.md()` renders it as intended: section labels in monospace, italicized words in italics. A small number of entries contain a literal `_` or `[`/`]` that could occasionally be misread as markdown syntax of its own; verified directly that no entry starts with `#`, so no accidental heading is possible. A known, accepted limitation of rendering the file's own markup as markdown, not something the notebook works around.

No dedicated test file, matching this codebase's existing convention for marimo notebooks (none of them have one). Verified instead by: `py_compile` for basic syntax; `marimo export script` followed by `py_compile` of the exported script, to confirm the cell dependency graph resolves with no undefined variables; and a standalone smoke-test script that drives the notebook's own cell logic (load, exact match, case/diacritic-insensitive exact match, homonym-tie fuzzy fallback with correct preselection, no-match, blank input, no-lexicon-loaded) against the real 51,596-entry file, end to end outside the interactive marimo kernel. Full suite re-run afterward: still 1197 passed, 7 deselected -- a marimo notebook file isn't collected as tests on its own.
