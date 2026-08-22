# Release history

Current version: **0.3.0**.



**0.3.0**, *Aug. 22, 2026*: Now packaged project for direct import from github repository.

Fixes: better handling of `numeral` tokens.

Additions: `syntaxer_ctsdata` notebook allows selection of multiple citable passages. 


**0.2.0**,  *Aug. 21, 2026*:

Breaking changes: syntactically absolute substantives are now assigned to the verbal unit of the circumstantial participle they agree with, not the verbal unit of the governing clause.

Additions: 

- relations of praenomina now included in syntax graph
- special uses of accusative and ablative expanded; syntax of vocative case added
- tests for all new relations; suite for `pytest` now includes 630 tests
- optional depth parameter in HTML block display + new function to find maximum depth of subordination of a passage, and updated marimo notebooks
- new marimo notebook to visualize saved analyses (no LLM required), with option to export Mermaid graph of syntax
- new utilities for managing maximum token numbers along with options to see tokens, prompts and costs of queries in. marimo notebooks


**0.1.0**, *Aug. 17, 2026*: Initial public release, built using Opus 5. Includes a complete framework for developing, testing and optimizing Latin syntactic analyzers with a wide variety of language models using `dspy`. This release includes:

    - a python package with a complete implementation of the initial syntactic scheme
    - more than 500 tests verifying the structure of the code and its data structures
    - configuration for any LM via litelm API using environmental variables or settings in `.env` file
    - command-line scripts and marimo notebooks for interactive analysis of citable passages of Latin 
    - utilities for visualizing syntactic analyses as Mermaid graphs, and as HTML display with a variety of syntactic highlighting.
    - serialization and loading of syntactic analyses to/from plain-text files
    - utilities supporting automated loading of validated analyses into training set or evaluation data set
    - optimization pipeline against a given model using GEPA
    - "bakeoff" utility script to automate comparative testing of open models from Hugging Face or running locally on ollama