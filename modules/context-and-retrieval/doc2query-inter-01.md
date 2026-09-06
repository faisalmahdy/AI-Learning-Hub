---
id: doc2query-inter-01
title: Index the questions a passage answers, not only its words — or a short query lands on a lexical look-alike, not the answer
topic: context-and-retrieval
level: intermediate
status: ready
time: 17 min
summary: A lexical retriever scores a document by how many query words it contains, so it fails whenever the asker and the passage's author chose different words for the same idea — "how do plants make food from light" versus "photosynthesis converts sunlight energy inside chloroplasts." The right passage shares almost no words with the query and scores near zero, while a passage about a "food processor" that "makes" "meals" shares the surface words and ranks first. doc2query closes the gap from the document side: before indexing, a small model predicts the questions each passage answers, and those predicted questions are appended to the indexed text. The same lexical retriever, unchanged, then matches the query's words against the predicted questions and ranks the right passage first. On a fixture where the query shares its vocabulary with the gold passage's predicted questions and not its text, ranking by text alone puts the look-alike at rank 1 (0.158) and the gold answer at rank 2 (0.000), while ranking by text-plus-expansions lifts the gold answer to rank 1 (0.527).
eli5: A librarian files a book about photosynthesis under the exact words on its cover. You walk up and ask "how do plants make food from light" — none of your words are on that cover, so the librarian shrugs, and hands you a cookbook that happens to say "food" and "make" instead. The fix is to also file the book under the questions it answers: "how do plants make food?" Now when you ask in your own words, the librarian finds the right book — because someone wrote down, ahead of time, the questions it was meant to answer.
---

## Why this module

Lexical retrieval matches words, not meaning, so the moment your query and the answer passage use different vocabulary for the same idea, the retriever ranks a word-for-word look-alike above the passage that actually answers you.

A keyword retriever — BM25, TF-IDF, or any bag-of-words scorer — ranks a document by how many query terms it contains and how rare those terms are. That works when the query and the document speak the same dialect. It breaks the instant they do not. A user asks "how do plants make food from light"; the passage that answers it was written as "photosynthesis converts sunlight energy inside chloroplasts." Not one content word overlaps, so the score is near zero and the passage sinks. Worse, an unrelated passage about a "food processor" that "makes" quick "meals" shares the literal words "food" and "make," so it floats to the top. The retriever did exactly what it was built to do; the failure is that the query's vocabulary and the answer's vocabulary never met.

**A lexical retriever scores word overlap, so a query phrased in different words than the answer passage ranks a lexical look-alike first and the true answer below it — the gap is vocabulary, not relevance.**

You cannot control how a user will phrase a question, but you can control the words a passage is indexed under, and that is the half of the gap doc2query fixes. Before indexing, run a small model over each passage to predict the questions it answers, and append those predicted questions to the text you index. The passage about photosynthesis is now indexed alongside "how do plants make food from light," which shares the asker's words — so the same retriever, unchanged, scores it highly and ranks it first. It is the mirror image of HyDE: HyDE rewrites the query toward the document's words at query time; doc2query rewrites the document toward the query's words, once, at index time. This module ranks a small corpus both ways and shows the gold passage move from rank 2 to rank 1.

## Concepts

**The vocabulary gap** is the mismatch between the words a user puts in a query and the words an author put in the answering passage. Lexical retrieval scores overlap, so a wide gap means a low score even for a perfectly relevant passage.

**A predicted question (the doc2query expansion)** is a question a small model generates from a passage — the kind of question a user who wanted this passage would type. It is phrased in querying language, not the passage's declarative language.

**Indexing the expansions** means appending each passage's predicted questions to the text you put in the index. The retriever is untouched; only the indexed bag of terms grows.

```python filename=modules/context-and-retrieval/code/doc2query-inter-01/doc2query.py:57-60 COMPLETE
def indexed_text(doc, expand, stop):
    """The bag of terms the retriever indexes for a doc: its text, plus its predicted questions when expand=True."""
    text = doc["text"] + (" " + doc["expansions"] if expand else "")
    return Counter(tokens(text, stop))
```

**The retriever never changes.** The same cosine over the same query vector ranks both indexes; the only difference is what went into each document's term vector.

```python filename=modules/context-and-retrieval/code/doc2query-inter-01/doc2query.py:63-68 COMPLETE
def ranking(data, expand):
    """Rank the docs by cosine to the query, indexing text alone (expand=False) or text+expansions (expand=True)."""
    stop = data["stop"]
    qv = Counter(tokens(data["query"], stop))
    scored = [(doc["id"], cosine(qv, indexed_text(doc, expand, stop))) for doc in data["docs"]]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)
```

