---
id: rmsnorm-inter-01
title: RMSNorm normalizes each token across its features — normalize across tokens and you leak
topic: below-the-prompt
level: intermediate
status: ready
time: 6-9h
summary: Every transformer layer normalizes the residual stream before reading it, because a few layers in, one token's activation vector can be ten times the magnitude of another's, and whatever reads them next would be swayed by loudness instead of content — RMSNorm divides each token's feature vector by its own root-mean-square times a learned gain, so every token arrives at unit scale. The entire correctness of it is the axis: RMSNorm is per-token, so token i's output is a function of token i's features alone, and computed that way the three-token fixture goes from RMS 1, 10, 2 to a uniform RMS 1 with each token depending on nothing but itself. Transpose the axis — divide each feature by its RMS across all tokens — and the numbers still look normalized but token 0's output now depends on token 1's value, so editing a later token changes an earlier token's representation, which in a causal model is a leak from the future into the past. The planted bug is the transposed axis, and the self-test catches it by perturbing one token and watching another token's output move.
eli5: Imagine a row of singers where one is blasting ten times louder than the rest, so you can't hear the tune, only the volume. RMSNorm turns each singer down to the same loudness by their own volume, so now you judge them on the notes. The trick is that each singer is adjusted by their own volume only. If instead you adjusted everyone by the average volume of the whole row, then one singer suddenly shouting would quietly change how loud everyone else comes out — and in a story told left to right, a word near the end must never change a word near the beginning. Same-looking numbers, but the wrong one lets the future whisper to the past.
---

## Why this module

A transformer layer never reads the residual stream raw; a normalization sits before every block. It is there because of a problem that grows with depth: the residual stream accumulates the output of every layer, and after a few layers one token's activation vector can be an order of magnitude larger than another's. Feed those unequal-magnitude vectors into the next attention or MLP and the large one dominates the dot products — the layer attends to loudness, not content. RMSNorm removes the magnitude so the next layer sees only direction: it divides each token's feature vector by its own root-mean-square and multiplies by a learned per-feature gain, and every token comes out at the same scale.

The mechanism is three lines of arithmetic, and its entire correctness lives in one choice — the axis. A residual stream is a grid: rows are token positions, columns are features. RMSNorm is a per-row operation: token i is divided by the RMS of token i's own features, so its normalized output is a pure function of itself. Transpose that — divide each feature (column) by the RMS of that feature across all token positions — and the arithmetic still produces normalized-looking numbers, but every token's output now depends on every other token's value in that column. In a causal language model, where position 0 must never see position 1, that is a catastrophe hiding as a plausible refactor: editing a later token silently changes an earlier token's representation, a future-to-past leak that no shape check catches.

This module builds both and measures the difference. The correct per-token norm takes a three-token stream from RMS 1, 10, 2 to a uniform RMS 1, with each token independent of the others; the transposed-axis bug leaves the tokens at unequal RMS and couples them, so perturbing one token moves another's output. Everything runs offline against a residual-stream fixture, stdlib Python 3, `$0.00`, with the RMS values computed. The instinct to unlearn is that normalization is a magnitude fix you can apply along whichever axis is convenient. It must run per token, and the axis is the difference between a working layer and a model that reads its own future.

## Concepts

Named here so you can find them again; each is built below.

- **Residual stream** — the grid of activations a layer reads: rows are tokens, columns are features.
- **Root-mean-square (RMS)** — the magnitude of a vector: the square root of the mean of its squared entries.
- **RMSNorm** — divide each token by its own RMS, times a learned per-feature gain, so every token is unit-scale.
- **The axis** — per-token (per-row) is correct; per-feature (per-column, across tokens) is the bug.
- **The leak** — under the wrong axis, one token's output depends on other tokens, so a later token changes an earlier one.
- **Learned gain** — a per-feature scale applied after normalization; it does not restore per-token magnitude.

## Worked example

Source: the normalization every transformer block applies to its residual stream — RMSNorm as used in modern language models. The three-token, four-feature stream stands in for a slice of a real residual stream a few layers deep, where the magnitude spread that RMSNorm removes has already appeared.

Script and fixture: `modules/below-the-prompt/code/rmsnorm-inter-01/` — `rmsnorm.py`, and `stream.json`, one small residual stream. Every command runs from there.

### The magnitude of a token

RMS is the one primitive both the norm and the bug are built from: the size of a vector, root of the mean of its squares.

