import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo


    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Analyze a tokenized passage
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > Read a file with `#!sentences`/`#!tokens` blocks -- the format `utilities/tokenize_ctsdata.py` writes (see notes/serialization_formats.md's "Tokenizations without analysis") -- pick one sentence, then click *Analyze* to run it through syntax analysis with a configured LM.
    """)
    return


@app.cell(hide_code=True)
def _(tokenized_file_browser):
    tokenized_file_browser
    return


@app.cell(hide_code=True)
def _(analyze_button, mo, read_error, sentence_dropdown, sentences):
    if read_error is not None:
        tokenized_status = mo.callout(
            mo.md(f"Could not read this file as a tokenized/segmented file: {read_error}"),
            kind="danger",
        )
    elif not sentences:
        tokenized_status = mo.md("*Choose a tokenized file above to list its sentences.*")
    else:
        tokenized_status = mo.md(f"## Sentence selection\n\n*{len(sentences)} sentence(s) loaded from this file.*")

    mo.vstack(
        [tokenized_status, mo.hstack([sentence_dropdown, analyze_button], justify="start")]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    # Same "See cost" checkbox latin_syntaxer_ctsdata.py's own analysis
    # notebooks offer -- this one makes real LM calls too
    # (analyze_with_retry(), in the Analysis cell below) and had simply
    # never gotten this control.
    seecost = mo.ui.checkbox(label="*See cost*")
    seecost
    return (seecost,)


@app.cell(hide_code=True)
def _(cost_summary, format_lm_cost, mo, seecost):
    costdisplay = None
    if seecost.value:
        costdisplay = mo.md(f"**LM cost so far**: {format_lm_cost(cost_summary)}")
    costdisplay
    return


@app.cell(hide_code=True)
def _(sentence_preview):
    sentence_preview
    return


@app.cell(hide_code=True)
def _(analysis_warnings, download_widget, mo, save_extension):
    # Same download row as latin_syntaxer_ctsdata.py's own -- a save_extension
    # radio (cex/txt) next to the download button, plus any warning
    # serialize_analyses() itself raised (an id it couldn't find a
    # citation for, a sentence whose tokens don't form a contiguous run --
    # see serialization.py's own docstring), shown the same "don't just
    # crash, show a callout" way.
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
def _(maxdepth):
    maxdepth
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
def _(mo):
    mo.md("""
    ## Diagram syntactic relations
    """)
    return


@app.cell(hide_code=True)
def _(diagram_tool):
    diagram_tool
    return


@app.cell(hide_code=True)
def _(
    diagram,
    diagram_tool,
    displacy_svg,
    displacy_warnings,
    dot_source,
    dot_warnings,
    graphviz,
    mo,
):
    # Same three-way diagram_tool branch, and the same two distinct
    # Graphviz failure modes to degrade visibly from, as
    # latin_syntaxer_ctsdata.py's own diagram_display cell (see
    # notes/dot_diagrams.md/notes/displacy_viz.md): the `graphviz` package
    # itself missing is never reachable here either, since diagram_tool's
    # own options only offer "graphviz" when graphviz_available is True
    # (see that widget's definition below); the `dot` executable missing
    # from PATH (graphviz.ExecutableNotFound) can only be discovered by
    # actually trying, so it's still handled here. displaCy needs neither
    # check -- displacy_svg below is already a complete, ready-to-display
    # SVG string the moment it's computed, same as tokengraph_to_mermaid()'s
    # own diagram text.
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
    elif diagram_tool.value == "displacy":
        diagram_display = mo.vstack(
            [mo.Html(displacy_svg)]
            + (
                [mo.callout(mo.md("\n".join(f"- {w}" for w in displacy_warnings)), kind="warn")]
                if displacy_warnings
                else []
            )
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
    # Browse for a file previously written by write_segmentation() (usually
    # via utilities/tokenize_ctsdata.py -- see notes/serialization_formats.md's
    # "Tokenizations without analysis"). A file_browser is used for the
    # same reason every sibling notebook's own file_browser is:
    # selecting a single FILE by clicking it just works, unlike
    # mo.ui.file_browser's "directory" selection mode.
    tokenized_file_browser = mo.ui.file_browser(
        initial_path=Path(__file__).parent.parent,
        selection_mode="file",
        multiple=False,
        label="*Tokenized file*:",
    )
    return (tokenized_file_browser,)


@app.cell
def _(read_segmentation, tokenized_file_browser):
    # Re-read the file every time the file_browser's own selection changes.
    # No LM call here at all -- read_segmentation() reconstructs every
    # Sentence (and its Tokens) purely from the file's own #!sentences/
    # #!tokens text, cross-checking the two blocks against each other (see
    # arsgrammatica/segmentation_serialization.py's module docstring).
    tokenized_path = tokenized_file_browser.path(index=0)
    sentences = []
    read_error = None
    if tokenized_path is not None:
        try:
            sentences = read_segmentation(str(tokenized_path))
        except (ValueError, OSError) as e:
            read_error = str(e)
    return read_error, sentences


@app.function
# Label one menu entry as "<n>. <citation>: <first six words>…" -- numbered
# so entries are always unique even when several sentences share (or lack)
# a citation, or happen to start with the same words. Unlike
# latin_syntaxer_review.py's own sentence_label(), there's no
# tokengraph_to_text()-quality rendering available yet (these are raw,
# unanalyzed Tokens -- no tokentype, so no relation-aware spacing/enclitic
# handling) -- this preview is the same naive "join every token's own text
# with a space" approximation pipeline.py's own _render_sentence_text()
# uses to build SentenceAnalysis's `passage` field, good enough for a short
# preview label even though it isn't faithful surface text.
def sentence_label(index, citation, sentence, preview_words=6):
    words = [tok.text for tok in sentence.tokens]
    preview = " ".join(words[:preview_words])
    ellipsis = "…" if len(words) > preview_words else ""
    prefix = f"{citation}: " if citation else ""
    return f"{index + 1}. {prefix}{preview}{ellipsis}"


@app.cell
def _(mo, sentences):
    # Menu for selecting one sentence -- a dropdown, not a multiselect,
    # since exactly one sentence is analyzed at a time here (matching
    # latin_syntaxer_review.py's own single-sentence menu, not
    # latin_syntaxer_ctsdata.py's multi-passage one). Maps each label
    # directly to that sentence's own index, so sentence_dropdown.value is
    # an int usable to index into `sentences` directly.
    sentence_options = {}
    for i, sentence in enumerate(sentences):
        citation = sentence.tokens[0].citation if sentence.tokens else None
        sentence_options[sentence_label(i, citation, sentence)] = i

    sentence_dropdown = mo.ui.dropdown(
        options=sentence_options,
        label="*Sentence*:",
    )
    return (sentence_dropdown,)


@app.cell
def _(mo, sentence_dropdown):
    # A new instance is created (and analyze_button.value resets to False)
    # every time sentence_dropdown's own selection changes, since this cell
    # depends on sentence_dropdown.value -- so changing the selection
    # always requires a fresh, deliberate Analyze click rather than
    # silently re-using a previous click's result on a different sentence
    # (same reasoning as latin_syntaxer_ctsdata.py's own analyze_button).
    analyze_button = mo.ui.run_button(
        label="Analyze",
        disabled=sentence_dropdown.value is None,
    )
    return (analyze_button,)


@app.cell
def _(sentence_dropdown, sentences):
    # The currently selected sentence -- None until one is actually picked.
    selected_sentence = None
    if sentence_dropdown.value is not None and 0 <= sentence_dropdown.value < len(sentences):
        selected_sentence = sentences[sentence_dropdown.value]
    return (selected_sentence,)


@app.cell
def _(mo, selected_sentence):
    # A plain, uncolored preview of the selected sentence's own raw text --
    # shown as soon as a sentence is picked, independent of whether Analyze
    # has been clicked yet (no LM call involved, same reasoning as
    # latin_syntaxer_ctsdata.py's own rawpreview cell). Uses the same naive
    # "join every token's own text with a space" approximation as
    # sentence_label()'s own preview and the Analysis cell's own
    # passage_text -- these are pre-analysis Tokens, so there's no
    # tokentype-aware spacing/enclitic handling available yet (see
    # sentence_label()'s own docstring). Deliberately plain text, with no
    # verbal-unit coloring, unlike vuhtml below -- a stable, always-legible
    # reference for the colored rendering below it.
    import html as _html

    if selected_sentence is not None and selected_sentence.tokens:
        _text = " ".join(tok.text for tok in selected_sentence.tokens)
        sentence_preview = mo.md(f"**Selected sentence**: {_html.escape(_text)}")
    else:
        sentence_preview = mo.md("")
    return (sentence_preview,)


@app.cell
def _(selected_sentence):
    # A readable default filename base for the diagram download below,
    # drawn from the selected sentence's own citation (every token in one
    # sentence shares the same `citation` -- see arsgrammatica/models.py's
    # Token) -- same alnum-sanitizing convention latin_syntaxer_ctsdata.py's
    # own filename_base uses, just derived from one sentence rather than a
    # list of selected passages. This notebook has no "serialize analysis
    # to file" section of its own (unlike latin_syntaxer_ctsdata.py) to
    # share a filename_base with -- it exists here purely for the diagram
    # download's own filename.
    filename_base = "analysis"
    if selected_sentence is not None and selected_sentence.tokens:
        _citation = selected_sentence.tokens[0].citation
        if _citation:
            filename_base = _citation
    filename_base = "".join(c if c.isalnum() else "_" for c in filename_base).strip("_") or "analysis"
    return (filename_base,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI selections for serialization
    """)
    return


