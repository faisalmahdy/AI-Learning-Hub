---
id: beamlen-inter-01
title: Normalize beam scores by length — or beam search prefers the shorter sequence because every token adds another negative log-probability
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Beam search ranks hypotheses by the product of their token probabilities — equivalently, the sum of the token log-probabilities. Every probability is at most one, so every log-probability is at most zero, and each additional token can only subtract from the total. A hypothesis's raw score therefore falls monotonically as it grows longer, no matter how good the tokens are, so beam search comparing sequences of different lengths is comparing them on a quantity contaminated by length. The consequence is beam search's notorious length bias: it drifts toward short, terse, generic completions, and in the limit toward the empty sequence, whose score of zero is the largest a sum of negative terms can be. On the fixture here three candidates compete — "ok." (one token, per-token probability 0.45), "sure thing" (two tokens, per-token 0.57), and "i can help with that" (five tokens, per-token 0.70). Raw beam scores them -0.80, -1.11, -1.78 and picks "ok.", the shortest, even though it is the least fluent token for token. Length normalization — dividing the summed log-probability by the sequence length (optionally length to a penalty exponent alpha) — turns the score into a per-token average that no longer shrinks with length: the normalized scores are -0.80, -0.55, -0.36, and beam now picks "i can help with that", the fluent long answer, exactly reversing the ranking. Sweeping alpha from 0 to 1 walks the winner from the shortest candidate to the longest, crossing over near alpha 0.5. The rule: score a beam hypothesis by its length-normalized log-probability, never the raw sum, or the decoder systematically rewards brevity it was never asked to reward.
eli5: Imagine judging essays by counting spelling mistakes, and whoever has the fewest mistakes wins. A student who writes one short sentence has almost no chance to make a mistake, so they win — not because their writing is better, but because they wrote less. A student who writes a full, excellent page makes a few more mistakes just by writing more words, and loses. That is unfair: you rewarded shortness, not quality. The fix is to judge by mistakes per sentence instead of total mistakes, so the long excellent essay is compared fairly against the short one. Beam search has the same bug — it scores a sentence by adding up a small penalty for every word, so long sentences always look worse — and the same fix: divide by the length so you are scoring quality per word, not total.
---

## Why this module

Beam search is the decoder you reach for when you want the most probable sequence, not just a plausible sample. It keeps several hypotheses alive at once and, at the end, returns the one with the best score. That last step hides an assumption that quietly breaks: that the scores of two different hypotheses are comparable.

They are not, if the hypotheses have different lengths. A beam score is a running sum of log-probabilities, one negative term per token. A longer sequence has more terms, all pulling the sum down, so length itself is a handicap in the ranking — before quality enters at all. The decoder ends up preferring the short hypothesis not because it is better but because it is shorter.

This module builds three complete candidates of lengths one, two, and five, scores them the raw way and the normalized way, and watches the ranking flip. The short, generic "ok." wins on raw score; the long, fluent "i can help with that" — more probable at every single token — wins once the score is normalized by length. Then it shows the mechanism, the fix, and how a penalty exponent tunes it.

**Beam search does not have a preference for brevity — it has a scoring bug that looks exactly like one, because it sums a penalty per token and then compares sums across sequences of different token counts.**

## Concepts

A beam hypothesis is scored by the probability of the whole sequence, which factorizes into a product of per-token probabilities. Multiplying many small probabilities underflows, so every implementation works in log space, where the product becomes a sum: the score is the sum of the token log-probabilities.

Here is the whole trouble in one observation. A probability is at most one, so its logarithm is at most zero. Every token therefore contributes a term that is zero or negative to the sum. Adding a token can never raise the score and almost always lowers it. The raw score is a monotonically non-increasing function of length, independent of how good the tokens are.

So when beam search compares a three-token hypothesis against a one-token hypothesis, the three-token one is carrying two extra negative terms purely for existing. If both are equally fluent — same per-token probability — the shorter one wins every time. The comparison is not "which sequence is more probable per token" but "which sequence had fewer tokens to accumulate penalty," and those are different questions with different answers.

The pathological endpoint makes it vivid: the empty sequence has a score of exactly zero, because an empty sum is zero, and zero is the largest value a sum of non-positive terms can reach. A decoder ranking by raw score considers the empty output the single best hypothesis available. Real systems clip this with a minimum length, but the pressure toward brevity is always there, dragging outputs toward curt fragments.

