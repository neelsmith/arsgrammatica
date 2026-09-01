---
title: marimo notebooks
---

[marimo](https://marimo.io) is a reactive notebook system written in Python. You can find the notebooks listed in the `marimo` directory of the `arsgrammatica` github repository,  here are available in the `marimo` directory, and run them as you would any marimo notebook, e.g., `marimo run NOTEBOOKNAME.py`.

::: {.callout-warning}
The poorly chosen names for these notebooks will certainly be changed (and improved!) in a future release of `arsgrammatica`.
:::

## Marimo notebooks for analysis with a configured language model

`latin_syntaxer_workflow.py` and `latin_syntaxer_ctsdata.py` use a configured language model to analyze the syntax of Latin text. To configure your model, create an `.env` file like this:


```bash
API_BASE=https://localmodel/api
MODEL=litellm/modelname
API_KEY=your-key-here
```



### `latin_syntaxer_workflow.py`

A notebook for a real-world testing loop. Enter text content and identifier for a passage, analyze it, and visualize the results. Optionally download the analysis results.

### `latin_syntaxer_ctsdata.py`

Citable passage to analyze come from a source file in CEX format. Load a file, then pick one or more passages to analyze from a multiselect menu. Note: this can be handy when you want to analyze sentences that span more than one citation unit, as frequently or usually happens in Latin poetry. Analyze and visualize the result. Optionally download the analysis results


## Notebooks for working with saved analyses



### `latin_syntaxer_review.py`

Load a file with one or more saved analyses, pick a sentence fromthe menu that appears, and visualize it, as well as the interpretation of the analysis as an Agent-Action-Target (AAT)) graph.


## `latin_syntaxer_graphs.py`

 also no LM access needed -- browse for a previously-saved analysis file the same way `latin_syntaxer_review.py` does, but pick one *or more* sentences from a multiselect (rather than a single sentence from a dropdown), since comparing several sentences' structure side by side is the point here. For each sentence selected, it builds a NetworkX `MultiDiGraph` via `tokengraph_to_networkx()` -- the same nodes, labels, and edges `tokengraph_to_mermaid()` would draw, just as a graph object instead of diagram source (see `graphs.py`) -- and computes `graph_metrics()` on it, then displays a heading (numbered the same way `latin_syntaxer_review.py`'s own menu is), a size/complexity table (token and relation counts, cyclomatic number, longest dependency chain), a shape table (leaf-token count/fraction, mean and max dependents per token), and a relationship-type histogram. Any relation `tokengraph_to_mermaid()` would have skipped (pointing at punctuation or a missing token id) is surfaced as a warning under that sentence's tables rather than silently dropped. Useful for characterizing or comparing sentences' dependency-graph shape -- how tree-like, how deep, how bushy -- without an LM call.