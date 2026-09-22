# Publishing to TestPyPI / PyPI

arsgrammatica has never been published (`notes/install.md` used to say so explicitly -- every install was a `pip install git+https://...`). This sets up publishing via GitHub Actions using PyPI's "Trusted Publishing" (OIDC): no API tokens stored as GitHub secrets anywhere, ever. `.github/workflows/publish.yml` does the building and uploading; the only thing that has to happen on pypi.org/test.pypi.org itself is telling each index, once, that this specific GitHub repo+workflow is allowed to publish under this project name.

## What was fixed first

`pyproject.toml`'s `version` field was stuck at `"0.5.0"` -- stale by several releases: `releases.md` is already at "Current version: **0.10.0**" with an in-progress, unreleased `0.11.0` entry (this refactoring work), and the repo's own git tags go up to `v0.10.0`. Since PyPI publishes whatever `pyproject.toml`'s `version` says regardless of which tag triggered the build, publishing at `0.5.0` right now would have shipped a version number several releases behind the actual code -- bumped it to **`0.11.0`** to match where `releases.md` and the tags are heading. Going forward, bumping this field is a real step in cutting a release (see "Ongoing release process" below), not just bookkeeping -- worth keeping it in sync each time from now on, unlike whatever caused this drift.

Also modernized the license metadata while touching `pyproject.toml`: the old `license = { file = "LICENSE" }` table plus a `License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)` classifier are both deprecated by setuptools (unsupported entirely after 2027-Feb-18) in favor of an SPDX expression. Replaced with `license = "GPL-3.0-or-later"` plus `license-files = ["LICENSE"]`, dropped the now-redundant classifier, and bumped the `[build-system]` floor from `setuptools>=68` to `setuptools>=77` (the SPDX-string form needs it). Confirmed with a real `python -m build` + `twine check dist/*` -- clean build, `PASSED` on both the sdist and the wheel, no warnings.

## Verified locally before any of this touches GitHub

In a scratch venv (`build`, `twine` installed, deleted afterward): `python -m build` produces `arsgrammatica-0.11.0-py3-none-any.whl` -- a genuine pure-Python universal wheel, confirming the `notes/wasm_export.md` refactor (moving `dspy` to the optional `llm` extra) actually paid off here too, not just for WASM: this wheel installs with only `pydantic`+`networkx` pulled in, nothing native. `twine check dist/*` passed on both the wheel and the sdist. Installed the built wheel into a second clean venv and ran `import arsgrammatica` from *outside* the checkout entirely (proving the package works as an actually-installed dependency, not just via `pythonpath = .`) -- worked, every name importable.

## One-time setup (do this before the first tag push)

### 1. GitHub Environments

In the repo's GitHub settings (Settings -> Environments), create two environments, named exactly:

- `testpypi`
- `pypi`

These names have to match `environment: name:` in `.github/workflows/publish.yml` exactly, and have to match what you register as the "Environment name" on PyPI/TestPyPI's own trusted-publisher form in the next step. For `pypi` specifically, consider adding a required reviewer (Environment protection rules -> Required reviewers) -- since real-PyPI publishes are already gated behind an explicit "publish a GitHub Release" action, this would be a second, belt-and-suspenders human checkpoint before anything actually reaches the real index. Not required for the mechanism to work at all, just an extra safety margin given a real PyPI publish can't be un-published.

### 2. Register a Trusted Publisher on TestPyPI

On <https://test.pypi.org>, logged in, go to your account's **Publishing** page (or, since this project doesn't exist there yet, the "pending publisher" flow: account -> Publishing -> "Add a new pending publisher"). Fill in:

| Field | Value |
|---|---|
| PyPI Project Name | `arsgrammatica` |
| Owner | `neelsmith` |
| Repository name | `arsgrammatica` |
| Workflow name | `publish.yml` |
| Environment name | `testpypi` |

A "pending" publisher is what you register for a project that hasn't been published yet -- the project itself gets created automatically on the first successful publish that matches it.

### 3. Register a Trusted Publisher on PyPI

Same thing on <https://pypi.org> itself, with **Environment name** set to `pypi` instead of `testpypi`. Everything else identical.

## Ongoing release process

Once the two trusted publishers above are registered, cutting a release is:

1. Bump `version` in `pyproject.toml` and add/finalize that version's entry in `releases.md` (replace its `*??*` date placeholder with the actual date), in the same commit.
2. Commit and push that to `main` (or merge `wip` into `main` first, however this repo normally promotes a branch to release -- not something this refactor changes).
3. Tag that commit `vX.Y.Z` (matching `pyproject.toml`'s version exactly -- there's no automatic check tying the two together here, since this repo uses a plain static `version` string rather than something like `setuptools-scm` deriving it from the tag; keeping them in sync is on whoever cuts the release) and push the tag: `git tag v0.11.0 && git push origin v0.11.0`.
4. That tag push alone triggers `publish-to-testpypi` -- watch it in the repo's Actions tab. Once it succeeds, sanity-check the real thing: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ arsgrammatica==0.11.0` in a scratch venv (the `--extra-index-url` matters: TestPyPI doesn't mirror PyPI, so a real dependency like `pydantic` won't otherwise resolve there).
5. Happy with that? Go to the repo's Releases page on GitHub and publish a Release for the `v0.11.0` tag (drafting one from the tag, writing release notes -- `releases.md`'s own entry for that version is a natural source). Publishing that Release is what triggers `publish-to-pypi` -- the real, permanent, un-take-backable one.

Nothing above pushes, tags, or publishes anything on Neel's behalf -- per `CLAUDE.md`, that's his call at each step.
