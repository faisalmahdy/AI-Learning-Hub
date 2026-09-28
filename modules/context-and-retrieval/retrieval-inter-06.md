---
id: retrieval-inter-06
title: Rank retrieved chunks for relevance and novelty — pure top-k returns duplicates
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: Ranking retrieved chunks by pure relevance and keeping the top k crowds the context with near-duplicates, because the most relevant passages tend to cover the same sub-topic — a query needing dosage, side effects, and interactions gets the three highest-scoring dosage chunks and nothing else, covering 1 of 3 needed sub-topics, so the answer is confidently incomplete. Maximal marginal relevance scores each candidate for relevance minus its similarity to what is already selected, so once a dosage chunk is picked its near-duplicates are penalized and a side-effects chunk wins the slot; MMR covers all 3 needed sub-topics while still including the single most relevant chunk. The lesson is that a context budget spent on redundant chunks answers one facet three times and the others not at all, and diversity, not just relevance, is what makes retrieved context complete.
eli5: If you ask five friends about a movie and pick the three who agree most, you hear the same opinion three times and learn nothing new. Better to pick the most useful person, then the most useful person who adds something different, and so on. That way your three picks cover the plot, the acting, and the ending — instead of three takes on just the plot.
---

## Why this module

Retrieval feeds an answer, and the answer is only as complete as the chunks you put in the context. The reflex is to score every chunk for relevance to the query and keep the top k, which sounds obviously right and quietly fails on any query that needs more than one thing answered. This module builds that failure — a context full of near-duplicate chunks — and the standard fix, maximal marginal relevance, because the difference between them is the difference between an answer that covers the question and one that answers a single facet of it three times.

The problem is that relevance and coverage are not the same objective. The most relevant chunks to a query are often near-duplicates of each other: several passages about the same sub-topic, all scoring high, because they all match the query strongly. Pure top-k selects them all, spending the whole context budget on one facet and leaving the others unretrieved. A query about a drug that needs dosage, side effects, and interactions gets three dosage chunks — the three highest scores — and the model, given only those, writes a fluent answer about dosage and says nothing about the rest, with no signal that anything is missing. Maximal marginal relevance fixes this by changing what it optimizes: each candidate is scored for its relevance minus its similarity to the chunks already chosen, so a chunk that duplicates a selected one is penalized and a novel chunk on a different sub-topic wins the slot. The result trades a little relevance for a lot of coverage, and coverage is what a multi-faceted answer needs.

You need the retrieval-measurement instinct from `retrieval-basic-01` and the reranking framing from `retrieval-inter-05`. Everything runs offline against a chunk fixture — six candidates with relevance scores and topic labels — stdlib Python 3, `$0.00`. The instinct to unlearn is that the best context is the k most relevant chunks. The best context is the k chunks that together cover what the query needs, and past the first chunk on a sub-topic, more of the same sub-topic adds relevance and no coverage.

Here is pure top-k, three chunks deep on one facet:

```
# modules/context-and-retrieval/code/retrieval-inter-06/ — COMPLETE, run from that directory
$ python3 mmr.py --topk

TOPK — pure relevance, top 3
------------------------------------------------------------------
  c1   rel=0.95  topic=dosage
  c2   rel=0.90  topic=dosage
  c3   rel=0.88  topic=dosage
  topics covered: ['dosage'] (1 of 3 needed)
```

run: 2026-08-26 · deterministic; relevance and topics are a fixture · 6 chunks · `python3 mmr.py --topk`

The three highest-relevance chunks are all about dosage — 1 of the 3 needed sub-topics — so the answer built from this context can only speak to dosage. This module is why that happens and how MMR broadens the selection.

## Concepts

Named here so you can find them again; each is built below.

- **Relevance** — how well a chunk matches the query; what top-k ranks on.
- **Redundancy** — near-duplicate chunks covering the same sub-topic, all scoring high.
- **Coverage** — how many of the needed sub-topics the selected chunks span.
- **Maximal marginal relevance (MMR)** — selecting for relevance minus similarity to what is chosen.
- **Novelty penalty** — the similarity of a candidate to the already-selected set, subtracted from its score.
- **Lambda** — the MMR weight trading relevance against novelty.

