---
id: scale-inter-01
title: Divide the attention scores by √d_k — or the softmax saturates as the head grows
topic: below-the-prompt
level: intermediate
status: ready
time: 22 min
summary: A dot product of d-dimensional vectors has a spread that grows like √d, so as the head widens the attention softmax collapses onto one key and its gradients vanish. Dividing every score by √d_k rescales the spread back to ~1. Unscaled, weight entropy falls from 1.10 to 0.02; scaled, it holds near its 2.08 max.
eli5: When you compare two long lists of numbers by multiplying and adding them up, the totals get bigger just because the lists are long — not because the match is better. If you don't shrink those totals back down, the computer thinks one key is a perfect match and ignores all the others. Dividing by the square root of the list length shrinks them back to a fair size.
---

## Why this module

The single most-copied line in the transformer is `scores / math.sqrt(d_k)`, and most people type it without knowing what breaks if they leave it out. What breaks is everything: the attention distribution collapses, the gradients die, and the model stops learning — and it gets worse the bigger you make the model.

Here is the mechanism in one sentence. Attention scores a query against a key with a dot product, and a dot product of two d-dimensional vectors is a sum of d terms, so its typical size grows with d. Concretely, for vectors whose entries are around unit scale, the dot product has variance about d and therefore a spread of about √d. That means the raw attention scores for a wide head — d_k of 64, 128, 256 — swing over a range of tens, and when you softmax scores that swing over tens, the single largest one wins almost all the weight. The attention distribution becomes nearly one-hot: it stops attending to a blend of keys and just picks the argmax.

That would be merely crude if it were the end of it, but softmax has a second problem exactly where it saturates: its gradient goes to zero. A head whose weights are pinned near one-hot cannot learn which key it *should* prefer, because the derivative that would nudge the weights has vanished. So the scale is not a cosmetic normalization — it is what keeps the attention head trainable as you scale the model up. Leave it out and your small model limps while your big model refuses to train at all.

We will build the dot products directly, watch the score spread grow from 6 to 36 as the head widens from 4 to 256, and watch the softmax entropy collapse from 1.10 nats to 0.02 — a distribution over eight keys crushed onto essentially one. Then we divide by √d_k and watch the entropy climb back and stay near its maximum of 2.08 at every head size.

**The dot product grows with the head width for a reason that has nothing to do with relevance, and without the √d_k scale the softmax reads that growth as certainty and collapses.**

## Concepts

Why √d specifically? Take a query q and a key k whose entries are independent, zero-mean, and unit-variance. Their dot product is the sum over d dimensions of q_i·k_i. Each product term has mean zero and variance one, and the terms are independent, so their sum has variance d — variances add. The standard deviation, the typical magnitude, is therefore √d. Double the head width and the scores do not double; they grow by √2. Multiply the width by 64 and the spread grows by 8. That is the √d that has to be divided back out.

Now feed that into softmax. Softmax turns scores into weights proportional to their exponentials, so what matters is the *differences* between scores, measured in the natural units of the exponential. When the spread is about 1 — a few tenths between the top scores — the exponentials are comparable and the weight is shared across several keys: a soft, informative distribution. When the spread is about 30, the top score's exponential dwarfs everything else by factors of e^30, and one key takes essentially all the weight. Same softmax, same keys; only the scale of the scores changed, and it changed because the head got wider.

The measure we will use for "soft versus collapsed" is entropy: the Shannon entropy of the weight distribution, in nats. Entropy is maximal — ln(8) ≈ 2.08 for eight keys — when the weight is spread evenly, and it falls to zero when one key takes all the weight. Watching entropy as the head grows is watching attention lose its ability to attend to more than one thing.

The fix restores the units. Divide every score by √d_k and the spread goes back to about 1 regardless of d, because you have divided a √d-scale quantity by √d. The differences that drive the softmax are back in the range where the exponential is gentle, the weight stays shared, and the entropy stays high. The scale does not change which key scores highest — it divides all scores equally — it only stops the softmax from over-reacting to a spread that is an artifact of dimension.

