"""Decompose a multi-aspect query into one sub-query per aspect, don't embed it as a single vector -- a compound query's single embedding lands at the midpoint between its aspects, where it ranks a document that is weakly about both above the documents that thoroughly cover one aspect each, so single-vector retrieval returns a shallow compromise and misses the sources that actually answer the question.

A dense retriever turns a query into one vector and ranks documents by cosine similarity. That is exactly right for a query with one information need. A query with two independent needs -- 'compare the side effects of drug A and drug B', 'what are the pricing and the SLA of plan X' -- breaks the assumption, because its single embedding is roughly the average of the two aspect directions and sits between them.

At that midpoint the geometry works against you. A document that thoroughly covers aspect A points in the A direction, so it is only moderately similar to the midpoint. A document that is weakly about both aspects points near the midpoint itself, so it scores highest -- even though it answers neither aspect well. The top result is a vague passage that mentions both, and the two documents that actually contain each aspect's answer rank below it. Retrieve a few and you get the compromise plus, at best, one aspect; the other aspect's source never makes the cut.

The fix is to decompose: split the compound query into a sub-query per aspect, retrieve for each independently, and union the results. Each aspect's strong document is now retrieved by a sub-query pointing straight at it, so both answer sources are recovered. This is distinct from multi-hop retrieval, where the aspects are chained through a bridge entity and must be resolved in sequence; here the aspects are independent parallel needs, and the sub-queries can run at once.

On this fixture the two aspects are orthogonal directions and the compound query is their sum. Single-vector retrieval ranks the weakly-both document first (cosine 1.0) and the two strong single-aspect documents below it (0.707 each), so the top-2 covers only one aspect. Decomposed retrieval pulls the strong A document with sub-query A and the strong B document with sub-query B, covering both. This computes both.

  --single   single-vector retrieval with the compound query: the weak-both doc wins, coverage is incomplete
  --decompose  one sub-query per aspect, merged: each aspect's strong doc is retrieved, coverage is complete
  --check    single-vector ranks the weak-both doc above the strong single-aspect docs and its top-k misses an aspect, while decomposition covers both aspects

the aspect directions, the compound query, the documents, and top_k are the fixture; every similarity, ranking, retrieved set, and aspect coverage is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "multiaspect.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(a, b):
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def rank(query, documents):
    """Documents by descending cosine similarity to the query."""
    scored = [(d["id"], cosine(query, d["embedding"])) for d in documents]
    return sorted(scored, key=lambda t: t[1], reverse=True)


def retrieve_single(query, documents, k):
    """Single-vector retrieval: the top-k documents by similarity to the one compound query."""
    return [doc_id for doc_id, _s in rank(query, documents)[:k]]


def retrieve_decomposed(sub_queries, documents):
    """Decomposed retrieval: the top-1 document for each sub-query, unioned (order preserved)."""
    out = []
    for q in sub_queries:
        top = rank(q, documents)[0][0]
        if top not in out:
            out.append(top)
    return out


def coverage(doc_ids, documents):
    """The set of aspects thoroughly covered by a set of retrieved documents."""
    by_id = {d["id"]: d for d in documents}
    covered = set()
    for i in doc_ids:
        covered.update(by_id[i]["covers"])
    return covered


# ----------------------------------------------------------------- printing

def single_view(d):
    q = d["compound_query"]
    print("SINGLE — one compound query vector %s, top-%d" % (q, d["top_k"]))
    print("-" * 64)
    for doc_id, s in rank(q, d["documents"]):
        print("  %-14s cosine %.3f" % (doc_id, s))
    got = retrieve_single(q, d["documents"], d["top_k"])
    print("  retrieved: %s   aspects covered: %s" % (got, sorted(coverage(got, d["documents"])) or "none"))
    print("-" * 64)
    print("  the weakly-both doc sits at the query midpoint and wins; an aspect's strong doc is missed")


def decompose_view(d):
    subs = [d["aspect_a"], d["aspect_b"]]
    print("DECOMPOSE — one sub-query per aspect: %s and %s" % (d["aspect_a"], d["aspect_b"]))
    print("-" * 64)
    for label, q in zip(("aspect A", "aspect B"), subs):
        print("  %s top: %s" % (label, rank(q, d["documents"])[0][0]))
    got = retrieve_decomposed(subs, d["documents"])
    print("  merged: %s   aspects covered: %s" % (got, sorted(coverage(got, d["documents"])) or "none"))
    print("-" * 64)
    print("  each sub-query points straight at one aspect's strong doc, so both are retrieved")


def check(d):
    print("SELF-TEST — single-vector ranks the weak-both doc above the strong single-aspect docs and its top-k misses an aspect, while decomposition covers both aspects")
    print("-" * 112)
    q = d["compound_query"]
    subs = [d["aspect_a"], d["aspect_b"]]
    both_aspects = {"A", "B"}

    ranking = rank(q, d["documents"])
    top_id = ranking[0][0]
    weakboth_ranked_first = top_id == "doc_both_weak"
    print("  the compound query ranks the weakly-both doc first = %s (%s at %.3f)" % (weakboth_ranked_first, top_id, ranking[0][1]))

    single_got = retrieve_single(q, d["documents"], d["top_k"])
    single_cov = coverage(single_got, d["documents"])
    single_misses = single_cov != both_aspects
    print("  single-vector top-%d does NOT cover both aspects = %s (covers %s)" % (d["top_k"], single_misses, sorted(single_cov) or "none"))

    dec_got = retrieve_decomposed(subs, d["documents"])
    dec_cov = coverage(dec_got, d["documents"])
    decompose_covers_both = dec_cov == both_aspects
    print("  decomposed retrieval covers both aspects = %s (covers %s)" % (decompose_covers_both, sorted(dec_cov)))

    strong_below_weak = dict(ranking)["doc_a"] < dict(ranking)["doc_both_weak"] and dict(ranking)["doc_b"] < dict(ranking)["doc_both_weak"]
    print("  both strong single-aspect docs score below the weak-both doc = %s (A %.3f, B %.3f < %.3f)"
          % (strong_below_weak, dict(ranking)["doc_a"], dict(ranking)["doc_b"], dict(ranking)["doc_both_weak"]))

    ok = (weakboth_ranked_first and single_misses and decompose_covers_both and strong_below_weak)
    print("-" * 112)
    print("SELF-TEST %s  weakboth_ranked_first=%s  single_misses=%s  decompose_covers_both=%s  strong_below_weak=%s"
          % ("PASS" if ok else "FAIL", weakboth_ranked_first, single_misses, decompose_covers_both, strong_below_weak))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multi-aspect query decomposition: split a query with two independent information needs into one sub-query per aspect and merge the results, because a single compound-query embedding lands at the midpoint between the aspects, where a document weakly about both outranks the documents that thoroughly cover one aspect each -- so single-vector retrieval returns a shallow compromise and misses an aspect's answer source; distinct from multi-hop, where aspects chain through a bridge entity.")
    p.add_argument("--single", action="store_true")
    p.add_argument("--decompose", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("compound_query=%s  top_k=%d  documents=%d  file=%s"
          % (d["compound_query"], d["top_k"], len(d["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.single:
        single_view(d)
    elif args.decompose:
        decompose_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
