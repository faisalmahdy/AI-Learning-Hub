---
id: compress-inter-01
title: Compress a retrieved chunk to its query-relevant sentences — or you spend the budget on filler that answers nothing
topic: context-and-retrieval
level: intermediate
status: ready
time: 17 min
summary: Retrieval returns whole chunks, but a chunk is mostly not about the query — an intro line, an unrelated aside, a sign-off, and one or two sentences that actually address the question. Inject the whole chunk and you pay for all of it: the filler eats context-window budget you could spend on more chunks, and it dilutes the model's attention, burying the answer among on-topic-looking text. The chunk was the right thing to retrieve; it is the wrong thing to inject whole. Contextual compression scores each sentence by its query overlap and keeps only those clearing a threshold, before the chunk enters the prompt. On a five-sentence chunk of 26 tokens where only two sentences mention the query (scores 1 and 2, the other three scoring 0), keeping the two yields 13 tokens — half the size — and both carry the answer detail "30", so the answer is preserved while the filler is gone.
eli5: When you find the right page in a manual, you don't read the whole page aloud to someone who asked one question — you read them the one sentence that answers it. A retrieved chunk is that page: mostly stuff that isn't the answer. Before handing it to the model, cross out the sentences that don't mention what was asked and keep the ones that do. You still found the answer, but now it fits in a fraction of the space and nothing distracts from it.
---

## Why this module

Finding the right chunk and injecting the right text are two different jobs, and a chunk that was perfect for retrieval is mostly wasted space once it reaches the prompt.

Retrieval works at the chunk granularity for good reason: a chunk is big enough to match a query and to hold the surrounding context. But that same size means most of a chunk's tokens are not the answer. A support passage that contains the refund window also contains a greeting, a note about shipping, and a sign-off — sentences that came along because they were in the same chunk, not because they address the question. Inject the chunk whole and every one of those tokens costs you twice: once in context-window budget, which you could have spent retrieving another chunk, and once in the model's attention, which now has to find the answer sentence inside a block of plausibly-relevant filler. The filler is not obviously junk — it came from a relevant document — which is exactly what makes it good at hiding the answer.

**A retrieved chunk is the right unit to search but the wrong unit to inject whole, because most of its tokens are filler that spends budget and dilutes attention without addressing the query.**

Contextual compression closes the gap by filtering inside the chunk before it enters the prompt. Score each sentence by how much of the query it contains, keep the sentences that clear a threshold, and drop the rest. The answer sentence survives because it carries the query terms; the filler is removed. You retrieved at the chunk granularity for recall and inject at the sentence granularity for density. This module scores a chunk's sentences, compresses it, and shows the answer preserved at half the token cost.

## Concepts

**Retrieval granularity is the chunk**, chosen large enough to match and to carry context. This is the right unit for the search, and the reason a chunk arrives with filler attached.

**Injection granularity should be finer.** What you put in the prompt need not be the whole retrieved chunk; it can be the subset of sentences that actually address the query.

A **sentence's relevance score** is its overlap with the query. The answer sentence scores high because it contains the query terms; filler sentences score zero.

```python filename=modules/context-and-retrieval/code/compress-inter-01/compress.py:40-42 COMPLETE
def score(sentence, query):
    """A sentence's relevance: how many distinct query terms it contains."""
    return len(set(query) & set(sentence))
```

**Compression keeps the sentences above a threshold** and drops the rest, so the injected text shrinks to the part that earns its place while the answer, being the highest-scoring sentence, is retained.

**The two-granularity split is the whole idea: search coarse for recall, inject fine for density — the retriever finds the passage, and the compressor strips it to what answers the query.**

<svg role="img" aria-label="A retrieved chunk of five sentences is filtered to the two that mention the query before it enters the prompt" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">retrieve whole chunk → compress → inject</text>
  <rect x="15" y="24" width="55" height="52" fill="none" stroke="var(--grid)" stroke-width="1"/>
  <rect x="20" y="28" width="45" height="7" fill="var(--grid)"/><rect x="20" y="37" width="45" height="7" fill="var(--s1)"/><rect x="20" y="46" width="45" height="7" fill="var(--grid)"/><rect x="20" y="55" width="45" height="7" fill="var(--s1)"/><rect x="20" y="64" width="45" height="7" fill="var(--grid)"/>
  <text x="20" y="88" fill="var(--muted)" font-size="7">chunk: 5 sentences</text>
  <text x="80" y="52" fill="var(--muted)" font-size="10">→</text>
  <rect x="100" y="36" width="55" height="26" fill="none" stroke="var(--grid)" stroke-width="1"/>
  <rect x="105" y="40" width="45" height="7" fill="var(--s1)"/><rect x="105" y="49" width="45" height="7" fill="var(--s1)"/>
  <text x="100" y="88" fill="var(--muted)" font-size="7">kept: 2 relevant</text>
  <text x="165" y="52" fill="var(--muted)" font-size="10">→</text>
  <rect x="185" y="40" width="100" height="18" fill="var(--s1)"/><text x="190" y="52" fill="var(--panel)" font-size="8">into the prompt</text>
