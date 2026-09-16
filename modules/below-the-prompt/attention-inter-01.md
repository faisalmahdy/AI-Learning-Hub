---
id: attention-inter-01
title: Attention needs a causal mask, or the model reads its own answer
topic: below-the-prompt
level: intermediate
status: ready
time: 8-10h
summary: Build scaled dot-product self-attention over a five-token sequence and, unmasked, every early position spends real weight on the tokens that come after it — 0.45 of the first position's attention lands on its own future. A causal mask sets those future scores to negative infinity before the softmax, driving future mass to exactly 0.00 at every position, and the next-token leak — how much of token i+1 soaks into position i's output — drops with it, because a next-token predictor that can attend forward is just reading the answer it was asked to guess.
eli5: To learn to guess the next word you must not be allowed to peek at it. Attention lets every word look at every other word, including the ones ahead — so you cover the future with a card, and each word may only look left, at what it has already seen.
---

## Why this module

The last module cut text into tokens. This one takes the sequence of token vectors and builds the operation at the heart of a transformer: self-attention, where each position looks at the others and mixes in what is relevant. The scan lists attention among the internals with "broad coverage, zero implementation," so this is the second tiny rebuild — small enough to multiply the matrices by hand, real enough to expose the single most important correctness constraint in a language model.

That constraint is the causal mask, and it is easy to leave out because attention works without it — it just works *wrong*. A language model is trained to predict the next token, so position `i`'s job is to produce a representation that predicts token `i+1` without having seen it. But plain self-attention lets `i` attend to every position, including `i+1` and beyond, so `i`'s representation is soaked in the very token it is supposed to guess. Training accuracy looks perfect and the model learns nothing useful, because you handed it the answer sheet. The mask is the card over the future: before the softmax, every score from a position to a later position is set to negative infinity, so those positions get exactly zero weight.

You need `tokens-basic-01` for what a token is; everything here is plain-Python matrices, stdlib only, `$0.00`. The instinct to unlearn is that attention is symmetric — that "these two tokens attend to each other." In a causal language model attention is strictly one-directional in time: the present may read the past, never the future.

Here is the leak, measured — how much attention each position spends on its own future, with and without the mask:

```
# modules/below-the-prompt/code/attention-inter-01/ — COMPLETE, run from that directory
$ python3 attn.py --leak

FUTURE MASS — attention weight each position spends on later tokens
------------------------------------------------------------
  position   unmasked   masked
  the        0.446      0.000
  cat        0.265      0.000
  sat        0.284      0.000
  on         0.250      0.000
  mat        0.000      0.000
```

run: 2026-08-25 · deterministic; token vectors are a fixture · seq_len=5, dim=4 · `python3 attn.py --leak`

Unmasked, the first token pours 0.446 of its attention into tokens it has not reached yet; every early position leaks a quarter to nearly half of its attention forward. Masked, every one of those numbers is exactly zero. This module is that column of zeros and why a language model is broken without it.

## Concepts

Named here so you can find them again; each is built below.

- **Self-attention** — each position produces a weighted blend of all positions' values, weighted by relevance.
- **Scaled dot-product score** — relevance of `i` to `j` as their dot product, divided by √dim so the softmax does not saturate.
- **Softmax** — turns a row of scores into a probability distribution over positions.
- **Causal mask** — forbids attending to later positions by setting their scores to −∞ before the softmax.
- **Future mass** — the attention weight a position spends on later positions; the leak the mask removes.
- **Next-token leak** — how much of token `i+1` ends up in position `i`'s output; what the mask exists to prevent.

## Worked example

Source: the below-the-prompt track's anatomy material on attention, rebuilt here as runnable matrices rather than prose. The sequence and its embeddings are a fixture chosen so every dot product is checkable by hand.

Script and fixture: `modules/below-the-prompt/code/attention-inter-01/` — `attn.py`, and `seq.json`, five tokens with a 4-dimensional vector each. Every command runs from there.

