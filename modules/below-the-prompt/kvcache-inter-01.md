---
id: kvcache-inter-01
title: The KV cache — reuse the past, and match the recompute exactly
topic: below-the-prompt
level: intermediate
status: ready
time: 8-10h
summary: Generating a token runs attention over the whole sequence so far, and doing it from scratch rebuilds every prefix key and value each step — 15 key/value builds for a 5-token sequence, growing with the square of length. Cache each position's key and value the first time and reuse them and it is 5 builds, linear, with byte-identical outputs. The classic bug — attend before appending the current token's key/value — still runs and still returns a vector, but every step after the first is wrong, because position t never attends to itself.
eli5: Re-reading the whole book each time you turn a page is slow; remembering what you already read is fast. Keep a running memory of every earlier token so each new one is cheap — but if you check your memory before writing down the current token, the current one is missing, and the answer is quietly wrong.
---

## Why this module

The last two modules cut text into tokens and built attention over a fixed sequence. Generation is different: the sequence grows one token at a time, and at every step the model runs attention over everything so far to produce the next token. The scan lists the KV cache among the internals with "zero implementation," and it is the single optimization that makes generation practical — without it, producing a long response is quadratic in length, re-doing all the earlier work at every step. This is the third tiny rebuild, and it comes with a correctness constraint as sharp as the causal mask: the fast path must produce exactly what the slow path would.

The idea is simple and the bug is subtle. Each position's key and value depend only on that position, so once computed they never change — a token's key at step 5 is the same key it had at step 3. The from-scratch path ignores this and rebuilds every prefix key and value at every step; the cache stores them once and reuses them, turning quadratic work into linear. But a cache is shared mutable state threaded through a loop, and the classic mistake — attending over the cache *before* appending the current token — produces a model that runs cleanly, returns a plausible vector, and is wrong at every step, because the newest position never sees itself. There is no crash to catch it; only a comparison against the from-scratch result.

You need `attention-inter-01` — this reuses its scaled-dot-product attention, now driven left to right. Everything is plain Python, stdlib only, `$0.00`. The instinct to unlearn is that an optimization is correct because it is faster and returns output. A cache is correct only if it matches the thing it replaces, token for token, and proving that match is the whole discipline.

Here is the cache doing strictly less work and matching exactly:

```
# modules/below-the-prompt/code/kvcache-inter-01/ — COMPLETE, run from that directory
$ python3 kv.py --cached

CACHED — append one KV per step, reuse the rest
------------------------------------------------------------
  step 0: 1 new KV, attend over 1 cached  -> output matches scratch: True
  step 2: 1 new KV, attend over 3 cached  -> output matches scratch: True
  step 4: 1 new KV, attend over 5 cached  -> output matches scratch: True
  total KV builds = 5 vs 15 from scratch -- linear, not quadratic.
```

run: 2026-08-25 · deterministic; token vectors are a fixture · seq_len=5, dim=4 · `python3 kv.py --cached`

Five key/value builds instead of fifteen, and every step's output identical to recomputing from scratch. This module is that three-to-one saving, why it grows with length, and the one-line bug that gives it up.

## Concepts

Named here so you can find them again; each is built below.

- **Key / value** — per position, the vectors attention reads; they depend only on that position, so they never change once computed.
- **From-scratch generation** — rebuild every prefix key and value at each step. Correct, and quadratic.
- **KV cache** — store each position's key and value once and reuse them; one new pair per step.
- **Linear vs quadratic** — cached work grows with length; from-scratch work grows with length squared.
- **Cache correctness** — the cached outputs must equal the from-scratch outputs, exactly.
- **The append-order bug** — attending before appending the current token, so a position never attends to itself.

## Worked example

Source: the below-the-prompt track's anatomy material on the KV cache, rebuilt as runnable code, and `agent/agent/core/loop.py`'s notion of a checkpointed generation state (the cache is the per-turn state generation carries forward). The sequence and its vectors are the same fixture as the attention module.

