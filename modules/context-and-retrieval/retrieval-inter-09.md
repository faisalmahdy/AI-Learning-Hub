---
id: retrieval-inter-09
title: Expand a vague query before you embed it — a short query lands far from the answer
topic: context-and-retrieval
level: intermediate
status: ready
time: 5-8h
summary: Dense retrieval matches a query's embedding against document embeddings, but a real user query is short and underspecified — a few keywords, not the full language of the answer — so its embedding sits in a thin, generic region of the space, close to anything sharing its one keyword and not especially close to the document that actually answers it. Query expansion fixes the input, not the index: before embedding, grow the query into the fuller language the answer would use, or (the HyDE trick) generate a hypothetical answer and embed that, so the expanded query lands in the specific region where the relevant document lives. On the fixture the raw query ranks an off-topic distractor above the relevant document (cosine 0.77 vs 0.52) and misses it at rank 1, while the expanded query puts the relevant document first (1.00 vs 0.33) — same documents, same index, same scorer, only the query representation changed. The lesson is that retrieval quality is bounded by how well the query is stated, and a vague query cannot be rescued by a better index or reranker downstream because it never surfaces the right document in the first place; the cheapest fix is to state the query more like the answer before you search.
eli5: If you walk into a huge library and ask only for "attention," the librarian has no idea if you mean a psychology book or an AI textbook, and points you at a random shelf that happens to have that word. If instead you say the whole thing you're really after — "how the attention mechanism in transformers lets a model weigh different words" — they walk you straight to the right book. Filling out your question before you search, so it sounds like the answer you want, is what gets you to the right shelf.
---

## Why this module

Dense retrieval works by turning both the query and the documents into vectors and returning the documents whose vectors are closest to the query's. It has a quiet dependency that decides whether it works at all: the query has to land near the right document in the vector space. And a real query often does not, because a real query is short. A user types "attention" or "rope scaling" — a keyword or two — while the document that answers them is written in full, rich language. The short query's embedding is generic and thin, sitting near anything that shares its surface words, and not particularly near the specific document that actually holds the answer.

The failure is not the index's fault and not the scorer's fault; it is upstream of both. If the query embedding is in the wrong neighborhood, the nearest documents are the wrong documents, and no amount of reranking the results or improving the embedding model rescues it — a reranker can only reorder what retrieval returned, and if the relevant document was not in the top-k, it is gone. The bottleneck is the query representation, and the query is the one thing you can cheaply change before you search.

Query expansion changes it. Instead of embedding the bare keywords, you first grow the query into the language the answer would use — expand it with the concepts a full answer contains, or generate a hypothetical answer to the query and embed that (the HyDE technique: a hypothetical document embedding). The expanded query lands in the specific region of the space where the relevant document actually lives, so it retrieves what the raw query walked past. This module makes that concrete: a raw query that ranks an off-topic distractor above the relevant document, and an expanded query — same documents, same index, same scorer — that puts the relevant document first. Everything runs offline against a vector fixture, stdlib Python 3, `$0.00`, with every similarity computed. The instinct to unlearn is that retrieval quality is a property of the index. It is bounded by the query, and a vague query is a ceiling no downstream stage can lift.

## Concepts

Named here so you can find them again; each is built below.

- **Query embedding** — the vector for the search query; where in the space the search starts.
- **Vague query** — a short, underspecified query whose embedding is generic and mislocated.
- **Query expansion** — rewriting the query into the fuller language the answer uses, before embedding.
- **HyDE** — generating a hypothetical answer and embedding that instead of the raw query.
- **The miss** — the relevant document ranked below a distractor, so it never reaches the top-k.
- **Query-bounded retrieval** — the ceiling a poor query places on everything downstream.

## Worked example

Source: the query-encoding step of a dense retriever — turning the user's text into the vector the search runs on. The vectors stand in for real embeddings, with each dimension a concept, so the raw query's mislocation and the expanded query's fix are exact.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-09/` — `expand.py`, and `vectors.json`, one query and three documents. Every command runs from there.

