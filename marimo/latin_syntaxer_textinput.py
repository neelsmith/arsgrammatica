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
    *Enter values for a base URN, passage reference, and text to analyze, then submit the form with the `Analyze` button.*
    """)
    return


@app.cell(hide_code=True)
def _(input_form):
    input_form
    return


@app.cell(hide_code=True)
def _(disable_cache, mo, seecost):
    mo.hstack([seecost, disable_cache], justify="start")
    return


@app.cell(hide_code=True)
def _(costdisplay):
    costdisplay
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
    # diagram_tool.value == "graphviz", same convention
    # latin_syntaxer_ctsdata.py's own diagram_display cell uses (see
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
def _(diagram_download):
    diagram_download
    return


@app.cell
def _(mo):
    seetokens = mo.ui.checkbox(label="*See list of tokens*")
    seecost = mo.ui.checkbox(label="*See cost*")
    seeprompts = mo.ui.checkbox(label="*See prompts*")
    # dspy.LM caches responses by default (model + messages + config), so
    # re-submitting the exact same form values normally just replays the
    # earlier result instead of hitting the LM again -- correct for
    # everyday use, but exactly the wrong behavior when you're
    # deliberately re-running the same passage to see whether the LM's
    # output changes (e.g. after a prompt tweak, or to check run-to-run
    # variance, or to get a fresh sample after a truncated/malformed
    # response -- see token_budget.py's analyze_with_retry(), which
    # already bypasses the cache on its own internal retries but has no
    # way to force a fresh *first* attempt). This is dspy's own
    # client-side response cache, unrelated to configure_lm()'s Anthropic
    # `cache_control_injection_points` prompt caching below -- that one
    # only caches the STATIC system-message prefix to make each
    # still-genuinely-fresh call cheaper, it never replays a whole
    # response, so it stays on regardless of this checkbox.
    disable_cache = mo.ui.checkbox(label="*Disable LM cache (debugging)*")
    mo.hstack([seetokens, seeprompts], justify="start")
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
        costdisplay = mo.md(f"**Total cost**: {format_lm_cost(cost_summary)}")
    costdisplay
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
    ## Analysis
    """)
    return


@app.cell
def _(analyze_string, input_form):
    # Analyze text passage -- only once the form has been submitted at
    # least once (input_form.value is None until then), and only again on
    # each subsequent submission, not on every keystroke in the form's own
    # inputs.
    passage = ''
    sentences, results = [], []
    if input_form.value and input_form.value.get("text_area"):
        passage = input_form.value["text_area"]
        citation = input_form.value["urnbase"] + input_form.value["citation_context"]
        sentences, results = analyze_string(passage, citation=citation)
    return results, sentences


@app.cell
def _(combined_tokengraph, results):
    # Flatten every sentence's own tokengraph into the one combined list
    # every viz/display cell below shares -- pulled out as its own cell
    # (rather than produced inside the Mermaid-diagram cell, as it used to
    # be) so maxdepth's own slider (bounded by THIS SAME finaltokens, via
    # max_subordination_depth()) can sit upstream of, and then feed its
    # value back into, the diagram-composition cells below without
    # creating a reactive dependency cycle (finaltokens -> maxdepth ->
    # depth -> diagram, never the other way around).
    finaltokens = combined_tokengraph(results)
    return (finaltokens,)


@app.cell
def _(finaltokens, max_subordination_depth, mo):
    # Same slider convention as latin_syntaxer_ctsdata.py's own `maxdepth`
    # widget: None until there's something to bound it by, then a slider
    # from 0 up to this passage's own deepest subordination level,
    # defaulting to "show everything" (the max itself).
    maxdepth = None
    if finaltokens:
        maxdepth = mo.ui.slider(
            start=0,
            stop=max_subordination_depth(finaltokens),
            label="*Maximum depth to display*:",
            show_value=True,
            value=max_subordination_depth(finaltokens),
        )
    return (maxdepth,)


@app.cell
def _(maxdepth):
    # Shared by every viz cell below (the Mermaid diagram, the Graphviz
    # DOT diagram, and both HTML displays) -- computed once here rather
    # than re-deriving the same "maxdepth can be None before the first
    # Analyze submission" guard in each of them. tokengraph_to_html()/
    # tokengraph_to_depth_html() take this as their own `depth` (clause-
    # level subordination depth); tokengraph_to_mermaid()/tokengraph_to_dot()
    # take it as `aat_depth` (a different notion that agrees with
    # subordination depth on any well-formed sentence -- see each
    # function's own docstring) -- one slider value, meaningfully the same
    # cutoff everywhere despite the two different parameter names.
    depth = maxdepth.value if maxdepth is not None else None
    return (depth,)


@app.cell
def _(graphviz_available, mo):
    # "graphviz" is only ever offered as a choice when the graphviz PyPI
    # package actually imported successfully above -- see
    # latin_syntaxer_ctsdata.py's own diagram_tool cell for the identical
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
    # the `dot` executable (handled in diagram_display below).
    dot_source, dot_warnings = tokengraph_to_dot(finaltokens, aat_depth=depth)
    return dot_source, dot_warnings


@app.cell
def _(sentences):
    tokens = [tok for sentence in sentences for tok in sentence.tokens]
    return


@app.cell
def _(results):
    vus = [res.verbalunits for res in results]
    return


