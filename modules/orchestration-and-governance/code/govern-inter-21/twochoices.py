"""Pick the least-loaded of two random workers, or one random choice leaves a worker buried under the tail.

Random dispatch is the cheapest load balancer: each task picks a worker uniformly at random, no coordination,
no shared counter. On average every worker gets the same share. But the average is not what hurts -- the MAX is.
With one random choice, some worker gets unlucky and lands well above the mean, and that most-loaded worker sets
the tail latency, the queue depth, the thing that pages you. Balancing "on average" still leaves a hot spot,
because uniform random has real variance and nothing pulls the outliers back down.

The power of two choices is a one-line change with a wildly disproportionate effect. Instead of picking one
worker, sample TWO at random and send the task to the less loaded of the two. You are still doing almost no
work -- two samples, one comparison -- and there is still no global coordination. But now a task actively avoids
the more-loaded of its two options, so loads that start to run high get passed over, and the maximum load
collapses. The theory says the expected max drops from about log n / log log n down to log log n; in practice one
extra sample nearly halves the peak.

A single trial is noisy -- with 100 tasks over 20 workers one lucky run can go either way -- so the claim is
about the EXPECTED max, averaged over many trials. On this fixture (100 tasks, 20 workers, mean 5) the average
busiest worker holds 9.62 tasks under one choice and 6.33 under two, across 300 trials. One representative trial
shows 9 versus 6. Same tasks, same workers; the only change is sampling two and taking the smaller. This
computes both.

  --dispatch   one representative trial's per-worker loads under one choice and two choices
  --max        the average max load over all trials under each strategy, versus the mean
  --check      one choice overshoots the mean; two choices cuts the average max; the mean is the same target

The tasks, workers, and seeds are the fixture; every assignment is computed. Stdlib only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "twochoices.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dispatch(tasks, workers, seed, d):
    """Assign each task to a worker. d=1 picks one worker at random; d=2 samples two and takes the less loaded.
    Returns the per-worker load list. rng is seeded so the run is reproducible."""
    rng = random.Random(seed)
    load = [0] * workers
    for _ in range(tasks):
        picks = [rng.randrange(workers) for _ in range(d)]
        chosen = min(picks, key=lambda w: load[w])
        load[chosen] += 1
    return load


def avg_max(tasks, workers, base_seed, trials, d):
    """Mean of the max load over `trials` independent trials (seed = base_seed + trial)."""
    return sum(max(dispatch(tasks, workers, base_seed + i, d)) for i in range(trials)) / trials


# ----------------------------------------------------------------- printing

def dispatch_view(data):
    t, w, es = data["tasks"], data["workers"], data["example_seed"]
    one = dispatch(t, w, es, 1)
    two = dispatch(t, w, es, 2)
    print("DISPATCH — per-worker load, one representative trial (%d tasks, %d workers, mean %.1f)" % (t, w, t / w))
    print("-" * 68)
    print("  one choice (d=1):  %s   max %d" % (one, max(one)))
    print("  two choices (d=2): %s   max %d" % (two, max(two)))
    print("-" * 68)
    print("  one choice leaves a worker well above the mean; two choices flattens the peak.")


def max_view(data):
    t, w, bs, tr = data["tasks"], data["workers"], data["base_seed"], data["trials"]
    mean = t / w
    a1 = avg_max(t, w, bs, tr, 1)
    a2 = avg_max(t, w, bs, tr, 2)
    print("MAX — average busiest worker over %d trials vs the mean" % tr)
    print("-" * 62)
    print("  mean load:          %.1f" % mean)
    print("  one choice avg max: %.2f   (%.1fx the mean)" % (a1, a1 / mean))
    print("  two choices avg max:%.2f   (%.1fx the mean)" % (a2, a2 / mean))
    print("-" * 62)
    print("  the tail worker sets latency; two choices cuts the average peak from %.2f to %.2f." % (a1, a2))


def check(data):
    print("SELF-TEST — one choice overshoots the mean; two choices cuts the average max; the target mean is fixed")
    print("-" * 104)
    t, w, bs, tr = data["tasks"], data["workers"], data["base_seed"], data["trials"]
    mean = t / w
    a1 = avg_max(t, w, bs, tr, 1)
    a2 = avg_max(t, w, bs, tr, 2)

    one_overshoots = a1 > 1.5 * mean
    print("  one choice's average max is well above the mean = %s (%.2f > %.1f)" % (one_overshoots, a1, 1.5 * mean))

    two_cuts_max = a2 < a1
    print("  two choices lowers the average max = %s (%.2f < %.2f)" % (two_cuts_max, a2, a1))

    two_closer_to_mean = (a2 - mean) < (a1 - mean) / 2
    print("  two choices more than halves the gap to the mean = %s (%.2f < %.2f)" % (two_closer_to_mean, a2 - mean, (a1 - mean) / 2))

    total_conserved = sum(dispatch(t, w, bs, 1)) == sum(dispatch(t, w, bs, 2)) == t
    print("  every trial places all tasks (total load conserved) = %s (%d)" % (total_conserved, t))

    a1_again = avg_max(t, w, bs, tr, 1)
    deterministic = a1 == a1_again
    print("  the seeded average is reproducible = %s (%.4f)" % (deterministic, a1))

    ok = one_overshoots and two_cuts_max and two_closer_to_mean and total_conserved and deterministic
    print("-" * 104)
    print("SELF-TEST %s  one_overshoots=%s  two_cuts_max=%s  two_closer_to_mean=%s  total_conserved=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", one_overshoots, two_cuts_max, two_closer_to_mean, total_conserved, deterministic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Power of two choices: sampling two workers and taking the less loaded collapses the expected max load versus one random choice.")
    p.add_argument("--dispatch", action="store_true")
    p.add_argument("--max", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tasks=%d  workers=%d  mean=%.1f  trials=%d  file=%s  (the parameters are a fixture)"
          % (data["tasks"], data["workers"], data["tasks"] / data["workers"], data["trials"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.dispatch:
        dispatch_view(data)
    elif args.max:
        max_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
