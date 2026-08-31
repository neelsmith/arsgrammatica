# Keeping requests to an LM at a manageable size

When `arsgrammatica` submits a passage to analyze to a configured language model, the prompt it submits includes a lengthy specification of how to analyze Latin syntax in the specific scheme used in this package. The reply from the LM includes a token-by-token analysis that will vary in length depending on the length of the passage submitted. The inevitable result is that each analysis requires a very large context: Latin syntax is complicated. `arsgrammatica` includes a couple of tricks to help manage that.

## Work one sentence at a time, not a whole passage at once

The most basic way this package keeps any single request manageable is by not asking the AI to do too much in one request. Rather than submitting an entire paragraph to analyze, the package first breaks the passage into individual sentences, and then analyzes each sentence separately, one request at a time.

## Make an educated guess about how much room the answer will need

For each sentence, the package has to tell the AI up front, "you're allowed to write up to this much before I'll cut you off." Get that number too low, and a genuinely long or complicated sentence gets truncated. Get it too high, all the time, and you're routinely paying for -- and waiting on -- more headroom than any answer actually uses, and risk exceeding hardcoded limits to the model you're using.

The package includes an optional "calibration" step: feed it a batch of real sentences of known length, see how long the AI's answers to each one actually turned out to be, and fit a simple relationship between the two -- something like "a longer input sentence tends to need a longer answer, roughly in proportion to how long it is, plus a bit of a fixed overhead no matter what." Once that relationship is worked out for whatever AI model is currently in use, the package can look at a brand-new sentence's length and make a well-informed guess about how much writing room to leave for its answer, before ever sending the request.

That guess also gets padded with a safety cushion, since a sentence's true complexity isn't perfectly predictable just from counting its words -- two sentences of the same length can still need noticeably different amounts of explanation. And the final number is kept within sensible bounds: never so small that even a short, simple sentence would be shortchanged, and never larger than the AI is actually willing to produce in one response no matter what you ask for.

If nobody has ever run that calibration step yet -- say, the very first time the package is used against a brand-new AI model -- `arsgrammatica` falls back to a deliberately generous, cautious estimate instead, one that's designed to err on the side of leaving too much room rather than too little, until a real calibration can replace it with something more precisely tuned.

## Check the answer, and ask again if it came back cut short

Even a well-informed guess can turn out to be wrong for one particular sentence. So after the LM responds, the package doesn't just trust that everything came back complete -- it actually checks. The most reliable check is simple: does the returned analysis account for every single word of the original sentence? If a word is unaccounted for, that's a clear sign the answer was cut off partway through, regardless of what the LM provider's own systems say about it. As a second, corroborating check, the package also looks at whether the LM provider itself flagged the response as having been stopped early for running out of room.

When either check suggests the answer was cut short, the package resubmits the same sentence, but with meaningfully more writing room allowed this time, and again checks the new response the same way. It's willing to try this a couple of times, giving the AI progressively more room on each attempt, before it stops.

If, after those extra attempts, the answer still looks incomplete, `arsgrammatica` returns the best answer it has, but flags it clearly with a warning naming exactly what appears to be missing.

## Reusing the instructions instead of resending them every time

This last one isn't really about making any single request *smaller* -- it's about making a large, unavoidable part of every request cheaper to repeat.

Every request the package sends includes a substantial, detailed set of instructions describing exactly how to analyze Latin syntax under this package's own grammatical scheme. Those instructions are long, but they're also exactly the same, word for word, on every single request; only the addition at the end of the actual sentence to analyze changes.

Recognizing that, the package takes advantage of a feature some AI providers offer, sometimes called "prompt caching," which lets the provider remember that unchanging block of instructions from one request to the next, rather than having to read through it in full (and charge for it in full) every single time. This doesn't shrink any individual sentence's own analysis, but it meaningfully cuts down the real-world cost and time of running many sentences through the package one after another.

