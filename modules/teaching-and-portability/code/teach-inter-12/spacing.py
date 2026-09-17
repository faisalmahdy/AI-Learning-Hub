"""Space the reviews out -- massing the same number into one session retains almost nothing by the test.

Given a fixed amount of study, when you do it matters as much as how much. Three review sessions crammed
into one day (massed) and three spread across three weeks (distributed) are the same effort, but they do
not build the same memory. Model memory with a stability S -- roughly how many days until it fades --
where retention after a gap is exp(-gap/S). A review raises S, but by how much depends on spacing: a
review that comes after a real gap, when the memory has partly faded, is effortful and builds durable
stability; a review that comes right after another adds almost nothing, because there was nothing to
reconstruct. So massed reviews pile onto a memory that never got a chance to fade and barely grow its
stability, while spaced reviews each rebuild a faded memory and compound its stability.

Two effects then favor distributed practice. It builds more stability (each spaced review is effortful),
and it leaves the last review closer to the test (less time to decay before you are measured). Massing
loses on both: low stability and a long decay from the single early session to the test.

On this fixture three reviews are tested on day 30. Massed (all on day 0) ends at stability 5 and, decaying
for 30 days, retains just 0.0025 -- essentially forgotten. Distributed (days 0, 10, 20) builds stability up
to 15.5 and, decaying only 10 days from the last review, retains 0.52. Same three sessions; 0.25% versus
52%. This computes the stability and retention for both.

  --schedules  the two study schedules and the test day
  --retention  each schedule's final stability and retention at the test
  --check      distributed retains far more than massed for the same number of reviews

The schedules, test day, and starting stability are the fixture; every retention is computed. Stdlib.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "study.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def final_stability(schedule, start):
    """Build up memory stability across the reviews; a spaced review adds more than a massed one."""
    S = start
    last = None
    for day in schedule:
        if last is not None:
            gap = day - last
            # a review after a gap comparable to S is effortful and adds stability; gap 0 adds nothing
            S = S + S * (1 - math.exp(-gap / S))
        last = day
    return S


def retention(schedule, test_day, start):
    """Retention at the test: decay from the last review, over the stability built."""
    S = final_stability(schedule, start)
    last = schedule[-1]
    return math.exp(-(test_day - last) / S)


# ----------------------------------------------------------------- printing

def schedules_view(data):
    print("SCHEDULES — same number of reviews, tested on day %d" % data["test_day"])
    print("-" * 50)
    for name, sched in data["schedules"].items():
        print("  %-12s reviews on days %s   (last review day %d)" % (name, sched, sched[-1]))
    print("-" * 50)
    print("  both do %d reviews -- the only difference is when." % len(next(iter(data["schedules"].values()))))


def retention_view(data):
    t, s0 = data["test_day"], data["start_stability"]
    print("RETENTION — final stability and retention at day %d" % t)
    print("-" * 58)
    for name, sched in data["schedules"].items():
        S = final_stability(sched, s0)
        r = retention(sched, t, s0)
        print("  %-12s stability %5.2f   last review day %2d   retention %.4f" % (name, S, sched[-1], r))
    print("-" * 58)
    print("  distributed builds more stability and its last review is nearer the test.")


def check(data):
    print("SELF-TEST — distributed retains far more than massed for the same number of reviews")
    print("-" * 88)
    t, s0 = data["test_day"], data["start_stability"]
    massed, distributed = data["schedules"]["massed"], data["schedules"]["distributed"]

    r_massed = retention(massed, t, s0)
    r_dist = retention(distributed, t, s0)

    distributed_wins = r_dist > r_massed
    print("  distributed retains more than massed = %s (%.4f vs %.4f)" % (distributed_wins, r_dist, r_massed))

    same_effort = len(massed) == len(distributed)
    print("  both schedules use the same number of reviews = %s (%d each)" % (same_effort, len(massed)))

    distributed_more_stable = final_stability(distributed, s0) > final_stability(massed, s0)
    print("  distributed builds more stability = %s (%.2f vs %.2f)"
          % (distributed_more_stable, final_stability(distributed, s0), final_stability(massed, s0)))

    big_gap = r_dist > 10 * r_massed
    print("  the retention gap is large, not marginal = %s (%.0fx)" % (big_gap, r_dist / r_massed))

    ok = distributed_wins and same_effort and distributed_more_stable and big_gap
    print("-" * 88)
    print("SELF-TEST %s  distributed_wins=%s  same_effort=%s  distributed_more_stable=%s  big_gap=%s"
          % ("PASS" if ok else "FAIL", distributed_wins, same_effort, distributed_more_stable, big_gap))
    return ok


def main():
    p = argparse.ArgumentParser(description="Space the reviews out -- massing retains almost nothing.")
    p.add_argument("--schedules", action="store_true")
    p.add_argument("--retention", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("schedules=%s  test_day=%d  start_stability=%.1f  file=%s  (the schedules are a fixture)"
          % (list(data["schedules"]), data["test_day"], data["start_stability"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schedules:
        schedules_view(data)
    elif args.retention:
        retention_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