Script and fixture: `modules/below-the-prompt/code/kvcache-inter-01/` — `kv.py`, and `seq.json`, five tokens with a 4-dimensional vector each. Every command runs from there.

### The frame: a running total, not a re-count

Imagine a cashier totalling a basket. The slow way is to re-add every item from the start each time a new item is scanned: one addition for the first item, two for the second, three for the third — the work grows with the square of the basket. The fast way is a running total: add only the new item to what you already had. Same answer, far less work, and the saving grows the longer the basket.

Attention during generation is the basket. Each token's key and value are its "price" — fixed the moment it is scanned. The from-scratch path re-computes every price at every step; the cache keeps a running list and adds only the new one. The catch is the running total's discipline: you must add the current item *before* you read the total, or the total is missing the thing you just scanned. That ordering is the entire bug at the end of this module.

### Attention over a prefix

The primitive is one position attending over a set of keys and values — the same scaled-dot-product attention from the last module.

```
# kv.py:46-52 — COMPLETE (one position's attention over given keys/values)
def attend(query, keys, values):
    """One position's attention over a set of key/value vectors: scaled dot-product
    scores, softmax, weighted blend of values."""
    d = len(query)
    sc = [dot(query, k) / sqrt(d) for k in keys]
    w = softmax(sc)
    return [sum(w[j] * values[j][c] for j in range(len(values))) for c in range(d)]
```

Generation calls this once per new token, over the prefix so far. The only question is where the keys and values come from — rebuilt, or remembered.

### From scratch: rebuild everything, every step

The naive generator rebuilds the whole prefix's keys and values at each step and attends. It is correct and it is wasteful.

```
# kv.py:57-65 — COMPLETE (rebuild the prefix's KV every step)
def recompute(emb):
    """No cache: at each step t, (re)build keys/values for the whole prefix 0..t and
    attend. Returns the per-step outputs and the number of key/value builds."""
    outputs, kv_builds = [], 0
    for t in range(len(emb)):
        keys = values = emb[: t + 1]           # rebuilt from scratch every step
        kv_builds += t + 1                      # ...at a cost of t+1 KV each step
        outputs.append(attend(emb[t], keys, values))
    return outputs, kv_builds
```

Count the cost and the quadratic shows immediately:

```
# $ python3 kv.py --recompute
#   step 0: attend over 1 position(s), rebuilt 1 KV  (cumulative 1)
#   step 1: attend over 2 position(s), rebuilt 2 KV  (cumulative 3)
#   step 2: attend over 3 position(s), rebuilt 3 KV  (cumulative 6)
#   step 3: attend over 4 position(s), rebuilt 4 KV  (cumulative 10)
#   step 4: attend over 5 position(s), rebuilt 5 KV  (cumulative 15)
#   total KV builds = 15 for 5 tokens -- grows with the square of length.
```

run: 2026-08-25 · fixture · `python3 kv.py --recompute`

Fifteen builds for five tokens: 1 + 2 + 3 + 4 + 5, the sum that equals n(n+1)/2. At a thousand tokens that is half a million rebuilds, and almost every one recomputes a key that has not changed since the token was first seen.

