"""Apply the hard filter before the top-k cut, not after -- post-filtering a search result can return far fewer hits than you asked for.

Retrieval often carries a hard constraint alongside the semantic query: only documents from this year, only this user's files, only the 'legal' category, only in-stock products. There are two places to apply that constraint, and they are not equivalent. POST-filtering runs the vector search first, takes the top-k most similar documents, and then discards the ones that fail the constraint. PRE-filtering restricts to the documents that satisfy the constraint first, and searches for the top-k within that subset. They sound interchangeable and they are not: post-filtering can hand back far fewer results than you asked for, sometimes none.

The failure is a starvation. The top-k cut happens before the constraint is checked, so the k slots get filled by the most similar documents regardless of whether they satisfy the constraint -- and if the highest-similarity documents happen to fail it, they consume the slots and are then thrown away, leaving only the few (or zero) matching documents that made the top-k. Worse, perfectly good matching documents that ranked just below the top-k are never even considered: they lost their slots to non-matching documents that were only going to be discarded. So post-filtering under-returns and misses valid results at the same time, and it does so silently -- you asked for k and got a short list, with no signal that better matching documents were sitting just outside the cut.

Pre-filtering fixes it by making the constraint part of the search space, not a cleanup step. Restrict to the matching documents, then take the top-k among them, and every slot goes to a valid document -- you get k results (as long as k matching documents exist), and they are the k most similar matching ones. The constraint no longer competes with similarity for the slots. The cost is that the index must support filtering during search (a filtered nearest-neighbor query, or a metadata index) to do this efficiently; where it cannot, the middle ground is to over-fetch (retrieve far more than k, then post-filter) to reduce the starvation, but pre-filtering is the correct answer when the index supports it.

The rule: apply a hard metadata constraint before the top-k cut (pre-filter: search within the matching subset), not after it (post-filter: search then discard), because taking the top-k first lets high-similarity non-matching documents consume the slots and be thrown away -- so post-filtering returns fewer than k and misses valid lower-ranked matches, while pre-filtering fills all k slots with the best matching documents.

On this fixture the query wants the top-3 category-A documents. Post-filtering takes the top-3 by similarity (two category-B, one category-A) and discards the B's, returning just 1 -- and missing d5 and d6, valid A documents. Pre-filtering restricts to A first and returns the top-3 A documents. This computes both.

  --docs      the documents by similarity with their categories, and which the top-k cut includes
  --filter    post-filter (top-k then discard) vs pre-filter (restrict then top-k): what each returns
  --check     post-filtering under-returns and misses valid matches; pre-filtering fills all k slots with the best matches

documents, top_k, and required_category are the fixture; the two result sets and counts are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "prefilter.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def by_similarity(docs):
    return sorted(docs, key=lambda d: (-d["similarity"], d["id"]))


def post_filter(docs, k, category):
    """Search first: take the top-k by similarity, THEN discard non-matching."""
    topk = by_similarity(docs)[:k]
    return [d for d in topk if d["category"] == category]


def pre_filter(docs, k, category):
    """Restrict to matching documents first, THEN take the top-k by similarity."""
    matching = [d for d in docs if d["category"] == category]
    return by_similarity(matching)[:k]


def ids(docs):
    return [d["id"] for d in docs]


# ----------------------------------------------------------------- printing

def docs_view(data):
    docs, k, cat = data["documents"], data["top_k"], data["required_category"]
    topk = by_similarity(docs)[:k]
    print("DOCS — documents by similarity (top_k=%d, required category '%s')" % (k, cat))
    print("-" * 58)
    print("  doc   similarity   category   in top-%d?" % k)
    for d in by_similarity(docs):
        print("  %-4s  %-10.1f   %-8s   %s" % (d["id"], d["similarity"], d["category"], d in topk))
    print("-" * 58)
    print("  the top-%d by similarity is %s -- categories mixed" % (k, ids(topk)))


def filter_view(data):
    docs, k, cat = data["documents"], data["top_k"], data["required_category"]
    post = post_filter(docs, k, cat)
    pre = pre_filter(docs, k, cat)
    print("FILTER — post-filter (top-k then discard) vs pre-filter (restrict then top-k)")
    print("-" * 66)
    print("  post-filter: %s -> %d result(s) of %d requested" % (ids(post), len(post), k))
    print("  pre-filter:  %s -> %d result(s) of %d requested" % (ids(pre), len(pre), k))
    print("-" * 66)
    missed = [d["id"] for d in pre if d["id"] not in ids(post)]
    print("  valid matches post-filter missed: %s" % (missed or "none"))


def check(data):
    print("SELF-TEST — post-filtering under-returns and misses valid matches; pre-filtering fills all k slots with the best matches")
    print("-" * 122)
    docs, k, cat = data["documents"], data["top_k"], data["required_category"]
    post = post_filter(docs, k, cat)
    pre = pre_filter(docs, k, cat)
    total_matching = sum(1 for d in docs if d["category"] == cat)

    enough_matches_exist = total_matching >= k
    print("  enough matching documents exist to fill top-%d = %s (%d category-'%s')" % (k, enough_matches_exist, total_matching, cat))

    postfilter_underreturns = len(post) < k
    print("  post-filter returns fewer than requested = %s (%d of %d)" % (postfilter_underreturns, len(post), k))

    prefilter_returns_k = len(pre) == k
    print("  pre-filter returns the full top-%d = %s (%s)" % (k, prefilter_returns_k, ids(pre)))

    postfilter_misses_valid = any(d["id"] not in ids(post) for d in pre)
    missed = [d["id"] for d in pre if d["id"] not in ids(post)]
    print("  post-filter misses valid matching documents = %s (%s)" % (postfilter_misses_valid, missed))

    all_prefilter_match = all(d["category"] == cat for d in pre)
    print("  every pre-filter result satisfies the constraint = %s" % all_prefilter_match)

    prefilter_is_best_matching = ids(pre) == ids(by_similarity([d for d in docs if d["category"] == cat])[:k])
    print("  pre-filter returns the k most similar matching documents = %s (%s)" % (prefilter_is_best_matching, ids(pre)))

    ok = (enough_matches_exist and postfilter_underreturns and prefilter_returns_k and postfilter_misses_valid
          and all_prefilter_match and prefilter_is_best_matching)
    print("-" * 122)
    print("SELF-TEST %s  enough_matches_exist=%s  postfilter_underreturns=%s  prefilter_returns_k=%s  postfilter_misses_valid=%s  all_prefilter_match=%s  prefilter_is_best_matching=%s"
          % ("PASS" if ok else "FAIL", enough_matches_exist, postfilter_underreturns, prefilter_returns_k, postfilter_misses_valid, all_prefilter_match, prefilter_is_best_matching))
    return ok


def main():
    p = argparse.ArgumentParser(description="Metadata pre-filtering: apply a hard metadata constraint before the top-k cut (pre-filter: search within the matching subset), not after it (post-filter: search then discard), because taking the top-k first lets high-similarity non-matching documents consume the slots and be thrown away -- so post-filtering returns fewer than k and misses valid lower-ranked matches, while pre-filtering fills all k slots with the best matching documents.")
    p.add_argument("--docs", action="store_true")
    p.add_argument("--filter", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("documents=%d  top_k=%d  required_category=%s  file=%s  (documents, k, and the constraint are a fixture)"
          % (len(data["documents"]), data["top_k"], data["required_category"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.docs:
        docs_view(data)
    elif args.filter:
        filter_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
