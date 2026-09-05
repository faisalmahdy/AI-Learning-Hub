"""Put a relevance floor under retrieval -- always returning the top hit injects noise on an out-of-scope query.

A vector retriever always has a top result. Ask it anything -- even a question it has no document for --
and it will rank its documents by similarity and hand back the best one. But "the best of a bad lot" is
still a bad lot: if the closest document is barely related, injecting it into the prompt does not help,
it misleads, because the model treats retrieved context as relevant by default and will happily answer
from an irrelevant passage. The retriever cannot say "I have nothing for this" unless you let it.

A relevance threshold is that permission. Keep the top hit only if its similarity clears a floor; below
the floor, return nothing and let the model answer from its own knowledge or decline. The floor turns
retrieval from "always inject something" into "inject only when there is a real match," which is what
keeps out-of-scope queries from being answered out of irrelevant context.

On this fixture two in-scope queries match a document at cosine ~0.99 and two out-of-scope queries
(a weather question, a stock tip) match every document only ~0.1-0.2. Always-top-1 injects a document
for all four, so the two out-of-scope queries get irrelevant billing context. The 0.5 threshold injects
for the two in-scope queries and abstains on the two out-of-scope ones -- same coverage of the real
matches, zero junk injected. This runs both policies and counts coverage and junk.

  --queries    each query, its best-matching document, and that match's cosine similarity
  --retrieve   what always-top-1 vs the threshold policy injects for each query
  --check      the threshold abstains on out-of-scope queries while still covering every in-scope one

The vectors and threshold are the fixture; every cosine and decision is computed. Stdlib only.
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


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def best_match(qvec, docs):
    """The highest-similarity document and its cosine."""
    best = max(docs, key=lambda d: cosine(qvec, docs[d]))
    return best, cosine(qvec, docs[best])


# ------------------------------------------------------------- two policies

def always_top1(qvec, docs, threshold):
    """Always inject the top hit, however weak the match."""
    doc, sim = best_match(qvec, docs)
    return doc, sim


def with_threshold(qvec, docs, threshold):
    """Inject the top hit only if its similarity clears the floor; otherwise abstain (return None)."""
    doc, sim = best_match(qvec, docs)
    if sim < threshold:
        return None, sim
    return doc, sim


# ----------------------------------------------------------------- printing

def queries_view(data):
    docs = data["docs"]
    print("QUERIES — each query's best-matching document and its cosine")
    print("-" * 58)
    for q, qd in data["queries"].items():
        doc, sim = best_match(qd["vec"], docs)
        scope = "in-scope" if qd["in_scope"] else "OUT-of-scope"
        print("  %-11s %-12s best=%-11s cos %.3f" % (q, scope, doc, sim))
    print("-" * 58)
    print("  in-scope queries match ~0.99; out-of-scope match ~0.1-0.2 -- a 0.5 floor splits them.")


def retrieve_view(data):
    docs, thr = data["docs"], data["threshold"]
    print("RETRIEVE — what each policy injects (threshold %.1f)" % thr)
    print("-" * 60)
    print("  query        always-top-1        with-threshold")
    for q, qd in data["queries"].items():
        a_doc, _ = always_top1(qd["vec"], docs, thr)
        t_doc, sim = with_threshold(qd["vec"], docs, thr)
        t_str = t_doc if t_doc else "(abstain)"
        print("  %-11s %-18s %s" % (q, a_doc, t_str))
    print("-" * 60)
    print("  always-top-1 injects a doc for the weather and stock-tip queries; the threshold abstains.")


def junk_injected(data, policy):
    """How many OUT-of-scope queries got a document injected (irrelevant context)."""
    docs, thr = data["docs"], data["threshold"]
    return sum(1 for qd in data["queries"].values()
               if not qd["in_scope"] and policy(qd["vec"], docs, thr)[0] is not None)


def in_scope_covered(data, policy):
    """How many IN-scope queries got their document injected."""
    docs, thr = data["docs"], data["threshold"]
    return sum(1 for qd in data["queries"].values()
               if qd["in_scope"] and policy(qd["vec"], docs, thr)[0] is not None)


def check(data):
    print("SELF-TEST — the threshold abstains on out-of-scope queries while still covering every in-scope one")
    print("-" * 92)
    n_out = sum(1 for qd in data["queries"].values() if not qd["in_scope"])
    n_in = sum(1 for qd in data["queries"].values() if qd["in_scope"])

    always_junk = junk_injected(data, always_top1)
    always_injects_junk = always_junk == n_out
    print("  always-top-1 injects junk on every out-of-scope query = %s (%d of %d)"
          % (always_injects_junk, always_junk, n_out))

    thr_junk = junk_injected(data, with_threshold)
    threshold_no_junk = thr_junk == 0
    print("  the threshold injects junk on none of them = %s (%d of %d)" % (threshold_no_junk, thr_junk, n_out))

    thr_cov = in_scope_covered(data, with_threshold)
    threshold_keeps_coverage = thr_cov == n_in
    print("  the threshold still covers every in-scope query = %s (%d of %d)" % (threshold_keeps_coverage, thr_cov, n_in))

    always_cov = in_scope_covered(data, always_top1)
    same_in_scope = thr_cov == always_cov
    print("  the two policies agree on the in-scope queries = %s (both %d)" % (same_in_scope, thr_cov))

    ok = always_injects_junk and threshold_no_junk and threshold_keeps_coverage and same_in_scope
    print("-" * 92)
    print("SELF-TEST %s  always_injects_junk=%s  threshold_no_junk=%s  threshold_keeps_coverage=%s  same_in_scope=%s"
          % ("PASS" if ok else "FAIL", always_injects_junk, threshold_no_junk, threshold_keeps_coverage, same_in_scope))
    return ok


def main():
    p = argparse.ArgumentParser(description="Put a relevance floor under retrieval so it can return nothing.")
    p.add_argument("--queries", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("queries=%d  docs=%d  threshold=%.1f  file=%s  (the vectors are a fixture)"
          % (len(data["queries"]), len(data["docs"]), data["threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.queries:
        queries_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
