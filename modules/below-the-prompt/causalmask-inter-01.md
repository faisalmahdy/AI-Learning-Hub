---
id: causalmask-inter-01
title: Mask the future before the softmax — without a causal mask, a next-token model attends to the answer and cheats
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A decoder predicts token i+1 from tokens 0..i using self-attention: position i builds its output as a weighted average of the value vectors at the positions it attends to, with weights from a softmax over attention scores. Nothing in that machinery by itself stops position i from attending to positions i+1 and beyond — the future tokens. During teacher-forced training the full sequence is present, so a position that can attend to the future can read the very token it is meant to predict; training loss collapses toward zero not because the model learned language but because it learned to copy the answer from a position it will not have at inference. The causal mask fixes this at exactly one place: for each query position i, every future key j>i has its score set to negative infinity before the softmax, so exp(-inf)=0 gives those positions zero weight and position i's output averages only positions 0..i. On a fixture with equal scores (to isolate the mask) and stand-in token values 10, 20, 30, 40, the unmasked attention makes every position output 25 — the average of all four tokens, so position 0 already depends on the future 20, 30, 40 — while the masked attention outputs 10, 15, 20, 25, each depending only on the past and present.
eli5: Imagine a fill-in-the-blank test where you're supposed to guess each next word from the words before it. If you're allowed to peek ahead at the answer, you'll ace the practice test by copying — but you learned nothing, and in the real test the future words aren't written down yet, so you fail. A causal mask is a blindfold that covers every word after the one you're on, so the model is forced to actually predict from the past instead of peeking. During practice (training) the whole sentence is visible, which is exactly when peeking is possible and most tempting, so the blindfold has to be on then too.
---

## Why this module

A decoder is trained on whole sentences it will later have to produce one word at a time, and the gap between those two situations is where a silent, fatal bug lives. If the model is allowed to look at the words after the one it is predicting, training goes beautifully and generation is nonsense — because the thing it leaned on during training does not exist during generation.

A decoder predicts token i+1 from tokens 0..i. It does this with self-attention: position i builds its output as a weighted average of the value vectors at the positions it attends to, where the weights come from a softmax over attention scores. Nothing in that machinery, by itself, stops position i from attending to positions i+1 and beyond — the future tokens. During training that is a disaster hiding as a triumph: the model is trained on complete sequences (teacher forcing), so the future tokens are present, and a position that can attend to them can read the very token it is supposed to predict. Training loss collapses toward zero, not because the model learned language, but because it learned to copy the answer from a position it will not have at inference.

The causal mask is the fix, applied at exactly one place: the attention scores, before the softmax. For each query position i, every future key position j>i has its score set to negative infinity. Because exp(−inf) is 0, after the softmax those future positions carry zero weight, and position i's output is a weighted average of only positions 0..i. The mask is a property of the architecture, not the data: it must be present at training (or the model learns to cheat) and matches inference (where the future simply is not there). Getting it wrong — an off-by-one that lets position i see i+1, a mask applied after the softmax, or no mask at all — produces a model that scores beautifully in training and generates nonsense. This module attends over a 4-token sequence with and without the mask and shows the leak.

**A decoder's self-attention must forbid position i from attending to future positions, done by setting their scores to −inf before the softmax; without the mask, position i attends to the tokens it is meant to predict, so teacher-forced training collapses by cheating and the model cannot generate autoregressively.**

## Concepts

**Attention weights** come from a softmax over scores, per query position. The causal mask sets future scores to −inf before that softmax, so the mask is applied to scores, never to the weights afterward.

```python filename=modules/below-the-prompt/code/causalmask-inter-01/causalmask.py:55-62 COMPLETE
def attention_weights(scores, causal):
    """Per-position softmax attention weights; if causal, mask future positions (j>i) to -inf BEFORE the softmax."""
    n = len(scores)
    rows = []
    for i in range(n):
        masked = [scores[i][j] if (not causal or j <= i) else float("-inf") for j in range(n)]
        rows.append(softmax(masked))
    return rows
```

