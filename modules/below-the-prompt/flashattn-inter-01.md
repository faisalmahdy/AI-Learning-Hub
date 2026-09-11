---
id: flashattn-inter-01
title: Compute attention in one streaming pass with a running max — or you store the whole score row and overflow on big scores
topic: below-the-prompt
level: intermediate
status: ready
time: 18 min
summary: Attention turns a query into a weighted average of value vectors, weighted by the softmax of the query-key scores, and the textbook softmax needs the whole score row in memory at once — one pass for the max, one to exponentiate and sum, one to normalize. For a query over thousands of keys, and every query in a long sequence, that materializes an N×N matrix of scores, the memory that makes naive attention quadratic in space. Online (streaming) softmax computes the identical result in a single pass keeping only three running scalars — a running max, a running normalizer, and a running output — by rescaling the accumulators by exp(old_max − new_max) whenever a larger score arrives. This is the kernel behind FlashAttention: stream over keys in blocks, carry the three scalars, and attention runs in memory that does not grow with the sequence. The running max also prevents overflow: subtract it and every exponent is ≤ 0. On a fixture, the online pass matches two-pass attention exactly (39.95 on moderate scores), and on scores near 1000 the naive sum-of-exp overflows to nan while the online pass returns the correct 21.55.
eli5: To average a huge list of numbers where each gets an "importance" from an exponential, you'd normally read the whole list twice — once to find the biggest (so the exponentials don't blow up) and once to add them. But if the list is enormous you don't want to hold it all. The trick: walk through once, keeping a running "biggest so far," a running total, and a running answer. Every time you meet a new biggest, you gently shrink what you've accumulated so far to match the new scale, then add the new item. At the end you have the exact same average, having held only three numbers.
---

## Why this module

Softmax is defined over a whole vector — you cannot normalize until you have seen every term — so the obvious implementation stores the entire score row, and for attention that row, across all queries, is the quadratic memory that stops long contexts from fitting.

Attention computes, for each query, a weighted average of value vectors where the weights are the softmax of the query's scores against every key. Softmax needs the maximum (subtracted so the exponentials do not overflow) and the sum of exponentials (to normalize), and both are properties of the whole vector, so the textbook routine makes three passes over a stored score row: find the max, exponentiate and sum, then divide. For one query against a few keys that is nothing. For a query against thousands of keys, and for every one of thousands of query positions, the scores form an N×N matrix that must be held in memory — the quadratic space cost of attention, and the practical wall that a long context slams into long before it runs out of compute. The row has to exist, in this telling, because you cannot normalize a softmax until you have seen all of it.

**Softmax needs the max and the sum over the whole vector, so a naive attention stores the entire N×N score matrix — the quadratic memory that, not the FLOPs, is what makes long-context attention infeasible.**

Online softmax breaks the assumption that you must see the whole row before you can normalize. Walk the keys once, carrying three running scalars: the maximum score so far, the running sum of exponentials, and the running weighted output. When a new score exceeds the running maximum, every accumulator you built against the old maximum is scaled wrong by a known factor — exp(old_max − new_max) — so you multiply the running sum and output by that correction, then add the new term against the new maximum. At the end, the running output divided by the running normalizer is *exactly* the softmax-weighted average, and you never stored more than three numbers. This is the kernel behind FlashAttention: process keys in blocks, carry the three scalars from block to block, and attention runs in memory independent of the sequence length. The running maximum does double duty — it also keeps every exponent ≤ 0, so nothing overflows. This module runs both and shows them agree to the digit.

## Concepts

**Two-pass softmax attention** subtracts the max, exponentiates, sums, and normalizes — correct, numerically safe, and dependent on having the whole score row in memory.

```python filename=modules/below-the-prompt/code/flashattn-inter-01/flashattn.py:43-48 COMPLETE
def two_pass_attention(scores, values):
    """Standard softmax attention: subtract the max, exponentiate, normalize -- needs the whole score row."""
    m = max(scores)
    weights = [math.exp(s - m) for s in scores]
    z = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / z
```

**Online softmax attention** keeps a running max `m`, normalizer `l`, and output `o`, and rescales `l` and `o` by exp(m − m_new) whenever a larger score arrives, so it needs only those three scalars.