<svg role="img" aria-label="A bar chart of raw beam score for three candidates of length one, two, and five; the bars grow steadily more negative as length increases, from about minus 0.8 to minus 1.8, while a dashed horizontal band marks where the per-token average sits" viewBox="0 0 640 300">
<line x1="60" y1="60" x2="60" y2="250" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="60" x2="600" y2="60" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="52" y="64" fill="var(--muted)" font-size="10" text-anchor="end">0</text>
<text x="30" y="160" fill="var(--muted)" font-size="11" text-anchor="middle" transform="rotate(-90 30 160)">raw score</text>
<rect x="110" y="60" width="90" height="85" fill="var(--s1)" opacity="0.7"/>
<text x="155" y="270" fill="var(--muted)" font-size="11" text-anchor="middle">len 1</text>
<text x="155" y="158" fill="var(--ink)" font-size="10" text-anchor="middle">-0.80</text>
<rect x="270" y="60" width="90" height="118" fill="var(--s1)" opacity="0.7"/>
<text x="315" y="270" fill="var(--muted)" font-size="11" text-anchor="middle">len 2</text>
<text x="315" y="191" fill="var(--ink)" font-size="10" text-anchor="middle">-1.11</text>
<rect x="430" y="60" width="90" height="190" fill="var(--s1)" opacity="0.7"/>
<text x="475" y="270" fill="var(--muted)" font-size="11" text-anchor="middle">len 5</text>
<text x="475" y="263" fill="var(--ink)" font-size="10" text-anchor="middle">-1.78</text>
<text x="475" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">per-token 0.70</text>
<text x="155" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">per-token 0.45</text>
</svg>
^ The raw score sinks with length even as per-token fluency rises from 0.45 to 0.70 — length alone drives the ranking.

**Because every token subtracts from the raw score, beam search ranks sequences partly by length before it ranks them by quality, and length is the confound that has to be removed.**

## Worked example

The fixture is three complete candidates, each given by its per-token probabilities.

```json filename=modules/below-the-prompt/code/beamlen-inter-01/beamlen.json:3-6 COMPLETE
  "candidates": [
    {"label": "ok.", "token_probs": [0.45]},
    {"label": "sure thing", "token_probs": [0.55, 0.60]},
    {"label": "i can help with that", "token_probs": [0.70, 0.70, 0.70, 0.70, 0.70]}
```

The short one is a single low-probability token; the long one is five high-probability tokens. Beam's native score sums their log-probabilities.

```python filename=modules/below-the-prompt/code/beamlen-inter-01/beamlen.py:31-33 COMPLETE
def raw_score(cand):
    """Beam's native score: the sum of token log-probabilities (a product of probabilities)."""
    return sum(math.log(p) for p in cand["token_probs"])
```

Length normalization divides that sum by the length — the score becomes a per-token average rather than a total.

```python filename=modules/below-the-prompt/code/beamlen-inter-01/beamlen.py:36-39 COMPLETE
def normalized_score(cand, alpha=1.0):
    """Length-normalized score: the raw score divided by length**alpha -- a per-token average at alpha=1."""
    length = len(cand["token_probs"])
    return raw_score(cand) / (length ** alpha)
```

To judge fluency independently of length, take the geometric mean probability per token — this is what "more probable token for token" means precisely.

```python filename=modules/below-the-prompt/code/beamlen-inter-01/beamlen.py:42-44 COMPLETE
def per_token_mean(cand):
    """The geometric mean probability per token -- how fluent the sequence is, independent of its length."""
    return math.exp(raw_score(cand) / len(cand["token_probs"]))
```

Scoring all three both ways lays the reversal out in a single table.

```text filename=beamlen.py --score
SCORE — each candidate by raw total versus length-normalized
------------------------------------------------------------------------
  candidate              len         raw   per-token    normalized
  ok.                      1     -0.7985      0.4500       -0.7985  raw-win
  sure thing               2     -1.1087      0.5745       -0.5543  
  i can help with that     5     -1.7834      0.7000       -0.3567  norm-win
------------------------------------------------------------------------
  raw score falls with length; the normalized score is a per-token average that does not
```

Read the two score columns against the per-token column. Raw score marches down the table from -0.80 to -1.78 as length grows, tracking length, not fluency — it crowns "ok." at per-token 0.45. Normalized score marches the other way, from -0.80 to -0.36, tracking the per-token column exactly — it crowns "i can help with that" at per-token 0.70. Same probabilities, opposite winners.