<svg role="img" aria-label="Query terms fail to reach the passage text directly, but reach it through the passage's predicted questions, which share the query's vocabulary" viewBox="0 0 300 104" width="300" height="104">
  <rect x="6" y="40" width="66" height="26" fill="none" stroke="var(--line)"/><text x="12" y="50" fill="var(--ink)" font-size="8">query</text>
  <text x="10" y="61" fill="var(--muted)" font-size="7">plants make food</text>
  <rect x="120" y="12" width="80" height="26" fill="none" stroke="var(--s1)"/><text x="126" y="22" fill="var(--ink)" font-size="8">predicted Qs</text>
  <text x="124" y="33" fill="var(--muted)" font-size="7">how plants make food</text>
  <rect x="120" y="68" width="80" height="26" fill="none" stroke="var(--muted)"/><text x="126" y="78" fill="var(--ink)" font-size="8">passage text</text>
  <text x="124" y="89" fill="var(--muted)" font-size="7">photosynthesis…</text>
  <line x1="72" y1="50" x2="120" y2="28" stroke="var(--s1)"/><text x="74" y="40" fill="var(--s1)" font-size="7">shared words ✓</text>
  <line x1="72" y1="58" x2="120" y2="80" stroke="var(--muted)" stroke-dasharray="3 3"/><text x="74" y="82" fill="var(--muted)" font-size="7">no shared words ✗</text>
  <line x1="200" y1="28" x2="238" y2="70" stroke="var(--s1)"/><text x="210" y="52" fill="var(--muted)" font-size="7">same passage</text>
  <text x="6" y="102" fill="var(--muted)" font-size="8">the query reaches the passage only through the questions it was predicted to answer</text>
</svg>
^ The query shares no words with the passage text, but its words do match the passage's predicted questions — so indexing those questions gives the query a path to the right passage.

**doc2query fixes the document side of the vocabulary gap: predict the questions a passage answers and index them with it, so the same lexical retriever matches the asker's words without ever changing the query or the scorer.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/doc2query-inter-01/doc2query.py

The fixture is a three-document corpus where the gold passage answers the query but shares its vocabulary only through predicted questions.

```json filename=modules/context-and-retrieval/code/doc2query-inter-01/doc2query.json:3-9 COMPLETE
  "query": "how do plants make food from light",
  "gold": "A",
  "stop": ["a", "an", "the", "of", "in", "into", "from", "for", "and", "to", "do", "does", "on", "with"],
  "docs": [
    {"id": "A", "text": "photosynthesis converts sunlight energy inside chloroplasts producing glucose", "expansions": "how plants make food light energy leaf turns"},
    {"id": "B", "text": "food processor makes quick work chopping vegetables meal", "expansions": "kitchen appliance chopping blender"},
    {"id": "C", "text": "solar panels generate electricity sunlight rooftop inverter", "expansions": "renewable power photovoltaic grid"}
```

Run `--rank` to score the corpus both ways.

```text filename=--rank
RANK — score by passage text alone vs by text plus the questions it answers
--------------------------------------------------------------------
  text only                     text + predicted questions
  B  0.158                 A  0.527  <- gold
  A  0.000  <- gold        B  0.120
  C  0.000                 C  0.000
--------------------------------------------------------------------
  text alone ranks the lexical look-alike first; expansions put the gold answer on top.
```

Look at the text-only column: the gold passage A scores exactly 0.000 — its text and the query have no content word in common — while B, the food processor, scores 0.158 purely on the coincidence that it contains "food" and "make." A keyword retriever hands back the wrong document with complete confidence, because by its own measure the right one is invisible. The text-plus-expansions column flips it: A jumps to 0.527 and takes rank 1, because its predicted questions "how plants make food light energy" carry every query term the passage's own prose lacked. Nothing about the retriever or the query changed between the two columns; only A's indexed vocabulary grew, and that was enough to turn a zero into the top score. This is the whole technique in one table.