### The frame: a card over the words you haven't reached

Imagine learning to predict the next word in a sentence by covering the page with a card and sliding it right one word at a time. At each step you may look at everything the card has already uncovered — the words to your left — and you guess what is under the card's edge. That discipline is the only thing that makes the exercise a prediction: the moment you lift the card and peek at the next word, your "prediction" is a copy, and you have learned nothing about predicting.

Self-attention is a room where every word can look at every other word at once. That is wonderful for understanding a finished sentence and fatal for learning to generate one, because it lets each word peek under the card. The causal mask is the card, reimposed inside the math: it makes the score from any position to a later position negative infinity, so after the softmax that later position contributes exactly nothing. The whole module is putting that card back.

### Scores, scaled

Attention starts by scoring how much each position wants each other position — the dot product of their vectors, divided by √dim so a high-dimensional dot product does not push the softmax into a spike.

```
# attn.py:52-57 — COMPLETE (scaled dot-product scores)
def scores(emb):
    """Scaled dot-product scores: how much position i wants position j, scaled by
    sqrt(dim) so the softmax does not saturate."""
    d = len(emb[0])
    n = len(emb)
    return [[dot(emb[i], emb[j]) / sqrt(d) for j in range(n)] for i in range(n)]
```

Each row becomes a distribution with a softmax, and the position's output is that distribution's weighted blend of all the value vectors.

```
# attn.py:43-47 — COMPLETE (softmax, skipping the masked -inf entries)
def softmax(row):
    m = max(v for v in row if v != NEG_INF)
    exps = [0.0 if v == NEG_INF else exp(v - m) for v in row]
    s = sum(exps)
    return [e / s for e in exps]
```

Run the unmasked attention and look at the matrix — row `i` is how position `i` splits its attention across all five positions:

```
# $ python3 attn.py --weights
#         the    cat    sat    on     mat
#   the   0.55   0.12   0.12   0.07   0.12
#   cat   0.13   0.60   0.13   0.05   0.08
#   sat   0.08   0.08   0.56   0.21   0.08
#   on    0.06   0.03   0.25   0.41   0.25
#   mat   0.10   0.06   0.10   0.28   0.46
```

run: 2026-08-25 · fixture · `python3 attn.py --weights`

The whole upper triangle — everything to the right of the diagonal — is a position attending to its future. `the`, the first token, gives 0.12 + 0.12 + 0.07 + 0.12 = 0.446 of its attention to `cat`, `sat`, `on`, and `mat`, none of which it should be able to see. That upper triangle is the bug.

<svg viewBox="0 0 700 200" role="img" aria-label="Two 5x5 attention matrices. Unmasked, the whole grid is filled including the upper triangle (the future). Masked, the upper triangle above the diagonal is zeroed, leaving a lower-triangular matrix.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--s2)">unmasked — upper triangle attends to the future</text>
    <text x="380" y="18" fill="var(--s1)">masked — future zeroed before softmax</text>
    <g>
      <g transform="translate(40,30)">
        <rect x="0" y="0" width="150" height="150" fill="none" stroke="var(--line)"></rect>
        <line x1="0" y1="0" x2="150" y2="150" stroke="var(--muted)" stroke-dasharray="2 2"></line>
        <g fill="var(--s2)" opacity="0.5"><rect x="30" y="0" width="120" height="30"></rect><rect x="60" y="30" width="90" height="30"></rect><rect x="90" y="60" width="60" height="30"></rect><rect x="120" y="90" width="30" height="30"></rect></g>
        <g fill="var(--s1)" opacity="0.4"><rect x="0" y="0" width="30" height="30"></rect><rect x="0" y="30" width="60" height="30"></rect><rect x="0" y="60" width="90" height="30"></rect><rect x="0" y="90" width="120" height="30"></rect><rect x="0" y="120" width="150" height="30"></rect></g>
        <text x="95" y="20" fill="var(--s2)" font-size="8">future</text>
      </g>
    </g>
    <g>
      <g transform="translate(400,30)">
        <rect x="0" y="0" width="150" height="150" fill="none" stroke="var(--line)"></rect>
        <line x1="0" y1="0" x2="150" y2="150" stroke="var(--muted)" stroke-dasharray="2 2"></line>
        <g fill="var(--s1)" opacity="0.4"><rect x="0" y="0" width="30" height="30"></rect><rect x="0" y="30" width="60" height="30"></rect><rect x="0" y="60" width="90" height="30"></rect><rect x="0" y="90" width="120" height="30"></rect><rect x="0" y="120" width="150" height="30"></rect></g>
        <text x="95" y="20" fill="var(--muted)" font-size="8">0.00</text>
      </g>
    </g>
  </g>
