---
id: maxsim-inter-01
title: Score retrieval token by token (MaxSim), not by one mean-pooled vector — or a blurry doc outranks a real match
topic: context-and-retrieval
level: intermediate
status: ready
time: 17 min
summary: A single-vector retriever compresses a query and a document each into one embedding — usually the mean of their token vectors — and scores by the cosine between the two means. Fast, and fine when a document is about one thing, but the mean throws away which specific tokens matched which. A document that genuinely contains an exact match for each query term, buried among other tokens, ends up with a blended mean; a document full of vague tokens that half-match everything can have a mean that lands right on the query's mean. The mean cannot tell distinct tokens that each fully match a query term from one fuzzy token that partially matches all of them, so it can rank the vague document above the real answer. Late interaction (ColBERT's MaxSim) keeps the token vectors and scores by summing, over each query token, its maximum cosine to any document token — every query term goes looking for its best match. On a fixture, mean-pooling gives a blurry distractor a cosine of 1.00 to the query and the gold document only 0.89 (ranking the distractor first), while MaxSim gives the gold a perfect 2.00 (an exact match per query token) against the distractor's 1.41 (ranking the gold first).
eli5: To decide if a page answers your two-word question, you could blend both your words into one "average idea" and blend the whole page into one "average idea" and see if the averages feel alike. But a page that's vaguely about both your words — matching neither exactly — can have an average that looks just like yours, while the page that actually contains both your exact words gets its average muddied by everything else on it. Better to check each of your words separately: does the page contain a good match for word one? For word two? The page that answers both, word by word, is the real answer.
---

## Why this module

A mean-pooled embedding is a lossy summary that keeps a document's average direction and forgets which of its parts matched your query — so two documents that are nothing alike, term for term, can collapse to the same summary and be ranked as equals.

The dominant retrieval design embeds a query and a document each as a single vector and ranks by their cosine similarity. Where does that single vector come from? Usually by pooling the per-token vectors — most simply, averaging them. Averaging is a drastic compression: a document of hundreds of tokens becomes one point, and that point is the centroid of all its token meanings. The centroid answers "what is this document about, on average?" but not "does this document contain the specific thing I asked for?" — and those are different questions. A document that mentions your rare query term once, in a sea of common tokens, has a centroid barely nudged toward that term. A document that never contains your term but is full of tokens each pointing halfway toward it has a centroid that can sit exactly where yours does. To the cosine of the means, the second looks like a better match than the first, which is precisely backwards.

**Mean-pooling a document to one vector keeps its average direction and discards which tokens matched the query, so a document whose tokens each half-match everything can outscore one that contains an exact match for every query term — the summary cannot distinguish real term matches from a coincidental average.**

Late interaction refuses the lossy summary on the scoring side while keeping it cheap on the indexing side. It stores every token's vector for every document (precomputed offline, like any embedding index), and at query time it scores with MaxSim: for each query token, find its single best-matching document token (the maximum cosine over all document tokens), and sum those best matches across the query. Now every query term independently searches the document for its match, and a term that finds an exact hit contributes fully while a term with no real match contributes little — regardless of how the rest of the document averages out. This recovers the term-level precision the mean destroys, and it sits between the fast-but-coarse single-vector bi-encoder and the accurate-but-slow cross-encoder. This module ranks the same two documents both ways and watches them disagree on the winner.

## Concepts

**Single-vector (bi-encoder) scoring** mean-pools each side to one vector and takes the cosine. It is one dot product per document, but the pooling is where the term-level signal is lost.

```python filename=modules/context-and-retrieval/code/maxsim-inter-01/maxsim.py:59-61 COMPLETE
def single_vector_score(query_tokens, doc_tokens):
    """Bi-encoder score: cosine between the mean-pooled query and the mean-pooled document."""
    return cosine(mean_vec(query_tokens), mean_vec(doc_tokens))
```

**MaxSim (late interaction)** keeps the token vectors and sums, over each query token, its maximum cosine to any document token — each query term finds its own best match.

```python filename=modules/context-and-retrieval/code/maxsim-inter-01/maxsim.py:64-66 COMPLETE
def maxsim_score(query_tokens, doc_tokens):
    """Late-interaction score: for each query token, its best cosine to any doc token, summed."""
    return sum(max(cosine(q, d) for d in doc_tokens) for q in query_tokens)
```

**A query term's contribution is its best single match.** MaxSim rewards a document for containing, somewhere, a token that matches the term — not for its average leaning toward the term — which is what makes it robust to dilution.