</svg>
^ The chunk is retrieved whole for recall, then the compressor keeps only the two query-relevant sentences (colored) and drops the filler (grey) before anything is injected.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/compress-inter-01/compress.py

The fixture is one retrieved chunk of five sentences, the query, and the answer token the kept text must retain.

```json filename=modules/context-and-retrieval/code/compress-inter-01/compress.json:5-13 COMPLETE
  "threshold": 1,
  "sentences": [
    ["our", "store", "values", "customers"],
    ["a", "refund", "completes", "within", "30", "days"],
    ["shipping", "is", "separate", "from", "returns"],
    ["refund", "time", "is", "30", "days", "after", "receipt"],
    ["contact", "support", "for", "help"]
  ]
}
```

Compression keeps the sentence indices clearing the threshold and measures token counts by sentence.

```python filename=modules/context-and-retrieval/code/compress-inter-01/compress.py:45-53 COMPLETE
def keep(sentences, query, threshold):
    """Indices of the sentences that clear the relevance threshold."""
    return [i for i, s in enumerate(sentences) if score(s, query) >= threshold]


def tokens(sentences, indices=None):
    """Total token count of all sentences, or of the given indices."""
    idx = range(len(sentences)) if indices is None else indices
    return sum(len(sentences[i]) for i in idx)
```

Run `--score` to see each sentence judged.

```text filename=--score
SCORE — each sentence's query overlap and whether it is kept (threshold 1)
------------------------------------------------------------------
  s0  score 0  drop  our store values customers
  s1  score 1  KEEP  a refund completes within 30 days
  s2  score 0  drop  shipping is separate from returns
  s3  score 2  KEEP  refund time is 30 days after receipt
  s4  score 0  drop  contact support for help
------------------------------------------------------------------
  only the sentences that mention the query survive; the filler is dropped.
```

Three of the five sentences — the greeting, the shipping aside, and the sign-off — contain no query term and score zero. They are real text from a real retrieved chunk, but they do not address "refund time," so compression drops them. Sentence 1 scores 1 and sentence 3 scores 2 (it has both query terms), so both are kept. The answer detail "30 days" lives in the kept sentences; the discarded sentences carried none of it. The filter kept exactly the part of the chunk the query was asking about.

<svg role="img" aria-label="Five sentences: s1 and s3 mention the query and are kept, s0, s2, s4 score zero and are dropped" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">sentence relevance to the query (kept vs dropped)</text>
  <text x="10" y="30" fill="var(--muted)" font-size="8">s0</text><rect x="40" y="21" width="4" height="10" fill="var(--grid)"/><text x="50" y="30" fill="var(--muted)" font-size="7">score 0 — drop</text>
  <text x="10" y="48" fill="var(--s1)" font-size="8">s1</text><rect x="40" y="39" width="60" height="10" fill="var(--s1)"/><text x="106" y="48" fill="var(--s1)" font-size="7">score 1 — KEEP</text>
  <text x="10" y="66" fill="var(--muted)" font-size="8">s2</text><rect x="40" y="57" width="4" height="10" fill="var(--grid)"/><text x="50" y="66" fill="var(--muted)" font-size="7">score 0 — drop</text>
  <text x="10" y="84" fill="var(--s1)" font-size="8">s3</text><rect x="40" y="75" width="120" height="10" fill="var(--s1)"/><text x="166" y="84" fill="var(--s1)" font-size="7">score 2 — KEEP (answer)</text>
  <text x="10" y="102" fill="var(--muted)" font-size="8">s4</text><rect x="40" y="93" width="4" height="10" fill="var(--grid)"/><text x="50" y="102" fill="var(--muted)" font-size="7">score 0 — drop</text>
  <text x="10" y="116" fill="var(--muted)" font-size="8">the two bars that clear the threshold are the two sentences worth injecting</text>
</svg>
^ Only s1 and s3 have any query overlap, so they are kept; the three zero-score sentences are filler and dropped, leaving just the part of the chunk that answers.

## Build

The payoff is tokens. Run `--compress`.

```text filename=--compress
COMPRESS — full chunk vs compressed chunk
------------------------------------------------------------------
  full chunk:       5 sentences, 26 tokens   answer '30' present: True
  compressed chunk: 2 sentences, 13 tokens   answer '30' present: True
  budget kept:      50% of the tokens removed
------------------------------------------------------------------
  half the tokens gone, the answer still there -- density without losing the answer.
```

The full chunk is 26 tokens; the compressed chunk is 13 — half removed — and the answer token "30" is present in both. That saved budget is not abstract: it is another chunk you can now afford to retrieve, or attention the model no longer spends on the greeting and the sign-off. Across many chunks in a real context window the effect compounds, often halving or better the tokens spent on retrieved content while keeping the same answers. And the compression is cheap — a per-sentence relevance score, no extra model call in this lexical form — so it is close to free budget.

