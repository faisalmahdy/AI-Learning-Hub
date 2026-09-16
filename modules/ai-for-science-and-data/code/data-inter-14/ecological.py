"""The ecological fallacy -- a correlation of group averages can be the opposite of the individual one.

You have data grouped into units -- regions, schools, cohorts -- and you compute a correlation on the
group averages: average income against average vote, mean class size against mean score. It comes out
strong and positive, and it is tempting to conclude the same about individuals: richer people vote this
way, smaller classes help each student. That inference is the ecological fallacy. A correlation computed on
group averages describes the groups, not the people inside them, and the two can differ in magnitude and
even in sign. Averaging throws away all the within-group variation -- exactly the variation that carries
the individual-level relationship -- and keeps only the between-group trend, which can point the other way.

The classic shape: within every group, x and y move opposite (as one person's x rises, their y falls), so
the individual correlation is negative. But the groups are arranged so that groups with a higher average x
also have a higher average y, so the correlation of the averages is positive. Look only at the group
averages and you would swear x and y move together; look inside any group and they move apart. The
aggregate correlation is not a weak version of the individual one -- it is a different quantity that here
has the opposite sign.

This is not Simpson's paradox (a reversal in categorical rates when you pool or split); it is the
continuous-correlation version of the same warning: a relationship measured at one level of aggregation
does not transfer to another. On this fixture three groups each have a within-group correlation of -0.80,
while the correlation of the three group means is +1.00. Same data; the aggregate says +1, the individuals
say -0.8. This computes both.

  --groups     each group's points and its own within-group correlation
  --levels     the individual (within-group) correlation vs the ecological (group-means) correlation
  --check      the within-group correlation is negative while the group-means correlation is positive

The grouped points are the fixture; every correlation is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "groups.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def correlation(xs, ys):
    """Pearson correlation of two equal-length lists."""
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(cov / (vx * vy), 3) if vx and vy else 0.0


def within_corr(group):
    return correlation([p[0] for p in group], [p[1] for p in group])


def group_mean(group):
    return (mean([p[0] for p in group]), mean([p[1] for p in group]))


def ecological_corr(groups):
    """Correlation of the group means -- the aggregate-level relationship."""
    means = [group_mean(g) for g in groups.values()]
    return correlation([m[0] for m in means], [m[1] for m in means])


def mean_within_corr(groups):
    """Average of the per-group (individual-level) correlations."""
    return round(mean([within_corr(g) for g in groups.values()]), 3)


# ----------------------------------------------------------------- printing

def groups_view(data):
    groups = data["groups"]
    print("GROUPS — each group's points and its own within-group correlation")
    print("-" * 60)
    for name, g in groups.items():
        mx, my = group_mean(g)
        print("  %s  points %s" % (name, g))
        print("      mean (%.1f, %.1f)   within-group corr %.2f" % (mx, my, within_corr(g)))
    print("-" * 60)
    print("  inside every group, y falls as x rises (negative).")


def levels_view(data):
    groups = data["groups"]
    print("LEVELS — the same data at two levels of aggregation")
    print("-" * 60)
    print("  individual (mean within-group) correlation:  %+.2f" % mean_within_corr(groups))
    print("  ecological (group-means) correlation:        %+.2f" % ecological_corr(groups))
    print("-" * 60)
    print("  the group means say +1; the people inside say -0.8. Opposite signs.")


def check(data):
    print("SELF-TEST — the within-group correlation is negative while the group-means correlation is positive")
    print("-" * 96)
    groups = data["groups"]
    within = mean_within_corr(groups)
    eco = ecological_corr(groups)

    within_negative = within < 0
    print("  the individual (within-group) correlation is negative = %s (%+.2f)" % (within_negative, within))

    ecological_positive = eco > 0
    print("  the ecological (group-means) correlation is positive = %s (%+.2f)" % (ecological_positive, eco))

    sign_flip = (within < 0) != (eco < 0)
    print("  the two levels have opposite signs = %s (%+.2f vs %+.2f)" % (sign_flip, within, eco))

    every_group_negative = all(within_corr(g) < 0 for g in groups.values())
    print("  every single group is negative internally = %s" % every_group_negative)

    gap = abs(eco - within)
    ecological_misleads = gap > 1.0
    print("  the aggregate misstates the individual by more than one full unit of correlation = %s (gap %.2f)" % (ecological_misleads, gap))

    ok = within_negative and ecological_positive and sign_flip and every_group_negative and ecological_misleads
    print("-" * 96)
    print("SELF-TEST %s  within_negative=%s  ecological_positive=%s  sign_flip=%s  every_group_negative=%s  ecological_misleads=%s"
          % ("PASS" if ok else "FAIL", within_negative, ecological_positive, sign_flip, every_group_negative, ecological_misleads))
    return ok


def main():
    p = argparse.ArgumentParser(description="The ecological fallacy: a group-averages correlation can be opposite the individual one.")
    p.add_argument("--groups", action="store_true")
    p.add_argument("--levels", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("groups=%d  points_per_group=%d  file=%s  (the grouped points are a fixture)"
          % (len(data["groups"]), len(next(iter(data["groups"].values()))), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.groups:
        groups_view(data)
    elif args.levels:
        levels_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