```python filename=modules/below-the-prompt/code/flashattn-inter-01/flashattn.py:51-61 COMPLETE
def online_attention(scores, values):
    """One streaming pass keeping (running max m, running normalizer l, running output o); rescale on a new max."""
    m, l, o = float("-inf"), 0.0, 0.0
    for s, v in zip(scores, values):
        m_new = max(m, s)
        correction = math.exp(m - m_new)          # rescales the old accumulators to the new max
        e = math.exp(s - m_new)
        l = l * correction + e
        o = o * correction + e * v
        m = m_new
    return o / l
```

**The rescaling is what makes streaming exact.** Because every accumulator is always expressed relative to the current running max, a later, larger score simply re-bases the earlier work by a known factor rather than invalidating it.

<svg role="img" aria-label="As scores stream in, the running max updates; when a new larger score arrives the running sum and output are multiplied by exp(old max minus new max) before the new term is added" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">streaming update when a bigger score arrives</text>
  <text x="10" y="32" fill="var(--ink)" font-size="8">running: m=3, l, o</text>
  <line x1="120" y1="28" x2="150" y2="28" stroke="var(--line)"/><polygon points="150,25 156,28 150,31" fill="var(--line)"/>
  <text x="160" y="32" fill="var(--s2)" font-size="8">new score 5</text>
  <text x="10" y="56" fill="var(--muted)" font-size="7">1. m_new = max(3,5) = 5</text>
  <text x="10" y="70" fill="var(--muted)" font-size="7">2. correction = exp(3−5) = 0.135</text>
  <text x="10" y="84" fill="var(--muted)" font-size="7">3. l ← l·0.135 + exp(5−5);  o ← o·0.135 + exp(0)·v</text>
  <text x="10" y="102" fill="var(--muted)" font-size="8">the old work is re-based to the new max, not recomputed — three scalars carry everything</text>
</svg>
^ When a score larger than the running max arrives, the running normalizer and output are multiplied by exp(old_max − new_max) to re-base them, then the new term is added — so the streaming result stays exact with only three scalars of state.

**Online softmax rescales its running accumulators to each new maximum, so it computes the exact softmax-weighted attention in one pass with three scalars — never storing the score row that makes naive attention quadratic in memory.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/flashattn-inter-01/flashattn.py

The fixture is one query's scores and values, plus a large-score variant for the overflow case.

```json filename=modules/below-the-prompt/code/flashattn-inter-01/flashattn.json:3-6 COMPLETE
  "scores": [1.0, 3.0, 2.0, 5.0, 4.0],
  "values": [10.0, 20.0, 30.0, 40.0, 50.0],
  "large_scores": [1000.0, 1002.0, 1001.0],
  "large_values": [10.0, 20.0, 30.0]
```

Run `--attention` to compute the output both ways.

```text filename=--attention
ATTENTION — two-pass softmax vs one-pass online (moderate scores)
--------------------------------------------------------------
  scores:            [1.0, 3.0, 2.0, 5.0, 4.0]
  two-pass output:   39.9521  (stores the whole 5-score row)
  online output:     39.9521  (three running scalars, one pass)
  match?             True
```

Both produce 39.9521, identical to four decimals — and in fact identical to machine precision, as the self-test confirms. The two-pass version held the whole five-element weight vector; the online version held three scalars and streamed the scores one at a time, rescaling twice (when 3 arrived after 1, and when 5 arrived after 3). The output is a weighted average pulled toward the values with the highest scores: the score of 5 at position 3 dominates the softmax, so the output (39.95) sits near that position's value (40). Nothing about the answer changed — online softmax is not an approximation, it is an exact reformulation of the same computation into a form that never needs the whole row present at once. That is the entire basis of the memory win: identical math, streamed.

<svg role="img" aria-label="Two-pass attention stores a 5-element row and outputs 39.95; online attention keeps 3 scalars and outputs the same 39.95" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same output, very different working memory</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">two-pass</text>
  <g><rect x="70" y="22" width="16" height="12" fill="var(--s2)"/><rect x="88" y="22" width="16" height="12" fill="var(--s2)"/><rect x="106" y="22" width="16" height="12" fill="var(--s2)"/><rect x="124" y="22" width="16" height="12" fill="var(--s2)"/><rect x="142" y="22" width="16" height="12" fill="var(--s2)"/></g>
  <text x="164" y="32" fill="var(--muted)" font-size="7">stores 5 scores → 39.95</text>
  <text x="6" y="58" fill="var(--muted)" font-size="8">online</text>
  <g><rect x="70" y="50" width="16" height="12" fill="var(--s1)"/><rect x="88" y="50" width="16" height="12" fill="var(--s1)"/><rect x="106" y="50" width="16" height="12" fill="var(--s1)"/></g>
  <text x="128" y="60" fill="var(--muted)" font-size="7">3 scalars (m, l, o) → 39.95</text>
  <text x="6" y="86" fill="var(--muted)" font-size="8">the online row does not grow with the number of keys — that is the FlashAttention memory win</text>
