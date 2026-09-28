"""Advance on mastery, not on the clock -- fixed pacing lets prerequisite gaps compound down the chain.

Teach a chain of topics where each builds on the last -- fractions, then ratios, then algebra, functions,
calculus -- and the pacing policy decides whether the chain holds or collapses. FIXED PACING moves every
learner on a schedule: when a learner has not finished a topic, they advance anyway, carrying a gap. And
because the next topic stands on this one, the gap does not stay the same size -- it compounds. If a
learner reaches only 80% of each topic before being pushed on, their effective grasp of topic i is 80% of
their grasp of topic i-1, so the masteries multiply down the chain: 0.80, 0.64, 0.51, 0.41, 0.33. By the
fifth topic the learner is operating at a third of full mastery, lost not because the last topic was hard
but because four small gaps stacked.

MASTERY-BASED advancement breaks the compounding. Hold the learner on each topic until they reach the
target before advancing, so every topic rests on a fully-mastered prerequisite and nothing is carried
forward. It costs more time on the early topics, but the chain stays at 1.0 the whole way down instead of
decaying to a third. This computes the mastery of each topic under both policies.

  --chain      the topic chain and the two pacing policies
  --mastery    each topic's effective mastery, fixed pacing vs mastery-based
  --check      fixed pacing compounds the gaps to a fraction; mastery-based holds the chain at full

The chain and the per-topic fraction are the fixture; every topic mastery is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chain.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two pacing policies

def masteries_fixed(topics, per_topic):
    """Fixed pace: each topic reaches per_topic of the previous topic's mastery -- the gap compounds."""
    out = []
    m = 1.0
    for _ in topics:
        m *= per_topic
        out.append(round(m, 4))
    return out


def masteries_mastery(topics, target):
    """Mastery-based: hold until the target before advancing, so every topic rests on a full prerequisite."""
    out = []
    m = 1.0
    for _ in topics:
        m = m * target  # advancing only at mastery = 1.0 leaves m unchanged
        out.append(round(m, 4))
    return out


# ----------------------------------------------------------------- printing

def chain_view(data):
    print("CHAIN — %d topics, each a prerequisite for the next" % len(data["topics"]))
    print("-" * 54)
    print("  " + " -> ".join(data["topics"]))
    print("-" * 54)
    print("  fixed pace: reach %.0f%% of each topic then advance."
          % (data["fixed_per_topic"] * 100))
    print("  mastery-based: hold until %.0f%% before advancing." % (data["mastery_target"] * 100))


def mastery_view(data):
    topics = data["topics"]
    fx = masteries_fixed(topics, data["fixed_per_topic"])
    ms = masteries_mastery(topics, data["mastery_target"])
    print("MASTERY — effective grasp of each topic, fixed pace vs mastery-based")
    print("-" * 56)
    print("  topic          fixed pace    mastery-based")
    for t, f, m in zip(topics, fx, ms):
        print("  %-12s   %.3f          %.3f" % (t, f, m))
    print("-" * 56)
    print("  fixed pace decays down the chain; mastery-based holds at full.")


def check(data):
    print("SELF-TEST — fixed pacing compounds the gaps to a fraction; mastery-based holds the chain at full")
    print("-" * 92)
    topics = data["topics"]
    per_topic, target = data["fixed_per_topic"], data["mastery_target"]
    fx = masteries_fixed(topics, per_topic)
    ms = masteries_mastery(topics, target)

    fixed_decays = all(fx[i] < fx[i - 1] for i in range(1, len(fx)))
    print("  fixed pacing's mastery falls at every step (gaps compound) = %s (%s)" % (fixed_decays, fx))

    fixed_last_is_fraction = fx[-1] < 0.4
    print("  by the last topic the fixed-pace learner is at a fraction = %s (%.3f)" % (fixed_last_is_fraction, fx[-1]))

    mastery_holds = all(abs(m - 1.0) < 1e-9 for m in ms)
    print("  mastery-based stays at full mastery down the whole chain = %s (%s)" % (mastery_holds, ms))

    gap_widens = (ms[-1] - fx[-1]) > (ms[0] - fx[0])
    print("  the gap between the policies widens with depth = %s (%.3f at end vs %.3f at start)"
          % (gap_widens, ms[-1] - fx[-1], ms[0] - fx[0]))

    ok = fixed_decays and fixed_last_is_fraction and mastery_holds and gap_widens
    print("-" * 92)
    print("SELF-TEST %s  fixed_decays=%s  fixed_last_is_fraction=%s  mastery_holds=%s  gap_widens=%s"
          % ("PASS" if ok else "FAIL", fixed_decays, fixed_last_is_fraction, mastery_holds, gap_widens))
    return ok


def main():
    p = argparse.ArgumentParser(description="Advance on mastery, not the clock -- gaps compound under fixed pacing.")
    p.add_argument("--chain", action="store_true")
    p.add_argument("--mastery", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("topics=%d  fixed_per_topic=%.2f  mastery_target=%.2f  file=%s  (the chain is a fixture)"
          % (len(data["topics"]), data["fixed_per_topic"], data["mastery_target"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.chain:
        chain_view(data)
    elif args.mastery:
        mastery_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
