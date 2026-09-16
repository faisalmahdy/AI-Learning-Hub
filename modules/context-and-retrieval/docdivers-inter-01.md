---
id: docdivers-inter-01
title: Cap chunks per document in the top-k — one dominant document fills every slot with distinct chunks and starves a multi-source question
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval scores chunks and the obvious selector takes the top k by score, which works when the answer lives in one place and fails when a question needs evidence spread across several documents. Scores do not distribute themselves fairly across sources: one thorough, on-topic document can produce the several highest-scoring chunks and take every slot, leaving no room for the second and third documents that hold the rest of the answer. The crowding chunks are not duplicates — each is a genuinely different passage covering a different fact, so a novelty or maximal-marginal-relevance filter, which drops near-duplicate content, keeps all of them; they are all novel. That is what makes this a separate problem from de-duplication: the chunks are diverse in content and identical in source, and it is the shared source, not repeated content, that starves the other documents. The fix is to diversify by source — cap how many chunks any one document may contribute to the top-k, keeping the best few from each and letting lower-scoring chunks from other documents into the remaining slots — so a single document can no longer monopolize the results and a multi-document question gets at least one chunk from each relevant source. On a fixture where one document supplies the three top-scoring chunks, pure top-k returns all three and covers one of the three required facts, while a per-document cap spreads the three slots across the three documents and covers all three.
eli5: Imagine you're researching a report and you can only carry three books out of the library. You need one fact from a history book, one from a science book, and one from a geography book. But the library's "most relevant" shelf happens to be stacked with three different history books, all genuinely useful and all about your topic — so if you just grab the top three, you walk out with three history books and none of the science or geography you also needed. Each book is different and worthwhile; the problem is they're all the same subject, crowding out the other subjects. The fix is a simple rule: take at most one book per subject, so your three slots spread across history, science, and geography. Search results work the same way — if one source can fill every slot, cap it, so the other sources you need still get a place.
---

## Why this module

A retrieval system's job is not just to find relevant chunks but to assemble a set of chunks that together answer the question. For a single-fact question, the best set is simply the highest-scoring chunk, and top-by-score is exactly right. But many real questions are multi-aspect or multi-hop — they need a fact from here and a fact from there — and for those the quality of the set is about coverage, not just the score of each member.

Top-by-score optimizes each member and ignores the set. It ranks every chunk and takes the k best, on the implicit assumption that the k best chunks form the k best answer. They do not, when the scores clump by source. A single comprehensive document that is squarely on topic will have many passages that all score highly, and top-by-score will happily take all of them, because each is individually excellent — filling the budget with one document's perspective.

The documents that hold the other pieces of the answer lose, not because their chunks are bad, but because they scored just below the dominant document's surplus. The result reads as thorough — several strong, distinct chunks — while quietly missing the sources a complete answer requires. This module selects from a ranked list two ways, pure top-k and per-document-capped, and measures how many of the question's required facts each covers.

**Top-by-score optimizes each chunk and ignores the set, so one on-topic document's several high-scoring chunks fill the budget and starve the other documents a multi-source answer needs.**

## Concepts

The distinction that matters is content diversity versus source diversity, because they are different axes and need different fixes. Content diversity is about not repeating the same information — the job of maximal-marginal-relevance and de-duplication, which drop chunks that are near-duplicates of ones already chosen. Source diversity is about spreading across documents, which is a different thing entirely: the crowding chunks here are content-distinct, each carrying a new fact, so a content-novelty filter is perfectly happy with them and does nothing to spread the sources.

That is the crux: a set can be maximally diverse in content and still come entirely from one document. Three passages from one report, each about a different sub-topic, are all novel relative to each other — MMR keeps them — yet they represent a single source's framing and evidence. If the question needs corroboration or facts from independent documents, this content-diverse but source-monolithic set fails, and no amount of content-novelty filtering will fix it, because there is nothing redundant to remove.

The per-document cap attacks the source axis directly. It limits how many chunks one document may contribute, so after a document hits its cap, the next slot goes to the best chunk from a document not yet at its cap — even if that chunk scored lower than more chunks from the dominant document. The cost is explicit: you trade some raw score for source spread, which is a loss if the answer really was all in one document and a large win if it was spread out. That trade-off is why the cap is a tunable, matched to how multi-source the workload's questions are.

