import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo


    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Analyze Latin syntax with a configured LM

    Read  a delimited-text *source data*, then choose one of its passages from the
    menu to analyze it.
    """)
    return


@app.cell(hide_code=True)
def _(ctsdata_file_browser):
    ctsdata_file_browser
    return


@app.cell(hide_code=True)
def _(analyze_button, ctsdata_error, ctsdata_rows, mo, passage_dropdown):
    if ctsdata_error is not None:
        ctsdata_status = mo.callout(
            mo.md(f"Could not read this file as a `#!ctsdata` source: {ctsdata_error}"),
            kind="danger",
        )
    elif not ctsdata_rows:
        ctsdata_status = mo.md("*Choose a source data file above to list its passages.*")
    else:
        ctsdata_status = mo.md(f"*{len(ctsdata_rows)} passage(s) loaded from this file.*")

    mo.vstack(
        [ctsdata_status, mo.hstack([passage_dropdown, analyze_button], justify="start")]
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
    ## Analysis
    """)
    return


@app.cell
def _(analyze_button, analyze_passage, passage_dropdown):
    # Analyze the selected passage -- only once the Analyze button has been
    # clicked. This lets the reader browse a whole text passage-by-passage
    # (see the raw preview above) and choose deliberately when to spend an
    # LM call on one, rather than re-analyzing on every selection change.
    #
    # analyze_button.value is True for exactly the one reactive cycle
    # triggered by a click; marimo's run_button then resets it to False
    # internally (a direct state assignment, not a value-change event), so
    # this cell isn't spuriously re-run and cleared by the button's own
    # reset -- only by a genuine new dependency change (another click, or a
    # new passage selection, which recreates analyze_button with its value
    # back at False and so clears results/sentences back to empty until
    # Analyze is clicked again).
    passage = ''
    sentences, results = [], []
    if analyze_button.value and passage_dropdown.value is not None:
        row = passage_dropdown.value
        passage = row.text
        citation = row.urnbase + row.citation
        sentences, results = analyze_passage(passage, citation=citation)
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
    return (vus,)


@app.cell
def _(vus):
    vus[0] if vus else None
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(mo, passage_dropdown):
    # Show the raw, as-selected passage text as soon as a menu item is
    # picked -- no LM call involved, so this can update immediately and
    # independently of whether Analyze has been clicked yet. Lets the
    # reader browse a whole text passage-by-passage (the user's own stated
    # goal of hunting for edge cases) without spending an LM call on every
    # single selection.
    import html as _html

    if passage_dropdown.value is not None:
        _row = passage_dropdown.value
        rawpreview = mo.Html(
            f"<b><i>Selected passage {_html.escape(_row.citation)}</i></b>: "
            f"{_html.escape(_row.text)}"
        )
    else:
        rawpreview = mo.Html("")
    return (rawpreview,)


@app.cell
def _(finaltokens, mo, passage_dropdown, tokengraph_to_text):
    citation_label = passage_dropdown.value.citation if passage_dropdown.value else ""
    psghtml = mo.Html(
        f"<b><i>Reconstructed passage {citation_label}</i></b>: " + tokengraph_to_text(finaltokens)
    )
    return (psghtml,)


@app.cell
def _(finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens))
    return (vuhtml,)


@app.cell
def _(finaltokens, mo, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)
    return (indentpsg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Save analysis
    """)
    return


@app.cell
def _(finaltokens, results, sentences, serialize_analyses):
    # Flatten every sentence's own verbalunits into the one flat list
    # serialize_analyses()/write_analyses() expect, matching how
    # combined_tokengraph() already flattens tokengraph across sentences.
    all_verbalunits = [vu for result in results for vu in result.verbalunits]
    analysis_text, analysis_warnings = serialize_analyses(sentences, all_verbalunits, finaltokens)
    return analysis_text, analysis_warnings


@app.cell
def _(passage_dropdown):
    # A readable default filename base, drawn from the selected row's own
    # urn (falling back to "analysis" if nothing's been selected yet) --
    # the extension is chosen separately, via save_extension below. Same
    # derivation syntaxer_workflow.py's own form-based filename_base uses,
    # just reading urnbase/citation off the selected CtsDataRow instead of
    # off submitted form fields.
    filename_base = ""
    if passage_dropdown.value is not None:
        filename_base = (passage_dropdown.value.urnbase or "") + (passage_dropdown.value.citation or "")
    filename_base = "".join(c if c.isalnum() else "_" for c in filename_base).strip("_") or "analysis"
    return (filename_base,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Source data
    """)
    return


