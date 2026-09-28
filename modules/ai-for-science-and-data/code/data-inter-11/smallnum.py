"""Rank by signal, not by raw rate -- the most extreme rates come from the smallest samples, which is just noise.

Line up units -- clinics, counties, stores, model variants -- by the rate at which something happens, and
the top and bottom of the list will be dominated by the SMALLEST units. Not because small units are better
or worse, but because a small sample is noisy: with few trials the observed rate swings far from the true
rate on pure chance. So the highest rate and the lowest rate both tend to come from the units with the
least data, and reading either as a real effect is the law of small numbers -- mistaking sampling variance
for signal.

The honest measure is not the raw rate but how far it sits from the baseline in units of its own standard
error, which shrinks as the sample grows. An extreme rate over a tiny sample is a small number of standard
errors -- explainable by noise. A modest rate over a huge sample can be many standard errors -- a real
anomaly. Ranking by that z-score surfaces genuine signals and demotes the small-sample flukes that ranking
by raw rate promotes.

On this fixture five units all draw from a baseline rate of 0.10. The eye-catching extremes are unit A
(rate 0.30, n=20) and unit B (rate 0.00, n=25) -- the two smallest samples, and both within about 1-3
standard errors of baseline. The real signal is unit C: an unremarkable rate of 0.13, but over n=5000,
which is 7 standard errors out. Rank by raw rate and you chase A and B; rank by z and you find C. This
computes the rate, standard error, and z-score for each.

  --units      each unit's n, successes, and observed rate
  --signal     rate vs standard error vs z-score, and the ranking by each
  --check      the extreme raw rates come from the smallest samples; the strongest signal is the largest one

The counts and baseline are the fixture; every rate, standard error, and z-score is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "units.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rate(u):
    return u["successes"] / u["n"]


def std_error(n, p):
    """Standard error of a rate estimated from n trials at baseline p -- shrinks as 1/sqrt(n)."""
    return math.sqrt(p * (1 - p) / n)


def zscore(u, p):
    """How many standard errors the observed rate sits from baseline -- the signal, size-adjusted."""
    return (rate(u) - p) / std_error(u["n"], p)


# ----------------------------------------------------------------- printing

def units_view(data):
    print("UNITS — observed rate per unit (baseline %.2f)" % data["baseline_rate"])
    print("-" * 46)
    for name, u in sorted(data["units"].items()):
        print("  %s  n=%-5d successes=%-4d rate %.3f" % (name, u["n"], u["successes"], rate(u)))
    print("-" * 46)
    print("  the raw rates range from 0.00 to 0.30 -- but the samples range from 20 to 5000.")


def signal_view(data):
    p = data["baseline_rate"]
    print("SIGNAL — rate vs standard error vs z-score, and the two rankings")
    print("-" * 62)
    print("  unit  n      rate    std err   z (signal)")
    for name, u in sorted(data["units"].items()):
        print("  %s     %-6d %.3f   %.4f    %+6.2f" % (name, u["n"], rate(u), std_error(u["n"], p), zscore(u, p)))
    print("-" * 62)
    by_rate = [n for n, _ in sorted(data["units"].items(), key=lambda kv: rate(kv[1]), reverse=True)]
    by_z = [n for n, _ in sorted(data["units"].items(), key=lambda kv: abs(zscore(kv[1], p)), reverse=True)]
    print("  ranked by raw rate: %s" % " > ".join(by_rate))
    print("  ranked by signal:   %s" % " > ".join(by_z))
    print("  raw rate crowns the small samples; signal crowns the big one.")


def check(data):
    print("SELF-TEST — the extreme raw rates come from the smallest samples; the strongest signal is the largest")
    print("-" * 96)
    p = data["baseline_rate"]
    units = data["units"]
    ns = {name: u["n"] for name, u in units.items()}

    by_rate = sorted(units, key=lambda name: rate(units[name]))
    smallest = sorted(ns, key=lambda name: ns[name])[:2]
    lowest, highest = by_rate[0], by_rate[-1]
    extremes_are_smallest = set([lowest, highest]) == set(smallest)
    print("  the highest and lowest raw rates are the two smallest samples = %s (%s and %s, n=%d and %d)"
          % (extremes_are_smallest, highest, lowest, ns[highest], ns[lowest]))

    extremes_within_noise = abs(zscore(units[highest], p)) < 3.5 and abs(zscore(units[lowest], p)) < 3.5
    print("  those extremes are within noise of baseline = %s (|z| %.2f and %.2f)"
          % (extremes_within_noise, abs(zscore(units[highest], p)), abs(zscore(units[lowest], p))))

    by_z = sorted(units, key=lambda name: abs(zscore(units[name], p)), reverse=True)
    biggest = max(ns, key=lambda name: ns[name])
    strongest_is_largest = by_z[0] == biggest
    print("  the strongest signal is the largest sample = %s (%s, n=%d, z=%.2f)"
          % (strongest_is_largest, by_z[0], ns[biggest], zscore(units[biggest], p)))

    rankings_disagree = by_rate[-1] != by_z[0]
    print("  ranking by raw rate and by signal disagree = %s (rate top %s, signal top %s)"
          % (rankings_disagree, by_rate[-1], by_z[0]))

    ok = extremes_are_smallest and extremes_within_noise and strongest_is_largest and rankings_disagree
    print("-" * 96)
    print("SELF-TEST %s  extremes_are_smallest=%s  extremes_within_noise=%s  strongest_is_largest=%s  rankings_disagree=%s"
          % ("PASS" if ok else "FAIL", extremes_are_smallest, extremes_within_noise, strongest_is_largest, rankings_disagree))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rank by signal, not raw rate -- extreme rates come from small samples.")
    p.add_argument("--units", action="store_true")
    p.add_argument("--signal", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("units=%d  baseline=%.2f  file=%s  (the counts are a fixture)"
          % (len(data["units"]), data["baseline_rate"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.units:
        units_view(data)
    elif args.signal:
        signal_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
