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
    # Analyze specific passages from a CEX corpus, by id
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > Read citable text from a delimited-text (CEX) file, then type or paste the exact list of passage ids to analyze together. This is the same underlying analysis latin_syntaxer_ctsdata.py's own multiselect menu offers -- use this notebook instead when you already know which ids you want (e.g. from a list of ids some other process produced, like utilities/group_ctsdata_by_sentence.py's own output) rather than picking them off a menu.
    """)
    return


@app.cell(hide_code=True)
def _(ctsdata_file_browser):
    ctsdata_file_browser
    return


@app.cell(hide_code=True)
def _(ctsdata_error, ctsdata_rows, mo):
    if ctsdata_error is not None:
        ctsdata_status = mo.callout(
            mo.md(f"Could not read this file as a `#!ctsdata` source: {ctsdata_error}"),
            kind="danger",
        )
    elif not ctsdata_rows:
        ctsdata_status = mo.md("*Choose a source data file above to see its available passage ids.*")
    else:
        ctsdata_status = mo.md(f"## Passage selection\n\n*{len(ctsdata_rows)} passage(s) loaded from this file -- see the reference list below for their ids.*")

    ctsdata_status
    return


@app.cell(hide_code=True)
def _(available_ids_display):
    available_ids_display
    return


@app.cell(hide_code=True)
def _(passage_ids_input):
    passage_ids_input
    return


@app.cell(hide_code=True)
def _(analyze_button, id_status, mo):
    mo.vstack([id_status, analyze_button])
    return


@app.cell(hide_code=True)
def _(rawpreview):
    rawpreview
    return


@app.cell(hide_code=True)
def _(mo, results):
    mo.md("**Discussion**:\n\n" + "\n\n".join(f"> {result.reasoning}" for result in results))
    return


@app.cell(hide_code=True)
def _(psghtml):
    psghtml
    return


@app.cell(hide_code=True)
def _(vuhtml):
    vuhtml
    return


@app.cell(hide_code=True)
def _(maxdepth):
    maxdepth
    return


@app.cell(hide_code=True)
def _(indentpsg):
    indentpsg
    return


@app.cell(hide_code=True)
def _(diagram, mo):
    mo.mermaid(diagram)
    return


@app.cell(hide_code=True)
def _(analysis_warnings, download_widget, mo, save_extension):
    mo.vstack(
        [
            mo.hstack([save_extension, download_widget], justify="start"),
        ]
        + (
            [mo.callout(mo.md("\n".join(f"- {w}" for w in analysis_warnings)), kind="warn")]
            if analysis_warnings
            else []
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    seetokens = mo.ui.checkbox(label="*See list of tokens*")
    seecost = mo.ui.checkbox(label="*See cost*")
    seeprompts = mo.ui.checkbox(label="*See prompts*")
    # Same rationale as latin_syntaxer_ctsdata.py's identical checkbox --
    # dspy.LM's own response cache would otherwise silently replay an
    # earlier result for the exact same id selection instead of hitting
    # the LM again.
    disable_cache = mo.ui.checkbox(label="*Disable LM cache (debugging)*")
    mo.hstack([seetokens, seeprompts, seecost, disable_cache], justify="start")
    return disable_cache, seecost, seeprompts, seetokens


@app.cell(hide_code=True)
def _(finaltokens, seetokens):
    tokendisplay = None
    if seetokens.value:
        tokendisplay = finaltokens

    tokendisplay
    return


@app.cell(hide_code=True)
def _(cost_summary, format_lm_cost, mo, seecost):
    costdisplay = None
    if seecost.value:
        costdisplay = mo.md(f"**LM cost so far**: {format_lm_cost(cost_summary)}")
    costdisplay
    return


@app.cell(hide_code=True)
def _(dspy, seeprompts):
    prompts = None
    if seeprompts.value:
        prompts = dspy.inspect_history()
    prompts
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
    ## UI selections for analysis
    """)
    return


@app.cell
def _(ctsdata_file_browser, read_ctsdata):
    # Choose file with CEX source data.
    # Re-read the file every time the file_browser's own selection changes.
    ctsdata_path = ctsdata_file_browser.path(index=0)
    ctsdata_rows = []
    ctsdata_error = None
    if ctsdata_path is not None:
        try:
            ctsdata_rows = read_ctsdata(str(ctsdata_path))
        except (ValueError, OSError) as e:
            ctsdata_error = str(e)
    return ctsdata_error, ctsdata_rows


@app.cell
def _(Path, mo):
    # Same file_browser pattern latin_syntaxer_ctsdata.py uses -- see that
    # notebook's own comment for why a file_browser (rather than a typed
    # path) is used here.
    ctsdata_file_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Source data file*:",
    )
    return (ctsdata_file_browser,)