```
# rmsnorm.py:40-41 — COMPLETE (RMS: the magnitude of a feature vector)
def rms(vec):
    return math.sqrt(sum(x * x for x in vec) / len(vec) + EPS)
```

The small `EPS` inside the square root is the standard guard against a zero vector dividing by zero — a real detail, not decoration. Everything else is the definition: square, mean, root.

### The correct norm: per token

The correct RMSNorm walks the stream one token at a time, and each token is divided by its own RMS.

```
# rmsnorm.py:46-53 — COMPLETE (per-token: each row divided by its OWN rms, times the gain)
def rmsnorm_per_token(stream, gain):
    """Correct: each token divided by its OWN rms, times the learned per-feature gain."""
    out = []
    for row in stream:
        r = rms(row)
        out.append([(x / r) * g for x, g in zip(row, gain)])
    return out
```

The loop is `for row in stream` — one token per iteration, and `r` is that token's own magnitude. Nothing inside the iteration touches another token. That independence is the property that makes the norm safe in a causal model, and it is exactly what the bug destroys. Run it on the stream:

```
# $ python3 rmsnorm.py --stream
#   token  raw                         rms    per-token-rms(out)  across-rms(out)
#   t0     [1.0, 1.0, 1.0, 1.0]       1.000  1.010              0.171
#   t1     [10.0, 10.0, 10.0, 10.0]   10.000  1.010              1.707
#   t2     [2.0, -2.0, 2.0, -2.0]     2.000  1.010              0.341
```

run: 2026-08-27 · deterministic; the residual stream is a fixture · 3 tokens × 4 features · `python3 rmsnorm.py --stream`

The raw RMS column is the problem: t1 is ten times t0. The per-token-rms column is the fix: all three tokens come out at 1.010 — the same scale, so the next layer compares them on content. (It is 1.010 not exactly 1 because the learned gain scales the result; the normalization itself lands each token at exactly 1, as the self-test confirms with a unit gain.) The across-rms column is the bug's output — 0.171, 1.707, 0.341 — nothing like uniform, with t1 still dominating at ten times t0. The transposed axis did not even do the one job normalization exists for.

<svg viewBox="0 0 700 210" role="img" aria-label="Three tokens' RMS in three states. Raw: t0 at 1, t1 at 10 (very tall), t2 at 2 — a huge spread. Per-token norm: all three at 1, equal. Across-token bug: t0 at 0.17, t1 at 1.71, t2 at 0.34 — still a 10x spread, the hot token dominates. Only per-token norm equalizes the tokens.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">token RMS: raw (spread) → per-token norm (equal) vs across-token bug (still spread)</text>
    <line x1="50" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <text x="110" y="188" text-anchor="middle" fill="var(--muted)" font-size="8">RAW</text>
    <rect x="70" y="158" width="24" height="12" fill="var(--muted)"></rect><text x="82" y="152" text-anchor="middle" fill="var(--muted)" font-size="7">1</text>
    <rect x="100" y="50" width="24" height="120" fill="var(--s2)"></rect><text x="112" y="44" text-anchor="middle" fill="var(--s2)" font-size="7">10</text>
    <rect x="130" y="146" width="24" height="24" fill="var(--muted)"></rect><text x="142" y="140" text-anchor="middle" fill="var(--muted)" font-size="7">2</text>
    <text x="320" y="188" text-anchor="middle" fill="var(--muted)" font-size="8">PER-TOKEN NORM</text>
    <rect x="280" y="146" width="24" height="24" fill="var(--s1)"></rect><rect x="310" y="146" width="24" height="24" fill="var(--s1)"></rect><rect x="340" y="146" width="24" height="24" fill="var(--s1)"></rect><text x="322" y="140" text-anchor="middle" fill="var(--s1)" font-size="7">all 1</text>
    <text x="560" y="188" text-anchor="middle" fill="var(--muted)" font-size="8">ACROSS-TOKEN BUG</text>
    <rect x="520" y="166" width="24" height="4" fill="var(--s2)"></rect><text x="532" y="160" text-anchor="middle" fill="var(--s2)" font-size="7">.17</text>
    <rect x="550" y="129" width="24" height="41" fill="var(--s2)"></rect><text x="562" y="123" text-anchor="middle" fill="var(--s2)" font-size="7">1.71</text>
    <rect x="580" y="162" width="24" height="8" fill="var(--s2)"></rect><text x="592" y="156" text-anchor="middle" fill="var(--s2)" font-size="7">.34</text>
    <text x="50" y="204" fill="var(--muted)" font-size="8">only per-token norm equalizes the tokens; the bug leaves the hot token dominating</text>
  </g>
