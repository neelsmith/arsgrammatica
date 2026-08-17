# Release history

Current version: **0.1.0**.



- **0.1.0**, *Aug. 17, 2026*: Initial public release, built using Opus 5. Includes a complete framework for developing, testing and optimizing Latin syntactic analyzers with a wide variety of language models using `dspy`. This release includes:

    - a python package with a complete implementation of the initial syntactic scheme
    - more than 500 tests verifying the structure of the code and its data structures
    - configuration for any LM via litelm API using environmental variables or settings in `.env` file
    - command-line scripts and marimo notebooks for interactive analysis of citable passages of Latin 
    - utilities for visualizing syntactic analyses as Mermaid graphs, and as HTML display with a variety of syntactic highlighting.
    - serialization and loading of syntactic analyses to/from plain-text files
    - utilities supporting automated loading of validated analyses into training set or evaluation data set
    - optimization pipeline against a given model using GEPA
    - "bakeoff" utility script to automate comparative testing of open models from Hugging Face or running locally on ollama