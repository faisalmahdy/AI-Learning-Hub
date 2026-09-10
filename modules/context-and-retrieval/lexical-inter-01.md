---
id: lexical-inter-01
title: Match rare exact tokens with lexical (BM25) scoring, not dense embeddings alone — an error code barely moves an embedding, so dense retrieval can rank the wrong document first
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Dense retrieval embeds the query and every document into a vector space and ranks by semantic similarity, which is excellent for meaning but has a specific blind spot — a rare exact token like an error code, a SKU, a function name, or an ID contributes almost nothing to a document's embedding, because the embedding is a smear of overall meaning and one rare token barely moves it. So a document that literally contains the token the user typed can rank below a document that is only semantically similar and does not contain it: the user asks for error E4501 and gets a page about resetting passwords, because "reset" was in the query and dense similarity rewarded the topical overlap. Lexical retrieval scores the opposite way — it counts which query terms each document actually contains, weighted by inverse document frequency (IDF), so a term appearing in only one of N documents is worth far more than one appearing in all of them. This is the core of BM25, and the rare exact token, precisely because it is rare, gets a high IDF weight that shoots the one document containing it to the top. Lexical matching cannot understand meaning, but it never fumbles an exact token, which is exactly where dense retrieval is weakest, so the two fail on opposite inputs and production retrieval hybridizes them. On a fixture where the query is "reset error E4501", dense retrieval ranks d1 ("reset password", similarity 0.8) first even though it has no E4501, while lexical retrieval weights the rare E4501 by its high IDF and ranks d2 ("error E4501 login") first — the document the user actually wanted.
eli5: Imagine you ask a librarian for the book that mentions the exact code "E4501". One librarian goes by vibes — she brings you books that feel related to your question, and since you also said the word "reset", she hands you a book about resetting passwords that never mentions E4501 at all. The other librarian goes by the words on the page — she knows "E4501" is a weird, rare code that shows up in almost no books, so the one book that actually contains it jumps out at her, and that's the one she brings. The vibes librarian is great when you want books "about" a topic, but for a rare exact code you want the one who reads the actual words. The best library has both, and asks each of them.
---

## Why this module

Almost every retrieval system today embeds the query and the documents into vectors and ranks by cosine similarity. This is dense retrieval, and it earns its place: it finds documents that mean the same thing even when they share no words, matching "car won't start" to a passage about "dead batteries". But that strength is built on compression — the embedding folds a whole document down to a few hundred numbers that capture its overall meaning — and compression has a cost. A rare exact token barely survives it.

Think about what an error code like E4501 contributes to a document's embedding. The embedding is dominated by the document's topic, its common words, its general shape. One rare string that the embedding model may never have seen enough to place precisely moves the vector by almost nothing. So two documents can have very similar embeddings while only one of them contains the exact code the user needs — and dense similarity, blind to the literal token, may rank the one without it first. The user typed a precise identifier and the retriever answered with something that is merely on-topic.

This is not a rare corner case. Queries with exact tokens are everywhere: error codes, part numbers, API names, legal citations, ticket IDs, people's names. This module runs one such query through both a dense and a lexical scorer and watches them disagree on the top result.

**A rare exact token barely moves a document's embedding, so dense similarity can rank a semantically-close document that lacks the token above the document that actually contains it — which is why exact-match queries need lexical (BM25) scoring, or a dense+lexical hybrid, not dense embeddings alone.**

## Concepts

The fixture is a query and three documents. The query carries three terms; one of them, the error code E4501, is the rare exact token the user most needs matched. Each document lists the words it contains (for lexical matching) and a precomputed dense similarity to the query.

```json filename=modules/context-and-retrieval/code/lexical-inter-01/lexical.json:3-9 COMPLETE
  "query_terms": ["reset", "error", "E4501"],
  "rare_term": "E4501",
  "documents": [
    {"id": "d1", "terms": ["reset", "password"], "dense_sim": 0.8},
    {"id": "d2", "terms": ["error", "E4501", "login"], "dense_sim": 0.5},
    {"id": "d3", "terms": ["error", "codes", "fixes"], "dense_sim": 0.6}
  ]
```

Read the tension straight from the numbers. Document d1 has the highest dense similarity (0.8) because it shares the common word "reset" with the query and is topically close — but it does not contain E4501. Document d2 is the one the user wants: it holds the exact code, plus "error". Yet its dense similarity is only 0.5. Dense retrieval, ranking by that column, will put d1 on top and the exact-match document second.

