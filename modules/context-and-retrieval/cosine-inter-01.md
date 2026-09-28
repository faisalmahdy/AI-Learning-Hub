---
id: cosine-inter-01
title: Rank by direction (cosine), not raw dot product — an unnormalized vector's magnitude outranks a better match
topic: context-and-retrieval
level: intermediate
status: ready
time: 14 min
summary: Vector search works because an embedding turns meaning into direction: two texts that mean the same thing get vectors pointing the same way, so you retrieve by finding the document vector most aligned with the query. "Most aligned" means the smallest angle, which is cosine similarity — the dot product divided by the two vectors' magnitudes, so it depends only on direction and lives in [−1, 1]. The trap is using the raw dot product without normalizing: the dot product is alignment times magnitude, so it rewards a vector for being long as well as for pointing the right way, and a document whose embedding happens to have a large magnitude can outscore one that is genuinely more aligned. Magnitude is usually incidental — it tracks document length or token frequency, not relevance — so dot-product ranking on unnormalized vectors biases retrieval toward high-norm documents. The fix is to normalize to unit length (or use cosine directly); once every vector has magnitude 1, dot product and cosine are the same number. On a fixture with query [1, 0], doc_aligned = [1, 0.1] (cosine 0.995, short) versus doc_offaxis = [2.1, 2.1] (cosine 0.707, three times longer), raw dot product scores doc_offaxis 2.10 over doc_aligned 1.00 and ranks the wrong one first, while cosine scores doc_aligned 0.995 over doc_offaxis 0.707 and ranks the aligned one first; normalizing makes the dot product equal the cosine.
eli5: Think of each document as an arrow, and you want the arrow pointing most nearly the same way as your question's arrow. What matters is the DIRECTION, not how long the arrow is. But the plain dot product secretly rewards long arrows: a big arrow pointing somewhat the wrong way can score higher than a small arrow pointing exactly right. Since an arrow's length often just reflects boring things like how long the document is, you'd be picking documents for being long instead of relevant. The fix is to shrink every arrow to the same length first, so only its direction counts — then the arrow pointing the right way wins, as it should.
---

## Why this module

Two similarity functions differ by one division, and picking the wrong one silently reweights your entire index toward long documents. The dot product and cosine agree on which direction is best but disagree the moment vector lengths differ — and embedding lengths differ all the time, for reasons that have nothing to do with relevance.

Vector search works because an embedding turns meaning into direction: two texts that mean the same thing get vectors that point the same way, so you retrieve by finding the document vector most aligned with the query vector. "Most aligned" means the smallest angle, which is cosine similarity — the dot product divided by the two vectors' magnitudes, so it depends only on direction and lives in [−1, 1]. The trap is using the raw dot product instead, without normalizing. The dot product is alignment *times* magnitude, so it rewards a vector for being long as well as for pointing the right way, and a document whose embedding happens to have a large magnitude can outscore a document that is genuinely more aligned with the query. Magnitude is usually incidental — it tracks things like document length or token frequency, not relevance — so ranking by dot product on unnormalized vectors quietly biases retrieval toward long or high-norm documents regardless of what they are about.

The fix is to normalize the vectors to unit length (divide each by its magnitude) before comparing, or equivalently to use cosine similarity directly. Once every vector has magnitude 1, the dot product and the cosine are the same number, so the magnitude bias is gone and ranking is purely by direction. Most embedding pipelines normalize at index time for exactly this reason; the ones that use raw dot product do so only because their model was trained to produce unit-norm embeddings already, which is the same condition by another name. This module ranks two documents both ways and shows the magnitude bias and its fix.

**Semantic similarity is the angle between embeddings, so rank by cosine (the dot product divided by the magnitudes) or on normalized vectors — ranking by the raw dot product rewards vector magnitude, letting a longer but less-aligned document outrank a more relevant one.**

## Concepts

**Cosine similarity** is the dot product divided by both magnitudes, so it measures only the angle and ignores length — the query and a document are similar exactly when their vectors point the same way.

```python filename=modules/context-and-retrieval/code/cosine-inter-01/cosine.py:54-55 COMPLETE
def cosine(u, v):
    return dot(u, v) / (norm(u) * norm(v))
```

**Normalizing** to unit length divides a vector by its own magnitude. After it, every vector has length 1, so the dot product of two unit vectors *is* their cosine — the two similarity functions collapse into one.