**The softmax** is why −inf is the right mask value: exp(−inf) is 0, so a masked position contributes zero weight and the remaining weights still sum to 1. Masking after the softmax (zeroing weights) would break that sum; masking the scores keeps it a valid distribution.

```python filename=modules/below-the-prompt/code/causalmask-inter-01/causalmask.py:47-52 COMPLETE
def softmax(xs):
    """Softmax over a list; a score of -inf contributes exp(-inf)=0, i.e. zero weight."""
    m = max(v for v in xs if v != float("-inf"))
    e = [math.exp(v - m) if v != float("-inf") else 0.0 for v in xs]
    s = sum(e)
    return [v / s for v in e]
```

<svg role="img" aria-label="A 4 by 4 attention grid where the lower triangle and diagonal are allowed (a query attends to itself and the past) and the upper triangle is masked out as future positions" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">causal mask: query i (row) may attend to key j (col) only if j ≤ i</text>
  <text x="10" y="80" fill="var(--muted)" font-size="7" transform="rotate(-90 10 80)">query i →</text>
  <text x="150" y="126" fill="var(--muted)" font-size="7">key j →</text>
  <g transform="translate(30,20)">
  <rect x="0" y="0" width="24" height="24" fill="var(--s1)"/><rect x="26" y="0" width="24" height="24" fill="var(--muted)"/><rect x="52" y="0" width="24" height="24" fill="var(--muted)"/><rect x="78" y="0" width="24" height="24" fill="var(--muted)"/>
  <rect x="0" y="26" width="24" height="24" fill="var(--s1)"/><rect x="26" y="26" width="24" height="24" fill="var(--s1)"/><rect x="52" y="26" width="24" height="24" fill="var(--muted)"/><rect x="78" y="26" width="24" height="24" fill="var(--muted)"/>
  <rect x="0" y="52" width="24" height="24" fill="var(--s1)"/><rect x="26" y="52" width="24" height="24" fill="var(--s1)"/><rect x="52" y="52" width="24" height="24" fill="var(--s1)"/><rect x="78" y="52" width="24" height="24" fill="var(--muted)"/>
  <rect x="0" y="78" width="24" height="24" fill="var(--s1)"/><rect x="26" y="78" width="24" height="24" fill="var(--s1)"/><rect x="52" y="78" width="24" height="24" fill="var(--s1)"/><rect x="78" y="78" width="24" height="24" fill="var(--s1)"/>
  </g>
  <text x="140" y="40" fill="var(--s1)" font-size="7">■ allowed (0..i)</text>
  <text x="140" y="56" fill="var(--muted)" font-size="7">■ masked (future, −inf)</text>
</svg>
^ Each row is a query position, each column a key; the diagonal and lower triangle are allowed (a position attends to itself and the past), and the upper triangle — every future key — is set to −inf, so the attention matrix is lower-triangular.

**The mask is applied to the scores before the softmax, setting future positions to −inf so they get exactly zero weight while the row stays a valid distribution — masking the weights after the softmax would instead leave an invalid, unnormalized row.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/causalmask-inter-01/causalmask.py

The fixture uses equal attention scores — so nothing but the mask distinguishes positions — and stand-in token value vectors.

```json filename=modules/below-the-prompt/code/causalmask-inter-01/causalmask.json:3-9 COMPLETE
  "values": [10, 20, 30, 40],
  "scores": [
    [0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0]
  ]
```

Run `--weights` to see the attention matrix both ways.

```text filename=--weights
WEIGHTS — attention weight matrix, unmasked vs causal-masked
------------------------------------------------------------
  UNMASKED (attends everywhere):
    pos 0: [0.25, 0.25, 0.25, 0.25]
    pos 1: [0.25, 0.25, 0.25, 0.25]
    pos 2: [0.25, 0.25, 0.25, 0.25]
    pos 3: [0.25, 0.25, 0.25, 0.25]
  MASKED (attends only 0..i):
    pos 0: [1.0, 0.0, 0.0, 0.0]
    pos 1: [0.5, 0.5, 0.0, 0.0]
    pos 2: [0.333, 0.333, 0.333, 0.0]
    pos 3: [0.25, 0.25, 0.25, 0.25]
```