@app.function
def citation_suffix(citation):
    """The final segment of a CitedText's own `citation` -- see
    latin_syntaxer_ctsdata.py's identical helper for the full rationale.
    Purely a shorter display label; the full `citation` is still what's
    actually typed into the id text box and passed to
    analyze_selected_passages()."""
    return citation.rpartition(":")[-1]


@app.function
def parse_passage_ids(raw_text):
    """Parse a free-form list of passage ids out of one text_area's own
    value: split on whitespace (any run of spaces, tabs, and/or
    newlines), same as Python's own str.split() with no argument -- so
    ids can be entered one per line, space-separated on a single line, or
    any mix of both. This is deliberately whitespace-, not comma-,
    delimited: it's meant to accept a line of
    utilities/group_ctsdata_by_sentence.py's own output (space-joined by
    default -- see that script's own docstring) pasted in directly,
    without needing to reformat it first. A CTS URN never contains
    whitespace, so this never splits an id in half. Preserves
    first-occurrence order, though that order doesn't actually matter to
    analysis: analyze_selected_passages() always analyzes selected
    passages in the SOURCE file's own order, never the order ids are
    listed here (see that function's own docstring, and
    notes/passage_selection.md, for why)."""
    return raw_text.split()


@app.cell
def _(ctsdata_rows, mo):
    # A reference listing of every id actually available in the loaded
    # file, so there's somewhere to copy ids from -- unlike
    # latin_syntaxer_ctsdata.py's menu-driven selection, this notebook has
    # no menu of its own; the id text box below is freeform.
    if ctsdata_rows:
        _lines = [
            f"- `{row.citation}` -- {row.text[:60]}{'…' if len(row.text) > 60 else ''}"
            for row in ctsdata_rows
        ]
        available_ids_display = mo.md(
            "**Available passage ids in this file:**\n\n" + "\n".join(_lines)
        )
    else:
        available_ids_display = mo.md("")
    return (available_ids_display,)


@app.cell
def _(mo):
    # Freeform id entry, rather than latin_syntaxer_ctsdata.py's multiselect
    # menu -- the whole point of this notebook is analyzing a list of ids
    # already in hand, most directly a line pasted straight from
    # utilities/group_ctsdata_by_sentence.py's own space-delimited stdout
    # output (see parse_passage_ids() below), rather than picking ids off
    # a menu one at a time.
    passage_ids_input = mo.ui.text_area(
        value="",
        full_width=True,
        rows=4,
        placeholder="urn:cts:...:1.1 urn:cts:...:1.2 urn:cts:...:1.3",
        label="*Passage id(s)* -- separated by spaces and/or newlines "
              "(paste a line of utilities/group_ctsdata_by_sentence.py's "
              "own output directly):",
    )
    return (passage_ids_input,)


@app.cell
def _(passage_ids_input):
    parsed_passage_ids = parse_passage_ids(passage_ids_input.value)
    return (parsed_passage_ids,)


@app.cell
def _(ctsdata_rows, parsed_passage_ids):
    # Mirrors analyze_selected_passages()'s own selection filter (see
    # pipeline.py) -- kept here separately, rather than reusing that
    # function's return value directly, purely so the raw-text preview and
    # download-filename cells below have the actual selected CitedText
    # rows to work with even before the Analyze button is clicked. The
    # real selection AND validation still happen inside
    # analyze_selected_passages() itself when Analyze runs; this is
    # display-only.
    _wanted = set(parsed_passage_ids)
    selected_rows = [row for row in ctsdata_rows if row.citation in _wanted]
    return (selected_rows,)


@app.cell
def _(ctsdata_rows, parsed_passage_ids):
    # Ids typed above that don't match any passage in the loaded file --
    # computed up front so the Analyze button can stay disabled and the id
    # status line can name them immediately, rather than waiting for
    # analyze_selected_passages() to raise ValueError only after a click.
    _known_ids = {row.citation for row in ctsdata_rows}
    missing_ids = sorted({pid for pid in parsed_passage_ids if pid not in _known_ids})
    return (missing_ids,)


@app.cell
def _(ctsdata_rows, missing_ids, mo, parsed_passage_ids, selected_rows):
    if not ctsdata_rows:
        id_status = mo.md("*Choose a source data file above first.*")
    elif not parsed_passage_ids:
        id_status = mo.md("*Enter one or more passage ids above (see the reference list) to select passages.*")
    elif missing_ids:
        id_status = mo.callout(
            mo.md(
                "Unknown passage id(s), not found in this file: "
                + ", ".join(f"`{m}`" for m in missing_ids)
            ),
            kind="danger",
        )
    else:
        id_status = mo.md(
            f"*{len(selected_rows)} passage(s) recognized -- will be analyzed together, "
            "in the source file's own order.*"
        )
    return (id_status,)


