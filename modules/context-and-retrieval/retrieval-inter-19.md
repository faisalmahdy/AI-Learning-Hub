---
id: retrieval-inter-19
title: Weight matched terms by IDF — or a document matching only common words beats the one that answers the query
topic: context-and-retrieval
level: intermediate
status: ready
time: 19 min
summary: A lexical scorer decides how well a document matches a query. The naive rule counts matched query terms — more hits, higher score — which treats every word as equally informative. It is not. In "how does backpropagation work," the words how, does, and work appear in most documents and say almost nothing about relevance; backpropagation appears in a handful and says almost everything. A document containing how, does, and work but never backpropagation scores three matched terms; the document actually about backpropagation scores one, and the count ranks the off-topic one first. Inverse document frequency fixes it — weight each matched term by IDF = log(n_docs/df), so a term in nearly every document weighs near zero and a rare term weighs a lot. On a 1000-doc corpus the common terms have IDF ≈ 0.2–0.5 while backpropagation (df 5) has IDF 5.3, so the rare-term document wins 5.3 to 0.9.
eli5: If you are looking for a book about dragons, the words "the" and "and" being present tells you nothing — every book has them. The word "dragon" tells you everything. A search that just counts how many of your words appear would rank a boring book that happens to share "the," "does," and "work" above the one book that actually says "dragon." Weighting rare words heavily fixes that, because the rare word is the one that carries the meaning.
---

## Why this module

Counting how many query words a document contains is the obvious relevance score, and it hands the top rank to documents that share only the meaningless words.

A query is a bag of words, some carrying the meaning and most carrying none. "how does backpropagation work" has one word that matters — backpropagation — and three that appear in nearly every document in the corpus. A scorer that counts matched terms gives a document three points for containing how, does, and work, even if that document is about baking bread and never mentions backpropagation. The document that actually answers the query, which contains backpropagation but phrases the rest differently, gets one point. Count wins, and the wrong document is ranked first — not because it is more relevant, but because it shares more of the filler.

**Counting matched terms treats a stopword and a keyword as equally informative, so a document can win on filler alone.**

Inverse document frequency corrects this by weighting each term by how rare it is across the corpus. A word in almost every document earns almost nothing for matching; a rare word earns a lot. The single keyword match then outweighs the three filler matches, and the right document rises. This module scores two documents both ways and shows the ranking flip.

## Concepts

The **document frequency** (df) of a term is how many documents in the corpus contain it. Common words have high df; rare, specific words have low df.

**Inverse document frequency** is IDF = log(n_docs / df). When a term is in nearly every document, df ≈ n_docs, so the ratio is ≈ 1 and its log is ≈ 0 — matching it counts for almost nothing. When a term is rare, df is small, the ratio is large, and its IDF is large — matching it counts for a lot. The logarithm keeps the weight from exploding for extremely rare terms.

The **count score** is just the number of matched query terms — every match worth 1. The **IDF score** sums the IDF of the matched terms — every match worth its rarity.

The mechanism of the fix is that IDF is a per-term informativeness weight derived from the corpus, not the query. It encodes the intuition that a word tells you more the more surprising it is to see — matching a word that appears everywhere is unsurprising and uninformative, matching a rare word is surprising and highly informative.

**IDF turns "how many words matched" into "how much information did the matches carry," which is the question relevance actually asks.**

IDF is a curve, not a switch: as a term's document frequency climbs toward the whole corpus, its weight slides smoothly to zero.

<svg role="img" aria-label="IDF weight as a function of document frequency: high for rare terms, decaying to zero as df approaches the corpus size" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="8" y="24" fill="var(--muted)" font-size="8">IDF</text>
  <text x="255" y="108" fill="var(--muted)" font-size="8">df → n</text>
  <text x="30" y="108" fill="var(--muted)" font-size="8">rare</text>
  <path d="M40,20 Q70,70 130,84 T285,93" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="46" cy="24" r="2.5" fill="var(--s1)"/><text x="50" y="24" fill="var(--s1)" font-size="7">backprop (df 5)</text>
  <circle cx="235" cy="92" r="2.5" fill="var(--s2)"/><text x="180" y="88" fill="var(--s2)" font-size="7">how/does (df 800+)</text>
</svg>
^ The weight decays continuously with document frequency — the rare term sits high on the curve, the filler words near the floor, with everything in between graded rather than cut off.

This is the other half of TF-IDF and BM25: term frequency captures how much a document is about a term, IDF captures how much that term distinguishes documents at all. Without IDF, the most common words dominate the score, which is exactly backwards.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/retrieval-inter-19/idf.py

The fixture is a corpus size, a query, each term's document frequency, and the two documents' matched terms.