<svg viewBox="0 0 700 190" role="img" aria-label="Cumulative key/value builds by step. From-scratch: 1, 3, 6, 10, 15 — a curve bending upward (quadratic). Cached: 1, 2, 3, 4, 5 — a straight line.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">cumulative KV builds — from-scratch bends up, cached is straight</text>
    <line x1="60" y1="160" x2="640" y2="160" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="160" stroke="var(--grid)"></line>
    <polyline points="100,150 220,132 340,104 460,66 580,30" fill="none" stroke="var(--s2)" stroke-width="2"></polyline>
    <g fill="var(--s2)"><circle cx="100" cy="150" r="3"></circle><circle cx="220" cy="132" r="3"></circle><circle cx="340" cy="104" r="3"></circle><circle cx="460" cy="66" r="3"></circle><circle cx="580" cy="30" r="3"></circle></g>
    <text x="590" y="30" fill="var(--s2)" font-size="8">15 (scratch)</text>
    <polyline points="100,150 220,144 340,138 460,132 580,126" fill="none" stroke="var(--s1)" stroke-width="2"></polyline>
    <g fill="var(--s1)"><circle cx="100" cy="150" r="3"></circle><circle cx="220" cy="144" r="3"></circle><circle cx="340" cy="138" r="3"></circle><circle cx="460" cy="132" r="3"></circle><circle cx="580" cy="126" r="3"></circle></g>
    <text x="590" y="126" fill="var(--s1)" font-size="8">5 (cached)</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="100" y="175">t0</text><text x="340" y="175">t2</text><text x="580" y="175">t4</text></g>
  </g>
</svg>
^ The two costs diverge as the sequence grows: from-scratch bends upward with the square of length, cached stays a straight line. On five tokens the gap is 15 versus 5; on a thousand it is half a million versus a thousand.

### The cache: append, then attend

The cache keeps the keys and values it has already built and appends one per step. Note the order — append the current token *first*, then attend over the cache.

```
# kv.py:70-79 — COMPLETE (append the new KV, then attend over the cache)
def cached(emb):
    """With a KV cache: append the new token's key/value, then attend over the cache.
    One KV build per step. Must match recompute() exactly."""
    ck, cv, outputs, kv_builds = [], [], [], 0
    for t in range(len(emb)):
        ck.append(emb[t])                       # append current token FIRST
        cv.append(emb[t])
        kv_builds += 1                          # one new KV per step
        outputs.append(attend(emb[t], ck, cv))
    return outputs, kv_builds
```

The `--cached` output from the cold open confirms both halves: every step's output matches the from-scratch result, and the total is 5 builds instead of 15. The cache is not an approximation — it is the identical computation with the redundant rebuilds removed, which is exactly why it is safe to use.

<svg viewBox="0 0 700 150" role="img" aria-label="The cache at step 3: keys/values for tokens 0,1,2 are already stored (reused); token 3's key/value is appended (one new build); then position 3 attends over all four. Earlier steps' values are reused, not recomputed.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">step 3: reuse cached KV for 0,1,2; build only token 3; attend over all four</text>
    <g>
      <rect x="60" y="40" width="60" height="28" rx="4" fill="var(--s1)" opacity="0.4"></rect><text x="76" y="58" fill="var(--ink)">KV 0</text>
      <rect x="130" y="40" width="60" height="28" rx="4" fill="var(--s1)" opacity="0.4"></rect><text x="146" y="58" fill="var(--ink)">KV 1</text>
      <rect x="200" y="40" width="60" height="28" rx="4" fill="var(--s1)" opacity="0.4"></rect><text x="216" y="58" fill="var(--ink)">KV 2</text>
      <rect x="270" y="40" width="60" height="28" rx="4" fill="var(--s1)"></rect><text x="284" y="58" fill="var(--panel)">KV 3</text>
      <text x="340" y="58" fill="var(--s1)">&lt;- 1 new build</text>
      <text x="60" y="86" fill="var(--muted)" font-size="8">reused (already in cache)</text>
    </g>
    <line x1="90" y1="100" x2="300" y2="100" stroke="var(--muted)"></line>
    <text x="60" y="124" fill="var(--ink)">query 3 attends over cache[0..3] -> output for position 3</text>
  </g>
</svg>
^ At each step only the newest key/value is built; the earlier ones are read straight from the cache. The blend still runs over the whole prefix — the saving is in not *rebuilding* the prefix, not in attending to less of it.

### The bug: attend before you append

The cache is mutable state in a loop, and the order of two lines decides correctness. Attend *before* appending the current token and position t attends only to 0..t−1 — it never sees itself.

