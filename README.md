# arsgrammatica

> *See [release history](https://github.com/neelsmith/arsgrammatica/blob/main/releases.md)*.

`arsgrammatica` is a python package leveraging LLMs with [dspy](https://dspy.ai) to analyze the syntax of passages of Latin.

It offers an alternative analytic scheme to [Universal Dependencies](https://universaldependencies.org), designed to describe Latin syntax in familiar terms that are convenient for research and teaching.

Released under the [GNU General Public License v3 or later](LICENSE).


## Installing

To use `arsgrammatica` from another project, install it straight from this repository (no PyPI account or release process needed):

```sh
pip install git+https://github.com/neelsmith/arsgrammatica.git
```

That installs whatever's currently on the `main` branch. Pin to a specific branch, tag, or commit by appending `@<ref>`, e.g. `pip install git+https://github.com/neelsmith/arsgrammatica.git@wip` for the development branch, or `@v0.2.0` once a version is tagged. Either way, only `arsgrammatica/` itself is installed as a package -- `dspy` and `pydantic` come along automatically as declared dependencies; the marimo notebooks, tests, and other repo scripts are not part of the installed package and aren't needed to use it.

Working on `arsgrammatica` itself (this repo checked out locally) rather than depending on it from elsewhere: `pip install -e .` from the repo root installs it in editable mode, so source edits take effect immediately without reinstalling.


## Using `arsgrammatica`



- [USAGE.md](https://github.com/neelsmith/arsgrammatica/blob/main/USAGE.md)
- [API documentation](https://neelsmith.github.io/arsgrammatica/arsgrammatica-api-docs.html)
- [TESTING.md](https://github.com/neelsmith/arsgrammatica/blob/main/TESTING.md)
- [OPTIMIZING.md](https://github.com/neelsmith/arsgrammatica/blob/main/OPTIMIZING.md)
- [BAKEOFF.md](https://github.com/neelsmith/arsgrammatica/blob/main/BAKEOFF.md)
- [DEVELOPMENT.md](https://github.com/neelsmith/arsgrammatica/blob/main/DEVELOPMENT.md) -- how the above fit together into one development loop
- Some additional [technical info](https://github.com/neelsmith/arsgrammatica/blob/main/technical.md)



See the [project issue tracker](https://github.com/neelsmith/arsgrammatica/issues) for known gaps and work in progress.


