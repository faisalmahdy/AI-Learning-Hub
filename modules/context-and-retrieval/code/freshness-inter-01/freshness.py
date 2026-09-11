"""Search the index, but the index is a snapshot -- a document added after the last build is invisible until you re-index.

A retrieval system does not search your data; it searches an INDEX of your data, and the index is a snapshot frozen at
the moment it was last built. Every document that existed then is in it; every document created or changed SINCE then is
not, until the index is rebuilt or incrementally updated. This is easy to forget because the corpus and the index feel like
the same thing -- you add a document to the store and assume it is now findable -- but they are decoupled: the write goes to
the store immediately, and the index catches up only on its own schedule. In the gap between 'document added' and 'index
updated,' the document exists and is completely invisible to search. A query whose true best answer is that new document
gets, instead, the best of the OLD documents, and it comes back looking like a perfectly good result -- there is no error,
no empty response, just a confidently returned older, worse match, with the right answer sitting unindexed a few
milliseconds away.

The failure is silent and it is worst exactly where it matters most: freshness-sensitive queries. Ask about the latest
release, today's incident, the document someone just uploaded, the price that changed this morning -- the correct answer is
the newest document, which is the one most likely to be on the wrong side of the last index build. So a stale index does
not degrade uniformly; it degrades specifically on the queries where recency is the point, returning yesterday's answer to
a question about today and giving no sign that a better answer exists.

The fix is to treat index freshness as a first-class property with a real target: index incrementally so new and changed
documents enter the index quickly (near-real-time indexing), track and monitor the indexing lag (how far behind the index
is), and for the most recency-critical paths, either guarantee a tight freshness SLA or supplement retrieval with a
recency-aware source that can see writes the batch index has not caught. The index being a snapshot is not a bug to
eliminate -- rebuilding continuously has real cost -- but a property to manage: you decide how stale is acceptable and
engineer the lag to stay under it.

The rule: a search index is a snapshot, so a document added or changed after the last index build is invisible to search
until the index is updated -- and a query for it silently returns an older, worse match instead of the right answer -- so
index freshness must be managed (incremental/near-real-time indexing, monitored lag, a freshness SLA) rather than assumed.

On this fixture the best answer, d2_latest_update (relevance 5), was added after the index was built, so it is unindexed.
A search against the stale index returns d1_overview (relevance 2), missing the better document entirely. After re-indexing,
the same search finds d2 (relevance 5). This computes both.

  --search    the top result from the stale index (indexed docs only) vs a fresh index (all docs), and their relevance
  --index     what the snapshot index contains vs what the corpus contains -- the freshness gap and which doc is missing
  --check     the best document is unindexed, so the stale index returns a worse match; re-indexing finds the best one

documents (with relevance and indexed flags) are the fixture; every search result and freshness gap is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "freshness.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def search(documents, use_full_corpus):
    """Return the highest-relevance document the search can see. A stale index sees only indexed docs."""
    candidates = documents if use_full_corpus else [d for d in documents if d["indexed"]]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d["relevance"])


def best_document(documents):
    """The truly best answer in the corpus, indexed or not."""
    return max(documents, key=lambda d: d["relevance"])


# ----------------------------------------------------------------- printing

def search_view(data):
    docs = data["documents"]
    stale = search(docs, use_full_corpus=False)
    fresh = search(docs, use_full_corpus=True)
    print("SEARCH — top result from the stale index vs a freshly rebuilt index")
    print("-" * 66)
    print("  corpus (id, relevance, indexed?):")
    for d in docs:
        print("    %-18s relevance %d   indexed=%s" % (d["id"], d["relevance"], d["indexed"]))
    print("-" * 66)
    print("  stale index returns: %s (relevance %d)" % (stale["id"], stale["relevance"]))
    print("  fresh index returns: %s (relevance %d)" % (fresh["id"], fresh["relevance"]))
    print("  the stale index misses the best document because it is not yet indexed.")


def index_view(data):
    docs = data["documents"]
    indexed = [d["id"] for d in docs if d["indexed"]]
    missing = [d["id"] for d in docs if not d["indexed"]]
    print("INDEX — the snapshot index vs the corpus")
    print("-" * 58)
    print("  corpus has %d documents: %s" % (len(docs), [d["id"] for d in docs]))
    print("  index (snapshot) has %d: %s" % (len(indexed), indexed))
    print("  NOT yet indexed (added after the last build): %s" % missing)
    print("-" * 58)
    print("  the freshness gap is the %d document(s) in the corpus but not the index." % len(missing))


def check(data):
    print("SELF-TEST — the best document is unindexed, so the stale index returns a worse match; re-indexing finds the best")
    print("-" * 110)
    docs = data["documents"]
    stale = search(docs, use_full_corpus=False)
    fresh = search(docs, use_full_corpus=True)
    best = best_document(docs)

    index_is_snapshot = sum(1 for d in docs if d["indexed"]) < len(docs)
    print("  the index is a snapshot missing some corpus documents = %s (%d of %d indexed)"
          % (index_is_snapshot, sum(1 for d in docs if d["indexed"]), len(docs)))

    best_doc_unindexed = not best["indexed"]
    print("  the best document is not in the index = %s (%s, relevance %d)" % (best_doc_unindexed, best["id"], best["relevance"]))

    stale_misses_best = stale["id"] != best["id"]
    print("  the stale index misses the best document = %s (returns %s, not %s)" % (stale_misses_best, stale["id"], best["id"]))

    stale_returns_worse = stale["relevance"] < best["relevance"]
    print("  the stale result is worse than the true best = %s (relevance %d < %d)" % (stale_returns_worse, stale["relevance"], best["relevance"]))

    reindex_finds_best = fresh["id"] == best["id"]
    print("  re-indexing makes the search find the best document = %s (%s, relevance %d)" % (reindex_finds_best, fresh["id"], fresh["relevance"]))

    ok = index_is_snapshot and best_doc_unindexed and stale_misses_best and stale_returns_worse and reindex_finds_best
    print("-" * 110)
    print("SELF-TEST %s  index_is_snapshot=%s  best_doc_unindexed=%s  stale_misses_best=%s  stale_returns_worse=%s  reindex_finds_best=%s"
          % ("PASS" if ok else "FAIL", index_is_snapshot, best_doc_unindexed, stale_misses_best, stale_returns_worse, reindex_finds_best))
    return ok


def main():
    p = argparse.ArgumentParser(description="Index freshness: a search index is a snapshot, so a document added or changed after the last index build is invisible to search until the index is updated -- and a query for it silently returns an older, worse match instead of the right answer -- so index freshness must be managed (incremental/near-real-time indexing, monitored lag, a freshness SLA) rather than assumed.")
    p.add_argument("--search", action="store_true")
    p.add_argument("--index", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("documents=%d  file=%s  (the corpus with relevance and indexed flags is a fixture)"
          % (len(data["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.search:
        search_view(data)
    elif args.index:
        index_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
