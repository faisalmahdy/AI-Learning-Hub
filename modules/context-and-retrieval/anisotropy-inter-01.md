---
id: anisotropy-inter-01
title: Subtract the corpus mean before cosine — anisotropic embeddings share a dominant direction that survives normalization and misranks retrieval
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Cosine similarity is meant to compare direction, and it does normalize away magnitude — but it does not normalize away a direction that every vector shares, and real transformer embeddings share one. They are anisotropic: instead of spreading over the sphere they pack into a narrow cone all pointing roughly the same way, so every pair of embeddings already has a high cosine before you compare anything, the scores bunch into a narrow high band, and the single direction they all share dominates the similarity. A distractor with a large component along that shared direction scores high with the query for the wrong reason — not because it answers the query but because it points the same generic way everything does — and it can outrank the true match. Normalizing to unit length does not help, because the shared direction is a direction, not a length, and survives normalization intact. The fix estimates the shared direction as the corpus mean and subtracts it from every vector; what remains is each vector's residual, its distinguishing signal, and cosine on the centered residuals spreads the scores out and ranks by real similarity. On a fixture where the shared direction is the first axis and the query's real signal is on the second, raw cosine ranks a distractor first (0.9285 vs 0.9080, all scores in a 0.07 band) while centered cosine ranks the true match first (0.2548 vs 0.0909, spread 0.78).
eli5: Imagine a room where everyone is facing almost the same way — toward a big window — and you want to find the one person actually looking at you. If you just measure who is facing your general direction, almost everyone scores high, because they are all facing the window anyway, and the person turned most toward the window beats the person genuinely looking at you. The shared pull of the window drowns out the small real differences. The fix is to first note the average direction everyone is facing and mentally subtract it, so you are left with only how each person differs from the crowd — and now the one turned toward you stands out clearly. Embeddings have the same problem: they all lean the same generic way, so you subtract that shared lean (the average vector) before comparing, and the real match finally stands out.
---

## Why this module

Cosine similarity has a clean story: it measures the angle between two vectors, ignoring how long they are, so it compares meaning rather than magnitude. A neighboring module makes exactly that case — rank by direction, not by raw dot product, so a long vector cannot outvote a better-aimed short one. This module is about a second, sneakier failure that cosine does not fix, and that you hit even after you have switched to cosine.

The catch is that cosine removes one thing vectors can share — their length — but not another, which is a common direction. Real embedding models do not scatter their outputs evenly over the sphere. The vectors clump into a narrow cone, all leaning the same generic way, and that shared lean is a direction, so normalizing to unit length leaves it completely intact. Every embedding still points mostly the same way as every other, and cosine, which only sees direction, is now comparing vectors that are already 90-something percent aligned before the query is even involved.

The consequence for retrieval is concrete: scores bunch into a narrow high band where nothing is distinguishable, and a document that merely leans hard into the shared direction scores high with the query for the wrong reason. This module builds a tiny embedding space with that shared direction baked in, runs a query, and watches a distractor beat the true match — then removes the shared direction and watches the ranking correct itself.

**Cosine normalizes away magnitude but not a shared direction, and real embeddings are anisotropic — they cluster in a cone with one dominant shared direction — so raw cosine scores are compressed into a high band and a document aligned with the shared direction can outrank the true match.**

## Concepts

The property has a name: anisotropy, meaning "not the same in all directions." An isotropic embedding space would spread its vectors evenly, so a random pair would have a cosine near zero and there would be lots of room to separate a good match from a bad one. Transformer embeddings are the opposite — anisotropic — with a strongly preferred direction, so a random pair has a high positive cosine and the vectors live in a thin cone rather than filling the sphere.

Think about what that does to a query. When every vector already points mostly along the shared cone axis, the part of the cosine that comes from the shared direction is large and roughly the same for every candidate, while the part that comes from the actual query-specific signal is small. The big shared term swamps the small distinguishing term, so the ranking is decided mostly by how much each candidate leans into the cone — not by how well it answers the query. A distractor that happens to sit far out along the shared axis wins on the shared term alone.

