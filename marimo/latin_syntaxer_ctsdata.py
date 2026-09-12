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
def _(disable_cache, mo, seecost):
    mo.hstack([seecost, disable_cache],justify="start")
    return


@app.cell(hide_code=True)
def _(costdisplay):
    costdisplay
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
def _(diagram_tool):
    diagram_tool
    return


@app.cell(hide_code=True)
def _(diagram, diagram_tool, dot_source, dot_warnings, graphviz, mo):
    # Two distinct failure modes to degrade visibly from when
    # diagram_tool.value == "graphviz", same "don't just crash the cell"
    # convention latin_syntaxer_review.py's own diagram_display cell uses
    # (see notes/dot_diagrams.md):
    #   - the `graphviz` package itself isn't installed -- not actually
    #     reachable here, since diagram_tool's own options only offer
    #     "graphviz" at all when graphviz_available is True (see that
    #     widget's definition below), but the "mermaid"-only fallback is
    #     what a user without the package ever sees instead;
    #   - it IS installed, but the Graphviz `dot` executable isn't on PATH
    #     (graphviz.ExecutableNotFound, only raised once you actually try
    #     to render something) -- this one genuinely can't be known ahead
    #     of time without trying, so it's still handled here.
    if diagram_tool.value == "graphviz":
        try:
            svg_bytes = graphviz.Source(dot_source).pipe(format="svg")
            diagram_display = mo.vstack(
                [mo.Html(svg_bytes.decode("utf-8"))]
                + (
                    [mo.callout(mo.md("\n".join(f"- {w}" for w in dot_warnings)), kind="warn")]
                    if dot_warnings
                    else []
                )
            )
        except graphviz.ExecutableNotFound:
            diagram_display = mo.callout(
                mo.md(
                    "The `graphviz` package is installed, but the Graphviz "
                    "`dot` command itself isn't on your system's PATH -- "
                    "install Graphviz separately (e.g. `brew install "
                    "graphviz` on macOS, `apt install graphviz` on Linux), "
                    "or switch back to *Mermaid* above. See "
                    "notes/dot_diagrams.md."
                ),
                kind="warn",
            )
    else:
        diagram_display = mo.mermaid(diagram)

    diagram_display
    return


@app.cell(hide_code=True)
def _(diagram_download):
    diagram_download
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


@app.cell
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
    mo.hstack([seetokens, seeprompts], justify="start")
    return disable_cache, seecost, seeprompts, seetokens


@app.cell(hide_code=True)
def _(
    mo,
    optimized_program_browser,
    optimized_program_error,
    optimized_program_path,
):
    if optimized_program_error is not None:
        optimized_program_status = mo.callout(
            mo.md(f"Could not load this file as an optimized program: {optimized_program_error}"),
            kind="danger",
        )
    elif optimized_program_path is not None:
        optimized_program_status = mo.md(
            f"*Using the optimized prompt loaded from `{optimized_program_path}`.*"
        )
    else:
        optimized_program_status = mo.md(
            "*No optimized program selected -- using `analyze`'s default (unoptimized) prompt.*"
        )

    mo.vstack([optimized_program_browser, optimized_program_status])
    return


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
    return (costdisplay,)


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
    # the "choose a folder to save to" field latin_syntaxer_textinput.py used
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


@app.cell
def _(Path, mo):
    # Same file_browser convention as ctsdata_file_browser above. Optional --
    # analyze() below falls back to `analyze`'s own default (unoptimized)
    # prompt whenever nothing is selected here, so leaving this untouched is
    # the normal, expected state, not an error condition.
    optimized_program_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Optimized program (.json), optional*:",
    )
    return (optimized_program_browser,)


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


@app.cell
def _(maxdepth):
    # Guard against maxdepth being None (nothing analyzed yet) rather than
    # calling .value unconditionally -- same guard latin_syntaxer_review.py
    # and latin_syntaxer_tokenized.py use for the same reason. Shared by the
    # indented-text display and both diagram-composition cells below, so the
    # diagrams' own AAT-depth cutoff always matches whatever the
    # text-display depth slider shows.
    depth = maxdepth.value if maxdepth is not None else None
    return (depth,)


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
def _(graphviz_available, mo):
    # "graphviz" is only ever offered as a choice when the graphviz PyPI
    # package actually imported successfully above -- there's no point
    # offering an option that can only ever show an install-instructions
    # callout. This can't rule out the OTHER failure mode (the package
    # installed but the `dot` executable missing from PATH), which is why
    # diagram_display still has to handle graphviz.ExecutableNotFound even
    # though this list is filtered.
    diagram_tool = mo.ui.radio(
        options=["mermaid", "graphviz"] if graphviz_available else ["mermaid"],
        value="mermaid",
        inline=True,
        label="*Diagram tool*:",
    )
    return (diagram_tool,)


