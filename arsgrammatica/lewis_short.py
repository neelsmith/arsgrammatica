"""
Loads Lewis & Short's *A Latin Dictionary* from the delimited-text edition
published at https://shot.holycross.edu/lexica/ls-articles.cex, and looks
articles up by headword ('key' in that file -- called `lemma` here, matching
`models.TokenAnalysis.lemma`'s own name for the same idea: "dictionary
headword, for lexical tokens").

File shape (verified directly against the real ~28MB / 51,596-row file, not
assumed): a single header line

    seq|urn|key|entry

immediately followed by one data row per article, four '|'-delimited
columns, no repeated header/block-label lines anywhere in the file (unlike
ctsdata.py's own '#!ctsdata' block format) and no blank lines in the middle.
`seq` is a 1-based integer id (in the file as published, it also happens to
equal the row's own position, but read_lewis_short() doesn't require that --
only that it parses as an int); `urn` is a CITE2 urn (`urn:cite2:hmt:
ls.markdown:n<seq-1>`), not a CTS urn like ctsdata.py's own `urn` column, so
it gets no 5-part-colon-separated validation here; `key` is the headword;
`entry` is the article's full text, in Lewis & Short's own lightweight
markup (backtick-quoted section labels like `` `I` ``/`` `I.A` ``,
asterisk-wrapped Latin/italicized words like `*littera*`) -- left exactly as
written, unparsed, since rendering that markup is a separate concern this
module doesn't address.

Every row has exactly 4 columns and a non-blank key/entry in the published
file, but read_lewis_short() validates this the same way ctsdata.py
validates its own rows, rather than assuming it: malformed rows raise
ValueError naming the offending line, rather than being silently skipped or
guessed at.

`key` itself has one wrinkle worth knowing before writing lookup code
against it: about 4,200 of the 51,596 keys (roughly 8%) end in a digit --
homonym disambiguation for headwords Lewis & Short split into more than one
article (e.g. `abdico1`/`abdico2`, two entirely different words that happen
to be spelled alike). There is no *bare* `abdico` key alongside them -- only
the numbered forms exist once a headword has more than one article. A
caller looking up the bare lemma therefore won't get an exact hit on a
homonym-bearing headword at all; see LewisShortLexicon.lookup()'s own
docstring for how that surfaces (both numbered forms come back tied for
first place in the fuzzy-ranked fallback, which -- since Lewis & Short
themselves give no way to disambiguate from the spelling alone -- is the
honest answer, not a bug to work around).
"""

import difflib
import unicodedata
import urllib.request
from typing import Dict, Iterator, List, NamedTuple, Optional

LEWIS_SHORT_HEADER_COLUMNS = ("seq", "urn", "key", "entry")

# The stable, published location of the file this whole module is built
# around -- read_lewis_short_from_url()'s own default `url`, and
# LewisShortLexicon.from_url()'s by extension. A module-level constant
# rather than a string repeated at each call site, so a caller wanting to
# just name/log/compare against it doesn't need to reach into a function
# signature's default to find it.
LEWIS_SHORT_URL = "https://shot.holycross.edu/lexica/ls-articles.cex"


class LewisShortEntry(NamedTuple):
    """One row of the ls-articles.cex file, essentially unchanged -- a
    plain NamedTuple, not a pydantic model, matching this codebase's own
    convention for a data record that never needs DSPy to generate or
    validate it (see GraphMetrics in graphs.py, LMCostSummary in
    lm_cost.py) rather than models.py's pydantic BaseModel subclasses,
    which are reserved for structures dspy.Predict itself produces."""

    seq: int
    urn: str
    key: str
    entry: str


class LewisShortMatch(NamedTuple):
    """One candidate returned by LewisShortLexicon.lookup(): the matched
    entry, plus a similarity score in [0.0, 1.0] -- always exactly 1.0 for
    an exact (case/diacritic-insensitive) match, and a difflib
    SequenceMatcher ratio for a fuzzy-fallback candidate. Never a mix of
    the two within one lookup() call: an exact hit short-circuits fuzzy
    matching entirely (see lookup()'s own docstring)."""

    entry: LewisShortEntry
    score: float