```json filename=modules/context-and-retrieval/code/retrieval-inter-19/idf.json:1-9 COMPLETE
{
  "_meta": "A lexical match over a corpus of n_docs documents. The query is a list of terms; df is each term's document frequency (how many of the n_docs documents contain it), so a common word has high df and a rare word has low df. IDF = log(n_docs / df) downweights common terms. Two candidate documents each match a different subset of the query terms; the question is which one a scorer ranks first.",
  "n_docs": 1000,
  "query": ["how", "does", "backpropagation", "work"],
  "df": {"how": 800, "does": 850, "backpropagation": 5, "work": 600},
  "doc_common": ["how", "does", "work"],
  "doc_rare": ["backpropagation"]
}
```

IDF is one line; the two scorers differ only in the weight per match — 1 each for count, the term's IDF for the weighted score.

```python filename=modules/context-and-retrieval/code/retrieval-inter-19/idf.py:41-53 COMPLETE
def idf(term, df, n_docs):
    """Inverse document frequency: log(n_docs / df). Near 0 for common terms, large for rare ones."""
    return math.log(n_docs / df[term])


def count_score(matched):
    """Naive score: how many query terms the document matched."""
    return float(len(matched))


def idf_score(matched, df, n_docs):
    """IDF-weighted score: sum of the matched terms' IDF weights."""
    return sum(idf(t, df, n_docs) for t in matched)
```

Run `--idf` and read each term's weight.

```text filename=--idf
IDF — document frequency and weight per query term (corpus 1000 docs)
------------------------------------------------------------
  term             df     IDF=log(n/df)
  how              800     0.223
  does             850     0.163
  backpropagation    5     5.298
  work             600     0.511
------------------------------------------------------------
  common terms weigh near zero; the rare term weighs an order more.
```

The three common terms weigh between 0.16 and 0.51 — matching all three is barely worth half a point of one rare match. backpropagation, in only 5 of 1000 documents, weighs 5.30, more than ten times any common term. The corpus statistics alone, with no knowledge of meaning, recover that backpropagation is the word that matters.

<svg role="img" aria-label="IDF weights: how 0.22, does 0.16, work 0.51 are tiny bars while backpropagation 5.30 is a bar ten times longer" viewBox="0 0 300 130" width="300" height="130">
  <line x1="110" y1="12" x2="110" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="110" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <rect x="110" y="20" width="7" height="14" fill="var(--s2)"/><text x="10" y="31" fill="var(--muted)" font-size="8">how 0.22</text>
  <rect x="110" y="40" width="5" height="14" fill="var(--s2)"/><text x="10" y="51" fill="var(--muted)" font-size="8">does 0.16</text>
  <rect x="110" y="60" width="168" height="14" fill="var(--s1)"/><text x="10" y="71" fill="var(--muted)" font-size="8">backprop 5.30</text>
  <rect x="110" y="80" width="16" height="14" fill="var(--s2)"/><text x="10" y="91" fill="var(--muted)" font-size="8">work 0.51</text>
  <text x="130" y="122" fill="var(--muted)" font-size="8">one rare term dwarfs all the common ones combined</text>
</svg>
^ The rare term's IDF bar dwarfs the three common terms put together — matching it carries more than ten times the information of matching any filler word.

## Build

The score view tallies each document under both rules and prints the count next to the IDF sum.

```python filename=modules/context-and-retrieval/code/retrieval-inter-19/idf.py:69-78 COMPLETE
def score_view(data):
    n, df = data["n_docs"], data["df"]
    a, b = data["doc_common"], data["doc_rare"]
    print("SCORE — term-count vs IDF-sum for each document")
    print("-" * 60)
    print("  doc            matched                     count   IDF-sum")
    print("  common-word    %-26s %5.0f   %6.3f" % (",".join(a), count_score(a), idf_score(a, df, n)))
    print("  rare-word      %-26s %5.0f   %6.3f" % (",".join(b), count_score(b), idf_score(b, df, n)))
    print("-" * 60)
    print("  count ranks the common-word doc first; IDF ranks the rare-word doc first.")
```

Now score the two documents with `--score`.

```text filename=--score
SCORE — term-count vs IDF-sum for each document
------------------------------------------------------------
  doc            matched                     count   IDF-sum
  common-word    how,does,work                  3    0.896
  rare-word      backpropagation                1    5.298
------------------------------------------------------------
  count ranks the common-word doc first; IDF ranks the rare-word doc first.
```

By count, the common-word document wins 3 to 1 — it matched more query terms, so a term-counting retriever puts it on top and buries the document about backpropagation. By IDF sum, the rare-word document wins 5.30 to 0.90 — its single meaningful match outweighs all three filler matches combined. The ranking reverses entirely, and the IDF ranking is the correct one.

<svg role="img" aria-label="Ranking reverses: by count the common-word doc leads 3 to 1, by IDF the rare-word doc leads 5.3 to 0.9" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="16" fill="var(--muted)" font-size="8">by count</text>
  <rect x="70" y="10" width="90" height="14" fill="var(--s1)"/><text x="163" y="21" fill="var(--muted)" font-size="8">common 3</text>
  <rect x="70" y="28" width="30" height="14" fill="var(--s2)"/><text x="103" y="39" fill="var(--muted)" font-size="8">rare 1</text>
  <text x="10" y="70" fill="var(--muted)" font-size="8">by IDF</text>
  <rect x="70" y="64" width="16" height="14" fill="var(--s1)"/><text x="89" y="75" fill="var(--muted)" font-size="8">common 0.9</text>
  <rect x="70" y="82" width="95" height="14" fill="var(--s2)"/><text x="168" y="93" fill="var(--muted)" font-size="8">rare 5.3</text>
  <text x="30" y="118" fill="var(--muted)" font-size="8">the winner flips: count picks filler, IDF picks the keyword</text>