Unmasked, every row is uniform 0.25 — each position attends equally to all four tokens, including the ones after it. Masked, the matrix is lower-triangular: position 0 attends only to itself (weight 1.0), position 1 splits over positions 0 and 1, position 2 over 0–2, and only the last position, which has no future, is unchanged.

<svg role="img" aria-label="Two 4 by 4 weight matrices: unmasked with every cell shaded uniformly, and masked with only the lower triangle shaded and the upper triangle blank" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">weights: uniform everywhere (unmasked) vs lower-triangular (masked)</text>
  <text x="30" y="28" fill="var(--muted)" font-size="7">unmasked</text>
  <g transform="translate(20,32)">
  <rect x="0" y="0" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="20" y="0" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="40" y="0" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="60" y="0" width="18" height="18" fill="var(--s1)" opacity="0.5"/>
  <rect x="0" y="20" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="20" y="20" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="40" y="20" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="60" y="20" width="18" height="18" fill="var(--s1)" opacity="0.5"/>
  <rect x="0" y="40" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="20" y="40" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="40" y="40" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="60" y="40" width="18" height="18" fill="var(--s1)" opacity="0.5"/>
  <rect x="0" y="60" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="20" y="60" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="40" y="60" width="18" height="18" fill="var(--s1)" opacity="0.5"/><rect x="60" y="60" width="18" height="18" fill="var(--s1)" opacity="0.5"/>
  </g>
  <text x="190" y="28" fill="var(--muted)" font-size="7">masked</text>
  <g transform="translate(180,32)">
  <rect x="0" y="0" width="18" height="18" fill="var(--s1)"/><rect x="20" y="0" width="18" height="18" fill="none" stroke="var(--line)"/><rect x="40" y="0" width="18" height="18" fill="none" stroke="var(--line)"/><rect x="60" y="0" width="18" height="18" fill="none" stroke="var(--line)"/>
  <rect x="0" y="20" width="18" height="18" fill="var(--s1)"/><rect x="20" y="20" width="18" height="18" fill="var(--s1)"/><rect x="40" y="20" width="18" height="18" fill="none" stroke="var(--line)"/><rect x="60" y="20" width="18" height="18" fill="none" stroke="var(--line)"/>
  <rect x="0" y="40" width="18" height="18" fill="var(--s1)"/><rect x="20" y="40" width="18" height="18" fill="var(--s1)"/><rect x="40" y="40" width="18" height="18" fill="var(--s1)"/><rect x="60" y="40" width="18" height="18" fill="none" stroke="var(--line)"/>
  <rect x="0" y="60" width="18" height="18" fill="var(--s1)"/><rect x="20" y="60" width="18" height="18" fill="var(--s1)"/><rect x="40" y="60" width="18" height="18" fill="var(--s1)"/><rect x="60" y="60" width="18" height="18" fill="var(--s1)"/>
  </g>
</svg>
^ The unmasked matrix shades every cell equally (each position attends to all four tokens), while the masked matrix fills only the diagonal and below and leaves the upper triangle blank — the future positions that carry zero weight. That triangular shape is the entire mechanism. Look at position 0's row: unmasked it puts 0.75 of its attention on positions 1, 2, 3 — tokens it is supposed to predict — and masked it puts all of it on position 0. The equal scores make this stark: with nothing learned, the only thing shaping the attention is the mask, and it is the difference between "sees the future" and "does not." Note also that the masked rows still sum to 1; masking the scores to −inf before the softmax renormalizes over the allowed positions, which is why the mask goes there and not on the weights afterward.

## Build

The triangular matrix matters because of what it does to the output — whether a position's value is contaminated by the future. Run `--leak`.