## Worked example

Source: maximal marginal relevance (Carbonell & Goldstein) as used for diverse retrieval and summarization, and the redundancy problem it solves in RAG context assembly; the chunks here stand in for real retrieved passages so the coverage difference is exact and checkable.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-06/` — `mmr.py`, and `chunks.json`, six chunks with relevance scores and topics, needing three sub-topics covered. Every command runs from there.

### Pure top-k: relevance blind to redundancy

Top-k is a sort. It ranks by relevance and takes the head, with no notion of what it has already picked.

```
# mmr.py:49-51 — COMPLETE (pure relevance top-k)
def select_topk(chunks, k):
    """Pure relevance: the k highest-scoring chunks."""
    return sorted(chunks, key=lambda c: (-c["relevance"], c["id"]))[:k]
```

The three dosage chunks — 0.95, 0.90, 0.88 — are the three highest scores, so top-k takes them, and it would take a fourth and fifth dosage chunk too if k were larger, because it has no memory of the topic it already covered. Relevance is a per-chunk score, and summing the top per-chunk scores maximizes total relevance while completely ignoring whether the chunks say the same thing. On a single-facet query that is fine; on a multi-facet one it is a trap, because the facets the query needs are not the facets with the highest individual scores.

<svg viewBox="0 0 700 180" role="img" aria-label="Six chunks as dots positioned by topic (dosage cluster of three on the left, side_effects, interactions, storage spread right) and height by relevance. Top-k circles the three dosage dots (highest relevance, all clustered). The side_effects and interactions dots are left unselected.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">chunks by topic (x) and relevance (y); top-k grabs the tallest cluster</text>
    <line x1="50" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <g fill="var(--s2)"><circle cx="110" cy="40" r="7"></circle><circle cx="135" cy="52" r="7"></circle><circle cx="160" cy="58" r="7"></circle></g>
    <ellipse cx="135" cy="50" rx="45" ry="35" fill="none" stroke="var(--s2)" stroke-dasharray="4 3"></ellipse>
    <text x="135" y="105" text-anchor="middle" fill="var(--s2)" font-size="8">top-k: all 3 dosage</text>
    <circle cx="320" cy="80" r="7" fill="var(--s1)"></circle><text x="320" y="100" text-anchor="middle" fill="var(--s1)" font-size="8">side_effects</text>
    <circle cx="460" cy="95" r="7" fill="var(--s1)"></circle><text x="460" y="115" text-anchor="middle" fill="var(--s1)" font-size="8">interactions</text>
    <circle cx="590" cy="128" r="7" fill="var(--muted)"></circle><text x="590" y="145" text-anchor="middle" fill="var(--muted)" font-size="8">storage</text>
    <text x="110" y="170" fill="var(--muted)" font-size="8">dosage</text>
    <text x="300" y="135" fill="var(--s1)" font-size="8">needed, but unselected -&gt;</text>
  </g>
</svg>
^ The three dosage chunks are the tallest dots and sit in one cluster, so top-k circles all three and leaves side effects and interactions — needed but individually lower-scoring — unselected. Ranking by height alone never spreads across the x-axis.

### The coverage cost

The selection covers one of three needed sub-topics. The `topics_covered` count makes the failure quantitative.

```
# mmr.py:43-45 — COMPLETE (which sub-topics the selection spans)
def topics_covered(selected):
    return {c["topic"] for c in selected}