def _parse_lewis_short_lines(raw_lines: List[str], delimiter: str, source: str) -> List[LewisShortEntry]:
    """Shared row-parsing/validation for read_lewis_short() (a local file)
    and read_lewis_short_from_url() (a fetched HTTP response) -- the file's
    shape is the same either way, so there's exactly one place that knows
    it. `source` is only used for error messages (a path or a URL,
    whichever the caller has); `raw_lines` is already split on newlines,
    with no assumption about where they came from.

    Raises ValueError, naming the offending line, for: a missing or
    mismatched header line (must be exactly `delimiter.join(
    LEWIS_SHORT_HEADER_COLUMNS)`); a data row that isn't exactly 4 columns;
    a blank `key` or `entry` column; or a `seq` column that doesn't parse
    as an int. Raises ValueError (not returning an empty list) if there's
    no content at all, or a header line but no data rows, so a caller
    can't mistake "wrong/empty source" for "lexicon with zero entries".
    Does NOT require duplicate-free keys -- that's LewisShortLexicon.
    __init__()'s job (see its own docstring), not a row-parsing concern.
    """
    expected_header = delimiter.join(LEWIS_SHORT_HEADER_COLUMNS)

    non_blank = [(i, line) for i, line in enumerate(raw_lines, start=1) if line.strip() != ""]
    if not non_blank:
        raise ValueError(f"{source!r} is empty")

    header_line_no, header_line = non_blank[0]
    if header_line != expected_header:
        raise ValueError(
            f"line {header_line_no}: expected header {expected_header!r}, got {header_line!r}"
        )

    entries: List[LewisShortEntry] = []
    for line_no, line in non_blank[1:]:
        parts = line.split(delimiter)
        if len(parts) != 4:
            raise ValueError(
                f"line {line_no}: row has {len(parts)} column(s) (delimiter "
                f"{delimiter!r}), expected 4: {line!r}"
            )
        seq_text, urn, key, entry = parts

        try:
            seq = int(seq_text)
        except ValueError:
            raise ValueError(f"line {line_no}: seq {seq_text!r} is not an integer") from None

        if key == "":
            raise ValueError(f"line {line_no}: row has an empty key column")
        if entry == "":
            raise ValueError(f"line {line_no}: row has an empty entry column")

        entries.append(LewisShortEntry(seq=seq, urn=urn, key=key, entry=entry))

    if not entries:
        raise ValueError(f"{source!r} has a header line but no data rows")

    return entries


