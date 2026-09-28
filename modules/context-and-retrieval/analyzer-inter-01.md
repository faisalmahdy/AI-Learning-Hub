---
id: analyzer-inter-01
title: Analyze the query with the same analyzer that built the index — a raw search for "Running" misses a document that literally contains the word
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A lexical index does not store raw text; it stores analyzed terms. An analyzer turns a document's text into a normalized token stream — it lowercases, splits on non-word characters, and often stems each token toward a root, so "Running", "runs", and "RUNNING" all collapse to one term at index time. The inverted index then maps each analyzed term to the documents that contain it, which is exactly what lets those spelling variants find the same passage. The catch is that the query must go through the identical analyzer, because the index contains only analyzed terms: search the index for the raw string "Running" and you find nothing, not because no document contains that word, but because the index stored the stemmed, lowercased form and "Running" is not it. The word is right there in the document's text, visible to any reader, and the search still misses it — nothing errors, the query just returns the wrong or empty result. This is the lexical counterpart of embedding the query and the corpus with one model version: the two sides must be processed the same way or they live in different spaces and cannot meet. A mismatched analyzer — an un-analyzed query, or one that lowercases but does not stem while the index does both — silently breaks matching for exactly the terms the normalization touched. On a fixture where "Running shoes for athletes" is indexed with the analyzed term "runn", a raw search for "Running" finds nothing while analyzing the query to "runn" finds the document.
eli5: Imagine a library where the librarian files every book by a shortened, all-lowercase version of its keywords — a book about "Running" gets filed under "runn". That's fine, and it's clever, because now books about "running", "runs", and "RUNNING" all end up in the same drawer. But here's the trap: when you come to the desk and ask for "Running" spelled exactly like that, the librarian looks in the "Running" drawer — and there is no such drawer, because everything was filed under "runn". So she says "we don't have it", even though the book is sitting right there in the "runn" drawer. The only way to find it is to shorten and lowercase your request the same way she shortened the books: ask for "runn" and out it comes. Whatever rule was used to file the books has to be the exact same rule used to look them up.
---

## Why this module

Keyword search feels like it should be literal: type a word, find the documents containing that word. But a real lexical index is not a substring scan over raw text — that would be far too slow at scale. It is an inverted index, a precomputed map from terms to documents, and the terms in that map are not the words as written. They have been passed through an analyzer that lowercases, tokenizes, and usually stems them into normalized forms.

That normalization is a feature, not an accident. It is precisely what makes keyword search useful: because "Running", "runs", and "RUNNING" all reduce to the same term, a search finds the passage regardless of which surface form the writer used. The index deliberately throws away case and inflection so that meaning-equivalent spellings collapse together. The price of that power is that the stored terms no longer look like the original words.

And that price comes due at query time. If the query is not put through the same analyzer, it arrives at the index in a form the index never stored. Searching for the raw word "Running" against an index that contains "runn" is like asking for a drawer that does not exist — the match fails silently, returning nothing or the wrong documents, even for a word that is plainly present in the corpus. This module builds the analyzed index and runs both a raw and an analyzed query to show the miss and the fix.

**A lexical index stores analyzed terms, not raw words — so the query must be analyzed the same way, or it searches for a form the index never stored and misses documents that contain the word.**

## Concepts

The governing principle is symmetry: whatever transformation is applied to the documents at index time must be applied to the query at search time, because matching happens in the transformed space, not the original one. Indexing and querying are two halves of one pipeline, and if the halves disagree on how to normalize text, terms that should be identical end up different and never meet.

This is the same principle as embedding-version consistency on the dense side of retrieval, and it is worth seeing them as one idea. There, both the corpus and the query must be embedded by the same model or their vectors are incomparable. Here, both must be analyzed by the same tokenizer and stemmer or their terms are incomparable. Dense or sparse, retrieval only works when the query is processed into the same representation as the corpus.

The failure is especially treacherous because it is invisible in two ways at once. The word is visibly present in the document's raw text, so a human reviewer is sure the match should succeed; and the search raises no error, it simply returns nothing. There is no exception to catch and no obviously wrong output — just a quietly empty or degraded result set for the exact terms the analyzer normalized, which are often the most important content words.

<svg role="img" aria-label="Two parallel paths into a shared term space: the document path is analyzed and stored, the query path must be analyzed the same way to land in the same space and meet" viewBox="0 0 440 140">
<rect x="20" y="20" width="90" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="37" fill="var(--ink)" font-size="9" text-anchor="middle">document</text>
<line x1="110" y1="33" x2="150" y2="33" stroke="var(--muted)"/>
<rect x="150" y="20" width="90" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="195" y="37" fill="var(--ink)" font-size="9" text-anchor="middle">analyzer</text>
<line x1="240" y1="33" x2="300" y2="55" stroke="var(--s1)"/>
<rect x="20" y="94" width="90" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="111" fill="var(--ink)" font-size="9" text-anchor="middle">query</text>
<line x1="110" y1="107" x2="150" y2="107" stroke="var(--muted)"/>
<rect x="150" y="94" width="90" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="195" y="111" fill="var(--ink)" font-size="9" text-anchor="middle">same analyzer</text>
<line x1="240" y1="107" x2="300" y2="85" stroke="var(--s1)"/>
<rect x="300" y="55" width="120" height="30" fill="var(--s1)" stroke="var(--line)"/>
<text x="360" y="74" fill="var(--ink)" font-size="10" text-anchor="middle">shared term space</text>
</svg>
^ Document and query reach the same term space only if both pass through the same analyzer; a different query analyzer lands somewhere they cannot meet.

