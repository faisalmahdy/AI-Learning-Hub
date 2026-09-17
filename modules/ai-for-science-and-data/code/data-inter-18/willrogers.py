"""Relabel one member across two groups and BOTH group means can rise, though no value changed.

Two groups, a better-scoring one and a worse-scoring one. Take the weakest member of the better group -- a
value that is still above everything in the worse group -- and reclassify it into the worse group. No number
changed; you only moved a label. Yet the better group's mean goes UP (you removed its lowest member) and the
worse group's mean also goes UP (you added a member above its old average). Both group averages improve while
the whole population is byte-for-byte identical. This is the Will Rogers phenomenon, and it is exactly how
"stage migration" makes cancer survival statistics improve when a better scanner reclassifies patients without
curing anyone: each stage looks better because the borderline cases were shuffled, not treated.

The trap is comparing group means across a reclassification and reading the improvement as real. It is not a
real effect; it is an artifact of moving a value that sits BELOW the better group's mean but ABOVE the worse
group's mean. Removing it lifts the group it left; adding it lifts the group it joined. The population mean --
the only average over an unchanged set -- does not move at all. The fix is to hold the grouping fixed when you
compare, or to compare the population, not the subgroups, across a reclassification.

On this fixture 'good' is 8, 9, 10 (mean 9) and 'poor' is 1, 2, 3 (mean 2). Move the 8 -- below 9, above 2 --
into 'poor'. Good becomes 9, 10 (mean 9.5) and poor becomes 1, 2, 3, 8 (mean 3.5): both up, and the pooled
mean stays 5.5. This computes both.

  --means      each group's mean before and after the reclassification, and the pooled mean
  --condition  why both means rise: the moved value is below one mean and above the other
  --check      both group means rise while no value changes and the pooled mean is unchanged

The two groups and the moved value are the fixture; every mean is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "groups.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def reclassify(good, poor, v):
    """Move value v from good to poor without changing any number."""
    new_good = list(good)
    new_good.remove(v)
    new_poor = poor + [v]
    return new_good, new_poor


# ----------------------------------------------------------------- printing

def means_view(data):
    good, poor, v = data["good"], data["poor"], data["move_value"]
    ng, npr = reclassify(good, poor, v)
    pooled = good + poor
    print("MEANS — group means before and after moving %d from good to poor" % v)
    print("-" * 60)
    print("  good:   %s mean %.2f   ->   %s mean %.2f" % (good, mean(good), ng, mean(ng)))
    print("  poor:   %s mean %.2f   ->   %s mean %.2f" % (poor, mean(poor), npr, mean(npr)))
    print("  pooled: mean %.2f (%d values)   ->   mean %.2f (%d values)"
          % (mean(pooled), len(pooled), mean(ng + npr), len(ng + npr)))
    print("-" * 60)
    print("  both group means rise; the pooled mean does not move.")


def condition_view(data):
    good, poor, v = data["good"], data["poor"], data["move_value"]
    print("CONDITION — why both rise: the moved value straddles the two means")
    print("-" * 60)
    print("  moved value %d" % v)
    print("  poor mean %.2f  <  moved %d  <  good mean %.2f" % (mean(poor), v, mean(good)))
    print("  below good's mean -> removing it raises good")
    print("  above poor's mean -> adding it raises poor")
    print("-" * 60)
    print("  any value in that gap lifts both groups when moved down.")


def check(data):
    print("SELF-TEST — both group means rise while no value changes and the pooled mean is unchanged")
    print("-" * 100)
    good, poor, v = data["good"], data["poor"], data["move_value"]
    ng, npr = reclassify(good, poor, v)

    good_mean_rises = mean(ng) > mean(good)
    print("  the good group's mean rises = %s (%.2f -> %.2f)" % (good_mean_rises, mean(good), mean(ng)))

    poor_mean_rises = mean(npr) > mean(poor)
    print("  the poor group's mean rises = %s (%.2f -> %.2f)" % (poor_mean_rises, mean(poor), mean(npr)))

    moved_straddles = mean(poor) < v < mean(good)
    print("  the moved value is between the two means = %s (%.2f < %d < %.2f)" % (moved_straddles, mean(poor), v, mean(good)))

    no_value_changed = sorted(good + poor) == sorted(ng + npr)
    print("  the full set of values is unchanged = %s" % no_value_changed)

    pooled_mean_unchanged = abs(mean(good + poor) - mean(ng + npr)) < 1e-9
    print("  the pooled mean is unchanged = %s (%.2f)" % (pooled_mean_unchanged, mean(ng + npr)))

    ok = good_mean_rises and poor_mean_rises and moved_straddles and no_value_changed and pooled_mean_unchanged
    print("-" * 100)
    print("SELF-TEST %s  good_mean_rises=%s  poor_mean_rises=%s  moved_straddles=%s  no_value_changed=%s  pooled_mean_unchanged=%s"
          % ("PASS" if ok else "FAIL", good_mean_rises, poor_mean_rises, moved_straddles, no_value_changed, pooled_mean_unchanged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Reclassify one member across two groups and watch both means rise (Will Rogers phenomenon).")
    p.add_argument("--means", action="store_true")
    p.add_argument("--condition", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("good=%d values  poor=%d values  move=%d  file=%s  (the groups are a fixture)"
          % (len(data["good"]), len(data["poor"]), data["move_value"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.means:
        means_view(data)
    elif args.condition:
        condition_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
