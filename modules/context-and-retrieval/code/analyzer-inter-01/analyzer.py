"""Analyze the query with the same analyzer that built the index -- a lexical search stores lowercased, stemmed terms, so searching for the raw word 'Running' misses a document that literally contains it, because the index holds 'runn', not 'Running'.

A lexical index does not store raw text; it stores analyzed terms. An analyzer turns a document's text into a normalized token stream -- it lowercases, splits on non-word characters, and stems each token toward a root (here, stripping a trailing 'ing', 'ed', or 's'). The inverted index then maps each analyzed term to the documents that contain it. That normalization is what lets 'Running', 'runs', and 'RUNNING' all find the same passage: they collapse to one term at index time.

The catch is that the query must go through the identical analyzer, because the index contains only analyzed terms. Search the index for the raw string 'Running' and you find nothing -- not because no document contains that word, but because the index stored the stemmed, lowercased form and 'Running' is not it. The word is right there in the document's text, visible to any human, and the search still misses it. Nothing errors; the query just returns the wrong (or empty) result.

This is the lexical counterpart of embedding the query and the corpus with one model version: the two sides must be processed the same way, or they live in different spaces and cannot meet. A mismatched analyzer -- an un-analyzed query, or a query analyzer that lowercases but does not stem while the index does both -- silently breaks matching for exactly the terms the normalization touched.

The rule: run the query through the same analyzer that built the index -- same lowercasing, tokenizing, and stemming -- because the index stores only analyzed terms, so a raw or differently-analyzed query fails to match a term the index normalized, even a word that appears verbatim in the document.

On this fixture the document 'Running shoes for athletes' is indexed as the analyzed terms including 'runn'. A raw search for 'Running' finds nothing though the word is in the text; analyzing the query to 'runn' finds the document. This computes both.

  --index    each document's analyzed terms as stored in the inverted index
  --search   the raw-query search (which misses) vs the analyzed-query search (which matches)
  --check    the index stores analyzed terms, so a raw query misses a word it contains; analyzing the query matches

docs and query are the fixture; the analyzed index and the two searches are computed. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "analyzer.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def stem(word):
    """A crude stemmer: strip one trailing 'ing', 'ed', or 's'."""
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[: -len(suffix)]
    return word


def analyze(text):
    """The analyzer: lowercase, split on non-word characters, stem each token."""
    return [stem(tok) for tok in re.split(r"\W+", text.lower()) if tok]


def build_index(docs):
    """Map each document id to the set of analyzed terms it contains."""
    return {d["id"]: set(analyze(d["text"])) for d in docs}


def raw_search(index, query):
    """Search the index for the query string as-is -- no analysis."""
    return [doc_id for doc_id, terms in index.items() if query in terms]


def analyzed_search(index, query):
    """Analyze the query the same way, then match any of its terms."""
    q_terms = set(analyze(query))
    return [doc_id for doc_id, terms in index.items() if terms & q_terms]


# ----------------------------------------------------------------- printing

def index_view(data):
    index = build_index(data["docs"])
    print("INDEX — analyzed terms stored per document")
    print("-" * 58)
    for d in data["docs"]:
        print("  %s  %-28s -> %s" % (d["id"], repr(d["text"]), sorted(index[d["id"]])))
    print("-" * 58)
    print("  the index stores stemmed, lowercased terms -- not the original words")


def search_view(data):
    index = build_index(data["docs"])
    q = data["query"]
    print("SEARCH — raw query vs analyzed query for %r" % q)
    print("-" * 58)
    print("  analyze(%r) = %s" % (q, analyze(q)))
    print("  raw search      (looks up %r)        -> %s" % (q, raw_search(index, q)))
    print("  analyzed search (looks up %s) -> %s" % (analyze(q), analyzed_search(index, q)))
    print("-" * 58)
    print("  the raw query misses a document whose text contains the word")


def check(data):
    print("SELF-TEST — the index stores analyzed terms, so a raw query misses a word it contains; analyzing the query matches")
    print("-" * 116)
    index = build_index(data["docs"])
    q = data["query"]
    docs = data["docs"]

    q_analyzed = analyze(q)

    index_stores_analyzed = q not in index[docs[0]["id"]] and q_analyzed[0] in index[docs[0]["id"]]
    print("  index stores %r not %r for the first doc = %s"
          % (q_analyzed[0], q, index_stores_analyzed))

    word_literally_in_doc = q.lower() in docs[0]["text"].lower()
    print("  the raw query word appears verbatim in that doc's text = %s" % word_literally_in_doc)

    raw_hits = raw_search(index, q)
    raw_finds_nothing = raw_hits == []
    print("  raw (un-analyzed) query finds nothing = %s (%s)" % (raw_finds_nothing, raw_hits))

    analyzed_hits = analyzed_search(index, q)
    analyzed_finds_it = docs[0]["id"] in analyzed_hits
    print("  analyzed query finds the document = %s (%s)" % (analyzed_finds_it, analyzed_hits))

    parity_required = len(raw_hits) < len(analyzed_hits)
    print("  matching the query analyzer to the index is required = %s" % parity_required)

    ok = (index_stores_analyzed and word_literally_in_doc and raw_finds_nothing
          and analyzed_finds_it and parity_required)
    print("-" * 116)
    print("SELF-TEST %s  index_stores_analyzed=%s  word_literally_in_doc=%s  raw_finds_nothing=%s  analyzed_finds_it=%s  parity_required=%s"
          % ("PASS" if ok else "FAIL", index_stores_analyzed, word_literally_in_doc,
             raw_finds_nothing, analyzed_finds_it, parity_required))
    return ok


def main():
    p = argparse.ArgumentParser(description="Analyzer parity: run the query through the same analyzer that built the index -- same lowercasing, tokenizing, and stemming -- because the index stores only analyzed terms, so a raw or differently-analyzed query fails to match a term the index normalized, even a word that appears verbatim in the document.")
    p.add_argument("--index", action="store_true")
    p.add_argument("--search", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  query=%r  file=%s  (the corpus and query are a fixture)"
          % (len(data["docs"]), data["query"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.index:
        index_view(data)
    elif args.search:
        search_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