@app.cell
def _(combined_tokengraph, results):
    # Pulled out as its own cell (rather than produced inside the
    # Mermaid-diagram cell, as it used to be) so maxdepth's own slider
    # (which itself depends on finaltokens, above) can sit upstream of, and
    # then feed its value back into, the diagram-composition cells below
    # without creating a reactive dependency cycle (finaltokens -> maxdepth
    # -> depth -> diagram, never the other way around) -- same restructuring
    # latin_syntaxer_textinput.py already uses for the same reason.
    finaltokens = combined_tokengraph(results)
    return (finaltokens,)


@app.cell
def _(depth, finaltokens, tokengraph_to_mermaid):
    # Compose Mermaid diagram:
    diagram, mermaid_warnings = tokengraph_to_mermaid(finaltokens, aat_depth=depth)
    return (diagram,)


@app.cell
def _(depth, finaltokens, tokengraph_to_dot):
    # Compose Graphviz diagram: cheap to always compute regardless of which
    # tool is currently selected -- tokengraph_to_dot() is pure string
    # building with no dependency of its own (see notes/dot_diagrams.md),
    # unlike actually rendering it, which needs the graphviz package and
    # the `dot` executable (handled in diagram_display above).
    dot_source, dot_warnings = tokengraph_to_dot(finaltokens, aat_depth=depth)
    return dot_source, dot_warnings


@app.cell
def _(diagram, diagram_tool, dot_source, filename_base, finaltokens, mo):
    # Downloads whichever diagram is currently selected/displayed above,
    # not both -- same reactive "follows the widget" convention
    # save_extension/download_widget already use for the serialized
    # analysis. Mermaid source is wrapped in a ```mermaid fenced code
    # block and saved as .md, matching latin_syntaxer_textinput.py's own
    # download_mermaid; Graphviz source is saved raw as .dot, matching
    # latin_syntaxer_review.py's own diagram_download -- both are renderable
    # elsewhere (a Markdown viewer with Mermaid support, `dot -Tsvg`, an
    # online DOT viewer, Quarto's fenced ```{dot}```/```{mermaid}```
    # blocks) without needing this notebook. disabled=not finaltokens
    # rather than checking the diagram/dot_source strings themselves --
    # both always render a non-empty header (e.g. "graph BT") even for an
    # empty tokengraph, so the strings alone can't tell "nothing to show
    # yet" apart from "a real, if minimal, diagram".
    if diagram_tool.value == "graphviz":
        diagram_download = mo.download(
            data=dot_source.encode("utf-8"),
            filename=f"{filename_base}.dot",
            label="Download Graphviz DOT source (.dot)",
            mimetype="text/plain",
            disabled=not finaltokens,
        )
    else:
        diagram_download = mo.download(
            data=("```mermaid\n\n" + diagram + "\n```\n").encode("utf-8"),
            filename=f"{filename_base}.md",
            label="Download Mermaid diagram (.md)",
            mimetype="text/plain",
            disabled=not finaltokens,
        )
    return (diagram_download,)


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
    # it exists purely so marimo's dependency analysis (which derives a
    # cell's inputs from actual NAME USAGE in its body, not just from
    # whatever's in the function signature) sees this cell as depending on
    # `results`, and re-runs it every time a new Analyze click produces a
    # new `results` list. Depending on `lm` alone does NOT do that:
    # lm.history is mutated IN PLACE (appended to) by every LM call, and
    # marimo only re-runs a cell when a variable it actually reads gets
    # REASSIGNED -- `lm` itself is never reassigned after configure_lm()
    # first creates it, so a cell that only reads `lm` runs exactly once,
    # when `lm` is first configured, and then never again, even though
    # lm.history keeps growing with every analysis. (This was true of the
    # old last_call/cost cells this replaced too -- same blind spot, just
    # masked by the AttributeError crash on an empty history firing
    # first.) `results` -- reassigned to a fresh list by the Analysis
    # cell on every Analyze click -- gives this cell something that
    # actually changes to react to.
    _ = results
    #
    # summarize_lm_cost() (arsgrammatica/lm_cost.py) itself sums cost
    # across EVERY call in lm.history, not just the last one -- a single
    # Analyze click makes one segmentation call plus one SentenceAnalysis
    # call per sentence, so "cost of the last call alone" understates
    # what that click actually cost. It also never crashes on an empty
    # history or on a call served from dspy's own cache (cost=None -- see
    # that module's own docstring).
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
def _(depth, finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens,depth=depth))
    return (vuhtml,)


@app.cell
def _(depth, finaltokens, mo, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens, depth=depth)
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
    # '#!lm' records which model produced each sentence's analysis
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
    import json
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    return Path, dspy, json, load_dotenv, os