<svg role="img" aria-label="Two axes of diversity: content diversity removes near-duplicate chunks along one axis, source diversity spreads across documents along the other; a set can be high on one and low on the other" viewBox="0 0 440 150">
<line x1="60" y1="120" x2="400" y2="120" stroke="var(--line)"/>
<line x1="60" y1="20" x2="60" y2="120" stroke="var(--line)"/>
<text x="230" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">content diversity (MMR)</text>
<text x="30" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">source</text>
<circle cx="340" cy="100" r="6" fill="var(--s2)"/>
<text x="340" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">one doc,</text>
<text x="340" y="115" fill="var(--muted)" font-size="8" text-anchor="middle">distinct facts</text>
<circle cx="340" cy="40" r="6" fill="var(--s1)"/>
<text x="340" y="30" fill="var(--s1)" font-size="8" text-anchor="middle">capped: many docs,</text>
<text x="386" y="52" fill="var(--muted)" font-size="8" text-anchor="middle">distinct</text>
</svg>
^ Content and source diversity are independent axes; the crowding set is high on content diversity yet low on source diversity, which only the cap raises.

**Content diversity and source diversity are different axes: a content-novelty filter keeps distinct chunks from one document, so only a per-document cap spreads the results across sources — at the cost of trading some score for that spread.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/docdivers-inter-01. The fixture is a ranked list of chunks; document A supplies the three top scorers, and the required facts are spread across A, B, and C.

```json filename=modules/context-and-retrieval/code/docdivers-inter-01/docdivers.json:3-12 COMPLETE
  "chunks": [
    {"id": "A1", "doc": "A", "score": 0.90, "fact": "f1"},
    {"id": "A2", "doc": "A", "score": 0.88, "fact": "f2"},
    {"id": "A3", "doc": "A", "score": 0.86, "fact": "f3"},
    {"id": "B1", "doc": "B", "score": 0.84, "fact": "f4"},
    {"id": "C1", "doc": "C", "score": 0.82, "fact": "f5"}
  ],
  "required": ["f1", "f4", "f5"],
  "top_k": 3,
  "per_doc_cap": 1
```

Pure top-k takes the k highest-scoring chunks, ignoring their source.

```python filename=modules/context-and-retrieval/code/docdivers-inter-01/docdivers.py:38-40 COMPLETE
def pure_topk(chunks, k):
    """Take the k highest-scoring chunks, ignoring their source."""
    return by_score(chunks)[:k]
```

The capped selector takes chunks by score but allows at most `cap` from any one document.

```python filename=modules/context-and-retrieval/code/docdivers-inter-01/docdivers.py:43-53 COMPLETE
def capped_topk(chunks, k, cap):
    """Take the highest-scoring chunks but at most `cap` from any one document."""
    selected = []
    counts = {}
    for c in by_score(chunks):
        if counts.get(c["doc"], 0) < cap:
            selected.append(c)
            counts[c["doc"]] = counts.get(c["doc"], 0) + 1
        if len(selected) == k:
            break
    return selected
```

Before running it, predict: pure top-3 should be A1, A2, A3 — all from document A; the cap of 1 should force one chunk each from A, B, C. Run `--select`:

```text filename=docdivers.py --select
SELECT — pure top-3 vs per-document cap of 1
------------------------------------------------------------
  pure top-k   : ['A1', 'A2', 'A3']   sources=['A']
  capped top-k : ['A1', 'B1', 'C1']   sources=['A', 'B', 'C']
```

The prediction holds. Pure top-k is three chunks from one document — document A monopolizes the budget with its three strong, distinct passages. The cap of 1 keeps A's best chunk and gives the other two slots to B and C, spreading the selection across all three sources.

