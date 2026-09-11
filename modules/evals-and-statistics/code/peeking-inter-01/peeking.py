"""Decide the sample size before you look -- peeking at an experiment and stopping at the first significant result manufactures false positives.

You run an A/B test and watch the dashboard. On day three the p-value dips below 0.05, the result is 'significant', and you ship. This feels like diligence -- you caught the effect as soon as it appeared -- and it is the single most common way online experiments produce effects that are not real. The problem is not any one look; it is looking repeatedly and stopping at whichever look happens to cross the line. Even when the two arms are IDENTICAL -- no true effect at all -- the test statistic wanders as data accumulates, and a wandering statistic given many chances to cross a threshold will eventually cross it by chance. Stop at that moment and you have declared a real effect from pure noise.

The nominal false-positive rate -- the 5% you accept when you set the threshold at 0.05 -- is the probability of crossing on ONE predetermined look. It is a guarantee about a single test, not about a sequence of them. Each additional peek is another chance for the noise to cross, so the probability that SOME look crosses climbs with the number of looks, well past 5%. The fixed-horizon discipline -- decide the sample size in advance, look once at the end, and judge significance only by that final look -- is what keeps the guarantee intact. Peeking trades that guarantee away one glance at a time.

What makes peeking so seductive is that the false positives look like early wins: the statistic crosses the threshold at an interim look and, if you had kept going, would often have drifted back below it by the planned end. The peeking analyst never sees the drift-back, because they stopped and shipped at the crossing. So the very trajectories that a fixed-horizon test would have correctly called null are the ones peeking converts into 'significant' -- the method is biased toward stopping exactly when the noise is most extreme.

The rule: fix the sample size in advance and evaluate significance only at that predetermined endpoint, rather than checking significance at every interim look and stopping at the first crossing, because the 0.05 false-positive rate is the probability of crossing on a single look -- repeated looks give the wandering statistic many chances to cross, inflating the real false-positive rate far above nominal, and the crossings that trigger an early stop are disproportionately the noise excursions that would have reverted by the planned end.

On these eight A/A tests (identical arms, true effect zero, every 'significant' result a false positive) the fixed-horizon rule -- judge only the final look -- flags 1 of 8, near the nominal level, while peeking -- stop at the first look above 1.96 -- flags 5 of 8, four of them on trajectories that crossed at an interim look and then fell back below the threshold. This computes both.

  --trajectories   each A/A test's z at every interim look, its peak, and whether it ever crosses 1.96
  --rates          fixed-horizon vs peeking: which tests each rule flags, and the false-positive rate of each
  --check          the arms are identical, yet peeking flags far more tests than the fixed-horizon rule -- inflated false positives from the same data

z_threshold, true_effect, and trajectories are the fixture; every crossing, stopping point, and rate is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "peeking.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def crosses_peeking(traj, thr):
    """Under peeking, the test 'wins' if ANY interim look reaches the threshold."""
    return any(abs(z) >= thr for z in traj)


def first_crossing(traj, thr):
    """The interim look index (1-based) where peeking would stop, or None."""
    for i, z in enumerate(traj):
        if abs(z) >= thr:
            return i + 1
    return None


def crosses_fixed(traj, thr):
    """Under a fixed horizon, the test 'wins' only if the FINAL look reaches the threshold."""
    return abs(traj[-1]) >= thr


def rate(flags):
    return sum(flags) / len(flags)


# ----------------------------------------------------------------- printing

def trajectories_view(data):
    thr = data["z_threshold"]
    trajs = data["trajectories"]
    print("TRAJECTORIES — each A/A test's z at every interim look (threshold %.2f)" % thr)
    print("-" * 74)
    print("  test   z at looks 1..5                 peak    ever crosses?   stops at look")
    for name in sorted(trajs):
        traj = trajs[name]
        peak = max(abs(z) for z in traj)
        fc = first_crossing(traj, thr)
        print("  %-5s  %-30s  %-6.2f  %-13s  %s"
              % (name, " ".join("%.2f" % z for z in traj), peak, crosses_peeking(traj, thr), fc if fc else "-"))
    print("-" * 74)
    print("  (true effect = %d: every crossing is a false positive)" % data["true_effect"])


def rates_view(data):
    thr = data["z_threshold"]
    trajs = data["trajectories"]
    names = sorted(trajs)
    fixed_flags = [crosses_fixed(trajs[n], thr) for n in names]
    peek_flags = [crosses_peeking(trajs[n], thr) for n in names]
    print("RATES — fixed-horizon (final look only) vs peeking (any look)")
    print("-" * 68)
    print("  fixed-horizon flags: %s" % ([names[i] for i in range(len(names)) if fixed_flags[i]] or "none"))
    print("  peeking flags:       %s" % ([names[i] for i in range(len(names)) if peek_flags[i]] or "none"))
    print("-" * 68)
    print("  false-positive rate  fixed-horizon = %d/%d = %.0f%%   peeking = %d/%d = %.0f%%"
          % (sum(fixed_flags), len(names), 100 * rate(fixed_flags), sum(peek_flags), len(names), 100 * rate(peek_flags)))
    reverted = [n for n in names if crosses_peeking(trajs[n], thr) and not crosses_fixed(trajs[n], thr)]
    print("  peeked 'wins' that had reverted below %.2f by the final look: %s" % (thr, reverted))


def check(data):
    print("SELF-TEST — the arms are identical, yet peeking flags far more tests than the fixed-horizon rule -- inflated false positives from the same data")
    print("-" * 142)
    thr = data["z_threshold"]
    trajs = data["trajectories"]
    names = sorted(trajs)
    fixed_flags = [crosses_fixed(trajs[n], thr) for n in names]
    peek_flags = [crosses_peeking(trajs[n], thr) for n in names]
    fixed_rate = rate(fixed_flags)
    peek_rate = rate(peek_flags)

    all_aa_tests = data["true_effect"] == 0
    print("  every test is an A/A test (true effect zero, so any win is a false positive) = %s" % all_aa_tests)

    fixed_horizon_near_nominal = fixed_rate <= 0.20
    print("  fixed-horizon false-positive rate stays near nominal = %s (%d/%d = %.0f%%)" % (fixed_horizon_near_nominal, sum(fixed_flags), len(names), 100 * fixed_rate))

    peeking_inflated = peek_rate > fixed_rate
    print("  peeking's false-positive rate exceeds the fixed-horizon rate = %s (%.0f%% > %.0f%%)" % (peeking_inflated, 100 * peek_rate, 100 * fixed_rate))

    peeking_at_least_doubles = peek_rate >= 2 * fixed_rate
    print("  peeking at least doubles the false-positive rate = %s (%.0f%% vs %.0f%%)" % (peeking_at_least_doubles, 100 * peek_rate, 100 * fixed_rate))

    reverted = [n for n in names if crosses_peeking(trajs[n], thr) and not crosses_fixed(trajs[n], thr)]
    reversion_drives_it = len(reverted) > 0
    print("  some peeked wins had reverted below the threshold by the end = %s (%s)" % (reversion_drives_it, reverted))

    fixed_ignores_reverted = all(not crosses_fixed(trajs[n], thr) for n in reverted)
    print("  the fixed-horizon rule correctly ignores those reverted trajectories = %s" % fixed_ignores_reverted)

    ok = all_aa_tests and fixed_horizon_near_nominal and peeking_inflated and peeking_at_least_doubles and reversion_drives_it and fixed_ignores_reverted
    print("-" * 142)
    print("SELF-TEST %s  all_aa_tests=%s  fixed_horizon_near_nominal=%s  peeking_inflated=%s  peeking_at_least_doubles=%s  reversion_drives_it=%s  fixed_ignores_reverted=%s"
          % ("PASS" if ok else "FAIL", all_aa_tests, fixed_horizon_near_nominal, peeking_inflated, peeking_at_least_doubles, reversion_drives_it, fixed_ignores_reverted))
    return ok


def main():
    p = argparse.ArgumentParser(description="Peeking / optional stopping: fix the sample size in advance and evaluate significance only at that predetermined endpoint, rather than checking significance at every interim look and stopping at the first crossing, because the 0.05 false-positive rate is the probability of crossing on a single look -- repeated looks give the wandering statistic many chances to cross, inflating the real false-positive rate far above nominal, and the crossings that trigger an early stop are disproportionately the noise excursions that would have reverted by the planned end.")
    p.add_argument("--trajectories", action="store_true")
    p.add_argument("--rates", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tests=%d  looks_each=%d  z_threshold=%.2f  true_effect=%d  file=%s  (the A/A trajectories are a fixture)"
          % (len(data["trajectories"]), len(next(iter(data["trajectories"].values()))), data["z_threshold"], data["true_effect"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trajectories:
        trajectories_view(data)
    elif args.rates:
        rates_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