```
# kv.py:82-93 — COMPLETE (the off-by-one: attend, then append)
def cached_buggy(emb):
    """THE BUG: attend over the cache BEFORE appending the current token, so position
    t never attends to itself. Still runs, still returns a vector -- just wrong."""
    ck, cv, outputs = [], [], []
    for t in range(len(emb)):
        if not ck:                              # t=0: nothing cached yet
            outputs.append(list(emb[t]))        # degenerate: emit the token as-is
        else:
            outputs.append(attend(emb[t], ck, cv))   # attends 0..t-1, misses self
        ck.append(emb[t])                       # append AFTER (the off-by-one)
        cv.append(emb[t])
    return outputs, 0
```

It runs without error and returns a vector at every step — and every step after the first is wrong:

```
# $ python3 kv.py --bug
#   step 0: matches from-scratch = True
#   step 1: matches from-scratch = False
#   step 2: matches from-scratch = False
#   step 3: matches from-scratch = False
#   step 4: matches from-scratch = False
```

run: 2026-08-25 · fixture · `python3 kv.py --bug`

Step 0 matches only by degeneracy — with an empty cache there is nothing to get wrong. From step 1 on, every position's output is missing its own token's contribution, so the representation that predicts the next token is subtly, consistently wrong. This is the worst kind of bug: no exception, plausible-looking outputs, and a model that quietly generates worse text. The only thing that catches it is the comparison the cache must always pass.

<svg viewBox="0 0 700 150" role="img" aria-label="At step 3, the correct cache attends over KV 0,1,2,3 including the current token. The buggy cache attends over KV 0,1,2 only because it appends token 3 after attending, so position 3 never sees itself.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--s1)">correct: append 3, then attend over 0,1,2,3</text>
    <g>
      <rect x="40" y="30" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="55" y="46" fill="var(--ink)">KV0</text>
      <rect x="90" y="30" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="105" y="46" fill="var(--ink)">KV1</text>
      <rect x="140" y="30" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="155" y="46" fill="var(--ink)">KV2</text>
      <rect x="190" y="30" width="46" height="24" rx="3" fill="var(--s1)"></rect><text x="203" y="46" fill="var(--panel)">KV3</text>
      <text x="250" y="46" fill="var(--s1)">self included -> correct</text>
    </g>
    <text x="20" y="90" fill="var(--s2)">buggy: attend over 0,1,2, THEN append 3</text>
    <g>
      <rect x="40" y="102" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="55" y="118" fill="var(--ink)">KV0</text>
      <rect x="90" y="102" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="105" y="118" fill="var(--ink)">KV1</text>
      <rect x="140" y="102" width="46" height="24" rx="3" fill="var(--s1)" opacity="0.4"></rect><text x="155" y="118" fill="var(--ink)">KV2</text>
      <rect x="190" y="102" width="46" height="24" rx="3" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="203" y="118" fill="var(--s2)">KV3?</text>
      <text x="250" y="118" fill="var(--s2)">self missing -> wrong, no error</text>
    </g>
  </g>
</svg>
^ Same step, two append orders. Appending before attending puts the current token in the cache in time; appending after leaves position 3 attending over only 0,1,2 — self absent, output wrong, nothing raised.

**A KV cache is correct only if its output is byte-identical to recomputing from scratch — so test the fast path against the slow one, because an off-by-one cache still runs and still returns a plausible, wrong answer.**

### The running tally

| generation | KV builds (n=5) | growth | matches from-scratch |
|---|---|---|---|
| from scratch | 15 | quadratic | — (it is the reference) |
| cached (append then attend) | 5 | linear | yes, every step |
| cached (attend then append) | 5 | linear | no, every step after 0 |

The outputs the cache must produce never changed; only whether the work was reused, and whether the current token was in the cache when it mattered. The cache buys a quadratic-to-linear speedup for free *if* it is exact, and the exactness is not automatic — it hangs on an append happening before an attend. The self-test is the guardrail:

