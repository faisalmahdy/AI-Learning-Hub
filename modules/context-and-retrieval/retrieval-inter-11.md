---
id: retrieval-inter-11
title: Put a relevance floor under retrieval — always returning the top hit injects noise on an out-of-scope query
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: A vector retriever always has a top result, so it hands back a document even for a question it has nothing for — and the model treats that irrelevant passage as relevant. A similarity threshold lets retrieval abstain. Two in-scope queries match at cosine 0.99, two out-of-scope match at 0.1–0.2; the floor injects for the first two and returns nothing for the rest.
eli5: If you ask a librarian for a book they don't have, a bad librarian still hands you the closest thing on the shelf — and you might think it's the answer. A good librarian says "we don't have anything on that." Retrieval needs that "we don't have it" option, or it forces a wrong book on every question.
---

## Why this module

A vector retriever cannot say "I have nothing for this" unless you build it the ability, and without that ability it lies by always answering.

The mechanics guarantee it. Retrieval ranks every document by similarity to the query and returns the top one — or top k. That is a sort, and a sort always has a winner, no matter how bad the field. Ask a customer-support index a question about the weather and it will still rank its billing, shipping, and returns documents and hand you whichever is least unrelated. The "best" match might be at cosine 0.1 — essentially orthogonal, essentially noise — but the retriever returns it with the same interface it uses for a perfect match, and nothing downstream knows the difference.

The harm is that the model trusts retrieved context. Injected passages arrive with an implicit label of "this is relevant, use it," and the model will dutifully try to answer the weather question from a billing document, producing a confident, grounded-sounding, wrong answer. Retrieval that always injects something turns every out-of-scope query into a hallucination with a citation. The failure is worst exactly where you most want the system to decline: questions outside its knowledge.

The fix is a relevance floor. Keep the top hit only if its similarity clears a threshold; below the threshold, return nothing and let the model answer from its own knowledge or say it does not know. This converts retrieval from "always inject something" to "inject only on a real match," and it costs one comparison.

We will run four queries — two in-scope, two out-of-scope — through both policies. Always-top-1 injects a document for all four, feeding the weather and stock-tip queries irrelevant billing context. The 0.5 threshold injects for the two real matches and abstains on the two out-of-scope queries, with zero loss of coverage on the ones that mattered.

**A retriever's sort always produces a winner, so without a similarity floor it injects its least-bad document into every out-of-scope query — and the model answers from that noise as if it were relevant.**

## Concepts

The core confusion is between rank and relevance. A retriever gives you rank: which document is most similar to the query, relative to the others. It does not, by itself, give you relevance: whether that document is actually about the query at all. Rank is always defined — there is always a most-similar document — but relevance is a property of the absolute similarity, not the ordering. A top hit at cosine 0.99 is relevant; a top hit at cosine 0.1 is the top of a pile of noise. Same rank, opposite relevance.

The threshold is how you recover relevance from rank. You pick a floor — a minimum similarity below which even the best match is considered "no real match" — and you abstain when the top hit falls below it. Choosing that floor is a calibration problem: set it too high and you reject weak-but-useful matches, hurting recall on genuine but hard queries; set it too low and out-of-scope queries slip through and inject noise. The right floor lives in the gap between the similarity of real matches and the similarity of non-matches, and the wider that gap, the easier the choice. On a well-separated index — real matches near 1, non-matches near 0 — almost any middling threshold works; on a poorly separated one, no threshold cleanly separates and the threshold's failures tell you your embeddings need work.

Abstention is a feature, not a failure. A retriever that returns nothing on an out-of-scope query has done its job correctly: it has reported that it has no relevant knowledge, which is exactly the signal the downstream system needs to fall back to the model's own knowledge, to say "I don't know," or to route the query elsewhere. The alternative — silently injecting noise — removes that signal and forces a grounded answer where none is warranted. The whole value of retrieval-augmented generation rests on the retrieved context being relevant; a retriever with no floor breaks that premise on every query it has no answer for.

This is why production retrieval almost always has a score cutoff, and why "top-k with no threshold" is a demo pattern that leaks noise in the field. The threshold is what lets the system distinguish "here is the answer" from "I have nothing," which is a distinction users and models both depend on.

**Rank is always defined; relevance is not — the threshold reads relevance off the absolute similarity, and abstaining below it is the retriever correctly reporting it has nothing.**

## Worked example

The fixture is a tiny index over three support topics and four queries, two of which are deliberately out of scope.

