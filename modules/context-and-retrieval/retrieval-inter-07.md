---
id: retrieval-inter-07
title: Rank dense retrieval by cosine, not raw dot product — or vector length outvotes meaning
topic: context-and-retrieval
level: intermediate
status: ready
time: 5-8h
summary: Dense retrieval scores a query embedding against document embeddings, and the tempting score is the raw dot product because it is one multiply-and-add and it is what a matrix multiply hands you — but the dot product multiplies alignment (direction, which is meaning) by magnitude (length, which for an embedding is mostly an artifact), so a long, only-vaguely-related document outscores a short, exactly-on-topic one purely by being big. On the fixture the dot product crowns d_big — an off-topic vector with dot 6 and cosine 0.447 — over the perfectly-aligned d_rel (dot 4, cosine 1.0), and it buries the small on-topic d_small (dot 1) dead last, while cosine, which divides out both norms, ranks the two relevant docs first and d_big last and lifts d_small from last to the top. The lesson is that similarity is direction, cosine is the dot product of the unit vectors, and once you normalize every embedding to unit length the dot product and cosine coincide — which is exactly why every dense index stores normalized vectors and the magnitude trap disappears.
eli5: Imagine matching people by which way they're pointing. The right way is to see who points most nearly the same direction as you. A lazy shortcut multiplies "same direction" by "how tall the person is," so a giant pointing roughly sideways beats a short person pointing exactly your way — height drowns out direction. The fix is to shrink everyone to the same height first and then compare directions; now only where they point matters, and the short on-topic person you'd buried comes right back to the top.
---

## Why this module

A dense retriever turns the query and every document into an embedding — a vector in some high-dimensional space where "means the same thing" is supposed to be "points the same way" — and then it needs a number for how well each document matches the query. The number almost everyone reaches for first is the dot product, for two good reasons: it is a single multiply-and-accumulate per dimension, and it is literally what a matrix multiply of the query against the document matrix computes, so it is free when you already have the vectors. It is also, used directly, the wrong number.

The dot product of two vectors is their alignment times their magnitudes: `a · b = |a| |b| cos(θ)`. The `cos(θ)` factor is the part you want — it is the angle between the directions, which is the semantic similarity. But it is multiplied by `|a| |b|`, the lengths, and an embedding's length is largely an artifact — of how long the text was, of quirks in how the model scales its outputs — not of relevance. So a document that points only vaguely toward the query but happens to be a long vector can post a bigger dot product than a document that points exactly at the query but is short. Magnitude outvotes meaning, and your top result is the loud document, not the relevant one.

<svg viewBox="0 0 700 150" role="img" aria-label="The dot product decomposed as three boxes multiplied: cosine of the angle (the meaning you want), times the norm of a, times the norm of b (the magnitudes, mostly artifact). An arrow shows cosine dividing out both norms to leave cosine alone.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">a · b = cos(θ) × |a| × |b| — the dot product mixes meaning with length</text>
    <rect x="40" y="44" width="120" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="100" y="60" text-anchor="middle" fill="var(--acc-ink)" font-size="8">cos(θ)</text><text x="100" y="75" text-anchor="middle" fill="var(--acc-ink)" font-size="7">meaning ✓</text>
    <text x="172" y="68" fill="var(--muted)">×</text>
    <rect x="190" y="44" width="90" height="40" fill="var(--panel)" stroke="var(--s2)"></rect><text x="235" y="60" text-anchor="middle" fill="var(--s2)" font-size="8">|a|</text><text x="235" y="75" text-anchor="middle" fill="var(--s2)" font-size="7">length</text>
    <text x="288" y="68" fill="var(--muted)">×</text>
    <rect x="306" y="44" width="90" height="40" fill="var(--panel)" stroke="var(--s2)"></rect><text x="351" y="60" text-anchor="middle" fill="var(--s2)" font-size="8">|b|</text><text x="351" y="75" text-anchor="middle" fill="var(--s2)" font-size="7">length</text>
    <text x="410" y="68" fill="var(--muted)" font-size="8">÷ |a| |b|  →</text>
    <rect x="500" y="44" width="150" height="40" fill="var(--s1)"></rect><text x="575" y="60" text-anchor="middle" fill="var(--panel)" font-size="8">cos(θ) = cosine</text><text x="575" y="75" text-anchor="middle" fill="var(--panel)" font-size="7">meaning alone</text>
    <text x="40" y="122" fill="var(--muted)" font-size="8">cosine divides the two length boxes back out, leaving only the angle — the part that is relevance</text>
  </g>