```python filename=modules/context-and-retrieval/code/cosine-inter-01/cosine.py:58-60 COMPLETE
def unit(u):
    n = norm(u)
    return [x / n for x in u]
```

<svg role="img" aria-label="Query vector along the x-axis, a short doc_aligned vector nearly parallel to it, and a long doc_offaxis vector at 45 degrees; cosine measures the angle while dot product also scales with length" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">cosine = angle only; dot = angle × length</text>
  <line x1="30" y1="110" x2="30" y2="24" stroke="var(--line)"/><line x1="30" y1="110" x2="285" y2="110" stroke="var(--line)"/>
  <line x1="30" y1="110" x2="250" y2="110" stroke="var(--ink)"/><text x="252" y="114" fill="var(--muted)" font-size="7">query</text>
  <line x1="30" y1="110" x2="130" y2="98" stroke="var(--s1)"/><text x="132" y="98" fill="var(--muted)" font-size="7">doc_aligned (short, cos 0.995)</text>
  <line x1="30" y1="110" x2="180" y2="40" stroke="var(--s2)"/><text x="150" y="34" fill="var(--muted)" font-size="7">doc_offaxis (long, cos 0.707)</text>
  <path d="M70,110 A40,40 0 0,0 62,96" fill="none" stroke="var(--s2)"/><text x="72" y="90" fill="var(--muted)" font-size="6">45°</text>
</svg>
^ doc_aligned points almost along the query (a tiny angle, cosine 0.995) but is short; doc_offaxis is 45° off (cosine 0.707) but much longer — cosine cares only about the angle, while the raw dot product also multiplies by that greater length.

**Cosine ranks by the angle alone; a unit-normalized dot product is the same thing — so comparing directions means either dividing out the magnitudes or storing vectors that already have magnitude 1.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/cosine-inter-01/cosine.py

The fixture is a query and two documents, with the truly-relevant (aligned) one marked gold.

```json filename=modules/context-and-retrieval/code/cosine-inter-01/cosine.json:3-8 COMPLETE
  "query": [1.0, 0.0],
  "docs": {
    "doc_aligned": [1.0, 0.1],
    "doc_offaxis": [2.1, 2.1]
  },
  "gold": "doc_aligned"
```

Run `--rank` to score both similarities.

```text filename=--rank
RANK — dot product vs cosine for query [1.0, 0.0]
--------------------------------------------------------------
  doc           dot     |vector|   cosine
  doc_aligned   1.00    1.005      0.995
  doc_offaxis   2.10    2.970      0.707
--------------------------------------------------------------
  ranked by dot product : ['doc_offaxis', 'doc_aligned']   (top = doc_offaxis)
  ranked by cosine      : ['doc_aligned', 'doc_offaxis']   (top = doc_aligned, the gold doc_aligned)
```

The two similarity functions rank the documents in opposite order. By cosine, doc_aligned scores 0.995 and doc_offaxis 0.707 — the aligned document is far more similar in direction, which is correct, because it points almost exactly along the query. By raw dot product, doc_offaxis scores 2.10 and doc_aligned 1.00 — the off-axis document wins. Read the middle column to see why: doc_offaxis has magnitude 2.970 versus doc_aligned's 1.005, nearly three times longer. The dot product is cosine times the two magnitudes, so doc_offaxis's larger length more than compensates for its worse angle: 0.707 × 2.970 × 1 = 2.10 beats 0.995 × 1.005 × 1 = 1.00. The document that wins under dot product wins for being *long*, not for being relevant, and if that extra magnitude came from the document simply being wordier — which is exactly what raw embedding norms often track — then dot-product retrieval has ranked verbosity over relevance.

<svg role="img" aria-label="Dot product decomposed as cosine times magnitude: doc_aligned has high cosine but small length giving 1.00, doc_offaxis has low cosine but large length giving 2.10, so magnitude flips the ranking" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">dot = cosine × magnitude — length flips the order</text>
  <g font-size="6">
  <text x="10" y="36" fill="var(--muted)">aligned</text>
  <rect x="60" y="28" width="99" height="10" fill="var(--s1)"/><text x="62" y="36" fill="var(--panel)">cos 0.995</text>
  <text x="164" y="36" fill="var(--muted)">× |1.005|  = dot 1.00</text>
  <text x="10" y="60" fill="var(--muted)">offaxis</text>
  <rect x="60" y="52" width="70" height="10" fill="var(--s2)"/><text x="62" y="60" fill="var(--panel)">cos 0.707</text>
  <text x="135" y="60" fill="var(--muted)">× |2.970|  = dot 2.10 ← wins</text>
  </g>
  <text x="10" y="88" fill="var(--muted)" font-size="7">cosine picks aligned (0.995 &gt; 0.707); multiplying by length hands it to offaxis</text>
  <text x="10" y="102" fill="var(--muted)" font-size="7">the magnitude, not the relevance, decided the dot-product winner</text>