</svg>
^ Raw, the tokens span 10×; per-token norm flattens them to a common scale; the across-token bug leaves the same 10× spread, having normalized the wrong thing entirely. The bug is not just unsafe — it does not even normalize the tokens.

### The bug: per feature, across tokens

The transposed version divides each feature by the RMS of that feature over all token positions.

```
# rmsnorm.py:57-66 — COMPLETE (the bug: each feature divided by its rms ACROSS tokens)
def rmsnorm_across_tokens(stream, gain):
    """The bug: each feature divided by the rms of that feature ACROSS all tokens -- couples them."""
    n_tok = len(stream)
    n_feat = len(stream[0])
    col_rms = [rms([stream[t][j] for t in range(n_tok)]) for j in range(n_feat)]
    out = []
    for row in stream:
        out.append([(x / col_rms[j]) * gain[j] for j, x in enumerate(row)])
    return out
```

Look at `col_rms`: it is computed once, across every token, and then applied to every row. That single shared vector is the coupling — the divisor for token 0's feature j is a function of token 1's and token 2's feature j.

<svg viewBox="0 0 700 200" role="img" aria-label="The residual stream as a grid, tokens as rows and features as columns. On the left, per-token norm draws a horizontal box around each row: each token normalized by its own row. On the right, the across-token bug draws a vertical box down each column: each feature normalized across all tokens, coupling the rows. The correct axis is along the row, the bug is along the column.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the residual stream grid — which axis do you normalize?</text>
    <text x="40" y="40" fill="var(--s1)">per-token (rows) ✓</text>
    <text x="30" y="70" fill="var(--muted)" font-size="7">t0</text><text x="30" y="98" fill="var(--muted)" font-size="7">t1</text><text x="30" y="126" fill="var(--muted)" font-size="7">t2</text>
    <rect x="48" y="56" width="180" height="24" fill="var(--acc-soft)" stroke="var(--s1)"></rect>
    <rect x="48" y="84" width="180" height="24" fill="var(--acc-soft)" stroke="var(--s1)"></rect>
    <rect x="48" y="112" width="180" height="24" fill="var(--acc-soft)" stroke="var(--s1)"></rect>
    <text x="138" y="152" text-anchor="middle" fill="var(--s1)" font-size="7">each row by its own RMS → self-only</text>
    <text x="420" y="40" fill="var(--s2)">across-token (columns) ✗</text>
    <rect x="430" y="56" width="42" height="80" fill="var(--panel)" stroke="var(--s2)"></rect>
    <rect x="476" y="56" width="42" height="80" fill="var(--panel)" stroke="var(--s2)"></rect>
    <rect x="522" y="56" width="42" height="80" fill="var(--panel)" stroke="var(--s2)"></rect>
    <rect x="568" y="56" width="42" height="80" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="520" y="152" text-anchor="middle" fill="var(--s2)" font-size="7">each column across tokens → couples rows</text>
    <text x="40" y="184" fill="var(--muted)" font-size="8">same grid, transposed axis: rows keep tokens independent, columns tie them together</text>
  </g>
</svg>
^ RMSNorm normalizes along the rows — each token by its own features — keeping tokens independent. The bug normalizes down the columns — each feature across all tokens — which ties every token in a column together. The axis is the entire difference.

It is an easy bug to write: it is what you get from a library's normalization with the default axis. The output looks normalized, it is not per-token, and that is the whole problem.

### The leak: perturb one token, watch another move

The property that distinguishes the two is causal independence, tested by perturbing: add a delta to one token and re-normalize, and a correct norm leaves every other token's output untouched.

```
# rmsnorm.py:70-77 — COMPLETE (perturb one token; did another token's output row change?)
def perturb(stream, token, delta):
    """Return a copy of the stream with `delta` added to every feature of one token."""
    return [[x + (delta if t == token else 0.0) for x in row] for t, row in enumerate(stream)]


def row_changed(a, b, i):
    """Did token i's output row change between two normalizations?"""
    return any(abs(a[i][j] - b[i][j]) > 1e-9 for j in range(len(a[i])))
```

Add 5 to token t1 and ask whether t0's output moved:

```
# $ python3 rmsnorm.py --leak
#   per-token norm: did t0's output change? False
#   across-token bug: did t0's output change? True
```

run: 2026-08-27 · deterministic · `python3 rmsnorm.py --leak`

