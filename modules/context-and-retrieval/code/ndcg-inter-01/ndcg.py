"""Score retrieval ranking with nDCG, not a set metric like recall -- recall counts only whether relevant items were retrieved, so two rankings of the same set score identically even when one puts the best result first and the other buries it last; nDCG rewards putting the most relevant results at the top.

Retrieval quality has two parts: did you fetch the relevant items, and did you order them well. Recall and hit-rate measure only the first. They treat the result list as a set, so a ranking that returns the perfect answer at position 1 and a ranking that returns the same perfect answer at position 10 look identical -- both "retrieved" it. For anything a person or a model reads top-down, that is the wrong thing to measure, because position is most of the value.

nDCG measures both parts at once. It starts from graded relevance -- a result is not just relevant or not, it is exactly right, useful, marginal, or irrelevant, a score not a flag. It then discounts each result's relevance by its rank, dividing the gain by the logarithm of the position, so a highly relevant result earns much more at rank 1 than at rank 4. Summing the discounted gains gives DCG, the discounted cumulative gain of this ordering.

The 'n' normalizes it. DCG on its own is not comparable across queries -- a query with more relevant documents can score higher just for having more to find -- so nDCG divides DCG by IDCG, the DCG of the ideal ordering (the same items sorted best-first). The result is in 0 to 1, where 1 means the ranking is already optimal and lower means relevant results are sitting below where they should be. That single number rewards both retrieving the right things and ordering them well.

A set metric cannot do this by construction. Because it ignores order, it assigns the same recall to the best possible ordering and the worst possible ordering of an identical retrieved set, so it is blind to exactly the ranking quality that matters most for a top-down reader.

The rule: evaluate retrieval ranking with nDCG -- graded relevance discounted by position and normalized by the ideal ordering -- not with an order-blind set metric like recall, because two rankings that retrieve the same items score identically under recall while nDCG correctly ranks the one that puts the most relevant results highest above the one that buries them.

On this fixture two orderings retrieve the identical set of four graded results; recall is the same for both, but the good ordering (best first) scores nDCG 1.0 while the bad ordering (best last) scores about 0.61. This computes both.

  --dcg      each ordering's per-rank discounted gain, its DCG, and the ideal DCG
  --score    each ordering's nDCG next to the order-blind recall, showing recall cannot tell them apart
  --check    recall is identical for both orderings; nDCG rewards the one that ranks relevant results highest

the orderings (graded relevance per rank) are the fixture; the DCG, IDCG, nDCG, and recall are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ndcg.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dcg(relevances):
    """Discounted cumulative gain: each relevance divided by log2 of its (1-based) rank + 1."""
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevances, start=1))


def ndcg(relevances):
    """Normalize DCG by the DCG of the ideal (best-first) ordering of the same relevances."""
    ideal = dcg(sorted(relevances, reverse=True))
    return dcg(relevances) / ideal if ideal else 0.0


def recall(relevances):
    """Order-blind: the fraction of relevant items (relevance > 0) present in the set."""
    total_relevant = sum(1 for r in relevances if r > 0)
    return total_relevant / len(relevances)


# ----------------------------------------------------------------- printing

def dcg_view(data):
    orders = data["orderings"]
    print("DCG — per-rank discounted gain for each ordering")
    print("-" * 58)
    for name, rels in orders.items():
        print("  %s ordering: relevances %s" % (name, rels))
        for rank, rel in enumerate(rels, start=1):
            print("    rank %d: %d / log2(%d) = %.3f" % (rank, rel, rank + 1, rel / math.log2(rank + 1)))
        print("    DCG = %.3f   (ideal DCG = %.3f)" % (dcg(rels), dcg(sorted(rels, reverse=True))))
    print("-" * 58)
    print("  a relevant result earns more the higher it sits")


def score_view(data):
    orders = data["orderings"]
    print("SCORE — nDCG vs order-blind recall")
    print("-" * 50)
    print("  ordering   recall   nDCG")
    for name, rels in orders.items():
        print("  %-9s  %-6.2f   %.3f" % (name, recall(rels), ndcg(rels)))
    print("-" * 50)
    print("  recall is identical; nDCG separates the good ordering from the bad")


def check(data):
    print("SELF-TEST — recall is identical for both orderings; nDCG rewards the one that ranks relevant results highest")
    print("-" * 112)
    orders = data["orderings"]
    good, bad = orders["good"], orders["bad"]

    same_set = sorted(good) == sorted(bad)
    print("  both orderings retrieve the identical set of items = %s" % same_set)

    recall_identical = recall(good) == recall(bad)
    print("  recall is the same for both orderings = %s (%.2f == %.2f)" % (recall_identical, recall(good), recall(bad)))

    ndcg_distinguishes = ndcg(good) > ndcg(bad)
    print("  nDCG scores the good ordering above the bad = %s (%.3f > %.3f)" % (ndcg_distinguishes, ndcg(good), ndcg(bad)))

    good_is_ideal = abs(ndcg(good) - 1.0) < 1e-9
    print("  the best-first ordering scores the ideal nDCG of 1.0 = %s" % good_is_ideal)

    bad_below_one = ndcg(bad) < 1.0
    print("  the buried ordering scores below 1.0 = %s (%.3f)" % (bad_below_one, ndcg(bad)))

    ok = (same_set and recall_identical and ndcg_distinguishes and good_is_ideal and bad_below_one)
    print("-" * 112)
    print("SELF-TEST %s  same_set=%s  recall_identical=%s  ndcg_distinguishes=%s  good_is_ideal=%s  bad_below_one=%s"
          % ("PASS" if ok else "FAIL", same_set, recall_identical, ndcg_distinguishes, good_is_ideal, bad_below_one))
    return ok


def main():
    p = argparse.ArgumentParser(description="nDCG: evaluate retrieval ranking with nDCG -- graded relevance discounted by position and normalized by the ideal ordering -- not with an order-blind set metric like recall, because two rankings that retrieve the same items score identically under recall while nDCG correctly ranks the one that puts the most relevant results highest above the one that buries them.")
    p.add_argument("--dcg", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("orderings=%d  results_each=%d  file=%s  (the graded relevances are a fixture)"
          % (len(data["orderings"]), len(next(iter(data["orderings"].values()))), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.dcg:
        dcg_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
