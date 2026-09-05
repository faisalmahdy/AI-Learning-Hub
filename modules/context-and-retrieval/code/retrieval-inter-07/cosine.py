#!/usr/bin/env python3
"""Rank dense retrieval by cosine, not raw dot product -- or vector length outvotes meaning.

Dense retrieval scores a query embedding against document embeddings and returns the closest.
The tempting score is the raw dot product, because it is one multiply-and-add and it is what a
matrix multiply gives you. But the dot product mixes two things: how aligned two vectors are
(their direction, which is meaning) and how long they are (their magnitude, which for an
embedding is mostly an artifact of the text's length and the model's quirks). Rank by dot
product and a long, only-vaguely-related document can outscore a short, perfectly-on-topic one
purely by being big -- magnitude outvoting meaning.

Cosine similarity is the fix: divide the dot product by both vectors' norms, which is the dot
product of the unit-length versions, so only direction survives. On this fixture a big,
loosely-aligned document wins the dot-product ranking while two perfectly-aligned documents --
one of them small -- win the cosine ranking, and the small on-topic document that the dot
product buries at the bottom comes back to the top. This builds both scorers, shows the dot
product crowning an irrelevant document, and shows cosine recovering the relevant ones. The
practical upshot is why every dense index normalizes its vectors: once every vector is unit
length, the dot product and cosine coincide, and the magnitude trap is gone for good.

  --docs     each doc's dot product, norm, and cosine against the query, plus relevance
  --rank     the dot-product ranking vs the cosine ranking, top to bottom
  --check    the dot-product top-1 is irrelevant; the cosine top-1 is relevant

The query and document vectors are the fixture; every dot, norm, and cosine is computed.
Deterministic; stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "vectors.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two scores

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cosine(a, b):
    """Dot product of the unit vectors: alignment only, magnitude divided out."""
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)


def normalize(a):
    n = norm(a)
    return [x / n for x in a] if n else a


# ------------------------------------------------------------- ranking

def rank_by(query, docs, score):
    """Docs sorted best-first by a score(query, vec) function; ties broken by id for determinism."""
    scored = [(d["id"], score(query, d["vec"])) for d in docs]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored


# ----------------------------------------------------------------- printing

def docs_view(data):
    q = data["query"]
    print("DOCS — dot product, norm, and cosine against the query %s" % q)
    print("-" * 66)
    print("  id        vec              dot     norm    cosine   relevant")
    for d in data["docs"]:
        print("  %-9s %-16s %-7.2f %-7.2f %-8.3f %s"
              % (d["id"], str(d["vec"]), dot(q, d["vec"]), norm(d["vec"]),
                 cosine(q, d["vec"]), d["relevant"]))
    print("-" * 66)
    print("  relevance is alignment with the query direction -- which is cosine, not dot.")


def rank_view(data):
    q, docs = data["query"], data["docs"]
    rel = {d["id"]: d["relevant"] for d in docs}
    by_dot = rank_by(q, docs, dot)
    by_cos = rank_by(q, docs, cosine)
    print("RANK — dot-product order vs cosine order (best first)")
    print("-" * 66)
    print("  by dot product:  %s" % [("%s%s" % (i, "*" if rel[i] else "")) for i, _ in by_dot])
    print("  by cosine:       %s" % [("%s%s" % (i, "*" if rel[i] else "")) for i, _ in by_cos])
    print("-" * 66)
    print("  (* = relevant)  the dot product puts the big off-topic doc first; cosine fixes it.")


def check(data):
    print("SELF-TEST — the dot-product top-1 is irrelevant; the cosine top-1 is relevant")
    print("-" * 66)
    q, docs = data["query"], data["docs"]
    rel = {d["id"]: d["relevant"] for d in docs}

    by_dot = rank_by(q, docs, dot)
    by_cos = rank_by(q, docs, cosine)

    dot_top_irrelevant = not rel[by_dot[0][0]]
    print("  dot-product top-1 is NOT relevant = %s (%s)" % (dot_top_irrelevant, by_dot[0][0]))

    cos_top_relevant = rel[by_cos[0][0]]
    print("  cosine top-1 IS relevant = %s (%s)" % (cos_top_relevant, by_cos[0][0]))

    # the small, perfectly-aligned doc: buried by dot, near the top by cosine
    small = data["small_relevant"]
    dot_pos = [i for i, _ in by_dot].index(small)
    cos_pos = [i for i, _ in by_cos].index(small)
    small_rescued = dot_pos >= len(docs) - 1 and cos_pos <= 1
    print("  the small on-topic doc %r: dot rank %d (last), cosine rank %d (top-2) = %s"
          % (small, dot_pos, cos_pos, small_rescued))

    # cosine equals the dot product of the normalized vectors
    d0 = docs[0]
    same = abs(cosine(q, d0["vec"]) - dot(normalize(q), normalize(d0["vec"]))) < 1e-12
    print("  cosine == dot product of the unit vectors = %s" % same)

    ok = dot_top_irrelevant and cos_top_relevant and small_rescued and same
    print("-" * 66)
    print("SELF-TEST %s  dot_top_irrelevant=%s  cos_top_relevant=%s  small_rescued=%s  cosine_is_normdot=%s"
          % ("PASS" if ok else "FAIL", dot_top_irrelevant, cos_top_relevant, small_rescued, same))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dense retrieval: rank by cosine, not raw dot product.")
    p.add_argument("--docs", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  dim=%d  file=%s  (the query and doc vectors are a fixture)"
          % (len(data["docs"]), len(data["query"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.docs:
        docs_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