```

Three chunks, one topic. The context handed to the model is three ways of saying the same thing about dosage, and the model cannot answer about side effects or interactions because that information is not in front of it — it was retrieved into the candidate pool (c4, c5 exist) but never selected. This is the quiet failure mode of RAG: the answer is fluent and correct about the facet it saw, and silent about the facets it did not, with nothing to flag the omission. A context budget is precious, and spending three slots on one facet is the expensive mistake.

### MMR: relevance minus redundancy

MMR selects greedily, but each pick is scored for relevance minus its similarity to everything already chosen.

```
# mmr.py:54-66 — COMPLETE (greedy MMR: relevance penalized by similarity to the selected)
def select_mmr(chunks, k, lam):
    """Greedily pick the chunk maximizing lam*relevance - (1-lam)*max_sim_to_selected."""
    selected, remaining = [], list(chunks)
    while remaining and len(selected) < k:
        best, best_score = None, None
        for c in remaining:
            novelty_penalty = max((similarity(c, s) for s in selected), default=0.0)
            score = lam * c["relevance"] - (1 - lam) * novelty_penalty
            if best_score is None or score > best_score or (score == best_score and c["id"] < best["id"]):
                best, best_score = c, score
        selected.append(best)
        remaining.remove(best)
    return selected
```

The novelty penalty rests on a similarity between chunks — here high within a topic and low across topics, a clean stand-in for embedding cosine:

```
# mmr.py:38-40 — COMPLETE (chunk-chunk similarity: high within a topic, low across)
def similarity(a, b):
    """A stand-in for chunk-chunk similarity: high within a topic, low across topics."""
    return 1.0 if a["topic"] == b["topic"] else 0.15