**Softmax responds to score differences on the exponential's scale; √d_k is exactly the factor that keeps those differences from growing with head width instead of with relevance.**

## Worked example

The query and keys are generated deterministically, so the run is reproducible without any fixture file — a tiny linear congruential generator emits ±1 entries, which are zero-mean and unit-scale, exactly the setup where the spread is √d.

```python filename=modules/below-the-prompt/code/scale-inter-01/scale.py:34-41 COMPLETE
def gen(seed, n):
    """Deterministic +/-1 vector of length n from a small LCG -- reproducible, zero-mean, unit-scale."""
    x = (seed * 2654435761 + 12345) & 0x7FFFFFFF
    out = []
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        out.append(1.0 if (x >> 16) & 1 else -1.0)
    return out
```

One query, eight keys, at head sizes 4, 16, 64, 256. The scoring is a dot product, optionally divided by √d.

```python filename=modules/below-the-prompt/code/scale-inter-01/scale.py:62-68 COMPLETE
def logits(d, scale):
    """The NUM_KEYS attention scores for one query at head size d; scale=True divides by sqrt(d)."""
    q = gen(0, d)
    raw = [dot(q, gen(j + 1, d)) for j in range(NUM_KEYS)]
    if scale:
        raw = [s / math.sqrt(d) for s in raw]
    return raw
```

Look at the raw scores before any scaling, and watch the spread grow.

```text filename=modules/below-the-prompt/code/scale-inter-01/scale.py --logits
LOGITS — raw dot-product scores for one query vs 8 keys, per head size
--------------------------------------------------------------
  d_k=  4  scores [2, 2, 4, 0, 0, 2, -2, 0]              spread 6.0
  d_k= 16  scores [-2, 4, 0, 4, -2, -2, 6, 4]            spread 8.0
  d_k= 64  scores [-6, 4, -2, 16, -4, -12, 0, 12]        spread 28.0
  d_k=256  scores [-22, 6, -10, 14, 8, 2, -2, -2]        spread 36.0
```

The spread climbs 6, 8, 28, 36 as the head quadruples each step — not exactly √d on a single random draw, but unmistakably growing with dimension rather than staying fixed. At d_k = 4 the scores sit within 6 of each other; at d_k = 256 they span 36. The keys did not become more or less relevant — the head just got wider, and the dot product got bigger for free.

<svg role="img" aria-label="Bar chart of score spread growing with head size: 6 at d=4, 8 at d=16, 28 at d=64, 36 at d=256" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">score spread vs head size d_k</text>
  <line x1="60" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <rect x="80" y="140" width="50" height="10" fill="var(--s1)" stroke="var(--line)"/><text x="90" y="166" font-family="var(--mono)" font-size="10" fill="var(--muted)">d=4</text><text x="96" y="134" font-family="var(--mono)" font-size="10" fill="var(--ink)">6</text>
  <rect x="170" y="137" width="50" height="13" fill="var(--s1)" stroke="var(--line)"/><text x="178" y="166" font-family="var(--mono)" font-size="10" fill="var(--muted)">d=16</text><text x="186" y="131" font-family="var(--mono)" font-size="10" fill="var(--ink)">8</text>
  <rect x="260" y="103" width="50" height="47" fill="var(--s1)" stroke="var(--line)"/><text x="268" y="166" font-family="var(--mono)" font-size="10" fill="var(--muted)">d=64</text><text x="272" y="97" font-family="var(--mono)" font-size="10" fill="var(--ink)">28</text>
  <rect x="350" y="90" width="50" height="60" fill="var(--s1)" stroke="var(--line)"/><text x="356" y="166" font-family="var(--mono)" font-size="10" fill="var(--muted)">d=256</text><text x="360" y="84" font-family="var(--mono)" font-size="10" fill="var(--ink)">36</text>
