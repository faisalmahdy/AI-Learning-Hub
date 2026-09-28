"""Sort retrieval results in the direction that matches the index's metric -- smallest-first for a distance, largest-first for a similarity -- because a vector index returns one or the other, and sorting a distance the way you sort a similarity returns the farthest, least-relevant documents.

A vector index answers a query with a number per document, and that number is one of two opposite kinds. A similarity -- cosine, inner product -- is larger when the document is more relevant. A distance -- Euclidean L2, or one minus cosine -- is smaller when the document is more relevant. The two run in opposite directions, so the correct sort direction depends entirely on which one the index handed you.

The trap is that many indexes return a distance by default -- FAISS's flat and IVF indexes return squared L2 distance -- and a distance is still just a float, so it is easy to treat it as a score and sort descending to take the 'top' results. Sorting a distance descending takes the largest distances, which are the farthest documents: the least relevant ones, in exactly reversed order. The mirror mistake, sorting a similarity ascending, does the same damage from the other side.

The failure is silent, which is what makes it dangerous. The retriever still returns k results, each with a real number attached, through the same interface a correct retriever uses -- they are simply the worst k matches instead of the best. Downstream, the model reads confidently-scored but irrelevant context and answers from it, and nothing signals that the ranking was inverted.

The fix is to know your index's metric and sort to match it: ascending (smallest first) for a distance, descending (largest first) for a similarity. When in doubt, check with a document you know is a perfect match -- it must come out on top -- because the metric's direction is a property of the index you must confirm, not assume.

On this fixture the four documents carry both a distance and a similarity to the query. Sorted correctly, the reset guide (distance 0.2, similarity 0.95) is first and the shipping info (distance 1.4, similarity 0.10) last; sorting the distance as if it were a similarity puts shipping info first and reverses the whole list. This computes both.

  --scores    each document's distance and similarity to the query
  --rank      the correct top-k vs the ranking you get sorting the distance the wrong way
  --check     sorting a distance descending returns the farthest documents, exactly reversing the correct order

query and the per-document distance and similarity are the fixture; the correct ranking, the reversed ranking, and the top picks are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "distsign.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rank_by_distance(docs):
    """Correct for a distance metric: smallest distance first (nearest = most relevant)."""
    return sorted(docs, key=lambda d: docs[d]["distance"])


def rank_by_similarity(docs):
    """Correct for a similarity metric: largest similarity first."""
    return sorted(docs, key=lambda d: docs[d]["similarity"], reverse=True)


def distance_sorted_as_similarity(docs):
    """The bug: treat the distance as a score and sort it descending -- largest distance first."""
    return sorted(docs, key=lambda d: docs[d]["distance"], reverse=True)


# ----------------------------------------------------------------- printing

def scores_view(data):
    docs = data["docs"]
    print("SCORES — distance (lower better) and similarity (higher better) to the query")
    print("-" * 56)
    print("  document        distance   similarity")
    for d in rank_by_distance(docs):
        print("  %-14s  %-9.2f  %.2f" % (d, docs[d]["distance"], docs[d]["similarity"]))
    print("-" * 56)
    print("  the two metrics run in opposite directions")


def rank_view(data):
    docs = data["docs"]
    correct = rank_by_distance(docs)
    buggy = distance_sorted_as_similarity(docs)
    print("RANK — correct (distance ascending) vs distance sorted as a similarity")
    print("-" * 56)
    print("  correct top-k : %s" % correct)
    print("  buggy   top-k : %s" % buggy)
    print("-" * 56)
    print("  the buggy sort returns the farthest documents first -- the least relevant")


def check(data):
    print("SELF-TEST — sorting a distance descending returns the farthest documents, exactly reversing the correct order")
    print("-" * 112)
    docs = data["docs"]
    correct = rank_by_distance(docs)
    buggy = distance_sorted_as_similarity(docs)

    nearest = min(docs, key=lambda d: docs[d]["distance"])
    farthest = max(docs, key=lambda d: docs[d]["distance"])

    correct_top_is_nearest = correct[0] == nearest
    print("  the correct top result is the nearest document = %s (%s, distance %.2f)" % (correct_top_is_nearest, correct[0], docs[correct[0]]["distance"]))

    buggy_top_is_farthest = buggy[0] == farthest
    print("  the buggy top result is the farthest document = %s (%s, distance %.2f)" % (buggy_top_is_farthest, buggy[0], docs[buggy[0]]["distance"]))

    ranking_reversed = buggy == correct[::-1]
    print("  the buggy ranking is the exact reverse of the correct one = %s" % ranking_reversed)

    distance_and_similarity_agree = rank_by_distance(docs) == rank_by_similarity(docs)
    print("  distance-ascending and similarity-descending give the same correct order = %s" % distance_and_similarity_agree)

    buggy_top_is_least_relevant = docs[buggy[0]]["similarity"] == min(docs[d]["similarity"] for d in docs)
    print("  the buggy top result has the lowest similarity of all = %s (similarity %.2f)" % (buggy_top_is_least_relevant, docs[buggy[0]]["similarity"]))

    ok = (correct_top_is_nearest and buggy_top_is_farthest and ranking_reversed
          and distance_and_similarity_agree and buggy_top_is_least_relevant)
    print("-" * 112)
    print("SELF-TEST %s  correct_top_is_nearest=%s  buggy_top_is_farthest=%s  ranking_reversed=%s  distance_and_similarity_agree=%s  buggy_top_is_least_relevant=%s"
          % ("PASS" if ok else "FAIL", correct_top_is_nearest, buggy_top_is_farthest, ranking_reversed,
             distance_and_similarity_agree, buggy_top_is_least_relevant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Distance vs similarity: sort retrieval results in the direction that matches the index's metric -- smallest-first for a distance, largest-first for a similarity -- because sorting a distance the way you sort a similarity returns the farthest, least-relevant documents in reversed order.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%r  docs=%s  file=%s  (these are a fixture)" % (data["query"], list(data["docs"].keys()), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