```

The `novelty_penalty` is the maximum similarity of a candidate to any already-selected chunk. The first pick has an empty selected set, so it is pure relevance — c1, dosage, 0.95. On the second pick, c2 (dosage) is highly similar to c1, so its score drops by `(1-lam)` times that similarity, while c4 (side effects) is dissimilar and keeps almost all its relevance — so c4 wins even though its raw relevance is lower. Run it:

```
# $ python3 mmr.py --mmr
#   c1   rel=0.95  topic=dosage
#   c4   rel=0.80  topic=side_effects
#   c5   rel=0.75  topic=interactions
#   topics covered: ['dosage', 'interactions', 'side_effects'] (3 of 3 needed)
```

run: 2026-08-26 · deterministic · `python3 mmr.py --mmr`

<svg viewBox="0 0 700 200" role="img" aria-label="Three rounds of greedy MMR. Round 1: c1 (dosage, rel 0.95) picked, no penalty. Round 2: c2 (dosage) penalized for similarity to c1 down to a low score, c4 (side_effects, rel 0.80) keeps its score and wins. Round 3: c5 (interactions) picked. The selected set grows to cover three topics.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">greedy MMR: each round penalizes candidates similar to the selected set</text>
    <text x="30" y="44" fill="var(--ink)">round 1</text>
    <text x="110" y="44" fill="var(--muted)">selected: {} -&gt; pure relevance -&gt;</text>
    <rect x="360" y="32" width="80" height="18" fill="var(--s1)"></rect><text x="400" y="45" text-anchor="middle" fill="var(--panel)">pick c1 .95</text>
    <text x="30" y="90" fill="var(--ink)">round 2</text>
    <text x="110" y="82" fill="var(--muted)">c2 dosage: .90 - penalty(sim to c1) -&gt; low</text>
    <text x="110" y="98" fill="var(--s1)">c4 side_effects: .80 - tiny penalty -&gt; wins</text>
    <rect x="470" y="76" width="90" height="18" fill="var(--s1)"></rect><text x="515" y="89" text-anchor="middle" fill="var(--panel)">pick c4 .80</text>
    <text x="30" y="140" fill="var(--ink)">round 3</text>
    <text x="110" y="140" fill="var(--muted)">remaining dosage penalized again -&gt;</text>
    <rect x="400" y="128" width="100" height="18" fill="var(--s1)"></rect><text x="450" y="141" text-anchor="middle" fill="var(--panel)">pick c5 interactions</text>
    <text x="110" y="178" fill="var(--s1)">selected = {c1, c4, c5} covering dosage, side_effects, interactions</text>
  </g>
</svg>
^ Round 1 is pure relevance; from round 2 on, every dosage duplicate is docked for its similarity to the already-picked c1, so the novel side-effects and interactions chunks win the slots. Greedy penalization is how coverage emerges.

MMR selected c1, c4, c5 — dosage, side effects, interactions — all three needed sub-topics, and it still kept c1, the single most relevant chunk. It gave up the 0.90 and 0.88 dosage chunks, whose relevance was real but whose information was redundant, in exchange for the side-effects and interactions chunks that the answer actually needs. The model now has context to answer the whole query.

<svg viewBox="0 0 700 180" role="img" aria-label="Two coverage bars over three needed sub-topics: dosage, side_effects, interactions. Top-k fills only the dosage segment (1 of 3). MMR fills all three segments (3 of 3).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">needed sub-topics covered (dosage, side_effects, interactions)</text>
    <text x="20" y="56" fill="var(--ink)">top-k</text>
    <rect x="120" y="44" width="150" height="20" fill="var(--s2)"></rect><text x="195" y="59" text-anchor="middle" fill="var(--panel)" font-size="8">dosage</text>
    <rect x="272" y="44" width="150" height="20" fill="none" stroke="var(--line)" stroke-dasharray="3 2"></rect>
    <rect x="424" y="44" width="150" height="20" fill="none" stroke="var(--line)" stroke-dasharray="3 2"></rect>
    <text x="590" y="59" fill="var(--s2)" font-size="8">1 / 3</text>
    <text x="20" y="106" fill="var(--ink)">MMR</text>
    <rect x="120" y="94" width="150" height="20" fill="var(--s1)"></rect><text x="195" y="109" text-anchor="middle" fill="var(--panel)" font-size="8">dosage</text>
    <rect x="272" y="94" width="150" height="20" fill="var(--s1)"></rect><text x="347" y="109" text-anchor="middle" fill="var(--panel)" font-size="8">side_effects</text>
    <rect x="424" y="94" width="150" height="20" fill="var(--s1)"></rect><text x="499" y="109" text-anchor="middle" fill="var(--panel)" font-size="8">interactions</text>
    <text x="590" y="109" fill="var(--s1)" font-size="8">3 / 3</text>
    <text x="120" y="145" fill="var(--muted)" font-size="8">same 3 slots, same query — top-k fills one facet three times, MMR fills all three</text>
  </g>
</svg>
^ Both selections use the same three-chunk budget. Top-k fills only the dosage facet and leaves the other two empty; MMR fills all three. The dashed empty segments are answers the top-k context cannot give.

**The most relevant chunks are often near-duplicates, so pure top-k spends the context budget covering one sub-topic repeatedly and leaves the others unretrieved — MMR scores relevance minus similarity to the selected set, trading a little relevance for the coverage a multi-faceted answer needs.**

### The self-test

The `--check` mode asserts the redundancy and the fix: top-k returns fewer topics than chunks, MMR covers more and covers every needed sub-topic, top-k misses some, and MMR still keeps the top chunk.

```
# $ python3 mmr.py --check
#   top-k selects near-duplicates (fewer topics than chunks) = True (1 topics in 3 chunks)
#   MMR covers more distinct topics than top-k = True (3 vs 1)
#   MMR covers every needed sub-topic = True (['dosage', 'interactions', 'side_effects'])
#   top-k misses a needed sub-topic = True (missing ['interactions', 'side_effects'])
#   MMR still includes the most relevant chunk = True (c1)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 mmr.py --check`

The `mmr_covers_needed` line is the correctness anchor: MMR's selection must span every sub-topic the query needs, and if the novelty penalty were wrong — too weak to demote duplicates — that coverage would fail. The `mmr_keeps_top1` line guards against overcorrecting: diversity must not throw away the single best chunk, so the test requires the most relevant chunk to survive, proving MMR balances the two objectives rather than sacrificing relevance for novelty.

### The running tally

| selector | chunks | distinct topics | needed covered | what it optimizes |
|---|---|---|---|---|
| top-k (relevance) | c1, c2, c3 | 1 (dosage) | 1 of 3 | total relevance |
| MMR (λ=0.5) | c1, c4, c5 | 3 | 3 of 3 | relevance + coverage |