```json filename=modules/context-and-retrieval/code/retrieval-inter-11/queries.json:28-37 COMPLETE
  "queries": {
    "q_refund": {
      "vec": [
        0.1,
        0.1,
        0.95,
        0
      ],
      "in_scope": true
    },
```

The documents are orthogonal topic vectors (billing, shipping, returns); each query is a vector with an in-scope flag. The refund query points almost entirely along the returns axis. The similarity is plain cosine.

```python filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py:40-44 COMPLETE
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)
```

Look at each query's best match and how strong it is.

```text filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py --queries
QUERIES — each query's best-matching document and its cosine
----------------------------------------------------------
  q_refund    in-scope     best=d_returns   cos 0.989
  q_invoice   in-scope     best=d_billing   cos 0.989
  q_weather   OUT-of-scope best=d_billing   cos 0.100
  q_stocktip  OUT-of-scope best=d_billing   cos 0.201
----------------------------------------------------------
  in-scope queries match ~0.99; out-of-scope match ~0.1-0.2 -- a 0.5 floor splits them.
```

The two in-scope queries match their document at 0.989 — strong, unambiguous. The two out-of-scope queries match their best document at 0.100 and 0.201 — noise. Note that the weather and stock-tip queries both "best-match" the billing document; that is meaningless, an artifact of the sort picking a winner from near-orthogonal options. The always-top-1 policy returns that meaningless winner.

```python filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py:61-66 COMPLETE
def with_threshold(qvec, docs, threshold):
    """Inject the top hit only if its similarity clears the floor; otherwise abstain (return None)."""
    doc, sim = best_match(qvec, docs)
    if sim < threshold:
        return None, sim
    return doc, sim
```

Predict: with a 0.5 floor, the two 0.989 matches clear it and the two ~0.15 matches do not. Run both policies side by side.

```text filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py --retrieve
RETRIEVE — what each policy injects (threshold 0.5)
------------------------------------------------------------
  query        always-top-1        with-threshold
  q_refund    d_returns          d_returns
  q_invoice   d_billing          d_billing
  q_weather   d_billing          (abstain)
  q_stocktip  d_billing          (abstain)
------------------------------------------------------------
  always-top-1 injects a doc for the weather and stock-tip queries; the threshold abstains.
```

On the two in-scope queries the policies are identical — both inject the right document, so the threshold costs nothing on real matches. On the two out-of-scope queries they diverge completely: always-top-1 injects the billing document into a weather question and a stock tip, while the threshold abstains. That billing document, fed to the model alongside "what's the weather," is precisely the noise that produces a confident wrong answer grounded in an irrelevant passage.

<svg role="img" aria-label="A grid of four queries by two policies: always-top-1 injects a document on all four, the threshold injects on the two in-scope and abstains on the two out-of-scope" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="180" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">always-top-1</text>
  <text x="330" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">with threshold</text>
  <g font-family="var(--mono)" font-size="9">
    <text x="16" y="52" fill="var(--acc-ink)">q_refund (in)</text>
    <rect x="180" y="40" width="110" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="192" y="53" fill="var(--acc-ink)">inject d_returns</text>
    <rect x="330" y="40" width="110" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="342" y="53" fill="var(--acc-ink)">inject d_returns</text>
    <text x="16" y="82" fill="var(--acc-ink)">q_invoice (in)</text>
    <rect x="180" y="70" width="110" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="192" y="83" fill="var(--acc-ink)">inject d_billing</text>
    <rect x="330" y="70" width="110" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="342" y="83" fill="var(--acc-ink)">inject d_billing</text>
    <text x="16" y="112" fill="var(--s2)">q_weather (out)</text>
    <rect x="180" y="100" width="110" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="192" y="113" fill="var(--ink)">inject d_billing ✗</text>
    <rect x="330" y="100" width="110" height="18" fill="var(--panel)" stroke="var(--acc-ink)"/><text x="342" y="113" fill="var(--acc-ink)">abstain ✓</text>
    <text x="16" y="142" fill="var(--s2)">q_stocktip (out)</text>
    <rect x="180" y="130" width="110" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="192" y="143" fill="var(--ink)">inject d_billing ✗</text>
    <rect x="330" y="130" width="110" height="18" fill="var(--panel)" stroke="var(--acc-ink)"/><text x="342" y="143" fill="var(--acc-ink)">abstain ✓</text>
  </g>
  <text x="16" y="172" font-family="var(--mono)" font-size="9" fill="var(--muted)">identical on the two real matches; they differ only where a real match was absent</text>
