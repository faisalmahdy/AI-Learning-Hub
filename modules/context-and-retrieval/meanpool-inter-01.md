---
id: meanpool-inter-01
title: Mask the padding out of a mean-pooled embedding — averaging pad tokens in drags the vector off direction and misranks retrieval
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A standard way to turn a document into one vector for dense retrieval is to embed each token and average the token embeddings — mean pooling. It is simple and works, with one condition easy to drop: the average must be taken over the real tokens only. Documents in a batch are padded to a common length so they fit in a rectangular tensor, and those padding positions carry embeddings like any other token id — the pad id maps to some vector. Mean-pool over the whole padded tensor and you average those padding vectors into the sentence embedding, pulling it toward the padding direction and away from what the document says. The distortion is not uniform: a padded batch gives short documents more padding and long documents less, so the padding pulls a short document's embedding harder — exactly the wrong bias, because a short, highly relevant document is diluted more than a long, mediocre one, and the mediocre document's similarity to the query can end up higher and the ranking flips. Nothing looks broken — the embeddings have the right shape, the cosine is a real number, the pipeline runs — the bug lives entirely in whether the mean skipped the padding. The fix is masked mean pooling: use the attention mask to sum only the real-token embeddings and divide by the real-token count, so padding never enters the average and the embedding depends only on content. On a fixture where the query aligns perfectly with a short padded document A and less well with a longer unpadded document B, masked pooling ranks A first (cosine 1.00 vs 0.80) while naive pooling dilutes A to 0.71 and wrongly ranks B first.
eli5: To describe a whole sentence with one "average meaning," you take all the word-meanings and average them. But when sentences are lined up in a batch, the short ones get blank filler added to the end so every row is the same length — and that filler has a meaning-vector too. If you include the filler in your average, a short sentence gets watered down by all its blanks, so it drifts away from what it actually meant. A short sentence that perfectly answers your question can end up looking like a worse match than a longer, so-so one, just because it had more filler dragging its average around. The fix is to only average the real words and ignore the filler — then the length of a sentence, and how much blank padding it happened to get, stops messing up the match.
---

## Why this module

Dense retrieval needs one vector per document, and mean pooling is the workhorse that produces it: embed each token, average the vectors, normalize, done. The averaging step hides a dependency on something that has nothing to do with the document's meaning — the padding added to make a batch rectangular. Every document in a batch is padded up to the longest one's length, and the pad token, like any token, has an embedding. Whether that embedding leaks into the average depends on a single detail: does the mean divide by the real token count and skip the pad positions, or does it blindly average the whole padded row?

If it blindly averages, the sentence embedding is a blend of the document and the padding, tilted toward the padding by however much padding the document received. And padding is not distributed evenly — it is a function of length. A short document in a batch with a long document gets padded a lot; a long document gets padded little. So the tilt is strongest for short documents, which means the pooling systematically distorts short documents more than long ones, purely because of batch composition.

That length-dependent distortion is what makes it a retrieval bug and not just a small numerical error: it can reorder results, favoring a longer, less relevant document over a shorter, more relevant one. This module pools two documents both ways and watches the ranking flip.

**Padding tokens carry embeddings, so a mean pooled over the whole padded tensor tilts the sentence vector toward the padding — diluting short documents most and flipping the ranking; masked pooling averages only the real tokens so the embedding depends on content alone.**

## Concepts

The fixture is a query and two documents. Document A is short (2 real tokens) and gets 2 padding tokens; it is the truly relevant one, its real tokens pointing exactly along the query. Document B is unpadded and only partially aligned.

```json filename=modules/context-and-retrieval/code/meanpool-inter-01/meanpool.json:3-9 COMPLETE
  "query": [1, 0],
  "documents": [
    {
      "id": "A",
      "relevant": true,
      "real_tokens": [[1, 0], [1, 0]],
      "pad_tokens": [[0, 1], [0, 1]]
```

Two poolings differ only in what they average. Masked pooling averages the real tokens alone; naive pooling averages the real tokens plus the padding tokens. The pad token here embeds to [0, 1] — orthogonal to the query — so averaging it in rotates the embedding away from the query direction.

