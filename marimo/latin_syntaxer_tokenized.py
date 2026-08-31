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
    # Analyze a tokenized passage
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > Read a file with `#!sentences`/`#!tokens` blocks -- the format `utilities/tokenize_ctsdata.py` writes (see USAGE.md's "Tokenizing a source file without full syntax analysis") -- pick one sentence, then click *Analyze* to run it through syntax analysis with a configured LM.
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
def _(diagram, mo):
    mo.mermaid(diagram)
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
    # via utilities/tokenize_ctsdata.py -- see USAGE.md). A file_browser is
    # used for the same reason every sibling notebook's own file_browser is:
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
# uses to build SyntaxAnalysis's `passage` field, good enough for a short
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
    # MANAGING_PROMPT_SIZE.md) -- with the naive space-joined token text
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
def _(result):
    # Empty until an analysis has actually run -- every rendering utility
    # below already handles an empty tokengraph gracefully (an empty
    # diagram/string), same as latin_syntaxer_review.py's own
    # selected_tokengraph before a sentence is picked.
    finaltokens = result.tokengraph if result is not None else []
    return (finaltokens,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(finaltokens, tokengraph_to_mermaid):
    diagram, mermaid_warnings = tokengraph_to_mermaid(finaltokens)
    return (diagram,)


@app.cell
def _(finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens))
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
def _(finaltokens, maxdepth, mo, tokengraph_to_depth_html):
    # Guard against maxdepth being None (nothing analyzed yet) rather than
    # calling .value unconditionally -- same guard latin_syntaxer_review.py
    # uses for the same reason.
    depth = maxdepth.value if maxdepth is not None else None
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens, depth=depth)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)
    return (indentpsg,)


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
        tokengraph_to_depth_html,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        validate,
    )

    return (
        DEFAULT_CEILING,
        analyze_with_retry,
        max_subordination_depth,
        read_segmentation,
        tokengraph_to_depth_html,
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
        # latin_syntaxer_ctsdata.py's own configure_lm(): SyntaxAnalysis's
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