Lexical scoring weights each query term by how rare it is. The measure is inverse document frequency: a term's document frequency (df) is how many documents contain it, and its IDF is the log of the total document count over that df. A term in every document has an IDF near zero; a term in one document out of three has a high IDF.

```python filename=modules/context-and-retrieval/code/lexical-inter-01/lexical.py:33-40 COMPLETE
def document_frequency(term, documents):
    return sum(1 for d in documents if term in d["terms"])


def idf(term, documents):
    n = len(documents)
    df = document_frequency(term, documents)
    return math.log(n / df) if df else 0.0
```

A document's lexical score is the sum of the IDF weights of the query terms it contains — a simplified BM25. The rare token, with its high IDF, dominates that sum for any document lucky enough to contain it. Ranking is just sorting by score, high to low.

```python filename=modules/context-and-retrieval/code/lexical-inter-01/lexical.py:43-48 COMPLETE
def lexical_score(doc, query_terms, documents):
    return sum(idf(t, documents) for t in query_terms if t in doc["terms"])


def rank_by(pairs):
    return sorted(pairs, key=lambda kv: kv[1], reverse=True)
```

**Lexical scoring weights a query term by its rarity (IDF), so a rare exact token — worth little to an embedding — becomes the dominant signal, and the one document containing it rises to the top.**

<svg role="img" aria-label="A rare token E4501 is a large slice of a lexical score but a tiny wedge of a dense embedding, illustrating that lexical scoring weights it heavily while the embedding smears it away" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">what the rare token E4501 contributes to each score</text>
  <text x="16" y="40" font-size="8" fill="var(--s1)">lexical (IDF-weighted)</text>
  <rect x="16" y="46" width="180" height="16" fill="none" stroke="var(--line)"/>
  <rect x="16" y="46" width="132" height="16" fill="var(--s1)"/>
  <text x="60" y="58" font-size="7.5" fill="var(--panel)">E4501 (high IDF)</text>
  <text x="152" y="58" font-size="7" fill="var(--muted)">error</text>
  <text x="16" y="88" font-size="8" fill="var(--s2)">dense (embedding)</text>
  <rect x="16" y="94" width="180" height="16" fill="none" stroke="var(--line)"/>
  <rect x="16" y="94" width="10" height="16" fill="var(--s2)"/>
  <text x="30" y="106" font-size="7.5" fill="var(--ink)">E4501 barely moves the vector — topic dominates</text>
</svg>
^ The same rare token is weighted almost oppositely by the two scorers: it is the largest slice of the lexical score (high IDF) but a sliver of the dense embedding, which is dominated by overall topic. That gap is the whole failure mode.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the ranking step of a retrieval pipeline, reduced to one query and three documents so every score is checkable by hand.

Run `--idf` to see how rare each query term is.

```text filename=lexical.py --idf
  reset    df=1/3   idf=1.099
  error    df=2/3   idf=0.405
  E4501    df=1/3   idf=1.099  <- rare exact token
```

The term "error" appears in two of the three documents, so its IDF is low (0.405) — matching it says little, because it is almost everywhere. The rare token E4501 appears in one document, so its IDF is high (1.099): matching it is a strong signal, because only one document could have supplied it. "reset" is also in one document here, giving it the same IDF, but E4501 is the token the query hinges on.

Now `--rank` scores every document both ways.

```text filename=lexical.py --rank
  doc  lexical  dense  has E4501
  d1    1.099   0.80  no
  d2    1.504   0.50  yes
  d3    0.405   0.60  no
```

The two columns disagree on the winner. By dense similarity the order is d1 (0.80), d3 (0.60), d2 (0.50) — the exact-match document is last. By lexical score the order is d2 (1.504), d1 (1.099), d3 (0.405) — d2 wins because it collects both "error" (0.405) and the high-IDF E4501 (1.099), summing to 1.504. Dense retrieval hands back d1, a document about resetting passwords with no E4501 in it; lexical retrieval hands back d2, the document the user came for.

