#!/usr/bin/env python3
"""Do councils help? Only when the voters fail independently -- measure, don't assume.

A council -- several models vote, the majority wins -- is used across the labs but
never checked against outcomes. The intuition "three heads beat one" is a theorem
(Condorcet) with a fine-print condition: the voters must err INDEPENDENTLY. When
models share a blind spot -- same training data, same bias -- they fail the same
items together, the majority confidently ratifies the shared mistake, and a council
of one strong model and two correlated weak ones loses to the strong model alone.
This runs the same council on two vote sets, one independent and one correlated,
and shows the council helps in the first and hurts in the second.

  --scenario S   the per-item votes and truth for one scenario (independent|correlated)
  --compare      best single model vs the council, both scenarios, with error overlap
  --overlap      how often the models err together in each scenario (the deciding stat)
  --check        council beats single when errors are independent, loses when correlated

Stdlib only. No network, no model -- the votes are a fixture standing in for real
model runs. Deterministic. Point the council at your own scored model outputs.
"""
import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOTES = HERE / "votes.json"


def load():
    return json.loads(VOTES.read_text(encoding="utf-8"))["scenarios"]


def accuracy(votes, truth):
    return sum(1 for v, t in zip(votes, truth) if v == t) / len(truth)


def majority(row):
    """The council's answer for one item: the label with the most votes (ties ->
    the alphabetically first, a fixed, blind tie-break)."""
    counts = {}
    for v in row:
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    return sorted(k for k, c in counts.items() if c == top)[0]


def council_votes(models, n_items):
    return [majority([models[m][i] for m in models]) for i in range(n_items)]


def best_single(models, truth):
    """The strongest individual model -- the one-good-pass baseline a council must beat."""
    return max(((m, accuracy(v, truth)) for m, v in models.items()), key=lambda x: x[1])


def error_overlap(models, truth):
    """Fraction of item-pairs of models that are wrong on the SAME item -- a proxy
    for error correlation. High overlap is the regime where councils fail."""
    names = list(models)
    wrong = {m: {i for i, (v, t) in enumerate(zip(models[m], truth)) if v != t} for m in names}
    shared = total = 0
    for a, b in combinations(names, 2):
        shared += len(wrong[a] & wrong[b])
        total += len(wrong[a] | wrong[b])
    return shared / total if total else 0.0


# ------------------------------------------------------------------- printing

def scenario_view(scenarios, name):
    sc = scenarios[name]
    truth, models = sc["truth"], sc["models"]
    n = len(truth)
    print("SCENARIO %s — per-item votes (v = correct where it equals truth)" % name)
    print("-" * 66)
    print("  item     truth   %s   council" % "  ".join("%-4s" % m for m in models))
    coun = council_votes(models, n)
    for i in range(n):
        cells = "  ".join("%-4s" % models[m][i] for m in models)
        print("  %-7d  %-5s   %s   %s" % (i + 1, truth[i], cells, coun[i]))
    print("-" * 66)
    for m, v in models.items():
        print("  %-8s accuracy %.2f" % (m, accuracy(v, truth)))
    print("  council  accuracy %.2f" % accuracy(coun, truth))


def compare(scenarios):
    print("COUNCIL vs BEST SINGLE — does the vote help?")
    print("-" * 66)
    print("  scenario      best single       council   delta    error-overlap")
    for name, sc in scenarios.items():
        truth, models = sc["truth"], sc["models"]
        bm, ba = best_single(models, truth)
        ca = accuracy(council_votes(models, len(truth)), truth)
        ov = error_overlap(models, truth)
        verdict = "helps" if ca > ba else ("hurts" if ca < ba else "ties")
        print("  %-12s  %-5s %.2f       %.2f    %+.2f    %.2f  (%s)"
              % (name, bm, ba, ca, ca - ba, ov, verdict))
    print("-" * 66)
    print("  the council beats the best single only where error-overlap is low.")
    print("  where the models fail together, the majority ratifies the shared error.")


def overlap_view(scenarios):
    print("ERROR OVERLAP — how often the models are wrong on the SAME items")
    print("-" * 66)
    for name, sc in scenarios.items():
        ov = error_overlap(sc["models"], sc["truth"])
        print("  %-12s error-overlap = %.2f  (%s)"
              % (name, ov, "independent -> council helps" if ov < 0.4 else "correlated -> council fails"))
    print("-" * 66)
    print("  this single number predicts the council's verdict before you score it.")


def check(scenarios):
    print("SELF-TEST — council helps when independent, hurts when correlated")
    print("-" * 66)
    ind, cor = scenarios["independent"], scenarios["correlated"]

    def delta(sc):
        truth, models = sc["truth"], sc["models"]
        return accuracy(council_votes(models, len(truth)), truth) - best_single(models, truth)[1]

    d_ind, d_cor = delta(ind), delta(cor)
    print("  council - best_single:  independent = %+.2f   correlated = %+.2f" % (d_ind, d_cor))

    helps_ind = d_ind > 0
    print("  council beats the best single when errors are independent = %s" % helps_ind)
    hurts_cor = d_cor < 0
    print("  council loses to the best single when errors are correlated = %s" % hurts_cor)

    ov_ind = error_overlap(ind["models"], ind["truth"])
    ov_cor = error_overlap(cor["models"], cor["truth"])
    overlap_predicts = ov_cor > ov_ind
    print("  error-overlap is higher in the correlated scenario = %s (%.2f > %.2f)"
          % (overlap_predicts, ov_cor, ov_ind))

    # the mechanism: in correlated, two weak models outvote the strong one on a shared miss.
    truth, models = cor["truth"], cor["models"]
    bm, _ = best_single(models, truth)
    coun = council_votes(models, len(truth))
    dragged = any(models[bm][i] == truth[i] and coun[i] != truth[i] for i in range(len(truth)))
    print("  the council overrode the strong model into a shared error = %s" % dragged)

    det = council_votes(models, len(truth)) == council_votes(models, len(truth))
    ok = helps_ind and hurts_cor and overlap_predicts and dragged and det
    print("-" * 66)
    print("SELF-TEST %s  helps_ind=%s  hurts_cor=%s  overlap_predicts=%s  dragged=%s"
          % ("PASS" if ok else "FAIL", helps_ind, hurts_cor, overlap_predicts, dragged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Measure whether a council beats one strong pass.")
    p.add_argument("--scenario", metavar="S")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--overlap", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    scenarios = load()
    print("scenarios=%s  file=%s  (votes are a fixture)" % (list(scenarios), VOTES.name))
    print("")

    if args.check:
        return 0 if check(scenarios) else 1
    if args.scenario:
        scenario_view(scenarios, args.scenario)
    elif args.compare:
        compare(scenarios)
    elif args.overlap:
        overlap_view(scenarios)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