</svg>
^ The dot product is each document's cosine multiplied by its magnitude, so doc_offaxis's near-3× length overpowers its worse angle (0.707 × 2.970 = 2.10) and beats doc_aligned's better angle at a shorter length (0.995 × 1.005 = 1.00).

## Build

Normalizing both vectors to unit length erases the magnitude and makes the dot product agree with cosine. Run `--normalize`.

```text filename=--normalize
NORMALIZE — unit-length vectors: dot product becomes cosine
------------------------------------------------------------
  doc           dot(raw)   dot(normalized)   cosine
  doc_aligned   1.000      0.995             0.995
  doc_offaxis   2.100      0.707             0.707
```

After normalizing the query and each document to length 1, the dot product of the unit vectors is 0.995 for doc_aligned and 0.707 for doc_offaxis — exactly the cosine values, and now the aligned document ranks first. This is the whole fix: a unit vector's dot product *is* its cosine, so normalizing at index time lets a system use the fast, simple dot product (which vector databases and hardware optimize heavily) while still ranking by direction. The choice is not "dot product versus cosine" as two different philosophies; it is "normalize or not," and once you normalize they are the same operation. The reason some pipelines rank by raw dot product without an explicit normalization step is that their embedding model already emits unit-norm vectors — in which case the magnitudes are all 1 and there is nothing to bias the ranking. The danger is only when the vectors have uncontrolled magnitudes and you compare them with the bare dot product anyway.

```python filename=modules/context-and-retrieval/code/cosine-inter-01/cosine.py:63-65 COMPLETE
def rank_by(scores):
    """Doc ids sorted by score, highest first."""
    return sorted(scores, key=lambda d: scores[d], reverse=True)
```

<svg role="img" aria-label="Before and after normalization: raw dot product ranks the long off-axis doc first, normalized dot product equals cosine and ranks the aligned doc first" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">normalize to unit length → dot product becomes cosine</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">raw dot</text>
  <g transform="translate(70,24)" font-size="6">
  <rect x="0" y="0" width="50" height="12" fill="var(--s1)"/><text x="4" y="9" fill="var(--panel)">aligned 1.00</text>
  <rect x="60" y="0" width="105" height="12" fill="var(--s2)"/><text x="64" y="9" fill="var(--panel)">offaxis 2.10 ← wins</text>
  </g>
  <text x="10" y="66" fill="var(--muted)" font-size="7">normalized</text>
  <g transform="translate(70,56)" font-size="6">
  <rect x="0" y="0" width="100" height="12" fill="var(--s1)"/><text x="4" y="9" fill="var(--panel)">aligned 0.995 ← wins</text>
  <rect x="110" y="0" width="71" height="12" fill="var(--s2)"/><text x="114" y="9" fill="var(--panel)">offaxis 0.707</text>
  </g>
  <text x="10" y="96" fill="var(--muted)" font-size="7">same vectors, correct order once magnitude is divided out</text>
</svg>
^ Under raw dot product the long off-axis document wins (2.10 vs 1.00); after normalizing, the scores become the cosines (0.995 vs 0.707) and the aligned document wins — the reversal caused purely by removing the magnitude.

## Definition of done

The self-test pins the reversed rankings, the alignment and magnitude facts, and the normalization identity.