@app.cell
def _(Path, mo):
    # Browse for the delimited-text file listing passages to analyze (see
    # arsgrammatica/ctsdata.py for the '#!ctsdata' block format). Unlike
    # the "choose a folder to save to" field syntaxer_workflow.py used to
    # have (see that notebook's own history: mo.ui.file_browser's
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


@app.cell
def _(ctsdata_file_browser, read_ctsdata):
    # Re-read the file every time the file_browser's own selection
    # changes. Reading and parsing this delimited-text format is cheap (no
    # LM call involved), so this can run reactively on every selection
    # change rather than waiting on a separate "Load" button -- unlike the
    # Analysis cell below, which only re-runs when a passage is actually
    # chosen from the menu this produces.
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
def _(ctsdata_rows, mo):
    # One menu entry per row, labelled "<citation>: <first four words>…" --
    # e.g. "45.1: Non se poterat ultra…" -- so the reader can recognize a
    # passage without having to open the source file. The trailing "…" is
    # only added when the passage actually has more words than the preview
    # shows -- a passage that's already 4 words or shorter is shown in
    # full, with no ellipsis implying truncation that isn't there.
    # mo.ui.dropdown's options dict maps each label directly to its own
    # CtsDataRow, so passage_dropdown.value below is the CtsDataRow itself
    # once something is chosen (None until then), not just an index or a
    # label string.
    def _passage_label(row):
        words = row.text.split()
        preview = " ".join(words[:4])
        ellipsis = "…" if len(words) > 4 else ""
        return f"{row.citation}: {preview}{ellipsis}"

    passage_options = {_passage_label(row): row for row in ctsdata_rows}
    passage_dropdown = mo.ui.dropdown(
        options=passage_options,
        label="*Passage*:",
    )
    return (passage_dropdown,)


@app.cell
def _(mo, passage_dropdown):
    # A new instance is created (and analyze_button.value resets to False)
    # every time passage_dropdown's own selection changes, since this cell
    # depends on passage_dropdown.value -- so switching to a different
    # passage always requires a fresh, deliberate Analyze click rather than
    # silently re-using a previous click.
    analyze_button = mo.ui.run_button(
        label="Analyze",
        disabled=passage_dropdown.value is None,
    )
    return (analyze_button,)


@app.cell
def _(mo):
    save_extension = mo.ui.radio(
        options=["cex", "txt"], value="cex", inline=True, label="*File extension*:"
    )
    return (save_extension,)


@app.cell
def _(analysis_text, filename_base, mo, results, save_extension):
    # mo.download() puts the browser in charge of where the file lands --
    # no folder-path field to mistype, at the cost of not choosing a
    # location up front (the browser's own download prompt/default
    # download folder decides that). filename reactively follows both the
    # citation-derived filename_base and whichever extension is chosen
    # above.
    download_widget = mo.download(
        data=analysis_text.encode("utf-8"),
        filename=f"{filename_base}.{save_extension.value}",
        label="Download analysis",
        mimetype="text/plain",
        disabled=not results,
    )
    return (download_widget,)


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


    return Path, dspy, os


@app.cell
def _():
    from dotenv import load_dotenv

    return (load_dotenv,)


@app.cell
def _(Path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import (
        print_analysis,
        analyze_passage,
        tokengraph_to_mermaid,
        combined_tokengraph,
        tokengraph_to_html,
        tokengraph_to_text,
        tokengraph_to_depth_html,
        serialize_analyses,
        read_ctsdata,
    )

    return (
        analyze_passage,
        combined_tokengraph,
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
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
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
def _(dspy, getenv):
    def configure_lm():
        if dspy.settings.lm is not None:
            return dspy.settings.lm

        api_base = getenv("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
        model = getenv("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")
        api_key = getenv("API_KEY", "API_KEY")

        if not api_key:
            raise RuntimeError(
                "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
            )

        lm = dspy.LM(model=model, api_base=api_base, api_key=api_key)
        dspy.configure(lm=lm)
        return lm


    return (configure_lm,)


@app.cell
def _(configure_lm):
    configure_lm()
    return


if __name__ == "__main__":
    app.run()