```text filename=beamlen.py --decode
DECODE — what each beam returns
------------------------------------------------------------------------
  raw beam returns        : 'ok.'  (len 1, per-token 0.45)
  normalized beam returns : 'i can help with that'  (len 5, per-token 0.70)
------------------------------------------------------------------------
  raw beam took the terse 'ok.' though the longer answer is more probable token for token
```

The figure shows the two rankings as columns with the candidates crossing between them: what is top under raw score is bottom under normalized score.

<svg role="img" aria-label="Two ranked columns of the three candidates; under raw score the order top to bottom is ok, sure thing, i can help with that, and under normalized score the order is exactly reversed, with crossing lines connecting the same candidate in each column" viewBox="0 0 640 260">
<text x="160" y="40" fill="var(--ink)" font-size="12" text-anchor="middle">raw ranking</text>
<text x="480" y="40" fill="var(--ink)" font-size="12" text-anchor="middle">normalized ranking</text>
<text x="160" y="80" fill="var(--muted)" font-size="11" text-anchor="middle">1. ok.</text>
<text x="160" y="130" fill="var(--muted)" font-size="11" text-anchor="middle">2. sure thing</text>
<text x="160" y="180" fill="var(--muted)" font-size="11" text-anchor="middle">3. i can help with that</text>
<text x="480" y="80" fill="var(--muted)" font-size="11" text-anchor="middle">1. i can help with that</text>
<text x="480" y="130" fill="var(--muted)" font-size="11" text-anchor="middle">2. sure thing</text>
<text x="480" y="180" fill="var(--muted)" font-size="11" text-anchor="middle">3. ok.</text>
<line x1="250" y1="76" x2="390" y2="176" stroke="var(--s2)" stroke-width="1.5"/>
<line x1="250" y1="126" x2="390" y2="126" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="3 3"/>
<line x1="250" y1="176" x2="390" y2="76" stroke="var(--s1)" stroke-width="1.5"/>
<text x="320" y="230" fill="var(--muted)" font-size="10" text-anchor="middle">the best and worst swap places</text>
</svg>
^ Normalizing by length does not nudge the ranking — it inverts it, moving the fluent long answer from last to first.

**The long candidate is more probable at every token yet loses the raw comparison outright; the only thing raw beam rewarded it for having more of was penalty.**

## Build

The self-test pins the reversal to the two structural facts that cause it: raw beam takes the shortest candidate, normalized beam takes the longest, and the longest is the more fluent one — so the bias is punishing fluency for its length.

```python filename=modules/below-the-prompt/code/beamlen-inter-01/beamlen.py:95-105 COMPLETE
    raw_prefers_shortest = raw_win is shortest
    print("  raw beam's winner is the shortest candidate = %s (%r, len %d)" % (raw_prefers_shortest, raw_win["label"], len(raw_win["token_probs"])))

    normalized_prefers_longest = norm_win is longest
    print("  normalized beam's winner is the longest candidate = %s (%r, len %d)" % (normalized_prefers_longest, norm_win["label"], len(norm_win["token_probs"])))

    beams_disagree = raw_win is not norm_win
    print("  the two beams disagree = %s (raw %r vs norm %r)" % (beams_disagree, raw_win["label"], norm_win["label"]))

    longer_is_more_fluent = per_token_mean(longest) > per_token_mean(shortest)
    print("  the longer sequence is more probable per token = %s (%.2f vs %.2f)" % (longer_is_more_fluent, per_token_mean(longest), per_token_mean(shortest)))
```

The final flag confirms the mechanism directly: walking the long candidate's prefixes, each extra token strictly lowers the raw score. Running the check turns all five green.

```text filename=beamlen.py --check
SELF-TEST — raw beam prefers the shortest while normalized beam prefers the longest, and the longer sequence is the more fluent per token
----------------------------------------------------------------------------------------------------------------
  raw beam's winner is the shortest candidate = True ('ok.', len 1)
  normalized beam's winner is the longest candidate = True ('i can help with that', len 5)
  the two beams disagree = True (raw 'ok.' vs norm 'i can help with that')
  the longer sequence is more probable per token = True (0.70 vs 0.45)
  each extra token lowers the raw score = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  raw_prefers_shortest=True  normalized_prefers_longest=True  beams_disagree=True  longer_is_more_fluent=True  raw_score_falls_with_length=True
```

