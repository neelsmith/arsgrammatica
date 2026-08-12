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
    # Analyze Latin syntax with a configured LM
    """)
    return


@app.cell(hide_code=True)
def _(text_area):
    text_area
    return


@app.cell(hide_code=True)
def _(mo, ref):
    mo.md( "> " + ref.reasoning)
    return


@app.cell(hide_code=True)
def _(diagram, mo):
    mo.mermaid(diagram)
    return


@app.cell
def _(toks):
    toks
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
    ## Analysis
    """)
    return


@app.cell
def _(analyze_passage, text_area):
    passage = ''
    if text_area.value:
        passage = text_area.value
        toks, ref = analyze_passage(passage)
    return ref, toks


@app.cell
def _(ref, tokengraph_to_mermaid):
    diagram, mermaid_warnings = tokengraph_to_mermaid(ref.tokengraph)
    return (diagram,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI
    """)
    return


@app.cell
def _(mo):
    text_area = mo.ui.text_area(value = "ac plerique suam ipsi vitam narrare fiduciam potius morum quam adrogantiam arbitrati sunt, nec id Rutilio et Scauro citra fidem aut obtrectationi fuit: adeo virtutes isdem temporibus optime aestimantur, quibus facillime gignuntur. at nunc narraturo mihi vitam defuncti hominis venia opus fuit, quam non petissem incusaturus: tam saeva et infesta virtutibus tempora.", full_width=True, label="*Text to analyze*:").form()
    return (text_area,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Imports
    """)
    return


@app.cell
def _():
    import dspy
    import os
    from pathlib import Path

    return Path, dspy, os


@app.cell
def _():
    from dotenv import load_dotenv

    return (load_dotenv,)


@app.cell
def _(Path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from arsgrammatica import print_analysis, analyze_passage, tokengraph_to_mermaid

    return analyze_passage, tokengraph_to_mermaid


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Configuration of LM
    """)
    return


@app.cell
def _(Path, load_dotenv):
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    return


@app.cell
def _(os):
    api_base = os.getenv("API_BASE")
    model = os.getenv("MODEL")
    api_key = os.getenv("API_KEY")
    return


@app.cell
def _(os):
    def getenv(name: str, fallback_name: str, default: str | None = None) -> str | None:
        value = os.getenv(name)
        if value:
            return value
        value = os.getenv(fallback_name)
        if value:
            return value
        return default

    return (getenv,)


@app.cell
def _(dspy, getenv):
    def configure_lm():
        if dspy.settings.lm is not None:
            return dspy.settings.lm

        api_base = getenv("API_BASE", "API_BASE", "https://suarezai.holycross.edu/litellm")
        model = getenv("MODEL", "MODEL", "litellm_proxy/anthropic/Claude Opus 5")
        api_key = getenv("API_KEY", "API_KEY")

        if not api_key:
            raise RuntimeError(
                "Missing API key. Set API_KEY (preferred) or API_KEY in your .env file."
            )

        lm = dspy.LM(model=model, api_base=api_base, api_key=api_key)
        dspy.configure(lm=lm)
        return lm

    return (configure_lm,)


@app.cell
def _(configure_lm):
    configure_lm()
    return


if __name__ == "__main__":
    app.run()
