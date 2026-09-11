#!/usr/bin/env python3
"""An honest-effect gauntlet: a claimed discovery must survive every pitfall guard at once.

The AI-for-science track built each statistical pitfall one at a time, and each was a way a
real number lies: Simpson's paradox (data-basic-01) reversed an aggregate that ignored a
confounder, regression to the mean (data-inter-01) manufactured an improvement by selecting
the worst group, and multiple comparisons (data-inter-04) turned noise into a "significant"
finding by running enough tests. Each pitfall has a guard, and each guard alone lets the
other two pitfalls through. This composes the three guards into one gauntlet a claimed effect
must pass -- consistent across the confounder's segments, larger than a control selected the
same way, and surviving correction for how many tests were run -- and measures it against a
naive analyst who ships anything with a positive aggregate and a raw p below 0.05.

The point is that a claim can be wrong in three different ways, and catching one does nothing
for the other two. A confounder-segmented analysis still ships a regression-to-the-mean
artifact; a controlled study still ships a cherry-picked metric; a corrected p-value still
ships a Simpson reversal. Only the conjunction of all three guards keeps every false
discovery out while letting the one real effect through -- which is the whole job of an
honest analysis: not to find effects, but to not report the ones that are not there.

  --findings   the four claimed effects and the raw signal each guard reads
  --naive      the naive analyst: positive aggregate and raw p<0.05 -> ship
  --honest     each finding against all three guards; ship only if it passes every one
  --check      the honest gauntlet makes zero false discoveries and keeps the one real effect

The ground-truth 'real' flag on each finding is a hand-authored fixture, so the false- and
true-discovery counts are exact. Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "findings.json"
ALPHA = 0.05


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the three guards

def consistent_across_segments(f):
    """Simpson (data-basic-01): the effect holds within every segment, not just in aggregate.

    A positive aggregate whose segments are all negative is a confounder reversal -- the
    aggregate is an artifact of an uneven mix, not a real within-group effect.
    """
    agg = f["aggregate_effect"]
    if agg == 0:
        return False
    return all((seg > 0) == (agg > 0) for seg in f["segments"])


def beats_control(f):
    """Regression to the mean (data-inter-01): the treated change must exceed a control
    selected the same way. If an untreated control moved as much, the 'effect' is regression."""
    return (f["treated_change"] - f["control_change"]) > 0.005


def survives_correction(f):
    """Multiple comparisons (data-inter-04): the p-value must clear the Bonferroni threshold
    alpha/n_tests, not the raw alpha, or a finding picked from many tests is just noise."""
    return f["p_value"] < ALPHA / f["n_tests"]


GUARDS = [
    ("segments", consistent_across_segments),   # Simpson
    ("control", beats_control),                 # regression to the mean
    ("correction", survives_correction),        # multiple comparisons
]


# ------------------------------------------------------------- the two analysts

def honest_ships(f):
    """Ship only if the claim passes every guard -- the conjunction of all three."""
    return all(g(f) for _, g in GUARDS)


def naive_ships(f):
    """The bug: a positive aggregate and a raw p below 0.05 is enough to ship."""
    return f["aggregate_effect"] > 0 and f["p_value"] < ALPHA


def failed_guard(f):
    """Which guard (if any) a finding fails -- the pitfall that would have fooled a naive analyst."""
    for name, g in GUARDS:
        if not g(f):
            return name
    return None


# ----------------------------------------------------------------- printing

def findings_view(data):
    fs = data["findings"]
    print("FINDINGS — four claimed effects and the raw signal each guard reads")
    print("-" * 74)
    print("  id          agg     segments        treated/control   p       n_tests  real")
    for f in fs:
        print("  %-11s %+.3f  %-15s %+.2f / %+.2f     %-7s %-7d %s"
              % (f["id"], f["aggregate_effect"], str(f["segments"]),
                 f["treated_change"], f["control_change"], f["p_value"], f["n_tests"], f["real"]))
    print("-" * 74)
    print("  a real effect is consistent across segments, beats its control, and clears alpha/n_tests.")


def naive_view(data):
    fs = data["findings"]
    print("NAIVE — ship anything with a positive aggregate and raw p<0.05")
    print("-" * 74)
    shipped = []
    for f in fs:
        s = naive_ships(f)
        if s:
            shipped.append(f["id"])
        print("  %-11s agg%+.3f  p=%-7s -> %s" % (f["id"], f["aggregate_effect"], f["p_value"], "SHIP" if s else "drop"))
    false_disc = [f["id"] for f in fs if naive_ships(f) and not f["real"]]
    print("-" * 74)
    print("  shipped: %s   of which FALSE discoveries: %s" % (shipped, false_disc))


def honest_view(data):
    fs = data["findings"]
    print("HONEST — a claim ships only if it passes all three guards")
    print("-" * 74)
    print("  id          segments  control  correction  -> verdict (failed pitfall)")
    for f in fs:
        g = {name: fn(f) for name, fn in GUARDS}
        ship = honest_ships(f)
        fail = failed_guard(f)
        print("  %-11s %-9s %-8s %-11s -> %s%s"
              % (f["id"], g["segments"], g["control"], g["correction"],
                 "SHIP" if ship else "drop", "" if ship else "  (%s)" % fail))
    print("-" * 74)
    shipped = [f["id"] for f in fs if honest_ships(f)]
    print("  shipped: %s   false discoveries: %s"
          % (shipped, [f["id"] for f in fs if honest_ships(f) and not f["real"]]))


def check(data):
    print("SELF-TEST — the gauntlet keeps every false discovery out and the one real effect in")
    print("-" * 74)
    fs = data["findings"]

    n_real = sum(1 for f in fs if f["real"])
    honest_false = [f["id"] for f in fs if honest_ships(f) and not f["real"]]
    honest_true = [f["id"] for f in fs if honest_ships(f) and f["real"]]
    naive_false = [f["id"] for f in fs if naive_ships(f) and not f["real"]]

    honest_no_false = len(honest_false) == 0
    print("  honest gauntlet makes zero false discoveries = %s (%s)" % (honest_no_false, honest_false))

    honest_keeps_real = len(honest_true) == n_real
    print("  honest gauntlet keeps every real effect = %s (%d of %d)" % (honest_keeps_real, len(honest_true), n_real))

    naive_leaks = len(naive_false) >= 3
    print("  naive analyst makes >=3 false discoveries = %s (%s)" % (naive_leaks, naive_false))

    # each false discovery fails a DIFFERENT guard -- three distinct pitfalls, not one repeated
    fails = sorted({failed_guard(f) for f in fs if not f["real"]})
    three_distinct = fails == ["control", "correction", "segments"]
    print("  the three false claims each fail a different guard = %s (%s)" % (three_distinct, fails))

    ok = honest_no_false and honest_keeps_real and naive_leaks and three_distinct
    print("-" * 74)
    print("SELF-TEST %s  honest_no_false=%s  honest_keeps_real=%s  naive_leaks=%s  three_distinct=%s"
          % ("PASS" if ok else "FAIL", honest_no_false, honest_keeps_real, naive_leaks, three_distinct))
    return ok


def main():
    p = argparse.ArgumentParser(description="An honest-effect gauntlet composing three pitfall guards.")
    p.add_argument("--findings", action="store_true")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--honest", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("findings=%d  alpha=%.2f  file=%s  (claims and the ground-truth 'real' flag are a fixture)"
          % (len(data["findings"]), ALPHA, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.findings:
        findings_view(data)
    elif args.naive:
        naive_view(data)
    elif args.honest:
        honest_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