</svg>
^ The spread of the raw scores grows with head width — the dot product gets larger just because there are more dimensions to sum, not because any key matches better.

The softmax is the standard max-subtracted one, and entropy measures how spread out its weights are.

```python filename=modules/below-the-prompt/code/scale-inter-01/scale.py:50-54 COMPLETE
def softmax(scores):
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]
```

```python filename=modules/below-the-prompt/code/scale-inter-01/scale.py:57-59 COMPLETE
def entropy(weights):
    """Shannon entropy in nats -- high means the weights are spread over many keys, 0 means one-hot."""
    return round(-sum(w * math.log(w) for w in weights if w > 0), 4)
```

Now run the softmax both ways and read the entropy and the top weight at each head size.

```text filename=modules/below-the-prompt/code/scale-inter-01/scale.py --weights
WEIGHTS — softmax entropy (max 2.079) and top weight, unscaled vs 1/sqrt(d_k) scaled
--------------------------------------------------------------------
  d_k     unscaled: entropy  top      scaled: entropy  top
    4               1.096   0.683              1.747   0.391
   16               0.936   0.709              1.834   0.290
   64               0.090   0.982              1.536   0.445
  256               0.020   0.997              1.923   0.261
```

The unscaled column is a collapse in slow motion. At d_k = 4 the entropy is 1.096 and the top key holds 68% of the weight — already peaked, but sharing. By d_k = 64 the entropy has fallen off a cliff to 0.090 and the top key holds 98%; by d_k = 256 the entropy is 0.020 and one key holds 99.7% of the weight. Attention over eight keys has become attention over one. The scaled column, right beside it, does none of this: entropy stays between 1.5 and 1.9 out of a maximum 2.08, and the top weight stays between 0.26 and 0.45. Same query, same keys, same head sizes — the only difference is the √d_k divisor.

<svg role="img" aria-label="Entropy versus head size: the unscaled curve falls from 1.10 toward 0.02, the scaled curve stays high near the 2.08 maximum" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">entropy (nats) vs head size d_k</text>
  <line x1="60" y1="40" x2="60" y2="165" stroke="var(--line)"/>
  <line x1="60" y1="165" x2="430" y2="165" stroke="var(--line)"/>
  <line x1="60" y1="45" x2="430" y2="45" stroke="var(--grid)" stroke-dasharray="3 3"/>
  <text x="366" y="41" font-family="var(--mono)" font-size="10" fill="var(--muted)">max 2.08</text>
  <text x="30" y="49" font-family="var(--mono)" font-size="10" fill="var(--muted)">2</text>
  <text x="30" y="168" font-family="var(--mono)" font-size="10" fill="var(--muted)">0</text>
  <text x="70" y="182" font-family="var(--mono)" font-size="10" fill="var(--muted)">4</text><text x="180" y="182" font-family="var(--mono)" font-size="10" fill="var(--muted)">16</text><text x="290" y="182" font-family="var(--mono)" font-size="10" fill="var(--muted)">64</text><text x="395" y="182" font-family="var(--mono)" font-size="10" fill="var(--muted)">256</text>
  <polyline points="75,99 185,109 295,160 400,164" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="75" cy="99" r="3" fill="var(--s2)"/><circle cx="185" cy="109" r="3" fill="var(--s2)"/><circle cx="295" cy="160" r="3" fill="var(--s2)"/><circle cx="400" cy="164" r="3" fill="var(--s2)"/>
  <text x="90" y="96" font-family="var(--mono)" font-size="10" fill="var(--ink)">unscaled → collapses</text>
  <polyline points="75,60 185,55 295,73 400,50" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="75" cy="60" r="3" fill="var(--acc-line)"/><circle cx="185" cy="55" r="3" fill="var(--acc-line)"/><circle cx="295" cy="73" r="3" fill="var(--acc-line)"/><circle cx="400" cy="50" r="3" fill="var(--acc-line)"/>
  <text x="230" y="90" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">scaled → holds high</text>
