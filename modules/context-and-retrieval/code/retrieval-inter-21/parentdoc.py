"""Retrieve on small chunks but return the parent, or you match precisely and answer incompletely.

Chunk size is a tug of war. Small chunks match a query PRECISELY -- a short passage that is almost all query
terms scores high, because the match is not diluted by surrounding text. But a small chunk is starved of
context: the passage that matches 'refund policy' may not contain the actual number of days, which sits a
sentence away. Big chunks have the opposite problem: a whole section contains both the query terms and the
detail, so it answers completely, but its match score is diluted across all its other tokens, so it retrieves
worse and can lose to a more focused but less complete chunk. Pick small and you retrieve well but answer with
half the story; pick big and you answer fully but retrieve poorly.

Small-to-big retrieval (also called parent-document retrieval) takes both. Index and search the SMALL chunks,
so retrieval is precise -- the query lands on the exact passage that matches. But do not return that small
chunk; return its PARENT, the larger section it belongs to, which carries the surrounding context. You match on
the needle and hand the model the haystack around it. Retrieval quality comes from the small chunk's focus;
answer quality comes from the parent's completeness; neither is sacrificed to the other.

On this fixture a section P holds two small chunks: one full of the query terms ('refund', 'policy') and one
holding the detail ('30', 'days'). The query-term chunk scores 0.67 and retrieves best, but on its own it has
0 of the 2 context tokens -- an incomplete answer. Its parent P has all 2 context tokens but a diluted score of
0.29. Small-to-big retrieves via the 0.67 chunk and returns the complete parent. This computes both.

  --score      each candidate's retrieval score (overlap/length) and its context completeness
  --strategy   what small-only, parent-only, and small-to-big each retrieve and return
  --check      the small chunk matches best but is incomplete; the parent completes it; small-to-big does both

The chunks and query are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "docs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def overlap(tokens, query):
    return sum(1 for t in query if t in tokens)


def score(tokens, query):
    """Precision-weighted retrieval score: query overlap divided by the chunk's length."""
    return overlap(tokens, query) / len(tokens)


def completeness(tokens, context_needed):
    """Fraction of the needed context tokens present in the text."""
    return sum(1 for t in context_needed if t in tokens) / len(context_needed)


def parent_tokens(chunks, parent):
    out = []
    for c in chunks:
        if c["parent"] == parent:
            out += c["tokens"]
    return out


# ----------------------------------------------------------------- printing

def score_view(data):
    q, ctx, chunks = data["query"], data["context_needed"], data["chunks"]
    ptoks = parent_tokens(chunks, "P")
    print("SCORE — retrieval score (overlap/length) and context completeness")
    print("-" * 66)
    print("  candidate   len   overlap   score   completeness")
    for c in chunks:
        print("  %-10s  %2d    %d         %.2f    %.0f%%" % (c["id"], len(c["tokens"]), overlap(c["tokens"], q), score(c["tokens"], q), 100 * completeness(c["tokens"], ctx)))
    print("  %-10s  %2d    %d         %.2f    %.0f%%" % ("parent P", len(ptoks), overlap(ptoks, q), score(ptoks, q), 100 * completeness(ptoks, ctx)))
    print("-" * 66)
    print("  the small query-chunk scores best but is 0% complete; the parent is complete but scores low.")


def strategy_view(data):
    q, ctx, chunks = data["query"], data["context_needed"], data["chunks"]
    best = max(chunks, key=lambda c: score(c["tokens"], q))
    ptoks = parent_tokens(chunks, best["parent"])
    print("STRATEGY — what each approach retrieves and returns")
    print("-" * 66)
    print("  small-only:   retrieve %s (score %.2f) -> return it        -> %.0f%% complete" % (best["id"], score(best["tokens"], q), 100 * completeness(best["tokens"], ctx)))
    print("  parent-only:  retrieve parent P (score %.2f) -> return it   -> %.0f%% complete" % (score(ptoks, q), 100 * completeness(ptoks, ctx)))
    print("  small-to-big: retrieve %s (score %.2f) -> return parent P  -> %.0f%% complete" % (best["id"], score(best["tokens"], q), 100 * completeness(ptoks, ctx)))
    print("-" * 66)
    print("  small-to-big keeps the small chunk's score and the parent's completeness.")


def check(data):
    print("SELF-TEST — the small chunk matches best but is incomplete; the parent completes it; small-to-big does both")
    print("-" * 108)
    q, ctx, chunks = data["query"], data["context_needed"], data["chunks"]
    best = max(chunks, key=lambda c: score(c["tokens"], q))
    ptoks = parent_tokens(chunks, best["parent"])

    small_scores_best = score(best["tokens"], q) > score(ptoks, q)
    print("  the small query-chunk retrieves better than the parent = %s (%.2f > %.2f)" % (small_scores_best, score(best["tokens"], q), score(ptoks, q)))

    small_incomplete = completeness(best["tokens"], ctx) < 1.0
    print("  the small chunk alone is an incomplete answer = %s (%.0f%% of context)" % (small_incomplete, 100 * completeness(best["tokens"], ctx)))

    parent_complete = completeness(ptoks, ctx) == 1.0
    print("  the parent contains all the needed context = %s (%.0f%%)" % (parent_complete, 100 * completeness(ptoks, ctx)))

    parent_retrieval_weaker = score(ptoks, q) < score(best["tokens"], q)
    print("  the parent retrieves worse (why not just index parents) = %s" % parent_retrieval_weaker)

    small_to_big_best_of_both = score(best["tokens"], q) == max(score(c["tokens"], q) for c in chunks) and completeness(ptoks, ctx) == 1.0
    print("  small-to-big keeps the best score and full completeness = %s" % small_to_big_best_of_both)

    ok = small_scores_best and small_incomplete and parent_complete and parent_retrieval_weaker and small_to_big_best_of_both
    print("-" * 108)
    print("SELF-TEST %s  small_scores_best=%s  small_incomplete=%s  parent_complete=%s  parent_retrieval_weaker=%s  small_to_big_best_of_both=%s"
          % ("PASS" if ok else "FAIL", small_scores_best, small_incomplete, parent_complete, parent_retrieval_weaker, small_to_big_best_of_both))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retrieve on small chunks and return their parent (small-to-big) for precise match and complete context.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--strategy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  context_needed=%s  chunks=%d  file=%s  (the document is a fixture)"
          % (data["query"], data["context_needed"], len(data["chunks"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.strategy:
        strategy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
