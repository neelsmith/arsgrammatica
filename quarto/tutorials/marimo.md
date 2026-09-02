---
title: Marimo notebooks for Latin syntactic analysis
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

For review and visualization of an analysis. Load a file with one or more saved analyses, pick a sentence from the menu that appears, and visualize it, as well as the interpretation of the analysis as an Agent-Action-Target (AAT)) graph.



### `latin_syntaxer_compose_diagram.py`

Compose diagrams in the `dot` format used by the open-source `graphviz` software. Load a file with one or more saved analyses, pick a sentence from the menu that appears, and set diagramming opens. If you have installed `graphviz` on your system, displays within the notebook with option to save the `dot` file.






### `latin_syntaxer_graphs.py`

For graph analysis. Similar to `latin_syntaxer_review.py`, but pick one *or more* sentences from a multiselect (rather than a single sentence from a dropdown). The dependency graph for each sentence is instantiated as a NetworkX `MultiDiGraph` and basic graph metrics are computed to compare the syntactic form and complexity of the chosen sentences.
