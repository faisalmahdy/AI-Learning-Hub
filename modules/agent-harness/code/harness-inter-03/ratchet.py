#!/usr/bin/env python3
"""A self-improvement loop that keeps a learned skill only if it measurably helps.

An agent reflects on a finished transcript and compiles a candidate skill. The
question every self-improvement loop dodges: does the skill actually improve
outcomes? Here the ratchet runs a paired before/after eval (the same tasks with
and without the skill) and keeps the skill only when the paired difference clears
zero -- the interval and sign test from evals-inter-01, pointed at a keep/reject
decision instead of a leaderboard.

  --evaluate SKILL   the before/after pass rates and the paired difference + CI
  --ratchet          the KEEP / REJECT decision for both candidate skills
  --naive            the "keep it if it ever helped" ratchet (the trap)
  --check            paired difference two ways, the point-estimate bug, seeds

Stdlib only (math.comb). No network, no model calls -- the runs are a fixture in
skills.json; the bootstrap is seeded. Point it at your own before/after runs.
"""
import argparse
import json
import random
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_FILE = HERE / "skills.json"

SEED = 0
BOOT = 10000


def load():
    data = json.loads(SKILLS_FILE.read_text(encoding="utf-8"))
    base = [int(c) for c in data["baseline"]]
    cands = {k: [int(c) for c in v] for k, v in data["candidates"].items()}
    return base, cands


def percentile(sorted_xs, q):
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


def mean(xs):
    return sum(xs) / len(xs)


# ----------------------------------------------------- paired stats (inter-01)

def paired_diffs(base, skill):
    """skill outcome minus baseline outcome, per task. Paired: same task both."""
    return [skill[i] - base[i] for i in range(len(base))]


def bootstrap_diff_ci(base, skill, rng):
    n = len(base)
    d = paired_diffs(base, skill)
    boots = []
    for _ in range(BOOT):
        s = 0
        for _ in range(n):
            s += d[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def sign_test(base, skill):
    d = paired_diffs(base, skill)
    wins = sum(1 for x in d if x > 0)
    losses = sum(1 for x in d if x < 0)
    n = wins + losses
    tail = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n) if n else 1.0
    return wins, losses, len(base) - wins - losses, tail


# ---------------------------------------------------------- the ratchet rules

def keep_measured(base, skill, rng):
    """KEEP only if the paired improvement clears zero AND the sign test agrees."""
    lo, hi = bootstrap_diff_ci(base, skill, rng)
    _, _, _, p = sign_test(base, skill)
    return (lo > 0) and (p < 0.05), (lo, hi, p)


def keep_naive(base, skill):
    """The trap: keep the skill if it helped on ANY task."""
    wins, _, _, _ = sign_test(base, skill)
    return wins > 0


def keep_point_estimate(base, skill):
    """THE BUG: keep the skill if its raw gain is positive, ignoring the interval."""
    return mean(skill) - mean(base) > 0


# ------------------------------------------------------------------- printing

def evaluate(base, cands):
    print("BEFORE/AFTER — paired eval of each candidate skill")
    print("-" * 66)
    for name, skill in cands.items():
        rng = random.Random(SEED)
        lo, hi = bootstrap_diff_ci(base, skill, rng)
        w, l, t, p = sign_test(base, skill)
        print("  %-8s baseline %.2f -> with-skill %.2f   diff %+.2f  CI [%+.2f, %+.2f]"
              % (name, mean(base), mean(skill), mean(skill) - mean(base), lo, hi))
        print("           helps %d, hurts %d, ties %d   sign p=%.4f" % (w, l, t, p))
    print("-" * 66)
    print("  same 20 tasks, run with and without each skill; the diff is paired.")


def ratchet(base, cands):
    print("THE RATCHET — keep a skill only if it measurably helps")
    print("-" * 66)
    for name, skill in cands.items():
        rng = random.Random(SEED)
        keep, (lo, hi, p) = keep_measured(base, skill, rng)
        verdict = "KEEP" if keep else "REJECT"
        print("  %-8s diff %+.2f  CI [%+.2f, %+.2f]  sign p=%.4f  ->  %s"
              % (name, mean(skill) - mean(base), lo, hi, p, verdict))
    print("-" * 66)
    print("  KEEP needs the CI to clear zero. skill_B changed 11 tasks and still")
    print("  cannot: its gain is inside the noise, so the ratchet does not click.")


def naive(base, cands):
    print("THE NAIVE RATCHET — keep it if it ever helped (the trap)")
    print("-" * 66)
    for name, skill in cands.items():
        kept = keep_naive(base, skill)
        w, _, _, _ = sign_test(base, skill)
        print("  %-8s helped %2d tasks -> %s" % (name, w, "KEEP" if kept else "REJECT"))
    print("-" * 66)
    print("  both kept. This is how a skill library fills with unmeasured cruft:")
    print("  every skill helped *somewhere*, so every skill stays forever.")


def check(base, cands):
    print("SELF-TEST — paired diff two ways, the point-estimate bug, determinism")
    print("-" * 66)
    skill = cands["skill_B"]
    d_a = mean(skill) - mean(base)
    d_b = mean(paired_diffs(base, skill))
    print("  skill_B diff via rate means   = %+.6f" % d_a)
    print("  skill_B diff via paired diffs  = %+.6f" % d_b)
    agree = abs(d_a - d_b) < 1e-9
    print("  routes agree                   = %s" % agree)

    # the bug: the point-estimate ratchet keeps skill_B; the measured one rejects it.
    rng = random.Random(SEED)
    measured_keep, (lo, hi, p) = keep_measured(base, skill, rng)
    point_keep = keep_point_estimate(base, skill)
    print("  skill_B CI = [%+.2f, %+.2f], sign p=%.4f" % (lo, hi, p))
    print("  measured ratchet keeps skill_B = %s  (CI includes zero -> reject)" % measured_keep)
    print("  point-estimate ratchet keeps   = %s  (the bug: +0.05 > 0 -> keep)" % point_keep)
    bug_shows = (measured_keep is False) and (point_keep is True)

    lo1, hi1 = bootstrap_diff_ci(base, skill, random.Random(SEED))
    lo2, hi2 = bootstrap_diff_ci(base, skill, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  CI run 1 = [%+.2f, %+.2f]   CI run 2 = [%+.2f, %+.2f]   det = %s"
          % (lo1, hi1, lo2, hi2, deterministic))

    ok = agree and bug_shows and deterministic
    print("-" * 66)
    print("SELF-TEST %s  routes_agree=%s  bug_detectable=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, bug_shows, deterministic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Ratchet a learned skill on measured improvement.")
    for flag in ("evaluate", "ratchet", "naive", "check"):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()

    base, cands = load()
    print("tasks=%d  candidates=%s  file=%s  (runs are a fixture)"
          % (len(base), ",".join(cands), SKILLS_FILE.name))
    print("")

    if args.check:
        return 0 if check(base, cands) else 1
    if args.evaluate:
        evaluate(base, cands)
    elif args.ratchet:
        ratchet(base, cands)
    elif args.naive:
        naive(base, cands)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