It helps to see one candidate split into its two parts: a large shared component along the cone axis plus a small residual that carries its real, distinguishing signal.

<svg role="img" aria-label="A candidate vector decomposed into a long shared component pointing along the cone axis and a short residual component perpendicular to it. The shared component is much longer than the residual, so raw cosine is dominated by the shared part while the residual carries the real signal." viewBox="0 0 440 150">
<line x1="40" y1="120" x2="330" y2="120" stroke="var(--grid)"/>
<text x="335" y="123" fill="var(--muted)" font-size="8">shared cone axis</text>
<line x1="40" y1="120" x2="300" y2="70" stroke="var(--s1)"/>
<text x="250" y="82" fill="var(--s1)" font-size="8">candidate vector</text>
<line x1="40" y1="120" x2="290" y2="120" stroke="var(--muted)" stroke-dasharray="4 3"/>
<text x="150" y="134" fill="var(--muted)" font-size="8" text-anchor="middle">shared component (large)</text>
<line x1="290" y1="120" x2="300" y2="70" stroke="var(--s2)"/>
<text x="330" y="95" fill="var(--s2)" font-size="8">residual (small — the real signal)</text>
</svg>
^ Every vector is a large shared component along the cone axis plus a small residual; raw cosine is dominated by the shared part, so centering keeps only the residual — the distinguishing signal.

<svg role="img" aria-label="Left: an anisotropic embedding space where the query and three document vectors all cluster into a narrow cone pointing the same way, so their pairwise angles are tiny and cosine cannot separate them. Right: after subtracting the corpus mean, the residual vectors fan out widely and the true match sits closest to the query." viewBox="0 0 440 180">
<text x="112" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">raw: a narrow cone</text>
<line x1="40" y1="150" x2="180" y2="150" stroke="var(--grid)"/>
<line x1="40" y1="150" x2="185" y2="70" stroke="var(--line)"/>
<line x1="40" y1="150" x2="178" y2="58" stroke="var(--line)"/>
<line x1="40" y1="150" x2="170" y2="52" stroke="var(--s1)"/>
<line x1="40" y1="150" x2="182" y2="64" stroke="var(--s2)"/>
<text x="188" y="70" fill="var(--muted)" font-size="8">B</text>
<text x="188" y="52" fill="var(--s1)" font-size="8">A</text>
<text x="150" y="44" fill="var(--s2)" font-size="8">query</text>
<text x="112" y="168" fill="var(--muted)" font-size="8" text-anchor="middle">all cosines high, no separation</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">centered: residuals fan out</text>
<circle cx="330" cy="110" r="3" fill="var(--ink)"/>
<line x1="330" y1="110" x2="400" y2="70" stroke="var(--s2)"/>
<line x1="330" y1="110" x2="395" y2="95" stroke="var(--s1)"/>
<line x1="330" y1="110" x2="270" y2="90" stroke="var(--muted)"/>
<line x1="330" y1="110" x2="300" y2="160" stroke="var(--muted)"/>
<text x="404" y="70" fill="var(--s2)" font-size="8">query</text>
<text x="399" y="98" fill="var(--s1)" font-size="8">A</text>
<text x="262" y="90" fill="var(--muted)" font-size="8">B</text>
<text x="330" y="172" fill="var(--muted)" font-size="8" text-anchor="middle">true match A nearest the query</text>
</svg>
^ Raw embeddings sit in a narrow cone where every angle is small and cosine cannot separate them; centering subtracts the cone's axis so the residuals fan out and the true match lands nearest the query.

The fix is to estimate the shared direction and subtract it. A good estimate is the corpus mean — the average of all the document vectors — because if every vector leans along the cone axis, so does their average. Subtract that mean from every vector, query included, and the shared component cancels: what remains is each vector's residual, how it differs from the generic direction, which is exactly the query-relevant signal you wanted to compare in the first place.