### The raw query lands in the wrong neighborhood

Retrieval scores each document by cosine similarity to the query vector.

```
# expand.py:45-50 — COMPLETE (cosine similarity, the retrieval score)
def cosine(a, b):
    na, nb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))
    return dot(a, b) / (na * nb) if na and nb else 0.0
```

The relevant document `d_rel` covers concepts A, B, C. The raw query carries only concept A plus a spurious bit of concept D — the thin, generic signal a two-word query gives — so it sits near whatever shares A and D, which happens to be the off-topic distractor `d1`. Score the raw and expanded queries against every document:

```
# $ python3 expand.py --query
#   doc      relevant?  raw q    expanded q
#   d_rel    True       0.5164   1.0000
#   d1       False      0.7746   0.3333
#   d2       False      0.2582   0.0000
```

run: 2026-08-27 · deterministic; query and doc vectors are a fixture · 3 docs, dim 6 · `python3 expand.py --query`

<svg viewBox="0 0 700 180" role="img" aria-label="Similarity of each document to the raw query and the expanded query. Under the raw query, d1 (distractor) is highest at 0.77 and d_rel (answer) is 0.52 below it. Under the expanded query, d_rel is 1.0 and d1 drops to 0.33. The answer and distractor swap dominance.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">document similarity: raw query (left) vs expanded query (right)</text>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--line)"></line>
    <text x="180" y="168" text-anchor="middle" fill="var(--muted)" font-size="8">RAW QUERY</text>
    <rect x="100" y="88" width="40" height="62" fill="var(--s1)"></rect><text x="120" y="82" text-anchor="middle" fill="var(--s1)" font-size="7">d_rel .52</text>
    <rect x="160" y="57" width="40" height="93" fill="var(--s2)"></rect><text x="180" y="51" text-anchor="middle" fill="var(--s2)" font-size="7">d1 .77</text>
    <rect x="220" y="119" width="40" height="31" fill="var(--muted)"></rect><text x="240" y="113" text-anchor="middle" fill="var(--muted)" font-size="7">d2</text>
    <text x="490" y="168" text-anchor="middle" fill="var(--muted)" font-size="8">EXPANDED QUERY</text>
    <rect x="410" y="30" width="40" height="120" fill="var(--s1)"></rect><text x="430" y="24" text-anchor="middle" fill="var(--s1)" font-size="7">d_rel 1.0</text>
    <rect x="470" y="110" width="40" height="40" fill="var(--s2)"></rect><text x="490" y="104" text-anchor="middle" fill="var(--s2)" font-size="7">d1 .33</text>
    <rect x="530" y="150" width="40" height="2" fill="var(--muted)"></rect><text x="550" y="144" text-anchor="middle" fill="var(--muted)" font-size="7">d2 0</text>
  </g>
</svg>
^ Under the raw query the distractor d1 towers over the answer d_rel; under the expanded query the answer dominates and the distractor collapses. The bars swapped which is on top — that swap is the miss becoming a hit.

Under the raw query, the relevant document scores 0.5164 and the off-topic distractor `d1` scores 0.7746 — the distractor is more similar to the query than the answer is. The raw query is vague enough that its accidental overlap with `d1` (they both touch concepts A and D) outweighs its partial overlap with the real answer. Under the expanded query, `d_rel` scores a perfect 1.0000 and `d1` drops to 0.3333. The expanded query, stated in the full A-B-C language of the answer, points straight at the answer and away from the distractor.