```python filename=modules/context-and-retrieval/code/cosine-inter-01/cosine.py:103-112 COMPLETE
    dot_ranks_offaxis = dot_rank[0] == off
    print("  the raw dot product ranks the off-axis doc first = %s (top = %s)" % (dot_ranks_offaxis, dot_rank[0]))

    cos_rank = rank_by({d: cosine(q, docs[d]) for d in docs})
    cosine_ranks_gold = cos_rank[0] == gold
    print("  cosine ranks the aligned gold doc first = %s (top = %s)" % (cosine_ranks_gold, cos_rank[0]))

    gold_more_aligned = cosine(q, docs[gold]) > cosine(q, docs[off])
    print("  the gold doc is more aligned (higher cosine) = %s (%.3f > %.3f)"
          % (gold_more_aligned, cosine(q, docs[gold]), cosine(q, docs[off])))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — dot ranks the higher-magnitude off-axis doc first; cosine ranks the aligned gold doc first; normalized dot equals cosine
--------------------------------------------------------------------------------------------------------------------------------
  the raw dot product ranks the off-axis doc first = True (top = doc_offaxis)
  cosine ranks the aligned gold doc first = True (top = doc_aligned)
  the gold doc is more aligned (higher cosine) = True (0.995 > 0.707)
  the off-axis doc has the larger magnitude = True (2.970 > 1.005)
  normalizing makes the dot product equal the cosine = True
```

**Done means the magnitude bias and its fix are proven on real scores: the raw dot product ranks the off-axis document first (2.10 > 1.00) even though the gold document is more aligned (cosine 0.995 > 0.707) and the off-axis one is only ahead because its magnitude is larger (2.970 > 1.005), while cosine — equivalently the dot product of the normalized vectors — ranks the aligned gold document first, so retrieval must compare direction, not raw dot product.**

## Boss fight

Predict two ways the choice of similarity is subtler than "always normalize," because normalization discards information that sometimes matters and the metric must match how the index was built.

The first trap is that the similarity function is not free to choose — it must match the space the embedding model was trained in, and mismatching it silently degrades retrieval. Models are trained with a specific similarity (cosine or dot product) baked into their loss, so their vector geometry is calibrated for that metric; a model trained for cosine expects normalized comparison, and using raw dot product on it reintroduces exactly the magnitude bias this module shows, while a model trained for maximum-inner-product search may deliberately encode useful information *in* the magnitude (for example, some models let a vector's norm express confidence or term importance), and normalizing it away throws that signal out. So "always normalize" is as wrong as "never normalize": the rule is to use the metric the model documents, and to be consistent between indexing and querying — a query normalized while the documents were not (or scored with cosine against a dot-product-trained index) gives quietly wrong rankings. The metric is a property of the model, not a preference.

The second trap is that the approximate index underneath vector search is built for one metric, so the metric is a structural choice, not just a scoring formula. Real systems do not compare the query against every vector; they use an approximate-nearest-neighbor index (HNSW, IVF, product quantization) that is constructed and tuned for a specific distance — inner product, cosine, or Euclidean — and its graph or clusters encode that geometry. Query it with a different metric than it was built for and the "nearest" neighbors it returns are wrong, not merely approximate. This is also why cosine is often implemented as normalize-then-inner-product rather than as its own metric: the index natively does inner-product (or L2) search, and normalizing the vectors at insert time turns inner product into cosine for free, so you get cosine ranking with the index's optimized inner-product machinery. Relatedly, on unit vectors cosine similarity and squared Euclidean distance are monotonically related (maximizing cosine equals minimizing L2 distance), so a normalized L2 index and a cosine index return the same ordering — which is why the practical advice reduces to one instruction: normalize your vectors at index time, then whichever of inner-product or L2 the index offers gives you cosine ranking. Pick the metric to match the model and the index, and normalization is the bridge that makes them agree.

**The similarity metric must match the embedding model (which is trained for cosine or for magnitude-carrying inner product — so both "always normalize" and "never normalize" are wrong) and must match the approximate index, which is built for one specific distance and returns wrong neighbors under another; the practical resolution is to normalize at index time, after which inner-product and L2 indexes both yield cosine ranking, keeping the model, the metric, and the index consistent.**

## External resources

Any vector-database or embedding documentation on similarity metrics (cosine, inner product, Euclidean) — why the metric must match the embedding model, and why cosine is commonly implemented as normalize-then-inner-product.

Writing on maximum-inner-product search and normalization — when embedding magnitude carries signal (so you keep the dot product) versus when it is incidental (so you normalize), and the monotone relationship between cosine and Euclidean distance on unit vectors.

The companion late-interaction (MaxSim) and reranking modules in this topic — they too compare query and document vectors, so they inherit the same requirement to normalize or use the model's intended metric consistently across indexing and querying.