<svg role="img" aria-label="Two ranked lists side by side: dense ranks d1 first (no E4501), lexical ranks d2 first (contains E4501), disagreeing on the top document" viewBox="0 0 320 140">
  <text x="14" y="16" font-size="8.5" fill="var(--s2)">dense ranking</text>
  <text x="180" y="16" font-size="8.5" fill="var(--s1)">lexical ranking</text>
  <g font-size="7.5">
  <rect x="14" y="24" width="120" height="15" fill="var(--s2)"/><text x="20" y="35" fill="var(--panel)">1. d1  0.80  (no E4501)</text>
  <rect x="14" y="42" width="120" height="15" fill="none" stroke="var(--line)"/><text x="20" y="53" fill="var(--muted)">2. d3  0.60</text>
  <rect x="14" y="60" width="120" height="15" fill="none" stroke="var(--line)"/><text x="20" y="71" fill="var(--ink)">3. d2  0.50  (E4501!)</text>
  <rect x="180" y="24" width="126" height="15" fill="var(--s1)"/><text x="186" y="35" fill="var(--panel)">1. d2  1.504 (E4501!)</text>
  <rect x="180" y="42" width="126" height="15" fill="none" stroke="var(--line)"/><text x="186" y="53" fill="var(--muted)">2. d1  1.099</text>
  <rect x="180" y="60" width="126" height="15" fill="none" stroke="var(--line)"/><text x="186" y="71" fill="var(--muted)">3. d3  0.405</text>
  </g>
  <text x="14" y="98" font-size="8" fill="var(--ink)">the exact-match document d2 is last by dense, first by lexical</text>
  <text x="14" y="118" font-size="7.5" fill="var(--muted)">dense rewards topical overlap ("reset"); lexical rewards the rare exact token</text>
</svg>
^ Dense retrieval ranks the exact-match document d2 dead last because its embedding is only semantically middling; lexical retrieval ranks it first because the rare E4501 dominates the IDF-weighted score. Same query, same documents, opposite winners.

**On this query the two scorers invert the exact-match document — dense puts d2 last, lexical puts it first — because dense reads topic and lexical reads the literal rare token.**

## Build

The self-test asserts the setup and the failure: the query really carries a rare token, that token really has the highest IDF, and then the two scorers really disagree in the way that matters. The first two clauses establish the premise.

```python filename=modules/context-and-retrieval/code/lexical-inter-01/lexical.py:94-99 COMPLETE
    query_has_rare_term = rare in query_terms
    print("  the query carries the rare exact token '%s' = %s" % (rare, query_has_rare_term))

    rare_term_high_idf = idf(rare, documents) == max(idf(t, documents) for t in query_terms)
    print("  the rare token has the highest idf of any query term = %s (idf=%.3f, df=%d/%d)"
          % (rare_term_high_idf, idf(rare, documents), document_frequency(rare, documents), n))
```

The payload clauses compare the two top documents. Dense retrieval's winner must lack the token; lexical retrieval's winner must contain it; and the two must disagree — if they agreed, there would be no failure to fix.

```python filename=modules/context-and-retrieval/code/lexical-inter-01/lexical.py:101-109 COMPLETE
    dense_top, lex_top = dense_ranked[0][0], lex_ranked[0][0]
    dense_misses_exact = not has[dense_top]
    print("  dense retrieval's top doc %s does NOT contain the token = %s" % (dense_top, dense_misses_exact))

    lexical_finds_exact = has[lex_top]
    print("  lexical retrieval's top doc %s DOES contain the token = %s" % (lex_top, lexical_finds_exact))

    rankings_disagree = dense_top != lex_top
    print("  dense and lexical disagree on the top document = %s (dense %s, lexical %s)" % (rankings_disagree, dense_top, lex_top))
```

Running the check confirms every clause.

```text filename=lexical.py --check
  the query carries the rare exact token 'E4501' = True
  the rare token has the highest idf of any query term = True (idf=1.099, df=1/3)
  dense retrieval's top doc d1 does NOT contain the token = True
  lexical retrieval's top doc d2 DOES contain the token = True
  dense and lexical disagree on the top document = True (dense d1, lexical d2)
  SELF-TEST PASS  query_has_rare_term=True  rare_term_high_idf=True  dense_misses_exact=True  lexical_finds_exact=True  rankings_disagree=True
```

**The check pins the failure to a precise, reproducible fact: dense retrieval's top document does not contain the exact token the query hinges on, and lexical retrieval's does — the two rankings disagree exactly on the document that matters.**

## Definition of done