<svg viewBox="0 0 700 210" role="img" aria-label="A 2D sketch of the embedding space. The relevant document d_rel and the off-topic distractor d1 are in different directions. The raw query points between them but closer to d1. The expanded query points directly at d_rel. Moving from raw to expanded rotates the query onto the answer.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">expanding the query rotates it off the distractor and onto the answer</text>
    <circle cx="90" cy="150" r="4" fill="var(--ink)"></circle><text x="70" y="165" fill="var(--muted)" font-size="7">origin</text>
    <line x1="90" y1="150" x2="300" y2="50" stroke="var(--s1)"></line><text x="305" y="48" fill="var(--s1)" font-size="8">d_rel (answer)</text>
    <line x1="90" y1="150" x2="330" y2="150" stroke="var(--s2)"></line><text x="335" y="153" fill="var(--s2)" font-size="8">d1 (distractor)</text>
    <line x1="90" y1="150" x2="300" y2="120" stroke="var(--muted)" stroke-dasharray="4 3"></line><text x="305" y="122" fill="var(--muted)" font-size="8">raw query (near d1)</text>
    <line x1="90" y1="150" x2="290" y2="55" stroke="var(--acc-line)"></line><text x="300" y="70" fill="var(--acc-ink)" font-size="8">expanded query (on d_rel)</text>
    <path d="M 250 128 Q 245 100 240 78" fill="none" stroke="var(--acc-line)" stroke-dasharray="2 2"></path><text x="200" y="100" fill="var(--acc-ink)" font-size="7">expand →</text>
    <text x="90" y="195" fill="var(--muted)" font-size="8">the raw query leans toward the distractor; expansion swings it onto the answer's direction</text>
  </g>
</svg>
^ The raw query points between the answer and the distractor but leans toward the distractor; expansion rotates it onto the answer's direction. The documents and the scorer never moved — only where the query points.

### The miss becomes a hit

Ranking is cosine similarity, sorted; the only thing that changes the order is the query.

```
# expand.py:52-61 — COMPLETE (rank documents by similarity; find the relevant doc's rank)
def ranked(query, docs):
    """Docs best-first by cosine similarity to the query."""
    scored = [(d["id"], round(cosine(query, d["vec"]), 4)) for d in docs]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored


def rank_of(query, docs, target):
    order = [i for i, _ in ranked(query, docs)]
    return order.index(target) + 1
```

```
# $ python3 expand.py --rank
#   raw query:      ['d1', 'd_rel*', 'd2']
#   expanded query: ['d_rel*', 'd1', 'd2']
```

run: 2026-08-27 · deterministic · `python3 expand.py --rank`

Under the raw query the order is `d1`, `d_rel`, `d2` — the relevant document is at rank 2, behind the distractor. If the retriever returns only the top-1, the answer is missed entirely; and crucially, nothing downstream can fix that, because a reranker or a second-stage scorer only ever sees the documents retrieval handed up, and if you fetched only `d1` the answer is not in the pile. Under the expanded query the order is `d_rel`, `d1`, `d2` — the relevant document is first. Same three documents, same cosine scorer; the expansion changed the query from one that misses to one that hits, upstream of everything else.

**A short, vague query embeds into a generic region of the space and can rank an off-topic distractor above the answer (0.77 vs 0.52, a miss at rank 1), so retrieval quality is bounded by the query, not just the index — expanding the query into the answer's fuller language (or embedding a hypothetical answer, HyDE) relocates it onto the relevant document (1.00 vs 0.33, a hit), a fix no downstream reranker can supply because it must act before retrieval, not after.**

### The self-test

The `--check` mode plants the bug — searching with the raw query — and proves it: the raw query misses the relevant document, the expanded query retrieves it first, expansion raises similarity to the answer, and it flips the relevance gap from negative to positive.

```
# $ python3 expand.py --check
#   the raw query ranks the relevant doc below rank 1 (a miss) = True (rank 2)
#   the expanded query ranks the relevant doc first = True (rank 1)
#   expansion raises similarity to the relevant doc = True (0.5164 -> 1.0000)
#   expansion turns a negative relevance gap positive = True (raw -0.258, expanded 0.667)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 expand.py --check`

That gap is computed as the answer's score minus the best distractor's, under each query — negative means a distractor wins:

