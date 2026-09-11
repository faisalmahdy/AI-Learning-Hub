---
id: retrieval-inter-21
title: Retrieve on small chunks but return the parent — or you match precisely and answer incompletely
topic: context-and-retrieval
level: intermediate
status: ready
time: 19 min
summary: Chunk size is a tug of war. Small chunks match a query precisely — a short passage that is almost all query terms scores high, undiluted by surrounding text — but a small chunk is starved of context: the passage matching "refund policy" may not contain the number of days, which sits a sentence away. Big chunks are the reverse: a whole section holds both the query terms and the detail, so it answers completely, but its match is diluted across all its other tokens, so it retrieves worse. Small-to-big (parent-document) retrieval takes both: index and search the small chunks so retrieval is precise, but return their parent section for context. On a section with a query-term chunk (score 0.67, 0% of the needed context) and a detail chunk, the parent has 100% of the context but a diluted score of 0.29 — small-to-big retrieves via the 0.67 chunk and returns the complete parent.
eli5: To find a fact in a book, a single sentence is easy to match to your question, but that sentence alone might not tell the whole story. The whole chapter tells the story but is hard to pinpoint. The trick is to search by sentences to find the exact spot, then hand over the whole chapter around it — you locate with the needle and read with the haystack.
---

## Why this module

Making a chunk small enough to match a query well makes it too small to answer the query, and making it big enough to answer makes it too diffuse to match — one knob cannot do both jobs.

Retrieval scores a chunk by how much of the query it contains relative to its size, so a short passage that is mostly query terms scores high — the match is sharp and undiluted. That precision is exactly why small chunks retrieve well. But the same smallness starves the chunk of context: the passage that matches "refund policy" often does not contain the actual answer, the number of days, which lives in the next sentence. Return that small chunk to the model and it answers with half the story. Go the other way and index whole sections: now a chunk contains both the query terms and the detail, so it answers completely — but its query terms are diluted across all its other tokens, its match score drops, and it can lose the retrieval to a smaller, more focused, less complete chunk.

**A chunk cannot be both maximally matchable and maximally complete, because match precision wants it small and context completeness wants it large.**

Small-to-big retrieval refuses the trade. Search the small chunks, so retrieval lands precisely on the passage that matches; then return not that chunk but its parent — the larger section it belongs to, which carries the surrounding context. You match on the needle and hand the model the haystack. This module scores both granularities and shows small-to-big keep the small chunk's precision and the parent's completeness at once.

## Concepts

The **retrieval score** here is query overlap divided by chunk length — a precision-weighted match, so a short passage full of query terms scores higher than a long one where they are diluted.

**Completeness** is the fraction of the answer's needed context tokens present in the returned text. A chunk can score high on retrieval and low on completeness, or the reverse.

A **small chunk** maximizes retrieval score: focused, mostly query terms, high overlap-per-length. But it often holds only part of the answer, so its completeness is low.

A **parent** (the section a small chunk belongs to) maximizes completeness: it contains the query terms *and* the detail. But its retrieval score is diluted by its length, so it matches worse.

**Small-to-big retrieval** decouples the two: the small chunk is used for the search (its high score finds the right location), and the parent is used for the return (its completeness answers the query). Indexing the parents instead would give completeness but sacrifice retrieval; returning the small chunk gives retrieval but sacrifices completeness; small-to-big is the only option that gets both.

**Retrieval quality is a property of what you search; answer quality is a property of what you return — small-to-big lets those be different granularities.**

<svg role="img" aria-label="A small chunk is used for search and its parent for the returned answer; two granularities feed two different stages" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="14" fill="var(--muted)" font-size="8">one index entry, two granularities</text>
  <rect x="15" y="24" width="70" height="22" fill="var(--s1)"/><text x="24" y="39" fill="var(--panel)" font-size="8">small chunk</text>
  <rect x="15" y="52" width="130" height="34" fill="var(--s2)"/><text x="24" y="66" fill="var(--panel)" font-size="8">parent section</text>
  <text x="24" y="80" fill="var(--panel)" font-size="7">(holds the small chunk)</text>
  <text x="160" y="39" fill="var(--muted)" font-size="8">→ used to SEARCH (precise match)</text>
  <text x="160" y="70" fill="var(--muted)" font-size="8">→ used to RETURN (full context)</text>
</svg>
^ The small chunk drives the search stage and the parent drives the return stage — one entry serves both, at the size each stage wants.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/retrieval-inter-21/parentdoc.py

The fixture is a section P split into a query-term chunk and a detail chunk.

```json filename=modules/context-and-retrieval/code/retrieval-inter-21/docs.json:1-11 COMPLETE
{
  "_meta": "A document section (parent P) split into two small chunks. query is the terms the user searches for; context_needed is the tokens the answer actually requires (the specific detail). Each small chunk lists its tokens and its parent. Retrieval score is keyword-overlap divided by chunk length, so a short precise chunk scores higher than a long diluted one. Completeness is the fraction of context_needed present in the returned text. The question: which chunk matches the query, and which text must be RETURNED to answer it?",
  "query": ["refund", "policy"],
  "context_needed": ["30", "days"],
  "chunks": [
    {"id": "c_match",  "parent": "P", "tokens": ["refund", "policy", "process"]},
    {"id": "c_detail", "parent": "P", "tokens": ["within", "30", "days", "receipt"]}
  ]
}
```