<svg role="img" aria-label="The full chunk is 26 tokens and the compressed chunk 13 tokens, both containing the answer" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">tokens injected (both contain the answer)</text>
  <line x1="70" y1="20" x2="70" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="26" width="200" height="16" fill="var(--s2)"/><text x="74" y="38" fill="var(--panel)" font-size="8">full chunk: 26 tokens</text>
  <rect x="70" y="50" width="100" height="16" fill="var(--s1)"/><text x="74" y="62" fill="var(--panel)" font-size="8">compressed: 13 tokens (answer kept)</text>
  <text x="70" y="94" fill="var(--muted)" font-size="8">half the budget freed, the answer detail '30' still present in both</text>
</svg>
^ The compressed bar is half the full bar's length, yet both carry the answer — the removed half was filler that cost budget and attention without helping.

## Definition of done

The self-test pins it: the answer is in the full chunk and survives compression, the compressed chunk is smaller, the top-scoring sentence is kept, and every zero-overlap filler is dropped.

```python filename=modules/context-and-retrieval/code/compress-inter-01/compress.py:90-105 COMPLETE
    answer_in_full = any(ans in s for s in sents)
    print("  the answer token is in the full chunk = %s" % answer_in_full)

    answer_in_compressed = any(ans in sents[i] for i in kept)
    print("  the answer token survives compression = %s" % answer_in_compressed)

    compressed_smaller = tokens(sents, kept) < tokens(sents)
    print("  the compressed chunk is smaller than the full chunk = %s (%d < %d tokens)" % (compressed_smaller, tokens(sents, kept), tokens(sents)))

    top = max(range(len(sents)), key=lambda i: score(sents[i], q))
    top_sentence_kept = top in kept
    print("  the highest-scoring sentence is kept = %s (s%d, score %d)" % (top_sentence_kept, top, score(sents[top], q)))

    filler = [i for i, s in enumerate(sents) if score(s, q) == 0]
    filler_dropped = all(i not in kept for i in filler)
    print("  every zero-overlap filler sentence is dropped = %s (%s)" % (filler_dropped, ["s%d" % i for i in filler]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the answer sentence is kept, the filler is dropped, and the compressed chunk is smaller
--------------------------------------------------------------------------------------------------------
  the answer token is in the full chunk = True
  the answer token survives compression = True
  the compressed chunk is smaller than the full chunk = True (13 < 26 tokens)
  the highest-scoring sentence is kept = True (s3, score 2)
  every zero-overlap filler sentence is dropped = True (['s0', 's2', 's4'])
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  answer_in_full=True  answer_in_compressed=True  compressed_smaller=True  top_sentence_kept=True  filler_dropped=True
```

**Done means the density gain is proven safe: compression cut the chunk from 26 to 13 tokens by dropping the three zero-overlap fillers (s0, s2, s4) while keeping s1 and the top-scoring s3, and the answer token "30" is present before and after.**

## Boss fight

Lexical overlap compressed this chunk. Predict where a word-overlap filter fails, and the risk that compression itself introduces. It is tempting to trust the overlap score to always keep the answer.

Lexical overlap fails exactly where retrieval's lexical leg fails: when the answer sentence does not share words with the query. If the query says "how long for a refund" and the answer sentence says "reimbursements are issued within thirty days," a word-overlap score is zero and compression drops the very sentence that answers — the same question-answer vocabulary gap that motivates dense retrieval and HyDE. So a robust compressor scores sentences by semantic similarity (an embedding, or a cross-encoder relevance model, or a small LLM asked "is this sentence relevant to the query"), not raw token overlap. The lexical version in this module is the cheap approximation; the general technique scores relevance however your retriever does, so the compressor does not throw away answers its own retriever would have found.

The risk compression adds is dropping context the answer needs. A sentence can be essential yet score low: the answer "within 30 days" may depend on a previous sentence establishing "for online orders," and if you keep only the high-scoring sentence you inject a rule without its condition. Compression trades recall of context for density, and set too aggressively it produces confidently wrong answers built on a fragment torn from its qualifier. Mitigate it by keeping a small window around each kept sentence (the neighbors that carry its conditions), by tuning the threshold conservatively, and by compressing to the answer plus its immediate context rather than to the answer alone. The goal is to remove filler, not to shred the passage — keep enough that the retained sentences still mean what they meant in place.

```python filename=modules/context-and-retrieval/code/compress-inter-01/compress.py:72-74 COMPLETE
    kept = keep(sents, q, thr)
    full_ans = any(ans in s for s in sents)
    comp_ans = any(ans in sents[i] for i in kept)
```

**Compress a retrieved chunk to its query-relevant sentences before injecting — search coarse for recall, inject fine for density — but score relevance semantically, not by raw word overlap (or you drop answers phrased in different words), and keep each answer sentence's surrounding context, because a fragment torn from its qualifier is a confident wrong answer.**

## External resources

LangChain's "Contextual Compression" retriever documentation — the production pattern of a base retriever plus a compressor (an LLM extractor, an embeddings filter, or a cross-encoder) that strips retrieved documents to the query-relevant spans.

The literature on extractive query-focused summarization and sentence-level relevance filtering — the general problem of selecting the sentences that answer a query, of which retrieval compression is a special case.

The companion "pack the context by score-per-token" and "embed a hypothetical answer, not the question" modules — score-per-token selects among chunks while compression trims within one, and the HyDE module explains the vocabulary gap that makes lexical relevance scoring miss answers.