@app.cell
def _(ctsdata_rows, id_status, mo, missing_ids, parsed_passage_ids):
    # A new instance is created (and analyze_button.value resets to False)
    # every time the id text box or the loaded file changes, same
    # rationale as latin_syntaxer_ctsdata.py's own analyze_button -- so
    # editing the id list always requires a fresh, deliberate Analyze
    # click rather than silently re-using a previous click.
    analyze_button = mo.ui.run_button(
        label="Analyze",
        disabled=not parsed_passage_ids or bool(missing_ids) or not ctsdata_rows,
    )
    return (analyze_button,)


@app.cell
def _(finaltokens, max_subordination_depth, mo):
    maxdepth = None
    if finaltokens:
        maxdepth = mo.ui.slider(start=0,stop=max_subordination_depth(finaltokens),label="*Maximum depth of subordination to display*:",show_value=True,value=max_subordination_depth(finaltokens))
    return (maxdepth,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI selections for serialization
    """)
    return


@app.cell
def _(mo):
    save_extension = mo.ui.radio(
        options=["cex", "txt"], value="cex", inline=True, label="*File extension*:"
    )
    return (save_extension,)


@app.cell
def _(selected_rows):
    # Same readable-default-filename convention latin_syntaxer_ctsdata.py's
    # own filename_base cell uses -- see that cell's comment for the full
    # rationale.
    filename_base = ""
    if selected_rows:
        shared_prefix, sep, _ = selected_rows[0].citation.rpartition(":")
        filename_base = shared_prefix + sep + "_".join(
            citation_suffix(row.citation) for row in selected_rows
        )
    filename_base = "".join(c if c.isalnum() else "_" for c in filename_base).strip("_") or "analysis"
    return (filename_base,)


@app.cell
def _(analysis_text, filename_base, mo, results, save_extension):
    download_widget = mo.download(
        data=analysis_text.encode("utf-8"),
        filename=f"{filename_base}.{save_extension.value}",
        label="Download analysis",
        mimetype="text/plain",
        disabled=not results,
    )
    return (download_widget,)


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Analysis
    """)
    return


@app.cell
def _(analyze_button, analyze_selected_passages, ctsdata_rows, parsed_passage_ids):
    # Analyze exactly the passages named in parsed_passage_ids, when the
    # Analyze button is clicked. analyze_selected_passages() (pipeline.py)
    # selects those ids out of ctsdata_rows in the SOURCE FILE'S OWN
    # order -- never the order ids were typed above -- then runs them
    # through analyze_sources() exactly as latin_syntaxer_ctsdata.py's own
    # Analysis cell does for its multiselect-driven selection. The
    # try/except is a defensive backstop, not the primary validation path
    # (the Analyze button is already disabled whenever missing_ids is
    # non-empty -- see analyze_button above); it only matters if
    # ctsdata_rows itself changes out from under an already-enabled button
    # in the same reactive cycle. selection_error is surfaced by the
    # selection_error_display cell below, if it's ever actually set.
    sentences, results, selection_error = [], [], None
    if analyze_button.value and parsed_passage_ids and ctsdata_rows:
        try:
            sentences, results = analyze_selected_passages(parsed_passage_ids, ctsdata_rows)
        except ValueError as e:
            selection_error = str(e)
    return results, selection_error, sentences


@app.cell(hide_code=True)
def _(mo, selection_error):
    selection_error_display = None
    if selection_error is not None:
        selection_error_display = mo.callout(
            mo.md(f"Could not analyze this selection: {selection_error}"), kind="danger"
        )
    selection_error_display
    return


@app.cell
def _(combined_tokengraph, results, tokengraph_to_mermaid):
    # Compose Mermaid diagram:
    finaltokens = combined_tokengraph(results)
    diagram, mermaid_warnings = tokengraph_to_mermaid(finaltokens)
    return diagram, finaltokens


@app.cell
def _(sentences):
    tokens = [tok for sentence in sentences for tok in sentence.tokens]
    return


@app.cell
def _(results):
    vus = [res.verbalunits for res in results]
    return


@app.cell
def _():
    return