</svg>
^ The two rules pick opposite winners — count crowns the document that shares the most filler, IDF crowns the one that shares the keyword.

## Definition of done

The self-test pins the reversal: count ranks the common-word document first, IDF ranks the rare-word one first, so the rankings reverse; one rare match outweighs all three common matches; and IDF equals log(n/df) for every term.

```python filename=modules/context-and-retrieval/code/retrieval-inter-19/idf.py:87-99 COMPLETE
    count_ranks_common_first = count_score(a) > count_score(b)
    print("  term-count ranks the common-word doc first = %s (%.0f > %.0f)" % (count_ranks_common_first, count_score(a), count_score(b)))

    idf_ranks_rare_first = idf_score(b, df, n) > idf_score(a, df, n)
    print("  IDF ranks the rare-word doc first = %s (%.3f > %.3f)" % (idf_ranks_rare_first, idf_score(b, df, n), idf_score(a, df, n)))

    ranking_reverses = count_ranks_common_first and idf_ranks_rare_first
    print("  the two rules pick opposite winners = %s" % ranking_reverses)

    rare_outweighs_all_common = idf("backpropagation", df, n) > idf_score(a, df, n)
    print("  one rare match outweighs all three common matches = %s (%.3f > %.3f)" % (rare_outweighs_all_common, idf("backpropagation", df, n), idf_score(a, df, n)))

    idf_is_log_n_over_df = all(abs(idf(t, df, n) - math.log(n / df[t])) < 1e-12 for t in data["query"])
    print("  IDF equals log(n_docs/df) for every term = %s" % idf_is_log_n_over_df)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — term-count ranks the off-topic document first; IDF ranks the on-topic one first
----------------------------------------------------------------------------------------------------
  term-count ranks the common-word doc first = True (3 > 1)
  IDF ranks the rare-word doc first = True (5.298 > 0.896)
  the two rules pick opposite winners = True
  one rare match outweighs all three common matches = True (5.298 > 0.896)
  IDF equals log(n_docs/df) for every term = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  count_ranks_common_first=True  idf_ranks_rare_first=True  ranking_reverses=True  rare_outweighs_all_common=True  idf_is_log_n_over_df=True
```

**Done means the flip is derived from the corpus stats, not asserted: the count 3 > 1 and the IDF sum 5.30 > 0.90 point opposite ways, and the single rare term's 5.30 exceeds the common trio's 0.90.**

## Boss fight

IDF fixed the ranking by downweighting common terms. Predict what a pure stopword list — just deleting how, does, and work before matching — would do instead, and whether it is equivalent. It is tempting to think dropping stopwords is the same fix.

It is a cruder version that fails at the boundary. A fixed stopword list is a hard cutoff: a word is either a stopword (weight 0) or not (weight 1), with nothing in between. IDF is continuous — work gets 0.51, more than how's 0.22, because it is somewhat less common, and a moderately rare technical term gets a moderate weight. A stopword list also cannot adapt to the corpus: "cell" is a stopword in a biology corpus and a keyword in a prison-reform corpus, and only IDF, computed from the actual documents, captures that. Stopword removal is IDF with a threshold and no gradations; IDF subsumes it.

The mirror-image mistake is using IDF without term frequency. IDF alone says a rare term is valuable to match, but not how much a given document is about it — a document mentioning backpropagation once and one discussing it throughout both score the same rare match. That is why real scorers multiply IDF by term frequency (TF-IDF) or its saturated form (BM25): IDF weights which terms matter, TF weights how much each document engages them. This module isolates the IDF half; the TF half is its partner.

```python filename=modules/context-and-retrieval/code/retrieval-inter-19/idf.py:41-43 COMPLETE
def idf(term, df, n_docs):
    """Inverse document frequency: log(n_docs / df). Near 0 for common terms, large for rare ones."""
    return math.log(n_docs / df[term])
```

**Weight each matched term by IDF = log(n_docs/df) so relevance follows information, not word count — a continuous, corpus-derived weight that subsumes stopword removal and pairs with term frequency to make TF-IDF.**

## External resources

Spärck Jones, "A Statistical Interpretation of Term Specificity and Its Application in Retrieval" (1972) — the paper that introduced IDF and the argument that term weight should track rarity.

Manning, Raghavan, and Schütze, "Introduction to Information Retrieval," the TF-IDF chapter — how IDF combines with term frequency, the variants of the IDF formula, and why the log is there.

The Elasticsearch/Lucene similarity documentation — IDF as it appears inside BM25 in a production search engine, alongside the term-frequency saturation of the companion module.