@app.cell
def _(mo):
    # Same save_extension radio as latin_syntaxer_ctsdata.py's own.
    save_extension = mo.ui.radio(
        options=["cex", "txt"], value="cex", inline=True, label="*File extension*:"
    )
    return (save_extension,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Analysis
    """)
    return


@app.cell
def _(analyze_button, analyze_with_retry, selected_sentence, validate):
    # Run syntax analysis on the selected sentence's own tokens when the
    # Analyze button is clicked. analyze_button.value is True for exactly
    # the one reactive cycle triggered by a click. Goes through
    # token_budget.analyze_with_retry() rather than calling analyze()
    # directly -- same calibrated max_tokens budgeting and
    # retry-on-truncation pipeline.analyze_sources() itself uses (see
    # token_budget.py's own module docstring) -- with the naive
    # space-joined token text
    # (pipeline.py's own _render_sentence_text() approximation) as the
    # `passage` field. validate()'s own problem list is printed the same
    # way pipeline.analyze_sources() prints it -- to the marimo server's
    # own console, not this notebook's UI -- rather than duplicating that
    # convention as a new callout here.
    result = None
    if analyze_button.value and selected_sentence is not None and selected_sentence.tokens:
        passage_text = " ".join(tok.text for tok in selected_sentence.tokens)
        result = analyze_with_retry(passage=passage_text, tokens=selected_sentence.tokens)

        problems = validate(selected_sentence.tokens, result)
        if problems:
            print(f"Validation warnings (sentence starting at {selected_sentence.tokens[0].id}):")
            for p in problems:
                print(f"  - {p}")
    return (result,)


@app.cell
def _(graphviz_available, mo):
    # Same "graphviz" option, gated on graphviz_available, as
    # latin_syntaxer_ctsdata.py's own diagram_tool -- see that notebook's
    # identical cell/comment. "displacy" (notes/displacy_viz.md) is always
    # offered, unlike "graphviz", since tokengraph_to_displacy_svg() has no
    # external dependency to check for at all.
    diagram_tool = mo.ui.radio(
        options=["mermaid", "graphviz", "displacy"] if graphviz_available else ["mermaid", "displacy"],
        value="mermaid",
        inline=True,
        label="*Diagram tool*:",
    )
    return (diagram_tool,)


@app.cell
def _(result):
    # Empty until an analysis has actually run -- every rendering utility
    # below already handles an empty tokengraph gracefully (an empty
    # diagram/string), same as latin_syntaxer_review.py's own
    # selected_tokengraph before a sentence is picked.
    finaltokens = result.tokengraph if result is not None else []
    return (finaltokens,)


@app.cell
def _(lm, result, summarize_lm_cost):
    # The `_ = result` line below doesn't do anything with `result` -- it
    # exists purely so marimo sees this cell as depending on it (marimo
    # derives a cell's inputs from actual name usage in its body, not just
    # the function signature) and re-runs the cell on every Analyze click.
    # Depending on `lm` alone doesn't do that: lm.history is mutated in
    # place by each LM call, and marimo only re-runs a cell when a
    # variable it actually reads is REASSIGNED -- `lm` itself never is,
    # after configure_lm() first creates it -- see
    # latin_syntaxer_ctsdata.py's identical cell/comment for the full
    # explanation.
    _ = result
    #
    # summarize_lm_cost() (arsgrammatica/lm_cost.py) sums cost across
    # every call in lm.history and never crashes on an empty history (true
    # before the first Analyze click) or a call served from dspy's own
    # cache (cost=None) -- see that module's own docstring.
    cost_summary = summarize_lm_cost(lm.history)
    return (cost_summary,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(depth, finaltokens, mo, tokengraph_to_html):
    # depth=depth (not omitted): tokengraph_to_html()'s own `depth`
    # parameter caps how deep the COLOR highlighting goes -- it never drops
    # a token from the rendered text, only un-highlights one whose verbal
    # unit's subordination depth exceeds `depth`, falling back to plain,
    # unhighlighted (but still escaped) text -- same clause-level
    # subordination-depth notion tokengraph_to_depth_html() already uses
    # for indentpsg below, via the same `depth` value from maxdepth's own
    # slider, so both displays' idea of "how deep" always agree.
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens, depth=depth))
    return (vuhtml,)


@app.cell
def _(finaltokens, max_subordination_depth, mo):
    # Same depth-cap slider as the other analysis notebooks -- left None
    # until a sentence has actually been analyzed.
    maxdepth = None
    if finaltokens:
        maxdepth = mo.ui.slider(
            start=0,
            stop=max_subordination_depth(finaltokens),
            label="*Maximum depth of subordination to display*:",
            show_value=True,
            value=max_subordination_depth(finaltokens),
        )
    return (maxdepth,)


@app.cell
def _(maxdepth):
    # Guard against maxdepth being None (nothing analyzed yet) rather than
    # calling .value unconditionally -- same guard latin_syntaxer_review.py
    # uses for the same reason. Shared by both the indented-text display
    # below and the Mermaid diagram cell, so the diagram's own AAT-depth
    # cutoff always matches whatever the text-display depth slider shows.
    depth = maxdepth.value if maxdepth is not None else None
    return (depth,)


@app.cell
def _(depth, finaltokens, tokengraph_to_mermaid):
    diagram, mermaid_warnings = tokengraph_to_mermaid(finaltokens, aat_depth=depth)
    return (diagram,)


@app.cell
def _(depth, finaltokens, tokengraph_to_dot):
    # Compose Graphviz diagram: cheap to always compute regardless of which
    # tool is currently selected -- tokengraph_to_dot() is pure string
    # building with no dependency of its own (see notes/dot_diagrams.md),
    # unlike actually rendering it, which needs the graphviz package and
    # the `dot` executable (handled in the diagram_display cell above).
    # Same cell as latin_syntaxer_ctsdata.py's own.
    dot_source, dot_warnings = tokengraph_to_dot(finaltokens, aat_depth=depth)
    return dot_source, dot_warnings


@app.cell
def _(depth, finaltokens, tokengraph_to_displacy_svg):
    # Compose the displaCy-style diagram: cheap to always compute regardless
    # of which tool is currently selected, same reasoning as dot_source
    # above -- but unlike dot_source, tokengraph_to_displacy_svg() has no
    # external dependency at all (see notes/displacy_viz.md), so this is
    # already a complete, ready-to-display SVG string, with no separate
    # rendering step for diagram_display to handle. Same cell as
    # latin_syntaxer_ctsdata.py's own.
    displacy_svg, displacy_warnings = tokengraph_to_displacy_svg(finaltokens, aat_depth=depth)
    return displacy_svg, displacy_warnings


@app.cell
def _(
    diagram,
    diagram_tool,
    displacy_svg,
    dot_source,
    filename_base,
    finaltokens,
    mo,
):
    # Downloads whichever diagram is currently selected/displayed above,
    # not both -- same reactive "follows the widget" convention as
    # latin_syntaxer_ctsdata.py's own diagram_download. Mermaid source is
    # wrapped in a ```mermaid fenced code block and saved as .md; Graphviz
    # source is saved raw as .dot; displaCy's own SVG is already fully
    # rendered the moment it's computed, so its download offers the .svg
    # directly. disabled=not finaltokens rather than checking the
    # diagram/dot_source strings themselves -- both always render a
    # non-empty header (e.g. "graph BT") even for an empty tokengraph, so
    # the strings alone can't tell "nothing to show yet" apart from "a
    # real, if minimal, diagram".
    if diagram_tool.value == "graphviz":
        diagram_download = mo.download(
            data=dot_source.encode("utf-8"),
            filename=f"{filename_base}.dot",
            label="Download Graphviz DOT source (.dot)",
            mimetype="text/plain",
            disabled=not finaltokens,
        )
    elif diagram_tool.value == "displacy":
        diagram_download = mo.download(
            data=displacy_svg.encode("utf-8"),
            filename=f"{filename_base}_displacy.svg",
            label="Download displaCy-style diagram (.svg)",
            mimetype="image/svg+xml",
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
def _(depth, finaltokens, mo, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens, depth=depth)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)
    return (indentpsg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Save analysis
    """)
    return


