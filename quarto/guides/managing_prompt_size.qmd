# Keeping requests to an LM at a manageable size

When `arsgrammatica` submits a passage to analyze to a configured language model, the prompt it submits includes a lengthy specification of how to analyze Latin syntax in the specific scheme used in this package. The reply from the LM includes a token-by-token analysis that will vary in length depending on the length of the passage submitted. The inevitable result is that each analysis requires a very large context: Latin syntax is complicated. `arsgrammatica` includes a couple of tricks to help manage that.

## Work one sentence at a time, not a whole passage at once

The most basic way this package keeps requests manageable is by breaking passages into individual sentences, then analyzing each sentence separately, one request at a time.

## Make an educated guess about how much room the answer will need

For each analysis request, the package sends a maximum size for the complete context. If the figure is too low, long replies are truncated. If it too is high, and you're routinely paying for (and waiting on) more headroom than any answer actually uses, and you risk exceeding hardcoded limits to the model you're using.

The package includes an optional "calibration" step to estimate how long a give LM's answers tend to be for sentences of a given length. It estimates a figure for maximum context size tht is roughly in proportion to how long the sentence is, plus fixed overhead for the static instructions, plus some extra padding since a sentence's syntactic complexity isn't predictable just from its length; two sentences of the same length can still need noticeably different amounts of explanation. Once you have calibrated a given model, the package can look at a new sentence's length and make an informed guess about how much room to leave for its answer.

To take advantage of this feature, run `python3 calibrate_max_tokens.py`. (This can be slow because it runs through all the examples in the "gold" training set.)

If nobody has ever run that calibration step yet -- say, the first time the package is used against a new model -- `arsgrammatica` falls back to a deliberately generous, cautious estimate that's designed to err on the side of leaving too much room rather than too little, until a real calibration can replace it with something more precisely tuned.

## Check the answer, and ask again if it came back cut short

`arsgrammatica` checks responses from the LM to see if the reply is complete. The most reliable check is simple: does the returned analysis account for every single word of the original sentence? If a word is unaccounted for, the answer was probably cut off partway through. As a second, corroborating check, the package also looks at whether the LM provider itself flagged the response as having been stopped early for running out of room.

When either check suggests the answer was cut short, the package resubmits the same sentence, but with meaningfully more writing room allowed this time, and again checks the new response the same way. It's willing to try this a couple of times, giving the LM progressively more room on each attempt, before it stops.

If, after those extra attempts, the answer still looks incomplete, `arsgrammatica` returns the best answer it has, but flags it clearly with a warning naming exactly what appears to be missing.

## Reusing the instructions instead of resending them every time

`arsgrammatica` also takes advantage of a feature some AI providers offer, sometimes called "prompt caching." This lets the provider remember the lengthy, unchanging block of instructions from one request to the next. Since this is the longest part of a prompt-request exchange, that meaningfully cuts down the real-world cost and time of running multiple sentences through the package.

