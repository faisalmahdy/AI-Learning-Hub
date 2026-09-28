"""Pre-filter the corpus by metadata before the search, not after -- post-filtering the top-k can return nothing.

Real retrieval almost always carries a metadata constraint: only this user's documents, only this date range,
only this team's, only published pages. There are two places to apply that filter, and they are not
equivalent. POST-FILTER runs the vector search first, takes the top-k by similarity, and then drops the
results that fail the filter. PRE-FILTER applies the constraint first, restricting the candidate set to the
allowed documents, and then takes the top-k among those. They give the same answer only when the top-k
happen to pass the filter -- and when they do not, post-filter silently returns fewer than k results, or
none, because it filtered away everything it retrieved.

The failure is common because the highest-similarity documents are often exactly the ones the filter
excludes: the most relevant text might be in another team's space, or outside the date range, or in a draft.
Post-filter retrieves those, discards them, and hands back a short or empty list, and the caller thinks
there was nothing relevant when really the relevant allowed documents were sitting just below the cut.

On this fixture the query may only use team==eng documents, and the three highest-scoring documents are all
team==sales. Post-filtering the top-3 returns 0 allowed results. Pre-filtering to the eng documents first and
then taking the top-3 returns 3. Same documents, same filter -- only the order of filter-then-search versus
search-then-filter differs.

  --docs       the documents, their scores, and their team, and which the query is allowed
  --retrieve   what post-filter vs pre-filter returns for the top-k
  --check      post-filter starves under a restrictive filter; pre-filter returns the intended k

The scores and teams are the fixture; every retrieval is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "docs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def by_score(docs):
    return sorted(docs, key=lambda d: -d["score"])


# ------------------------------------------------------------- two filter orderings

def post_filter(docs, k, allowed):
    """Search first: take the top-k by score, THEN drop the ones failing the filter -- may return < k."""
    topk = by_score(docs)[:k]
    return [d for d in topk if d["team"] == allowed]


def pre_filter(docs, k, allowed):
    """Filter first: keep the allowed documents, THEN take the top-k among them -- returns k if enough exist."""
    allowed_docs = [d for d in docs if d["team"] == allowed]
    return by_score(allowed_docs)[:k]


# ----------------------------------------------------------------- printing

def docs_view(data):
    allowed = data["allowed_team"]
    print("DOCS — score and team per document (query allowed: team==%s)" % allowed)
    print("-" * 46)
    for d in by_score(data["docs"]):
        mark = "  <- allowed" if d["team"] == allowed else ""
        print("  %s  score %.2f  team=%-6s%s" % (d["id"], d["score"], d["team"], mark))
    print("-" * 46)
    print("  the three highest scores are all the wrong team.")


def retrieve_view(data):
    docs, k, allowed = data["docs"], data["k"], data["allowed_team"]
    post = post_filter(docs, k, allowed)
    pre = pre_filter(docs, k, allowed)
    print("RETRIEVE — top-%d under post-filter vs pre-filter (allowed team==%s)" % (k, allowed))
    print("-" * 56)
    print("  post-filter: %s   (%d of %d wanted)" % ([d["id"] for d in post] or "(empty)", len(post), k))
    print("  pre-filter:  %s   (%d of %d wanted)" % ([d["id"] for d in pre], len(pre), k))
    print("-" * 56)
    print("  post-filter kept the top-3 (all sales) then dropped them; pre-filter searched within eng.")


def check(data):
    print("SELF-TEST — post-filter starves under a restrictive filter; pre-filter returns the intended k")
    print("-" * 88)
    docs, k, allowed = data["docs"], data["k"], data["allowed_team"]
    n_allowed = sum(1 for d in docs if d["team"] == allowed)

    post = post_filter(docs, k, allowed)
    pre = pre_filter(docs, k, allowed)

    post_starves = len(post) < k
    print("  post-filter returns fewer than the %d wanted = %s (%d returned)" % (k, post_starves, len(post)))

    pre_returns_k = len(pre) == k
    print("  pre-filter returns the full k = %s (%d returned, %d allowed exist)" % (pre_returns_k, len(pre), n_allowed))

    pre_all_allowed = all(d["team"] == allowed for d in pre)
    print("  every pre-filter result satisfies the filter = %s" % pre_all_allowed)

    pre_beats_post = len(pre) > len(post)
    print("  pre-filter returns more usable results than post-filter = %s (%d vs %d)" % (pre_beats_post, len(pre), len(post)))

    ok = post_starves and pre_returns_k and pre_all_allowed and pre_beats_post
    print("-" * 88)
    print("SELF-TEST %s  post_starves=%s  pre_returns_k=%s  pre_all_allowed=%s  pre_beats_post=%s"
          % ("PASS" if ok else "FAIL", post_starves, pre_returns_k, pre_all_allowed, pre_beats_post))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pre-filter the corpus by metadata before the search, not after.")
    p.add_argument("--docs", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  k=%d  allowed_team=%s  file=%s  (the scores and teams are a fixture)"
          % (len(data["docs"]), data["k"], data["allowed_team"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.docs:
        docs_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
