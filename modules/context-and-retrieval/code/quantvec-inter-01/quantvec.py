"""Rescore the quantized search's top candidates with exact vectors -- quantization is cheap but misranks close neighbors.

Storing every document's embedding at full precision is expensive: a corpus of millions of documents, each a vector of
hundreds of 32-bit floats, is gigabytes of memory, and scanning it for every query is slow. A standard fix is
QUANTIZATION -- store the vectors at lower precision (round each component to an 8-bit integer, or even a single bit),
shrinking the index several-fold and speeding up the distance computations. The catch is that rounding is lossy: two
vectors that were slightly different at full precision can round to the same or crossed values, so distances computed on
the quantized vectors are approximate, and the approximation is worst exactly where it matters -- among documents that are
CLOSE to the query, whose true distances differ by less than the rounding step. There, quantization can flip the order, so
the quantized search's top result is not actually the nearest neighbor.

The failure looks like a normal result: the quantized search returns a document, ranked first by its quantized distance,
and it is a plausible neighbor -- just not the closest one, because the rounding error was larger than the gap between the
true nearest and a runner-up. Trusting the quantized ranking directly therefore returns slightly-wrong nearest neighbors,
which for retrieval means the best passage loses to a nearly-as-good one on a rounding artifact.

The fix is a TWO-STAGE search: use the cheap quantized index to fetch a CANDIDATE SET -- the top-k by quantized distance,
with k larger than the number you ultimately want -- and then RE-SCORE just those few candidates with the exact,
full-precision vectors, ranking the final answer by exact distance. The quantized stage does not need to get the order
right; it only needs to be good enough to pull the true nearest neighbor somewhere into the candidate set (high recall at
k), which it usually is, because its errors reorder close neighbors but rarely eject them entirely. The exact stage then
fixes the order precisely, at the cost of a handful of full-precision distance computations instead of millions. You keep
quantization's memory and speed for the corpus-wide scan and pay for exactness only on the short list.

The rule: search a quantized (low-precision) vector index to fetch a candidate set, then re-score those candidates with the
exact full-precision vectors and rank by exact distance, because quantization's rounding error misranks close neighbors --
so the quantized top result is not reliably the nearest -- but the candidate set still contains the true nearest, which
exact rescoring recovers cheaply.

On this fixture the true nearest document is d1 (exact distance 0.1), but rounding puts d2 in the query's integer bucket
(quantized distance 0) and rounds d1 away (quantized distance 1), so the quantized search ranks d2 first -- wrong. The
quantized top-2 candidate set still includes d1, and rescoring it exactly returns d1. This computes both.

  --search    the exact distances (true nearest) vs the quantized distances (misranked top-1), for every document
  --twostage  the quantized candidate set (top-k), then exact rescoring of those candidates to the correct nearest
  --check     the quantized search misranks the nearest neighbor; two-stage rescoring recovers it from the candidate set

query, documents, and candidate_k are the fixture; every quantized vector, distance, and ranking is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "quantvec.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def distance(a, b):
    """Euclidean distance between two vectors."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def quantize(vec):
    """Low-precision storage: round each component to the nearest integer."""
    return [round(x) for x in vec]


def exact_ranking(query, docs):
    """Documents ranked by exact (full-precision) distance, nearest first."""
    return sorted(docs, key=lambda d: (distance(query, docs[d]), d))


def quantized_ranking(query, docs):
    """Documents ranked by distance between the quantized query and quantized doc vectors."""
    q = quantize(query)
    return sorted(docs, key=lambda d: (distance(q, quantize(docs[d])), d))


def two_stage(query, docs, k):
    """Fetch the top-k candidates by quantized distance, then re-rank them by exact distance."""
    candidates = quantized_ranking(query, docs)[:k]
    rescored = sorted(candidates, key=lambda d: (distance(query, docs[d]), d))
    return candidates, rescored


# ----------------------------------------------------------------- printing