The score divides query overlap by length; completeness counts the context tokens present; the parent is the union of its chunks' tokens.

```python filename=modules/context-and-retrieval/code/retrieval-inter-21/parentdoc.py:45-60 COMPLETE
def score(tokens, query):
    """Precision-weighted retrieval score: query overlap divided by the chunk's length."""
    return overlap(tokens, query) / len(tokens)


def completeness(tokens, context_needed):
    """Fraction of the needed context tokens present in the text."""
    return sum(1 for t in context_needed if t in tokens) / len(context_needed)


def parent_tokens(chunks, parent):
    out = []
    for c in chunks:
        if c["parent"] == parent:
            out += c["tokens"]
    return out
```

Run `--score` for each candidate.

```text filename=--score
SCORE — retrieval score (overlap/length) and context completeness
------------------------------------------------------------------
  candidate   len   overlap   score   completeness
  c_match      3    2         0.67    0%
  c_detail     4    0         0.00    100%
  parent P     7    2         0.29    100%
------------------------------------------------------------------
  the small query-chunk scores best but is 0% complete; the parent is complete but scores low.
```

c_match holds both query terms in just three tokens, so it scores 0.67 — the best retrieval — but it contains none of the needed context (0%). c_detail has all the context but zero query overlap, so it never gets retrieved. The parent P has the context (100%) but its two query terms are spread over seven tokens, so its score falls to 0.29. No single candidate is both the top retriever and complete.

<svg role="img" aria-label="c_match scores 0.67 but 0% complete; parent P scores 0.29 but 100% complete; the two goals point at different candidates" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="14" fill="var(--muted)" font-size="8">retrieval score (bar) · completeness (label)</text>
  <line x1="70" y1="20" x2="70" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="26" width="140" height="16" fill="var(--s1)"/><text x="214" y="38" fill="var(--muted)" font-size="8">c_match 0.67 · 0% complete</text>
  <rect x="70" y="48" width="0" height="16" fill="var(--s2)"/><text x="74" y="60" fill="var(--muted)" font-size="8">c_detail 0.00 · 100%</text>
  <rect x="70" y="70" width="61" height="16" fill="var(--s2)"/><text x="135" y="82" fill="var(--muted)" font-size="8">parent P 0.29 · 100% complete</text>
  <text x="70" y="112" fill="var(--muted)" font-size="8">best score and full completeness are on different rows</text>
</svg>
^ The longest bar (best retrieval, c_match) is 0% complete; the complete candidate (parent P) has a short bar — the two objectives land on different rows.

## Build

The strategy view retrieves the best-scoring small chunk, then reads that chunk's parent for the return — the `best["parent"]` link is what turns a search hit into a bigger answer.

```python filename=modules/context-and-retrieval/code/retrieval-inter-21/parentdoc.py:78-86 COMPLETE
def strategy_view(data):
    q, ctx, chunks = data["query"], data["context_needed"], data["chunks"]
    best = max(chunks, key=lambda c: score(c["tokens"], q))
    ptoks = parent_tokens(chunks, best["parent"])
    print("STRATEGY — what each approach retrieves and returns")
    print("-" * 66)
    print("  small-only:   retrieve %s (score %.2f) -> return it        -> %.0f%% complete" % (best["id"], score(best["tokens"], q), 100 * completeness(best["tokens"], ctx)))
    print("  parent-only:  retrieve parent P (score %.2f) -> return it   -> %.0f%% complete" % (score(ptoks, q), 100 * completeness(ptoks, ctx)))
    print("  small-to-big: retrieve %s (score %.2f) -> return parent P  -> %.0f%% complete" % (best["id"], score(best["tokens"], q), 100 * completeness(ptoks, ctx)))
```

Compare the whole strategies with `--strategy`.

```text filename=--strategy
STRATEGY — what each approach retrieves and returns
------------------------------------------------------------------
  small-only:   retrieve c_match (score 0.67) -> return it        -> 0% complete
  parent-only:  retrieve parent P (score 0.29) -> return it   -> 100% complete
  small-to-big: retrieve c_match (score 0.67) -> return parent P  -> 100% complete
```

Small-only retrieves brilliantly (0.67) and answers incompletely (0%). Parent-only answers completely (100%) but retrieves at 0.29 — in a real corpus that weaker score can lose to some other section's focused chunk, so it may not be retrieved at all. Small-to-big retrieves with the 0.67 chunk *and* returns the 100%-complete parent: it took the retrieval score from the row that had it and the completeness from the row that had it. The chunk you search and the chunk you return were never required to be the same.