```
# expand.py:106-111 — COMPLETE (the relevance gap flips from negative to positive)
    best_distractor = max((cosine(data["raw"], d["vec"]) for d in docs if d["id"] != rel))
    raw_gap = cosine(data["raw"], rel_vec) - best_distractor
    exp_best_distractor = max((cosine(data["expanded"], d["vec"]) for d in docs if d["id"] != rel))
    exp_gap = cosine(data["expanded"], rel_vec) - exp_best_distractor
    discriminates = raw_gap < 0 < exp_gap
```

<svg viewBox="0 0 700 150" role="img" aria-label="A pipeline: query, then expand, then embed, then retrieve, then rerank. A bracket marks that expand and retrieve are upstream, and rerank only reorders what retrieve returned, so a query fixed at the expand stage cannot be fixed at the rerank stage.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">expansion acts upstream of retrieval; rerank only reorders what was fetched</text>
    <rect x="30" y="50" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="70" y="69" text-anchor="middle" fill="var(--ink)" font-size="8">query</text>
    <rect x="130" y="50" width="90" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="175" y="69" text-anchor="middle" fill="var(--acc-ink)" font-size="8">EXPAND</text>
    <rect x="240" y="50" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="280" y="69" text-anchor="middle" fill="var(--ink)" font-size="8">embed</text>
    <rect x="340" y="50" width="90" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="385" y="69" text-anchor="middle" fill="var(--ink)" font-size="8">retrieve</text>
    <rect x="450" y="50" width="90" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="495" y="69" text-anchor="middle" fill="var(--muted)" font-size="8">rerank</text>
    <line x1="110" y1="65" x2="130" y2="65" stroke="var(--ink)"></line><line x1="220" y1="65" x2="240" y2="65" stroke="var(--ink)"></line><line x1="320" y1="65" x2="340" y2="65" stroke="var(--ink)"></line><line x1="430" y1="65" x2="450" y2="65" stroke="var(--ink)"></line>
    <text x="385" y="105" text-anchor="middle" fill="var(--muted)" font-size="7">if the answer isn't in here ↑</text>
    <text x="495" y="105" text-anchor="middle" fill="var(--s2)" font-size="7">↑ rerank can't add it</text>
    <text x="175" y="105" text-anchor="middle" fill="var(--acc-ink)" font-size="7">fix the query here →</text>
  </g>
</svg>
^ Expansion sits at the front of the pipeline; retrieval decides which documents exist downstream, and rerank only reorders them. A query that misses the answer must be fixed at the expand stage, because no later stage can conjure a document retrieval did not fetch.

The `discriminates` line is the sharpest way to state the fix. The relevance gap is the answer's score minus the best distractor's score: under the raw query it is −0.258 (the distractor wins), under the expanded query it is +0.667 (the answer wins by a lot). Expansion did not just nudge the answer up a little; it reversed the sign of the competition, which is the difference between the answer being retrievable and not.

```
# expand.py:94-98 — COMPLETE (the raw query misses; the expanded query ranks the answer first)
    raw_misses = raw_rank > 1
    print("  the raw query ranks the relevant doc below rank 1 (a miss) = %s (rank %d)" % (raw_misses, raw_rank))

    exp_rank = rank_of(data["expanded"], docs, rel)
    expanded_finds = exp_rank == 1
    print("  the expanded query ranks the relevant doc first = %s (rank %d)" % (expanded_finds, exp_rank))
```

### The running tally

| | raw query | expanded query |
|---|---|---|
| cosine to d_rel (answer) | 0.5164 | 1.0000 |
| cosine to d1 (distractor) | 0.7746 | 0.3333 |
| relevance gap (answer − best distractor) | −0.258 | +0.667 |
| rank of the answer | 2 (missed) | 1 (found) |