This is why centering is sometimes described as whitening's first step: it re-centers the cloud on the origin so that direction once again means something. Cosine on the residuals is now comparing distinguishing signals against distinguishing signals, the scores spread out across the full range instead of bunching near one, and the true match — which shares the query's real signal rather than just the generic lean — comes out on top.

**Estimate the shared direction as the corpus mean and subtract it from every vector; cosine on the residuals compares distinguishing signal to distinguishing signal, so the scores spread out and the true match ranks first.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/anisotropy-inter-01. The fixture is a query and three candidates in a three-dimensional space where the first axis is the shared cone direction: the query's real signal is on the second axis, the true match A shares it, and the distractors B and C lean hard into the first axis with little real signal.

```json filename=modules/context-and-retrieval/code/anisotropy-inter-01/anisotropy.json:3-9 COMPLETE
  "query": [10, 5, 0],
  "candidates": {
    "A": {"vector": [4, 5, 0], "label": "true match — shares the query's second-axis signal, small shared-axis component"},
    "B": {"vector": [12, 1, 0], "label": "distractor — large shared-axis (first-axis) component, little real signal"},
    "C": {"vector": [11, 0, 3], "label": "distractor — large shared-axis component, signal on the third axis"}
  },
  "true_match": "A"
```

Cosine is direction only — it divides out each vector's length, so magnitude cannot decide the ranking here.

```python filename=modules/context-and-retrieval/code/anisotropy-inter-01/anisotropy.py:39-44 COMPLETE
def cosine(a, b):
    """Similarity by direction: the dot product of the unit vectors (magnitude normalized away)."""
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)
```

The shared direction is estimated as the corpus mean, the average document vector.

```python filename=modules/context-and-retrieval/code/anisotropy-inter-01/anisotropy.py:47-51 COMPLETE
def mean_vector(vectors):
    """The corpus mean -- the average document vector, which points along the shared cone."""
    n = len(vectors)
    dims = len(vectors[0])
    return [sum(v[d] for v in vectors) / n for d in range(dims)]
```

The centered ranking subtracts the mean from the query and from each candidate — one subtraction each — then ranks by cosine on the residuals.

```python filename=modules/context-and-retrieval/code/anisotropy-inter-01/anisotropy.py:65-71 COMPLETE
def rank_centered(query, candidates):
    """Rank candidates by cosine after subtracting the corpus mean from the query and every candidate."""
    vectors = [c["vector"] for c in candidates.values()]
    m = mean_vector(vectors)
    q_c = subtract(query, m)
    scored = [(cid, cosine(q_c, subtract(c["vector"], m))) for cid, c in candidates.items()]
    return sorted(scored, key=lambda p: p[1], reverse=True)
```

Before running it, predict: A is the true match, so a healthy retriever ranks A first. Run `--raw` — cosine on the uncentered vectors:

```text filename=anisotropy.py --raw
RAW — cosine similarity of the query to each candidate (no centering)
------------------------------------------------------------
  B  cos = +0.9285   distractor — large shared-axis (first-axis) component, little real signal
  A  cos = +0.9080   true match — shares the query's second-axis signal, small shared-axis component
  C  cos = +0.8629   distractor — large shared-axis component, signal on the third axis
------------------------------------------------------------
  ranking: B > A > C   spread(top-bottom) = 0.0656
  the scores bunch in a narrow high band -- the signature of anisotropy
```

The prediction fails. B, the distractor, ranks first at 0.9285, above the true match A at 0.9080 — and cosine already normalized magnitude, so this is not a length problem the previous module would have caught. Notice the band: every score is between 0.86 and 0.93, a spread of only 0.0656. That compression is the fingerprint of anisotropy — the shared first-axis component is inflating every cosine, and B wins because it leans hardest into that shared axis, not because it answers the query.

