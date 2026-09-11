---
id: retrieval-inter-17
title: Pack the context by score-per-token — or one fat high-score chunk crowds out two lean ones
topic: context-and-retrieval
level: intermediate
status: ready
time: 20 min
summary: Retrieval returns more chunks than fit in the context window, so you select a subset under a fixed token budget. The obvious rule — keep the highest-scoring chunks — is greedy by raw relevance, and it wastes the window: a single long top-scoring chunk eats most of the budget and blocks two shorter chunks whose combined relevance is higher. Ranking by value density (score per token) fixes it. On a 10-token budget, greedy-by-score takes chunk A (score 10, 9 tokens) and nothing else fits — total relevance 10. Greedy-by-density takes B then C (score 11, 10 tokens), fills the budget exactly, and matches the exhaustive optimum. Same chunks, same budget; density wins.
eli5: You have a small backpack and lots of things to pack, each worth some points and taking some space. Grabbing the single most valuable thing first can fill the bag so nothing else fits. If instead you grab the things worth the most points per unit of space, you fit more total value in the same bag. Packing a context window works the same way.
---

## Why this module

Retrieval always hands you more chunks than fit, so the real question is not "which chunks are good" but "which set of good chunks fits the window and holds the most relevance."

The context window is a fixed token budget. You have a pile of retrieved chunks, each with a relevance score from the reranker and a token length. You must pick a subset that fits. The rule most first-cut pipelines ship is the obvious one: sort by score, take from the top until the next chunk doesn't fit. That rule quietly wastes the budget. A single long, top-scoring chunk can eat most of the window and block two shorter chunks whose combined relevance is higher. You paid for a big window and filled it with less relevance than it could hold.

**Selecting chunks under a token budget is a packing problem, and raw score is the wrong sort key for packing.**

The fix is to rank by value density — score per token — not by raw score. A chunk that is slightly less relevant but half the length earns its place, because it leaves room for another chunk behind it. This module builds both selectors on one fixture, adds an exhaustive optimum to judge them against, and measures the gap.

## Concepts

The **budget** is the token window: the total length of the chunks you inject cannot exceed it. Here it is 10 tokens.

Each chunk has a **score** (relevance, higher is better) and a **token length** (its cost). Greedy-by-score sorts by score and takes greedily. Greedy-by-density sorts by **score divided by tokens** — how much relevance each token buys — and takes greedily.

This is the classic **knapsack** shape: maximize value (relevance) subject to a weight limit (tokens). Sorting by value-per-weight is the fractional-knapsack heuristic. It is not guaranteed optimal for the 0/1 knapsack — you cannot take half a chunk — but it dominates the naive "top scores win" rule and, on realistic chunk sets, comes very close to the true best.

The trap is that raw score ignores cost. A chunk scoring 10 looks twice as good as one scoring 5, but if it is nearly twice as long, it buys no more relevance per token — and by taking the whole window it forbids you from adding anything else. Density makes cost visible in the ranking.

**Density asks the question raw score can't: not how good is this chunk, but how good is it per token of budget it spends.**

The two sort keys disagree on order, and that disagreement is the whole story: A leads by score but trails by density.

<svg role="img" aria-label="By score the order is A, B, C; by density the order is B, A, C — A and B swap" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="25" fill="var(--muted)" font-size="9">by score</text>
  <text x="120" y="25" fill="var(--s1)" font-size="12" font-family="var(--mono)">A</text>
  <text x="160" y="25" fill="var(--ink)" font-size="12" font-family="var(--mono)">B</text>
  <text x="200" y="25" fill="var(--ink)" font-size="12" font-family="var(--mono)">C</text>
  <text x="118" y="40" fill="var(--muted)" font-size="8">10</text>
  <text x="158" y="40" fill="var(--muted)" font-size="8">6</text>
  <text x="198" y="40" fill="var(--muted)" font-size="8">5</text>
  <line x1="10" y1="60" x2="290" y2="60" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="85" fill="var(--muted)" font-size="9">by density</text>
  <text x="120" y="85" fill="var(--s2)" font-size="12" font-family="var(--mono)">B</text>
  <text x="160" y="85" fill="var(--ink)" font-size="12" font-family="var(--mono)">A</text>
  <text x="200" y="85" fill="var(--ink)" font-size="12" font-family="var(--mono)">C</text>
  <text x="114" y="100" fill="var(--muted)" font-size="8">1.20</text>
  <text x="154" y="100" fill="var(--muted)" font-size="8">1.11</text>
  <text x="194" y="100" fill="var(--muted)" font-size="8">1.00</text>
</svg>
^ A tops the score ranking but B tops the density ranking; taking the leader of each is what splits the two selections.

To know whether either heuristic is any good, compute the **exhaustive optimum** — try every subset, keep the highest-scoring one that fits. On three chunks that is eight subsets; on a real pile it is exponential, which is exactly why you use a cheap heuristic instead. The optimum here is a yardstick, not the production method.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/retrieval-inter-17/pack.py