@app.cell
def _(lm, results, summarize_lm_cost):
    # The `_ = results` line below doesn't do anything with `results` --
    # it exists purely so marimo sees this cell as depending on it (marimo
    # derives a cell's inputs from actual name usage in its body, not just
    # the function signature) and re-runs the cell on every form
    # submission. Depending on `lm` alone doesn't do that: lm.history is
    # mutated in place by each LM call, and marimo only re-runs a cell
    # when a variable it actually reads is REASSIGNED -- `lm` itself
    # never is, after configure_lm() first creates it -- see
    # latin_syntaxer_ctsdata.py's identical cell/comment for the full
    # explanation.
    _ = results
    #
    # summarize_lm_cost() (arsgrammatica/lm_cost.py) sums cost across
    # EVERY call in lm.history, not just the last one -- analyze_string()
    # can segment its passage into several sentences, each its own
    # SentenceAnalysis call, on top of the one segmentation call, so this
    # is what actually makes "Total cost" above a total rather than just
    # the last individual call's own cost. It also never crashes on an
    # empty history (true before the form's first submission) or on a
    # call served from dspy's own cache (cost=None) -- see that module's
    # own docstring.
    cost_summary = summarize_lm_cost(lm.history)
    return (cost_summary,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(finaltokens, input_form, mo, tokengraph_to_text):
    citation_label = input_form.value["citation_context"] if input_form.value else ""
    psghtml = mo.Html(f"<b><i>Passage {citation_label}</i></b>: " + tokengraph_to_text(finaltokens))
    return (psghtml,)


@app.cell
def _(depth, finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html(
        "<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens, depth=depth)
    )
    return (vuhtml,)


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


@app.cell
def _(input_form):
    # A readable default filename base, drawn from whatever citation the
    # form was submitted with (falling back to "analysis" if the passage
    # field was left blank) -- the extension is chosen separately, via
    # save_extension below.
    filename_base = ""
    if input_form.value:
        filename_base = (input_form.value.get("urnbase") or "") + (input_form.value.get("citation_context") or "")
    filename_base = "".join(c if c.isalnum() else "_" for c in filename_base).strip("_") or "analysis"
    return (filename_base,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI
    """)
    return


@app.cell
def _(mo):
    urnbase = mo.ui.text(value="urn:cts:latinLit:stoa1263.stoa001.hc:", label="*Base URN*:")
    return (urnbase,)


@app.cell
def _(mo):
    citation_context = mo.ui.text(placeholder="urn:cts:latinLit:....", label="*Passage*:")
    return (citation_context,)


@app.cell
def _(mo):
    text_area = mo.ui.text_area(value = "arma virumque cano.", full_width=True, label="*Text to analyze*:")
    return (text_area,)


@app.cell
def _(citation_context, mo, text_area, urnbase):
    # All three inputs as one form -- marimo only updates input_form.value
    # (and so only re-triggers the Analysis cell below) when the whole form
    # is submitted, never on every keystroke in an individual field. This
    # is the same batch()/form() shape sketched out (but never wired up) in
    # syntaxer.py's own commented-out UI cell.
    input_form = (
        mo.md(
            """
            {urnbase}

            {citation_context}

            {text_area}
            """
        )
        .batch(urnbase=urnbase, citation_context=citation_context, text_area=text_area)
        .form(submit_button_label="Analyze")
    )
    return (input_form,)


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


@app.cell
def _(diagram, diagram_tool, dot_source, filename_base, finaltokens, mo):
    # Downloads whichever diagram is currently selected/displayed above,
    # not both -- same reactive "follows the widget" convention
    # save_extension/download_widget already use for the serialized
    # analysis. Mermaid source is wrapped in a ```mermaid fenced code
    # block and saved as .md; Graphviz source is saved raw as .dot,
    # matching latin_syntaxer_ctsdata.py's own diagram_download cell --
    # both are renderable elsewhere (a Markdown viewer with Mermaid
    # support, `dot -Tsvg`, an online DOT viewer, Quarto's fenced
    # ```{dot}```/```{mermaid}``` blocks) without needing this notebook.
    # disabled=not finaltokens rather than checking the diagram/dot_source
    # strings themselves -- both always render a non-empty header (e.g.
    # "graph BT") even for an empty tokengraph, so the strings alone can't
    # tell "nothing to show yet" apart from "a real, if minimal, diagram".
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
        analyze_string,
        tokengraph_to_mermaid,
        tokengraph_to_dot,
        combined_tokengraph,
        tokengraph_to_html,
        tokengraph_to_text,
        tokengraph_to_depth_html,
        serialize_analyses,
        max_subordination_depth,
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
    # below.
    try:
        import graphviz

        graphviz_available = True
    except ImportError:
        graphviz = None
        graphviz_available = False
    return (
        DEFAULT_CEILING,
        analyze_string,
        combined_tokengraph,
        format_lm_cost,
        graphviz,
        graphviz_available,
        max_subordination_depth,
        serialize_analyses,
        summarize_lm_cost,
        tokengraph_to_depth_html,
        tokengraph_to_dot,
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
        # analyze_string() -> analyze_sources() overrides this per call via
        # analyze_with_retry(), but segment_sources()'s own LM call does not,
        # so without this it would fall through to whatever the provider/
        # litellm defaults to; it also keeps dspy's own truncation warning
        # (which always reports this baseline, never a per-call override)
        # from misleadingly reading "max_tokens=None".
        #
        # cache=not disable_cache.value: dspy.LM defaults to caching every
        # response it gets (keyed on model + messages + these very
        # lm_kwargs), so re-submitting the form with an unchanged passage
        # normally just replays the cached result rather than calling the
        # LM again -- see the *Disable LM cache (debugging)* checkbox
        # above for why that's sometimes exactly what you don't want.
        # Reading disable_cache.value here (rather than passing
        # `cache=False` unconditionally) means toggling the checkbox takes
        # effect immediately: it's a parameter of this very cell, so
        # flipping it rebuilds configure_lm's closure (and, downstream,
        # the `lm = configure_lm()` cell) the same way editing .env does.
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