```python filename=modules/context-and-retrieval/code/meanpool-inter-01/meanpool.py:33-45 COMPLETE
def mean(vectors):
    n = len(vectors)
    return [sum(comp) / n for comp in zip(*vectors)]


def masked_pool(doc):
    """Mean over the real tokens only -- padding is masked out."""
    return mean(doc["real_tokens"])


def naive_pool(doc):
    """Mean over real AND padding tokens -- the padding leaks in."""
    return mean(doc["real_tokens"] + doc["pad_tokens"])
```

Retrieval ranks documents by cosine similarity between the query and each pooled embedding, highest first.

```python filename=modules/context-and-retrieval/code/meanpool-inter-01/meanpool.py:48-57 COMPLETE
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def rank(query, docs, pool):
    scored = [(d["id"], cosine(query, pool(d))) for d in docs]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)
```

The only difference between a correct and a broken retriever here is which pooling `rank` is handed — and that difference is enough to reorder the results.

<svg role="img" aria-label="Document A's real tokens point along the query at direction [1,0], but averaging in the padding at [0,1] rotates the pooled vector to [0.5,0.5], off the query direction" viewBox="0 0 320 130">
  <line x1="30" y1="110" x2="30" y2="20" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="110" x2="300" y2="110" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="110" x2="250" y2="110" stroke="var(--s2)" stroke-width="2"/>
  <text x="250" y="122" font-size="7.5" fill="var(--s2)">query / real tokens [1,0]</text>
  <line x1="30" y1="110" x2="30" y2="30" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="3 3"/>
  <text x="34" y="34" font-size="7.5" fill="var(--muted)">pad token [0,1]</text>
  <line x1="30" y1="110" x2="170" y2="40" stroke="var(--s1)" stroke-width="2"/>
  <text x="150" y="36" font-size="7.5" fill="var(--s1)">naive pool [0.5,0.5]</text>
  <text x="60" y="80" font-size="7" fill="var(--ink)">padding rotates the embedding off the query direction</text>
</svg>
^ Document A's real tokens lie exactly along the query, so masked pooling gives a vector on the query axis. Averaging in the two padding tokens at [0,1] rotates the pooled vector up to [0.5,0.5], 45 degrees off the query — a large drop in cosine for a document that is a perfect content match.

**Masked and naive pooling differ only in whether the padding tokens enter the average — and because padding points away from the query, that inclusion rotates the embedding and lowers the similarity.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the document-embedding step of a dense retriever, reduced to 2-D vectors so every cosine is checkable by hand.

Run `--pool` to see each document's two pooled embeddings.

```text filename=meanpool.py --pool
  doc A (2 real, 2 pad)  masked=[1.0, 0.0]  naive=[0.5, 0.5]
  doc B (2 real, 0 pad)  masked=[0.8, 0.6]  naive=[0.8, 0.6]
```

Document A's masked embedding is [1.0, 0.0] — exactly along the query. Its naive embedding is [0.5, 0.5], because the two padding tokens at [0, 1] are averaged in with the two real tokens at [1, 0], pulling half the weight up the second axis. Document B has no padding, so its two poolings are identical — the bug only touches padded documents, and B is unpadded, so it is unaffected. The asymmetry is the whole point: naive pooling changed A and left B alone.

Now `--rank` scores both and orders them.

```text filename=meanpool.py --rank
  doc  relevant  masked cos   naive cos
  A    True      1.00         0.71
  B    False     0.80         0.80
```

Under masked pooling, A scores 1.00 (perfect alignment) and B scores 0.80, so A ranks first — correct, A is the relevant document. Under naive pooling, A is diluted to 0.71 by its padding while B stays at 0.80, so B ranks first — wrong. The retriever returns the less relevant document, and the only cause is that the padding was averaged into A's embedding. B did not get better; A got dragged below it by tokens that carry no information about the document at all.

