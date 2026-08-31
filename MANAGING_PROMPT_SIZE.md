# How this package keeps its requests to the AI a manageable size



## What's a "prompt," and why does its size matter?

Every time this package analyzes a piece of Latin, it's really having a conversation with an AI language model: it sends the model a request -- instructions plus the passage to analyze -- and the model sends back an answer. That request is usually called a "prompt," and the answer is usually called a "completion" or a "response."

Both the prompt and the response have a size, measured not in words exactly, but in small chunks of text called *tokens* -- roughly a word or a piece of a word each. Size matters for a few practical reasons:

- **Cost.** AI providers charge by the token, for both what you send and what you get back. A bigger prompt, or a longer answer, costs more.
- **Speed.** A longer response takes longer to generate.
- **A hard ceiling.** Every model has a maximum response length it's allowed to produce in one go. If you ask for something that would need a longer answer than that, the response gets cut off partway through -- like a book missing its last few pages. An analysis that gets cut off mid-sentence isn't just incomplete, it can be actively wrong, because pieces the rest of the answer depended on are simply missing.

So the package has to walk a careful line: leave enough room for the AI to finish its answer, without wastefully asking for far more room than it will ever use. This document explains, without any code, the handful of tricks it uses to strike that balance.

## Trick one: work one sentence at a time, not a whole passage at once

The most basic way this package keeps any single request manageable is by not asking the AI to do too much in one breath. Rather than handing over an entire paragraph or chapter and asking for a complete grammatical analysis of the whole thing in one shot, the package first breaks the passage into individual sentences, and then analyzes each sentence separately, one request at a time.

This is a bit like asking someone to summarize a book one chapter at a time rather than demanding one giant summary of the whole thing in a single breath. Each individual request stays small and predictable, the AI has an easier time paying close attention to just one sentence's worth of grammar, and if something does go wrong, it's contained to that one sentence rather than derailing an entire passage.

## Trick two: make an educated guess about how much room the answer will need

For each sentence, the package has to tell the AI up front, "you're allowed to write up to this much before I'll cut you off." Get that number too low, and a genuinely long or complicated sentence gets truncated. Get it too high, all the time, and you're routinely paying for -- and waiting on -- far more headroom than any answer actually uses.

Rather than picking one fixed number and hoping for the best, the package tries to learn a sensible rule of thumb from experience. It has an optional "calibration" step: feed it a batch of real sentences of known length, see how long the AI's answers to each one actually turned out to be, and fit a simple relationship between the two -- something like "a longer input sentence tends to need a longer answer, roughly in proportion to how long it is, plus a bit of a fixed overhead no matter what." Once that relationship is worked out for whatever AI model is currently in use, the package can look at a brand-new sentence's length and make a well-informed guess about how much writing room to leave for its answer, before ever sending the request.

That guess also gets padded with a safety cushion, since a sentence's true complexity isn't perfectly predictable just from counting its words -- two sentences of the same length can still need noticeably different amounts of explanation. And the final number is kept within sensible bounds: never so small that even a short, simple sentence would be shortchanged, and never larger than the AI is actually willing to produce in one response no matter what you ask for.

If nobody has ever run that calibration step yet -- say, the very first time the package is used against a brand-new AI model -- it doesn't just guess blindly. It falls back to a deliberately generous, cautious estimate instead, one that's designed to err on the side of leaving too much room rather than too little, until a real calibration can replace it with something more precisely tuned.

## Trick three: check the answer, and ask again if it came back cut short

Even a well-informed guess can turn out to be wrong for one particular sentence. So after the AI responds, the package doesn't just trust that everything came back complete -- it actually checks. The most reliable check is simple: does the returned analysis account for every single word of the original sentence? If a word is unaccounted for, that's a clear sign the answer was cut off partway through, regardless of what the AI provider's own systems say about it. As a second, corroborating check, the package also looks at whether the AI provider itself flagged the response as having been stopped early for running out of room.

When either check suggests the answer was cut short, the package doesn't just give up or quietly hand back a broken result. It asks again -- the same sentence, but with meaningfully more writing room allowed this time -- and checks the new answer the same way. It's willing to try this a couple of times, giving the AI progressively more room on each attempt, before it stops.

If, after those extra attempts, the answer still looks incomplete, the package doesn't pretend everything is fine. It hands back the best answer it has, but flags it clearly with a warning naming exactly what appears to be missing -- so whoever is using the result knows to take a closer look, rather than unknowingly relying on an analysis with silent gaps in it.

## A related trick: reusing the instructions instead of resending them every time

This last one isn't really about making any single request *smaller* -- it's about making a large, unavoidable part of every request cheaper to repeat.

Every request the package sends includes a substantial, detailed set of instructions describing exactly how to analyze Latin syntax under this package's own grammatical scheme -- what counts as a subject, how to handle an implied verb, and so on. Those instructions are long, but they're also exactly the same, word for word, on every single request; only the short bit at the end -- the actual sentence being analyzed -- changes each time.

Recognizing that, the package takes advantage of a feature some AI providers offer, sometimes called "prompt caching," which lets the provider remember that unchanging block of instructions from one request to the next, rather than having to read through it in full -- and charge for it in full -- every single time. It's a bit like a tutor who's already memorized a long reference sheet: you don't need to hand them the whole sheet again for every single question, just the new question itself. This doesn't shrink any individual sentence's own analysis, but it meaningfully cuts down the real-world cost and time of running many sentences through the package one after another, since that big, repeated block of instructions stops being paid for and waited on again and again.

## The overall philosophy

Across all of these tricks, the same basic approach shows up repeatedly: keep each individual request modest and focused rather than sprawling, start from an informed estimate rather than either a blind guess or a wastefully oversized default, verify the result rather than simply trusting it, correct course when the estimate turns out to be wrong, and -- when even that isn't enough -- say so plainly rather than quietly handing back something incomplete.