Now subtract the corpus mean and rank the residuals. Run `--centered`:

```text filename=anisotropy.py --centered
CENTERED — cosine after subtracting the corpus mean [9.0, 2.0, 1.0]
------------------------------------------------------------
  A  cos = +0.2548   true match — shares the query's second-axis signal, small shared-axis component
  B  cos = +0.0909   distractor — large shared-axis (first-axis) component, little real signal
  C  cos = -0.5222   distractor — large shared-axis component, signal on the third axis
------------------------------------------------------------
  ranking: A > B > C   spread(top-bottom) = 0.7771
  centering removes the shared direction, so the scores spread out
```

The mean is (9, 2, 1) — dominated by the first axis, exactly the shared direction. Subtract it and the ranking flips to A first, the true match. And the spread jumps from 0.0656 to 0.7771: with the shared direction gone, the residuals fan out and the scores use the full range, so the gap between a real match and a distractor is now wide and obvious instead of a rounding error.

<svg role="img" aria-label="Two horizontal score scales. Raw: A, B, and C all cluster between 0.86 and 0.93 in a tiny band with B just above A. Centered: A at 0.25, B at 0.09, C at minus 0.52, spread wide apart with A clearly highest." viewBox="0 0 440 170">
<text x="20" y="24" fill="var(--muted)" font-size="9">raw cosine — all in a 0.07 band</text>
<line x1="30" y1="50" x2="410" y2="50" stroke="var(--line)"/>
<circle cx="360" cy="50" r="4" fill="var(--s2)"/>
<text x="360" y="40" fill="var(--s2)" font-size="8" text-anchor="middle">B .93</text>
<circle cx="352" cy="50" r="4" fill="var(--s1)"/>
<text x="340" y="66" fill="var(--s1)" font-size="8" text-anchor="middle">A .91</text>
<circle cx="335" cy="50" r="4" fill="var(--muted)"/>
<text x="322" y="40" fill="var(--muted)" font-size="8" text-anchor="middle">C .86</text>
<text x="20" y="108" fill="var(--muted)" font-size="9">centered cosine — spread 0.78</text>
<line x1="30" y1="134" x2="410" y2="134" stroke="var(--line)"/>
<line x1="70" y1="128" x2="70" y2="140" stroke="var(--grid)"/>
<text x="70" y="152" fill="var(--muted)" font-size="7" text-anchor="middle">0</text>
<circle cx="120" cy="134" r="4" fill="var(--s1)"/>
<text x="120" y="124" fill="var(--s1)" font-size="8" text-anchor="middle">A .25</text>
<circle cx="88" cy="134" r="4" fill="var(--s2)"/>
<text x="88" y="124" fill="var(--s2)" font-size="8" text-anchor="middle">B .09</text>
<circle cx="330" cy="134" r="4" fill="var(--muted)"/>
<text x="330" y="124" fill="var(--muted)" font-size="8" text-anchor="middle">C -.52</text>
</svg>
^ Raw cosine packs all three candidates into a 0.07 band with the distractor B on top; centering spreads them across 0.78 and lifts the true match A clearly above both distractors.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the shared direction (the mean) is larger than the average distinguishing residual, that the raw cosines are packed into a narrow high band, that raw cosine ranks a distractor above the true match, that centered cosine ranks the true match first, and that centering widens the score spread.