The two rows spend the identical three-chunk budget and differ entirely in coverage. Top-k maximizes total relevance and answers one third of the query; MMR gives up two high-relevance duplicates and answers all of it. The number that matters for a multi-faceted query is not the sum of relevance scores — top-k wins that by construction — it is the coverage of what the answer needs, and past the first chunk on a facet, relevance and coverage stop agreeing. When a query has several parts, rank for both.

### What we did not settle

MMR is one diversity method with one knob. Lambda tunes the relevance-novelty tradeoff, and the right value depends on the query — a single-facet lookup wants high lambda (near pure relevance), a survey question wants lower; picking it per query is its own problem. The similarity here is a clean within-topic indicator; real systems use embedding cosine between chunks, which is noisier and can under- or over-penalize. Coverage assumes you know the needed sub-topics, which in practice you infer from the query or discover during generation. And there are alternatives to MMR — clustering the candidates and taking one per cluster, or determinantal point processes that model diversity probabilistically. The core here — penalize a candidate by its similarity to what you already have — is the idea every diversity-aware selector shares.

## Build

The practice in one paragraph: when a query needs more than one thing answered, do not fill the context with the top-k most relevant chunks; select for relevance minus redundancy, so each added chunk covers something new, using MMR or a clustering variant; measure coverage of the needed sub-topics, not just total relevance, because those objectives diverge once a facet is covered; and tune the relevance-novelty weight to the query's breadth. Keep the single most relevant chunk, and diversify from there.

We opened on the redundant top-k. The number that shows the difference is coverage:

```
# modules/context-and-retrieval/code/retrieval-inter-06/ — COMPLETE, run from that directory
$ python3 mmr.py --mmr
  topics covered: ['dosage', 'interactions', 'side_effects'] (3 of 3 needed)
```

Now do it to your own retrieval. Take a multi-faceted query, retrieve a candidate pool, and select k chunks two ways: pure top-k, and MMR. Your number to beat is not total relevance; it is **the coverage of the sub-topics the answer needs, which MMR raises and pure top-k leaves low when the top chunks are redundant**. Then sweep lambda and watch coverage trade against relevance. Bring back both selections and their coverage. Good luck.

## Definition of done

- [ ] A multi-faceted query with a candidate pool spanning several sub-topics
- [ ] A pure top-k selection by relevance
- [ ] An MMR selection scoring relevance minus similarity to the selected set
- [ ] Coverage of the needed sub-topics measured for both selections
- [ ] Confirmation top-k returns near-duplicates and misses needed sub-topics
- [ ] Confirmation MMR covers the needed sub-topics while keeping the most relevant chunk
- [ ] `python3 mmr.py --check` printing SELF-TEST PASS: topk-redundant, mmr-more, mmr-covers-needed, topk-misses, mmr-keeps-top1
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why do the most relevant chunks tend to be near-duplicates, and what does that do to a top-k context?
2. What does MMR add to a relevance score, and how does that change which chunk wins a slot?
3. Top-k maximizes total relevance yet gives a worse answer here. Explain how relevance and coverage diverge.
4. What does lambda control, and why would a single-facet query and a survey query want different values?
5. Your own query was selected two ways. What was the sub-topic coverage under top-k and under MMR?

## External resources

- Carbonell & Goldstein, *The Use of MMR for Reordering Documents and Producing Summaries* (1998) — my summary: the original maximal marginal relevance formulation this module implements, for diverse retrieval and summarization; read it for the relevance-novelty tradeoff and the lambda parameter.
- Retrieval-diversity writing on MMR in RAG pipelines — my summary: how production RAG uses MMR (and clustering) to de-duplicate retrieved chunks before assembling context; read it for embedding-cosine similarity in place of the clean topic indicator here.
- This hub, *retrieval-inter-05* — modules/context-and-retrieval/retrieval-inter-05.md — my summary: the reranking module that reorders a candidate pool for precision; read it for the step before diversity — MMR selects from the reranked pool, trading some of that precision for coverage.
