---
id: dimtrunc-inter-01
title: Truncating an embedding to fewer dimensions is safe only if the model front-loads its information
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Halving a vector store's dimension is a real way to cut cost and memory, and the tempting implementation is to slice every stored vector to its first k dimensions — but whether that is safe is a property of the embedding model, not of the slice. A Matryoshka-trained model (MRL) is optimized so the leading dimensions carry the most important directions, so a prefix of the vector is itself a usable lower-dimensional embedding and cosine ranking over the prefix still works. An ordinary model spreads the discriminating signal across the whole vector, so slicing off the tail can throw away exactly the dimensions that carried the answer and the truncated ranking flips. On the fixture both models rank the relevant document above the distractor at full dimension with identical cosines (0.923 vs 0.588), so at full width you cannot tell them apart; truncate to the first 3 of 6 dimensions and they diverge — the ordinary model scores the distractor 1.000 and the relevant document 0.000, a flip to the wrong answer, while the Matryoshka model still ranks the relevant document first, 1.000 to 0.577. Same truncation, opposite outcome, decided entirely by how the model laid out its dimensions. A second, separate point the same operation raises: truncating a unit-length vector (norm 3.606 here) leaves it no longer unit length (norm 1.000), so an index that ranks by raw dot product rather than cosine must renormalize after truncation, or every score is silently rescaled. The rule: dimension truncation is a capability you inherit from the embedding model, not an optimization you can apply to any vector.
eli5: Suppose each book is summarized by six numbers, and you want to save space by keeping only the first three. Whether that works depends on how the summary was written. Some are written so the three most important facts come first — cut the rest and you still know what the book is about. Others scatter the important facts anywhere across the six numbers, so cutting the last three might delete the one fact that told two books apart, and now you grab the wrong book. The catch is that at full length both kinds of summary look equally good, so you can't tell which kind you have just by using all six numbers — you find out only when you cut, and by then the wrong book is already on the pile. So you can shorten a summary only if it was written to be shortened.
---

## Why this module

Vector stores are expensive in proportion to their dimension: every stored embedding costs memory and every query costs a dot product across all its dimensions. Cutting the dimension in half is one of the biggest, simplest levers available, and slicing each vector to its first k components is the obvious way to pull it.

The trap is that this looks like a pure engineering optimization — a slice, a smaller array — when it is actually a question about the model. Some embeddings survive truncation and some are destroyed by it, and the two are indistinguishable at full width. You cannot audit for this by checking that retrieval works today; it works today at full dimension either way.

**Truncating an embedding is a capability you inherit from how the model was trained, not an optimization you can safely apply to any vector.**

## Concepts

An embedding places meaning in a direction, and cosine similarity ranks documents by how closely their direction matches the query's. Truncating to the first k dimensions projects every vector onto the leading k axes and ranks in that smaller space. Whether the smaller space preserves the ranking depends on where the model put the discriminating information.

Matryoshka Representation Learning trains the model so that the first few dimensions already form a good embedding, the next few refine it, and so on — like nested dolls, each prefix is a complete smaller embedding. The important, document-separating directions are front-loaded, so a prefix keeps them and the ranking survives. This is a deliberate training objective, not a property vectors have by default.

An ordinary embedding has no such structure. Its training only cared that the full vector ranked correctly, so the signal that separates a relevant document from a distractor can live anywhere across the dimensions — including entirely in the tail you are about to cut. Truncate it and you may delete exactly the axes that carried the answer, leaving the leading dimensions, which happened to hold whatever the two documents share.

The cruel part is that both kinds look identical at full dimension: same architecture, same cosine, same correct ranking. The difference is invisible until you truncate, which is why "we truncated and retrieval still passed the smoke test" is not evidence — the smoke test needs the specific documents whose signal lived in the tail.

**A Matryoshka model front-loads the separating signal so a prefix still ranks; an ordinary model may hold that signal in the dropped tail, and both look the same until you cut.**

<svg role="img" aria-label="A fork. At full dimension both the ordinary and Matryoshka models rank correctly. After truncation the path splits: the ordinary model flips to the wrong document, the Matryoshka model stays correct." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">identical at full width, diverge at the cut</text>
<text x="30" y="80" fill="var(--ink)" font-size="10">full dim:</text>
<text x="95" y="80" fill="var(--muted)" font-size="10">both rank relevant first</text>
<line x1="230" y1="76" x2="290" y2="52" stroke="var(--line)"></line>
<line x1="230" y1="82" x2="290" y2="108" stroke="var(--line)"></line>
<text x="200" y="66" fill="var(--muted)" font-size="9">truncate</text>
<text x="296" y="55" fill="var(--s2)" font-size="10">matryoshka: still correct</text>
<text x="296" y="112" fill="var(--s1)" font-size="10">ordinary: flips to wrong doc</text>
</svg>
^ The two models are one point at full dimension and two outcomes after the cut — truncation is where an invisible difference becomes a retrieval bug.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.py