**The bug is not in any probability the model produced — every token probability is exactly what it should be — it is in aggregating them with a sum that a normalization by length would have made comparable.**

## Definition of done

You are done when every beam hypothesis is ranked by a length-normalized score, so that the length of a candidate does not, by itself, move it up or down the ranking.

Plain division by length is the simplest normalization, but production decoders usually expose a penalty exponent `alpha`: the score is the raw sum divided by `length**alpha`, so `alpha = 0` recovers raw beam (full length bias) and `alpha = 1` is the pure per-token average, with intermediate values partially rewarding length. Sweeping it on this fixture walks the winner from the shortest candidate to the longest.

<svg role="img" aria-label="A horizontal axis of the penalty exponent alpha from 0 to 1, with the beam winner marked at several points: alpha 0 and 0.25 pick the short candidate, alpha 0.5 picks the middle candidate at a crossover, and alpha 0.75 and 1.0 pick the long candidate" viewBox="0 0 640 200">
<line x1="60" y1="120" x2="600" y2="120" stroke="var(--line)" stroke-width="1"/>
<text x="330" y="165" fill="var(--muted)" font-size="11" text-anchor="middle">penalty exponent alpha &#8594;</text>
<circle cx="90" cy="120" r="4" fill="var(--s1)"/>
<text x="90" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">0.0</text>
<text x="90" y="145" fill="var(--muted)" font-size="9" text-anchor="middle">ok.</text>
<circle cx="215" cy="120" r="4" fill="var(--s1)"/>
<text x="215" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">0.25</text>
<text x="215" y="145" fill="var(--muted)" font-size="9" text-anchor="middle">ok.</text>
<circle cx="340" cy="120" r="5" fill="var(--ink)"/>
<text x="340" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">0.5</text>
<text x="340" y="145" fill="var(--muted)" font-size="9" text-anchor="middle">sure thing</text>
<circle cx="465" cy="120" r="4" fill="var(--s2)"/>
<text x="465" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">0.75</text>
<text x="465" y="145" fill="var(--muted)" font-size="9" text-anchor="middle">i can help…</text>
<circle cx="565" cy="120" r="4" fill="var(--s2)"/>
<text x="565" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">1.0</text>
<text x="565" y="145" fill="var(--muted)" font-size="9" text-anchor="middle">i can help…</text>
</svg>
^ As the penalty exponent rises the winner crosses from the shortest candidate through the middle one near 0.5 to the longest — alpha is the knob for how much length is rewarded.

**Length normalization is not a special case for "long-output tasks"; any beam comparison of unequal-length hypotheses is biased, so the normalized score is the correct default and raw beam is the special case you almost never want.**

## Boss fight

Your turn: make the short candidate genuinely excellent and see whether normalization still helps. Set `"ok."`'s `token_probs` to `[0.95]` — one near-certain token — and rerun `--score`. Now the short candidate's per-token probability is 0.95, above the long candidate's 0.70, so it is the more fluent sequence, and length normalization correctly keeps it on top. Normalization did not blindly favor length; it removed the length confound, and with the confound gone the genuinely-better short sequence wins.

Then push `alpha` past one — divide by `length**1.5` — and the pendulum swings the other way: now length is over-rewarded, and a rambling low-probability sequence can beat a crisp high-probability one. This is the real tension. `alpha` too low reproduces the brevity bias; `alpha` too high manufactures a verbosity bias. The correct value is task-dependent and tuned on held-out data, which is exactly why decoders expose it as a knob rather than hardcoding division by length. The lesson is not "always divide by length" but "length is a confound in the raw score, and you must decide deliberately how much of it to remove."

**The fix for a brevity bias is not a verbosity bias — normalization is a dial, and the goal is to score sequences on their per-token quality, not to trade one length prejudice for its opposite.**

## External resources

Wu and colleagues' "Google's Neural Machine Translation System" (2016) introduced the length-penalty form `lp(Y) = ((5 + |Y|) / (5 + 1))**alpha` that most production decoders use, and its coverage penalty — read it for the exact formula behind the `alpha` knob.

Murray and Chiang's "Correcting Length Bias in Neural Machine Translation" (2018) analyzes why beam search shortens outputs and evaluates length-normalization strategies against learned length models.

The Hugging Face `generate` documentation exposes this directly as `length_penalty` on beam search; its notes on values above and below one are a practical companion to the boss-fight experiment here.
