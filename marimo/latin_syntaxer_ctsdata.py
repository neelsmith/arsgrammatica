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
    # Analyze Latin syntax with a configured LM
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > Read citable text from a delimited-text (CEX) file, then choose one or more passages to analyze together.
    """)
    return


@app.cell(hide_code=True)
def _(ctsdata_file_browser):
    ctsdata_file_browser
    return


@app.cell(hide_code=True)
def _(analyze_button, ctsdata_error, ctsdata_rows, mo, passage_multiselect):
    if ctsdata_error is not None:
        ctsdata_status = mo.callout(
            mo.md(f"Could not read this file as a `#!ctsdata` source: {ctsdata_error}"),
            kind="danger",
        )
    elif not ctsdata_rows:
        ctsdata_status = mo.md("*Choose a source data file above to list its passages.*")
    else:
        ctsdata_status = mo.md(f"## Passage selection\n\n*{len(ctsdata_rows)} passage(s) loaded from this file.*")

    mo.vstack(
        [ctsdata_status, mo.hstack([passage_multiselect, analyze_button], justify="start")]
    )
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
    # dspy.LM caches responses by default (model + messages + config), so
    # re-clicking Analyze on the exact same passage selection normally just
    # replays the earlier result instead of hitting the LM again -- correct
    # for everyday use, but exactly the wrong behavior when you're
    # deliberately re-running the same passage to see whether the LM's
    # output changes (e.g. after a prompt tweak, or to check run-to-run
    # variance). This is dspy's own client-side response cache, unrelated
    # to configure_lm()'s Anthropic `cache_control_injection_points` prompt
    # caching below -- that one only caches the STATIC system-message
    # prefix to make each still-genuinely-fresh call cheaper, it never
    # replays a whole response, so it stays on regardless of this checkbox.
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
def _(cost, mo, seecost):
    costdisplay = None
    if seecost.value:
        costdisplay = mo.md(f"**Cost of last LM call**: {cost}")
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
    # Browse for the delimited-text file listing passages to analyze (see
    # arsgrammatica/ctsdata.py for the '#!ctsdata' block format). Unlike
    # the "choose a folder to save to" field latin_syntaxer_workflow.py used
    # to have (see that notebook's own history: mo.ui.file_browser's
    # "directory" selection mode has no way to select the folder currently
    # being browsed, only a subfolder shown in its listing), selecting a
    # single FILE by clicking it works correctly -- there's no equivalent
    # gap for selection_mode="file" -- so a file_browser is used here
    # rather than a typed path.
    ctsdata_file_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Source data file*:",
    )
    return (ctsdata_file_browser,)


@app.function
def citation_suffix(citation):
    """The final segment of a CitedText's own `citation` -- for a CTS URN
    like 'urn:cts:compnov:bible.genesis.vulgate:45.1', whatever follows its
    last ':' ('45.1'); for a citation with no ':' at all (e.g. a hand-typed
    'Aeneid 1.1'), `citation` itself, unchanged. read_ctsdata() hands back
    each row's own citation as the row's WHOLE urn (see arsgrammatica/
    ctsdata.py) -- this is purely a shorter display label derived from
    that, used everywhere below a menu/heading would otherwise repeat a
    long shared urn prefix on every single passage; `row.citation` itself,
    in full, is still what's actually passed to analyze_sources()."""
    return citation.rpartition(":")[-1]


@app.function
# Format label for one menu entry as "<citation suffix>: <first four
# words>…" The trailing "…" is only added when the passage actually has
# more words than the preview shows -- a passage that's already 4 words or
# shorter is shown in full.
def passage_label(row):
    words = row.text.split()
    preview = " ".join(words[:4])
    ellipsis = "…" if len(words) > 4 else ""
    return f"{citation_suffix(row.citation)}: {preview}{ellipsis}"