</svg>
^ As the head widens, the unscaled entropy falls toward zero while the scaled entropy stays near its maximum — the √d_k divisor is what keeps the curve flat.

<svg role="img" aria-label="Two attention weight distributions over eight keys at head size 256: unscaled is one tall bar near 1.0, scaled is eight comparable bars" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">weights at d_k=256 (8 keys)</text>
  <text x="30" y="44" font-family="var(--mono)" font-size="10" fill="var(--ink)">unscaled: top=0.997</text>
  <g fill="var(--s2)" stroke="var(--line)">
    <rect x="30" y="52" width="14" height="4"/><rect x="50" y="52" width="14" height="4"/><rect x="70" y="52" width="14" height="4"/><rect x="90" y="52" width="14" height="80"/><rect x="110" y="52" width="14" height="4"/><rect x="130" y="52" width="14" height="4"/><rect x="150" y="52" width="14" height="4"/><rect x="170" y="52" width="14" height="4"/>
  </g>
  <text x="90" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">one key</text>
  <text x="250" y="44" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">scaled: top=0.261</text>
  <g fill="var(--acc-line)" stroke="var(--acc-ink)">
    <rect x="250" y="112" width="14" height="20"/><rect x="270" y="102" width="14" height="30"/><rect x="290" y="110" width="14" height="22"/><rect x="310" y="80" width="14" height="52"/><rect x="330" y="108" width="14" height="24"/><rect x="350" y="120" width="14" height="12"/><rect x="370" y="116" width="14" height="16"/><rect x="390" y="118" width="14" height="14"/>
  </g>
  <text x="285" y="150" font-family="var(--mono)" font-size="9" fill="var(--muted)">spread across keys</text>
</svg>
^ At the same head size the unscaled softmax is a single spike — attention has become argmax — while the scaled softmax keeps weight on many keys.

## Build

Reproduce the collapse and the fix. Pure standard library and a deterministic generator, so every number here is exact — 1.096 down to 0.020 unscaled, holding near 1.9 scaled.

Run `--logits` for the growing spread, `--weights` for the entropy table, `--check` for the gate. The self-test does not just check the scaled version is softer; it checks all four legs of the story — that unscaled collapses, that it reaches near-one-hot, that scaled stays soft everywhere, and that scaled beats unscaled at the largest head.

```python filename=modules/below-the-prompt/code/scale-inter-01/scale.py:103-108 COMPLETE
    small, large = HEAD_SIZES[0], HEAD_SIZES[-1]
    ent_unscaled_small = entropy(softmax(logits(small, scale=False)))
    ent_unscaled_large = entropy(softmax(logits(large, scale=False)))
    unscaled_collapses = ent_unscaled_large < ent_unscaled_small / 2
    print("  unscaled entropy collapses as d_k grows = %s (d=%d: %.3f -> d=%d: %.3f)"
          % (unscaled_collapses, small, ent_unscaled_small, large, ent_unscaled_large))
```

The predicate `ent_unscaled_large < ent_unscaled_small / 2` demands the entropy at the widest head be less than half its value at the narrowest — not merely lower, but collapsed by more than half. That guards against a weak claim: a tiny drop would be uninteresting, so the test insists the effect is large. Here 0.020 is not half of 1.096, it is under a fiftieth of it. Here is the full gate.

```text filename=modules/below-the-prompt/code/scale-inter-01/scale.py --check
SELF-TEST — unscaled attention saturates as d_k grows; the 1/sqrt(d_k) scale keeps it soft
------------------------------------------------------------------------------
  unscaled entropy collapses as d_k grows = True (d=4: 1.096 -> d=256: 0.020)
  at the largest head the unscaled top weight is near one = True (0.997)
  scaled entropy stays soft at every head size = True (min 1.536 of max 2.079)
  scaling keeps the top weight far below the unscaled one = True (0.261 vs 0.997)
------------------------------------------------------------------------------
SELF-TEST PASS  unscaled_collapses=True  unscaled_near_onehot=True  scaled_stays_soft=True  scaled_beats_unscaled=True
```