def read_lewis_short(path: str, delimiter: str = "|") -> List[LewisShortEntry]:
    """Read every row of `path` (the ls-articles.cex file, or anything
    sharing its exact 4-column shape) into a flat list of LewisShortEntry,
    in file order.

    `delimiter` is the column separator, for both the header line and each
    data row -- '|' by default, matching this file's own published format
    and every other serialized format in this codebase. There is no
    escaping mechanism for whichever character is chosen (same caveat
    ctsdata.py's and serialization.py's own docstrings note): pick a
    `delimiter` that can't appear in `entry`'s own text if '|' ever does.

    See _parse_lewis_short_lines() for exactly what counts as malformed
    (same validation either way) -- this function only adds the "read a
    local file" half; read_lewis_short_from_url() is its "fetch over HTTP
    instead" sibling, sharing that same validation.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    return _parse_lewis_short_lines(raw_lines, delimiter, source=path)


def read_lewis_short_from_url(
    url: str = LEWIS_SHORT_URL, *, delimiter: str = "|", timeout: float = 60.0
) -> List[LewisShortEntry]:
    """Fetch `url` (the published ls-articles.cex file at LEWIS_SHORT_URL
    by default) over HTTP and parse it exactly like read_lewis_short()
    does for a local file -- same validation, same ValueError conditions
    (see _parse_lewis_short_lines()), naming `url` instead of a path when
    something's wrong with the content.

    The response body is decoded as UTF-8 (matching the published file's
    own encoding -- verified directly, not assumed: Lewis & Short's
    Greek quotations and other non-ASCII text round-trip correctly under
    plain UTF-8 decoding). `timeout` is a socket timeout in seconds passed
    straight to urllib.request.urlopen() -- 60s by default, generously
    sized for the published file's real size (~28MB, 51,596 entries) over
    an ordinary connection, not because the endpoint itself is typically
    slow to respond.

    Raises whatever urllib.request.urlopen() itself raises for a network
    failure -- urllib.error.HTTPError for a non-2xx response,
    urllib.error.URLError for anything that never got an HTTP response at
    all (DNS failure, connection refused, timeout) -- deliberately NOT
    caught or translated into some other exception type here, so a caller
    already handling those two (or letting them propagate) doesn't need a
    third, different exception type just for this one function.

    I couldn't verify this function against the real endpoint myself: this
    sandbox's own network access, and the linked device's, both got a 403
    from their egress proxy trying to reach shot.holycross.edu directly
    (see notes/lewis_short.md) -- so this is implemented and unit-tested
    against a mocked HTTP response (tests/test_lewis_short.py), not run
    end-to-end against the real file. Run its `network`-marked test
    yourself once (`pytest -m network`) to confirm it actually reaches the
    real file from a network that can.
    """
    with urllib.request.urlopen(url, timeout=timeout) as response:
        raw_bytes = response.read()

    raw_lines = raw_bytes.decode("utf-8").splitlines()
    return _parse_lewis_short_lines(raw_lines, delimiter, source=url)


def _normalize_lemma(s: str) -> str:
    """Casefold + strip diacritics (Unicode NFKD-decompose, then drop
    combining marks) -- used to decide what counts as an "exact" match in
    LewisShortLexicon.lookup(), and as the basis for its fuzzy fallback.

    Two reasons this counts as "exact" rather than a separate fuzzy tier:
    published `key` values themselves contain NO diacritics at all
    (verified directly against the real file -- proper nouns are
    capitalized, e.g. 'Aaron', but nothing is macron-marked), so a query
    like 'amō' (long stem vowel written out) has no chance of a literal
    string match against 'amo' even though it's unambiguously the same
    headword; and casefolding never collides two DIFFERENT keys in the
    real data (verified: zero case-insensitive collisions across all
    51,596 keys), so normalizing before comparing loses no precision here.
    A caller that genuinely wants literal, unnormalized key lookup instead
    has LewisShortLexicon.get() for that.
    """
    decomposed = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold()


class LewisShortLexicon:
    """Lewis & Short's *A Latin Dictionary*, loaded once from
    ls-articles.cex (or any file read_lewis_short() accepts), indexed for
    two kinds of lookup: get() for a literal, unnormalized `key` string
    you already have exactly right, and lookup() for the general case --
    "what article, if any, matches this lemma" -- covering typos, case,
    and macron differences via a fuzzy-ranked fallback.
    """

    def __init__(self, entries: List[LewisShortEntry]):
        self._entries: List[LewisShortEntry] = list(entries)

        self._by_key: Dict[str, LewisShortEntry] = {}
        self._by_normalized: Dict[str, List[LewisShortEntry]] = {}
        for e in self._entries:
            if e.key in self._by_key:
                other = self._by_key[e.key]
                raise ValueError(
                    f"duplicate key {e.key!r} (seq {other.seq} and seq {e.seq}) -- "
                    "LewisShortLexicon needs one entry per key to build its lookup index"
                )
            self._by_key[e.key] = e
            self._by_normalized.setdefault(_normalize_lemma(e.key), []).append(e)

        # The candidate pool difflib.get_close_matches() ranks against in
        # lookup()'s fuzzy fallback -- computed once here, not per call.
        self._normalized_keys: List[str] = list(self._by_normalized.keys())

    @classmethod
    def from_file(cls, path: str, delimiter: str = "|") -> "LewisShortLexicon":
        """Convenience constructor: read_lewis_short(path, delimiter=delimiter)
        followed by LewisShortLexicon(...) -- the common case of loading
        straight from a file on disk rather than an already-built entry list."""
        return cls(read_lewis_short(path, delimiter=delimiter))

    @classmethod
    def from_url(
        cls, url: str = LEWIS_SHORT_URL, *, delimiter: str = "|", timeout: float = 60.0
    ) -> "LewisShortLexicon":
        """Convenience constructor: read_lewis_short_from_url(url, ...)
        followed by LewisShortLexicon(...) -- fetches the dictionary over
        HTTP (from LEWIS_SHORT_URL, the published location, by default)
        rather than reading a local file (from_file()'s job). Same
        parameters, same exceptions, and the same "not verified against
        the real endpoint from this sandbox" caveat as
        read_lewis_short_from_url() itself -- see that function's own
        docstring."""
        return cls(read_lewis_short_from_url(url, delimiter=delimiter, timeout=timeout))

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[LewisShortEntry]:
        return iter(self._entries)

    def get(self, key: str) -> Optional[LewisShortEntry]:
        """Literal, case-sensitive, diacritic-sensitive lookup by `key` --
        exactly the column-3 value, homonym digit suffix and all (e.g.
        'abdico1', not 'abdico'). None if `key` isn't in the lexicon.

        Use this when you already have an exact key in hand (e.g. from a
        citation index, or from a previous lookup()'s own
        `match.entry.key`); use lookup() instead for anything that might
        need normalization or fuzzy matching."""
        return self._by_key.get(key)

    def lookup(self, lemma: str, *, limit: int = 5, cutoff: float = 0.6) -> List[LewisShortMatch]:
        """Find the article(s) matching `lemma`, preferring an exact match
        and falling back to a ranked fuzzy match only when there isn't one.

        "Exact" here means case- and diacritic-insensitive (see
        _normalize_lemma()'s own docstring for why that still counts as
        exact rather than fuzzy) -- so 'amo', 'Amo', and 'amō' all exact-
        match the same 'amo' entry. When an exact match is found, fuzzy
        matching never runs at all: the result is exactly that entry (or,
        in the -- currently nonexistent in the real data, but not assumed
        away -- case of two keys colliding once normalized, every one of
        them) at score 1.0, sorted by key for a deterministic order.

        Without an exact match, `lemma` is ranked by fuzzy similarity
        (difflib's SequenceMatcher.ratio(), via get_close_matches() for
        the initial fast pass -- stdlib only, no new dependency, and fast
        enough in practice: under ~0.15s per query benchmarked against the
        real 51,596-key vocabulary) against every OTHER normalized key in
        the lexicon, returning at most `limit` results with score >=
        `cutoff`, highest score first (ties broken by key, for a
        deterministic order). An empty list means nothing scored at or
        above `cutoff` -- not an error.

        A headword Lewis & Short split into homonyms (e.g. 'abdico1' /
        'abdico2' -- see this module's own docstring) has no bare-lemma
        exact match at all, so looking up 'abdico' lands in the fuzzy
        branch, where both numbered forms score identically (only the
        trailing digit differs) and come back tied for first place. That
        is the correct, honest answer -- Lewis & Short's own spelling
        gives no way to pick one over the other -- not a bug: a caller
        that wants a single answer regardless needs its own
        disambiguation logic (surrounding context, part of speech, ...)
        layered on top of this.

        Raises ValueError if `lemma` is blank (nothing to match against).
        """
        if not lemma.strip():
            raise ValueError("lemma must not be blank")

        normalized = _normalize_lemma(lemma)

        exact = self._by_normalized.get(normalized)
        if exact:
            return [LewisShortMatch(e, 1.0) for e in sorted(exact, key=lambda e: e.key)]

        close = difflib.get_close_matches(normalized, self._normalized_keys, n=limit, cutoff=cutoff)
        matches: List[LewisShortMatch] = []
        for candidate in close:
            ratio = difflib.SequenceMatcher(None, candidate, normalized).ratio()
            for e in self._by_normalized[candidate]:
                matches.append(LewisShortMatch(e, ratio))
        matches.sort(key=lambda m: (-m.score, m.entry.key))
        return matches[:limit]