```text filename=--leak
LEAK — attention mass on FUTURE tokens, and the output it corrupts
--------------------------------------------------------------
  pos   future mass (unmasked)   future mass (masked)
  0     0.750                    0.000
  1     0.500                    0.000
  2     0.250                    0.000
  3     0.000                    0.000
--------------------------------------------------------------
  unmasked output: [25.0, 25.0, 25.0, 25.0]  (every position = 25, it averaged the future too)
  masked   output: [10.0, 15.0, 20.0, 25.0]  (position i averages only tokens 0..i)
```

The future-mass column is the leak measured directly: unmasked, position 0 spends 75% of its attention on future tokens, position 1 spends 50%, position 2 spends 25% — masked, every one of these is 0. And the outputs show the damage. Unmasked, every position outputs 25.0, the average of all four token values, so position 0's representation is built from tokens 20, 30, and 40 that come *after* it — a representation it could never form at inference, where those tokens do not exist yet. Masked, position 0 outputs 10.0 (only its own token), position 1 outputs 15.0 (the average of 10 and 20), and so on: each output depends only on the past and present. In a real trained decoder this is the difference between a model that predicts the next token by copying it from the leaked future position (perfect training loss, useless at inference) and one that must actually learn to predict. The leak is measured as the attention mass sitting above the diagonal.

```python filename=modules/below-the-prompt/code/causalmask-inter-01/causalmask.py:71-74 COMPLETE
def future_mass(weights):
    """Per-position total attention weight landing on FUTURE positions (j>i)."""
    n = len(weights)
    return [round(sum(weights[i][j] for j in range(i + 1, n)), 4) for i in range(n)]
```

<svg role="img" aria-label="Position 0 under unmasked attention drawing on tokens 20, 30, 40 from the future to produce output 25, versus masked attention using only its own token 10 to produce output 10" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">position 0's output: unmasked pulls in the future, masked does not</text>
  <g transform="translate(20,22)" font-size="7">
  <rect x="0" y="0" width="30" height="16" fill="var(--s1)"/><text x="8" y="11" fill="var(--panel)">10</text>
  <rect x="34" y="0" width="30" height="16" fill="var(--muted)"/><text x="42" y="11" fill="var(--panel)">20</text>
  <rect x="68" y="0" width="30" height="16" fill="var(--muted)"/><text x="76" y="11" fill="var(--panel)">30</text>
  <rect x="102" y="0" width="30" height="16" fill="var(--muted)"/><text x="110" y="11" fill="var(--panel)">40</text>
  <text x="0" y="30" fill="var(--muted)">pos: 0(self)  1  2  3 (future)</text>
  </g>
  <g transform="translate(20,66)">
  <text x="0" y="10" fill="var(--muted)" font-size="7">unmasked pos0 ← all four →</text>
  <rect x="140" y="0" width="40" height="14" fill="var(--s2)"/><text x="146" y="11" fill="var(--panel)" font-size="7">out 25</text>
  <text x="190" y="11" fill="var(--muted)" font-size="7">(leaked future)</text>
  </g>
  <g transform="translate(20,90)">
  <text x="0" y="10" fill="var(--muted)" font-size="7">masked pos0 ← token 10 only</text>
  <rect x="140" y="0" width="40" height="14" fill="var(--s1)"/><text x="146" y="11" fill="var(--panel)" font-size="7">out 10</text>
  <text x="190" y="11" fill="var(--muted)" font-size="7">(past+present)</text>
  </g>
</svg>
^ Unmasked, position 0 averages its own token 10 with the future tokens 20, 30, 40 to output 25 — a value built from tokens it has not reached; masked, it uses only token 10 and outputs 10, a representation it could actually form at inference.

## Definition of done

The self-test pins the triangular shape, the zero future mass, the leak, and the changed output.

