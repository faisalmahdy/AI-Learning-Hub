"""Compare two models on the same items by their disagreements, or the concordant items fool you.

When two models are evaluated on the SAME test items, the results are PAIRED: for each item you know whether
each model got it right, so the items sort into four cells -- both right, A-only right, B-only right, both
wrong. The instinct is to compare the two accuracies, A's (both + A-only)/n against B's (both + B-only)/n. But
look at the difference: acc(A) - acc(B) = (A-only - B-only)/n. The 'both right' and 'both wrong' items appear
in both accuracies and cancel out completely. They tell you nothing about WHICH model is better, because both
models handled them identically. Only the DISCORDANT items -- where the models disagree -- carry information
about the comparison, and treating the two accuracies as if they came from independent samples throws away the
pairing that makes the comparison powerful.

McNemar's test uses exactly the discordant cells. Its statistic is (A-only - B-only)^2 / (A-only + B-only) --
built only from the two disagreement counts, ignoring the agreements entirely. So a comparison where the models
agree on 96 of 100 items rests entirely on the 4 they disagree on; the 96 concordant items, however many there
are, do not move it. This is why paired evals are efficient: they let every item's shared difficulty cancel,
concentrating the evidence in the disagreements.

On this fixture two scenarios have the SAME discordant counts (3 vs 1) but wildly different agreement -- one
agrees on 96 items, the other on 96 the other way. The accuracy difference (0.02) and the McNemar statistic
(1.0) are identical in both, because both depend only on the 3 and the 1. This computes both.

  --table      the 2x2 table, marginal accuracies, and the accuracy difference for each scenario
  --mcnemar    the McNemar statistic from the discordant cells, shown identical across the scenarios
  --check      the difference and the statistic depend only on the discordant cells, not the agreements

The 2x2 tallies are the fixture; every statistic is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paired.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def acc_a(c, n):
    """A's accuracy: items A got right = both_correct + a_only."""
    return (c["both_correct"] + c["a_only"]) / n


def acc_b(c, n):
    return (c["both_correct"] + c["b_only"]) / n


def mcnemar(c):
    """McNemar statistic from the discordant cells only: (a_only - b_only)^2 / (a_only + b_only)."""
    b, cc = c["a_only"], c["b_only"]
    return (b - cc) ** 2 / (b + cc) if (b + cc) else 0.0


# ----------------------------------------------------------------- printing

def table_view(data):
    n = data["n"]
    print("TABLE — 2x2 paired results, marginal accuracies, and the difference (n=%d)" % n)
    print("-" * 68)
    for name, c in data["scenarios"].items():
        print("  %-14s both=%d  A-only=%d  B-only=%d  both_wrong=%d" % (name, c["both_correct"], c["a_only"], c["b_only"], c["both_wrong"]))
        print("                 acc(A)=%.2f  acc(B)=%.2f  diff=%+.2f" % (acc_a(c, n), acc_b(c, n), acc_a(c, n) - acc_b(c, n)))
    print("-" * 68)
    print("  the two scenarios agree on very different numbers of items, yet the diff is the same.")


def mcnemar_view(data):
    print("MCNEMAR — the statistic uses only the discordant cells")
    print("-" * 68)
    for name, c in data["scenarios"].items():
        print("  %-14s discordant %d vs %d  ->  statistic (%d-%d)^2/(%d+%d) = %.2f"
              % (name, c["a_only"], c["b_only"], c["a_only"], c["b_only"], c["a_only"], c["b_only"], mcnemar(c)))
    print("-" * 68)
    print("  same discordant counts -> same statistic, whatever the agreement.")


def check(data):
    print("SELF-TEST — the difference and the statistic depend only on the discordant cells, not the agreements")
    print("-" * 104)
    n = data["n"]
    hi = data["scenarios"]["high_agreement"]
    lo = data["scenarios"]["low_agreement"]

    diff_is_discordant = abs((acc_a(hi, n) - acc_b(hi, n)) - (hi["a_only"] - hi["b_only"]) / n) < 1e-9
    print("  acc(A)-acc(B) equals (A-only - B-only)/n = %s (%.2f)" % (diff_is_discordant, acc_a(hi, n) - acc_b(hi, n)))

    concordant_differs = hi["both_correct"] != lo["both_correct"]
    print("  the two scenarios have very different agreement = %s (both_correct %d vs %d)" % (concordant_differs, hi["both_correct"], lo["both_correct"]))

    same_diff = abs((acc_a(hi, n) - acc_b(hi, n)) - (acc_a(lo, n) - acc_b(lo, n))) < 1e-9
    print("  yet the accuracy difference is identical = %s (%+.2f both)" % (same_diff, acc_a(hi, n) - acc_b(hi, n)))

    same_statistic = abs(mcnemar(hi) - mcnemar(lo)) < 1e-9
    print("  and the McNemar statistic is identical = %s (%.2f both)" % (same_statistic, mcnemar(hi)))

    evidence_is_discordant = (hi["a_only"] + hi["b_only"]) < n
    print("  the comparison rests on the %d discordant items, not all %d = %s" % (hi["a_only"] + hi["b_only"], n, evidence_is_discordant))

    ok = diff_is_discordant and concordant_differs and same_diff and same_statistic and evidence_is_discordant
    print("-" * 104)
    print("SELF-TEST %s  diff_is_discordant=%s  concordant_differs=%s  same_diff=%s  same_statistic=%s  evidence_is_discordant=%s"
          % ("PASS" if ok else "FAIL", diff_is_discordant, concordant_differs, same_diff, same_statistic, evidence_is_discordant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Compare two models on the same items with McNemar's test, using only their disagreements.")
    p.add_argument("--table", action="store_true")
    p.add_argument("--mcnemar", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  scenarios=%s  file=%s  (the 2x2 tallies are a fixture)"
          % (data["n"], list(data["scenarios"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.table:
        table_view(data)
    elif args.mcnemar:
        mcnemar_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