Four True flags. Unscaled_collapses: the entropy craters as the head grows. Unscaled_near_onehot: at the largest head one key holds 99.7% of the weight. Scaled_stays_soft: with the divisor the entropy never drops below 0.6 of its maximum, at any head size. Scaled_beats_unscaled: at d_k = 256 the scaled top weight, 0.261, is a quarter of the unscaled 0.997. The conjunction is the case: the scale is not a cosmetic preference, it is the difference between attending and collapsing.

**The self-test demands the collapse be more than half, so passing means the effect is large — a scale you can leave out on a toy head but never on a real one.**

## Definition of done

You are done when you reproduce the entropy table and can explain the √d from first principles.

Concretely: `--logits` shows the spread growing 6, 8, 28, 36; `--weights` shows unscaled entropy 1.096 → 0.020 and scaled entropy holding near 1.5–1.9; `--check` prints PASS with four True flags. You can derive why the dot product of unit-scale d-vectors has standard deviation √d — variances of d independent unit-variance terms add to d — and why √d is therefore the right divisor. You can explain what softmax does with a spread of 30 versus a spread of 1, in terms of the exponential's sensitivity to differences. And you can state the second, subtler cost of collapse: softmax gradients vanish at saturation, so a collapsed head cannot learn.

The portable understanding: any time you softmax a score that is a sum over a dimension, ask whether that score's scale grows with the dimension, and if it does, divide it back out before the softmax. The √d_k in attention is the canonical instance of a general rule.

## Boss fight

The instructive failure is that this bug hides at small scale and detonates at large scale.

An engineer writes an attention head, tests it at d_k = 16 on a toy task, and it works — the entropy at d_k = 16 is 0.936, peaked but still learning. They ship the architecture, someone scales d_k to 128 for a real model, and training stalls: the loss barely moves, the attention maps are one-hot from step one, and no one can see why because every line of code is "correct." The √d_k was never there, and it never mattered until the head got wide enough for the unscaled spread to saturate the softmax. This is the worst class of bug — invisible in the unit test, fatal in production — and it is exactly why the original paper calls the scaled dot product out by name.

Your turn, two moves. First, confirm the mechanism scales the way the theory says. The spread should grow like √d_k, so from d = 16 to d = 256 — a 16× jump — the spread should grow about √16 = 4×. Check the numbers: 8 to 36 is roughly 4.5×, close given it is a single random draw per head. Predict what d_k you would need for the unscaled top weight to exceed 0.999, and test it by adding a head size. Second, find the break-even. The scale divides by √d_k; what if you divided by d_k instead, or by √d_k of the wrong dimension? Try dividing by d_k (not its square root) and predict: you will over-correct, shrinking the spread below 1 and flattening the softmax toward uniform, which throws away real relevance the way the unscaled version threw away everything but one key. The √ is not decoration — it is the unique power that makes the corrected spread independent of d, and either exponent on the wrong side of it fails in its own direction.

## External resources

The scaled dot-product attention and its √d_k are introduced in Vaswani et al., "Attention Is All You Need" (2017), which states the exact reason: for large d_k the dot products grow large in magnitude, pushing the softmax into regions of vanishing gradient.

For the softmax-saturation half of the story — why gradients die where the distribution is near one-hot — any treatment of the softmax Jacobian works; the gradient is w_i(δ_ij − w_j), which goes to zero as the weights approach one-hot.

For the statistics half — why a sum of d independent unit-variance terms has variance d — any probability text's treatment of variance of sums covers it; it is the same √n that makes the standard error of a mean shrink like 1/√n, run in reverse.
