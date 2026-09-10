import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo


    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Look up a headword in Lewis & Short
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > No LM access needed -- either browse for a local copy of `ls-articles.cex` (Lewis & Short's *A Latin Dictionary*, delimited-text edition -- see `notes/lewis_short.md` and `arsgrammatica/lewis_short.py`) or download it fresh from its published URL, then type a headword. An exact match (case- and diacritic-insensitive) is shown directly; anything else falls back to a ranked list of the closest headwords by spelling to choose from.
    """)
    return


@app.cell(hide_code=True)
def _(download_button, input_source, lexicon_file_browser, lexicon_url, mo):
    # Only the control(s) for the currently-chosen source are shown --
    # input_source itself always is, so switching sources is always one
    # click away. "Local file" (the default) shows the same file_browser
    # this notebook has always used; "Download from URL" shows the URL
    # field plus its own explicit Download trigger (see download_button's
    # own definition below for why a click, not a reactive fetch).
    if input_source.value == "Download from URL":
        source_controls = mo.vstack([input_source, lexicon_url, download_button])
    else:
        source_controls = mo.vstack([input_source, lexicon_file_browser])

    source_controls
    return


@app.cell(hide_code=True)
def _(input_source, lexicon, lexicon_error, mo):
    if lexicon_error is not None:
        lexicon_status = mo.callout(
            mo.md(f"Could not load a Lewis & Short lexicon from this source: {lexicon_error}"),
            kind="danger",
        )
    elif lexicon is None:
        if input_source.value == "Download from URL":
            lexicon_status = mo.md("*Enter a URL and click Download above to look up headwords.*")
        else:
            lexicon_status = mo.md("*Choose a copy of `ls-articles.cex` above to look up headwords.*")
    else:
        lexicon_status = mo.md(f"*{len(lexicon)} article(s) loaded.*")

    lexicon_status
    return


@app.cell(hide_code=True)
def _(headword_input):
    headword_input
    return


@app.cell(hide_code=True)
def _(match_status):
    match_status
    return


@app.cell(hide_code=True)
def _(candidate_dropdown):
    candidate_dropdown
    return


@app.cell(hide_code=True)
def _(article_display):
    article_display
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html("<hr/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Implementation
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI selections
    """)
    return


@app.cell
def _(mo):
    # Chooses which of the two loading paths below (lexicon_file_browser or
    # lexicon_url/download_button) actually feeds the lexicon cell --
    # "Local file" is the default, matching this notebook's original,
    # only behavior before it could reach the published URL at all.
    input_source = mo.ui.radio(
        options=["Local file", "Download from URL"],
        value="Local file",
        inline=True,
        label="*Lexicon source*:",
    )
    return (input_source,)


@app.cell
def _(Path, mo):
    # Same file_browser pattern every other notebook in this codebase uses
    # for a single required input file -- see e.g.
    # latin_syntaxer_review.py's own analysis_file_browser for the full
    # rationale (selecting a single FILE by clicking it just works, unlike
    # mo.ui.file_browser's "directory" selection mode). ls-articles.cex
    # isn't checked into this repo (it's ~28MB -- see notes/lewis_short.md)
    # so there's no default path to preselect; Neel's own copy lives in
    # the git-ignored scratch/ directory. Only consulted when
    # input_source.value == "Local file" (the default) -- see the lexicon
    # cell below.
    lexicon_file_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Lewis & Short source file* (ls-articles.cex):",
    )
    return (lexicon_file_browser,)


@app.cell
def _(LEWIS_SHORT_URL, mo):
    # Prefilled with the dictionary's own published, stable location
    # (LEWIS_SHORT_URL -- see arsgrammatica/lewis_short.py's own module
    # docstring) but editable, for a mirror or alternate copy sharing the
    # same file shape. Only consulted when input_source.value ==
    # "Download from URL" -- see the lexicon cell below.
    lexicon_url = mo.ui.text(value=LEWIS_SHORT_URL, full_width=True, label="*Lexicon URL*:")
    return (lexicon_url,)


@app.cell
def _(lexicon_url, mo):
    # A run_button, not a reactive fetch-on-every-keystroke: downloading
    # the real ~28MB/51,596-entry file over HTTP (read_lewis_short_from_url()'s
    # own 60s default timeout) is far too expensive to trigger on every
    # character typed into lexicon_url above. Same convention
    # latin_syntaxer_ctsdata.py's own analyze_button uses: .value is True
    # for exactly the one reactive cycle triggered by a click; a NEW
    # instance (value reset to False) is created whenever lexicon_url's
    # own text changes, so editing the URL always requires a fresh,
    # deliberate click rather than silently reusing a previous one.
    download_button = mo.ui.run_button(
        label="Download",
        disabled=not lexicon_url.value.strip(),
    )
    return (download_button,)