```python filename=modules/context-and-retrieval/code/anisotropy-inter-01/anisotropy.py:120-136 COMPLETE
    raw = rank_raw(query, candidates)
    raw_spread = spread(raw)
    anisotropy_compresses = raw_spread < 0.15 and min(s for _, s in raw) > 0.8
    print("  raw cosines are packed in a narrow high band = %s (spread %.4f, min %.4f)"
          % (anisotropy_compresses, raw_spread, min(s for _, s in raw)))

    raw_misranks = raw[0][0] != true_match
    print("  raw cosine ranks a distractor above the true match = %s (top is %s, true is %s)"
          % (raw_misranks, raw[0][0], true_match))

    centered = rank_centered(query, candidates)
    centering_corrects = centered[0][0] == true_match
    print("  centered cosine ranks the true match first = %s (top is %s)" % (centering_corrects, centered[0][0]))

    centered_spread = spread(centered)
    centering_widens_spread = centered_spread > raw_spread
    print("  centering widens the score spread = %s (%.4f > %.4f)" % (centering_widens_spread, centered_spread, raw_spread))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the raw scores ever stopped compressing or centering ever failed to correct the ranking:

```text filename=anisotropy.py --check
SELF-TEST — raw cosine misranks under anisotropy; centering corrects the ranking and widens the spread
----------------------------------------------------------------------------------------------------------------
  the shared direction is larger than the distinguishing signal = True (|mean|=9.27 > avg residual 4.23)
  raw cosines are packed in a narrow high band = True (spread 0.0656, min 0.8629)
  raw cosine ranks a distractor above the true match = True (top is B, true is A)
  centered cosine ranks the true match first = True (top is A)
  centering widens the score spread = True (0.7771 > 0.0656)
```

**The self-test asserts both that raw cosine misranks and that centering corrects it on the same fixture — and pins the mechanism by checking the shared direction outweighs the residual signal and that the score band goes from compressed to wide, so a pass means centering fixed the ranking for the stated reason, not by luck.**

## Definition of done

You can define anisotropy and explain why transformer embeddings pack into a narrow cone rather than filling the sphere.
You can explain why cosine removes magnitude but not a shared direction, so switching from dot product to cosine does not fix this.
You can explain why a narrow high band of similarity scores is the observable signature of anisotropy.
You can explain why subtracting the corpus mean removes the shared direction and why the residual is the query-relevant signal.
You can predict that centering both widens the score spread and can flip the ranking toward the true match.

## Boss fight

Suppose you center by the corpus mean and it helps, but a stubborn distractor still ranks too high. You suspect one shared direction was not enough. Reason about what to do. Anisotropy is often not a single dominant direction but a few: the top handful of principal components of the embedding cloud carry most of the shared variance. Centering removes only the first moment — the mean; it does not touch the next-strongest shared axes. The stronger fix, called all-but-the-top or whitening, removes the top few principal components entirely, and full whitening additionally rescales each remaining axis so the residual cloud is isotropic. Centering is the cheap first move; if it under-corrects, remove more shared structure, not less.

Now the trap that makes centering dangerous in production: what is the mean of, and when is it computed? The mean must be estimated over a representative sample of the corpus and then frozen, applied identically to every document at index time and to every query at search time. If you recompute the mean per batch, or over just the current query's candidates, the subtraction shifts from run to run and the scores stop being comparable across queries — you have traded a fixed bias for a moving one. And a query is a single vector, so its "mean" is itself; you never center a query by its own mean, you center it by the corpus mean. The rule is one mean, estimated once on the corpus, subtracted from everything.

**Centering removes only the first shared direction; if that under-corrects, remove the top few principal components (all-but-the-top or whitening) — and the mean must be estimated once on a representative corpus sample and frozen, applied identically to documents and queries, never recomputed per query or per batch.**

## External resources

Mu and Viswanath, "All-but-the-Top: Simple and Effective Postprocessing for Word Representations" (2018), shows that subtracting the mean and removing the top principal components makes embeddings more isotropic and improves similarity tasks.
Ethayarajh, "How Contextual are Contextualized Word Representations?" (2019), measures the anisotropy of BERT, ELMo, and GPT embeddings directly and reports how high random-pair cosine similarity is.
The BERT-flow and whitening papers (Li et al. 2020; Su et al. 2021) extend centering to full whitening transforms for sentence embeddings; the topic's own module on ranking by cosine versus raw dot product covers the separate magnitude-normalization step this one builds on.
