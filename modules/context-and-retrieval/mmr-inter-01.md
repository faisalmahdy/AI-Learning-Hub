---
id: mmr-inter-01
title: Select by marginal relevance, not raw relevance — the top-k most relevant chunks are often near-duplicates
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval ranks chunks by relevance to the query, and the obvious way to fill a context window is to take the top k. But relevance ranks each chunk in isolation, and the top of that ranking tends to cluster: if three chunks all say the same highly-relevant thing, all three sit at the top, and taking the top k spends the whole budget on one point while other relevant aspects — ranked just below the cluster — never make the cut. The set is highly relevant and highly redundant, the worst combination for a context window, because the model sees one fact three times and never sees the second fact it needed. Maximal Marginal Relevance fixes this by ranking each candidate on its marginal relevance — its relevance minus its similarity to what is already selected — built greedily: the first pick is the most relevant chunk, and each later pick maximizes lambda·relevance(d) − (1−lambda)·max_similarity(d, selected). On a fixture where a1, a2, a3 are near-duplicates covering aspect A (relevance 0.90, 0.88, 0.86) and b1, b2 cover aspect B (0.80, 0.78), top-3 by relevance returns a1, a2, a3 — three restatements of aspect A with aspect B missing — while MMR returns a1, b1, a2, keeping the most relevant chunk but covering both aspects, because at step 2 the diverse b1 (marginal 0.35) beats the near-duplicate a2 (marginal −0.01).
eli5: Imagine asking a group of friends for restaurant recommendations and only having room to write down three. If you just take the three most enthusiastic answers, all three might be raving about the same pizza place — technically the top three, but you learned about one restaurant, not three. A smarter rule is: after writing down the first recommendation, give a bonus to answers that are DIFFERENT from what you already wrote, so your three picks cover a pizza place, a taco stand, and a sushi bar. You still start with the most enthusiastic answer, but you stop letting near-copies of it crowd out everything else.
---

## Why this module

The retriever's job looks done once it has ranked chunks by relevance — but the top of that ranking is where near-duplicates pile up, so "take the top k" quietly fills a scarce context window with the same point repeated, and drops the other things the answer needed. The chunks are all relevant, which is exactly why the redundancy is easy to miss.

Retrieval ranks chunks by relevance to the query, and the obvious way to fill a context window is to take the top k. But relevance ranks each chunk in isolation, and the top of that ranking tends to cluster: if three chunks all say the same highly-relevant thing, all three sit at the top, and taking the top k spends the whole budget on one point while other relevant aspects of the answer — ranked just below the cluster — never make the cut. The retrieved set is highly relevant and highly redundant, the worst combination for a context window, because the model sees the same fact three times and never sees the second fact it needed. The failure is not that the top chunks are irrelevant; it is that they are relevant in the same way.

Maximal Marginal Relevance fixes this by ranking each candidate not on its relevance alone but on its marginal relevance: how relevant it is minus how similar it is to what you have already selected. It builds the result greedily. The first pick is the most relevant chunk. Each subsequent pick maximizes lambda·relevance(d) − (1−lambda)·max_similarity(d, already_selected): a chunk earns its place by being relevant *and* by being different from the chunks already chosen. Lambda tunes the trade-off — lambda=1 is pure relevance (back to top-k), lambda=0 is pure diversity — and a middle value keeps the best chunk while pushing near-duplicates down in favor of chunks that add something new. This module selects three chunks both ways and shows the coverage change.

**Top-k by relevance clusters near-duplicate chunks and wastes the context budget while dropping other relevant aspects, so select by marginal relevance — relevance minus similarity to what is already chosen — which keeps the best chunk yet covers more of the answer for the same k.**

## Concepts

**The marginal score** is the heart of MMR: a candidate's relevance discounted by how similar it is to the already-selected set. A near-duplicate of a chosen chunk pays a large redundancy penalty; a chunk that adds something new pays almost none.

```python filename=modules/context-and-retrieval/code/mmr-inter-01/mmr.py:55-58 COMPLETE
def marginal_score(data, d, selected, lam):
    """MMR score for candidate d: lambda*relevance - (1-lambda)*max similarity to the already-selected set."""
    redundancy = max((sim(data, d, s) for s in selected), default=0.0)
    return lam * data["relevance"][d] - (1 - lam) * redundancy
```

**The greedy selection** applies that score repeatedly: the first pick has an empty selected set (so it is just the most relevant), and each later pick maximizes the marginal score against everything chosen so far.

```python filename=modules/context-and-retrieval/code/mmr-inter-01/mmr.py:61-69 COMPLETE
def mmr(data, k, lam):
    """Greedy Maximal Marginal Relevance: repeatedly add the candidate with the highest marginal score."""
    selected = []
    candidates = list(data["ids"])
    while len(selected) < k and candidates:
        best = max(candidates, key=lambda d: marginal_score(data, d, selected, lam))
        selected.append(best)
        candidates.remove(best)
    return selected
```

