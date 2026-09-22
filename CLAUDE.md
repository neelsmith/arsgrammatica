# arsgrammatica — read this first

Full working conventions for this repo (write restrictions, operating modes, verification steps, and a session log) live in files in the **[`notes/`](notes/)** directory. 

Summary of organization:

- `README.md`, `releases.md`, and `quarto/` are Neel's — read-only for Claude.
- `notes/` is where Claude's own notes and documentation go.
- `docs/` is generated output (via `quarto render` and `utilities/build_api_docs.py`) for GitHub Pages — not hand-edited.
- Never `git commit` or push on Neel's behalf.