<svg role="img" aria-label="Cosine bars: masked pooling gives A 1.00 above B 0.80, naive pooling gives A 0.71 below B 0.80, flipping which ranks first" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">cosine to query (A is the relevant document)</text>
  <text x="10" y="36" font-size="8" fill="var(--s1)">masked</text>
  <rect x="60" y="26" width="120" height="13" fill="var(--s1)"/><text x="184" y="36" font-size="7.5" fill="var(--ink)">A 1.00 ✓ first</text>
  <rect x="60" y="42" width="96" height="13" fill="none" stroke="var(--s2)"/><text x="160" y="52" font-size="7.5" fill="var(--muted)">B 0.80</text>
  <text x="10" y="80" font-size="8" fill="var(--s2)">naive</text>
  <rect x="60" y="70" width="85" height="13" fill="none" stroke="var(--s1)"/><text x="150" y="80" font-size="7.5" fill="var(--muted)">A 0.71</text>
  <rect x="60" y="86" width="96" height="13" fill="var(--s2)"/><text x="160" y="96" font-size="7.5" fill="var(--ink)">B 0.80 ✗ first</text>
  <text x="10" y="120" font-size="7.5" fill="var(--muted)">padding drops A below B — the relevant document loses to a padding artifact</text>
</svg>
^ Masked pooling puts A (1.00) above B (0.80); naive pooling drops A to 0.71, below B's unchanged 0.80, flipping the top result. The relevant document loses first place to a longer document purely because of padding it happened to receive in its batch.

**Masked pooling ranks the relevant A first (1.00 > 0.80); naive pooling dilutes A to 0.71 and ranks the irrelevant B first — the flip is caused entirely by padding averaged into A's embedding.**

## Build

The self-test asserts the setup and the distortion: the relevant document is padded, the padding changes its pooled embedding, and that lowers its cosine to the query.

```python filename=modules/context-and-retrieval/code/meanpool-inter-01/meanpool.py:96-105 COMPLETE
    doc_has_padding = len(relevant["pad_tokens"]) > 0
    print("  the relevant document is padded = %s (%d pad tokens)" % (doc_has_padding, len(relevant["pad_tokens"])))

    padding_pulls_embedding = masked_pool(relevant) != naive_pool(relevant)
    print("  padding changes the relevant doc's pooled embedding = %s (%s -> %s)"
          % (padding_pulls_embedding, [round(x, 2) for x in masked_pool(relevant)], [round(x, 2) for x in naive_pool(relevant)]))

    naive_dilutes = cosine(q, naive_pool(relevant)) < cosine(q, masked_pool(relevant))
    print("  naive pooling lowers the relevant doc's cosine = %s (%.2f < %.2f)"
          % (naive_dilutes, cosine(q, naive_pool(relevant)), cosine(q, masked_pool(relevant))))
```

Then the consequence and the fix: masked pooling ranks the relevant document first, naive pooling ranks the wrong one first.

```python filename=modules/context-and-retrieval/code/meanpool-inter-01/meanpool.py:107-110 COMPLETE
    masked_ranks_relevant_first = masked_order[0] == relevant["id"]
    print("  masked pooling ranks the relevant document first = %s (%s)" % (masked_ranks_relevant_first, masked_order))

    naive_ranks_wrong_first = naive_order[0] != relevant["id"]
    print("  naive pooling ranks the WRONG document first = %s (%s)" % (naive_ranks_wrong_first, naive_order))
```

Running the check confirms every clause.

```text filename=meanpool.py --check
  the relevant document is padded = True (2 pad tokens)
  padding changes the relevant doc's pooled embedding = True ([1.0, 0.0] -> [0.5, 0.5])
  naive pooling lowers the relevant doc's cosine = True (0.71 < 1.00)
  masked pooling ranks the relevant document first = True (['A', 'B'])
  naive pooling ranks the WRONG document first = True (['B', 'A'])
```

**The check traces the misranking from padded document to distorted embedding to lowered cosine to flipped order — and shows masked pooling ranking the relevant document first once the padding is excluded.**

## Definition of done

Done means naive pooling is shown to distort the padded document's embedding and flip the ranking, while masked pooling ranks the relevant document first. The clause that document B is unaffected is quietly important: it proves the bug is padding-specific and length-dependent, not a general shift that would cancel out — only the padded document moves, so the distortion actively reorders documents rather than rescaling them all together.