Read the rows top to bottom for each column: under the raw query the answer scores lower than the distractor, so the gap is negative and the answer is missed; under the expanded query the answer dominates, the gap is positive, and it is found. The only input that changed between the two columns is the query vector. That is the whole point — the documents, the index, and the similarity function are constants, and the entire difference between a failed search and a successful one lives in how the query was stated before it was embedded. Fix the query and you fix the retrieval; leave the query vague and no later stage can.

### What we did not settle

This is the case for expanding the query; production adds mechanics and caveats. HyDE generates the hypothetical answer with an LLM, which costs a model call and can hallucinate — but the hallucinated answer only has to be in the right neighborhood, not correct, since it is discarded after embedding. Expansion is not free: over-expanding can drift the query toward a generic centroid and hurt precision, so it helps most for short or ambiguous queries and least for already-specific ones. Multi-query expansion (embed several rewrites and merge the results) hedges against any single expansion going wrong. And expansion composes with the rest of the pipeline: it improves recall at the retrieval stage, which is exactly the stage a reranker (`retrieval-inter-05`) cannot repair, so the two are complements — expand to get the answer into the top-k, rerank to order it well. The invariant: state the query like the answer before you search, because retrieval cannot return what the query never pointed at.

## Build

The build in one paragraph: before embedding a search query, expand it into the fuller language the answer would use — add the concepts a real answer contains, or generate a hypothetical answer and embed that (HyDE) — so the query lands in the region of the space where the relevant document lives rather than a thin generic neighborhood near anything sharing a keyword; this fixes retrieval upstream, where a reranker cannot help because it only reorders what was already fetched. Reserve expansion for short or ambiguous queries, guard against over-expansion drifting toward a generic centroid, hedge with multi-query expansion, and pair it with reranking (expand for recall, rerank for order).

We opened on the two queries. The number that proves the fix is the rank of the answer under each:

```
# modules/context-and-retrieval/code/retrieval-inter-09/ — COMPLETE, run from that directory
$ python3 expand.py --rank
  raw query:      ['d1', 'd_rel*', 'd2']
  expanded query: ['d_rel*', 'd1', 'd2']
```

Now build your own. Take a short real query that retrieves poorly, expand it (add concepts, or generate a hypothetical answer with a model), and embed both. Your number to beat is not the index size; it is **the rank of the relevant document under the raw query versus the expanded one** — expansion should move it from missed toward rank 1. Confirm the raw query is fooled by a distractor and expansion reverses that. Bring back both ranks. Good luck.

## Definition of done

- [ ] Cosine-similarity retrieval over document embeddings
- [ ] A raw (vague) query and an expanded query
- [ ] A relevant document a distractor outranks under the raw query
- [ ] Confirmation the raw query ranks the relevant document below rank 1 (a miss)
- [ ] Confirmation the expanded query ranks the relevant document first
- [ ] Confirmation expansion raises similarity to the answer and flips the relevance gap positive
- [ ] `python3 expand.py --check` printing SELF-TEST PASS: raw_misses, expanded_finds, raises, discriminates
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a short query embed into a generic region and land near the wrong documents?
2. Why can't a reranker fix a query that misses the relevant document?
3. What is HyDE, and why does it not matter if the hypothetical answer is factually wrong?
4. What is the risk of over-expanding a query?
5. Your own vague query was expanded. What rank did the relevant document get before and after, and did a distractor fool the raw query?

## External resources

- Gao et al., *Precise Zero-Shot Dense Retrieval without Relevance Labels* (HyDE) — my summary: generating a hypothetical answer and embedding it to relocate the query; read it for why an imperfect generated answer still helps.
- Query expansion literature (pseudo-relevance feedback, RM3, and LLM-based rewrites) — my summary: the family of techniques for enriching a query before search; read it for the classical methods this module abstracts.
- This hub, *retrieval-inter-05* (rerank for precision) and *retrieval-inter-07* (cosine, not raw dot) — read them for the downstream stage expansion complements and the scorer it relies on.
