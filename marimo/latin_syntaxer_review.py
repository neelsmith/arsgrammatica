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
    # Review a saved Latin syntax analysis
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > No LM access needed -- browse a previously-saved analysis file (the same format `write_analyses()` produces), pick one sentence, and inspect it.
    """)
    return


@app.cell(hide_code=True)
def _(analysis_file_browser):
    analysis_file_browser
    return


@app.cell(hide_code=True)
def _(mo, read_error, sentence_dropdown, sentences, split_error):
    if read_error is not None:
        analysis_status = mo.callout(
            mo.md(f"Could not read this file as a saved analysis: {read_error}"),
            kind="danger",
        )
    elif split_error is not None:
        analysis_status = mo.callout(
            mo.md(f"Could not split this analysis by sentence: {split_error}"),
            kind="danger",
        )
    elif not sentences:
        analysis_status = mo.md("*Choose an analysis file above to list its sentences.*")
    else:
        analysis_status = mo.md(f"## Sentence selection\n\n*{len(sentences)} sentence(s) loaded from this file.*")

    mo.vstack([analysis_status, sentence_dropdown])
    return


@app.cell(hide_code=True)
def _(plaintext_html):
    plaintext_html
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
    # diagram_tool.value == "graphviz", same convention
    # latin_syntaxer_textinput.py's own diagram_display cell uses (see
    # notes/dot_diagrams.md):
    #   - the `graphviz` package itself isn't installed -- not actually
    #     reachable here, since diagram_tool's own options only offer
    #     "graphviz" at all when graphviz_available is True (see that
    #     widget's own definition), but the "mermaid"-only fallback is
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
def _(aat_display):
    aat_display
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
def _(Path, mo):
    # Browse for a previously-written analysis file (write_analyses()'s own
    # format -- see USAGE.md's "Saving and loading analyses"). A
    # file_browser is used for the same reason latin_syntaxer_ctsdata.py's
    # own ctsdata_file_browser is: selecting a single FILE by clicking it just
    # works, unlike mo.ui.file_browser's "directory" selection mode.
    analysis_file_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Analysis file*:",
    )
    return (analysis_file_browser,)


@app.cell
def _(analysis_file_browser, read_analyses):
    # Re-read the file every time the file_browser's own selection changes.
    # No LM call anywhere in this notebook -- read_analyses() reconstructs
    # everything from the file's own text.
    analysis_path = analysis_file_browser.path(index=0)
    tokengraph, verbalunits, sentences, lm_infos = [], [], [], []
    read_error = None
    if analysis_path is not None:
        try:
            tokengraph, verbalunits, sentences, lm_infos = read_analyses(str(analysis_path))
        except (ValueError, OSError) as e:
            read_error = str(e)
    return read_error, sentences, tokengraph, verbalunits


@app.cell
def _(sentences, split_analysis_by_sentence, tokengraph, verbalunits):
    # split_analysis_by_sentence() gives us each sentence's own tokengraph/
    # verbalunits slice out of the file's flat, whole-passage lists -- see
    # arsgrammatica/serialization.py -- so the rest of this notebook only
    # ever has to think about "the currently selected sentence's data".
    sentence_slices = []
    split_error = None
    if sentences:
        try:
            sentence_slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)
        except ValueError as e:
            split_error = str(e)
    return sentence_slices, split_error


@app.function
# Label one menu entry as "<n>. <citation>: <first six words>…" -- numbered
# so entries are always unique even when several sentences share (or lack)
# a citation, or happen to start with the same words.
def sentence_label(index, citation, sentence_tokengraph, tokengraph_to_text):
    preview_text = tokengraph_to_text(sentence_tokengraph)
    words = preview_text.split()
    preview = " ".join(words[:6])
    ellipsis = "…" if len(words) > 6 else ""
    prefix = f"{citation}: " if citation else ""
    return f"{index + 1}. {prefix}{preview}{ellipsis}"


@app.cell
def _(mo, sentence_slices, sentences, tokengraph_to_text):
    # Menu for selecting a sentence. Maps each label directly to that
    # sentence's own index, so sentence_dropdown.value is an int usable to
    # index into sentence_slices below -- zip() with sentences stops at
    # whichever list is shorter, so a split_analysis_by_sentence() failure
    # (sentence_slices left empty, sentences possibly not) can't produce a
    # mismatched, out-of-range index here.
    sentence_options = {}
    if sentence_slices:
        for i, (sentence, (sentence_tokengraph, _sentence_verbalunits)) in enumerate(
            zip(sentences, sentence_slices)
        ):
            citation = sentence.tokens[0].citation if sentence.tokens else None
            sentence_options[sentence_label(i, citation, sentence_tokengraph, tokengraph_to_text)] = i

    sentence_dropdown = mo.ui.dropdown(
        options=sentence_options,
        label="*Sentence*:",
    )
    return (sentence_dropdown,)


@app.cell
def _(sentence_dropdown, sentence_slices, sentences):
    # The currently selected sentence's own tokengraph/verbalunits slice --
    # empty until a sentence is actually picked, which every rendering
    # utility below already handles gracefully (an empty diagram/string).
    # selected_citation rides along for the diagram download's filename
    # below -- pulled from the Sentence's own first Token, same source
    # sentence_label()'s own menu-entry citation comes from.
    selected_tokengraph, selected_verbalunits = [], []
    selected_citation = None
    selected_sentence = None
    if sentence_dropdown.value is not None and 0 <= sentence_dropdown.value < len(sentence_slices):
        selected_tokengraph, selected_verbalunits = sentence_slices[sentence_dropdown.value]
        selected_sentence = sentences[sentence_dropdown.value]
        selected_citation = selected_sentence.tokens[0].citation if selected_sentence.tokens else None
    return selected_citation, selected_sentence, selected_tokengraph, selected_verbalunits


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(max_subordination_depth, mo, selected_tokengraph):
    # A slider bounding the diagrams and HTML displays below to a chosen
    # depth -- moved ahead of them (rather than sitting between vuhtml and
    # indentpsg, as it did before the Mermaid/Graphviz diagrams and the AAT
    # graph also started consuming its value) so its own `depth` cell can
    # sit upstream of every consumer. None until a sentence with at least
    # one token is selected.
    maxdepth = None
    if selected_tokengraph:
        maxdepth = mo.ui.slider(
            start=0,
            stop=max_subordination_depth(selected_tokengraph),
            label="*Maximum depth of subordination to display*:",
            show_value=True,
            value=max_subordination_depth(selected_tokengraph),
        )
    return (maxdepth,)


@app.cell
def _(maxdepth):
    # Shared by every viz cell below (the Mermaid diagram, the Graphviz DOT
    # diagram, both HTML displays, and the depth-filtered AAT graph) --
    # computed once here rather than re-deriving the same "maxdepth can be
    # None before a sentence is selected" guard in each of them.
    # tokengraph_to_html()/tokengraph_to_depth_html() take this as their own
    # `depth` (clause-level subordination depth); tokengraph_to_mermaid()/
    # tokengraph_to_dot() take it as `aat_depth` (a different notion that
    # agrees with subordination depth on any well-formed sentence -- see
    # each function's own docstring); filter_tokengraph_by_aat_depth() uses
    # that same aat_depth notion to shrink the tokengraph itself before the
    # AAT graph is built from it below -- one slider value, meaningfully the
    # same cutoff everywhere despite the different parameter names.
    depth = maxdepth.value if maxdepth is not None else None
    return (depth,)


@app.cell
def _(graphviz_available, mo):
    # "graphviz" is only ever offered as a choice when the graphviz PyPI
    # package actually imported successfully above -- see
    # latin_syntaxer_textinput.py's own diagram_tool cell for the identical
    # rationale; this can't rule out the OTHER failure mode (the package
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
def _(depth, selected_tokengraph, tokengraph_to_mermaid):
    diagram, mermaid_warnings = tokengraph_to_mermaid(selected_tokengraph, aat_depth=depth)
    return (diagram,)


@app.cell
def _(depth, selected_tokengraph, tokengraph_to_dot):
    # Compose Graphviz diagram: cheap to always compute regardless of which
    # tool is currently selected -- tokengraph_to_dot() is pure string
    # building with no dependency of its own (see notes/dot_diagrams.md),
    # unlike actually rendering it, which needs the graphviz package and
    # the `dot` executable (handled in diagram_display above).
    dot_source, dot_warnings = tokengraph_to_dot(selected_tokengraph, aat_depth=depth)
    return dot_source, dot_warnings


@app.cell
def _(selected_citation, sentence_dropdown):
    # Same alphanumeric-sanitizing convention latin_syntaxer_textinput.py's own
    # filename_base uses -- the sentence's own 1-based menu number goes
    # first (matching sentence_label()'s "<n>. ..." prefix) so every
    # download gets a distinct, stable name even across sentences that
    # share (or lack) a citation. Shared by both diagram tools' own
    # downloads below (it used to be named mermaid_filename_stem, back when
    # Mermaid was the only diagram tool this notebook offered).
    diagram_filename_stem = "sentence"
    if sentence_dropdown.value is not None:
        raw = f"{sentence_dropdown.value + 1}_{selected_citation or ''}"
        diagram_filename_stem = "".join(c if c.isalnum() else "_" for c in raw).strip("_") or "sentence"
    return (diagram_filename_stem,)


@app.cell
def _(diagram, diagram_filename_stem, diagram_tool, dot_source, mo, selected_tokengraph):
    # Downloads whichever diagram is currently selected/displayed above,
    # not both -- same reactive "follows the widget" convention
    # latin_syntaxer_textinput.py's own diagram_download cell uses. Mermaid
    # source is saved raw (unchanged from before this notebook offered a
    # choice of diagram tool at all); Graphviz source is likewise saved raw,
    # as .dot -- both are renderable elsewhere (mermaid.live, a README code
    # block, `dot -Tsvg`, an online DOT viewer) without needing this
    # notebook.
    if diagram_tool.value == "graphviz":
        diagram_download = mo.download(
            data=dot_source.encode("utf-8"),
            filename=f"{diagram_filename_stem}_dot.dot",
            label="Download Graphviz DOT source (.dot)",
            mimetype="text/plain",
            disabled=not selected_tokengraph,
        )
    else:
        diagram_download = mo.download(
            data=diagram.encode("utf-8"),
            filename=f"{diagram_filename_stem}_mermaid.mmd",
            label="Download Mermaid diagram (.mmd)",
            mimetype="text/plain",
            disabled=not selected_tokengraph,
        )
    return (diagram_download,)


@app.cell
def _(mo, selected_tokengraph, tokengraph_to_text):
    # Plain, uncolored text -- tokengraph_to_text() never emits HTML, but
    # the underlying surface text is still escaped before going into
    # mo.Html(), same as latin_syntaxer_ctsdata.py's own raw-passage-preview cell.
    import html as _html

    plaintext_html = mo.Html(
        "<b><i>Plain text</i></b>: " + _html.escape(tokengraph_to_text(selected_tokengraph))
    )
    return (plaintext_html,)


@app.cell
def _(depth, mo, selected_tokengraph, tokengraph_to_html):
    vuhtml = mo.Html(
        "<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(selected_tokengraph, depth=depth)
    )
    return (vuhtml,)


@app.cell
def _(depth, mo, selected_tokengraph, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(selected_tokengraph, depth=depth)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)
    return (indentpsg,)


@app.cell
def _(depth, filter_tokengraph_by_aat_depth, selected_tokengraph):
    # Filter the selected sentence's own tokengraph to the SAME depth
    # cutoff the Mermaid/Graphviz diagrams and HTML displays above use,
    # BEFORE building the AAT graph from it below -- so the AAT graph shown
    # here reflects only the clauses at or within the chosen depth, the
    # same way tokengraph_to_mermaid()'s/tokengraph_to_dot()'s own
    # aat_depth parameter limits which nodes THEY draw, rather than
    # building the full-depth AAT graph and then having no way to trim it.
    # See filter_tokengraph_by_aat_depth()'s own docstring (verbal_units.py)
    # for why this is safe: every token needed to resolve a KEPT verbal
    # expression's own governing chain is guaranteed to share that same
    # expression's own depth, so aatgraph() below never ends up with a
    # dangling reference into a filtered-away token.
    aat_tokengraph = filter_tokengraph_by_aat_depth(selected_tokengraph, depth)
    return (aat_tokengraph,)


@app.cell
def _(
    SimpleNamespace,
    aat_available,
    aat_tokengraph,
    aatgraph,
    graph_to_mermaid,
    selected_sentence,
    selected_verbalunits,
):
    # Build the AAT (Agent-Action-Target) graph for just the currently
    # selected sentence, limited to the depth cutoff above --  aatgraph()
    # takes (sentences, results) in analyze_sources()'s own shape, so a
    # one-element list of each is enough here; `results[i]` only needs to
    # duck-type `.tokengraph`/`.verbalunits`, which a bare SimpleNamespace
    # built from the depth-filtered tokengraph (aat_tokengraph, above) and
    # this sentence's own (unfiltered) verbalunits already satisfies --
    # aatgraph() only ever looks up a verbalunits entry for an anchor
    # that's still present in aat_tokengraph, so the extra entries for any
    # filtered-out anchor are simply never consulted. See USAGE.md's
    # "Building an AAT (Agent-Action-Target) graph".
    aat_diagram = None
    aat_warnings = []
    if aat_available and aat_tokengraph and selected_sentence is not None:
        result = SimpleNamespace(tokengraph=aat_tokengraph, verbalunits=selected_verbalunits)
        graph, aatgraph_warnings = aatgraph([selected_sentence], [result])
        aat_diagram, aat_mermaid_warnings = graph_to_mermaid(graph)
        aat_warnings = aatgraph_warnings + aat_mermaid_warnings
    return aat_diagram, aat_warnings


@app.cell
def _(aat_available, aat_diagram, aat_warnings, mo):
    # Same "compute a warnings list, show it in a callout only if
    # non-empty" convention latin_syntaxer_textinput.py's own
    # analysis_warnings display uses.
    if not aat_available:
        aat_display = mo.callout(
            mo.md(
                "The `aat` package isn't installed, so the AAT "
                "(Agent-Action-Target) graph can't be built here -- see "
                "USAGE.md's \"Building an AAT (Agent-Action-Target) graph\" "
                "section for how to install it."
            ),
            kind="warn",
        )
    elif aat_diagram is None:
        aat_display = mo.md("*Choose a sentence above to see its AAT (Agent-Action-Target) graph.*")
    else:
        aat_display = mo.vstack(
            [mo.md("**AAT (Agent-Action-Target) graph**"), mo.mermaid(aat_diagram)]
            + (
                [mo.callout(mo.md("\n".join(f"- {w}" for w in aat_warnings)), kind="warn")]
                if aat_warnings
                else []
            )
        )
    return (aat_display,)


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
    from types import SimpleNamespace

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import (
        aatgraph,
        filter_tokengraph_by_aat_depth,
        max_subordination_depth,
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_to_depth_html,
        tokengraph_to_dot,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
    )

    # aatgraph() (above) is always importable from arsgrammatica -- it
    # only raises when actually CALLED without the separate `aat` package
    # installed (see USAGE.md's "Building an AAT (Agent-Action-Target)
    # graph"). graph_to_mermaid() -- aat's own Mermaid renderer for the
    # AATGraph aatgraph() builds -- has no such fallback, so its import is
    # what actually detects whether `aat` is installed at all; the AAT
    # display cells below check aat_available rather than calling either
    # function and catching ImportError themselves.
    try:
        from aat.core import graph_to_mermaid

        aat_available = True
    except ImportError:
        graph_to_mermaid = None
        aat_available = False

    # graphviz (the PyPI package -- a thin subprocess wrapper around the
    # separately-installed Graphviz `dot` executable) is optional the same
    # way it is for latin_syntaxer_ctsdata.py's/latin_syntaxer_textinput.py's
    # own diagram display: importable or not, checked once here rather than
    # every display cell catching ImportError itself. Whether the `dot`
    # executable is actually on PATH is a SEPARATE check
    # (graphviz.ExecutableNotFound), made only when a diagram is actually
    # rendered -- see the diagram_display cell above.
    try:
        import graphviz

        graphviz_available = True
    except ImportError:
        graphviz = None
        graphviz_available = False

    return (
        Path,
        SimpleNamespace,
        aat_available,
        aatgraph,
        filter_tokengraph_by_aat_depth,
        graph_to_mermaid,
        graphviz,
        graphviz_available,
        max_subordination_depth,
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_to_depth_html,
        tokengraph_to_dot,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
    )


if __name__ == "__main__":
    app.run()