Two clarifications place this in real systems. First, the standard implementation is a masked mean: multiply the token embeddings by the attention mask, sum along the sequence, and divide by the mask's sum (the real-token count), which is exactly what libraries like Sentence-Transformers do in their pooling layer. The bug appears when someone hand-rolls pooling with a plain `.mean(dim=1)` over the padded tensor, or feeds an unmasked mean into a custom retriever; it is a classic "the framework was doing something for you that you didn't replicate" error. Second, the effect depends on what the pad token embeds to and on normalization. If padding embedded to an exact zero vector, an unmasked sum would be unchanged but an unmasked mean would still divide by the wrong count — shrinking magnitude, which matters whenever scores are not cosine-normalized (dot-product retrieval, or pooling feeding a later layer). In practice pad embeddings are rarely a clean zero, so the direction shifts too, as here. The safe rule is unconditional: always pool with the mask, so neither the pad embedding's value nor the document's length can touch the result.

<svg role="img" aria-label="Masked mean pooling: multiply token embeddings by the attention mask, sum, and divide by the mask sum, so only real tokens contribute" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">masked mean = (embeddings × mask).sum ÷ mask.sum</text>
  <g font-size="7.5">
  <rect x="16" y="30" width="30" height="14" fill="var(--s1)"/><text x="22" y="40" fill="var(--panel)">tok</text>
  <rect x="48" y="30" width="30" height="14" fill="var(--s1)"/><text x="54" y="40" fill="var(--panel)">tok</text>
  <rect x="80" y="30" width="30" height="14" fill="none" stroke="var(--line)"/><text x="86" y="40" fill="var(--muted)">pad</text>
  <rect x="112" y="30" width="30" height="14" fill="none" stroke="var(--line)"/><text x="118" y="40" fill="var(--muted)">pad</text>
  <text x="150" y="40" fill="var(--ink)">mask = [1,1,0,0]</text>
  </g>
  <text x="16" y="66" font-size="7.5" fill="var(--s1)">sum the two real tokens ÷ 2 → content-only embedding</text>
  <text x="16" y="88" font-size="7.5" fill="var(--muted)">a plain .mean() over the padded row divides by 4 and averages the pads in</text>
</svg>
^ Masked pooling multiplies by the attention mask before summing and divides by the mask's sum, so only real tokens contribute and the count is right. A plain mean over the padded row divides by the padded length and folds the pad vectors in — the bug this module isolates.

**Done means masked pooling ranks the relevant document first and naive pooling flips it, with the unaffected unpadded document proving the distortion is length-dependent — so the rule is to always pool with the attention mask, independent of the pad embedding's value.**

## Boss fight

A team builds a custom dense retriever and finds that short documents almost never surface, even when they are exact answers, while longer documents dominate the top results. Their embedding step runs a transformer over the batch and takes `embeddings.mean(dim=1)` as the document vector. The embedding model itself scores well on benchmarks. What is wrong, and how do you fix it?

They are mean-pooling over the padded sequence without masking, so the padding tokens are averaged into every short document's embedding. `embeddings.mean(dim=1)` divides by the padded sequence length and includes every pad position's vector, and because short documents get the most padding in a batch, their embeddings are pulled hardest toward the pad token's direction and away from their real content. That is exactly the observed symptom: short documents' vectors are distorted the most, so their similarity to relevant queries drops and they lose to longer documents whose embeddings are barely touched by padding. The benchmark score is fine because benchmark harnesses (and the model's own library) do masked pooling; the bug is in the team's hand-rolled pooling, not the model. The fix is masked mean pooling: take the attention mask, multiply the token embeddings by it (zeroing the pad positions), sum along the sequence dimension, and divide by the mask's sum — the real-token count — rather than the padded length. Concretely, replace `embeddings.mean(dim=1)` with `(embeddings * mask.unsqueeze(-1)).sum(1) / mask.sum(1).clamp(min=1)`. After that, a document's embedding depends only on its real tokens, its length no longer biases its vector, and short exact-answer documents rank on their merits. It is also worth normalizing the pooled vectors if the retriever uses dot product rather than cosine, so residual magnitude differences from length do not creep back in.

## External resources

The Sentence-Transformers pooling implementation and documentation (its masked mean-pooling layer, and the community threads on "why are my short documents ranked poorly") — the reference masked mean and the exact `sum(embeddings*mask)/sum(mask)` formulation this module reduces to.

Guidance on sentence-embedding pooling strategies (mean vs CLS vs max pooling, and the necessity of the attention mask in each) from embedding-model papers and library docs — why unmasked pooling silently corrupts the representation and how masked pooling keeps the embedding a function of content alone.
