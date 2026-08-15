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
def _(mo, results):
    mo.md("**Discussion**:\n\n" + "\n\n".join(f"> {result.reasoning}" for result in results))
    return


@app.cell(hide_code=True)
def _(psghtml):
    psghtml
    return


@app.cell(hide_code=True)
def _(vuhtml):
    vuhtml
    return


@app.cell
def _(indentpsg):
    indentpsg
    return


@app.cell(hide_code=True)
def _(diagram, mo):
    mo.mermaid(diagram)
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
    # Analyze text passage:
    passage = ''
    sentences, results = [], []
    if text_area.value:
        passage = text_area.value
        sentences, results = analyze_passage(passage)
    return results, sentences


@app.cell
def _(combined_tokengraph, results, tokengraph_to_mermaid):
    # Compose Mermaid diagram:
    finaltokens = combined_tokengraph(results)
    diagram, mermaid_warnings = tokengraph_to_mermaid(finaltokens)
    return diagram, finaltokens


@app.cell
def _(sentences):
    tokens = [tok for sentence in sentences for tok in sentence.tokens]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Format output display
    """)
    return


@app.cell
def _(finaltokens, mo, tokengraph_to_text):
    psghtml = mo.Html("<b><i>Passage</i></b>: " + tokengraph_to_text(finaltokens))
    return (psghtml,)


@app.cell
def _(finaltokens, mo, tokengraph_to_html):
    vuhtml = mo.Html("<b><i>Highlighted by verbal unit</i></b>: " + tokengraph_to_html(finaltokens))
    return (vuhtml,)


@app.cell
def _(finaltokens, mo, tokengraph_to_depth_html):
    indenthtml, indentwarnings = tokengraph_to_depth_html(finaltokens)
    indentpsg = mo.Html("<b><i>Indented by verbal unit</i></b>: " + indenthtml)

    return (indentpsg,)


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
 
    from arsgrammatica import print_analysis, analyze_passage, tokengraph_to_mermaid, combined_tokengraph, tokengraph_to_html, tokengraph_to_text, tokengraph_to_depth_html

    return (
        analyze_passage,
        combined_tokengraph,
        tokengraph_to_depth_html,
        tokengraph_to_html,
        tokengraph_to_mermaid,
        tokengraph_to_text,
    )


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
