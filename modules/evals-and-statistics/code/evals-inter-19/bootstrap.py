"""Bootstrap a confidence interval, or a single eval score hides how much it would move on other cases.

An eval gives you one number: the model passed 6 of 8 cases, so the score is 0.75. Reported alone, that number
pretends to be exact. But you evaluated on 8 particular cases; a different 8 cases would give a different score,
and with only 8 you have very little idea where the true pass rate sits. The point estimate carries no sense of
that wobble, so a 0.75 from 8 cases and a 0.75 from 8000 cases look identical on the dashboard while meaning
wildly different things.

The bootstrap measures the wobble without any formula or distribution assumption. Resample your cases WITH
REPLACEMENT to make a new eval set the same size, compute the score on it, and repeat thousands of times. The
spread of those resampled scores approximates how the score would vary across different samples of cases, and
the 2.5th and 97.5th percentiles of that spread are a 95% confidence interval. It works for any metric -- a
mean, an F1, a win rate -- not just proportions, which is why it is the general tool. Seed the random generator
so the interval is reproducible: the bootstrap is random, and an unseeded one gives a different interval every
run.

On this fixture the score is 0.75 from 8 cases. The bootstrap 95% interval is about [0.375, 1.0] -- enormous,
because 8 cases pin down almost nothing. The point 0.75 clears a 0.6 bar, but the interval's lower bound is
0.375, well below 0.6, so you CANNOT conclude the model is above the bar. This computes both.

  --resample   a few bootstrap resamples and their scores, then the interval
  --interval   the point estimate, the 95%% interval, its width, and the threshold decision
  --check      the point hides the spread; the bootstrap interval is wide and reproducible under the seed

The scores, seed, and resample count are the fixture; every interval is computed. Stdlib only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "scores.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def resample(scores, rng):
    """One bootstrap replica: draw len(scores) cases with replacement."""
    n = len(scores)
    return [scores[rng.randrange(n)] for _ in range(n)]


def bootstrap_interval(scores, seed, b):
    """The 95% percentile interval of the resampled means, using a seeded RNG for reproducibility."""
    rng = random.Random(seed)
    means = sorted(mean(resample(scores, rng)) for _ in range(b))
    lo = means[int(0.025 * b)]
    hi = means[int(0.975 * b) - 1]
    return lo, hi


# ----------------------------------------------------------------- printing

def resample_view(data):
    scores, seed, b = data["scores"], data["seed"], data["resamples"]
    rng = random.Random(seed)
    print("RESAMPLE — a few bootstrap replicas of %s (point %.3f)" % (scores, mean(scores)))
    print("-" * 62)
    for i in range(5):
        r = resample(scores, rng)
        print("  replica %d: %s  score %.3f" % (i + 1, r, mean(r)))
    lo, hi = bootstrap_interval(scores, seed, b)
    print("-" * 62)
    print("  across %d replicas the 95%% interval is [%.3f, %.3f]." % (b, lo, hi))


def interval_view(data):
    scores, seed, b, thr = data["scores"], data["seed"], data["resamples"], data["threshold"]
    point = mean(scores)
    lo, hi = bootstrap_interval(scores, seed, b)
    print("INTERVAL — point estimate, 95%% bootstrap interval, and the %.2f decision" % thr)
    print("-" * 62)
    print("  cases:            %d" % len(scores))
    print("  point estimate:   %.3f" % point)
    print("  95%% interval:     [%.3f, %.3f]   width %.3f" % (lo, hi, hi - lo))
    print("  above %.2f?  point says %s, but the interval reaches down to %.3f" % (thr, "yes" if point > thr else "no", lo))
    print("-" * 62)
    print("  the point clears the bar; the interval cannot rule out being below it.")


def check(data):
    print("SELF-TEST — the point hides the spread; the bootstrap interval is wide and reproducible under the seed")
    print("-" * 104)
    scores, seed, b, thr = data["scores"], data["seed"], data["resamples"], data["threshold"]
    point = mean(scores)
    lo, hi = bootstrap_interval(scores, seed, b)

    point_is_mean = point == mean(scores)
    print("  the point estimate is the mean score = %s (%.3f)" % (point_is_mean, point))

    interval_contains_point = lo <= point <= hi
    print("  the interval contains the point estimate = %s ([%.3f, %.3f])" % (interval_contains_point, lo, hi))

    interval_is_wide = (hi - lo) > 0.3
    print("  the interval is wide (small eval) = %s (width %.3f)" % (interval_is_wide, hi - lo))

    lower_below_threshold = lo < thr < point
    print("  the point clears %.2f but the lower bound does not = %s (%.3f < %.2f < %.3f)" % (thr, lower_below_threshold, lo, thr, point))

    reproducible = bootstrap_interval(scores, seed, b) == (lo, hi)
    print("  the seeded interval reproduces exactly = %s" % reproducible)

    ok = point_is_mean and interval_contains_point and interval_is_wide and lower_below_threshold and reproducible
    print("-" * 104)
    print("SELF-TEST %s  point_is_mean=%s  interval_contains_point=%s  interval_is_wide=%s  lower_below_threshold=%s  reproducible=%s"
          % ("PASS" if ok else "FAIL", point_is_mean, interval_contains_point, interval_is_wide, lower_below_threshold, reproducible))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bootstrap a confidence interval for an eval metric so a point estimate does not overstate certainty.")
    p.add_argument("--resample", action="store_true")
    p.add_argument("--interval", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cases=%d  seed=%d  resamples=%d  threshold=%.2f  file=%s  (the scores are a fixture)"
          % (len(data["scores"]), data["seed"], data["resamples"], data["threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.resample:
        resample_view(data)
    elif args.interval:
        interval_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