```python filename=modules/below-the-prompt/code/causalmask-inter-01/causalmask.py:115-122 COMPLETE
    lower_triangular = all(Wm[i][j] == 0.0 for i in range(n) for j in range(i + 1, n))
    print("  masked weights are lower-triangular (no weight on j>i) = %s" % lower_triangular)

    masked_no_future = sum(future_mass(Wm)) == 0.0
    print("  masked attention puts zero total mass on the future = %s" % masked_no_future)

    unmasked_leaks = future_mass(Wu)[0] > 0.0
    print("  unmasked attention leaks future mass (position 0) = %s (%.3f)" % (unmasked_leaks, future_mass(Wu)[0]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the masked weights are lower-triangular with zero future mass; unmasked leaks future mass; the mask changes the output
----------------------------------------------------------------------------------------------------------------------------------
  masked weights are lower-triangular (no weight on j>i) = True
  masked attention puts zero total mass on the future = True
  unmasked attention leaks future mass (position 0) = True (0.750)
  every attention row still sums to 1 (both) = True
  the mask changes position 0's output = True (25.0 unmasked vs 10.0 masked)
```

**Done means the leak and the fix are proven on real weights: the masked attention is lower-triangular with zero total future mass, the unmasked attention leaks 0.750 of position 0's attention onto future tokens, both matrices' rows still sum to 1, and the mask changes position 0's output from 25.0 (contaminated by the future) to 10.0 (past and present only) — so a decoder must mask the future before the softmax or it attends to what it is predicting.**

## Boss fight

Predict where the mask is subtler than "zero out the upper triangle," because its placement, its interaction with padding, and its relationship to bidirectional models all hide mistakes.

The first trap is that the mask must be applied to the scores, before the softmax, and applying it anywhere else silently breaks either correctness or the distribution. Zeroing the attention *weights* after the softmax leaves rows that no longer sum to 1 (the removed future mass is just gone, not redistributed), so every position's output is scaled down by however much future mass it had — a subtle, position-dependent corruption rather than a clean mask. Using a large negative number instead of true −inf (common in low-precision kernels, where −inf can produce NaNs) is fine only if it is large enough to make exp underflow to 0 at that precision; too small and a sliver of future leaks through. And the off-by-one is the classic bug: the diagonal must be *included* (position i attends to itself), so the condition is j ≤ i, not j < i — masking the diagonal too would stop a position from seeing its own token, and allowing j = i+1 would leak the immediate next token, which for next-token prediction is exactly the answer. The mask is one line, and each of these is a way to write that line wrong while training still runs.

The second trap is that the causal mask usually coexists with a padding mask, and they must compose without ever leaving a query with nothing to attend to. Batched sequences are padded to equal length, and the pad positions must be masked out as keys (no real query should attend to padding) — combine that with the causal mask and you get a per-position allowed set that is the intersection of "not future" and "not padding." The danger is a row masked down to *all* −inf: a query that is itself a pad token, under a causal mask, may have no valid keys, and softmax over all −inf is 0/0 = NaN that poisons the whole batch. Real implementations avoid this by never computing loss on pad positions and by guarding the all-masked row. And the broader point is that the causal mask is specifically a *decoder* construct: encoder self-attention in an encoder–decoder model, or a bidirectional model like BERT, deliberately has no causal mask because those positions are allowed to see the whole sequence — masking there would cripple them. So "always add a causal mask" is as wrong as forgetting it; the mask encodes the directionality the task requires, and you apply it exactly where generation must be left-to-right.

**The causal mask must go on the scores before the softmax (not the weights after, or rows stop summing to 1), include the diagonal (j ≤ i, or a position loses its own token or leaks the next one), and compose with a padding mask without producing an all-masked NaN row — and it belongs only in decoders that generate left-to-right, never in encoders or bidirectional models that are meant to see the whole sequence.**

## External resources

The "Attention Is All You Need" paper and any annotated transformer implementation — the masked self-attention in the decoder, why the mask is added to the scores before the softmax, and the lower-triangular structure it produces.

Writing on teacher forcing and autoregressive generation — why training on complete sequences makes future-token leakage possible and catastrophic, and how the causal mask keeps training consistent with one-token-at-a-time inference.

The companion attention and softmax modules in this topic — the causal mask is a modification to the attention scores before the softmax, so it builds directly on how attention weights and the softmax normalization work.