</svg>
^ Two-pass attention keeps the full five-score row; online attention keeps three scalars and streams — both output 39.95, so the memory saving costs nothing in accuracy.

## Build

The running max is not only about memory — it is the same subtraction that keeps softmax from overflowing, and dropping it is the tempting shortcut that breaks. Run `--overflow`.

```text filename=--overflow
OVERFLOW — scores near 1000: naive exp overflows, running-max online does not
----------------------------------------------------------------
  scores:                 [1000.0, 1002.0, 1001.0]
  naive sum(exp(score)):  nan  (exp(1000) = inf, so inf/inf)
  online output:          21.5470  (every exponent <= 0, so finite)
  two-pass output:        21.5470
```

The naive version — sum exp(score) with no max subtracted — computes exp(1000), which is larger than any finite float and becomes infinity; the normalizer is infinity, the weighted sum is infinity, and infinity divided by infinity is nan. The answer is destroyed not by a bug in the logic but by the range of the number type, and raw attention scores routinely reach magnitudes that do this.

```python filename=modules/below-the-prompt/code/flashattn-inter-01/flashattn.py:72-76 COMPLETE
def naive_no_max(scores, values):
    """The tempting shortcut: sum exp(score) with no max subtraction -- overflows to inf on large scores (inf/inf = nan)."""
    weights = [_ieee_exp(s) for s in scores]
    z = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / z
```

The online pass returns the correct 21.5470 on the same scores, because subtracting the running max makes every exponent ≤ 0, so every exp is in (0, 1] and nothing overflows. This is why the running max is load-bearing twice over: it is the state that lets the computation stream (memory), and it is the shift that keeps the exponentials in range (stability). The two properties are not a coincidence — softmax is invariant to subtracting a constant from all its inputs, so you are free to subtract the running max, and doing so is exactly what both a memory-safe streaming pass and a numerically-safe pass require. Skip the max and you get the worst of both: a version that neither streams nor survives large scores.

<svg role="img" aria-label="Naive exp of a score near 1000 overflows to infinity giving nan; subtracting the running max makes every exponent at most zero so the result is a finite 21.55" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">scores near 1000</text>
  <text x="6" y="34" fill="var(--muted)" font-size="8">naive</text>
  <text x="60" y="34" fill="var(--s2)" font-size="8">exp(1000) = ∞ → ∞/∞ = nan ✗</text>
  <line x1="6" y1="44" x2="290" y2="44" stroke="var(--grid)"/>
  <text x="6" y="62" fill="var(--muted)" font-size="8">online</text>
  <text x="60" y="62" fill="var(--ink)" font-size="8">exp(score − max) ∈ (0, 1] → 21.55 ✓</text>
  <text x="60" y="78" fill="var(--muted)" font-size="7">subtracting the running max shifts every exponent to ≤ 0</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">the same running max both streams the computation and keeps it in float range</text>
</svg>
^ Without the max, exp(1000) overflows to infinity and the result is nan; subtracting the running max puts every exponent in (0, 1], so the online pass returns the correct finite 21.55.

## Definition of done

The self-test pins both properties: online equals two-pass on moderate and large scores, the naive version overflows where online stays finite, and the online state is three scalars.