@app.cell
def _(ctsdata_rows, mo):
    # Menu for selecting one or more passages -- a multiselect rather than
    # a dropdown, since analyze_sources() (see the Analysis cell below)
    # accepts a list of sources and segments/analyzes them together, not
    # just one at a time. Maps each label directly to a CitedText (what
    # read_ctsdata() returns each row as), so passage_multiselect.value is
    # a list of the selected CitedTexts (in whatever order the widget
    # itself reports them -- see selected_rows below for why that order
    # isn't used directly).
    passage_options = {passage_label(row): row for row in ctsdata_rows}
    passage_multiselect = mo.ui.multiselect(
        options=passage_options,
        label="*Passage(s)*:",
    )
    return (passage_multiselect,)


@app.cell
def _(ctsdata_rows, passage_multiselect):
    # Always analyze selected passages in their original file order, not
    # whatever order passage_multiselect.value happens to report them in
    # (multiselect widgets are free to report selections in click order) --
    # segment_sources() (inside analyze_sources()) treats consecutive
    # sources as potentially sharing a sentence, so an out-of-file-order
    # source list could segment incorrectly or produce citations in a
    # confusing order.
    selected_rows = [row for row in ctsdata_rows if row in passage_multiselect.value]
    return (selected_rows,)


@app.cell
def _(mo, passage_multiselect):
    # A new instance is created (and analyze_button.value resets to False)
    # every time passage_multiselect's own selection changes, since this
    # cell depends on passage_multiselect.value -- so changing the
    # selection always requires a fresh, deliberate Analyze click rather
    # than silently re-using a previous click.
    analyze_button = mo.ui.run_button(
        label="Analyze",
        disabled=not passage_multiselect.value,
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
    # A readable default filename base, drawn from every selected row's own
    # citation (falling back to "analysis" if nothing's been selected yet)
    # -- the first selection's own citation up to and including its last
    # ':' (its shared urn prefix, if any -- see citation_suffix()'s own
    # docstring), plus every selection's own citation_suffix(), in file
    # order. This can get long with many passages selected at once, but
    # stays deterministic and collision-resistant; the extension is chosen
    # separately.
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
    # mo.download() puts the browser in charge of where the file lands.
    # filename reactively follows both citation-derived filename_base and whichever extension is chosen.
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
def _(analyze_button, analyze_sources, selected_rows):
    # Analyze every selected passage, together, when the Analyze button is
    # clicked. analyze_button.value is True for exactly the one reactive
    # cycle triggered by a click. Each selected row is already a CitedText
    # (read_ctsdata() returns them directly -- see arsgrammatica/
    # ctsdata.py) -- analyze_sources() segments across all of them at once
    # (a sentence may span two consecutive sources) and returns one flat
    # (sentences, results) pair spanning every selected passage, in the
    # file order selected_rows already established.
    sentences, results = [], []
    if analyze_button.value and selected_rows:
        sentences, results = analyze_sources(selected_rows)
    return results, sentences


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
def _(lm):
    last_call = None
    if lm.history:
        last_call = lm.history[-1]
    return (last_call,)


@app.cell
def _(last_call):
    #last_call = lm.history[-1]
    cost = last_call.get('cost')
    return (cost,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(mo, selected_rows):
    # Show the raw, as-selected passage text (one block per selection, in
    # file order) as soon as the menu selection changes -- no LM call
    # involved, so this can update immediately and independently of
    # whether Analyze has been clicked yet. Lets the reader browse a whole
    # text passage-by-passage (the user's own stated goal of hunting for
    # edge cases) without spending an LM call on every single selection.
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
    # Flatten every sentence's own verbalunits into the one flat list
    # serialize_analyses()/write_analyses() expect, matching how
    # combined_tokengraph() already flattens tokengraph across sentences.
    all_verbalunits = [vu for result in results for vu in result.verbalunits]
    # '#!LM' records which model produced each sentence's analysis
    # (lm.model -- the actual configured model, including configure_lm()'s
    # own fallback default, not just a raw MODEL env lookup) and that
    # sentence's own reasoning (dspy.ChainOfThought's `reasoning` output
    # field), one entry per sentence.
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
        analyze_sources,
        tokengraph_to_mermaid,
        combined_tokengraph,
        tokengraph_to_html,
        tokengraph_to_text,
        tokengraph_to_depth_html,
        serialize_analyses,
        read_ctsdata,
        max_subordination_depth
    )

    return (
        DEFAULT_CEILING,
        analyze_sources,
        combined_tokengraph,
        max_subordination_depth,
        read_ctsdata,
        serialize_analyses,
        tokengraph_to_depth_html,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Configuration of LM
    """)
    return


@app.cell
def _(Path, load_dotenv):
    # override=True: marimo's kernel is a long-lived process, not a fresh
    # one per run like syntaxer_main.py -- without this, once API_KEY (or
    # any other var here) is set in os.environ, re-running this cell after
    # editing .env would leave the stale value in place instead of picking
    # up the fix.
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
        # Always rebuild from the current environment -- no
        # `if dspy.settings.lm is not None: return dspy.settings.lm` guard.
        # dspy.settings is a module-level singleton that outlives any single
        # cell run in marimo's long-lived kernel, so that guard would freeze
        # whichever LM (and api_key) was first configured for the rest of
        # the kernel's life, silently ignoring every later edit to .env --
        # exactly the "works from the command line, fails in the notebook"
        # symptom that sent us looking here. dspy.LM(...) construction and
        # dspy.configure() are both cheap, local calls (no network round
        # trip), so rebuilding on every call costs nothing.
        api_base = getenv("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
        model = getenv("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")
        api_key = getenv("API_KEY", "API_KEY")

        if not api_key:
            raise RuntimeError(
                "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
            )

        # An explicit numeric baseline, not None (dspy.LM's own default) --
        # see arsgrammatica/token_budget.py's DEFAULT_CEILING and
        # syntaxer_main.py's own configure_lm() for the full rationale:
        # analyze_sources() overrides this per call via analyze_with_retry(),
        # but segment_sources()'s own LM call does not, so without this it
        # would fall through to whatever the provider/litellm defaults to;
        # it also keeps dspy's own truncation warning (which always reports
        # this baseline, never a per-call override) from misleadingly
        # reading "max_tokens=None".
        #
        # cache=not disable_cache.value: dspy.LM defaults to caching every
        # response it gets (keyed on model + messages + these very
        # lm_kwargs), so re-clicking Analyze on an unchanged passage
        # selection normally just replays the cached result rather than
        # calling the LM again -- see the *Disable LM cache (debugging)*
        # checkbox above for why that's sometimes exactly what you don't
        # want. Reading disable_cache.value here (rather than passing
        # `cache=False` unconditionally) means toggling the checkbox takes
        # effect immediately: it's a parameter of this very cell, so
        # flipping it rebuilds configure_lm's closure (and, downstream, the
        # `lm = configure_lm()` cell) the same way editing .env does.
        lm_kwargs = dict(
            model=model,
            api_base=api_base,
            api_key=api_key,
            max_tokens=DEFAULT_CEILING,
            cache=not disable_cache.value,
        )

        # Anthropic prompt caching: SentenceAnalysis's system message runs
        # ~40K characters and is byte-identical on every single call --
        # only the per-sentence user message actually changes. Marking it
        # with an ephemeral cache_control breakpoint lets a repeat call
        # within Anthropic's cache TTL reuse that whole block at ~10% of
        # its normal input-token price. litellm (which dspy.LM forwards
        # arbitrary kwargs to) applies cache_control_injection_points
        # provider-agnostically based solely on the param's presence, so
        # this is gated on the model actually being Anthropic-routed -- a
        # MODEL override pointing at Ollama/OpenAI/etc. would otherwise
        # just carry an inert, unrecognized field. No few-shot demos are
        # attached to `analyze` today, so one breakpoint on the system
        # message covers the whole static prefix; if a compiled/optimized
        # program with demos is ever loaded here, add a second point,
        # {"location": "message", "index": -2}, to fold the demo turns into
        # the same cached prefix too (the real, always-different input is
        # always the last message, so -2 is "whatever precedes it").
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