<svg role="img" aria-label="Pure top-3 shows three chunks all labeled document A filling the budget; capped top-3 shows one chunk each from documents A, B, and C" viewBox="0 0 440 160">
<text x="110" y="20" fill="var(--ink)" font-size="11" text-anchor="middle">pure top-3</text>
<rect x="55" y="34" width="110" height="22" fill="var(--s2)" stroke="var(--line)"/>
<text x="110" y="49" fill="var(--ink)" font-size="9" text-anchor="middle">A1 (doc A)</text>
<rect x="55" y="60" width="110" height="22" fill="var(--s2)" stroke="var(--line)"/>
<text x="110" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">A2 (doc A)</text>
<rect x="55" y="86" width="110" height="22" fill="var(--s2)" stroke="var(--line)"/>
<text x="110" y="101" fill="var(--ink)" font-size="9" text-anchor="middle">A3 (doc A)</text>
<text x="110" y="126" fill="var(--s2)" font-size="9" text-anchor="middle">1 source</text>
<text x="330" y="20" fill="var(--ink)" font-size="11" text-anchor="middle">capped (1/doc)</text>
<rect x="275" y="34" width="110" height="22" fill="var(--s1)" stroke="var(--line)"/>
<text x="330" y="49" fill="var(--ink)" font-size="9" text-anchor="middle">A1 (doc A)</text>
<rect x="275" y="60" width="110" height="22" fill="var(--s1)" stroke="var(--line)"/>
<text x="330" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">B1 (doc B)</text>
<rect x="275" y="86" width="110" height="22" fill="var(--s1)" stroke="var(--line)"/>
<text x="330" y="101" fill="var(--ink)" font-size="9" text-anchor="middle">C1 (doc C)</text>
<text x="330" y="126" fill="var(--s1)" font-size="9" text-anchor="middle">3 sources</text>
</svg>
^ Pure top-k fills all three slots from document A; the per-document cap spreads them across A, B, and C.

Now the coverage that actually matters — did the selection get the facts the question needs? Run `--coverage`:

```text filename=docdivers.py --coverage
COVERAGE — required facts ['f1', 'f4', 'f5'] covered by each selection
----------------------------------------------------------
  pure top-k   covers ['f1']  (1 of 3)
  capped top-k covers ['f1', 'f4', 'f5']  (3 of 3)
```

The required facts f1, f4, f5 live in documents A, B, and C respectively. Pure top-k, stuck in document A, covers only f1 — it collected A's f1, f2, f3 but the question needed only f1 from A and both other facts from elsewhere. The capped selection covers all three, because it reached B and C. Same budget, same ranking; source spread won two more required facts.

<svg role="img" aria-label="Coverage of three required facts f1 f4 f5: pure top-k covers only f1, one of three; capped covers all three" viewBox="0 0 440 130">
<text x="110" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">pure top-k</text>
<rect x="50" y="30" width="36" height="24" fill="var(--s1)" stroke="var(--line)"/>
<text x="68" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">f1</text>
<rect x="90" y="30" width="36" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="108" y="46" fill="var(--s2)" font-size="9" text-anchor="middle">f4</text>
<rect x="130" y="30" width="36" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="148" y="46" fill="var(--s2)" font-size="9" text-anchor="middle">f5</text>
<text x="108" y="72" fill="var(--s2)" font-size="9" text-anchor="middle">1 of 3</text>
<text x="330" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">capped</text>
<rect x="270" y="30" width="36" height="24" fill="var(--s1)" stroke="var(--line)"/>
<text x="288" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">f1</text>
<rect x="310" y="30" width="36" height="24" fill="var(--s1)" stroke="var(--line)"/>
<text x="328" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">f4</text>
<rect x="350" y="30" width="36" height="24" fill="var(--s1)" stroke="var(--line)"/>
<text x="368" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">f5</text>
<text x="328" y="72" fill="var(--s1)" font-size="9" text-anchor="middle">3 of 3</text>
</svg>
^ The required facts sit in different documents, so the source-spread selection covers all three while the single-source one covers only one.

## Build

The self-test plants the failure and names each claim as a boolean flag. It builds both selections and confirms first that the chunks are content-distinct — so this is not a de-duplication problem.