<svg role="img" aria-label="Single-vector scoring collapses query and doc to one mean each and compares; MaxSim keeps tokens and each query token picks its best matching doc token" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">single-vector: compare two means</text>
  <circle cx="40" cy="30" r="4" fill="var(--s2)"/><text x="48" y="33" fill="var(--muted)" font-size="7">query mean</text>
  <line x1="44" y1="30" x2="120" y2="30" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <circle cx="124" cy="30" r="4" fill="var(--s2)"/><text x="132" y="33" fill="var(--muted)" font-size="7">doc mean</text>
  <text x="200" y="33" fill="var(--muted)" font-size="7">one cosine, term signal lost</text>
  <line x1="6" y1="46" x2="292" y2="46" stroke="var(--grid)"/>
  <text x="6" y="60" fill="var(--muted)" font-size="8">MaxSim: each query token → its best doc token</text>
  <circle cx="40" cy="76" r="3" fill="var(--s1)"/><text x="24" y="79" fill="var(--muted)" font-size="7">q1</text>
  <circle cx="40" cy="96" r="3" fill="var(--s1)"/><text x="24" y="99" fill="var(--muted)" font-size="7">q2</text>
  <g stroke="var(--s1)"><line x1="44" y1="76" x2="150" y2="72"/><line x1="44" y1="96" x2="150" y2="100"/></g>
  <circle cx="154" cy="72" r="3" fill="var(--ink)"/><circle cx="154" cy="86" r="3" fill="var(--muted)"/><circle cx="154" cy="100" r="3" fill="var(--ink)"/>
  <text x="170" y="80" fill="var(--muted)" font-size="7">each term finds its best match, summed</text>
</svg>
^ Single-vector scoring compares one mean per side and loses which token matched; MaxSim keeps the tokens and lets each query token pick its best-matching document token, summing those individual matches.

**MaxSim scores a document by how well each query term individually finds a match in it, so it recovers the term-level precision a single mean-pooled vector averages away.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/maxsim-inter-01/maxsim.py

The fixture is a two-token query and two documents: a gold doc with an exact match for each query token, and a blurry distractor whose mean coincides with the query's.

```json filename=modules/context-and-retrieval/code/maxsim-inter-01/maxsim.json:3-8 COMPLETE
  "query": [[1.0, 0.0], [0.0, 1.0]],
  "documents": {
    "A_gold": [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    "B_distractor": [[0.5, 0.5], [0.5, 0.5]]
  },
  "gold": "A_gold"
```

Run `--score` to rank the documents both ways.

```text filename=--score
SCORE — single-vector (mean-pool) ranking vs MaxSim (late interaction)
------------------------------------------------------------------
  single-vector (bi-encoder):
    B_distractor   1.000
    A_gold         0.894  <- gold
  MaxSim (late interaction):
    A_gold         2.000  <- gold
    B_distractor   1.414
```

The single-vector retriever ranks B_distractor first at a perfect cosine of 1.000 and the gold A at 0.894 — a confident, wrong answer. Here is why: the query's two tokens average to [0.5, 0.5], and the distractor's two [0.5, 0.5] tokens average to exactly [0.5, 0.5], so their means align perfectly. The gold document, meanwhile, contains three tokens pointing at [1, 0] and one at [0, 1], so its mean is [0.75, 0.25] — pulled toward the more common token, and no longer aligned with the balanced query mean. Mean-pooling rewarded the distractor for being uniformly vague and penalized the gold for having a majority token, even though the gold actually contains both things the query asked for and the distractor contains neither. MaxSim reverses it: the gold scores 2.000 (each query token finds an exact match) and the distractor 1.414 (each query token only half-matches a [0.5, 0.5] token). Same documents, same query, opposite winners — and MaxSim's winner is the one that genuinely answers the query.

<svg role="img" aria-label="The bi-encoder ranks B_distractor 1.00 above A_gold 0.894; MaxSim ranks A_gold 2.00 above B_distractor 1.41" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">rankings (✦ = gold); the top result flips</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">bi-encoder</text>
  <rect x="80" y="22" width="150" height="12" fill="var(--s2)"/><text x="234" y="32" fill="var(--muted)" font-size="7">B 1.00</text>
  <rect x="80" y="36" width="134" height="12" fill="var(--s1)"/><text x="218" y="46" fill="var(--muted)" font-size="7">✦ A 0.89</text>
  <line x1="6" y1="56" x2="292" y2="56" stroke="var(--grid)"/>
  <text x="6" y="72" fill="var(--muted)" font-size="8">MaxSim</text>
  <rect x="80" y="64" width="200" height="12" fill="var(--s1)"/><text x="120" y="74" fill="var(--panel)" font-size="7">✦ A 2.00</text>
  <rect x="80" y="78" width="141" height="12" fill="var(--s2)"/><text x="225" y="88" fill="var(--muted)" font-size="7">B 1.41</text>
  <text x="6" y="100" fill="var(--muted)" font-size="8">the bi-encoder puts the distractor on top; MaxSim puts the gold on top</text>