<svg role="img" aria-label="A cluster of three near-duplicate chunks a1 a2 a3 covering aspect A and a separate pair b1 b2 covering aspect B; top-k circles all three A chunks, MMR spans both clusters" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">top-k stays inside one cluster; MMR spans both aspects</text>
  <text x="40" y="30" fill="var(--muted)" font-size="7">aspect A (near-duplicates)</text>
  <circle cx="60" cy="55" r="6" fill="var(--s1)"/><text x="52" y="58" fill="var(--panel)" font-size="6">a1</text>
  <circle cx="78" cy="45" r="6" fill="var(--s1)"/><text x="70" y="48" fill="var(--panel)" font-size="6">a2</text>
  <circle cx="72" cy="66" r="6" fill="var(--s1)"/><text x="64" y="69" fill="var(--panel)" font-size="6">a3</text>
  <text x="200" y="30" fill="var(--muted)" font-size="7">aspect B</text>
  <circle cx="220" cy="58" r="6" fill="var(--s2)"/><text x="212" y="61" fill="var(--panel)" font-size="6">b1</text>
  <circle cx="238" cy="50" r="6" fill="var(--s2)"/><text x="230" y="53" fill="var(--panel)" font-size="6">b2</text>
  <ellipse cx="70" cy="55" rx="34" ry="26" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"/>
  <text x="40" y="96" fill="var(--muted)" font-size="7">top-3 (dashed): all aspect A</text>
  <path d="M60,55 L220,58" stroke="var(--ink)" stroke-dasharray="2 3"/>
  <text x="40" y="112" fill="var(--muted)" font-size="7">MMR: a1 then b1 (across the gap) then a2</text>
</svg>
^ The three aspect-A chunks sit close together, so top-k (dashed circle) selects all of them and never leaves the cluster; MMR jumps across the gap to b1 after a1, so its selection spans both aspects.

**MMR scores a candidate by relevance minus its redundancy against the already-chosen set, so the first pick is the most relevant chunk and each later pick must add something new — turning "the k most relevant" into "the k that best cover the answer."**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/mmr-inter-01/mmr.py

The fixture is five chunks: a1–a3 are near-duplicates of aspect A, b1–b2 cover aspect B, and A is slightly more relevant than B.

```json filename=modules/context-and-retrieval/code/mmr-inter-01/mmr.json:5-7 COMPLETE
  "ids": ["a1", "a2", "a3", "b1", "b2"],
  "relevance": {"a1": 0.90, "a2": 0.88, "a3": 0.86, "b1": 0.80, "b2": 0.78},
  "aspect": {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B"},
```

Run `--select` to pick three chunks both ways.

```text filename=--select
SELECT — top-k by relevance vs MMR (k=3, lambda=0.5)
--------------------------------------------------------------
  chunk relevance and aspect:
    a1   relevance 0.90  aspect A
    a2   relevance 0.88  aspect A
    a3   relevance 0.86  aspect A
    b1   relevance 0.80  aspect B
    b2   relevance 0.78  aspect B
--------------------------------------------------------------
  top-3 by relevance : ['a1', 'a2', 'a3']   aspects covered: ['A']
  MMR                : ['a1', 'b1', 'a2']   aspects covered: ['A', 'B']
  top-k returns 3 restatements of aspect A; MMR covers A and B.
```

<svg role="img" aria-label="Two result sets of three slots: top-k holds a1 a2 a3 all labelled aspect A, MMR holds a1 b1 a2 labelled A B A, so MMR covers two aspects and top-k one" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same 3 slots — top-k covers 1 aspect, MMR covers 2</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">top-k</text>
  <g transform="translate(60,28)" font-size="7">
  <rect x="0" y="0" width="40" height="18" fill="var(--s1)"/><text x="10" y="12" fill="var(--panel)">a1·A</text>
  <rect x="44" y="0" width="40" height="18" fill="var(--s1)"/><text x="54" y="12" fill="var(--panel)">a2·A</text>
  <rect x="88" y="0" width="40" height="18" fill="var(--s1)"/><text x="98" y="12" fill="var(--panel)">a3·A</text>
  <text x="140" y="12" fill="var(--muted)">→ aspects {A}</text>
  </g>
  <text x="10" y="76" fill="var(--muted)" font-size="7">MMR</text>
  <g transform="translate(60,64)" font-size="7">
  <rect x="0" y="0" width="40" height="18" fill="var(--s1)"/><text x="10" y="12" fill="var(--panel)">a1·A</text>
  <rect x="44" y="0" width="40" height="18" fill="var(--s2)"/><text x="54" y="12" fill="var(--panel)">b1·B</text>
  <rect x="88" y="0" width="40" height="18" fill="var(--s1)"/><text x="98" y="12" fill="var(--panel)">a2·A</text>
  <text x="140" y="12" fill="var(--muted)">→ aspects {A,B}</text>
  </g>
  <text x="10" y="104" fill="var(--muted)" font-size="7">both keep the best chunk a1; MMR swaps a redundant a3 for the new-aspect b1</text>