</svg>
^ The attention matrix, unmasked and masked. The mask deletes the upper triangle — every position-to-future score — leaving each position attending only to itself and its past. A causal language model is the right-hand shape or it is cheating.

### The mask: negative infinity before the softmax

The mask sets every future score to −∞ so the softmax gives it zero weight. It has to happen *before* the softmax — zeroing weights after would leave the distribution un-normalised.

```
# attn.py:60-64 — COMPLETE (forbid attending to any later position)
def apply_mask(sc):
    """Causal mask: position i may not attend to any j > i. Set those scores to
    -inf BEFORE the softmax so they get exactly zero weight."""
    n = len(sc)
    return [[sc[i][j] if j <= i else NEG_INF for j in range(n)] for i in range(n)]
```

The full attention assembles it: score, optionally mask, softmax, blend.

```
# attn.py:67-76 — COMPLETE (score -> mask -> softmax -> weighted blend of values)
def attention(emb, masked):
    sc = scores(emb)
    if masked:
        sc = apply_mask(sc)
    weights = [softmax(row) for row in sc]
    out = []
    for i in range(len(emb)):
        out.append([sum(weights[i][j] * emb[j][k] for j in range(len(emb)))
                    for k in range(len(emb[0]))])
    return weights, out
```

Run it masked and the matrix is lower-triangular — the first token attends only to itself, each later token only to itself and what came before:

```
# $ python3 attn.py --weights mask
#         the    cat    sat    on     mat
#   the   1.00   0.00   0.00   0.00   0.00
#   cat   0.18   0.82   0.00   0.00   0.00
#   sat   0.11   0.11   0.79   0.00   0.00
#   on    0.07   0.05   0.33   0.55   0.00
#   mat   0.10   0.06   0.10   0.28   0.46
```

run: 2026-08-25 · fixture · `python3 attn.py --weights mask`

`the` now attends 1.00 to itself — it has no past, so it can only look at itself. Every zero above the diagonal is a peek the mask forbade.

### Measuring the leak

Future mass makes the bug a number: per position, the total attention weight spent on later positions.

```
# attn.py:81-85 — COMPLETE (attention weight each position spends on its future)
def future_mass(weights):
    """Per position, the total attention weight spent on later positions -- the
    fraction of its representation that came from the future."""
    n = len(weights)
    return [sum(weights[i][j] for j in range(i + 1, n)) for i in range(n)]
```

Unmasked it is 0.45, 0.27, 0.28, 0.25, 0 — the last token has no future so it never leaks — and masked it is zero everywhere. The consequence is the next-token leak: how much of token `i+1` ends up in position `i`'s output.

```
# $ python3 attn.py --readout
#   position   unmasked   masked
#   the        0.540      0.400
#   cat        0.616      0.403
#   sat        0.834      0.683
#   on         0.827      0.690
```

run: 2026-08-25 · fixture · `python3 attn.py --readout`

Unmasked, position `on`'s output is 0.827 aligned with the next token `mat` — its representation is soaked in the answer. Masked, that drops. Note the masked numbers are not zero: the tokens' embeddings are correlated, so some resemblance to the next token survives even when you cannot attend to it — an honest reminder that the mask removes the *direct* leak, not every statistical trace. But the direct channel, the one that lets the model trivially cheat, is gone.