</svg>
^ The bi-encoder ranks the blurry distractor above the gold (1.00 vs 0.89); MaxSim ranks the gold above the distractor (2.00 vs 1.41) — the same inputs, opposite top results.

## Build

Why the gap? Run `--tokens` to see each query term hunt for its match.

```text filename=--tokens
TOKENS — each query token's best match (max cosine) in each document
------------------------------------------------------------
  query token 0 = [1.0, 0.0]:
    best match in A_gold         = 1.000
    best match in B_distractor   = 0.707
  query token 1 = [0.0, 1.0]:
    best match in A_gold         = 1.000
    best match in B_distractor   = 0.707
```

Each query token, judged on its own, tells the true story. Query token 0 ([1, 0]) finds a perfect 1.000 match in the gold (which contains [1, 0] tokens) and only a 0.707 in the distractor (whose [0.5, 0.5] tokens are 45 degrees off). Query token 1 ([0, 1]) likewise finds its exact match in the gold and only a half-match in the distractor. MaxSim sums these — 1.000 + 1.000 = 2.000 for the gold, 0.707 + 0.707 = 1.414 for the distractor — so the gold wins because it satisfies *both* terms exactly, while the distractor never fully satisfies either. This is the information mean-pooling destroyed: the mean of the gold's tokens is not [1, 0] or [0, 1], it is the blended [0.75, 0.25], so the single vector no longer shows that the exact matches are in there. MaxSim never blends; it lets each term reach into the document and grab its best token. That is why late interaction shines on queries with a rare or specific term that a document contains but that a document's average washes out — long documents, multi-aspect queries, exact entity or code-token matches — the cases where "what is this about on average" and "does this contain what I asked" diverge most.

<svg role="img" aria-label="For both query tokens, the gold has a best match of 1.0 while the distractor has 0.707" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">best match per query token (max cosine)</text>
  <text x="6" y="32" fill="var(--muted)" font-size="8">token 0</text>
  <rect x="60" y="24" width="180" height="12" fill="var(--s1)"/><text x="130" y="34" fill="var(--panel)" font-size="7">gold 1.00</text>
  <rect x="60" y="38" width="127" height="10" fill="var(--s2)"/><text x="190" y="47" fill="var(--muted)" font-size="7">distractor 0.71</text>
  <text x="6" y="66" fill="var(--muted)" font-size="8">token 1</text>
  <rect x="60" y="58" width="180" height="12" fill="var(--s1)"/><text x="130" y="68" fill="var(--panel)" font-size="7">gold 1.00</text>
  <rect x="60" y="72" width="127" height="10" fill="var(--s2)"/><text x="190" y="81" fill="var(--muted)" font-size="7">distractor 0.71</text>
  <text x="6" y="93" fill="var(--muted)" font-size="8">the gold exactly satisfies both terms (sum 2.0); the distractor half-satisfies each (sum 1.41)</text>
</svg>
^ Both query tokens find an exact 1.00 match in the gold and only a 0.71 half-match in the distractor, so MaxSim sums to 2.00 for the gold and 1.41 for the distractor — the per-term view mean-pooling collapsed.

## Definition of done

The self-test pins the disagreement and its cause: mean-pooling ranks the distractor first, MaxSim ranks the gold first, the gold's MaxSim is a perfect per-token match, and every query token finds an exact match in the gold.

```python filename=modules/context-and-retrieval/code/maxsim-inter-01/maxsim.py:113-126 COMPLETE
    single_vector_wrong = sv[0][0] != gold
    print("  the single-vector retriever ranks a non-gold doc first = %s (top = %s)" % (single_vector_wrong, sv[0][0]))

    maxsim_right = ms[0][0] == gold
    print("  MaxSim ranks the gold doc first = %s (top = %s)" % (maxsim_right, ms[0][0]))

    gold_maxsim_perfect = abs(maxsim_score(q, docs[gold]) - len(q)) < 1e-9
    print("  the gold's MaxSim is the perfect %d (an exact match per query token) = %s (%.3f)" % (len(q), gold_maxsim_perfect, maxsim_score(q, docs[gold])))

    maxsim_gold_beats_distractor = maxsim_score(q, docs[gold]) > max(maxsim_score(q, t) for n, t in docs.items() if n != gold)
    print("  the gold's MaxSim beats every distractor's = %s" % maxsim_gold_beats_distractor)

    per_token_exact = all(max(cosine(qt, d) for d in docs[gold]) > 0.999 for qt in q)
    print("  every query token finds an exact match in the gold = %s" % per_token_exact)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — mean-pooling ranks the distractor first; MaxSim ranks the gold first with a perfect per-token match
--------------------------------------------------------------------------------------------------------------
  the single-vector retriever ranks a non-gold doc first = True (top = B_distractor)
  MaxSim ranks the gold doc first = True (top = A_gold)
  the gold's MaxSim is the perfect 2 (an exact match per query token) = True (2.000)
  the gold's MaxSim beats every distractor's = True
  every query token finds an exact match in the gold = True
```

