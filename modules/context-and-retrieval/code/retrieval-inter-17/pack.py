"""Pack the context by score-per-token, or one fat high-score chunk crowds out two lean ones.

Retrieval hands you more chunks than fit. The context window is a fixed token budget, so you must
select a subset. The obvious rule -- "keep the highest-scoring chunks" -- is greedy by raw relevance
score, and it quietly wastes the budget: a single long, top-scoring chunk can eat most of the window
and block two shorter chunks whose combined relevance is higher. You paid for a big window and filled
it with less relevance than it could hold.

The fix is to rank by value density -- score per token -- not by raw score. A chunk that is only
slightly less relevant but half the length earns its place, because it leaves room for another chunk
after it. Greedy-by-density is the fractional-knapsack heuristic; on realistic chunk sets it packs
more total relevance into the same budget than greedy-by-score, and here it matches the exhaustive
optimum. It is not guaranteed optimal for the 0/1 knapsack in general, but it dominates the naive
"top scores win" rule that most first-cut retrieval pipelines ship.

On this fixture the budget is 10 tokens. Chunk A scores 10 but costs 9 tokens; B and C each score
5-6 for 5 tokens. Greedy-by-score takes A (score 10) and nothing else fits. Greedy-by-density takes
B then C (score 11) and fills the budget exactly. Same chunks, same budget; density wins by 1. This
computes both, plus the brute-force optimum.

  --pack       what greedy-by-score vs greedy-by-density each select, and the total relevance
  --optimum    the exhaustive best subset under the budget, to judge the two heuristics against
  --check      greedy-by-score wastes budget; density packs more relevance and matches the optimum

The chunks, scores, lengths, and budget are the fixture; every selection is computed. Stdlib only.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chunks.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def greedy(chunks, budget, key):
    """Take chunks in descending order of key(name), skipping any that would overflow the budget."""
    order = sorted(chunks, key=lambda n: key(n), reverse=True)
    picked, used = [], 0
    for n in order:
        if used + chunks[n]["tokens"] <= budget:
            picked.append(n)
            used += chunks[n]["tokens"]
    return picked, used


def total_score(chunks, picked):
    return sum(chunks[n]["score"] for n in picked)


def by_score(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"])


def by_density(chunks):
    return greedy(chunks, LOADED["budget"], lambda n: chunks[n]["score"] / chunks[n]["tokens"])


def optimum(chunks, budget):
    """Exhaustive best subset: the highest total score whose tokens fit the budget."""
    best, best_score = [], -1
    names = list(chunks)
    for r in range(len(names) + 1):
        for combo in itertools.combinations(names, r):
            used = sum(chunks[n]["tokens"] for n in combo)
            sc = sum(chunks[n]["score"] for n in combo)
            if used <= budget and sc > best_score:
                best, best_score = list(combo), sc
    return best, best_score


# ----------------------------------------------------------------- printing

def pack_view(data):
    chunks, budget = data["chunks"], data["budget"]
    print("PACK — select chunks under a %d-token budget" % budget)
    print("-" * 64)
    print("  chunk   score   tokens   score/token")
    for n in sorted(chunks, key=lambda n: chunks[n]["score"] / chunks[n]["tokens"], reverse=True):
        c = chunks[n]
        print("  %-6s  %5d   %5d    %8.3f" % (n, c["score"], c["tokens"], c["score"] / c["tokens"]))
    print("-" * 64)
    ps, us = by_score(chunks)
    pd, ud = by_density(chunks)
    print("  by score:     %-12s tokens %2d/%d   total relevance %d" % (" ".join(ps), us, budget, total_score(chunks, ps)))
    print("  by density:   %-12s tokens %2d/%d   total relevance %d" % (" ".join(pd), ud, budget, total_score(chunks, pd)))
    print("-" * 64)
    print("  ranking by score-per-token fits more relevance into the same window.")


def optimum_view(data):
    chunks, budget = data["chunks"], data["budget"]
    best, sc = optimum(chunks, budget)
    print("OPTIMUM — exhaustive best subset under the %d-token budget" % budget)
    print("-" * 64)
    print("  best subset: %s   tokens %d   total relevance %d"
          % (" ".join(best), sum(chunks[n]["tokens"] for n in best), sc))
    pd, _ = by_density(chunks)
    print("  density heuristic picks %s (relevance %d) — %s the optimum"
          % (" ".join(pd), total_score(chunks, pd), "matches" if total_score(chunks, pd) == sc else "MISSES"))
    print("-" * 64)
    print("  the cheap density heuristic lands on the optimum here.")


def check(data):
    print("SELF-TEST — greedy-by-score wastes budget; density packs more relevance and matches the optimum")
    print("-" * 100)
    chunks, budget = data["chunks"], data["budget"]
    ps, us = by_score(chunks)
    pd, ud = by_density(chunks)
    ss, sd = total_score(chunks, ps), total_score(chunks, pd)
    best, sc = optimum(chunks, budget)

    score_within_budget = us <= budget
    print("  the by-score selection fits the budget = %s (%d/%d tokens)" % (score_within_budget, us, budget))

    density_within_budget = ud <= budget
    print("  the by-density selection fits the budget = %s (%d/%d tokens)" % (density_within_budget, ud, budget))

    density_beats_score = sd > ss
    print("  density packs more relevance than raw score = %s (%d vs %d)" % (density_beats_score, sd, ss))

    density_matches_optimum = sd == sc
    print("  density matches the exhaustive optimum = %s (%d vs %d)" % (density_matches_optimum, sd, sc))

    score_suboptimal = ss < sc
    print("  by-score leaves relevance on the table = %s (optimum %d, by-score %d)" % (score_suboptimal, sc, ss))

    ok = score_within_budget and density_within_budget and density_beats_score and density_matches_optimum and score_suboptimal
    print("-" * 100)
    print("SELF-TEST %s  score_within_budget=%s  density_within_budget=%s  density_beats_score=%s  density_matches_optimum=%s  score_suboptimal=%s"
          % ("PASS" if ok else "FAIL", score_within_budget, density_within_budget, density_beats_score, density_matches_optimum, ss < sc))
    return ok


LOADED = load()


def main():
    p = argparse.ArgumentParser(description="Pack retrieved chunks into a token budget by value density.")
    p.add_argument("--pack", action="store_true")
    p.add_argument("--optimum", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = LOADED
    print("chunks=%d  budget=%d tokens  file=%s  (the chunks and budget are a fixture)"
          % (len(data["chunks"]), data["budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pack:
        pack_view(data)
    elif args.optimum:
        optimum_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
