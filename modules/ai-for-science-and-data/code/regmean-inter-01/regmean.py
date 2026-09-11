"""Extreme scores regress to the mean on retest -- so an 'intervention' on the worst looks effective when nothing was done.

Any noisy measurement is part signal and part luck: a test score is ability plus how the questions fell that day, a
month's sales is the salesperson plus which deals happened to close. When you pick out the MOST extreme scores -- the very
highest or the very lowest -- you are selecting for cases where the luck was also extreme, because a record-high score
usually needed both high ability AND good luck to line up. Luck does not repeat. So on a second measurement the same
subjects keep their ability but get average luck, and their scores move back toward the middle: the top performers
decline, the bottom performers rise, with nothing done to any of them. This is regression to the mean, and it is a
property of measuring the same noisy thing twice, not a story about the subjects.

It becomes a costly fallacy the moment you act on the extremes and then re-measure. Give the worst-performing group extra
coaching and they improve -- but they would have improved anyway, because their round-1 scores were unluckily low; the
coaching gets credit for regression. Praise or reward the best group and they decline -- so praise appears to hurt, and
punishment of the worst appears to help, which is exactly backwards and has misled real managers, teachers, and clinicians.
The tell is that the group's OVERALL mean did not change: the top came down and the bottom came up by similar amounts,
which is redistribution toward the center, not improvement. Without a control group -- subjects who were also extreme but
got no intervention -- you cannot separate a real treatment effect from the regression that happens for free.

On this fixture ten subjects are measured twice with no intervention, and the overall mean is exactly 100 in both rounds.
The top 3 by round 1 average 123.3, then 108.0 in round 2 -- down 15.3. The bottom 3 average 78.3, then 92.7 -- up 14.3.
Both groups moved toward the mean, the top is still above average (ability is real, so regression is partial), and the
overall mean never moved. This computes both.

  --regress    the top and bottom groups' round-1 vs round-2 averages -- top falls, bottom rises, overall mean flat
  --intervene  reframed as 'we coached the bottom group': the apparent +14.3 gain is regression, exposed by the untouched top
  --check      the top regresses down and the bottom regresses up while the overall mean is unchanged; the top stays above the mean

The two rounds of scores are the fixture; every group average and change is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "regmean.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def overall_mean(subjects, round_key):
    return mean([s[round_key] for s in subjects.values()])


def group_by_round1(subjects, k, top):
    """The k subjects with the highest (top=True) or lowest (top=False) round-1 score."""
    ordered = sorted(subjects, key=lambda name: subjects[name]["round1"], reverse=top)
    return ordered[:k]


def group_avg(subjects, names, round_key):
    return mean([subjects[n][round_key] for n in names])


# ----------------------------------------------------------------- printing

def regress_view(data):
    subs, k = data["subjects"], data["group_size"]
    top = group_by_round1(subs, k, True)
    bot = group_by_round1(subs, k, False)
    print("REGRESS — top and bottom %d by round 1, measured again (no intervention)" % k)
    print("-" * 66)
    print("  group    subjects       round1 avg   round2 avg   change")
    for label, g in (("top", top), ("bottom", bot)):
        a1, a2 = group_avg(subs, g, "round1"), group_avg(subs, g, "round2")
        print("  %-7s  %-13s  %-11.1f  %-11.1f  %+.1f" % (label, ",".join(g), a1, a2, a2 - a1))
    print("-" * 66)
    print("  overall mean: round1 %.1f -> round2 %.1f (unchanged) -- the groups moved toward it."
          % (overall_mean(subs, "round1"), overall_mean(subs, "round2")))


def intervene_view(data):
    subs, k = data["subjects"], data["group_size"]
    bot = group_by_round1(subs, k, False)
    top = group_by_round1(subs, k, True)
    gain = group_avg(subs, bot, "round2") - group_avg(subs, bot, "round1")
    drift = group_avg(subs, top, "round2") - group_avg(subs, top, "round1")
    print("INTERVENE — 'we coached the bottom group between rounds'")
    print("-" * 62)
    print("  bottom group round1 -> round2: %.1f -> %.1f  (apparent gain %+.1f)"
          % (group_avg(subs, bot, "round1"), group_avg(subs, bot, "round2"), gain))
    print("  but the UNTOUCHED top group moved %+.1f, and the overall mean is flat (%.1f)."
          % (drift, overall_mean(subs, "round2")))
    print("-" * 62)
    print("  the 'gain' is regression to the mean; only an untreated control group could reveal a real effect.")


def check(data):
    print("SELF-TEST — the top regresses down and the bottom regresses up while the overall mean is unchanged; the top stays above the mean")
    print("-" * 122)
    subs, k = data["subjects"], data["group_size"]
    top = group_by_round1(subs, k, True)
    bot = group_by_round1(subs, k, False)
    m1, m2 = overall_mean(subs, "round1"), overall_mean(subs, "round2")

    top_regresses_down = group_avg(subs, top, "round2") < group_avg(subs, top, "round1")
    print("  the top group's score falls on retest = %s (%.1f -> %.1f)"
          % (top_regresses_down, group_avg(subs, top, "round1"), group_avg(subs, top, "round2")))

    bottom_regresses_up = group_avg(subs, bot, "round2") > group_avg(subs, bot, "round1")
    print("  the bottom group's score rises on retest = %s (%.1f -> %.1f)"
          % (bottom_regresses_up, group_avg(subs, bot, "round1"), group_avg(subs, bot, "round2")))

    overall_mean_unchanged = abs(m1 - m2) < 1e-9
    print("  the overall mean is unchanged = %s (%.1f == %.1f)" % (overall_mean_unchanged, m1, m2))

    top_still_above_mean = group_avg(subs, top, "round2") > m2
    print("  the top group is still above the mean (partial regression) = %s (%.1f > %.1f)"
          % (top_still_above_mean, group_avg(subs, top, "round2"), m2))

    moved_toward_mean = top_regresses_down and bottom_regresses_up
    print("  both extreme groups moved toward the mean (regression signature) = %s" % moved_toward_mean)

    ok = top_regresses_down and bottom_regresses_up and overall_mean_unchanged and top_still_above_mean and moved_toward_mean
    print("-" * 122)
    print("SELF-TEST %s  top_regresses_down=%s  bottom_regresses_up=%s  overall_mean_unchanged=%s  top_still_above_mean=%s  moved_toward_mean=%s"
          % ("PASS" if ok else "FAIL", top_regresses_down, bottom_regresses_up, overall_mean_unchanged, top_still_above_mean, moved_toward_mean))
    return ok


def main():
    p = argparse.ArgumentParser(description="Regression to the mean: extreme measurements are extreme partly by luck, which does not repeat, so the highest scorers fall and the lowest rise on retest with no intervention; acting on the extremes then credits the treatment with regression, and only an untreated control group can separate a real effect from it.")
    p.add_argument("--regress", action="store_true")
    p.add_argument("--intervene", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("subjects=%d  group_size=%d  file=%s  (the two rounds of scores are a fixture)"
          % (len(data["subjects"]), data["group_size"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.regress:
        regress_view(data)
    elif args.intervene:
        intervene_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