Done means the two scorers disagree in the diagnostic direction: the dense winner lacks the rare token, the lexical winner has it. The `rare_term_high_idf` clause is what makes this a fair test rather than a rigged one — it proves the token is genuinely rare in this corpus, so lexical scoring's advantage comes from the token's rarity and not from some accident of the fixture.

The fix in production is not to throw dense retrieval away — it is still the only thing that matches meaning across different words — but to run both and combine them. A hybrid retriever computes a dense score and a lexical (BM25) score for each document and fuses them, so a document wins if it is either strongly on-topic or a strong exact match. On this fixture a hybrid would surface d2 for the exact code and still keep d1 available for its topical relevance, getting both kinds of relevance instead of trading one for the other.

<svg role="img" aria-label="A Venn-style diagram: dense retrieval covers semantic matches, lexical covers exact-token matches, and hybrid is the union covering both" viewBox="0 0 320 130">
  <circle cx="120" cy="65" r="46" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="46" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="70" y="40" font-size="8" fill="var(--s2)">dense</text>
  <text x="200" y="40" font-size="8" fill="var(--s1)">lexical</text>
  <text x="78" y="68" font-size="7" fill="var(--ink)">semantic</text>
  <text x="80" y="80" font-size="7" fill="var(--ink)">("reset")</text>
  <text x="200" y="68" font-size="7" fill="var(--ink)">exact token</text>
  <text x="204" y="80" font-size="7" fill="var(--ink)">(E4501)</text>
  <text x="138" y="66" font-size="7" fill="var(--muted)">both</text>
  <text x="60" y="120" font-size="7.5" fill="var(--muted)">hybrid = union: semantic recall AND exact-match precision</text>
</svg>
^ Dense and lexical retrieval cover different kinds of relevance — meaning versus literal token. Hybrid retrieval is their union, keeping semantic recall while regaining the exact-match precision that dense alone gives up.

A caveat on scope: lexical scoring is not universally better. On a query with no rare exact tokens — "how do I make my code faster" — dense retrieval usually wins, because there is nothing exact to match and everything to understand. The rule is targeted: reach for lexical or hybrid scoring specifically when the query carries a token that must match literally, which is precisely the input where dense embeddings are weakest.

**Done means the dense top document lacks the rare token and the lexical top document holds it, with the token proven rare (high IDF) — and the production answer is hybrid: fuse dense and lexical so exact-match queries stop losing to merely-topical documents.**

## Boss fight

A support-search feature over a knowledge base uses a pure vector (dense) retriever. It works well for natural-language questions like "my login keeps timing out", but users complain that searching for a specific error code — "E4501" — returns generic troubleshooting pages and not the one article that documents that exact code. Adding more documents did not help. What is happening, and how would you fix it?

It is the dense blind spot for rare exact tokens. The error code E4501 contributes almost nothing to any document's embedding — the embedding is dominated by the surrounding prose about errors and logins — so the article that literally documents E4501 has an embedding only middlingly similar to the query, while a general "troubleshooting login errors" page, rich in the common words, scores higher. Dense similarity ranks the generic page first and the exact-match article below it, or off the top-k entirely. Adding documents does not help and can hurt: it adds more topically-similar pages competing for the top slots, none of which contain the code. The fix is to stop relying on dense retrieval alone for these queries. Add a lexical (BM25) index alongside the vector index and fuse the two scores into a hybrid ranking, so a document that contains the exact code gets a large IDF-weighted boost — E4501 is rare across the corpus, so matching it is a strong signal — and surfaces above the generic pages, while natural-language queries still benefit from dense semantic matching. If a full hybrid is too much to build immediately, the interim step is to detect queries that contain rare exact tokens (an ID, a code, a quoted phrase) and route those to a keyword search, reserving pure dense retrieval for the natural-language ones. The principle: an exact token is a precision requirement, and precision on literal strings is what lexical scoring does and dense embeddings do not.

## External resources

The BM25 ranking function and its use in engines like Elasticsearch, OpenSearch, and Lucene — the IDF-weighted term scoring this module simplifies, including the term-frequency saturation and length-normalization real BM25 adds on top of the plain IDF sum shown here.

Documentation and papers on hybrid retrieval and score fusion (dense + sparse, reciprocal-rank fusion, and the "sparse-dense" hybrid indexes in vector databases like Pinecone, Weaviate, and Qdrant) — the production pattern for combining semantic recall with exact-match precision, and the evidence that hybrid beats either retriever alone on mixed query workloads.