<svg viewBox="0 0 700 170" role="img" aria-label="Future mass per position as bars. Unmasked: the 0.45, cat 0.27, sat 0.28, on 0.25, mat 0. Masked: all zero. The unmasked bars are substantial; the masked ones are a flat zero line.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">future mass per position — the attention spent on what comes next</text>
    <line x1="60" y1="130" x2="640" y2="130" stroke="var(--grid)"></line>
    <g fill="var(--s2)">
      <rect x="80" y="63" width="40" height="67"></rect><rect x="200" y="90" width="40" height="40"></rect><rect x="320" y="88" width="40" height="42"></rect><rect x="440" y="93" width="40" height="37"></rect><rect x="560" y="130" width="40" height="0"></rect>
    </g>
    <g fill="var(--muted)" text-anchor="middle" font-size="8"><text x="100" y="58">0.45</text><text x="220" y="85">0.27</text><text x="340" y="83">0.28</text><text x="460" y="88">0.25</text><text x="580" y="125">0</text></g>
    <g fill="var(--ink)" text-anchor="middle"><text x="100" y="145">the</text><text x="220" y="145">cat</text><text x="340" y="145">sat</text><text x="460" y="145">on</text><text x="580" y="145">mat</text></g>
    <line x1="60" y1="130" x2="640" y2="130" stroke="var(--s1)" stroke-width="2"></line>
    <text x="400" y="160" fill="var(--s1)" font-size="8">masked: a flat zero line along the axis</text>
  </g>
</svg>
^ Unmasked, every position but the last spends a quarter to nearly half its attention on the future; masked, the whole series collapses to the zero line. The mask converts a leaky, bidirectional operation into a strictly causal one.

<svg viewBox="0 0 700 150" role="img" aria-label="Next-token leak per position: how much of token i+1 is in position i's output. Unmasked bars (the 0.54, cat 0.62, sat 0.83, on 0.83) sit above the masked bars (0.40, 0.40, 0.68, 0.69).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">next-token leak: alignment of position i's output with token i+1</text>
    <g>
      <text x="20" y="45" fill="var(--ink)">the</text><rect x="90" y="37" width="216" height="10" fill="var(--s2)"></rect><rect x="90" y="49" width="160" height="10" fill="var(--s1)"></rect><text x="312" y="46" fill="var(--muted)">.54 / .40</text>
      <text x="20" y="80" fill="var(--ink)">sat</text><rect x="90" y="72" width="334" height="10" fill="var(--s2)"></rect><rect x="90" y="84" width="273" height="10" fill="var(--s1)"></rect><text x="430" y="81" fill="var(--muted)">.83 / .68</text>
      <text x="20" y="115" fill="var(--ink)">on</text><rect x="90" y="107" width="331" height="10" fill="var(--s2)"></rect><rect x="90" y="119" width="276" height="10" fill="var(--s1)"></rect><text x="430" y="116" fill="var(--muted)">.83 / .69</text>
    </g>
    <text x="470" y="60" fill="var(--s2)" font-size="8">unmasked (soaked in i+1)</text>
    <text x="470" y="100" fill="var(--s1)" font-size="8">masked (direct leak gone)</text>
  </g>
</svg>
^ How much of the next token is in each position's output. Unmasked is higher everywhere — the representation carries the answer; masking removes the direct channel, and the residual is only the correlation between neighbouring embeddings the mask cannot touch.

**Self-attention is bidirectional by default, and a causal language model must not be: mask every position from its future before the softmax, or each token's representation contains the token it was supposed to predict.**

### The running tally

| attention | future mass (pos 1) | next-token leak (on) | valid causal LM? |
|---|---|---|---|
| unmasked | 0.446 | 0.827 | no — reads the answer |
| masked | 0.000 | 0.690 | yes — reads only the past |