def search_view(data):
    q, docs = data["query"], data["documents"]
    qq = quantize(q)
    print("SEARCH — exact vs quantized distances (query %s, quantized %s)" % (q, qq))
    print("-" * 70)
    print("  doc   vector       quantized   exact-dist   quantized-dist")
    for d in docs:
        print("  %-5s %-12s %-11s %-12.2f %.2f" % (d, docs[d], quantize(docs[d]), distance(q, docs[d]), distance(qq, quantize(docs[d]))))
    print("-" * 70)
    print("  exact nearest: %s ; quantized nearest: %s" % (exact_ranking(q, docs)[0], quantized_ranking(q, docs)[0]))


def twostage_view(data):
    q, docs, k = data["query"], data["documents"], data["candidate_k"]
    candidates, rescored = two_stage(q, docs, k)
    print("TWOSTAGE — quantized candidate set, then exact rescoring")
    print("-" * 62)
    print("  stage 1 (quantized) top-%d candidates: %s" % (k, candidates))
    print("  stage 2 (exact rescore of candidates):")
    for d in rescored:
        print("    %-5s exact distance %.2f" % (d, distance(q, docs[d])))
    print("-" * 62)
    print("  final nearest = %s (the true nearest, recovered by rescoring)" % rescored[0])


def check(data):
    print("SELF-TEST — the quantized search misranks the nearest neighbor; two-stage rescoring recovers it from the candidate set")
    print("-" * 118)
    q, docs, k = data["query"], data["documents"], data["candidate_k"]
    exact = exact_ranking(q, docs)
    quant = quantized_ranking(q, docs)
    candidates, rescored = two_stage(q, docs, k)
    true_nearest = exact[0]

    quantized_misranks = quant[0] != true_nearest
    print("  the quantized search's top-1 is NOT the true nearest = %s (quantized %s, true %s)" % (quantized_misranks, quant[0], true_nearest))

    true_nearest_in_candidates = true_nearest in candidates
    print("  the true nearest is still in the quantized candidate set = %s (%s in %s)" % (true_nearest_in_candidates, true_nearest, candidates))

    rescoring_recovers = rescored[0] == true_nearest
    print("  exact rescoring of the candidates recovers the true nearest = %s (%s)" % (rescoring_recovers, rescored[0]))

    far_doc_excluded = exact[-1] not in candidates
    print("  the far document is excluded by the quantized stage = %s (%s not in candidates)" % (far_doc_excluded, exact[-1]))

    exact_gap_below_rounding = distance(q, docs[exact[1]]) - distance(q, docs[exact[0]]) < 1.0
    print("  the true nearest and runner-up differ by less than the rounding step = %s (%.2f gap)"
          % (exact_gap_below_rounding, distance(q, docs[exact[1]]) - distance(q, docs[exact[0]])))

    ok = quantized_misranks and true_nearest_in_candidates and rescoring_recovers and far_doc_excluded and exact_gap_below_rounding
    print("-" * 118)
    print("SELF-TEST %s  quantized_misranks=%s  true_nearest_in_candidates=%s  rescoring_recovers=%s  far_doc_excluded=%s  exact_gap_below_rounding=%s"
          % ("PASS" if ok else "FAIL", quantized_misranks, true_nearest_in_candidates, rescoring_recovers, far_doc_excluded, exact_gap_below_rounding))
    return ok


def main():
    p = argparse.ArgumentParser(description="Quantized-vector rescoring: search a quantized (low-precision) vector index to fetch a candidate set, then re-score those candidates with the exact full-precision vectors and rank by exact distance, because quantization's rounding error misranks close neighbors (so the quantized top result is not reliably the nearest) but the candidate set still contains the true nearest, which exact rescoring recovers cheaply.")
    p.add_argument("--search", action="store_true")
    p.add_argument("--twostage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  documents=%d  candidate_k=%d  file=%s  (the query, docs, and candidate size are a fixture)"
          % (data["query"], len(data["documents"]), data["candidate_k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.search:
        search_view(data)
    elif args.twostage:
        twostage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
