---
id: hyde-inter-01
title: Embed a hypothetical answer, not the question — or the query's words match the wrong document
topic: context-and-retrieval
level: intermediate
status: ready
time: 18 min
summary: A question and its answer are written in different vocabularies. "How long until a refund" is made of question words — how, long, until — plus a topic word, while the answer "refunds are processed within thirty days of receipt" is made of answer words. They barely overlap, so embedding the raw question pulls the search toward text that looks like a question (an FAQ, another user's post) rather than the passage that answers it. HyDE — Hypothetical Document Embeddings — asks the model to write a hypothetical answer first, then retrieves with that answer's vector; the guess need not be factually correct, only answer-shaped. On a fixture, the query's nearest passage is the FAQ (cosine 0.447, sharing "how" and "refund") while the correct answer scores only 0.204 — the query retrieves the wrong document — but the hypothetical answer's nearest passage is the correct one (0.730), because it shares "refund", "processed", "within", and "days" with it.
eli5: If you want to find the page in a cookbook that tells you how long to bake bread, flipping to pages that ask "how long do I bake bread?" won't help — you want the page that says "bake for forty minutes." So first guess the answer in your own words — "bake it about forty minutes" — and go looking for the page that sounds like that. Even if your guess of the time is wrong, it's shaped like the answer, so it lands you on the right page.
---

## Why this module

Searching with the user's question matches documents that are shaped like questions, but the document you need is shaped like an answer, and those two share almost no words.

Embedding-based retrieval matches on vocabulary and phrasing. A question is built from interrogative words and a topic — "how long until a refund" — and the passage that answers it is built from declarative answer words — "refunds are processed within thirty days of receipt." The only word they share is the topic. So when you embed the raw question and pull the nearest passage, the question's words drag the match toward other question-shaped text: an FAQ heading that also says "how" and "refund," a forum post asking the same thing. The retriever is doing exactly what it was built to do — find the most similar text — and the most similar text to a question is another question, not its answer. The asymmetry between how questions and answers are written is the whole problem.

**A question and its answer are written in different vocabularies, so a raw-question embedding lands nearest to other questions, not to the passage that answers it.**

HyDE closes the gap by searching with an answer. Before retrieving anything, ask the model to write a hypothetical answer to the query — it comes out in the vocabulary and style of a real answer. The surprising part is that it does not need to be factually correct: even a made-up answer that guesses the wrong number is still written like the target passage, so its embedding lands near the real answer's. You retrieve with the hypothetical document's vector instead of the question's, and the nearest passage is the one that actually answers it. This module scores a query and a hypothetical answer against the same passages and shows the query miss while the hypothetical hits.

## Concepts

**Question-answer asymmetry** is the root cause: questions and answers share a topic but little else, so a question embedding is closer to other questions than to its answer.

A **raw-query embedding** searches with the question's own words, which pulls it toward question-shaped documents — FAQs, restated questions — that match the interrogative vocabulary rather than the answer.

A **hypothetical document** is an answer the model writes to the query before any retrieval. It carries answer vocabulary, so its embedding sits in the region of space where real answers live.

**The hypothetical answer may be wrong.** Its job is not to be correct but to be answer-shaped; a factually mistaken guess still matches the true passage on structure and vocabulary, and the real passage is what you ultimately return, not the guess.

```python filename=modules/context-and-retrieval/code/hyde-inter-01/hyde.py:44-47 COMPLETE
def cosine(a, b):
    """Cosine similarity over token presence: shared tokens / sqrt(|a| * |b|)."""
    sa, sb = set(a), set(b)
    return len(sa & sb) / math.sqrt(len(sa) * len(sb))
```

**HyDE trades the question's vocabulary for an answer's: you generate a decoy shaped like the target, throw it at the index, and keep whatever real passage it sticks to — so retrieval matches answer-to-answer instead of question-to-answer.**

<svg role="img" aria-label="The question and answer share only the topic word refund; the hypothetical answer sits in the same vocabulary region as the real answer" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">vocabulary regions in embedding space</text>
  <ellipse cx="80" cy="60" rx="55" ry="34" fill="none" stroke="var(--s2)" stroke-width="1"/><text x="52" y="30" fill="var(--s2)" font-size="8">question words</text>
  <text x="60" y="55" fill="var(--muted)" font-size="7">how long until</text>
  <ellipse cx="215" cy="60" rx="60" ry="34" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="188" y="30" fill="var(--s1)" font-size="8">answer words</text>
  <text x="175" y="55" fill="var(--muted)" font-size="7">processed within days</text>
  <circle cx="148" cy="62" r="3" fill="var(--ink)"/><text x="132" y="78" fill="var(--muted)" font-size="7">refund (shared topic)</text>
  <circle cx="205" cy="70" r="3" fill="var(--s1)"/><text x="190" y="84" fill="var(--s1)" font-size="7">hypothetical</text>
  <text x="30" y="112" fill="var(--muted)" font-size="8">the query sits left; the hypothetical answer sits right, beside the real answer</text>
</svg>
^ The question and its answer overlap only at the topic word; the hypothetical answer lives in the answer region, which is why searching with it lands on the real passage.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/hyde-inter-01/hyde.py

The fixture is a query, a hypothetical answer, and three candidate passages, all tokenized.

```json filename=modules/context-and-retrieval/code/hyde-inter-01/hyde.json:1-5 COMPLETE
{
  "_meta": "A retrieval fixture showing question-answer asymmetry. query is what the user asks, tokenized. hypothetical is a pseudo-answer the LLM writes to the query BEFORE any retrieval — it is written in the style and vocabulary of an answer, and it need not be factually correct (here it says 'business days', the real passage says 'thirty days'). passages are the candidate documents. We embed each text as its set of tokens and score similarity by cosine over token presence: overlap / sqrt(|a|*|b|). The point: the query shares its words with the wrong passage (the FAQ, which is itself a question), while the hypothetical answer shares its words with the right passage (the actual answer), so searching with the hypothetical retrieves better than searching with the query.",
  "query": ["how", "long", "until", "refund"],
  "hypothetical": ["refund", "processed", "within", "business", "days"],
```

The similarity is cosine over token presence; retrieval returns the passage with the highest similarity to whatever text you search with.

```python filename=modules/context-and-retrieval/code/hyde-inter-01/hyde.py:50-52 COMPLETE
def best_passage(text, passages):
    """The passage id with the highest cosine similarity to the given text."""
    return max(passages, key=lambda pid: cosine(text, passages[pid]))
```

Run `--score` to see every passage against both the query and the hypothetical answer.

```text filename=--score
SCORE — cosine similarity of each passage to the query and to the hypothetical answer
------------------------------------------------------------------
  passage       to query   to hypothetical
  p_correct     0.204      0.730
  p_faq         0.447      0.200
  p_shipping    0.000      0.400
------------------------------------------------------------------
  the query scores highest on the FAQ; the hypothetical answer scores highest on the correct passage.
```

Read the two columns. Against the query, the correct passage scores only 0.204 while the FAQ scores 0.447 — the query is more similar to a question-shaped document than to its own answer, because it shares "how" and "refund" with the FAQ but only "refund" with the answer. Against the hypothetical answer, the correct passage jumps to 0.730 — it shares "refund," "processed," "within," and "days" — while the FAQ drops to 0.200. Switching the search text from question to answer completely reorders which passage looks closest.

<svg role="img" aria-label="Against the query the FAQ scores 0.447 above the correct passage's 0.204; against the hypothetical answer the correct passage scores 0.730 above the FAQ's 0.200" viewBox="0 0 300 128" width="300" height="128">
  <text x="10" y="12" fill="var(--muted)" font-size="8">cosine to query (left) vs to hypothetical answer (right)</text>
  <text x="8" y="30" fill="var(--muted)" font-size="8">search with QUERY</text>
  <text x="10" y="45" fill="var(--muted)" font-size="7">correct</text><rect x="55" y="38" width="41" height="9" fill="var(--s1)"/><text x="99" y="46" fill="var(--muted)" font-size="7">0.204</text>
  <text x="10" y="58" fill="var(--muted)" font-size="7">faq</text><rect x="55" y="51" width="89" height="9" fill="var(--s2)"/><text x="147" y="59" fill="var(--s2)" font-size="7">0.447 ← wins</text>
  <text x="8" y="82" fill="var(--muted)" font-size="8">search with HYPOTHETICAL</text>
  <text x="10" y="97" fill="var(--muted)" font-size="7">correct</text><rect x="55" y="90" width="146" height="9" fill="var(--s1)"/><text x="204" y="98" fill="var(--s1)" font-size="7">0.730 ← wins</text>
  <text x="10" y="110" fill="var(--muted)" font-size="7">faq</text><rect x="55" y="103" width="40" height="9" fill="var(--muted)"/><text x="98" y="111" fill="var(--muted)" font-size="7">0.200</text>
  <text x="10" y="124" fill="var(--muted)" font-size="8">the winner flips from the FAQ to the correct passage when you search with the answer</text>
</svg>
^ Searching with the query, the FAQ's bar is longest; searching with the hypothetical answer, the correct passage's bar is longest — the same index, a different winner.

## Build

The scores decide what gets retrieved. Run `--retrieve`.

```text filename=--retrieve
RETRIEVE — top passage by query vs by hypothetical answer
------------------------------------------------------------------
  search with the QUERY:               retrieves p_faq       (cosine 0.447)
  search with the HYPOTHETICAL answer: retrieves p_correct   (cosine 0.730)
------------------------------------------------------------------
  the query lands on a question-shaped doc; the hypothetical answer lands on the answer.
```

Searching with the query retrieves p_faq — a question-shaped document that does not answer anything, because its interrogative words matched the query's. Searching with the hypothetical answer retrieves p_correct, the passage that actually states the refund window. And recall the hypothetical answer was factually wrong: it said "business days," the real passage says "thirty days." It did not matter — the guess only had to be shaped like an answer, and that shape was enough to land on the right passage. The model's job was to point the search in the answer's direction, not to know the answer.

<svg role="img" aria-label="The query arrow points to the FAQ; the hypothetical answer arrow points to the correct passage" viewBox="0 0 300 110" width="300" height="110">
  <rect x="15" y="24" width="60" height="20" fill="var(--s2)"/><text x="24" y="38" fill="var(--panel)" font-size="8">query</text>
  <line x1="75" y1="34" x2="150" y2="34" stroke="var(--s2)" stroke-width="1.5"/><polygon points="150,34 144,31 144,37" fill="var(--s2)"/>
  <rect x="152" y="24" width="70" height="20" fill="var(--grid)"/><text x="160" y="38" fill="var(--muted)" font-size="8">FAQ (wrong)</text>
  <rect x="15" y="70" width="60" height="20" fill="var(--s1)"/><text x="20" y="84" fill="var(--panel)" font-size="7">hypo answer</text>
  <line x1="75" y1="80" x2="150" y2="80" stroke="var(--s1)" stroke-width="1.5"/><polygon points="150,80 144,77 144,83" fill="var(--s1)"/>
  <rect x="152" y="70" width="90" height="20" fill="var(--s1)"/><text x="160" y="84" fill="var(--panel)" font-size="8">correct passage</text>
  <text x="15" y="104" fill="var(--muted)" font-size="8">the answer-shaped decoy points at the answer even though its facts are wrong</text>
</svg>
^ The question points the retriever at a question; the hypothetical answer points it at the answer — the redirect is the entire mechanism.

## Definition of done

The self-test pins the reversal: the query retrieves the wrong passage, the hypothetical retrieves the right one, it scores the correct passage far higher, the query prefers a question-shaped doc, and the hypothetical is not a copy of the passage.

```python filename=modules/context-and-retrieval/code/hyde-inter-01/hyde.py:85-98 COMPLETE
    query_retrieves_wrong = best_passage(q, passages) != correct
    print("  searching with the query retrieves the wrong passage = %s (got %s)" % (query_retrieves_wrong, best_passage(q, passages)))

    hyde_retrieves_right = best_passage(h, passages) == correct
    print("  searching with the hypothetical answer retrieves the correct passage = %s (got %s)" % (hyde_retrieves_right, best_passage(h, passages)))

    hyde_scores_correct_higher = cosine(h, passages[correct]) > cosine(q, passages[correct])
    print("  the hypothetical answer matches the correct passage far better than the query does = %s (%.3f > %.3f)" % (hyde_scores_correct_higher, cosine(h, passages[correct]), cosine(q, passages[correct])))

    question_answer_asymmetry = cosine(q, passages[correct]) < cosine(q, passages["p_faq"])
    print("  the query matches a question-shaped doc better than its own answer = %s (%.3f < %.3f)" % (question_answer_asymmetry, cosine(q, passages[correct]), cosine(q, passages["p_faq"])))

    hyde_not_a_copy = "business" in h and "business" not in passages[correct]
    print("  the hypothetical answer is not a copy of the passage (it can be factually wrong) = %s" % hyde_not_a_copy)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the query retrieves the wrong passage; the hypothetical answer retrieves the right one
----------------------------------------------------------------------------------------------------
  searching with the query retrieves the wrong passage = True (got p_faq)
  searching with the hypothetical answer retrieves the correct passage = True (got p_correct)
  the hypothetical answer matches the correct passage far better than the query does = True (0.730 > 0.204)
  the query matches a question-shaped doc better than its own answer = True (0.204 < 0.447)
  the hypothetical answer is not a copy of the passage (it can be factually wrong) = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  query_retrieves_wrong=True  hyde_retrieves_right=True  hyde_scores_correct_higher=True  question_answer_asymmetry=True  hyde_not_a_copy=True
```

**Done means the reversal is proven: the query retrieves p_faq (0.447) over the correct passage (0.204), while the hypothetical answer retrieves p_correct (0.730) — and it does so with a factually wrong guess ("business days" not "thirty days"), so answer-shape, not correctness, is what mattered.**

## Boss fight

HyDE fixed retrieval with a made-up answer. Predict when a hypothetical answer helps and when it hurts, and what its cost is. It is tempting to route every query through HyDE now that it worked here.

HyDE helps most where question and answer vocabularies diverge and the model can plausibly guess the answer's shape — factual and how-to queries in a domain the model roughly understands. It hurts where the model cannot write a sensible hypothetical: a query about a private, novel, or highly specific fact (an internal ticket ID, a name the model has never seen) produces a hypothetical that is confidently off-topic, and its embedding drags the search toward that wrong region, retrieving worse than the plain query would. So HyDE is not free insurance; it is a bet that the model's guess is shaped like the truth, and on out-of-distribution queries that bet loses. Many systems hedge by retrieving with both the query and the hypothetical and fusing the results, so a bad guess cannot fully override the literal query.

The other cost is latency and spend: HyDE adds a full generation before retrieval even starts, so every query pays for an extra model call on the critical path. That is acceptable for a research assistant answering a hard question and wasteful for a high-traffic autocomplete. And because the hypothetical can hallucinate, you must keep the discipline that the *retrieved passage*, not the hypothetical, is what reaches the answer step — the hypothetical is a search probe that gets thrown away, never a source. Use HyDE where the vocabulary gap is real and the extra call is affordable, fuse it with the raw query to stay safe, and never let the decoy leak into the context as if it were evidence.

```python filename=modules/context-and-retrieval/code/hyde-inter-01/hyde.py:70-74 COMPLETE
    bq, bh = best_passage(q, passages), best_passage(h, passages)
    print("RETRIEVE — top passage by query vs by hypothetical answer")
    print("-" * 66)
    print("  search with the QUERY:               retrieves %-11s (cosine %.3f)" % (bq, cosine(q, passages[bq])))
    print("  search with the HYPOTHETICAL answer: retrieves %-11s (cosine %.3f)" % (bh, cosine(h, passages[bh])))
```

**Retrieve with a model-written hypothetical answer, not the raw question, so the search vector carries answer vocabulary and matches the answer passage — but the guess only helps when it is shaped like the truth, so fuse it with the literal query for out-of-distribution cases, pay for the extra generation only where the vocabulary gap is real, and throw the hypothetical away rather than citing it.**

## External resources

The paper "Precise Zero-Shot Dense Retrieval without Relevance Labels" (Gao et al.) — the original HyDE method, showing that a generated hypothetical document, even an imperfect one, improves zero-shot retrieval across languages and tasks.

LlamaIndex and LangChain "HyDE query transform" documentation — the production implementations, including options to fuse the hypothetical with the original query.

The companion "expand a vague query before you embed it" and "the hybrid retrieval pipeline" modules — query expansion is the lighter-weight cousin that rewrites rather than answers, and hybrid retrieval's lexical leg is another hedge against a single embedding's blind spots.