</svg>
^ Top-k fills all three slots with aspect-A chunks (a1, a2, a3), while MMR keeps a1 but replaces a redundant a-chunk with b1, so its three slots cover both aspect A and aspect B.

Top-3 by relevance takes a1, a2, a3 — the three highest scores — and every one of them is aspect A. The set is maximally relevant and completely redundant: it answers aspect A three times and says nothing about aspect B, even though b1 at relevance 0.80 was a strong result. If the query genuinely needed both aspects, this context window has failed, and it failed precisely *because* it optimized relevance. MMR takes a1, b1, a2: it agrees that a1 is the single best chunk and keeps it, but then it declines to stack another near-duplicate of a1 and reaches for b1, which covers the missing aspect, before returning to a2. Same three slots, same relevance signal, but now the answer's two aspects are both represented. The difference is entirely in what happens after the first pick.

## Build

The second pick is where MMR earns its name — watch the marginal scores decide it. Run `--score`.

```text filename=--score
SCORE — the second MMR pick, after a1 is selected (lambda=0.5)
------------------------------------------------------------------
  candidate  relevance   sim to a1   marginal = 0.5*rel - 0.5*sim
    a2       0.88        0.9         -0.010
    a3       0.86        0.9         -0.020
    b1       0.80        0.1         0.350
    b2       0.78        0.1         0.340
------------------------------------------------------------------
  highest marginal score: b1 -- a diverse chunk beats the near-duplicate a2.
```

By raw relevance, a2 (0.88) should be the second pick — it is the second-highest score. But a2 is 0.9 similar to the already-chosen a1, so its marginal score is 0.5·0.88 − 0.5·0.9 = −0.01: almost all of its relevance is cancelled by its redundancy, because it barely adds anything a1 did not already provide. b1 has lower raw relevance (0.80) but is only 0.1 similar to a1, so its marginal score is 0.5·0.80 − 0.5·0.1 = 0.35 — it keeps almost all its relevance because it is new information. So b1 wins the second slot by a wide margin, 0.35 to −0.01, and the near-duplicates a2 and a3 are pushed down not for being irrelevant but for being redundant. That is the whole idea: relevance is scored against the query, redundancy against what you already have, and the pick that maximizes their difference is the one that adds the most. The naive alternative just sorts by relevance and never subtracts the redundancy.

```python filename=modules/context-and-retrieval/code/mmr-inter-01/mmr.py:50-52 COMPLETE
def top_k(data, k):
    """The k chunks with the highest raw relevance -- what a naive retriever returns."""
    return sorted(data["ids"], key=lambda d: data["relevance"][d], reverse=True)[:k]
```

<svg role="img" aria-label="Marginal scores for the second pick: a2 and a3 are negative, b1 and b2 are around 0.35, so a diverse chunk is chosen over the near-duplicates" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">step-2 marginal scores: near-duplicates go negative</text>
  <line x1="40" y1="60" x2="290" y2="60" stroke="var(--line)"/>
  <text x="34" y="34" fill="var(--muted)" font-size="7" text-anchor="end">+0.35</text>
  <text x="34" y="63" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <g transform="translate(60,0)">
  <rect x="0" y="60" width="24" height="4" fill="var(--s1)"/><text x="0" y="80" fill="var(--muted)" font-size="7">a2</text><text x="-2" y="90" fill="var(--muted)" font-size="6">-0.01</text>
  <rect x="40" y="60" width="24" height="6" fill="var(--s1)"/><text x="40" y="80" fill="var(--muted)" font-size="7">a3</text><text x="38" y="90" fill="var(--muted)" font-size="6">-0.02</text>
  <rect x="80" y="30" width="24" height="30" fill="var(--s2)"/><text x="80" y="80" fill="var(--muted)" font-size="7">b1</text><text x="80" y="90" fill="var(--muted)" font-size="6">0.35</text>
  <rect x="120" y="31" width="24" height="29" fill="var(--s2)"/><text x="120" y="80" fill="var(--muted)" font-size="7">b2</text><text x="120" y="90" fill="var(--muted)" font-size="6">0.34</text>
  </g>
  <text x="60" y="112" fill="var(--muted)" font-size="7">a2/a3 (similar to a1) lose their relevance to the redundancy penalty; b1/b2 keep it</text>
</svg>
^ The near-duplicates a2 and a3 score slightly negative because their high similarity to a1 cancels their relevance, while b1 and b2 score around 0.35 — so MMR selects a diverse chunk for the second slot rather than a restatement.

