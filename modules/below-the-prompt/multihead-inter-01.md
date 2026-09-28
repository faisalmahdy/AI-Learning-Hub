---
id: multihead-inter-01
title: Split attention into several heads — one head is a single weighted average and cannot retrieve two things at once
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: An attention head does one thing: it scores every token against the query, softmaxes the scores into a distribution, and returns the weighted average of the tokens' value vectors. The output of one head is therefore a convex combination of the value vectors — a single point inside their convex hull — and that is a real limitation. If the query needs information from two different tokens for two different reasons (a subject and its object, an article and the verb it governs), one head cannot do it cleanly, because one softmax can only be in one place: it can spread weight across both targets, but then it returns the average of the two, a blend that is neither, and the two distinct pieces of information collapse into their midpoint. Multi-head attention removes the limit by running several heads in parallel, each with its own scores and softmax, and concatenating their outputs — so head A attends fully to the subject and head B fully to the object, both retrieved at full strength and kept distinct in different slots of the output. Each head works in a lower-dimensional subspace (the model dimension is split among them), so several parallel lookups cost about the same as one full-width head. On a fixture where the query needs signal A (token 0's [1,0]) and signal B (token 2's [0,1]), a single head forced to cover both splits its weight and returns [0.5, 0.5] — each signal recovered at only 0.5, blended and inseparable — while two heads attend one to each, returning [1,0] and [0,1] that recover A and B at full strength 1.0.
eli5: Imagine you have one spotlight and you need to light up two people on opposite sides of a stage at the same time. With a single spotlight you have to point it at the middle, so both people are only half-lit and you can't really see either clearly. The fix isn't a brighter spotlight — it's TWO spotlights, one aimed at each person, so both are fully lit. An attention head is like a spotlight: it can only aim at one place at a time and gives you a blur if you make it cover two. Multiple heads are multiple spotlights, each aimed at a different thing the model needs to see, all at once.
---

## Why this module

The elegant thing about an attention head — average the values, weighted by relevance — is also its ceiling. A weighted average is a single point: no matter how you set the weights, one head's output lands somewhere inside the cloud of value vectors, and it can only land in one place. That is fine when the query needs one thing. It fails the moment the query needs two unrelated things at once, which in language is constantly — the word that fixes a verb's tense and the word that fixes its subject are different words, and a single averaged lookup that tries to grab both grabs the point halfway between them, which encodes neither. The limitation is not that the head is imprecise; it is that one distribution has one answer.

The output of one head is a convex combination of the value vectors — a single point inside their convex hull. If the query needs information from two different tokens for two different reasons, one head cannot do it cleanly, because one softmax can only be in one place: it can spread its weight across both targets, but then it returns the average of the two, a blend that is neither, and the two distinct pieces of information collapse into their midpoint.

Multi-head attention removes the limitation by running several heads in parallel, each with its own scores and its own softmax, and concatenating their outputs. Head A attends fully to one target and head B fully to the other, and because their outputs occupy different slots, both are retrieved at full strength and kept distinct — several independent lookups at roughly the cost of one, since the model dimension is split among the heads. This module runs a single head against two.

**Use multiple attention heads, because one head is a single softmax that returns one weighted average of the value vectors — a convex blend that collapses two distinct retrievals into their midpoint — while several heads run independent distributions in parallel and concatenate, so the model can attend to different tokens for different reasons and keep the results separate.**

## Concepts

**A head's output is the weighted average of the value vectors** under its softmax distribution — a single convex combination.

```python filename=modules/below-the-prompt/code/multihead-inter-01/multihead.py:53-56 COMPLETE
def weighted_average(weights, values):
    """One attention head's output: the weighted average of the value vectors under the softmax distribution `weights`."""
    dim = len(values[0])
    return [sum(w * v[k] for w, v in zip(weights, values)) for k in range(dim)]
```

**We measure how strongly an output carries a signal** by projecting it onto that signal's direction — 1.0 means fully retrieved, 0 means absent.

```python filename=modules/below-the-prompt/code/multihead-inter-01/multihead.py:59-62 COMPLETE
def recovery(output, signal):
    """How strongly `output` carries `signal`: the projection of output onto the unit signal direction."""
    norm2 = sum(s * s for s in signal)
    return sum(o * s for o, s in zip(output, signal)) / norm2
```

<svg role="img" aria-label="Value vectors A at (1,0) and B at (0,1); a single head's output is the midpoint (0.5,0.5) between them, while two heads output A and B separately at the corners" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one head = one point (the blend); two heads = two points</text>
  <line x1="40" y1="100" x2="40" y2="24" stroke="var(--grid)"/><line x1="40" y1="100" x2="120" y2="100" stroke="var(--grid)"/>
  <circle cx="120" cy="100" r="3" fill="var(--s1)"/><text x="122" y="102" fill="var(--s1)" font-size="7">A [1,0]</text>
  <circle cx="40" cy="30" r="3" fill="var(--s1)"/><text x="44" y="30" fill="var(--s1)" font-size="7">B [0,1]</text>
  <line x1="120" y1="100" x2="40" y2="30" stroke="var(--line)" stroke-dasharray="2 2"/>
  <circle cx="80" cy="65" r="4" fill="var(--s2)"/><text x="86" y="66" fill="var(--s2)" font-size="7">single head [0.5,0.5] (neither)</text>
  <text x="150" y="40" fill="var(--muted)" font-size="7">single head can only land ON this line —</text>
  <text x="150" y="52" fill="var(--muted)" font-size="7">one point between the values.</text>
  <text x="150" y="72" fill="var(--s1)" font-size="7">two heads output A and B at the</text>
  <text x="150" y="84" fill="var(--s1)" font-size="7">corners — both, kept separate.</text>
</svg>
^ A single head's output is a convex combination of the values, so it can only land on the line between A and B — its attempt to cover both is the midpoint [0.5,0.5], which is neither; two heads output A and B directly at the corners, retrieving both at full strength.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/multihead-inter-01/multihead.py

The fixture is three tokens' values (token 0 carries signal A, token 2 carries signal B) and the per-head attention weights.

```json filename=modules/below-the-prompt/code/multihead-inter-01/multihead.json:3-8 COMPLETE
  "values": [[1, 0], [0, 0], [0, 1]],
  "single_head_weights": [0.5, 0.0, 0.5],
  "head_a_weights": [1.0, 0.0, 0.0],
  "head_b_weights": [0.0, 0.0, 1.0],
  "signal_a": [1, 0],
  "signal_b": [0, 1]
```

Run `--attend`.

```text filename=--attend
ATTEND — one head's blended output vs two heads' separate outputs
------------------------------------------------------------
  values: [[1, 0], [0, 0], [0, 1]]  (token 0 = signal A, token 2 = signal B)
  SINGLE head weights [0.5, 0.0, 0.5] -> output [0.5, 0.5]
  TWO heads:
    head A weights [1.0, 0.0, 0.0] -> output [1.0, 0.0]
    head B weights [0.0, 0.0, 1.0] -> output [0.0, 1.0]
    concatenated -> [1.0, 0.0, 0.0, 1.0]
```

<svg role="img" aria-label="Two heads each produce a two-dimensional output; they are concatenated into a four-dimensional vector where head A occupies the first two slots and head B the last two, keeping both signals in separate slots" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">heads write to separate slots of the concatenated output</text>
  <rect x="20" y="26" width="50" height="18" fill="var(--s1)"/><text x="30" y="39" fill="var(--panel)" font-size="7">head A</text>
  <text x="24" y="56" fill="var(--muted)" font-size="6">[1, 0]</text>
  <rect x="90" y="26" width="50" height="18" fill="var(--s2)"/><text x="100" y="39" fill="var(--panel)" font-size="7">head B</text>
  <text x="94" y="56" fill="var(--muted)" font-size="6">[0, 1]</text>
  <text x="150" y="39" fill="var(--muted)" font-size="8">→ concat →</text>
  <rect x="216" y="26" width="34" height="18" fill="var(--s1)"/><rect x="250" y="26" width="34" height="18" fill="var(--s2)"/>
  <text x="222" y="39" fill="var(--panel)" font-size="7">1  0</text><text x="256" y="39" fill="var(--panel)" font-size="7">0  1</text>
  <text x="216" y="56" fill="var(--muted)" font-size="6">A's slots</text><text x="252" y="56" fill="var(--muted)" font-size="6">B's slots</text>
  <text x="20" y="80" fill="var(--muted)" font-size="6">both signals survive because they live in different slots — no averaging between them</text>
</svg>
^ Head A's output [1,0] and head B's output [0,1] are concatenated into [1,0,0,1], where A occupies the first two slots and B the last two — the signals never share a slot, so neither is averaged into the other, which is exactly what a single head's shared output cannot achieve.

The query needs both signal A (token 0's value [1,0]) and signal B (token 2's value [0,1]). The single head has one distribution to work with, and to include both targets it splits its weight 0.5/0.5 between tokens 0 and 2 — there is no other option, since a probability distribution that ignores neither must divide its mass. The result is [0.5, 0.5], the midpoint of A and B. That output is genuinely ambiguous: it looks the same as a head that attended weakly to something in the middle, and neither signal is present at full strength. The two heads each get their own distribution: head A puts all its weight on token 0 and outputs [1,0] (pure A), head B puts all its weight on token 2 and outputs [0,1] (pure B). Concatenated, the layer's output is [1,0,0,1], which contains both signals, in separate slots, at full strength. One head had to choose or blend; two heads did not have to choose.

## Build

Quantify what "blended" costs by measuring how much of each signal survives.

```text filename=--recover
RECOVER — how strongly each signal is retrieved (1.0 = full, 0 = absent)
----------------------------------------------------------
  single head output [0.5, 0.5]:
    signal A recovered = 0.5    signal B recovered = 0.5
  two heads (A output [1.0, 0.0], B output [0.0, 1.0]):
    signal A recovered = 1.0    signal B recovered = 1.0
```

Projecting each output onto the signal directions puts a number on the loss. The single head recovers signal A at 0.5 and signal B at 0.5 — each is present at only half strength, and the downstream layers receive a muddled vector that half-remembers two things instead of clearly carrying either. The two heads recover A at 1.0 and B at 1.0 — each signal is fully present. The 0.5 is not a coincidence of this fixture; it is the structural cost of forcing one convex combination to cover two targets: the best a single point can do to represent two equally-needed vectors is sit at their average, which is exactly half of each. Adding more targets makes it worse — a single head asked to gather k things splits to roughly 1/k of each — while adding heads keeps each retrieval whole. This is why the number of heads matters: it is the number of independent things the layer can look up about a token at once, and a model with too few heads is bottlenecked not on how well it can attend but on how many distinct relationships it can attend to simultaneously.

```python filename=modules/below-the-prompt/code/multihead-inter-01/multihead.py:107-115 COMPLETE
    single_blends = single == [0.5, 0.5]
    print("  single head output is the blend (midpoint) of A and B = %s (%s)" % (single_blends, single))

    single_half_each = recovery(single, sa) == 0.5 and recovery(single, sb) == 0.5
    print("  single head recovers each signal at only 0.5 = %s (A %.1f, B %.1f)"
          % (single_half_each, recovery(single, sa), recovery(single, sb)))

    twohead_recovers_a = recovery(head_a, sa) == 1.0
    print("  head A recovers signal A at full strength = %s (%.1f)" % (twohead_recovers_a, recovery(head_a, sa)))
```

## Definition of done

The self-test pins the single head's blend and half-strength recovery against the two heads' full, separate retrievals.

```python filename=modules/below-the-prompt/code/multihead-inter-01/multihead.py:117-121 COMPLETE
    twohead_recovers_b = recovery(head_b, sb) == 1.0
    print("  head B recovers signal B at full strength = %s (%.1f)" % (twohead_recovers_b, recovery(head_b, sb)))

    twohead_beats_single = min(recovery(head_a, sa), recovery(head_b, sb)) > min(recovery(single, sa), recovery(single, sb))
    print("  two heads' weakest recovery beats the single head's = %s (%.1f > %.1f)"
          % (twohead_beats_single, min(recovery(head_a, sa), recovery(head_b, sb)), min(recovery(single, sa), recovery(single, sb))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — one head blends the two signals to their midpoint; two heads retrieve both at full strength
--------------------------------------------------------------------------------------------------------
  single head output is the blend (midpoint) of A and B = True ([0.5, 0.5])
  single head recovers each signal at only 0.5 = True (A 0.5, B 0.5)
  head A recovers signal A at full strength = True (1.0)
  head B recovers signal B at full strength = True (1.0)
  two heads' weakest recovery beats the single head's = True (1.0 > 0.5)
```

<svg role="img" aria-label="Recovery of the two signals: single head recovers A and B at 0.5 each, two heads recover A and B at 1.0 each" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">signal recovery: single 0.5 each, two heads 1.0 each</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">single, A</text>
  <rect x="80" y="26" width="75" height="10" fill="var(--s2)"/><text x="159" y="35" fill="var(--muted)" font-size="7">0.5</text>
  <text x="10" y="48" fill="var(--muted)" font-size="7">single, B</text>
  <rect x="80" y="40" width="75" height="10" fill="var(--s2)"/><text x="159" y="49" fill="var(--muted)" font-size="7">0.5</text>
  <line x1="14" y1="56" x2="286" y2="56" stroke="var(--grid)"/>
  <text x="10" y="72" fill="var(--muted)" font-size="7">2 heads, A</text>
  <rect x="80" y="64" width="150" height="10" fill="var(--s1)"/><text x="234" y="73" fill="var(--muted)" font-size="7">1.0</text>
  <text x="10" y="86" fill="var(--muted)" font-size="7">2 heads, B</text>
  <rect x="80" y="78" width="150" height="10" fill="var(--s1)"/><text x="234" y="87" fill="var(--muted)" font-size="7">1.0</text>
</svg>
^ The single head recovers each of the two signals at only 0.5 (the structural cost of one convex combination covering two targets), while two heads recover each at the full 1.0 — the extra head, not extra width, is what restores the missing half.

**Done means the head bottleneck is proven on real vectors: a single head forced to cover both targets returns the midpoint [0.5, 0.5] and recovers each signal at only 0.5, while two heads attend one to each, returning [1,0] and [0,1] that recover both signals at 1.0 — so attention must be split into multiple heads to make several independent retrievals at once instead of one blended average.**

## Boss fight

Predict two ways the head story is more subtle than "more heads is strictly better," because heads trade against per-head capacity and are not all doing independent work.

The first trap is that heads are carved out of a fixed model dimension, so more heads means each head is narrower — there is a trade-off between the NUMBER of heads and the CAPACITY of each. The model dimension d is split across h heads, so each head operates in a d/h-dimensional subspace; double the heads and each head has half the dimensions to represent its keys, queries, and values. Push this too far and each head is too low-dimensional to represent a useful similarity — with a 1-dimensional head, a query can barely distinguish tokens at all. So the choice of head count is a balance: enough heads to make the distinct parallel lookups the task needs, but each head wide enough to make a meaningful lookup, and the right number depends on the model size and the task, not "as many as possible." This is why models specify both d and h and keep d/h in a sensible range (often 64 or 128), rather than maximizing h. The clean [1,0]/[0,1] retrieval in this fixture worked because the signals were axis-aligned in a 2-D space; a real head needs enough width to separate the directions it must tell apart.

The second trap is that heads are not guaranteed to specialize, and in practice many are redundant, so head count is an upper bound on parallel lookups, not a count of useful ones. Nothing forces head A and head B to attend to different things — they are initialized differently and learn from gradients, and they often converge on overlapping or duplicative attention patterns, so a 12-head layer may carry far fewer than 12 independent relationships. Research on pruning heads has shown that many heads can be removed after training with little loss, precisely because they were redundant; conversely, a few heads sometimes do most of the important work (induction heads, syntactic heads). This has two implications: adding heads has diminishing returns once you have enough for the distinct relationships that matter, and the effective capacity of multi-head attention is the number of *distinct* patterns the heads actually learn, not the nominal head count. It also connects to variants like grouped-query attention, which deliberately share key/value projections across heads (trading some independence for a smaller KV cache) on the bet that the heads did not all need fully independent keys and values anyway. So the honest picture is: heads give the model the *capacity* for parallel, distinct lookups, the task and training determine how much of that capacity is used, and the design job is to provide enough heads of enough width for the relationships that matter while not paying for redundancy.

**Heads trade against per-head width: the model dimension is split across them, so more heads means each works in a smaller subspace and can represent a coarser similarity — keep d/h wide enough (often 64–128) for each lookup to be meaningful rather than maximizing head count. And heads are not guaranteed to specialize: nothing forces them to attend to different things, many learn redundant patterns (which is why heads can often be pruned), so head count is an upper bound on parallel lookups, not a count of useful ones — provide enough heads of enough width for the distinct relationships that matter, and expect diminishing returns and redundancy beyond that.**

## External resources

The "Attention Is All You Need" paper and the Illustrated/annotated Transformer write-ups — the definition of scaled dot-product attention and multi-head attention, why the model dimension is split across heads, and how the heads are concatenated and projected.

Research on what attention heads learn and head redundancy (analyses of induction and syntactic heads, and "Are Sixteen Heads Really Better than One?" on head pruning) — evidence that heads specialize unevenly and that many are prunable, plus grouped-query attention as a capacity/cost trade-off.

The companion attention-scale, causal-mask, and grouped-query-attention modules in this topic — multi-head is the structure those refine: the √d_k scaling stabilizes each head's softmax, the causal mask constrains what each head may attend to, and GQA shares keys and values across heads to shrink the cache built on this multi-head design.