<svg role="img" aria-label="Text-only ranking puts document B at 0.158 above gold A at 0.000; text-plus-expansions ranking puts gold A at 0.527 above B at 0.120" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="10" fill="var(--muted)" font-size="8">score (bar length); ✦ marks the gold passage A</text>
  <text x="6" y="26" fill="var(--muted)" font-size="8">text only</text>
  <rect x="70" y="20" width="45" height="10" fill="var(--s2)"/><text x="118" y="28" fill="var(--muted)" font-size="7">B 0.158</text>
  <rect x="70" y="32" width="2" height="10" fill="var(--s1)"/><text x="76" y="40" fill="var(--muted)" font-size="7">✦ A 0.000</text>
  <rect x="70" y="44" width="2" height="10" fill="var(--muted)"/><text x="76" y="52" fill="var(--muted)" font-size="7">C 0.000</text>
  <line x1="6" y1="62" x2="292" y2="62" stroke="var(--grid)"/>
  <text x="6" y="78" fill="var(--muted)" font-size="8">+ expansions</text>
  <rect x="70" y="72" width="150" height="10" fill="var(--s1)"/><text x="223" y="80" fill="var(--muted)" font-size="7">✦ A 0.527</text>
  <rect x="70" y="84" width="34" height="10" fill="var(--s2)"/><text x="107" y="92" fill="var(--muted)" font-size="7">B 0.120</text>
  <rect x="70" y="96" width="2" height="10" fill="var(--muted)"/><text x="76" y="104" fill="var(--muted)" font-size="7">C 0.000</text>
  <text x="6" y="112" fill="var(--muted)" font-size="7">gold goes from invisible (0.000, rank 2) to first (0.527)</text>
</svg>
^ Text-only scoring leaves the gold passage at 0.000 behind the look-alike B; adding predicted questions lifts gold to 0.527 and first place, with the retriever unchanged.

## Build

Where did the lift come from? Run `--gap` to trace each query term to the part of the gold passage it matches.

```text filename=--gap
GAP — which query terms reach the gold passage, and through what
------------------------------------------------------------
  query terms:            ['food', 'how', 'light', 'make', 'plants']
  match gold TEXT:        []
  match gold EXPANSIONS:  ['food', 'how', 'light', 'make', 'plants']
  reached only via expansions: ['food', 'how', 'light', 'make', 'plants']
------------------------------------------------------------
  the query and the passage text barely share words; the predicted questions carry the overlap.
```

Every content term of the query — food, how, light, make, plants — matches the gold passage through its expansions and *none* through its text. The "match gold TEXT" line is literally empty: the passage's declarative prose ("photosynthesis," "sunlight," "chloroplasts") and the user's question share nothing a keyword index can key on. The predicted questions are the entire bridge; strip them and the score is the 0.000 you saw. This is why doc2query is worth the index-time cost of running a model over every passage: the generation happens once per document, offline, and pays off on every future query phrased in user vocabulary. It also composes cleanly — the expansions are just more indexed text, so BM25, hybrid lexical-plus-dense pipelines, and rerankers all inherit the closed gap for free.

<svg role="img" aria-label="All five query content terms match the gold passage only through its expansions and none through its text" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">query term → where it matches the gold passage</text>
  <text x="10" y="30" fill="var(--ink)" font-size="8">plants</text><text x="10" y="44" fill="var(--ink)" font-size="8">make</text><text x="10" y="58" fill="var(--ink)" font-size="8">food</text><text x="10" y="72" fill="var(--ink)" font-size="8">light</text><text x="10" y="86" fill="var(--ink)" font-size="8">how</text>
  <rect x="70" y="20" width="70" height="72" fill="none" stroke="var(--muted)" stroke-dasharray="3 3"/><text x="76" y="34" fill="var(--muted)" font-size="7">TEXT: none</text>
  <rect x="160" y="20" width="90" height="72" fill="none" stroke="var(--s1)"/><text x="166" y="34" fill="var(--s1)" font-size="7">EXPANSIONS</text>
  <line x1="52" y1="27" x2="160" y2="45" stroke="var(--s1)"/><line x1="52" y1="41" x2="160" y2="52" stroke="var(--s1)"/><line x1="52" y1="55" x2="160" y2="59" stroke="var(--s1)"/><line x1="52" y1="69" x2="160" y2="66" stroke="var(--s1)"/><line x1="52" y1="83" x2="160" y2="73" stroke="var(--s1)"/>
  <text x="6" y="99" fill="var(--muted)" font-size="8">five of five query terms reach the passage only through its predicted questions</text>
</svg>
^ Every query term routes to the gold passage through its expansions and none through its text, so the predicted questions are the whole reason the score rose from 0.000.

## Definition of done

The self-test pins the flip: text alone ranks a non-gold look-alike first with the gold below, text-plus-expansions ranks the gold first, and the lift is attributable to query terms that match only the expansions.

