"""Rank by direction (cosine), not raw dot product -- an unnormalized vector's magnitude outranks a better match.

Vector search works because an embedding turns meaning into direction: two texts that mean the same thing get vectors
that point the same way, so you retrieve by finding the document vector most aligned with the query vector. 'Most aligned'
means the smallest angle, which is cosine similarity -- the dot product DIVIDED BY the two vectors' magnitudes, so it
depends only on direction and lives in [-1, 1]. The trap is using the raw dot product instead, without normalizing. The
dot product is alignment TIMES magnitude, so it rewards a vector for being long as well as for pointing the right way,
and a document whose embedding happens to have a large magnitude can outscore a document that is genuinely more aligned
with the query. Magnitude is usually incidental -- it tracks things like document length or token frequency, not
relevance -- so ranking by dot product on unnormalized vectors quietly biases retrieval toward long or high-norm
documents regardless of what they are about.

The fix is to normalize the vectors to unit length (divide each by its magnitude) before comparing, or equivalently to
use cosine similarity directly. Once every vector has magnitude 1, the dot product and the cosine are the same number, so
the magnitude bias is gone and ranking is purely by direction. Most embedding pipelines normalize at index time for
exactly this reason; the ones that use raw dot product do so only because their model was trained to produce unit-norm
embeddings already, which is the same condition by another name. The rule: compare directions, so either store unit
vectors or divide out the norms -- never rank by the bare dot product of vectors whose magnitudes you do not control.

On this fixture the query is [1, 0]. doc_aligned = [1, 0.1] points almost exactly along the query (cosine 0.995) but is
short. doc_offaxis = [2.1, 2.1] points 45 degrees off (cosine 0.707) but is three times longer. Raw dot product scores
doc_offaxis 2.1 versus doc_aligned 1.0, so it ranks the off-axis document first -- the wrong one. Cosine scores
doc_aligned 0.995 versus doc_offaxis 0.707, ranking the aligned document first. Normalizing the vectors makes the dot
product equal the cosine. This computes all of it.

  --rank      each document's dot product, magnitude, and cosine -- dot ranks the long off-axis doc first, cosine the aligned one
  --normalize normalize both vectors to unit length; the dot product now equals the cosine and the ranking is correct
  --check     the dot product ranks the higher-magnitude off-axis doc first; cosine ranks the aligned gold doc first; normalized dot equals cosine

The vectors are the fixture; every dot product, norm, and cosine is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cosine.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def norm(u):
    return math.sqrt(dot(u, u))


def cosine(u, v):
    return dot(u, v) / (norm(u) * norm(v))


def unit(u):
    n = norm(u)
    return [x / n for x in u]


def rank_by(scores):
    """Doc ids sorted by score, highest first."""
    return sorted(scores, key=lambda d: scores[d], reverse=True)


# ----------------------------------------------------------------- printing

def rank_view(data):
    q, docs = data["query"], data["docs"]
    print("RANK — dot product vs cosine for query %s" % q)
    print("-" * 62)
    print("  doc           dot     |vector|   cosine")
    for name, v in docs.items():
        print("  %-12s  %-6.2f  %-9.3f  %.3f" % (name, dot(q, v), norm(v), cosine(q, v)))
    print("-" * 62)
    dot_rank = rank_by({d: dot(q, docs[d]) for d in docs})
    cos_rank = rank_by({d: cosine(q, docs[d]) for d in docs})
    print("  ranked by dot product : %s   (top = %s)" % (dot_rank, dot_rank[0]))
    print("  ranked by cosine      : %s   (top = %s, the gold %s)" % (cos_rank, cos_rank[0], data["gold"]))


def normalize_view(data):
    q, docs = data["query"], data["docs"]
    qn = unit(q)
    print("NORMALIZE — unit-length vectors: dot product becomes cosine")
    print("-" * 60)
    print("  doc           dot(raw)   dot(normalized)   cosine")
    for name, v in docs.items():
        print("  %-12s  %-8.3f   %-15.3f   %.3f" % (name, dot(q, v), dot(qn, unit(v)), cosine(q, v)))
    print("-" * 60)
    print("  after normalizing, dot(normalized) == cosine, so ranking is by direction only.")


def check(data):
    print("SELF-TEST — dot ranks the higher-magnitude off-axis doc first; cosine ranks the aligned gold doc first; normalized dot equals cosine")
    print("-" * 128)
    q, docs, gold = data["query"], data["docs"], data["gold"]
    off = next(d for d in docs if d != gold)

    dot_rank = rank_by({d: dot(q, docs[d]) for d in docs})
    dot_ranks_offaxis = dot_rank[0] == off
    print("  the raw dot product ranks the off-axis doc first = %s (top = %s)" % (dot_ranks_offaxis, dot_rank[0]))

    cos_rank = rank_by({d: cosine(q, docs[d]) for d in docs})
    cosine_ranks_gold = cos_rank[0] == gold
    print("  cosine ranks the aligned gold doc first = %s (top = %s)" % (cosine_ranks_gold, cos_rank[0]))

    gold_more_aligned = cosine(q, docs[gold]) > cosine(q, docs[off])
    print("  the gold doc is more aligned (higher cosine) = %s (%.3f > %.3f)"
          % (gold_more_aligned, cosine(q, docs[gold]), cosine(q, docs[off])))

    offaxis_higher_magnitude = norm(docs[off]) > norm(docs[gold])
    print("  the off-axis doc has the larger magnitude = %s (%.3f > %.3f)"
          % (offaxis_higher_magnitude, norm(docs[off]), norm(docs[gold])))

    qn = unit(q)
    normalized_dot_is_cosine = all(abs(dot(qn, unit(docs[d])) - cosine(q, docs[d])) < 1e-12 for d in docs)
    print("  normalizing makes the dot product equal the cosine = %s" % normalized_dot_is_cosine)

    ok = dot_ranks_offaxis and cosine_ranks_gold and gold_more_aligned and offaxis_higher_magnitude and normalized_dot_is_cosine
    print("-" * 128)
    print("SELF-TEST %s  dot_ranks_offaxis=%s  cosine_ranks_gold=%s  gold_more_aligned=%s  offaxis_higher_magnitude=%s  normalized_dot_is_cosine=%s"
          % ("PASS" if ok else "FAIL", dot_ranks_offaxis, cosine_ranks_gold, gold_more_aligned, offaxis_higher_magnitude, normalized_dot_is_cosine))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cosine vs dot product: semantic similarity is the angle between embeddings, so vector search must rank by cosine (dot product divided by magnitudes) or on normalized vectors; ranking by raw dot product rewards vector magnitude, letting a longer but less-aligned document outrank a more relevant one.")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  docs=%s  gold=%s  file=%s  (the vectors are a fixture)"
          % (data["query"], {d: data["docs"][d] for d in data["docs"]}, data["gold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rank:
        rank_view(data)
    elif args.normalize:
        normalize_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