</svg>
^ The two policies agree on the in-scope rows and split on the out-of-scope rows, where always-top-1 injects the same irrelevant billing doc that the threshold refuses.

<svg role="img" aria-label="Query space: three document points, two in-scope queries sitting close to a document inside the relevance radius, two out-of-scope queries far outside it" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">similarity to nearest document (schematic)</text>
  <circle cx="120" cy="110" r="60" fill="none" stroke="var(--acc-line)" stroke-dasharray="4 3"/>
  <text x="88" y="180" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">relevance floor (0.5)</text>
  <rect x="112" y="70" width="10" height="10" fill="var(--acc-ink)"/><text x="126" y="79" font-family="var(--mono)" font-size="9" fill="var(--ink)">d_returns</text>
  <rect x="150" y="130" width="10" height="10" fill="var(--acc-ink)"/><text x="164" y="139" font-family="var(--mono)" font-size="9" fill="var(--ink)">d_billing</text>
  <circle cx="118" cy="88" r="4" fill="var(--acc-line)"/><text x="60" y="92" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">q_refund</text>
  <circle cx="140" cy="120" r="4" fill="var(--acc-line)"/><text x="150" y="112" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">q_invoice</text>
  <circle cx="360" cy="60" r="4" fill="var(--s2)"/><text x="330" y="52" font-family="var(--mono)" font-size="8" fill="var(--s2)">q_weather</text>
  <circle cx="400" cy="150" r="4" fill="var(--s2)"/><text x="356" y="168" font-family="var(--mono)" font-size="8" fill="var(--s2)">q_stocktip</text>
  <text x="300" y="110" font-family="var(--mono)" font-size="9" fill="var(--muted)">out-of-scope: far from every doc</text>
</svg>
^ The in-scope queries fall inside the relevance floor around a document; the out-of-scope queries sit far outside it — always-top-1 still snaps them to the nearest doc, the threshold leaves them out.

## Build

Reproduce the two policies. Pure standard library, deterministic vectors, so the cosines 0.989, 0.100, 0.201 and the inject/abstain decisions come out exactly.

Run `--queries` for the matches, `--retrieve` for the two policies, `--check` for the gate. The self-test counts junk injected on out-of-scope queries and coverage on in-scope ones, for both policies.

```python filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py:97-100 COMPLETE
def junk_injected(data, policy):
    """How many OUT-of-scope queries got a document injected (irrelevant context)."""
    docs, thr = data["docs"], data["threshold"]
    return sum(1 for qd in data["queries"].values()
               if not qd["in_scope"] and policy(qd["vec"], docs, thr)[0] is not None)
```

The self-test's decisive pairing is `threshold_no_junk` together with `threshold_keeps_coverage`. Either alone is trivial to satisfy — a retriever that abstains on everything injects no junk, and a retriever that injects everything has full coverage. The point is to have both at once: zero junk on out-of-scope queries *and* full coverage on in-scope ones. That conjunction is what proves the threshold discriminates rather than just being cautious or reckless.

```text filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py:116-123 COMPLETE
    always_junk = junk_injected(data, always_top1)
    always_injects_junk = always_junk == n_out
    print("  always-top-1 injects junk on every out-of-scope query = %s (%d of %d)"
          % (always_injects_junk, always_junk, n_out))

    thr_junk = junk_injected(data, with_threshold)
    threshold_no_junk = thr_junk == 0
    print("  the threshold injects junk on none of them = %s (%d of %d)" % (threshold_no_junk, thr_junk, n_out))
```

```text filename=modules/context-and-retrieval/code/retrieval-inter-11/threshold.py --check
SELF-TEST — the threshold abstains on out-of-scope queries while still covering every in-scope one
--------------------------------------------------------------------------------------------
  always-top-1 injects junk on every out-of-scope query = True (2 of 2)
  the threshold injects junk on none of them = True (0 of 2)
  the threshold still covers every in-scope query = True (2 of 2)
  the two policies agree on the in-scope queries = True (both 2)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  always_injects_junk=True  threshold_no_junk=True  threshold_keeps_coverage=True  same_in_scope=True
```

Four True flags. Always_injects_junk: the no-floor policy feeds noise into every out-of-scope query. Threshold_no_junk: the floor injects noise into none. Threshold_keeps_coverage: the floor still serves every in-scope query. Same_in_scope: the two policies are identical on the queries that had real answers. The last two together are the proof that the threshold is free on real matches — it only changes behavior where behavior needed changing.