<svg role="img" aria-label="Small-to-big combines c_match's 0.67 retrieval score with parent P's 100 percent completeness" viewBox="0 0 300 110" width="300" height="110">
  <rect x="20" y="20" width="80" height="26" fill="var(--s1)"/><text x="30" y="37" fill="var(--panel)" font-size="8">search c_match</text>
  <text x="30" y="58" fill="var(--s1)" font-size="7">score 0.67 (precise)</text>
  <text x="108" y="37" fill="var(--muted)" font-size="12">→</text>
  <rect x="125" y="20" width="90" height="26" fill="var(--s2)"/><text x="135" y="37" fill="var(--panel)" font-size="8">return parent P</text>
  <text x="135" y="58" fill="var(--s2)" font-size="7">100% context (complete)</text>
  <text x="222" y="37" fill="var(--muted)" font-size="8">both</text>
  <text x="20" y="88" fill="var(--muted)" font-size="8">the searched chunk and the returned chunk are different granularities on purpose</text>
</svg>
^ Small-to-big draws its retrieval score from the small chunk and its completeness from the parent — the two arrows point at different objects, which is the whole idea.

## Definition of done

The self-test pins the decoupling: the small chunk retrieves best, it is incomplete, the parent is complete, the parent retrieves worse, and small-to-big keeps the best score and full completeness.

```python filename=modules/context-and-retrieval/code/retrieval-inter-21/parentdoc.py:98-110 COMPLETE
    small_scores_best = score(best["tokens"], q) > score(ptoks, q)
    print("  the small query-chunk retrieves better than the parent = %s (%.2f > %.2f)" % (small_scores_best, score(best["tokens"], q), score(ptoks, q)))

    small_incomplete = completeness(best["tokens"], ctx) < 1.0
    print("  the small chunk alone is an incomplete answer = %s (%.0f%% of context)" % (small_incomplete, 100 * completeness(best["tokens"], ctx)))

    parent_complete = completeness(ptoks, ctx) == 1.0
    print("  the parent contains all the needed context = %s (%.0f%%)" % (parent_complete, 100 * completeness(ptoks, ctx)))

    parent_retrieval_weaker = score(ptoks, q) < score(best["tokens"], q)
    print("  the parent retrieves worse (why not just index parents) = %s" % parent_retrieval_weaker)

    small_to_big_best_of_both = score(best["tokens"], q) == max(score(c["tokens"], q) for c in chunks) and completeness(ptoks, ctx) == 1.0
    print("  small-to-big keeps the best score and full completeness = %s" % small_to_big_best_of_both)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the small chunk matches best but is incomplete; the parent completes it; small-to-big does both
------------------------------------------------------------------------------------------------------------
  the small query-chunk retrieves better than the parent = True (0.67 > 0.29)
  the small chunk alone is an incomplete answer = True (0% of context)
  the parent contains all the needed context = True (100%)
  the parent retrieves worse (why not just index parents) = True
  small-to-big keeps the best score and full completeness = True
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  small_scores_best=True  small_incomplete=True  parent_complete=True  parent_retrieval_weaker=True  small_to_big_best_of_both=True
```

**Done means the two objectives are provably split: the searched c_match scores 0.67 (the max) while the returned parent P is 100% complete, so small-to-big holds both numbers no single chunk held.**

## Boss fight

Small-to-big returned the whole parent. Predict the cost of making the parent bigger and bigger to guarantee completeness. It is tempting to return an enormous parent so the context is never missing.

A huge parent buys completeness with context-budget waste and dilution at generation time. Return a whole chapter to answer one question and you fill the model's window with mostly-irrelevant text, spend tokens you did not need, and risk the lost-in-the-middle effect where the actual answer, buried in a large passage, gets less attention than it would in a focused one. The parent should be the smallest unit that reliably contains the answer's context — a section, not the document — so completeness is achieved without drowning the answer. Small-to-big is not "return more," it is "return the right enclosing unit," and that unit has a size that is tuned, not maximized.

The mirror-image mistake is letting the search chunks be so small they lose the query itself. If you split so finely that "refund" and "policy" land in different chunks, no small chunk matches both terms, and the precise retrieval you were buying evaporates — you have fine chunks that individually match nothing. The search granularity must still be large enough to hold a matchable unit of the query; small-to-big pairs small-enough-to-match search chunks with large-enough-to-answer parents, and both sizes are choices, not extremes.

```python filename=modules/context-and-retrieval/code/retrieval-inter-21/parentdoc.py:45-47 COMPLETE
def score(tokens, query):
    """Precision-weighted retrieval score: query overlap divided by the chunk's length."""
    return overlap(tokens, query) / len(tokens)
```

**Search small chunks for precise retrieval and return their parent for complete context — decoupling the searched unit from the returned one — but size the parent to the smallest enclosing context, not the whole document, and keep search chunks large enough to still match the query.**

## External resources

The LlamaIndex and LangChain "parent document retriever" / "auto-merging retriever" documentation — the production implementations of searching child chunks and returning parents, with the chunk-size parameters.

Discussions of "sentence-window retrieval" in RAG guides — a close variant that retrieves a sentence and returns a window of surrounding sentences, the same search-small-return-big idea at a different granularity.

The companion "chunking: cut too fine" and "chunk overlap" modules — chunk size and overlap are the tensions small-to-big resolves by using two granularities at once.