</svg>
^ The dot product is the cosine multiplied by both vectors' lengths; cosine divides those lengths back out and keeps only the angle. Rank by the whole product and length distorts the order; rank by cosine and only meaning remains.

Cosine similarity removes the magnitudes by dividing them back out: `cos(θ) = (a · b) / (|a| |b|)`, which is the same as taking the dot product of the two vectors after rescaling each to unit length. Only direction survives. This module builds both scorers on one query and four documents — with a big off-topic document and a small on-topic one planted specifically to expose the trap — shows the dot product crowning the irrelevant document and burying the small relevant one, and shows cosine putting both relevant documents on top. Everything runs offline against a vector fixture, stdlib Python 3, `$0.00`, with every dot, norm, and cosine computed. The instinct to unlearn is that the dot product is the similarity. Similarity is the cosine; the dot product is the cosine only after you have normalized, which is why dense indexes normalize.

## Concepts

Named here so you can find them again; each is built below.

- **Embedding** — a vector standing for a query or document; direction is meaning, length is mostly artifact.
- **Dot product** — alignment times magnitudes; cheap, and biased toward long vectors.
- **Norm** — a vector's length, the square root of its dot product with itself.
- **Cosine similarity** — the dot product divided by both norms; alignment alone.
- **Normalization** — rescaling a vector to unit length, after which dot product equals cosine.
- **The magnitude trap** — a long off-topic vector outscoring a short on-topic one under dot product.

## Worked example

Source: the scoring step of a dense retriever — the point where a query embedding is compared to document embeddings to pick the nearest. The vectors stand in for real embeddings, kept tiny and integer so every dot, norm, and cosine is exact and you can see the trap in the numbers.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-07/` — `cosine.py`, and `vectors.json`, one query and four documents. Every command runs from there.

### The two scores

The dot product, the norm, and the cosine are three lines, each built from the one before.

```
# cosine.py:44-58 — COMPLETE (dot product, norm, and cosine)
def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cosine(a, b):
    """Dot product of the unit vectors: alignment only, magnitude divided out."""
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)
```

`cosine` is `dot` divided by the two norms — the same alignment, with the lengths taken out. That single division is the entire difference between a ranker that measures meaning and one that measures loudness. Look at the four documents scored both ways:

```
# $ python3 cosine.py --docs
#   id        vec              dot     norm    cosine   relevant
#   d_rel     [2, 2, 0]        4.00    2.83    1.000    True
#   d_big     [5, 1, 8]        6.00    9.49    0.447    False
#   d_med     [1, 0, 1]        1.00    1.41    0.500    False
#   d_small   [0.5, 0.5, 0]    1.00    0.71    1.000    True
```

run: 2026-08-27 · deterministic; the query and doc vectors are a fixture · 4 docs, dim 3 · `python3 cosine.py --docs`

Read `d_rel` against `d_big`. `d_rel` points exactly where the query points — cosine 1.000, perfectly on topic — but its dot product is only 4.00. `d_big` points mostly elsewhere — cosine 0.447, off topic — but its dot product is 6.00, because its norm is 9.49, more than three times `d_rel`'s. On the dot product, the off-topic document wins, entirely on length. And `d_small` points exactly at the query too (cosine 1.000) but is a short vector, so its dot product is a mere 1.00 — the most on-topic document, scored dead last by the dot product.

<svg viewBox="0 0 700 210" role="img" aria-label="A 2D sketch of directions from the origin. The query points up-right along the diagonal. d_rel and d_small point along the same diagonal (aligned, cosine 1.0), d_small short and d_rel longer. d_big points mostly to the right and far, a long vector at a wide angle (cosine 0.447). d_med points partway. The dot product favors the long d_big; cosine favors the aligned d_rel and d_small.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">direction is relevance; length is not — but the dot product multiplies them</text>
    <line x1="60" y1="180" x2="60" y2="40" stroke="var(--line)"></line>
    <line x1="60" y1="180" x2="360" y2="180" stroke="var(--line)"></line>
    <line x1="60" y1="180" x2="230" y2="50" stroke="var(--muted)" stroke-dasharray="4 3"></line><text x="234" y="46" fill="var(--muted)" font-size="8">query direction</text>
    <line x1="60" y1="180" x2="180" y2="88" stroke="var(--s1)"></line><text x="184" y="86" fill="var(--s1)" font-size="8">d_rel (cos 1.0)</text>
    <line x1="60" y1="180" x2="120" y2="134" stroke="var(--s1)"></line><text x="124" y="132" fill="var(--s1)" font-size="8">d_small (cos 1.0)</text>
    <line x1="60" y1="180" x2="340" y2="120" stroke="var(--s2)"></line><text x="344" y="118" fill="var(--s2)" font-size="8">d_big (cos 0.447, long)</text>
    <text x="400" y="60" fill="var(--muted)" font-size="8">by dot product: d_big first (length wins)</text>
    <text x="400" y="80" fill="var(--s1)" font-size="8">by cosine: d_rel, d_small first (angle wins)</text>
    <text x="400" y="120" fill="var(--muted)" font-size="8">d_big sits at a wide angle but reaches</text>
    <text x="400" y="134" fill="var(--muted)" font-size="8">far, so its dot product is inflated</text>
  </g>
</svg>
^ d_rel and d_small lie along the query's direction (cosine 1.0); d_big sits at a wide angle but is a long vector, so its dot product is the largest. The dot product rewards reach, cosine rewards angle.

### The two rankings

Ranking is the same sort under either score; only the score function changes.

```
# cosine.py:67-71 — COMPLETE (rank best-first by a score function; ties broken by id)
def rank_by(query, docs, score):
    """Docs sorted best-first by a score(query, vec) function; ties broken by id for determinism."""
    scored = [(d["id"], score(query, d["vec"])) for d in docs]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored
```

Rank the four documents each way:

```
# $ python3 cosine.py --rank
#   by dot product:  ['d_big', 'd_rel*', 'd_med', 'd_small*']
#   by cosine:       ['d_rel*', 'd_small*', 'd_med', 'd_big']
#   (* = relevant)
```

run: 2026-08-27 · deterministic · `python3 cosine.py --rank`

The two orderings are nearly reversed. The dot product puts `d_big` — off topic — at the top and pushes both relevant documents down, with `d_small` last. Cosine puts the two relevant documents `d_rel` and `d_small` first and drops `d_big` to the bottom where its wide angle belongs. If you retrieve the top-1, the dot product hands the model an irrelevant document; if you retrieve the top-2, the dot product misses `d_small` entirely while cosine returns exactly the two on-topic ones. The retrieval quality difference is not a better model or better embeddings — it is dividing by the norms.

<svg viewBox="0 0 700 180" role="img" aria-label="Two ranked lists side by side. By dot product, top to bottom: d_big (irrelevant, highlighted as wrong at top), d_rel, d_med, d_small (relevant, at bottom). By cosine: d_rel (relevant, top), d_small (relevant), d_med, d_big (irrelevant, bottom). Arrows show d_big falling from top to bottom and d_small rising from bottom to near top.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">dot-product ranking vs cosine ranking (best at top)</text>
    <text x="90" y="40" fill="var(--s2)">by dot</text>
    <rect x="60" y="48" width="120" height="20" fill="var(--s2)"></rect><text x="120" y="62" text-anchor="middle" fill="var(--panel)" font-size="8">d_big (off-topic)</text>
    <rect x="60" y="70" width="120" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="84" text-anchor="middle" fill="var(--acc-ink)" font-size="8">d_rel *</text>
    <rect x="60" y="92" width="120" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="106" text-anchor="middle" fill="var(--muted)" font-size="8">d_med</text>
    <rect x="60" y="114" width="120" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="128" text-anchor="middle" fill="var(--acc-ink)" font-size="8">d_small *</text>
    <text x="500" y="40" fill="var(--s1)">by cosine</text>
    <rect x="470" y="48" width="120" height="20" fill="var(--s1)"></rect><text x="530" y="62" text-anchor="middle" fill="var(--panel)" font-size="8">d_rel *</text>
    <rect x="470" y="70" width="120" height="20" fill="var(--s1)"></rect><text x="530" y="84" text-anchor="middle" fill="var(--panel)" font-size="8">d_small *</text>
    <rect x="470" y="92" width="120" height="20" fill="var(--panel)" stroke="var(--line)"></rect><text x="530" y="106" text-anchor="middle" fill="var(--muted)" font-size="8">d_med</text>
    <rect x="470" y="114" width="120" height="20" fill="var(--panel)" stroke="var(--s2)"></rect><text x="530" y="128" text-anchor="middle" fill="var(--s2)" font-size="8">d_big (off-topic)</text>
    <path d="M 180 58 Q 320 90 470 124" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></path><text x="320" y="86" fill="var(--s2)" font-size="7">d_big falls</text>
    <path d="M 180 124 Q 320 150 470 80" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"></path><text x="320" y="150" fill="var(--s1)" font-size="7">d_small rises</text>
  </g>
</svg>
^ Dividing by the norms flips the ranking: the off-topic d_big falls from first to last and the small on-topic d_small rises from last to the top group. Cosine returns exactly the relevant documents in the top two.

**Embedding similarity is the angle between vectors, so rank by cosine — the dot product of the unit vectors — not the raw dot product, which multiplies alignment by magnitude and lets a long off-topic document outscore a short on-topic one; normalize every embedding to unit length and the dot product becomes cosine, which is why dense indexes store normalized vectors.**

### The self-test

The `--check` mode plants the bug — ranking by raw dot product — and proves it: the dot-product top-1 is irrelevant, the cosine top-1 is relevant, and the small on-topic document buried last by the dot product returns to the top under cosine.

```
# $ python3 cosine.py --check
#   dot-product top-1 is NOT relevant = True (d_big)
#   cosine top-1 IS relevant = True (d_rel)
#   the small on-topic doc 'd_small': dot rank 3 (last), cosine rank 1 (top-2) = True
#   cosine == dot product of the unit vectors = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 cosine.py --check`