@app.cell
def _(LewisShortLexicon, download_button, input_source, lexicon_file_browser, lexicon_url):
    # Two independent loading paths, chosen by input_source's own radio
    # above -- a local file (lexicon_file_browser, the default) or a fresh
    # HTTP download (lexicon_url + download_button). Only one ever runs.
    # The local-file path re-triggers this cell on every NEW selection,
    # same convention every other file_browser-driven notebook in this
    # codebase uses (see e.g. latin_syntaxer_review.py's own analysis_path
    # cell); the URL path only runs on an actual Download click
    # (download_button.value is True for exactly that one reactive cycle
    # -- see that widget's own definition above), never on a keystroke in
    # lexicon_url or an unrelated reactive rerun elsewhere in the
    # notebook. Either way, loading the real ~28MB/51,596-entry lexicon
    # takes about 1.5s locally (or however long the download itself takes,
    # remotely) -- this cell only re-runs when its own trigger fires,
    # never on a headword lookup below, so repeated lookups against the
    # same lexicon pay that cost exactly once, not per lookup.
    lexicon = None
    lexicon_error = None
    if input_source.value == "Download from URL":
        if download_button.value and lexicon_url.value.strip():
            try:
                lexicon = LewisShortLexicon.from_url(lexicon_url.value)
            except (ValueError, OSError) as e:
                lexicon_error = str(e)
    else:
        lexicon_path = lexicon_file_browser.path(index=0)
        if lexicon_path is not None:
            try:
                lexicon = LewisShortLexicon.from_file(str(lexicon_path))
            except (ValueError, OSError) as e:
                lexicon_error = str(e)
    return lexicon, lexicon_error


@app.cell
def _(mo):
    # Freeform single-headword entry -- mirrors latin_syntaxer_textinput.py's
    # own mo.ui.text() inputs (urnbase/citation_context).
    headword_input = mo.ui.text(
        value="",
        placeholder="amo",
        label="*Headword (lemma)*:",
    )
    return (headword_input,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Lookup
    """)
    return


@app.cell
def _(headword_input, lexicon):
    # lookup()'s own defaults (limit=5, cutoff=0.6 -- see
    # arsgrammatica/lewis_short.py and notes/lewis_short.md) are used as-is.
    # Guarded on a non-blank headword (lookup() itself raises ValueError on
    # a blank one -- see that function's own docstring) and on a lexicon
    # actually being loaded, so this cell quietly does nothing until both
    # are true, rather than raising on first load before any file is
    # chosen or before anything's been typed.
    matches = []
    if lexicon is not None and headword_input.value.strip():
        matches = lexicon.lookup(headword_input.value)
    return (matches,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(headword_input, lexicon, matches, mo):
    if lexicon is None:
        match_status = mo.md("")
    elif not headword_input.value.strip():
        match_status = mo.md("*Enter a headword above to look it up.*")
    elif not matches:
        match_status = mo.callout(
            mo.md(f"No article matches `{headword_input.value}` closely enough to suggest."),
            kind="warn",
        )
    elif len(matches) == 1 and matches[0].score == 1.0:
        match_status = mo.md(f"*Exact match for `{headword_input.value}`.*")
    else:
        match_status = mo.md(
            f"*No exact match for `{headword_input.value}` -- {len(matches)} closest "
            "headword(s) by spelling, ranked below.*"
        )
    return (match_status,)


@app.cell
def _(matches, mo):
    # Only shown when there's more than one candidate to choose from -- an
    # exact match (the common case) is a single result and goes straight
    # to the article display below with no extra click needed (same
    # None-when-not-applicable convention as e.g. latin_syntaxer_review.py's
    # own maxdepth, which is also sometimes None and displayed via the
    # identical bare-expression pattern at the top of this file). Options
    # are rebuilt fresh from `matches` every time it changes, with the
    # TOP-ranked candidate preselected as `value` -- unlike e.g. that same
    # notebook's sentence_dropdown (which starts unselected), a lookup
    # tool's whole point is showing its own best guess immediately, not
    # making the user re-click it.
    candidate_dropdown = None
    if len(matches) > 1:
        options = {f"{m.entry.key} (score {m.score:.2f})": i for i, m in enumerate(matches)}
        candidate_dropdown = mo.ui.dropdown(
            options=options,
            value=next(iter(options)),
            label="*Candidate*:",
        )
    return (candidate_dropdown,)


@app.cell
def _(candidate_dropdown, matches):
    # The match currently on display: the dropdown's own selection when
    # there's more than one candidate to choose from, otherwise the lone
    # match (an exact hit), or None before anything resolves at all.
    selected_match = None
    if candidate_dropdown is not None and candidate_dropdown.value is not None:
        selected_match = matches[candidate_dropdown.value]
    elif len(matches) == 1:
        selected_match = matches[0]
    return (selected_match,)


@app.cell
def _(mo, selected_match):
    # entry text is rendered as MARKDOWN, not escaped plain text -- Lewis &
    # Short's own lightweight markup (backtick-quoted section labels like
    # `I`/`I.A`, asterisk-wrapped Latin/italicized words) is deliberately
    # markdown-shaped already (its own urn even names the collection
    # "ls.markdown" -- see lewis_short.py's module docstring), so mo.md()
    # renders it as intended: section labels in monospace, italicized
    # words in italics. A small number of entries contain a literal `_`
    # or `[`/`]` that could occasionally be misread as markdown syntax of
    # its own (verified directly: no entry starts with `#`, so no
    # accidental heading is possible) -- a known, accepted limitation of
    # rendering the file's own markup as markdown, not something this
    # notebook works around.
    if selected_match is None:
        article_display = mo.md("")
    else:
        entry = selected_match.entry
        article_display = mo.md(
            f"### {entry.key}\n\n"
            f"*urn*: `{entry.urn}` &nbsp; *seq*: {entry.seq}\n\n"
            f"{entry.entry}"
        )
    return (article_display,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Imports
    """)
    return


@app.cell
def _():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import LEWIS_SHORT_URL, LewisShortLexicon

    return LEWIS_SHORT_URL, LewisShortLexicon, Path


if __name__ == "__main__":
    app.run()
