"""Compute cosine similarity after subtracting the corpus mean (centering), not on the raw embeddings -- transformer embeddings are anisotropic: they share one dominant direction, so raw cosine is compressed into a narrow high band and a document that merely aligns with the shared direction outranks the true match.

Cosine similarity is supposed to compare direction, and it does normalize away magnitude -- but it does not normalize away a direction that every vector shares. Real embedding spaces are anisotropic: the vectors do not spread over the sphere, they pack into a narrow cone all pointing roughly the same way. So every pair of embeddings already has a high cosine before you compare anything, the scores bunch up in a narrow high band, and the one direction they all share dominates the similarity. A distractor with a large component along that shared direction scores high with the query for the wrong reason -- not because it answers the query, but because it points the same generic way everything does.

Normalizing to unit length does not help, because the shared direction is a direction, not a length: it survives normalization intact. The unit vectors are still clustered in the cone, and cosine still cannot separate them.

The fix removes the shared direction at its source. Estimate it as the corpus mean -- the average of all the document vectors, which points along the cone -- and subtract it from every vector. What remains is each vector's residual: how it differs from the generic direction, which is exactly the distinguishing signal. Cosine on the centered residuals spreads the scores out and ranks by real similarity, so the true match comes first.

On this fixture the shared direction is the first axis, the query's real signal is on the second axis, the true match A shares that signal, and a distractor B has a big first-axis component and little else. Raw cosine (even though it normalizes magnitude) ranks B above A because B aligns better with the dominant first axis; centered cosine ranks A first. This computes both.

  --raw       raw cosine similarity of the query to each candidate, and the resulting ranking and score spread
  --centered  cosine after subtracting the corpus mean, and the resulting ranking and score spread
  --check     raw cosine misranks under anisotropy; centering the vectors corrects the ranking and widens the spread

query, the candidate vectors, and true_match are the fixture; the corpus mean, centered vectors, rankings, and spreads are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "anisotropy.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cosine(a, b):
    """Similarity by direction: the dot product of the unit vectors (magnitude normalized away)."""
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)


def mean_vector(vectors):
    """The corpus mean -- the average document vector, which points along the shared cone."""
    n = len(vectors)
    dims = len(vectors[0])
    return [sum(v[d] for v in vectors) / n for d in range(dims)]


def subtract(a, b):
    """Center a vector: remove the shared direction by subtracting the corpus mean."""
    return [x - y for x, y in zip(a, b)]


def rank_raw(query, candidates):
    """Rank candidates by raw cosine to the query."""
    scored = [(cid, cosine(query, c["vector"])) for cid, c in candidates.items()]
    return sorted(scored, key=lambda p: p[1], reverse=True)


def rank_centered(query, candidates):
    """Rank candidates by cosine after subtracting the corpus mean from the query and every candidate."""
    vectors = [c["vector"] for c in candidates.values()]
    m = mean_vector(vectors)
    q_c = subtract(query, m)
    scored = [(cid, cosine(q_c, subtract(c["vector"], m))) for cid, c in candidates.items()]
    return sorted(scored, key=lambda p: p[1], reverse=True)


def spread(scored):
    """How far apart the top and bottom scores are -- discrimination between candidates."""
    vals = [s for _, s in scored]
    return max(vals) - min(vals)


# ----------------------------------------------------------------- printing

def raw_view(data):
    query, candidates = data["query"], data["candidates"]
    scored = rank_raw(query, candidates)
    print("RAW — cosine similarity of the query to each candidate (no centering)")
    print("-" * 60)
    for cid, s in scored:
        print("  %s  cos = %+.4f   %s" % (cid, s, candidates[cid]["label"]))
    print("-" * 60)
    print("  ranking: %s   spread(top-bottom) = %.4f" % (" > ".join(c for c, _ in scored), spread(scored)))
    print("  the scores bunch in a narrow high band -- the signature of anisotropy")


def centered_view(data):
    query, candidates = data["query"], data["candidates"]
    m = mean_vector([c["vector"] for c in candidates.values()])
    scored = rank_centered(query, candidates)
    print("CENTERED — cosine after subtracting the corpus mean %s" % m)
    print("-" * 60)
    for cid, s in scored:
        print("  %s  cos = %+.4f   %s" % (cid, s, candidates[cid]["label"]))
    print("-" * 60)
    print("  ranking: %s   spread(top-bottom) = %.4f" % (" > ".join(c for c, _ in scored), spread(scored)))
    print("  centering removes the shared direction, so the scores spread out")


def check(data):
    print("SELF-TEST — raw cosine misranks under anisotropy; centering corrects the ranking and widens the spread")
    print("-" * 112)
    query, candidates, true_match = data["query"], data["candidates"], data["true_match"]

    vectors = [c["vector"] for c in candidates.values()]
    m = mean_vector(vectors)
    residual_norms = [norm(subtract(v, m)) for v in vectors]
    avg_residual = sum(residual_norms) / len(residual_norms)
    mean_dominates = norm(m) > avg_residual
    print("  the shared direction is larger than the distinguishing signal = %s (|mean|=%.2f > avg residual %.2f)"
          % (mean_dominates, norm(m), avg_residual))

    raw = rank_raw(query, candidates)
    raw_spread = spread(raw)
    anisotropy_compresses = raw_spread < 0.15 and min(s for _, s in raw) > 0.8
    print("  raw cosines are packed in a narrow high band = %s (spread %.4f, min %.4f)"
          % (anisotropy_compresses, raw_spread, min(s for _, s in raw)))

    raw_misranks = raw[0][0] != true_match
    print("  raw cosine ranks a distractor above the true match = %s (top is %s, true is %s)"
          % (raw_misranks, raw[0][0], true_match))

    centered = rank_centered(query, candidates)
    centering_corrects = centered[0][0] == true_match
    print("  centered cosine ranks the true match first = %s (top is %s)" % (centering_corrects, centered[0][0]))

    centered_spread = spread(centered)
    centering_widens_spread = centered_spread > raw_spread
    print("  centering widens the score spread = %s (%.4f > %.4f)" % (centering_widens_spread, centered_spread, raw_spread))

    ok = (mean_dominates and anisotropy_compresses and raw_misranks
          and centering_corrects and centering_widens_spread)
    print("-" * 112)
    print("SELF-TEST %s  mean_dominates=%s  anisotropy_compresses=%s  raw_misranks=%s  centering_corrects=%s  centering_widens_spread=%s"
          % ("PASS" if ok else "FAIL", mean_dominates, anisotropy_compresses, raw_misranks,
             centering_corrects, centering_widens_spread))
    return ok


def main():
    p = argparse.ArgumentParser(description="Anisotropy / centering: compute cosine similarity after subtracting the corpus mean, not on the raw embeddings, because embeddings are anisotropic -- they share one dominant direction that survives normalization, compresses all cosines into a narrow high band, and lets a document aligned with the shared direction outrank the true match.")
    p.add_argument("--raw", action="store_true")
    p.add_argument("--centered", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  candidates=%s  true_match=%s  file=%s  (these are a fixture)"
          % (data["query"], list(data["candidates"].keys()), data["true_match"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.raw:
        raw_view(data)
    elif args.centered:
        centered_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
