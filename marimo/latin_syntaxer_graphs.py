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
    # Characterize token-graph structure with NetworkX
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > No LM access needed -- browse a previously-saved analysis file (the same format `write_analyses()` produces), pick one or more sentences, and compute NetworkX-based size, complexity, and shape metrics for each one's own dependency graph.
    """)
    return


@app.cell(hide_code=True)
def _(analysis_file_browser):
    analysis_file_browser
    return


@app.cell(hide_code=True)
def _(mo, read_error, sentence_multiselect, sentences, split_error):
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

    mo.vstack([analysis_status, sentence_multiselect])
    return


@app.cell(hide_code=True)
def _(sentence_graph_displays):
    sentence_graph_displays
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
    # file_browser is used for the same reason latin_syntaxer_review.py's own
    # analysis_file_browser is: selecting a single FILE by clicking it just
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
    # ever has to think about "this one sentence's own tokengraph", exactly
    # what tokengraph_to_networkx() (below) expects.
    sentence_slices = []
    split_error = None
    if sentences:
        try:
            sentence_slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)
        except ValueError as e:
            split_error = str(e)
    return sentence_slices, split_error


@app.function
# Label one menu entry as "<n>. <citation>: <first six words>…" -- the same
# convention latin_syntaxer_review.py's own sentence_label() uses, so a
# sentence numbered here is the same sentence numbered there.
def sentence_label(index, citation, sentence_tokengraph, tokengraph_to_text):
    preview_text = tokengraph_to_text(sentence_tokengraph)
    words = preview_text.split()
    preview = " ".join(words[:6])
    ellipsis = "…" if len(words) > 6 else ""
    prefix = f"{citation}: " if citation else ""
    return f"{index + 1}. {prefix}{preview}{ellipsis}"


@app.cell
def _(mo, sentence_slices, sentences, tokengraph_to_text):
    # Menu for selecting one or more sentences -- a multiselect, since
    # graph_metrics() is meaningful one sentence at a time and comparing
    # several side by side is the whole point here, unlike
    # latin_syntaxer_review.py's single-sentence dropdown. Maps each label
    # directly to that sentence's own index, so sentence_multiselect.value
    # is a list of ints usable to index into sentence_slices below.
    sentence_options = {}
    if sentence_slices:
        for i, (sentence, (sentence_tokengraph, _sentence_verbalunits)) in enumerate(
            zip(sentences, sentence_slices)
        ):
            citation = sentence.tokens[0].citation if sentence.tokens else None
            sentence_options[sentence_label(i, citation, sentence_tokengraph, tokengraph_to_text)] = i

    sentence_multiselect = mo.ui.multiselect(
        options=sentence_options,
        label="*Sentence(s)*:",
    )
    return (sentence_multiselect,)


@app.cell
def _(sentence_multiselect):
    # Always display selected sentences in file order, not whatever order
    # the multiselect widget happens to report clicks in (same reasoning as
    # latin_syntaxer_ctsdata.py's own selected_rows) -- options map directly
    # to plain ints here, so sorting them is enough to recover file order.
    selected_indices = sorted(sentence_multiselect.value)
    return (selected_indices,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Graph construction and metrics
    """)
    return


@app.function
def render_sentence_metrics(
    index,
    sentence,
    sentence_tokengraph,
    tokengraph_to_networkx,
    graph_metrics,
    tokengraph_to_text,
    mo,
):
    """Build one sentence's own display: a heading (matching
    sentence_label()'s numbering), a NetworkX MultiDiGraph built via
    tokengraph_to_networkx() (the same nodes/labels/edges
    tokengraph_to_mermaid() would draw -- see graphs.py), and
    graph_metrics()'s size/complexity and shape metrics for that graph."""
    citation = sentence.tokens[0].citation if sentence.tokens else None
    heading = sentence_label(index, citation, sentence_tokengraph, tokengraph_to_text)

    graph, warnings = tokengraph_to_networkx(sentence_tokengraph)
    metrics = graph_metrics(graph)

    longest_chain_display = (
        metrics.longest_chain if metrics.longest_chain is not None else "n/a (cycle detected)"
    )
    size_table = "\n".join([
        "| Metric | Value |",
        "|---|---|",
        f"| Tokens (nodes) | {metrics.node_count} |",
        f"| Relations (edges) | {metrics.edge_count} |",
        f"| Cyclomatic number (edges beyond a spanning tree) | {metrics.cyclomatic_number} |",
        f"| Longest dependency chain (edges) | {longest_chain_display} |",
    ])

    shape_table = "\n".join([
        "| Metric | Value |",
        "|---|---|",
        f"| Leaf tokens (no dependents) | {metrics.leaf_count} ({metrics.leaf_fraction:.0%}) |",
        f"| Mean dependents per token | {metrics.mean_dependents:.2f} |",
        f"| Max dependents (single token) | {metrics.max_dependents} |",
    ])

    relationship_line = ", ".join(
        f"{label} ({count})"
        for label, count in sorted(
            metrics.relationship_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ) or "*none*"

    pieces = [
        f"#### {heading}",
        f"**Size & complexity**\n\n{size_table}",
        f"**Shape**\n\n{shape_table}\n\n**Relationship types**: {relationship_line}",
    ]
    if warnings:
        # Same "skipped edge" warnings tokengraph_to_mermaid() can report
        # for this sentence (a relatedtoken*/relationship* pointing at a
        # punctuation token or a missing id) -- worth surfacing here too,
        # since a skipped edge means the graph below is missing a relation
        # the analysis actually recorded.
        warning_lines = "\n".join(f"- {w}" for w in warnings)
        pieces.append(f"**Warnings**:\n\n{warning_lines}")

    return mo.md("\n\n".join(pieces))


@app.cell
def _(
    graph_metrics,
    mo,
    selected_indices,
    sentence_slices,
    sentences,
    tokengraph_to_networkx,
    tokengraph_to_text,
):
    if selected_indices:
        sentence_graph_displays = mo.vstack(
            [
                render_sentence_metrics(
                    i,
                    sentences[i],
                    sentence_slices[i][0],
                    tokengraph_to_networkx,
                    graph_metrics,
                    tokengraph_to_text,
                    mo,
                )
                for i in selected_indices
            ]
        )
    else:
        sentence_graph_displays = mo.md("*Select one or more sentences above.*")
    return (sentence_graph_displays,)


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
        graph_metrics,
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_to_networkx,
        tokengraph_to_text,
    )

    return (
        Path,
        graph_metrics,
        read_analyses,
        split_analysis_by_sentence,
        tokengraph_to_networkx,
        tokengraph_to_text,
    )


if __name__ == "__main__":
    app.run()