**Done means the two scorers are proven to disagree and MaxSim to be right: the single-vector retriever ranks the blurry distractor first (cosine 1.00 vs the gold's 0.89), while MaxSim ranks the gold first (2.00 vs 1.41) because every query token finds an exact 1.00 match in the gold and only a 0.71 half-match in the distractor — the term-level signal the mean-pool collapsed.**

## Boss fight

Predict the two prices late interaction charges for its precision. It is tempting to think MaxSim is strictly better than a single vector.

The first trap is storage and speed: keeping every token's vector is far more expensive than keeping one per document. A single-vector index stores one embedding per document; a late-interaction index stores one per token, so for documents of hundreds of tokens the index is one to two orders of magnitude larger, and the MaxSim computation is a query-token-by-document-token similarity matrix rather than a single dot product. That is why ColBERT-style systems invest heavily in compression (quantizing the token vectors, often to a few bits each) and in a two-stage pipeline: a cheap approximate first pass to shortlist candidates, then MaxSim only on the shortlist. Late interaction is a middle point on the cost-accuracy curve — more accurate and more expensive than a bi-encoder, less accurate and less expensive than a full cross-encoder — and choosing it means accepting the larger index and the reranking cost for the term-level precision, not getting that precision for free.

```python filename=modules/context-and-retrieval/code/maxsim-inter-01/maxsim.py:53-56 COMPLETE
def mean_vec(tokens):
    """Mean-pool a bag of token vectors into a single vector -- what a bi-encoder indexes."""
    dim = len(tokens[0])
    return [sum(t[i] for t in tokens) / len(tokens) for i in range(dim)]
```

The second trap is that MaxSim's "each term grabs its best match" is a strength that is also a specific failure mode: it rewards a document for containing a match for every query term *independently*, with no requirement that the matches be coherent or that the document not also contain contradictions. A document can score a perfect MaxSim by scattering the query's terms across unrelated sentences — the term matches are all present, just not together — so late interaction can over-reward keyword coverage the way a bag-of-words model does, missing that the terms need to relate. It also has no notion of a term appearing the *right number of times* or in the right role, since only the single best match per query token counts; a second, third, or negating occurrence is invisible to the max. That is exactly the gap a cross-encoder closes by attending jointly over query and document, at much higher cost. So the honest picture is a spectrum: single-vector pooling loses term identity, MaxSim recovers term identity but not term interaction, and a cross-encoder recovers interaction but cannot precompute. Pick the point on that spectrum your latency budget and your queries' term-sensitivity justify.

**Late interaction (MaxSim) scores retrieval by summing each query token's best match to any document token, recovering the term-level precision a single mean-pooled vector blurs away — so it ranks a document that genuinely contains every query term above a blurry one whose average merely coincides with the query — but it costs a per-token index (one to two orders larger, mitigated by quantization and a shortlist stage) and it rewards independent per-term matches without requiring them to be coherent, so it sits between the cheap-but-coarse bi-encoder and the accurate-but-uncachable cross-encoder, chosen when term-level precision is worth the index and reranking cost.**

## External resources

The ColBERT papers (Khattab and Zaharia, "ColBERT" and "ColBERTv2") — the definition of late interaction and MaxSim, the token-vector indexing, and the compression and candidate-generation techniques that make it practical.

Any survey of retrieval architectures contrasting bi-encoders (single-vector, dual-tower), late interaction (multi-vector), and cross-encoders — the cost-versus-accuracy spectrum and where each belongs in a pipeline.

The companion "retrieve with the bi-encoder, rerank with the cross-encoder" and "rank dense retrieval by cosine, not raw dot product" modules — the first places late interaction on the same spectrum between the two extremes, and the second is the single-vector scoring this module contrasts with, so together they cover how a match is scored from one vector, from token vectors, and from full cross-attention.