The scores never changed; only whether the future was set to −∞ before the softmax. Without the mask, attention is a fine encoder of a complete sequence — this is exactly what a bidirectional model like BERT uses on purpose — but it cannot be trained to generate, because generation is prediction and prediction forbids peeking. The mask is the one line that turns a sequence encoder into a language model, and leaving it out is the kind of bug that trains to a beautiful loss curve and produces a model that has learned to copy.

### What we did not settle

The fixture uses fixed embeddings and identity value vectors so the arithmetic is visible; a real attention layer learns separate query, key, and value projections, and there are many heads, but the mask sits in the same place and does the same thing. Three real details we skipped: the scale is √(head dim), and getting it wrong re-introduces the softmax-saturation problem this module only names; the mask at generation time interacts with the KV cache — you attend to cached past keys, never recomputing the future, which is a whole module of its own; and bidirectional attention is not wrong, it is a different objective — encoders want it, decoders forbid it, and knowing which you are building is the actual lesson. The dial here is one mask; the machinery around it is the rest of the transformer.

## Build

The pipeline in one paragraph: score every pair of positions with a scaled dot product; for a causal model, set every score from a position to a later one to −∞ before the softmax; softmax each row into a distribution and blend the value vectors by it; and verify the future mass is exactly zero at every position before you trust the layer to train a generator. Never train a next-token model on unmasked attention.

We opened on the leak. The column that must be all zeros:

```
# modules/below-the-prompt/code/attention-inter-01/ — COMPLETE, run from that directory
$ python3 attn.py --leak
  masked future mass: 0.000 at every position
```

Now build your own attention. Use real learned projections if you have them or the identity as here, and compute the future mass with and without the mask. Your number to beat is **future mass at zero for every position under the mask** — any positive value is a leak that will let a next-token model cheat. Add a position and confirm the new upper-triangle entries are the ones the mask zeroes. Bring back the two future-mass columns and confirm the masked one is all zeros. Good luck.

## Definition of done

- [ ] Scaled dot-product self-attention over a sequence of token vectors, in code you can hand-check
- [ ] A causal mask that sets future scores to −∞ before the softmax
- [ ] Future mass computed per position, unmasked and masked
- [ ] Your own `seq.json` sequence, with the leak visible unmasked and sealed masked
- [ ] The unmasked attention kept for contrast, so the upper-triangle leak is visible
- [ ] `python3 attn.py --check` printing SELF-TEST PASS: unmasked leaks, masked future mass is zero, rows are valid distributions, the next-token leak drops
- [ ] The two future-mass columns recorded, and confirmation the masked one is all zeros
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A next-token model trained on unmasked attention reaches a perfect training loss and generates garbage. Explain both facts with one word about what position `i` could see.
2. Why must the mask set future scores to −∞ *before* the softmax rather than zeroing the weights after it?
3. The first token's masked attention row is 1.00 on itself and zero elsewhere. Explain why, in terms of its past.
4. Future mass was 0.45 unmasked and 0.00 masked for the first position. What does that number measure, and why is the last position's future mass always zero?
5. Your own run produced two future-mass columns. What were they, and did any masked position leak?

## External resources

- Vaswani et al., *Attention Is All You Need* (2017) — https://arxiv.org/abs/1706.03762 — my summary: the paper that defines scaled dot-product attention and the decoder's masking; read section 3.2 for the √dim scale and the "masking out (setting to −∞)" of illegal connections this module builds.
- Karpathy, *Let's build GPT: from scratch* — https://www.youtube.com/watch?v=kCc8FmEb1nY — my summary: builds a causal transformer in a notebook, with the mask via a lower-triangular matrix; watch it for the exact `tril` masking trick and how the KV cache extends it at generation time.
- This hub, *tokens-basic-01* — modules/below-the-prompt/tokens-basic-01.md — my summary: what a token is, the input this attention layer consumes; read it first if "token vector" is not yet concrete, since attention operates on exactly those vectors.