The premise the whole test rests on is read straight off the top of each ranking — whether the best-scored document is actually relevant:

```
# cosine.py:111-114 — COMPLETE (the two top-1 assertions: dot picks irrelevant, cosine picks relevant)
    dot_top_irrelevant = not rel[by_dot[0][0]]
    print("  dot-product top-1 is NOT relevant = %s (%s)" % (dot_top_irrelevant, by_dot[0][0]))

    cos_top_relevant = rel[by_cos[0][0]]
    print("  cosine top-1 IS relevant = %s (%s)" % (cos_top_relevant, by_cos[0][0]))
```

The last line of the run is the one that names the fix precisely: cosine is not a different similarity, it is the dot product computed on the normalized vectors. So the practical move in a real system is not to change the scoring code at query time — it is to normalize every embedding once when you index it, after which the fast raw dot product your vector database already computes *is* cosine. The bug and the fix are the same operation; the only question is whether you did the division before storing.

```
# cosine.py:60-64 — COMPLETE (normalize to unit length; then dot product equals cosine)
def normalize(a):
    n = norm(a)
    return [x / n for x in a] if n else a
```

### The running tally

| doc | dot | cosine | relevant | dot rank | cosine rank |
|---|---|---|---|---|---|
| d_rel | 4.00 | 1.000 | yes | 2nd | 1st |
| d_big | 6.00 | 0.447 | no | 1st | 4th |
| d_med | 1.00 | 0.500 | no | 3rd | 3rd |
| d_small | 1.00 | 1.000 | yes | 4th | 2nd |

Read the two rank columns against the relevant column. Cosine's ranks put the two `yes` rows first; the dot product's ranks put a `no` row first and a `yes` row last. The only rows whose rank agrees between the two scores are the ones where magnitude did not distort the picture. Everywhere magnitude and direction disagree — the big off-topic vector, the small on-topic one — the dot product follows magnitude and cosine follows direction, and direction is what relevance means.