@app.cell
def _(lm, results, summarize_lm_cost):
    # The `_ = results` line below doesn't do anything with `results` --
    # it exists purely so marimo sees this cell as depending on it (marimo
    # derives a cell's inputs from actual name usage in its body, not just
    # the function signature) and re-runs the cell on every Analyze click.
    # Depending on `lm` alone doesn't do that: lm.history is mutated in
    # place by each LM call, and marimo only re-runs a cell when a
    # variable it actually reads is REASSIGNED -- `lm` itself never is,
    # after configure_lm() first creates it -- see
    # latin_syntaxer_ctsdata.py's identical cell/comment for the full
    # explanation.
    _ = results
    #
    # summarize_lm_cost() (arsgrammatica/lm_cost.py) sums cost across
    # EVERY call in lm.history, not just the last one, and never crashes
    # on an empty history (true before the first Analyze click) or a call
    # served from dspy's own cache (cost=None) -- see that module's own
    # docstring.
    cost_summary = summarize_lm_cost(lm.history)
    return (cost_summary,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(mo, selected_rows):
    # Show the raw, as-selected passage text (one block per selection, in
    # file order) as soon as the id list changes and resolves to known
    # ids -- no LM call involved, so this updates immediately, same as
    # latin_syntaxer_ctsdata.py's own rawpreview cell.
    import html as _html

    if selected_rows:
        _blocks = [
            f"## Selected passage: {_html.escape(citation_suffix(_row.citation))}\n\n{_html.escape(_row.text)}"
            for _row in selected_rows
        ]
        rawpreview = mo.md("\n\n---\n\n".join(_blocks))
    else:
        rawpreview = mo.md("")
    return (rawpreview,)


@app.cell
def _(finaltokens, mo, selected_rows, tokengraph_to_text):
    citation_label = ", ".join(citation_suffix(row.citation) for row in selected_rows)
    psghtml = mo.Html(
        f"<b><i>Reconstructed passage {citation_label}</i></b>: " + tokengraph_to_text(finaltokens)
    )
    return (psghtml,)


@app.cell
def _(finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens))
    return (vuhtml,)


@app.cell
def _(finaltokens, maxdepth, mo, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens,depth=maxdepth.value)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)
    return (indentpsg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Serialize analysis to file
    """)
    return


@app.cell
def _(finaltokens, lm, results, sentences, serialize_analyses):
    # Same flattening/serialization convention latin_syntaxer_ctsdata.py's
    # own cell uses -- see that cell's comment for the full rationale.
    all_verbalunits = [vu for result in results for vu in result.verbalunits]
    analysis_text, analysis_warnings = serialize_analyses(
        sentences,
        all_verbalunits,
        finaltokens,
        model=lm.model,
        reasoning=[result.reasoning for result in results],
    )
    return analysis_text, analysis_warnings


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Imports
    """)
    return


@app.cell
def _():
    import dspy
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    return Path, dspy, load_dotenv, os


@app.cell
def _(Path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import (
        DEFAULT_CEILING,
        print_analysis,
        analyze_selected_passages,
        tokengraph_to_mermaid,
        combined_tokengraph,
        tokengraph_to_html,
        tokengraph_to_text,
        tokengraph_to_depth_html,
        serialize_analyses,
        read_ctsdata,
        max_subordination_depth,
        summarize_lm_cost,
        format_lm_cost,
    )

    return (
        DEFAULT_CEILING,
        analyze_selected_passages,
        combined_tokengraph,
        max_subordination_depth,
        read_ctsdata,
        serialize_analyses,
        tokengraph_to_depth_html,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
        summarize_lm_cost,
        format_lm_cost,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Configuration of LM
    """)
    return


@app.cell
def _(Path, load_dotenv):
    # override=True: marimo's kernel is a long-lived process -- see
    # latin_syntaxer_ctsdata.py's identical cell/comment.
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)
    return


@app.cell
def _(os):
    api_base = os.getenv("API_BASE")
    model = os.getenv("MODEL")
    api_key = os.getenv("API_KEY")
    return


@app.cell
def _(os):
    def getenv(name: str, fallback_name: str, default: str | None = None) -> str | None:
        value = os.getenv(name)
        if value:
            return value
        value = os.getenv(fallback_name)
        if value:
            return value
        return default


    return (getenv,)


@app.cell
def _(DEFAULT_CEILING, disable_cache, dspy, getenv):
    def configure_lm():
        # Same rebuild-every-call convention latin_syntaxer_ctsdata.py's own
        # configure_lm() uses -- see that cell's comment for the full
        # rationale (no "already configured" guard, since dspy.settings
        # outlives any single cell run in marimo's long-lived kernel).
        api_base = getenv("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
        model = getenv("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")
        api_key = getenv("API_KEY", "API_KEY")

        if not api_key:
            raise RuntimeError(
                "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
            )

        lm_kwargs = dict(
            model=model,
            api_base=api_base,
            api_key=api_key,
            max_tokens=DEFAULT_CEILING,
            cache=not disable_cache.value,
        )

        # Anthropic prompt caching -- same rationale as
        # latin_syntaxer_ctsdata.py's own configure_lm().
        if "anthropic" in model.lower():
            lm_kwargs["cache_control_injection_points"] = [
                {"location": "message", "role": "system"}
            ]

        lm = dspy.LM(**lm_kwargs)
        dspy.configure(lm=lm)
        return lm


    return (configure_lm,)


@app.cell
def _(configure_lm):
    lm = configure_lm()
    return (lm,)


if __name__ == "__main__":
    app.run()