```python filename=modules/context-and-retrieval/code/doc2query-inter-01/doc2query.py:109-123 COMPLETE
    base_top_not_gold = base[0][0] != gold
    print("  text-only ranks a non-gold look-alike first = %s (rank 1 = %s)" % (base_top_not_gold, base[0][0]))

    base_gold_rank = [i for i, (d, _) in enumerate(base) if d == gold][0] + 1
    base_gold_below = base_gold_rank > 1
    print("  the gold passage ranks below it on text alone = %s (gold at rank %d)" % (base_gold_below, base_gold_rank))

    exp_gold_first = exp[0][0] == gold
    print("  text-plus-expansions ranks the gold passage first = %s (rank 1 = %s)" % (exp_gold_first, exp[0][0]))

    goldd = next(d for d in data["docs"] if d["id"] == gold)
    qterms = set(tokens(data["query"], stop))
    lift_terms = (qterms & set(tokens(goldd["expansions"], stop))) - set(tokens(goldd["text"], stop))
    lift_from_expansions = len(lift_terms) > 0
    print("  the lift comes from query terms matching only the expansions = %s (%s)" % (lift_from_expansions, sorted(lift_terms)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — text-only ranks a look-alike first and the gold below; doc2query lifts the gold to rank 1
----------------------------------------------------------------------------------------------------
  text-only ranks a non-gold look-alike first = True (rank 1 = B)
  the gold passage ranks below it on text alone = True (gold at rank 2)
  text-plus-expansions ranks the gold passage first = True (rank 1 = A)
  the lift comes from query terms matching only the expansions = True (['food', 'how', 'light', 'make', 'plants'])
  the retriever and query are unchanged; only the indexed text grew = True
```

**Done means the vocabulary gap is proven and closed from the document side: on text alone the gold passage scores 0.000 and sits at rank 2 behind a lexical look-alike, while indexing the passage's predicted questions lifts it to 0.527 at rank 1 — and every point of that lift traces to query terms that match the expansions and not the text, with the retriever and query untouched.**

## Boss fight

Predict where indexing the questions backfires, and what to test before you trust the lift you just saw. It is tempting to generate as many predicted questions as possible for every passage and index them all.

The first trap is that expansions are unvalidated model output, and appending them to the index injects the generator's errors into retrieval. If the small model hallucinates a question a passage does not actually answer, that passage now matches queries it should not, and you have manufactured a false positive at index time that no query-side check can see. Worse, the generator can pull passages toward popular phrasings regardless of content, so a bland passage stuffed with plausible-sounding questions can out-rank a precise one — the same over-expansion that keyword stuffing exploits. The discipline is to keep expansions few, faithful, and derived only from the passage's own content, and to evaluate retrieval quality on held-out queries after adding them, not to assume more predicted questions is strictly better. Measure the precision, not just the recall you gained.

```python filename=modules/context-and-retrieval/code/doc2query-inter-01/doc2query.py:49-54 COMPLETE
def cosine(a, b):
    """Cosine similarity between two term-count vectors (Counters)."""
    dot = sum(a[t] * b[t] for t in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0
```

The second trap is thinking doc2query and dense retrieval are redundant — that a good embedding model already crosses the vocabulary gap, so predicting questions is wasted work. They overlap but do not coincide. A dense retriever maps query and passage into a shared semantic space and can match "make food from light" to "photosynthesis" without shared words, which is exactly the gap doc2query targets — but embeddings have their own failure modes (out-of-domain jargon, rare entities, long passages that dilute the relevant sentence), and doc2query helps precisely there by planting the querying-language surface form in the index. The strongest systems use both: doc2query strengthens the lexical arm of a hybrid retriever, dense embeddings strengthen the semantic arm, and the fusion covers gaps that either alone leaves open. Reach for doc2query when your retrieval is lexical or hybrid and your queries and documents speak different dialects; skip it when a dense retriever already closes the gap and the index-time generation cost is not repaid. The technique is a document-side query rewrite, so its value is exactly the size of the vocabulary gap it closes minus the noise its predictions add.

**doc2query closes the document side of the query-document vocabulary gap by indexing each passage's predicted questions, but the expansions are unvalidated generation, so keep them few and faithful and re-measure precision on held-out queries — and treat it as the lexical complement to dense retrieval (and the index-time mirror of HyDE), reaching for it when your queries and documents use different words and the once-per-document generation cost is repaid across many queries.**

## External resources

The docTTTTTquery / doc2query papers (Nogueira and Lin, "Document Expansion by Query Prediction" and its T5 successor) — the original method of predicting queries from passages and appending them to the index, and the BM25 gains it produces.

Any reference contrasting document expansion with query expansion and with dense retrieval — the framing of the vocabulary-mismatch problem and the two sides (query rewrite vs document rewrite) you can attack it from.

The companion "embed a hypothetical answer, not the question" (HyDE) and "prepend each chunk's document context before embedding" modules — HyDE is the query-side mirror of this technique, and contextual prefixing is the other document-side rewrite, so the three together cover both ends of the query-document gap.