### What we did not settle

This is the core normalization fix; retrieval has more around it. Some embedding models are trained so that magnitude carries a little real signal (confidence or specificity), and a few systems keep it deliberately — but the default assumption should be cosine, and you deviate only with evidence. Euclidean (L2) distance is the other common metric, and on unit-normalized vectors it induces the same ranking as cosine, so normalization reconciles them too. The scores here feed ranking directly; a hybrid pipeline (`retrieval-adv-01`) fuses these dense scores with lexical ones, and fusion assumes each score is a sane similarity, which cosine is and raw dot is not. And a reranker (`retrieval-inter-05`) can only reorder what retrieval returns, so a dot-product retriever that drops `d_small` from the top-k denies the reranker any chance to recover it. The invariant is small and firm: normalize, then the dot product is cosine, and similarity is angle.

## Build

The build in one paragraph: score a query embedding against document embeddings by cosine — the dot product divided by both norms, equivalently the dot product of the unit-length vectors — never the raw dot product, which multiplies alignment by magnitude and lets a long off-topic vector outrank a short on-topic one; and in a real index, normalize every embedding to unit length once at indexing time so the fast raw dot product your database computes is already cosine. Confirm on a planted big-off-topic and small-on-topic pair that the raw dot product ranks them wrong and cosine ranks them right. Reconcile L2 distance by normalizing, feed cosine (not raw dot) into any fusion, and remember a reranker cannot recover what a magnitude-biased retriever dropped.

We opened on the four scores. The number that proves the fix is which document each ranking puts first:

```
# modules/context-and-retrieval/code/retrieval-inter-07/ — COMPLETE, run from that directory
$ python3 cosine.py --rank
  by dot product:  ['d_big', 'd_rel*', 'd_med', 'd_small*']
  by cosine:       ['d_rel*', 'd_small*', 'd_med', 'd_big']
```

Now build your own. Take real query and document embeddings — from any encoder — and include a long off-topic document and a short on-topic one. Your number to beat is not the raw score; it is **the relevance of the top-1 and the top-2 under raw dot product versus cosine** — the dot product should surface the long off-topic doc and miss the short on-topic one, while cosine surfaces the relevant ones. Then normalize your vectors and confirm the dot product now matches cosine. Bring back both rankings. Good luck.

## Definition of done

- [ ] Dot product, norm, and cosine (dot over the product of norms)
- [ ] Ranking of documents by each score
- [ ] A fixture with a long off-topic vector and a short on-topic one
- [ ] Confirmation the dot-product top-1 is irrelevant and the cosine top-1 is relevant
- [ ] Confirmation the small on-topic doc is last by dot product and top by cosine
- [ ] Confirmation cosine equals the dot product of the normalized vectors
- [ ] `python3 cosine.py --check` printing SELF-TEST PASS: dot_top_irrelevant, cos_top_relevant, small_rescued, cosine_is_normdot
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Decompose the dot product into alignment and magnitude. Which part is relevance, and which is mostly artifact?
2. Why does d_big outrank d_rel under the dot product despite being off topic?
3. What is cosine similarity in terms of the dot product and the norms, and equivalently in terms of normalized vectors?
4. Why is the practical fix "normalize at indexing time" rather than "change the query-time score"?
5. Your own embeddings were ranked both ways. Which doc was top-1 under each score, and did normalizing make the dot product match cosine?

## External resources

- Any dense-retrieval or vector-database documentation on similarity metrics (cosine vs dot vs L2) — my summary: why cosine is the default, when dot is used (on already-normalized vectors), and how L2 relates; read it for the metric your index actually applies.
- Sentence-embedding model cards that specify "normalize embeddings before use" — my summary: the one-line instruction most encoders ship and the reason behind it; read it to see the fix stated as a model requirement.
- This hub, *retrieval-adv-01* (the hybrid pipeline) and *retrieval-inter-05* (rerank for precision) — read them for how these dense scores fuse with lexical ones and why a magnitude-biased retriever starves the reranker.