@app.cell
def _(Path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import (
        DEFAULT_CEILING,
        print_analysis,
        analyze,
        analyze_sources,
        tokengraph_to_mermaid,
        tokengraph_to_dot,
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

    # graphviz (the PyPI package -- a thin subprocess wrapper around the
    # separately-installed Graphviz `dot` executable) is optional the same
    # way it is for latin_syntaxer_review.py's own diagram display: importable
    # or not, checked once here, rather than every display cell catching
    # ImportError itself. Whether the `dot` executable is actually on PATH
    # is a SEPARATE check (graphviz.ExecutableNotFound), made only when a
    # diagram is actually rendered -- see the diagram_display cell below.
    try:
        import graphviz

        graphviz_available = True
    except ImportError:
        graphviz = None
        graphviz_available = False
    return (
        DEFAULT_CEILING,
        analyze,
        analyze_sources,
        combined_tokengraph,
        format_lm_cost,
        graphviz,
        graphviz_available,
        max_subordination_depth,
        read_ctsdata,
        serialize_analyses,
        summarize_lm_cost,
        tokengraph_to_depth_html,
        tokengraph_to_dot,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
    )


@app.cell
def _(analyze):
    # A one-time, JSON-safe snapshot of `analyze`'s own default (unoptimized)
    # state, taken before this kernel ever loads an optimized program onto
    # it. `analyze` (arsgrammatica/latin_syntax_dspy.py) is a genuine shared
    # singleton -- the same dspy.ChainOfThought instance every
    # analyze_sources() call in this notebook goes through -- and
    # dspy.Module has no built-in "unload" back to a predictor's original
    # class docstring. Unlike configure_lm() below, whose "always rebuild,
    # never guard" fix works because dspy.LM/dspy.configure() are cheap to
    # redo from scratch every time, there's no equivalent "just rebuild
    # analyze from scratch" here -- `analyze` is a specific already-compiled
    # dspy.ChainOfThought(SentenceAnalysis) instance other modules already
    # hold a reference to, not a config value this notebook constructs
    # itself. So the optimized-program cell below restores this dict via
    # analyze.load_state(...) instead, whenever the file picker is cleared
    # or a load fails -- exactly the pattern configure_lm()'s own comment
    # already flags as the same category of long-lived-kernel gotcha.
    #
    # dump_state() returns a plain dict of JSON-serializable values (the
    # same dict analyze.save() itself would write out), not a live
    # reference to `analyze`'s own internals -- so this snapshot stays
    # pristine no matter what happens to `analyze` afterward. This cell
    # must never be re-run after a load has already happened in this same
    # kernel session (e.g. via marimo's "run this cell" on its own) -- that
    # would overwrite the pristine snapshot with whatever's currently
    # loaded, defeating the whole point. Re-running the whole notebook from
    # the top (which reconstructs `analyze` before this cell runs again) is
    # fine.
    pristine_analyze_state = analyze.dump_state()
    return (pristine_analyze_state,)


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
        # attached to `analyze`'s own default (unoptimized) prompt, so one
        # breakpoint on the system message covers the whole static prefix.
        # The *Optimized program (.json), optional* file_browser further
        # down this notebook can load a compiled program with demos onto
        # `analyze` -- if you're using that regularly, add a second point,
        # {"location": "message", "index": -2}, here to fold the demo turns
        # into the same cached prefix too (the real, always-different input
        # is always the last message, so -2 is "whatever precedes it"). Not
        # done automatically: configure_lm() has no visibility into whether
        # `analyze` currently carries a loaded program with demos.
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


@app.cell
def _(analyze, json, optimized_program_browser, pristine_analyze_state):
    # Runs on every change to optimized_program_browser's own selection --
    # including "cleared back to nothing" -- so this is the one place that
    # decides what prompt `analyze` actually carries right now. Always
    # restore the pristine snapshot first: analyze.load(path) only ever
    # calls dspy.Module.load_state() (see dump_state()'s own docstring, and
    # the pristine-snapshot cell above), which patches named_parameters()
    # onto `analyze` in place rather than resetting anything not present in
    # the loaded file -- so without this, clearing the file picker after a
    # successful load would silently leave the previously-loaded prompt in
    # place instead of actually reverting to the default.
    optimized_program_path = optimized_program_browser.path(index=0)
    optimized_program_error = None
    if optimized_program_path is not None:
        try:
            analyze.load(str(optimized_program_path))
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            optimized_program_error = f"{type(e).__name__}: {e}"
            analyze.load_state(pristine_analyze_state)
    else:
        analyze.load_state(pristine_analyze_state)
    return optimized_program_error, optimized_program_path


if __name__ == "__main__":
    app.run()