The fixture is three chunks and a budget. Every selection is computed.

```json filename=modules/context-and-retrieval/code/retrieval-inter-17/chunks.json:1-9 COMPLETE
{
  "_meta": "Retrieved chunks, each with a relevance score (higher is better) and a token length. budget is the fixed token window the selected chunks must fit inside. The task: pick a subset that maximizes total relevance without exceeding the budget.",
  "budget": 10,
  "chunks": {
    "A": {"score": 10, "tokens": 9},
    "B": {"score": 6, "tokens": 5},
    "C": {"score": 5, "tokens": 5}
  }
}
```

The selector is one greedy loop parameterized by a sort key. Sort the chunks by that key descending, then take each one that still fits. Pass the score as the key and it is greedy-by-score; pass score-over-tokens and it is greedy-by-density — the identical loop, a different ranking.

```python filename=modules/context-and-retrieval/code/retrieval-inter-17/pack.py:41-61 COMPLETE
def greedy(chunks, budget, key):
    """Take chunks in descending order of key(name), skipping any that would overflow the budget."""
    order = sorted(chunks, key=lambda n: key(n), reverse=True)
    picked, used = [], 0
    for n in order:
        if used + chunks[n]["tokens"] <= budget:
            picked.append(n)
            used += chunks[n]["tokens"]
    return picked, used


def total_score(chunks, picked):
    return sum(chunks[n]["score"] for n in picked)


def by_score(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"])


def by_density(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"] / chunks[n]["tokens"])
```

Run `--pack` and the two selections sit side by side.

```text filename=--pack
PACK — select chunks under a 10-token budget
----------------------------------------------------------------
  chunk   score   tokens   score/token
  B           6       5       1.200
  A          10       9       1.111
  C           5       5       1.000
----------------------------------------------------------------
  by score:     A            tokens  9/10   total relevance 10
  by density:   B C          tokens 10/10   total relevance 11
----------------------------------------------------------------
  ranking by score-per-token fits more relevance into the same window.
```

By score, A wins first and consumes 9 of 10 tokens; B and C each need 5, so neither fits — the selection stops at total relevance 10 with a token wasted. By density, B (1.200 per token) and A (1.111) lead, but after B the budget has 5 tokens left, A's 9 don't fit, and C's 5 do — so density takes B then C for total relevance 11, filling the window exactly.

<svg role="img" aria-label="Budget bar of 10 tokens: by-score fills 9 with chunk A and leaves 1 empty; by-density fills 5 with B and 5 with C" viewBox="0 0 300 140" width="300" height="140">
  <text x="10" y="25" fill="var(--muted)" font-size="9">by score</text>
  <rect x="10" y="32" width="252" height="24" fill="none" stroke="var(--line)" stroke-width="1"/>
  <rect x="10" y="32" width="227" height="24" fill="var(--s1)"/>
  <text x="95" y="49" fill="var(--panel)" font-size="10">A · score 10</text>
  <text x="240" y="49" fill="var(--muted)" font-size="9">idle</text>
  <text x="10" y="90" fill="var(--muted)" font-size="9">by density</text>
  <rect x="10" y="97" width="252" height="24" fill="none" stroke="var(--line)" stroke-width="1"/>
  <rect x="10" y="97" width="126" height="24" fill="var(--s2)"/>
  <rect x="136" y="97" width="126" height="24" fill="var(--s1)"/>
  <text x="35" y="114" fill="var(--panel)" font-size="10">B · 6</text>
  <text x="165" y="114" fill="var(--panel)" font-size="10">C · 5</text>
  <text x="10" y="136" fill="var(--muted)" font-size="9">total relevance: by-score 10 · by-density 11 (window 10 tokens)</text>
</svg>
^ The same 10-token window: raw score fills it with one fat chunk and wastes a token; density fits two lean chunks and packs one more point of relevance.

## Build

Is density just lucky here, or did it actually find the best packing? Compute the exhaustive optimum — every subset that fits, keep the highest score — and compare.

```python filename=modules/context-and-retrieval/code/retrieval-inter-17/pack.py:64-74 COMPLETE
def optimum(chunks, budget):
    """Exhaustive best subset: the highest total score whose tokens fit the budget."""
    best, best_score = [], -1
    names = list(chunks)
    for r in range(len(names) + 1):
        for combo in itertools.combinations(names, r):
            used = sum(chunks[n]["tokens"] for n in combo)
            sc = sum(chunks[n]["score"] for n in combo)
            if used <= budget and sc > best_score:
                best, best_score = list(combo), sc
    return best, best_score
```

Run `--optimum`.

```text filename=--optimum
OPTIMUM — exhaustive best subset under the 10-token budget
----------------------------------------------------------------
  best subset: B C   tokens 10   total relevance 11
  density heuristic picks B C (relevance 11) — matches the optimum
----------------------------------------------------------------
  the cheap density heuristic lands on the optimum here.
```

