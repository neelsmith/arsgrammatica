# Installing Graphviz's `dot` binary

Only needed to render `dot.py`'s DOT text into a picture (or to use `marimo/latin_syntaxer_dot.py`'s inline preview) -- generating the text itself needs nothing. See `notes/dot_diagrams.md`.

## macOS

```sh
brew install graphviz
```

## Windows

```powershell
winget install --id Graphviz.Graphviz
```

No `winget`? Install from https://graphviz.org/download/ instead, and make sure to check "Add Graphviz to the system PATH" during setup (or add the installed `bin` folder to PATH by hand afterward).

## Verify

```sh
dot -V
```

Prints a version string if it worked. If you get "command not found" (macOS) or "'dot' is not recognized" (Windows) right after installing, open a new terminal -- PATH changes don't reach ones already open.