```python filename=modules/context-and-retrieval/code/docdivers-inter-01/docdivers.py:99-102 COMPLETE
    pure = pure_topk(chunks, k)
    capped = capped_topk(chunks, k, cap)

    chunks_content_distinct = len(set(c["fact"] for c in chunks)) == len(chunks)
```

Then it checks that pure top-k comes from one document, that the cap spreads across more documents, and that the cap covers more of — indeed all of — the required facts.

```python filename=modules/context-and-retrieval/code/docdivers-inter-01/docdivers.py:105-116 COMPLETE
    pure_one_source = len(sources(pure)) == 1
    print("  pure top-k comes from a single document = %s (%s)" % (pure_one_source, sources(pure)))

    capped_multi_source = len(sources(capped)) > len(sources(pure))
    print("  the cap spreads the selection across more documents = %s (%s)" % (capped_multi_source, sources(capped)))

    pure_cov = len(required_covered(pure, req))
    capped_cov = len(required_covered(capped, req))
    capped_covers_more = capped_cov > pure_cov
    print("  the cap covers more of the required facts = %s (%d vs %d)" % (capped_covers_more, capped_cov, pure_cov))

    capped_covers_all = capped_cov == len(req)
    print("  the cap covers every required fact = %s (%d of %d)" % (capped_covers_all, capped_cov, len(req)))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the crowding chunks ever turn out to be duplicates or the cap stops improving coverage:

```text filename=docdivers.py --check
SELF-TEST — one document monopolizes pure top-k; a per-document cap spreads the sources and covers more required facts
----------------------------------------------------------------------------------------------------------------------------
  every chunk covers a distinct fact (not near-duplicates) = True
  pure top-k comes from a single document = True (['A'])
  the cap spreads the selection across more documents = True (['A', 'B', 'C'])
  the cap covers more of the required facts = True (3 vs 1)
  the cap covers every required fact = True (3 of 3)
```

**The self-test asserts the chunks are content-distinct while the fix is source spread — which proves this is a source-diversity problem a content-novelty filter cannot solve, not a hidden de-duplication.**

## Definition of done

You can explain why top-by-score optimizes each chunk but not the set, and when that gap matters (multi-aspect, multi-hop questions).
You can distinguish content diversity from source diversity and say which axis MMR addresses and which the per-document cap addresses.
You can explain why a content-novelty filter keeps a source-monolithic set — the chunks are all novel — so it does not spread sources.
You can state the per-document cap's trade-off: some raw score given up for source spread, a win when the answer is spread out and a loss when it is concentrated.
You can predict, for a given question type, whether a cap helps and roughly how tight it should be.

## Boss fight

Set the cap too tight for a single-source question. Suppose a question's whole answer is in document A across three passages, and you apply a per-document cap of 1. The cap now forces out A's second and third passages in favor of lower-scoring, less relevant chunks from B and C, and coverage drops. The lesson sharpens: the cap is not free, and its correct value depends on the workload. A cap of 1 maximizes source spread but hurts concentrated answers; a loose cap barely constrains monopolization. Systems that face both question types tune the cap, or apply it only when the query looks multi-aspect, rather than hard-coding one value.

Now consider interaction with the reranker. A cross-encoder reranker reorders the retrieved set for precision, but it, too, scores each chunk independently — so it can re-concentrate the top on the dominant document even after retrieval diversified it. The order matters: diversify after the reranker, or the reranker's per-chunk scoring undoes the spread. This mirrors the general rule that set-level objectives like diversity have to be applied at the stage that produces the final set, not before a later stage that re-optimizes each member and flattens the diversity away.

**The cap trades score for spread, so its value is workload-dependent and a too-tight cap hurts concentrated answers; and because a reranker also scores chunks independently, source diversification must be applied after it, or the reranker re-concentrates the top.**

## External resources

Retrieval frameworks such as LlamaIndex and Haystack expose per-document or per-source limits and "diversity" post-processors that implement exactly this cap.
Search-result diversification research (for example, the work on intent-aware and aspect diversity in web search) formalizes optimizing the set rather than each result, of which source spread is one objective.
The topic's own modules on maximal-marginal-relevance and on de-duplicating the injected context cover the content-diversity axis this module is carefully distinguished from.