**Indexing and querying are one pipeline that must agree on normalization; a query analyzer that differs from the index analyzer — dense or sparse — puts the two sides in different spaces, and the mismatch fails silently.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/analyzer-inter-01. The fixture is a tiny corpus and a query whose surface form differs from its analyzed form.

```json filename=modules/context-and-retrieval/code/analyzer-inter-01/analyzer.json:3-8 COMPLETE
  "docs": [
    {"id": "d1", "text": "Running shoes for athletes"},
    {"id": "d2", "text": "A cooking guide"},
    {"id": "d3", "text": "The runner trains daily"}
  ],
  "query": "Running"
```

The stemmer strips one trailing inflection — crude, but the point is that indexing and querying use the very same one.

```python filename=modules/context-and-retrieval/code/analyzer-inter-01/analyzer.py:33-38 COMPLETE
def stem(word):
    """A crude stemmer: strip one trailing 'ing', 'ed', or 's'."""
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[: -len(suffix)]
    return word
```

The analyzer lowercases, tokenizes on non-word characters, and stems each token.

```python filename=modules/context-and-retrieval/code/analyzer-inter-01/analyzer.py:41-43 COMPLETE
def analyze(text):
    """The analyzer: lowercase, split on non-word characters, stem each token."""
    return [stem(tok) for tok in re.split(r"\W+", text.lower()) if tok]
```

The raw search looks up the query string as-is, with no analysis — the bug.

```python filename=modules/context-and-retrieval/code/analyzer-inter-01/analyzer.py:51-53 COMPLETE
def raw_search(index, query):
    """Search the index for the query string as-is -- no analysis."""
    return [doc_id for doc_id, terms in index.items() if query in terms]
```

First, what the index actually stores. Run `--index`:

```text filename=analyzer.py --index
INDEX — analyzed terms stored per document
----------------------------------------------------------
  d1  'Running shoes for athletes' -> ['athlete', 'for', 'runn', 'shoe']
  d2  'A cooking guide'            -> ['a', 'cook', 'guide']
  d3  'The runner trains daily'    -> ['daily', 'runner', 'the', 'train']
----------------------------------------------------------
  the index stores stemmed, lowercased terms -- not the original words
```

Document d1's text says "Running", but the index stored "runn" — lowercased and stemmed. The original word is nowhere in the index; only its analyzed form is.

<svg role="img" aria-label="The document word Running passes through lowercase and stem steps and is stored in the index as the term runn, so the original spelling is not what the index holds" viewBox="0 0 440 110">
<rect x="20" y="40" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="59" fill="var(--ink)" font-size="11" text-anchor="middle">"Running"</text>
<text x="65" y="30" fill="var(--muted)" font-size="9" text-anchor="middle">doc word</text>
<line x1="110" y1="55" x2="150" y2="55" stroke="var(--muted)"/>
<rect x="150" y="40" width="80" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="190" y="59" fill="var(--ink)" font-size="10" text-anchor="middle">lowercase</text>
<line x1="230" y1="55" x2="260" y2="55" stroke="var(--muted)"/>
<rect x="260" y="40" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="290" y="59" fill="var(--ink)" font-size="10" text-anchor="middle">stem</text>
<line x1="320" y1="55" x2="350" y2="55" stroke="var(--muted)"/>
<rect x="350" y="40" width="70" height="30" fill="var(--s1)" stroke="var(--line)"/>
<text x="385" y="59" fill="var(--ink)" font-size="11" text-anchor="middle">"runn"</text>
<text x="385" y="30" fill="var(--muted)" font-size="9" text-anchor="middle">index term</text>
</svg>
^ The index stores the analyzed term "runn", not the original "Running" — so a lookup must use the analyzed form.

Now the two searches. Predict: the raw query "Running" misses, the analyzed query "runn" hits d1. Run `--search`:

```text filename=analyzer.py --search
SEARCH — raw query vs analyzed query for 'Running'
----------------------------------------------------------
  analyze('Running') = ['runn']
  raw search      (looks up 'Running')        -> []
  analyzed search (looks up ['runn']) -> ['d1']
----------------------------------------------------------
  the raw query misses a document whose text contains the word
```