The fixture embeds the same query and two documents with two models — one ordinary, one Matryoshka — in six dimensions.

```json filename=modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.json:3-14 COMPLETE
  "dim": 6,
  "k": 3,
  "ordinary": {
    "query":    [1, 0, 0, 2, 2, 2],
    "relevant": [0, 1, 0, 2, 2, 2],
    "distractor": [1, 0, 0, 0, 0, 1]
  },
  "matryoshka": {
    "query":    [2, 2, 2, 1, 0, 0],
    "relevant": [2, 2, 2, 0, 1, 0],
    "distractor": [0, 0, 1, 1, 0, 0]
  }
```

Ranking is cosine of the query against each document, optionally over a truncated prefix.

```python filename=modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.py:31-36 COMPLETE
def cosine(a, b):
    """Direction similarity: dot product over the product of norms."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)
```

```python filename=modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.py:49-55 COMPLETE
def rank(model, k=None):
    """Cosine of the query against each doc (optionally truncated to k dims), and which doc wins."""
    q = model["query"] if k is None else truncate(model["query"], k)
    rel = model["relevant"] if k is None else truncate(model["relevant"], k)
    dist = model["distractor"] if k is None else truncate(model["distractor"], k)
    cr, cd = cosine(q, rel), cosine(q, dist)
    return cr, cd, ("relevant" if cr > cd else "distractor")
```

At full dimension the two models are indistinguishable.

```text filename=dimtrunc.py --full
FULL — both models at full dimension 6
----------------------------------------------------------------
  ordinary    relevant=0.923  distractor=0.588  -> ranks relevant first
  matryoshka  relevant=0.923  distractor=0.588  -> ranks relevant first
----------------------------------------------------------------
  identical at full width: both models put the relevant document first
```

Both score the relevant document 0.923 and the distractor 0.588 — same numbers, both correct. Nothing here warns you that one of them is about to break.

<svg role="img" aria-label="Two six-cell vectors with a cut line after the third cell. The ordinary embedding has its dark, signal-carrying cells in the last three positions, past the cut. The Matryoshka embedding has its dark cells in the first three positions, before the cut." viewBox="0 0 460 170">
<rect x="0" y="0" width="460" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">where each model puts the separating signal (cut after 3)</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">ordinary</text>
<rect x="100" y="38" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<rect x="124" y="38" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<rect x="148" y="38" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<rect x="172" y="38" width="24" height="20" fill="var(--s2)"></rect>
<rect x="196" y="38" width="24" height="20" fill="var(--s2)"></rect>
<rect x="220" y="38" width="24" height="20" fill="var(--s2)"></rect>
<text x="250" y="52" fill="var(--s2)" font-size="9">signal in the dropped tail</text>
<text x="20" y="102" fill="var(--muted)" font-size="10">matryoshka</text>
<rect x="100" y="88" width="24" height="20" fill="var(--s1)"></rect>
<rect x="124" y="88" width="24" height="20" fill="var(--s1)"></rect>
<rect x="148" y="88" width="24" height="20" fill="var(--s1)"></rect>
<rect x="172" y="88" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<rect x="196" y="88" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<rect x="220" y="88" width="24" height="20" fill="var(--panel)" stroke="var(--line)"></rect>
<text x="250" y="102" fill="var(--s1)" font-size="9">signal in the kept prefix</text>
<line x1="172" y1="30" x2="172" y2="120" stroke="var(--ink)" stroke-dasharray="4 3"></line>
<text x="150" y="138" fill="var(--ink)" font-size="9">cut here (keep 3)</text>
</svg>
^ Both are valid full embeddings; the difference is only which side of the cut holds the signal, and that decides whether truncation keeps the answer or throws it away.

## Build

Truncate both to the first 3 dimensions and they part ways.

```python filename=modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.py:39-41 COMPLETE
def truncate(v, k):
    """Keep only the first k dimensions of the vector."""
    return v[:k]
```

```text filename=dimtrunc.py --trunc
TRUNC — both models truncated to the first 3 of 6 dimensions
----------------------------------------------------------------
  ordinary    relevant=0.000  distractor=1.000  -> ranks distractor first   <- FLIPPED to the wrong doc
  matryoshka  relevant=1.000  distractor=0.577  -> ranks relevant first
----------------------------------------------------------------
  the ordinary embedding's signal was in the dropped dimensions; the Matryoshka's was not
```

The ordinary model now ranks the distractor first — relevant 0.000, distractor 1.000, a complete flip — because the dimensions that separated relevant from distractor were the ones it dropped. The Matryoshka model still ranks the relevant document first, 1.000 to 0.577, because its separating signal was in the kept prefix. Same slice, opposite outcome.