The true best subset is B + C at relevance 11 — exactly what density picked. The cheap sort landed on the optimum, while the naive top-score rule left a point of relevance behind. That gap is small on three chunks; on a real pile of dozens it is the difference between a window full of answer and a window half-spent on one verbose passage.

<svg role="img" aria-label="Three selection strategies and their total relevance: by-score 10, by-density 11, optimum 11" viewBox="0 0 300 130" width="300" height="130">
  <line x1="90" y1="15" x2="90" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="100" x2="285" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <rect x="100" y="30" width="160" height="16" fill="var(--s1)"/>
  <text x="10" y="42" fill="var(--muted)" font-size="9">by score</text>
  <text x="265" y="42" fill="var(--muted)" font-size="9">10</text>
  <rect x="100" y="55" width="176" height="16" fill="var(--s2)"/>
  <text x="10" y="67" fill="var(--muted)" font-size="9">by density</text>
  <text x="281" y="67" fill="var(--muted)" font-size="9">11</text>
  <rect x="100" y="80" width="176" height="16" fill="none" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="10" y="92" fill="var(--muted)" font-size="9">optimum</text>
  <text x="281" y="92" fill="var(--muted)" font-size="9">11</text>
</svg>
^ Total relevance packed into the same 10-token window: density reaches the exhaustive optimum, raw score falls one short.

## Definition of done

The self-test pins all four claims with named flags: both selections fit the budget (neither overflows), density beats raw score, density equals the optimum, and raw score is strictly below the optimum.

```python filename=modules/context-and-retrieval/code/retrieval-inter-17/pack.py:119-132 COMPLETE
    score_within_budget = us <= budget
    print("  the by-score selection fits the budget = %s (%d/%d tokens)" % (score_within_budget, us, budget))

    density_within_budget = ud <= budget
    print("  the by-density selection fits the budget = %s (%d/%d tokens)" % (density_within_budget, ud, budget))

    density_beats_score = sd > ss
    print("  density packs more relevance than raw score = %s (%d vs %d)" % (density_beats_score, sd, ss))

    density_matches_optimum = sd == sc
    print("  density matches the exhaustive optimum = %s (%d vs %d)" % (density_matches_optimum, sd, sc))

    score_suboptimal = ss < sc
    print("  by-score leaves relevance on the table = %s (optimum %d, by-score %d)" % (score_suboptimal, sc, ss))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — greedy-by-score wastes budget; density packs more relevance and matches the optimum
----------------------------------------------------------------------------------------------------
  the by-score selection fits the budget = True (9/10 tokens)
  the by-density selection fits the budget = True (10/10 tokens)
  density packs more relevance than raw score = True (11 vs 10)
  density matches the exhaustive optimum = True (11 vs 11)
  by-score leaves relevance on the table = True (optimum 11, by-score 10)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  score_within_budget=True  density_within_budget=True  density_beats_score=True  density_matches_optimum=True  score_suboptimal=True
```

**Done means the packing is provably better, not just plausibly: density hits the exhaustive optimum of 11 while raw score is pinned one point below it.**

## Boss fight

Density beat raw score here, but density is still a greedy heuristic. Predict whether ranking by score-per-token always finds the optimal packing. It is tempting to say yes — it won on this fixture and it is the "right" knapsack sort.

It does not always win, and the reason is worth internalizing. Fractional knapsack is optimal only when you can take a fraction of an item; with whole chunks (0/1 knapsack) density can be fooled. Imagine a budget of 10 with one chunk scoring 10 for 6 tokens (density 1.67) and two chunks scoring 7 for 5 tokens each (density 1.4). Density grabs the 1.67 chunk first, spends 6 tokens, and only one of the 5-token chunks fits — total 17. But skipping the dense chunk entirely and taking both 5-token chunks gives 14... which is worse here, but shift the numbers slightly and the greedy first pick blocks a better pair. Density is a strong default that dominates raw score, not a guarantee; when the window is precious, spend the exhaustive optimum on the shortlist the heuristic produces.

The mirror-image mistake is scoring by relevance and then not tracking tokens at all — injecting chunks until the API rejects the request. That truncates mid-chunk, and a half-injected chunk is often worse than no chunk, because the model treats the fragment as complete.

```python filename=modules/context-and-retrieval/code/retrieval-inter-17/pack.py:56-61 COMPLETE
def by_score(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"])


def by_density(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"] / chunks[n]["tokens"])
```

**Rank by density to pack well, but treat the token budget as a hard constraint the selector enforces — never as something the API discovers by truncating you.**

## External resources

The 0/1 knapsack problem and the greedy value-density heuristic — any algorithms text (CLRS, "Introduction to Algorithms", the greedy and dynamic-programming chapters) covers why fractional-greedy is optimal and 0/1-greedy is not.

LangChain and LlamaIndex context-packing / "token limit" node postprocessors — production retrieval frameworks expose a budget and a selection policy; reading their defaults shows which ones sort by raw score and which account for length.

Liu et al., "Lost in the Middle" (2023) — why a full window is not automatically a good window: placement inside the budget matters too, so packing more relevant tokens is necessary but not sufficient.