```
# $ python3 kv.py --check
#   cached output == from-scratch output at every step = True
#   the off-by-one cache differs from from-scratch = True
#   cached KV builds = 5 (== n) ; scratch = 15 (== n(n+1)/2) = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 kv.py --check`

### What we did not settle

The fixture uses identity projections and re-attends over the full cache each step, so the math is visible. Real systems add details that do not change the lesson: keys and values are learned projections, not the raw embedding, but they still depend only on their position, which is why caching is valid; the cache has a memory cost that grows linearly with sequence length, so very long contexts trade compute for memory and motivate tricks like paged or windowed caches; and at generation time the causal mask from the previous module is implicit — you only ever cache and attend to the past, never the future, so the mask and the cache are two views of the same "past only" rule. The dial here is one cache over a short sequence; the engineering around it is managing that cache's memory at scale.

## Build

The pipeline in one paragraph: generate left to right, and at each step compute the new token's key and value once, append them to a cache, and attend over the cache; keep a from-scratch recompute path and assert the two produce identical outputs before you trust the cache; and count the key/value builds to confirm the cached path is linear where the recompute is quadratic. Never ship a KV cache without a byte-for-byte equivalence test against the recompute.

We opened on the saving. The rule that makes it safe:

```
# modules/below-the-prompt/code/kvcache-inter-01/ — COMPLETE, run from that directory
$ python3 kv.py --check
  cached output == from-scratch output at every step = True
```

Now build your own cache. Generate a short sequence both ways — rebuilding the prefix each step, and with a cache — and assert the outputs match at every step. Your number to beat is **zero difference between cached and from-scratch outputs**, at which point the KV-build counts show the linear-versus-quadratic gap for free. Swap the append and attend lines and confirm the equivalence test fails from step 1. Bring back the two build counts and the passing (then failing) equivalence check. Good luck.

## Definition of done

- [ ] Left-to-right generation with a from-scratch recompute path and a KV-cache path
- [ ] A cache that appends the new token's key/value before attending over the cache
- [ ] A byte-for-byte equivalence assertion between the cached and from-scratch outputs at every step
- [ ] Key/value build counts showing the cached path linear and the recompute quadratic
- [ ] The append-order bug kept for contrast, so the silent wrongness is visible
- [ ] `python3 kv.py --check` printing SELF-TEST PASS: cached matches, the bug differs, cost is linear vs quadratic
- [ ] The two build counts recorded, and confirmation the equivalence test catches the off-by-one
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Producing n tokens from scratch costs on the order of n-squared key/value builds. Explain where the square comes from and what the cache removes.
2. Why is it valid to reuse a token's key and value from an earlier step without recomputing them?
3. The buggy cache runs cleanly and returns a vector at every step but is wrong from step 1. State the one-line cause and what each position fails to attend to.
4. Why is "it is faster and returns output" not evidence a cache is correct, and what is?
5. Your own cache was tested against the recompute. What were the two build counts, and did swapping append and attend break the equivalence?

## External resources

- Karpathy, *Let's build GPT: from scratch* — https://www.youtube.com/watch?v=kCc8FmEb1nY — my summary: builds a causal transformer and discusses the KV cache as the generation-time optimization; watch it for how the cache extends the causal attention of the previous module into fast autoregressive decoding.
- *Efficient Memory Management for LLM Serving with PagedAttention* (vLLM) — https://arxiv.org/abs/2309.06180 — my summary: the systems paper on managing the KV cache's memory at scale, which this module's "what we did not settle" points at; read it for why the cache's linear memory growth is the real production constraint.
- This hub, *attention-inter-01* — modules/below-the-prompt/attention-inter-01.md — my summary: the scaled-dot-product attention and causal mask this cache accelerates; read it first, since the cache is just that attention with the past reused instead of rebuilt.
