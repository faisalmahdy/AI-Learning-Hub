#!/usr/bin/env python3
"""Interleave practice types, don't block them -- blocking wins the practice, interleaving the test.

Two learners practice the same three problem types the same number of times. One blocks --
all of type A, then all of B, then all of C (AAABBBCCC). One interleaves -- A, B, C, A, B, C
(ABCABC). Blocking feels better and scores better during practice, because within a block
every problem is the same type, so you are cued and fluent. Interleaving feels worse during
practice, because every problem is a switch and you have to first work out which method
applies. Then comes the delayed test: mixed problems, no cues, exactly like the real world --
and the interleaved learner crushes it, because the test is a discrimination task and
discrimination is the thing interleaving practiced and blocking never did.

The trap is selecting the practice schedule by how it scores during practice. That metric --
practice accuracy -- is a proxy, and it points the wrong way: it prefers blocking, which tests
worse. The metric that matters, the delayed mixed test, prefers interleaving. The whole
difference traces to one countable thing: the number of type-switches in the schedule, which is
how much discrimination each learner practiced. This computes both schedules' switch counts,
practice accuracy, and test accuracy, and shows the practice-best schedule is the test-worst.

  --schedules   each schedule, its type-switches, and the discrimination that implies
  --scores      practice accuracy vs delayed-test accuracy for both schedules
  --check       blocking wins practice while interleaving wins the test -- a reversal

The schedules and the learning-model constants are the fixture; every score is computed.
This is a stylized model of a replicated finding, deterministic. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "practice.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the mechanism: type-switches

def switches(seq):
    """How many trials differ in type from the trial before -- each is a discrimination rep."""
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])


def discrimination(seq):
    """Fraction of transitions that were switches: how much discrimination this schedule practiced."""
    return switches(seq) / (len(seq) - 1)


# ------------------------------------------------------------- the two outcomes

def practice_accuracy(seq, m):
    """During practice: execution minus a cost for every switch (interleaving feels harder)."""
    return m["exec_max"] - m["practice_switch_cost"] * discrimination(seq)


def test_accuracy(seq, m):
    """Delayed mixed test: execution times how well discrimination was practiced (the test needs it)."""
    return m["exec_max"] * (m["test_floor"] + (1 - m["test_floor"]) * discrimination(seq))


# ----------------------------------------------------------------- printing

def schedules_view(data):
    print("SCHEDULES — same 3 types, same reps each; the difference is the order")
    print("-" * 64)
    for s in data["schedules"]:
        seq = s["seq"]
        print("  %-12s %s" % (s["name"], "".join(seq)))
        print("     type-switches: %d of %d transitions   discrimination practiced: %.2f"
              % (switches(seq), len(seq) - 1, discrimination(seq)))
    print("-" * 64)
    print("  every switch is a rep at 'which method does this problem need?' -- the test's real task.")


def scores_view(data):
    m = data["model"]
    print("SCORES — practice accuracy (the proxy) vs delayed-test accuracy (the target)")
    print("-" * 64)
    print("  schedule     practice   delayed-test")
    for s in data["schedules"]:
        seq = s["seq"]
        print("  %-12s %.3f      %.3f" % (s["name"], practice_accuracy(seq, m), test_accuracy(seq, m)))
    print("-" * 64)
    print("  blocking looks better in practice and is worse on the test -- the metrics disagree.")


def check(data):
    print("SELF-TEST — blocking wins practice while interleaving wins the test (a reversal)")
    print("-" * 64)
    m = data["model"]
    sby = {s["name"]: s["seq"] for s in data["schedules"]}
    blk, inter = sby["blocked"], sby["interleaved"]

    # the mechanism: interleaving has many more type-switches
    more_switches = switches(inter) > switches(blk)
    print("  interleaving has more type-switches (more discrimination) = %s (%d vs %d)"
          % (more_switches, switches(inter), switches(blk)))

    blocking_wins_practice = practice_accuracy(blk, m) > practice_accuracy(inter, m)
    print("  blocking wins the PRACTICE score = %s (%.3f vs %.3f)"
          % (blocking_wins_practice, practice_accuracy(blk, m), practice_accuracy(inter, m)))

    interleaving_wins_test = test_accuracy(inter, m) > test_accuracy(blk, m)
    print("  interleaving wins the delayed TEST = %s (%.3f vs %.3f)"
          % (interleaving_wins_test, test_accuracy(inter, m), test_accuracy(blk, m)))

    # the reversal: whichever schedule wins practice loses the test
    practice_best = max(data["schedules"], key=lambda s: practice_accuracy(s["seq"], m))["name"]
    test_best = max(data["schedules"], key=lambda s: test_accuracy(s["seq"], m))["name"]
    reversal = practice_best != test_best
    print("  the practice-best schedule is NOT the test-best = %s (practice:%s, test:%s)"
          % (reversal, practice_best, test_best))

    ok = more_switches and blocking_wins_practice and interleaving_wins_test and reversal
    print("-" * 64)
    print("SELF-TEST %s  more_switches=%s  blocking_wins_practice=%s  interleaving_wins_test=%s  reversal=%s"
          % ("PASS" if ok else "FAIL", more_switches, blocking_wins_practice, interleaving_wins_test, reversal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Interleaving vs blocking: practice score vs delayed test.")
    p.add_argument("--schedules", action="store_true")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("schedules=%d  model=%s  file=%s  (schedules and model constants are a fixture)"
          % (len(data["schedules"]), data["model"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schedules:
        schedules_view(data)
    elif args.scores:
        scores_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
