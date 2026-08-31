# arsgrammatica

> *See [release history](https://github.com/neelsmith/arsgrammatica/blob/main/releases.md)*.

`arsgrammatica` is a python package leveraging LLMs with [dspy](https://dspy.ai) to analyze the syntax of passages of Latin.

It offers an alternative analytic scheme to [Universal Dependencies](https://universaldependencies.org), designed to describe Latin syntax in familiar terms that are convenient for research and teaching.

Released under the [GNU General Public License v3 or later](LICENSE).


## Installing

To use `arsgrammatica` from another project, install it from this repository:

```sh
pip install git+https://github.com/neelsmith/arsgrammatica.git
```

That installs whatever's currently on the `main` branch. Pin to a specific branch or tag by appending `@<ref>`, e.g. `pip install git+https://github.com/neelsmith/arsgrammatica.git@wip` for the development branch, or `@v0.2.0` for a tagged version. `arsgrammatica` itself is installed, and brigns `dspy` and `pydantic` as declared dependencies; the marimo notebooks, tests, and other repo scripts are not part of the installed package and are not needed to use it.

## Using `arsgrammatica`

- [USAGE.md](https://github.com/neelsmith/arsgrammatica/blob/main/USAGE.md)
- [API documentation](https://neelsmith.github.io/arsgrammatica/arsgrammatica-api-docs.html)
- [TESTING.md](https://github.com/neelsmith/arsgrammatica/blob/main/TESTING.md)
- [OPTIMIZING.md](https://github.com/neelsmith/arsgrammatica/blob/main/OPTIMIZING.md)
- [BAKEOFF.md](https://github.com/neelsmith/arsgrammatica/blob/main/BAKEOFF.md)
- [DEVELOPMENT.md](https://github.com/neelsmith/arsgrammatica/blob/main/DEVELOPMENT.md) -- how the above fit together into one development loop
- Some additional [technical info](https://github.com/neelsmith/arsgrammatica/blob/main/technical.md)



See the [project issue tracker](https://github.com/neelsmith/arsgrammatica/issues) for known gaps and work in progress.


## Related work

Parallel python packages for syntactic analysis:

- [grammatike](https://github.com/neelsmith/grammatike) for Ancient Greek
- [diqduq](https://github.com/neelsmith/diqduq) for Biblical Hebrew

A reduced model of natural-language syntax:

- [aat](https://github.com/neelsmith/aat), a Python package implementing an Agent-Action-Target model