<svg role="img" aria-label="Truncated cosines. Ordinary model: relevant bar at 0, distractor bar at 1.0, so the distractor wins. Matryoshka model: relevant bar at 1.0, distractor bar at 0.577, so the relevant wins." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">truncated cosine (taller = ranked first)</text>
<line x1="40" y1="130" x2="440" y2="130" stroke="var(--line)"></line>
<text x="70" y="146" fill="var(--muted)" font-size="9">ordinary</text>
<rect x="60" y="130" width="34" height="0" fill="var(--s2)"></rect>
<text x="60" y="126" fill="var(--s2)" font-size="9">rel 0.00</text>
<rect x="104" y="40" width="34" height="90" fill="var(--s1)"></rect>
<text x="104" y="36" fill="var(--s1)" font-size="9">dist 1.00</text>
<text x="290" y="146" fill="var(--muted)" font-size="9">matryoshka</text>
<rect x="270" y="40" width="34" height="90" fill="var(--s2)"></rect>
<text x="270" y="36" fill="var(--s2)" font-size="9">rel 1.00</text>
<rect x="314" y="78" width="34" height="52" fill="var(--s1)"></rect>
<text x="314" y="74" fill="var(--s1)" font-size="9">dist 0.58</text>
</svg>
^ Truncated, the ordinary model's distractor towers over its (zeroed) relevant document, while the Matryoshka model keeps the relevant document on top — the flip is the ordinary model's, not the operation's.

The self-test pins both halves: the flip on the ordinary model, the survival on the Matryoshka, and the norm change that a dot-product index would have to handle.

```python filename=modules/context-and-retrieval/code/dimtrunc-inter-01/dimtrunc.py:92-98 COMPLETE
    ocr, ocd, ord_trunc = rank(ordn, data["k"])
    trunc_breaks_ordinary = ord_trunc == "distractor"
    print("  truncated, the ordinary model ranks the DISTRACTOR first = %s (relevant=%.3f, distractor=%.3f)" % (trunc_breaks_ordinary, ocr, ocd))

    mcr, mcd, mat_trunc = rank(mat, data["k"])
    trunc_keeps_matryoshka = mat_trunc == "relevant"
    print("  truncated, the Matryoshka model still ranks the relevant doc first = %s (relevant=%.3f, distractor=%.3f)" % (trunc_keeps_matryoshka, mcr, mcd))
```

```text filename=dimtrunc.py --check
SELF-TEST — at full dim both rank the relevant doc first; truncated, the ordinary model ranks the distractor first while the Matryoshka model still ranks the relevant doc first, and truncation changes a unit vector's norm
----------------------------------------------------------------------------------------------------------------
  at full dimension both models rank the relevant doc first = True (ordinary=relevant, matryoshka=relevant)
  truncated, the ordinary model ranks the DISTRACTOR first = True (relevant=0.000, distractor=1.000)
  truncated, the Matryoshka model still ranks the relevant doc first = True (relevant=1.000, distractor=0.577)
  truncating changes the vector's norm (dot-product indexes must renormalize) = True (3.606 -> 1.000)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  full_both_correct=True  trunc_breaks_ordinary=True  trunc_keeps_matryoshka=True  norm_changes=True
```

**norm_changes is the second, quieter trap: cosine renormalizes for you, but a raw dot-product index does not, so truncating a normalized vector silently rescales every score by the shortened norm.**

## Definition of done

You can say why dimension truncation is a property of the embedding model rather than the operation, and name what a Matryoshka model does differently (front-loads the separating signal into the leading dimensions).

You can explain why full-dimension retrieval passing is not evidence that truncation is safe — the two kinds of model are identical at full width and diverge only on documents whose signal lived in the tail.

You can describe both failure modes: a truncated ordinary embedding flipping the ranking, and a truncated normalized vector needing renormalization before a dot-product index.

You can state how to validate a truncation before shipping it: re-run retrieval quality at the target dimension on real queries, because the drop is model- and data-specific, not a fixed fraction.

## Boss fight

To cut vector-store cost you truncate every embedding from 1536 to 768 dimensions. Offline recall on your eval set barely moves, so you ship it — and a week later a specific class of queries (comparisons between two similar products) has quietly gotten worse, while everything else is fine.

First: explain how offline recall could look fine while one query class regressed. What has to be true about where the "similar products" signal lived in the embedding, and why did the eval set miss it?

Then: you check and your embedding model is not Matryoshka-trained. Given that, is there any prefix length that is safe, or is the whole approach wrong for this model? Contrast what you would do with a Matryoshka model (and what its docs would let you promise) versus this one.

Finally: a teammate says "we normalize all vectors to unit length at index time, and we rank by dot product for speed." After truncating, what is now silently wrong with every score, and what one step restores correctness? Explain why cosine-based retrieval would have hidden this bug and dot-product retrieval exposed it.

## External resources

The Matryoshka Representation Learning paper introduces the training objective that makes prefixes usable, and its evaluation is exactly this module's experiment at scale: accuracy as a function of how many leading dimensions you keep.

OpenAI's text-embedding-3 models expose a "dimensions" parameter that returns a shortened, still-usable embedding — a production API built on this property — and their documentation's warning to renormalize a shortened vector is the norm-change point here.