@app.cell
def _(finaltokens, lm, result, selected_sentence, serialize_analyses):
    # Same serialize_analyses() call as latin_syntaxer_ctsdata.py's own,
    # just over this notebook's own single selected_sentence/result rather
    # than a flattened list spanning several passages: `sentences` is
    # `[selected_sentence]` (the one pre-analysis Sentence this tokengraph
    # came from), `verbalunits` is that one result's own list (no
    # flattening needed for a single sentence), and `reasoning` is its one
    # entry, matching '#!lm's "one reasoning per sentence" contract (see
    # serialization.py's own docstring). Left empty until an analysis has
    # actually run, same guard finaltokens/vuhtml/etc. already use.
    analysis_text, analysis_warnings = "", []
    if result is not None and selected_sentence is not None:
        analysis_text, analysis_warnings = serialize_analyses(
            [selected_sentence],
            result.verbalunits,
            finaltokens,
            model=lm.model,
            reasoning=[result.reasoning],
        )
    return analysis_text, analysis_warnings


@app.cell
def _(analysis_text, filename_base, mo, result, save_extension):
    # mo.download() puts the browser in charge of where the file lands,
    # same as latin_syntaxer_ctsdata.py's own download_widget -- filename
    # reactively follows both the sentence-derived filename_base and
    # whichever extension is chosen. disabled=result is None (not
    # `not analysis_text`, which an all-warnings-no-content edge case could
    # still leave falsy) -- there's exactly one result here, not a list.
    download_widget = mo.download(
        data=analysis_text.encode("utf-8"),
        filename=f"{filename_base}.{save_extension.value}",
        label="Download analysis",
        mimetype="text/plain",
        disabled=result is None,
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
    from dotenv import load_dotenv

    return Path, dspy, load_dotenv, os


@app.cell
def _(Path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import (
        DEFAULT_CEILING,
        analyze_with_retry,
        max_subordination_depth,
        read_segmentation,
        serialize_analyses,
        tokengraph_to_depth_html,
        tokengraph_to_displacy_svg,
        tokengraph_to_dot,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        validate,
        summarize_lm_cost,
        format_lm_cost,
    )

    # graphviz (the PyPI package -- a thin subprocess wrapper around the
    # separately-installed Graphviz `dot` executable) is optional the same
    # way it is for latin_syntaxer_ctsdata.py's own diagram display:
    # importable or not, checked once here rather than every display cell
    # catching ImportError itself. Whether the `dot` executable is actually
    # on PATH is a SEPARATE check (graphviz.ExecutableNotFound), made only
    # when a diagram is actually rendered -- see the diagram_display cell
    # above.
    try:
        import graphviz

        graphviz_available = True
    except ImportError:
        graphviz = None
        graphviz_available = False
    return (
        DEFAULT_CEILING,
        analyze_with_retry,
        format_lm_cost,
        graphviz,
        graphviz_available,
        max_subordination_depth,
        read_segmentation,
        serialize_analyses,
        summarize_lm_cost,
        tokengraph_to_depth_html,
        tokengraph_to_displacy_svg,
        tokengraph_to_dot,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        validate,
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
def _(DEFAULT_CEILING, dspy, getenv):
    def configure_lm():
        # Always rebuild from the current environment -- no
        # `if dspy.settings.lm is not None: return dspy.settings.lm` guard.
        # dspy.settings is a module-level singleton that outlives any single
        # cell run in marimo's long-lived kernel, so that guard would freeze
        # whichever LM (and api_key) was first configured for the rest of
        # the kernel's life, silently ignoring every later edit to .env --
        # same reasoning as latin_syntaxer_ctsdata.py's own configure_lm().
        api_base = getenv("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
        model = getenv("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")
        api_key = getenv("API_KEY", "API_KEY")

        if not api_key:
            raise RuntimeError(
                "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
            )

        # An explicit numeric baseline, not None (dspy.LM's own default) --
        # see arsgrammatica/token_budget.py's DEFAULT_CEILING and
        # syntaxer_main.py's own configure_lm() for the full rationale: the
        # Analyze cell below overrides this per call via analyze_with_retry(),
        # but this notebook's own budget only ever bounds THAT call -- it
        # doesn't change what dspy's own truncation warning prints, which
        # always reports this baseline, never a per-call override, and would
        # otherwise misleadingly read "max_tokens=None" on every truncation
        # even when a much larger, correctly-applied budget was actually used.
        lm_kwargs = dict(model=model, api_base=api_base, api_key=api_key, max_tokens=DEFAULT_CEILING)

        # Anthropic prompt caching -- same reasoning as
        # latin_syntaxer_ctsdata.py's own configure_lm(): SentenceAnalysis's
        # system message is byte-identical on every call, so marking it
        # with an ephemeral cache_control breakpoint lets a repeat call
        # within Anthropic's cache TTL reuse it cheaply. Gated on the model
        # actually being Anthropic-routed, same as the sibling notebook.
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
