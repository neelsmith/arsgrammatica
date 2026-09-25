import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Explore syntactic relationships in a saved analysis
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > No LM access needed -- browse a previously-saved analysis file (the same format `write_analyses()` produces), pick one sentence, then pick one relationship type to see it highlighted in the passage.
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

    #mo.vstack([analysis_status, sentence_dropdown])
    sentence_dropdown
    return


@app.cell(hide_code=True)
def _(plaintext_html):
    plaintext_html
    return


@app.cell(hide_code=True)
def _(mo, relationship_dropdown, relationship_html_display):
    mo.hstack([relationship_html_display, relationship_dropdown], widths=[4,1])
    return


@app.cell(hide_code=True)
def _(mo, selected_tokengraph):
    if not selected_tokengraph:
        relationship_status = mo.md("*Choose a sentence above to list the relationship types it attests.*")
    else:
        relationship_status = mo.md(
            "*Pick one relationship type below: its edges' start (source) tokens get "
            "underlined, their end (target) tokens get boxed. Hover over an underlined "
            "or boxed word to see exactly which edge(s) of this relationship it's part "
            "of -- other relations on the same word are left out of the tooltip.*"
        )

    return


@app.cell(hide_code=True)
def _(relationship_warnings_display):
    relationship_warnings_display
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
    # format) -- same file_browser setup as latin_syntaxer_review.py's own
    # analysis_file_browser, for the same reason: selecting a single FILE
    # by clicking it just works, unlike mo.ui.file_browser's "directory"
    # selection mode.
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
    # verbalunits slice out of the file's flat, whole-passage lists, so the
    # rest of this notebook only ever has to think about "the currently
    # selected sentence's own tokengraph" -- same as latin_syntaxer_review.py.
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
# a citation, or happen to start with the same words. Identical convention
# to latin_syntaxer_review.py's own sentence_label().
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
    # index into sentence_slices below.
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
def _(sentence_dropdown, sentence_slices):
    # The currently selected sentence's own tokengraph slice -- empty until
    # a sentence is actually picked, which every cell below already handles
    # gracefully (an empty relationship menu, an empty display).
    selected_tokengraph = []
    if sentence_dropdown.value is not None and 0 <= sentence_dropdown.value < len(sentence_slices):
        selected_tokengraph, _selected_verbalunits = sentence_slices[sentence_dropdown.value]
    return (selected_tokengraph,)


@app.cell
def _(mo, selected_tokengraph, tokengraph_relationship_types):
    # Every relationship label this ONE sentence actually attests --
    # tokengraph_relationship_types() already returns them alphabetically
    # sorted, so the dropdown's own option order needs no further sorting.
    # Passing a plain list (rather than a label->value dict, unlike
    # sentence_dropdown above) means relationship_dropdown.value IS the
    # relationship string itself -- exactly what
    # tokengraph_to_relationship_html()'s own `relationship` parameter
    # expects, with no extra lookup needed.
    relationship_types = (
        tokengraph_relationship_types(selected_tokengraph) if selected_tokengraph else []
    )
    relationship_dropdown = mo.ui.dropdown(
        options=relationship_types,
        label="*Relationship type*:",
    )
    return (relationship_dropdown,)


@app.cell
def _(
    mo,
    relationship_dropdown,
    selected_tokengraph,
    tokengraph_to_relationship_html,
):
    # relationship_dropdown.value is None until the user actually picks
    # one -- tokengraph_to_relationship_html(..., relationship=None) is a
    # well-defined, deliberate no-highlight default (identical output to
    # plain tokengraph_to_html(), see that function's own docstring), so
    # this needs no separate "nothing selected yet" branch.
    relationship_html, relationship_warnings = tokengraph_to_relationship_html(
        selected_tokengraph, relationship=relationship_dropdown.value
    )
    relationship_html_display = mo.Html(relationship_html)
    return relationship_html_display, relationship_warnings


@app.cell
def _(mo, relationship_warnings):
    if relationship_warnings:
        relationship_warnings_display = mo.callout(
            mo.md("\n".join(f"- {w}" for w in relationship_warnings)),
            kind="warn",
        )
    else:
        relationship_warnings_display = mo.md("")
    return (relationship_warnings_display,)


@app.cell
def _(mo, selected_tokengraph, tokengraph_to_text):
    # Plain, uncolored text for reference -- same convention as
    # latin_syntaxer_review.py's own plaintext_html cell.
    import html as _html

    plaintext_html = mo.Html(
        "<b><i>Passage text</i></b>: " + _html.escape(tokengraph_to_text(selected_tokengraph))
    )
    return (plaintext_html,)


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

    from arsgrammatica import (
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_relationship_types,
        tokengraph_to_relationship_html,
        tokengraph_to_text,
    )

    return (
        Path,
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_relationship_types,
        tokengraph_to_relationship_html,
        tokengraph_to_text,
    )


if __name__ == "__main__":
    app.run()