<svg role="img" aria-label="Two metrics for the two policies: junk injected on out-of-scope queries is 2 for always-top-1 and 0 for the threshold, while in-scope coverage is 2 for both" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">junk injected (of 2) and in-scope coverage (of 2)</text>
  <text x="16" y="52" font-family="var(--mono)" font-size="10" fill="var(--ink)">junk</text>
  <rect x="130" y="42" width="120" height="16" fill="var(--s2)" stroke="var(--line)"/><text x="256" y="54" font-family="var(--mono)" font-size="9" fill="var(--s2)">always 2 (bad)</text>
  <rect x="130" y="62" width="2" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="140" y="74" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">threshold 0 (good)</text>
  <text x="16" y="112" font-family="var(--mono)" font-size="10" fill="var(--ink)">coverage</text>
  <rect x="130" y="102" width="120" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="256" y="114" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">always 2</text>
  <rect x="130" y="122" width="120" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="256" y="134" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">threshold 2</text>
</svg>
^ The threshold drops junk from 2 to 0 while holding coverage at 2 — it removed only the noise, keeping every real match.

**Zero junk is trivial if you abstain on everything and full coverage is trivial if you inject everything; the test demands both, which is what separates a discriminating floor from a blunt one.**

## Definition of done

You are done when you reproduce the decisions and can explain why rank is not relevance.

Concretely: `--retrieve` shows the threshold abstaining on the weather and stock-tip queries while matching always-top-1 on the refund and invoice queries; `--check` prints PASS with four True flags. You can explain why a retriever always returns a top hit (a sort always has a winner) and why that top hit can be irrelevant (rank is relative, relevance is absolute). You can describe the threshold as a floor on absolute similarity and the calibration trade in choosing it — too high rejects hard-but-real matches, too low leaks noise. And you can say why abstention is the correct behavior on an out-of-scope query, not a failure.

The habit to carry: never ship top-k retrieval without a relevance floor, and when a RAG system confidently answers questions it should decline, check whether retrieval is injecting its least-bad document instead of returning nothing. Calibrate the floor on the gap between your real matches' scores and your non-matches' scores.

## Boss fight

The instructive failure is a support bot that answers everything, including questions it has no business answering.

A company builds a RAG assistant over its help docs with top-1 retrieval and no threshold. It works well on real support questions. Then users start asking it off-topic things — legal advice, medical questions, competitor comparisons — and it answers all of them, confidently, grounded in whatever help-doc paragraph scored highest. A question about a competitor retrieves the company's own pricing page and the bot generates a false comparison; a health question retrieves a return-policy page and the bot improvises. Every answer has a citation, so it looks authoritative, and every one is fabricated from an irrelevant passage. A relevance floor would have made the bot say "I don't have information about that," which is both correct and safe. The missing threshold turned a scoped support tool into a confident answerer of unscoped questions.

Your turn, two moves. First, find where the floor should sit. The in-scope matches are 0.989 and the out-of-scope are 0.100 and 0.201, so any threshold between 0.201 and 0.989 separates them perfectly — a wide safe gap. Predict what a threshold of 0.05 would do (too low: it lets both out-of-scope queries through, back to always-top-1's behavior) and what 0.99 would do (too high: it rejects even the 0.989 real matches, abstaining on everything). Confirm that the gap between real and noise scores is what makes the floor easy or hard to set. Second, shrink the gap and watch calibration get hard. Add a borderline query whose best match is 0.55 — genuinely ambiguous — and predict: no single threshold cleanly handles it, because it sits between clearly-relevant and clearly-noise. That is the real-world case, and it is why threshold choice is a precision-recall trade, not a solved constant: the borderline queries are exactly the ones a fixed floor gets wrong in one direction or the other.

## External resources

Most vector databases expose a score or distance threshold on their query API precisely for this — Pinecone, Weaviate, Qdrant, and pgvector all document a similarity cutoff; their guides on "filtering by score" cover the calibration trade this module isolates.

For the retrieval-quality framing, the "when not to retrieve" and "adaptive retrieval" literature (for example Self-RAG and FLARE) treats abstention and the decision of whether to retrieve at all as first-class, rather than assuming every query gets context.

For the deeper measurement — separating real matches from noise by their score distribution — any treatment of the precision-recall trade for a similarity threshold applies; the floor is a classification boundary, and choosing it is choosing an operating point on that curve.