Under the correct per-token norm, editing t1 leaves t0 exactly where it was — False, no leak. Under the transposed bug, editing t1 changes t0's output — True, a leak. In a causal language model t1 is a later token than t0, so the bug has let a future token reach back and alter a past token's representation — a bug that does not crash and does not shift the loss much at first, while quietly destroying the autoregressive property the architecture depends on.

<svg viewBox="0 0 700 180" role="img" aria-label="The leak test. On the left, per-token norm: an arrow from editing t1 does not reach t0 — t0 unchanged. On the right, across-token bug: editing t1 sends an arrow back to t0 through the shared column RMS — t0 changes. The bug lets a later token alter an earlier token.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">edit token t1 — does t0 (an earlier token) move?</text>
    <text x="40" y="48" fill="var(--s1)">per-token norm</text>
    <rect x="60" y="60" width="60" height="26" fill="var(--panel)" stroke="var(--acc-line)"></rect><text x="90" y="77" text-anchor="middle" fill="var(--acc-ink)" font-size="8">t0</text>
    <rect x="200" y="60" width="60" height="26" fill="var(--s1)"></rect><text x="230" y="77" text-anchor="middle" fill="var(--panel)" font-size="8">t1 +5</text>
    <text x="150" y="105" text-anchor="middle" fill="var(--s1)" font-size="8">t0 unchanged ✓</text>
    <text x="420" y="48" fill="var(--s2)">across-token bug</text>
    <rect x="440" y="60" width="60" height="26" fill="var(--panel)" stroke="var(--s2)"></rect><text x="470" y="77" text-anchor="middle" fill="var(--s2)" font-size="8">t0</text>
    <rect x="580" y="60" width="60" height="26" fill="var(--s2)"></rect><text x="610" y="77" text-anchor="middle" fill="var(--panel)" font-size="8">t1 +5</text>
    <path d="M 580 73 Q 530 30 500 60" fill="none" stroke="var(--s2)"></path><text x="540" y="26" text-anchor="middle" fill="var(--s2)" font-size="7">shared col-RMS</text>
    <text x="530" y="105" text-anchor="middle" fill="var(--s2)" font-size="8">t0 CHANGES ✗ (future → past)</text>
    <text x="40" y="150" fill="var(--muted)" font-size="8">the shared column RMS is the wire that carries the leak from a later token to an earlier one</text>
  </g>
</svg>
^ Editing the later token t1 leaves t0 untouched under per-token norm, but changes it under the across-token bug, where the shared column RMS is the wire between them. In a causal model that wire runs backward in time.

**RMSNorm's correctness is entirely in the axis: it must divide each token by its own RMS, so a token's normalized output depends on nothing but itself — normalize across tokens instead and the numbers still look normalized while a later token's value bleeds into an earlier token's representation, a future-to-past leak that no shape check catches.**

### The self-test

The `--check` mode plants the bug — the transposed axis — and catches it two ways: the correct norm gives unit-RMS tokens while the bug does not, and the correct norm is leak-free while the bug leaks.

```
# $ python3 rmsnorm.py --check
#   every token has unit rms after per-token norm = True ([1.0, 1.0, 1.0])
#   the across-token bug does NOT give unit-rms tokens = True ([0.169, 1.69, 0.338])
#   per-token norm: editing t1 leaves t0 unchanged (no leak) = True
#   across-token bug: editing t1 CHANGES t0 (a leak) = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 rmsnorm.py --check`

The two pairs of lines are the two independent ways the axis matters. The RMS lines check the job: with a unit gain, per-token norm lands every token at exactly 1.0, and the bug leaves them at 0.169, 1.69, 0.338. The leak lines check the safety property: only the buggy axis lets an edit to one token change another. A refactor that passed a shape check and a "looks normalized" eyeball would ship the bug; perturbing a token catches it.

```
# rmsnorm.py:119-128 — COMPLETE (the two RMS assertions: per-token is unit, the bug is not)
    ones = [1.0] * len(gain)
    per_unit = rmsnorm_per_token(stream, ones)
    unit_rms = all(abs(rms(row) - 1.0) < 1e-6 for row in per_unit)
    print("  every token has unit rms after per-token norm = %s (%s)"
          % (unit_rms, [round(rms(r), 3) for r in per_unit]))

    across_unit = rmsnorm_across_tokens(stream, ones)
    across_not_unit = any(abs(rms(row) - 1.0) > 1e-3 for row in across_unit)
    print("  the across-token bug does NOT give unit-rms tokens = %s (%s)"
          % (across_not_unit, [round(rms(r), 3) for r in across_unit]))
```