## Definition of done

The self-test pins the redundant top-k, the dropped aspect, and the MMR coverage that keeps the best chunk.

```python filename=modules/context-and-retrieval/code/mmr-inter-01/mmr.py:114-121 COMPLETE
    topk_one_aspect = len(aspects(data, tk)) == 1
    print("  top-k covers only one aspect (redundant) = %s (%s)" % (topk_one_aspect, aspects(data, tk)))

    topk_drops_b = not any(data["aspect"][d] == "B" for d in tk)
    print("  top-k drops aspect B entirely = %s (%s)" % (topk_drops_b, tk))

    mmr_covers_both = len(aspects(data, mm)) == 2
    print("  MMR covers both aspects = %s (%s)" % (mmr_covers_both, aspects(data, mm)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — top-k returns one redundant aspect and drops the other; MMR keeps the top chunk yet covers both aspects
------------------------------------------------------------------------------------------------------------------------
  top-k covers only one aspect (redundant) = True (['A'])
  top-k drops aspect B entirely = True (['a1', 'a2', 'a3'])
  MMR covers both aspects = True (['A', 'B'])
  MMR still picks the most relevant chunk first = True (a1)
  at step 2 the diverse b1 outscores the near-duplicate a2 = True (0.350 > -0.010)
```

**Done means the redundancy failure and the diversity fix are proven on real scores: top-3 by relevance returns a1, a2, a3 (one aspect, aspect B dropped entirely), while MMR returns a1, b1, a2 (both aspects) — keeping the most relevant chunk a1 first, then selecting the diverse b1 over the near-duplicate a2 because 0.35 beats −0.01 — so the same three slots cover twice the answer.**

## Boss fight

Predict two ways MMR is subtler than "add a diversity term," because lambda is a real dial and diversity is not free.

The first trap is that lambda trades away relevance for coverage, and the right setting depends on the query and the failure you are guarding against. At lambda=1 MMR is exactly top-k (no diversity), and at lambda=0 it ignores the query entirely and just spreads out over the candidate space, which can drag in diverse but weakly-relevant chunks — diversity for its own sake is as wrong as redundancy. A query with a single correct answer (a lookup, a definition) wants high lambda, because there is no second aspect to cover and forcing diversity only demotes the best chunk; a broad or multi-faceted query (a comparison, a "what are the tradeoffs" question) wants lower lambda, because the answer genuinely has parts. There is no universal lambda, and a system that hard-codes one will over-diversify narrow queries and under-diversify broad ones. The honest move is to treat lambda as tunable per query type, and to remember that MMR's diversity is measured by whatever similarity you feed it — which is only as good as the embeddings, so two chunks that are semantically redundant but lexically different can both slip through if the similarity metric cannot see their overlap.

The second trap is that MMR is a greedy heuristic solving a genuinely hard problem, so it is neither optimal nor the only tool. The set that maximizes total coverage for a given k is a combinatorial optimization (a facility-location / maximum-coverage problem), and greedy MMR approximates it — good in practice, but it can be beaten, and its first-pick-then-diversify order means an early greedy choice can lock in a set that is not globally best. It also does not know *how many* aspects exist, so with a tight k it may still miss a third aspect that neither top-k nor MMR had room for — diversity within k slots cannot manufacture coverage the budget cannot hold. In modern pipelines MMR is one option among several for the same goal: clustering the candidates and taking one per cluster, submodular optimization for coverage, or simply de-duplicating near-identical chunks before ranking. The unifying point is that relevance ranking alone is the wrong objective for filling a context window — the objective is coverage of the answer under a budget — and MMR is a cheap, effective, but tunable and approximate way to optimize for that instead.

**MMR's lambda is a per-query dial (high for single-answer queries, low for multi-faceted ones) and its diversity is only as good as the similarity metric, so a fixed lambda over- or under-diversifies and lexically-different-but-redundant chunks can slip through — and because greedy MMR only approximates the underlying maximum-coverage problem, treat it as one tunable tool (alongside clustering, submodular selection, and de-duplication) for the real objective: covering the answer under a budget, not maximizing relevance.**

## External resources

The original Maximal Marginal Relevance paper (Carbonell and Goldstein) — the lambda·relevance − (1−lambda)·redundancy formulation, the greedy algorithm, and its origin in reducing redundancy in retrieved and summarized results.

Writing on diversity and coverage in retrieval and RAG — why filling a context window is a coverage problem rather than a pure relevance-ranking problem, and alternatives to MMR such as clustering, submodular maximization, and near-duplicate removal.

The companion reranking and chunking modules in this topic — MMR operates on the candidate set a retriever and reranker produce, so its diversity depends on good relevance scores beneath it and on chunks that are not already near-duplicates by construction.
