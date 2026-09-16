"""Summarize possibly-contaminated data with the median (or a trimmed mean), not the mean -- the mean has a breakdown point of zero, so a single erroneous value drags it arbitrarily far, while the median needs a majority of the data corrupted before it moves out of range.

The breakdown point of an estimator is the fraction of the data you must corrupt to send the estimate arbitrarily far from the truth. It is a measure of how much bad data the summary can survive. For the mean, that fraction is zero: the mean is a sum divided by n, so one term pushed large enough dominates the sum and the mean follows it without bound. A single data-entry typo, a sensor that pegged, a field parsed wrong -- one bad point -- and the mean is wherever that point drags it.

The median is built differently. It is the middle value in sorted order, so a corrupted point does not enter an arithmetic total; it only changes which value sits in the middle. Push one point to a billion and the median shifts by at most one position. To move the median outside the range of the clean data you have to corrupt more than half the points -- its breakdown point is one half, the highest any estimator can have. The median does not care how large the bad value is, only how many bad values there are.

This is not the skewed-data question a companion module answers. There the long tail is real, the mean is the correct estimator for a total, and the median describes the typical case -- both are right for their job. Here the outlier is an error, not signal, and the mean is simply wrong: it reports a number no clean data point is near, produced entirely by the contamination. The distinction is whether the extreme value is real (use the mean for totals) or a defect (use a robust estimator).

Because almost every real dataset contains at least one error, the practical rule is to reach for a robust summary -- the median, or a trimmed mean that drops the extremes before averaging -- whenever the data has not been verified clean, and to treat a mean far from the median as a signal to go look for a bad value.

On this fixture five clean values around 12 get one injected outlier of growing size. The mean chases the outlier to 176, then to over 1600; the median stays at 12.5 no matter how large the outlier. This computes both, and the breakdown counts.

  --outlier    the mean and median of the clean data vs with one outlier of each size
  --breakdown  the mean and median as more of the data is corrupted, and when each moves out of range
  --check      one outlier wrecks the mean but not the median; the median survives a minority of corruption and breaks only at a majority

clean and outlier_sizes are the fixture; the mean and median under one outlier and under increasing corruption are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "breakdown.json"

BIG = 10 ** 9


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2


def corrupt(clean, k, big=BIG):
    """Replace the first k values with a huge contaminating value."""
    return [big] * k + list(clean[k:])


def in_range(value, clean):
    return min(clean) <= value <= max(clean)


# ----------------------------------------------------------------- printing

def outlier_view(data):
    clean = data["clean"]
    print("OUTLIER — one contaminating point added to clean data %s" % clean)
    print("-" * 56)
    print("  data                       mean        median")
    print("  %-25s  %-10.2f  %.2f" % ("clean", mean(clean), median(clean)))
    for o in data["outlier_sizes"]:
        d = clean + [o]
        print("  %-25s  %-10.2f  %.2f" % ("+ outlier %d" % o, mean(d), median(d)))
    print("-" * 56)
    print("  the mean chases the outlier without bound; the median barely moves")


def breakdown_view(data):
    clean = data["clean"]
    n = len(clean)
    print("BREAKDOWN — corrupt k of %d points to a huge value" % n)
    print("-" * 56)
    print("  k    mean            median        median in clean range?")
    for k in range(0, n + 1):
        d = corrupt(clean, k)
        print("  %-3d  %-15.2f %-13.2f %s" % (k, mean(d), median(d), in_range(median(d), clean)))
    print("-" * 56)
    print("  the mean leaves the range at k=1; the median only when k exceeds n/2")


def check(data):
    print("SELF-TEST — one outlier wrecks the mean but not the median; the median survives a minority of corruption and breaks only at a majority")
    print("-" * 112)
    clean = data["clean"]
    n = len(clean)

    with_one = clean + [1000]
    outlier_wrecks_mean = not in_range(mean(with_one), clean)
    print("  one outlier pushes the mean out of the clean range = %s (mean %.2f, range [%d, %d])"
          % (outlier_wrecks_mean, mean(with_one), min(clean), max(clean)))

    outlier_spares_median = in_range(median(with_one), clean)
    print("  the median stays in the clean range with that outlier = %s (median %.2f)" % (outlier_spares_median, median(with_one)))

    means = [mean(clean + [o]) for o in data["outlier_sizes"]]
    mean_tracks_outlier_size = means[0] < means[1] < means[2]
    print("  the mean grows without bound as the outlier grows = %s (%s)" % (mean_tracks_outlier_size, [round(m) for m in means]))

    medians = [median(clean + [o]) for o in data["outlier_sizes"]]
    median_invariant_to_outlier_size = medians[0] == medians[1] == medians[2]
    print("  the median is unchanged by the outlier's size = %s (%.2f)" % (median_invariant_to_outlier_size, medians[0]))

    minority = (n - 1) // 2                       # fewer than half
    majority = n // 2 + 1                         # more than half
    median_needs_majority = in_range(median(corrupt(clean, minority)), clean) and not in_range(median(corrupt(clean, majority)), clean)
    print("  median survives %d corrupted (minority) but breaks at %d (majority) = %s"
          % (minority, majority, median_needs_majority))

    ok = (outlier_wrecks_mean and outlier_spares_median and mean_tracks_outlier_size
          and median_invariant_to_outlier_size and median_needs_majority)
    print("-" * 112)
    print("SELF-TEST %s  outlier_wrecks_mean=%s  outlier_spares_median=%s  mean_tracks_outlier_size=%s  median_invariant_to_outlier_size=%s  median_needs_majority=%s"
          % ("PASS" if ok else "FAIL", outlier_wrecks_mean, outlier_spares_median, mean_tracks_outlier_size,
             median_invariant_to_outlier_size, median_needs_majority))
    return ok


def main():
    p = argparse.ArgumentParser(description="Breakdown point: summarize possibly-contaminated data with the median or a trimmed mean, not the mean, because the mean has a breakdown point of zero -- one erroneous value drags it arbitrarily far -- while the median needs a majority of the data corrupted before it moves out of range.")
    p.add_argument("--outlier", action="store_true")
    p.add_argument("--breakdown", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("clean=%s  outlier_sizes=%s  file=%s  (these are a fixture)" % (data["clean"], data["outlier_sizes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.outlier:
        outlier_view(data)
    elif args.breakdown:
        breakdown_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
