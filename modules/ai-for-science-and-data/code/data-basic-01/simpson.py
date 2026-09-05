#!/usr/bin/env python3
"""Simpson's paradox: the aggregate said B wins; every subgroup says A wins.

Comparing two options by their overall success rate is the first thing anyone does
and the first way anyone is fooled. When a confounder is distributed unevenly --
one option was handed the easy cases and the other the hard ones -- the aggregate
can point the opposite way from every honest, like-for-like comparison inside it.
This uses the classic kidney-stone-treatment numbers: treatment A wins on small
stones AND on large stones, yet loses on the overall rate, purely because A treated
far more of the hard (large-stone) cases. Segment by the confounder and the
reversal appears.

  --table       per-segment and overall success rates for both treatments
  --paradox      the overall winner vs the winner within every subgroup
  --confound     the case mix -- how the hard cases were split between the two
  --check        A wins every segment but loses the aggregate; the mix explains it

Stdlib only. No network. Counts are the published kidney-stone study, used as a
fixture. Deterministic. Point the same segmentation at your own A/B rates.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "trials.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["treatments"]


def rate(pair):
    num, den = pair
    return num / den if den else 0.0


def aggregate(t):
    """Pooled success rate across all segments -- the naive overall number."""
    num = sum(seg[0] for seg in t.values())
    den = sum(seg[1] for seg in t.values())
    return num / den, num, den


def segment_winner(treatments, seg):
    a = rate(treatments["A"][seg])
    b = rate(treatments["B"][seg])
    return "A" if a > b else ("B" if b > a else "tie"), a, b


def overall_winner(treatments):
    a, _, _ = aggregate(treatments["A"])
    b, _, _ = aggregate(treatments["B"])
    return "A" if a > b else ("B" if b > a else "tie"), a, b


# ------------------------------------------------------------------- printing

def table_view(treatments):
    segs = list(treatments["A"])
    print("SUCCESS RATES — by segment, and pooled")
    print("-" * 60)
    print("  treatment   %s   overall" % "   ".join("%-12s" % s for s in segs))
    for name, t in treatments.items():
        cells = []
        for s in segs:
            num, den = t[s]
            cells.append("%d/%d=%.2f" % (num, den, rate(t[s])))
        ov, num, den = aggregate(t)
        print("  %-10s  %s   %d/%d=%.2f" % (name, "   ".join("%-12s" % c for c in cells), num, den, ov))
    print("-" * 60)


def paradox_view(treatments):
    print("THE PARADOX — subgroup winner vs overall winner")
    print("-" * 60)
    for seg in treatments["A"]:
        w, a, b = segment_winner(treatments, seg)
        print("  within %-12s A=%.2f  B=%.2f  ->  %s wins" % (seg, a, b, w))
    w, a, b = overall_winner(treatments)
    print("  " + "-" * 40)
    print("  OVERALL          A=%.2f  B=%.2f  ->  %s wins" % (a, b, w))
    print("-" * 60)
    print("  A is better on every subgroup and worse overall -- the aggregate")
    print("  reverses the honest, like-for-like comparison. Trust the segments.")


def confound_view(treatments):
    print("THE CONFOUNDER — who took the hard (large-stone) cases")
    print("-" * 60)
    for name, t in treatments.items():
        total = sum(seg[1] for seg in t.values())
        hard = t["large"][1]
        print("  %-10s treated %d cases, %d of them large (%.0f%% hard)"
              % (name, total, hard, 100 * hard / total))
    print("-" * 60)
    print("  A took mostly hard cases, B mostly easy ones, so A's pooled rate is")
    print("  dragged down by the harder mix -- not by being a worse treatment.")


def check(treatments):
    print("SELF-TEST — A wins each segment but loses the pool; the mix is why")
    print("-" * 60)

    seg_winners = {seg: segment_winner(treatments, seg)[0] for seg in treatments["A"]}
    a_wins_all = all(w == "A" for w in seg_winners.values())
    print("  A wins within every segment = %s (%s)" % (a_wins_all, seg_winners))

    ow, a_ov, b_ov = overall_winner(treatments)
    b_wins_overall = ow == "B"
    print("  B wins the pooled rate = %s (A=%.3f, B=%.3f)" % (b_wins_overall, a_ov, b_ov))

    reversal = a_wins_all and b_wins_overall
    print("  the aggregate reverses every subgroup = %s" % reversal)

    # the confounder: A's share of hard cases is higher than B's.
    a_hard = treatments["A"]["large"][1] / sum(s[1] for s in treatments["A"].values())
    b_hard = treatments["B"]["large"][1] / sum(s[1] for s in treatments["B"].values())
    mix_explains = a_hard > b_hard
    print("  A took a higher share of hard cases than B = %s (%.2f vs %.2f)"
          % (mix_explains, a_hard, b_hard))

    det = aggregate(treatments["A"]) == aggregate(treatments["A"])
    ok = a_wins_all and b_wins_overall and reversal and mix_explains and det
    print("-" * 60)
    print("SELF-TEST %s  A_wins_segments=%s  B_wins_pool=%s  reversal=%s  mix_explains=%s"
          % ("PASS" if ok else "FAIL", a_wins_all, b_wins_overall, reversal, mix_explains))
    return ok


def main():
    p = argparse.ArgumentParser(description="Simpson's paradox on an A/B success rate.")
    p.add_argument("--table", action="store_true")
    p.add_argument("--paradox", action="store_true")
    p.add_argument("--confound", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    treatments = load()
    print("treatments=%s  segments=%s  file=%s  (counts are a fixture)"
          % (list(treatments), list(treatments["A"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(treatments) else 1
    if args.table:
        table_view(treatments)
    elif args.paradox:
        paradox_view(treatments)
    elif args.confound:
        confound_view(treatments)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