The prediction holds. The raw query returns nothing — "Running" is not a stored term — even though d1's text literally reads "Running shoes". Analyzing the query to "runn" first, the same way the index was built, finds d1. The only difference between a miss and a hit was whether the query went through the same analyzer.

<svg role="img" aria-label="The raw query Running searches the index and finds nothing; the same query analyzed to runn searches the index and finds document d1" viewBox="0 0 440 140">
<text x="110" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">raw query</text>
<rect x="60" y="30" width="100" height="26" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="47" fill="var(--ink)" font-size="10" text-anchor="middle">"Running"</text>
<line x1="110" y1="56" x2="110" y2="82" stroke="var(--muted)"/>
<rect x="60" y="84" width="100" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="101" fill="var(--s2)" font-size="10" text-anchor="middle">no match</text>
<text x="330" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">analyzed query</text>
<rect x="280" y="30" width="100" height="26" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="47" fill="var(--ink)" font-size="10" text-anchor="middle">"runn"</text>
<line x1="330" y1="56" x2="330" y2="82" stroke="var(--muted)"/>
<rect x="280" y="84" width="100" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="101" fill="var(--s1)" font-size="10" text-anchor="middle">d1 found</text>
</svg>
^ Same query, same index — analyzing the query the way the index was built turns an empty result into a hit.

## Build

The self-test plants the failure and names each claim as a boolean flag. It confirms the index stored the analyzed form and not the raw word, that the raw word is nonetheless present in the document's text, that the raw search finds nothing while the analyzed search finds the document, and that matching the query analyzer to the index is what is required.

```python filename=modules/context-and-retrieval/code/analyzer-inter-01/analyzer.py:103-110 COMPLETE
    raw_finds_nothing = raw_hits == []
    print("  raw (un-analyzed) query finds nothing = %s (%s)" % (raw_finds_nothing, raw_hits))

    analyzed_hits = analyzed_search(index, q)
    analyzed_finds_it = docs[0]["id"] in analyzed_hits
    print("  analyzed query finds the document = %s (%s)" % (analyzed_finds_it, analyzed_hits))

    parity_required = len(raw_hits) < len(analyzed_hits)
    print("  matching the query analyzer to the index is required = %s" % parity_required)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the raw query ever starts matching or the analyzed one ever stops:

```text filename=analyzer.py --check
SELF-TEST — the index stores analyzed terms, so a raw query misses a word it contains; analyzing the query matches
--------------------------------------------------------------------------------------------------------------------
  index stores 'runn' not 'Running' for the first doc = True
  the raw query word appears verbatim in that doc's text = True
  raw (un-analyzed) query finds nothing = True ([])
  analyzed query finds the document = True (['d1'])
  matching the query analyzer to the index is required = True
--------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  index_stores_analyzed=True  word_literally_in_doc=True  raw_finds_nothing=True  analyzed_finds_it=True  parity_required=True
```

**The self-test pins the surprise — the word is verbatim in the document yet the raw query returns nothing — so it proves the miss is the analyzer mismatch, not an absent word.**

## Definition of done

You can explain why a lexical index stores analyzed terms rather than raw words, and what that normalization buys.
You can state the symmetry rule: the query must be analyzed with the same lowercasing, tokenizing, and stemming as the index.
You can connect this to embedding-version consistency — same principle, sparse side versus dense side.
You can describe why the failure is doubly invisible: the word is present in the raw text, and the search raises no error.
You can name a partial mismatch that still breaks — a query analyzer that lowercases but does not stem while the index does both — and predict which terms it breaks.

## Boss fight

Make the mismatch partial instead of total: analyze the query but with a different stemmer — say, one that lowercases but does not strip suffixes. The query "Running" becomes "running", the index still holds "runn", and the search misses again. This is subtler than the raw-query bug because the query is being analyzed; it is just analyzed differently. The lesson tightens: parity is not "run some analyzer on the query", it is "run the same analyzer". Any divergence in a normalization step breaks exactly the terms that step touches, and case-only analysis leaves every stemmed term unmatched.

Now go the other way and consider a word the analyzer does not change. Search for "guide" against d2, whose index term is also "guide" — here the raw query and the analyzed query agree, because the analyzer left the word alone, so even the buggy raw search happens to work. That is why the bug hides in testing: queries for already-normalized words (lowercase, uninflected) match fine, and only queries for words the analyzer transforms fail. A test suite full of simple lowercase keywords would pass while real user queries with capitals and plurals silently miss.

**Parity means the same analyzer, not merely some analyzer — a query normalized differently still misses, and because already-normalized words match either way, the bug passes shallow tests and fails on real capitalized, inflected queries.**

## External resources

Elasticsearch's documentation on the analysis chain and "index-time vs search-time analysis" is the canonical treatment of why the query and index analyzers must correspond.
The Lucene documentation on Analyzer and its token filters explains the lowercasing and stemming stages that make stored terms differ from raw words.
The topic's own module on embedding-version consistency covers the same symmetry requirement on the dense-retrieval side — one representation for both corpus and query.
