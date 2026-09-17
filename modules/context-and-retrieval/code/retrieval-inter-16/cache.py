"""Set the semantic cache threshold high, or a superficially similar query gets served the wrong answer.

A semantic cache remembers past questions and their answers, keyed by the question's embedding. A new
question comes in; if it is close enough to a cached one, you return the cached answer instead of doing the
expensive retrieval-and-generation again. It is a big win for paraphrases -- 'how do I reset my password'
and 'reset my password please' should share one answer. The whole thing hinges on 'close enough,' which is
a similarity threshold, and the threshold is a trade-off. Set it too low and the cache fires on questions
that merely share words but mean something different, serving them a confidently wrong cached answer.

The danger case is a query that overlaps a cached one lexically but asks about a different thing. 'Reset my
subscription' shares 'reset' with the password-reset entry and 'subscription' with the cancel-subscription
entry, so it sits at moderate similarity to both -- high enough to trip a loose threshold, and it will be
handed one of those answers, neither of which is about resetting a subscription. A true paraphrase, by
contrast, sits at high similarity to its match. So the right threshold is above the moderate
lexical-overlap band and below the paraphrase band: tight enough to reject the impostor, loose enough to
still catch the real paraphrase.

On this fixture the cache holds a password-reset answer and a cancel-subscription answer. A loose threshold
(0.60) makes the different-intent 'reset my subscription' hit a cached answer -- a wrong reuse -- while a
tight threshold (0.80) rejects it (compute fresh) yet still serves the true paraphrase from cache. This
computes both.

  --sim        each incoming query's nearest cached entry and its similarity
  --serve      what each threshold serves each query, and whether it is a wrong reuse
  --check      a loose threshold serves a wrong cached answer; a tight one rejects it and keeps the good hit

The cache, queries, and thresholds are the fixture; every similarity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "queries.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def vec(text):
    d = {}
    for w in text.lower().split():
        d[w] = d.get(w, 0) + 1
    return d


def cosine(a, b):
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return round(dot / (na * nb), 3) if na and nb else 0.0


def nearest(query, cache):
    """The cached entry most similar to the query, and that similarity."""
    best = max(cache, key=lambda e: cosine(vec(query), vec(e["query"])))
    return best, cosine(vec(query), vec(best["query"]))


def serve(query, cache, threshold):
    """Return the cached answer id if the nearest is within threshold, else None (a cache miss)."""
    best, sim = nearest(query, cache)
    return best["id"] if sim >= threshold else None


def is_wrong_reuse(q, cache, threshold):
    """A hit that returns an id other than the query's expected match (None expected = should have missed)."""
    served = serve(q["text"], cache, threshold)
    return served is not None and served != q["expected"]


# ----------------------------------------------------------------- printing

def sim_view(data):
    cache = data["cache"]
    print("SIM — each incoming query's nearest cached entry")
    print("-" * 62)
    for q in data["queries"]:
        best, sim = nearest(q["text"], cache)
        want = q["expected"] if q["expected"] else "none (novel)"
        print("  %-26s -> %s  sim %.3f   (want %s)" % (repr(q["text"]), best["id"], sim, want))
    print("-" * 62)
    print("  the paraphrase sits high; the different-intent query sits moderate.")


def serve_view(data):
    cache, lo, hi = data["cache"], data["loose"], data["tight"]
    print("SERVE — what each threshold serves (loose %.2f vs tight %.2f)" % (lo, hi))
    print("-" * 66)
    print("  query                        loose         tight")
    for q in data["queries"]:
        sl, sh = serve(q["text"], cache, lo), serve(q["text"], cache, hi)
        tag_l = sl or "miss"
        tag_h = sh or "miss"
        wl = " (WRONG)" if is_wrong_reuse(q, cache, lo) else ""
        wh = " (WRONG)" if is_wrong_reuse(q, cache, hi) else ""
        print("  %-26s   %-8s%-8s  %s%s" % (repr(q["text"]), tag_l, wl, tag_h, wh))
    print("-" * 66)
    print("  loose serves a wrong answer to the different-intent query; tight does not.")


def check(data):
    print("SELF-TEST — a loose threshold serves a wrong cached answer; a tight one rejects it and keeps the good hit")
    print("-" * 104)
    cache, lo, hi = data["cache"], data["loose"], data["tight"]
    queries = data["queries"]
    para = next(q for q in queries if q["expected"])
    novel = next(q for q in queries if not q["expected"])

    loose_wrong_reuse = any(is_wrong_reuse(q, cache, lo) for q in queries)
    print("  the loose threshold produces a wrong reuse = %s (%s)"
          % (loose_wrong_reuse, [q["text"] for q in queries if is_wrong_reuse(q, cache, lo)]))

    tight_no_wrong_reuse = not any(is_wrong_reuse(q, cache, hi) for q in queries)
    print("  the tight threshold produces no wrong reuse = %s" % tight_no_wrong_reuse)

    tight_keeps_good_hit = serve(para["text"], cache, hi) == para["expected"]
    print("  the tight threshold still serves the true paraphrase from cache = %s (%s)"
          % (tight_keeps_good_hit, serve(para["text"], cache, hi)))

    tight_rejects_novel = serve(novel["text"], cache, hi) is None
    print("  the tight threshold makes the different-intent query miss = %s" % tight_rejects_novel)

    separable = nearest(para["text"], cache)[1] > nearest(novel["text"], cache)[1]
    print("  the paraphrase is more similar than the impostor, so a threshold separates them = %s (%.3f > %.3f)"
          % (separable, nearest(para["text"], cache)[1], nearest(novel["text"], cache)[1]))

    ok = loose_wrong_reuse and tight_no_wrong_reuse and tight_keeps_good_hit and tight_rejects_novel and separable
    print("-" * 104)
    print("SELF-TEST %s  loose_wrong_reuse=%s  tight_no_wrong_reuse=%s  tight_keeps_good_hit=%s  tight_rejects_novel=%s  separable=%s"
          % ("PASS" if ok else "FAIL", loose_wrong_reuse, tight_no_wrong_reuse, tight_keeps_good_hit, tight_rejects_novel, separable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Set the semantic cache threshold to reject different-intent lookalikes.")
    p.add_argument("--sim", action="store_true")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cache=%d  queries=%d  loose=%.2f  tight=%.2f  file=%s  (the cache and queries are a fixture)"
          % (len(data["cache"]), len(data["queries"]), data["loose"], data["tight"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sim:
        sim_view(data)
    elif args.serve:
        serve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