The `ones` gain isolates the normalization from the learned scale: with it, per-token norm lands every token at exactly 1.0, so any deviation is the axis, not the gain.

### The running tally

| property | per-token norm (correct) | across-token norm (bug) |
|---|---|---|
| t0, t1, t2 output RMS (unit gain) | 1.0, 1.0, 1.0 | 0.169, 1.69, 0.338 |
| tokens equalized to one scale? | yes | no — 10× spread remains |
| token i's output depends on | token i only | all tokens (shared column RMS) |
| edit t1 → does t0 move? | no | yes (future → past leak) |
| safe in a causal model? | yes | no |

Read the last two rows together: the bug fails both the job and the safety property, for the same reason — it normalized down the columns, tying every output cell to a whole column of tokens, where the correct norm ties each cell to one token. One transposed axis turns a component meant to make tokens comparable into one that makes them leak.

### What we did not settle

This is RMSNorm, the simplest of the modern norms; there is more around it. LayerNorm additionally subtracts the per-token mean and adds a learned bias — same per-token axis, one more centering step — and the axis argument here is identical for it. Where the norm sits (pre-norm versus post-norm) changes training stability but not the per-token rule. The learned gain here is applied but not trained; in a real model it is learned and can restore a per-feature scale the network wants. The invariant to carry out: normalization runs per token, and the axis is load-bearing, not incidental.

## Build

The build in one paragraph: normalize the residual stream per token — for each token compute the RMS of its own features, divide the token by that RMS, and multiply by the learned per-feature gain — so every token comes out at unit scale and its output depends on nothing but itself; never normalize across tokens, because a shared per-feature statistic couples the positions and lets a later token change an earlier one. Guard the RMS with a small epsilon, apply the gain after the division, and test the causal property directly by perturbing one token and asserting no other token's output moved.

We opened on the magnitude spread. The number that proves the fix is the token RMS after each norm:

```
# modules/below-the-prompt/code/rmsnorm-inter-01/ — COMPLETE, run from that directory
$ python3 rmsnorm.py --check
  every token has unit rms after per-token norm = True ([1.0, 1.0, 1.0])
  the across-token bug does NOT give unit-rms tokens = True ([0.169, 1.69, 0.338])
```

Now build your own. Take a real residual stream — a few token vectors from any layer, or synthetic ones with a deliberate magnitude spread — and implement RMSNorm both ways. Your number to beat is not the loss; it is **the per-token output RMS and the leak test: per-token norm must give unit RMS and leave other tokens unchanged under a perturbation, while the across-token axis must fail at least one**. Perturb a later token and confirm your correct norm leaves the earlier tokens exactly where they were. Bring back both norms' RMS vectors and both leak results. Good luck.

## Definition of done

- [ ] An RMS function with an epsilon guard
- [ ] A per-token RMSNorm dividing each token by its own RMS, times a learned gain
- [ ] An across-token version dividing each feature by its RMS over all tokens (the bug)
- [ ] Confirmation per-token norm lands every token at unit RMS (with unit gain) and the bug does not
- [ ] A perturbation test: edit one token, check whether another token's output moved
- [ ] Confirmation the per-token norm does not leak and the across-token norm does
- [ ] `python3 rmsnorm.py --check` printing SELF-TEST PASS: unit_rms, across_not_unit, per_no_leak, across_leaks
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a transformer normalize the residual stream before each block — what goes wrong without it?
2. Over which axis does RMSNorm operate, and what property of the output does that axis guarantee?
3. Describe the across-token bug. Why does the output still "look normalized"?
4. The leak test perturbs t1 and watches t0. Why is a change in t0 a disaster in a causal language model?
5. Your own stream was normalized both ways. What were the per-token RMS values, and which axis leaked under perturbation?

## External resources

- Zhang & Sennrich, *Root Mean Square Layer Normalization* — my summary: the paper that dropped LayerNorm's mean-centering and kept only the RMS rescale; read it for why the per-token RMS alone is enough and what the learned gain does.
- Ba, Kiros & Hinton, *Layer Normalization* — my summary: the original per-token normalization RMSNorm simplifies; read it for the mean-subtraction and bias RMSNorm leaves out, on the same axis.
- This hub, *transformer-adv-01* (one transformer layer end to end) and *attention-inter-01* (the causal mask) — read them for where this norm sits in the block and why the future-to-past leak it can introduce is the same property the causal mask protects.
