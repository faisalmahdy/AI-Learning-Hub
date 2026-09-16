"""Target the edge of ability -- items too easy or too hard teach almost nothing, and by the same amount.

Give a learner problems they already ace and they learn nothing: every success confirms what they knew.
Give them problems far beyond reach and they learn nothing either: every failure is noise they cannot
act on. The learning signal from an item is largest where the outcome is most uncertain -- where the
learner has roughly even odds -- because that is where the result actually resolves something. A tutor
that always serves easy wins feels good and wastes the session; one that always serves brutal problems
feels productive and wastes it too.

Model the learner with a skill level and each item with a difficulty; the chance of solving is the
logistic of (skill - difficulty), and the learning gain from an item is proportional to p*(1-p), which
peaks at p = 0.5 and vanishes as p approaches 0 or 1. Three policies pick difficulty relative to the
learner's CURRENT skill: too_easy sits well below it, too_hard well above it, targeted sits right at it.

Over 30 items the targeted policy keeps every item near even odds and climbs to skill 3.000. The
too-easy and too-hard policies both stall at 0.841 -- and the fact that they stall at the SAME value is
the point: an item you were 92% going to get right and one you were 8% going to get right carry the same
tiny amount of learning, because p*(1-p) is symmetric. This runs all three and reports the skill gained.

  --policies   the three difficulty policies and where each sits relative to the learner
  --run        the skill trajectory, mean success rate, and mean learning gain per policy
  --check      targeted beats both extremes; too-easy and too-hard waste the item equally

The policy offsets, learning rate, and item count are the fixture; every trajectory is computed. Stdlib.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "learning.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


# ------------------------------------------------------------- the learner simulation

def simulate(offset, start_skill, items, lr):
    """Run `items` steps of a policy that sets difficulty = current skill + offset. Returns (final, trace)."""
    skill = start_skill
    trace = []
    for _ in range(items):
        difficulty = skill + offset
        p = sigmoid(skill - difficulty)   # success probability on this item
        gain = lr * p * (1 - p)           # learning signal, maximal at p = 0.5
        skill += gain
        trace.append((p, gain, skill))
    return skill, trace


def mean_success(trace):
    return sum(step[0] for step in trace) / len(trace)


def mean_gain(trace):
    return sum(step[1] for step in trace) / len(trace)


# ----------------------------------------------------------------- printing

def policies_view(data):
    print("POLICIES — difficulty each sets, relative to the learner's current skill")
    print("-" * 56)
    for name, off in data["policies"].items():
        where = "at skill (even odds)" if off == 0 else ("%.1f below skill" % -off if off < 0 else "%.1f above skill" % off)
        print("  %-10s offset %+.1f   -> %s" % (name, off, where))
    print("-" * 56)
    print("  start skill=%.1f, %d items, learning rate=%.1f."
          % (data["start_skill"], data["items"], data["learning_rate"]))


def run_view(data):
    s0, n, lr = data["start_skill"], data["items"], data["learning_rate"]
    print("RUN — skill gained over %d items, per policy" % n)
    print("-" * 62)
    print("  policy      final skill   mean success   mean gain/item")
    for name, off in data["policies"].items():
        final, trace = simulate(off, s0, n, lr)
        print("  %-10s %8.3f      %8.3f       %8.4f" % (name, final, mean_success(trace), mean_gain(trace)))
    print("-" * 62)
    print("  targeted keeps success near 0.5 and learns most; the extremes stall together.")


def check(data):
    print("SELF-TEST — targeted beats both extremes; too-easy and too-hard waste the item equally")
    print("-" * 84)
    s0, n, lr = data["start_skill"], data["items"], data["learning_rate"]
    pol = data["policies"]

    easy, _ = simulate(pol["too_easy"], s0, n, lr)
    targ, targ_trace = simulate(pol["targeted"], s0, n, lr)
    hard, _ = simulate(pol["too_hard"], s0, n, lr)

    targeted_wins = targ > easy and targ > hard
    print("  the targeted policy gains the most skill = %s (targeted %.3f vs easy %.3f, hard %.3f)"
          % (targeted_wins, targ, easy, hard))

    extremes_equal = abs(easy - hard) < 1e-9
    print("  too-easy and too-hard stall at the SAME skill = %s (%.3f = %.3f)" % (extremes_equal, easy, hard))

    targeted_even_odds = abs(mean_success(targ_trace) - 0.5) < 1e-9
    print("  the targeted policy keeps success at even odds = %s (mean p %.3f)"
          % (targeted_even_odds, mean_success(targ_trace)))

    big_margin = targ > 2 * easy
    print("  targeting more than doubles the skill of either extreme = %s (%.3f vs %.3f)" % (big_margin, targ, easy))

    ok = targeted_wins and extremes_equal and targeted_even_odds and big_margin
    print("-" * 84)
    print("SELF-TEST %s  targeted_wins=%s  extremes_equal=%s  targeted_even_odds=%s  big_margin=%s"
          % ("PASS" if ok else "FAIL", targeted_wins, extremes_equal, targeted_even_odds, big_margin))
    return ok


def main():
    p = argparse.ArgumentParser(description="Target the edge of ability -- extremes teach almost nothing.")
    p.add_argument("--policies", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("policies=%s  items=%d  lr=%.1f  file=%s  (the policies and rates are a fixture)"
          % (list(data["policies"]), data["items"], data["learning_rate"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.policies:
        policies_view(data)
    elif args.run:
        run_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