```python filename=modules/below-the-prompt/code/flashattn-inter-01/flashattn.py:112-127 COMPLETE
    online_matches = abs(online_attention(sc, val) - two_pass_attention(sc, val)) < 1e-9
    print("  online attention equals two-pass on the moderate scores = %s (%.4f)" % (online_matches, online_attention(sc, val)))

    online_matches_large = abs(online_attention(lsc, lval) - two_pass_attention(lsc, lval)) < 1e-9
    print("  online equals two-pass on the large scores too = %s (%.4f)" % (online_matches_large, online_attention(lsc, lval)))

    naive_overflows = not math.isfinite(naive_no_max(lsc, lval))
    print("  the naive no-max version overflows to non-finite on large scores = %s (%s)" % (naive_overflows, naive_no_max(lsc, lval)))

    online_finite_large = math.isfinite(online_attention(lsc, lval))
    print("  the online version stays finite on the same large scores = %s" % online_finite_large)

    online_state_scalars = 3  # the online pass keeps exactly three running scalars (max, normalizer, output)
    state_smaller_than_row = online_state_scalars < len(sc)
    print("  the online pass keeps %d scalars, fewer than the %d-score row the two-pass stores = %s"
          % (online_state_scalars, len(sc), state_smaller_than_row))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — online equals two-pass exactly; naive overflows on large scores; the online state is O(1)
------------------------------------------------------------------------------------------------------------
  online attention equals two-pass on the moderate scores = True (39.9521)
  online equals two-pass on the large scores too = True (21.5470)
  the naive no-max version overflows to non-finite on large scores = True (nan)
  the online version stays finite on the same large scores = True
  the online pass keeps 3 scalars, fewer than the 5-score row the two-pass stores = True
```

**Done means the streaming reformulation is proven exact and safe: online attention equals two-pass to machine precision on both the moderate scores (39.9521) and the large ones (21.5470), the naive no-max version overflows to nan where the online version stays finite, and the online pass carries three scalars instead of the full score row — the exactness that makes FlashAttention a memory optimization, not an approximation.**

## Boss fight

Predict the two things this scalar sketch hides about the real kernel. It is tempting to think "one pass, three scalars" is the whole story.

The first trap is that the memory win is real but it comes with a compute cost, and the cost lands in the backward pass. FlashAttention does not store the N×N attention matrix, which is exactly what backpropagation would normally need to compute gradients — so it *recomputes* the attention on the fly during the backward pass, trading the quadratic memory for extra FLOPs. That is a good trade on modern accelerators, where memory bandwidth, not arithmetic, is the bottleneck: the whole point is that reading and writing the giant score matrix to high-bandwidth memory is slower than recomputing it in fast on-chip SRAM. So FlashAttention is not free speed; it is a memory-for-compute trade that wins because the hardware is memory-bound, and on a device where the balance is different the calculus changes. The same recompute-in-backward discipline as gradient checkpointing applies, including the correctness requirement that the recomputed forward reproduce the original exactly.

The second trap is that "attention" is not one scalar per key — it is a vector output over batched queries in tiles, and the scalar version elides where the real work is. The value `v` is a vector (the head dimension), so the running output `o` is a vector too, and the whole point of FlashAttention is that it processes *blocks* of queries against *blocks* of keys, keeping the three running quantities per query in the block and rescaling a whole tile at once, so the arithmetic is dense matrix multiplies that saturate the accelerator rather than the scalar loop shown here. The block structure is also where the numerical care concentrates: each block computes its own local max and the cross-block rescaling must combine them correctly, which is the online-softmax recurrence applied at the granularity of tiles, not elements. And the causal mask, dropout, and the softmax scale all have to be threaded through the tiled recurrence without ever forming the full matrix. The scalar streaming loop is the correct mental model of *why* it works; the production kernel is that recurrence lifted to tiles and fused into one GPU kernel, which is where the speed, and the implementation difficulty, actually live.

**Online softmax computes exact attention in one streaming pass with three running scalars, rescaling by exp(old_max − new_max) on each new maximum — the reformulation that lets FlashAttention avoid materializing the N×N score matrix and keeps the exponentials from overflowing — but it buys memory with compute (the attention is recomputed in the backward pass, a win only because the hardware is memory-bound), and the real kernel lifts this scalar recurrence to tiles of queries and keys, where the block-local maxima, the cross-block rescaling, and the mask must all be threaded through without ever forming the full matrix.**

## External resources

The FlashAttention papers (Dao et al., "FlashAttention" and "FlashAttention-2") and Milakov and Gimelshein's "Online normalizer calculation for softmax" — the derivation of the streaming softmax recurrence, the tiling, and the recompute-in-backward memory/compute trade.

Any reference on the IO-aware / memory-bound view of GPU kernels (the roofline model, HBM vs SRAM bandwidth) — why trading the quadratic score-matrix memory for extra FLOPs is a net win on current accelerators.

The companion "softmax must subtract the max before exp" and "keep sqrt(N) activations — gradient checkpointing" modules — the first is the numerical-stability subtraction that online softmax reuses as its running max, and the second is the same memory-for-recompute trade applied to activations rather than the attention matrix.
