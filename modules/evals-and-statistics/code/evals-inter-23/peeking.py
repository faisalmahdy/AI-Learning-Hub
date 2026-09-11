"""Don't stop the A/B test when it first hits significance, or peeking inflates the false-positive rate.

A significance test at alpha=0.05 promises: if the two variants are truly identical, you will wrongly call them
different only 5% of the time. That promise holds for ONE look, at a sample size fixed in advance. The moment you
watch the test run and stop as soon as the p-value dips below 0.05, you have broken the promise, because you are
no longer taking one 5% gamble -- you are taking a fresh gamble at every peek and keeping the first one that wins.
The running test statistic wanders (it is a random walk under the null), so given enough looks it will cross the
significance line by chance even when nothing is going on, and a peeker who stops at the first crossing declares a
winner that does not exist. The more often you peek, the more chances you give luck, and the higher the
false-positive rate climbs above the 5% you thought you were risking.

The discipline is to decide the sample size in advance and look once, at the end. Then the test statistic gets a
single chance to cross, and the false-positive rate is the nominal alpha. If you genuinely need to monitor a test
as it runs and stop early, you cannot use the fixed-sample cutoff -- you need a sequential method (alpha spending,
group-sequential boundaries, or Bayesian tests) that budgets the error across the looks so the TOTAL false-positive
rate stays at alpha. The sin is not looking; it is looking with a threshold that assumed you would look only once.

On this fixture the variants are identical (null true), so every 'significant' is false. Looking once gives a
false-positive rate of 0.05, exactly nominal. Peeking at 5 points and stopping at the first crossing gives 0.135 --
almost triple. And the rate climbs monotonically with the number of peeks: 0.05, 0.08, 0.10, 0.12, 0.14. This
computes both.

  --rate       the false-positive rate looking once (disciplined) vs peeking at every point (stop-early)
  --growth     how the false-positive rate climbs as you add more peeks
  --check      one look sits at alpha; peeking inflates the false-positive rate; more peeks make it worse

The peek schedule and cutoff are the fixture; every rate is simulated under the null. Stdlib only.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "peeking.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def crosses_any(seed, peeks, z_cutoff):
    """One trial under the null: streaming samples, does |z| cross the cutoff at ANY peek (stop-early peeking)?"""
    r = random.Random(seed)
    total, n, prev = 0.0, 0, 0
    for p in peeks:
        for _ in range(p - prev):
            total += r.gauss(0, 1)
            n += 1
        prev = p
        if abs(total / math.sqrt(n)) > z_cutoff:
            return True
    return False


def false_positive_rate(peeks, z_cutoff, trials, base_seed):
    """Fraction of null trials that cross at any peek in the schedule."""
    return sum(crosses_any(base_seed + i, peeks, z_cutoff) for i in range(trials)) / trials


# ----------------------------------------------------------------- printing

def rate_view(data):
    peeks, z, trials, seed = data["peeks"], data["z_cutoff"], data["trials"], data["base_seed"]
    once = false_positive_rate(peeks[-1:], z, trials, seed)
    peeking = false_positive_rate(peeks, z, trials, seed)
    print("RATE — false-positive rate under the null (variants identical), %d trials" % trials)
    print("-" * 62)
    print("  look once at n=%d (disciplined):   %.3f   (nominal alpha)" % (peeks[-1], once))
    print("  peek at %d points, stop early:      %.3f   (%.1fx alpha)" % (len(peeks), peeking, peeking / 0.05))
    print("-" * 62)
    print("  every 'significant' here is false; peeking manufactures %.0f%% more of them." % (100 * (peeking - once)))


def growth_view(data):
    peeks, z, trials, seed = data["peeks"], data["z_cutoff"], data["trials"], data["base_seed"]
    print("GROWTH — false-positive rate as the number of peeks grows")
    print("-" * 62)
    for k in range(1, len(peeks) + 1):
        fpr = false_positive_rate(peeks[:k], z, trials, seed)
        print("  %d look%s:  false-positive rate %.3f" % (k, " " if k == 1 else "s", fpr))
    print("-" * 62)
    print("  each extra peek is another chance at the 5%% event, so the rate only climbs.")


def check(data):
    print("SELF-TEST — one look sits at alpha; peeking inflates the false-positive rate; more peeks make it worse")
    print("-" * 104)
    peeks, z, trials, seed = data["peeks"], data["z_cutoff"], data["trials"], data["base_seed"]
    once = false_positive_rate(peeks[-1:], z, trials, seed)
    peeking = false_positive_rate(peeks, z, trials, seed)

    one_look_at_alpha = abs(once - 0.05) < 0.02
    print("  looking once gives about the nominal 5%% false-positive rate = %s (%.3f)" % (one_look_at_alpha, once))

    peeking_inflated = peeking > 2 * 0.05
    print("  peeking inflates the false-positive rate past 2x alpha = %s (%.3f)" % (peeking_inflated, peeking))

    peeking_above_once = peeking > once
    print("  peeking is worse than looking once = %s (%.3f > %.3f)" % (peeking_above_once, peeking, once))

    rates = [false_positive_rate(peeks[:k], z, trials, seed) for k in range(1, len(peeks) + 1)]
    monotonic = all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1)) and rates[-1] > rates[0]
    print("  the false-positive rate climbs with the number of peeks = %s (%s)" % (monotonic, [round(r, 3) for r in rates]))

    reproducible = false_positive_rate(peeks, z, trials, seed) == peeking
    print("  the seeded simulation is reproducible = %s (%.3f)" % (reproducible, peeking))

    ok = one_look_at_alpha and peeking_inflated and peeking_above_once and monotonic and reproducible
    print("-" * 104)
    print("SELF-TEST %s  one_look_at_alpha=%s  peeking_inflated=%s  peeking_above_once=%s  monotonic=%s  reproducible=%s"
          % ("PASS" if ok else "FAIL", one_look_at_alpha, peeking_inflated, peeking_above_once, monotonic, reproducible))
    return ok


def main():
    p = argparse.ArgumentParser(description="Peeking at a running test and stopping at the first significant look inflates the false-positive rate above alpha.")
    p.add_argument("--rate", action="store_true")
    p.add_argument("--growth", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("peeks=%s  z_cutoff=%.2f  trials=%d  seed=%d  file=%s  (the schedule is a fixture; null is true)"
          % (data["peeks"], data["z_cutoff"], data["trials"], data["base_seed"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rate:
        rate_view(data)
    elif args.growth:
        growth_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
