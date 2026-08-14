# arsgrammatica


The story started [here](https://neelsmith.github.io/GreekAndLatinSyntax/) in 2023. Here's [a Julia package](https://neelsmith.github.io/GreekSyntax.jl/stable/annotations/) that implemented this model.


## Testing

- `pytest` to run all.
- `pytest -v` for per-test names instead of dots. 
- `pytest tests/test_gold_examples.py` to run just one file. 
- `pytest -k agent` to run only tests matching a substring (handy once you've got fixtures named like agent_passive_roma_condita). 
- `pytest --collect-only` if you just want to see what it discovered without running anything.