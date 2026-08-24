#!/usr/bin/env python3
"""Same six checks, three ways to add them up — and three different winners.

Two systems graded by evals-basic-01's six-check rubric on the same 30 cases.
A and B pass the same NUMBER of checks, so the equal-weight mean ties them. But
A's failures are on critical checks (grounding, correctness, honesty) and B's on
cosmetic ones, so weighting or gating by what matters ranks B far ahead. The
aggregation function is part of the rubric, and it decides the verdict.

  --mean       equal-weight mean per case (what basic-01 did): the tie
  --weighted   weight critical checks 3x cosmetic: B pulls ahead
  --gate       a case passes only if every CRITICAL check passes: B routs A,
               with a paired bootstrap CI on the gap (from inter-01)
  --bug        the gate written 'fails only if ALL critical fail' (any/all swap)
  --all        the three aggregations and the winner under each
  --check      re-derive the mean two ways, prove the gate assertion, seeds

Stdlib only. No network, no keys, no model calls. Results are a fixture in
graded.json; the bootstrap is seeded. Point it at your own rubric results.
"""
import argparse
import json
import random
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADED_FILE = HERE / "graded.json"

SEED = 0
BOOT = 10000


def load():
    data = json.loads(GRADED_FILE.read_text(encoding="utf-8"))
    return data["_config"], data["cases"]


def percentile(sorted_xs, q):
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


def passed(case, system, config):
    """The set of check ids this system passed on this case."""
    order = config["order"]
    marks = case[system]
    return {order[i] for i, ch in enumerate(marks) if ch == "1"}


# ---------------------------------------------------------------- aggregations

def mean_score(case, system, config):
    """Fraction of the six checks passed. Every check weighted the same."""
    return len(passed(case, system, config)) / len(config["order"])


def weighted_score(case, system, config):
    """Sum of the weights of the passed checks, over the total weight."""
    w = config["weights"]
    got = sum(w[c] for c in passed(case, system, config))
    total = sum(w.values())
    return got / total


def gate_pass(case, system, config):
    """A case passes iff EVERY critical check passed. A cosmetic miss is fine;
    a critical miss fails the whole case."""
    p = passed(case, system, config)
    return all(c in p for c in config["critical"])


def gate_pass_buggy(case, system, config):
    """THE BUG: 'fails only if ALL critical checks fail' — an any/all swap.
    A case that fails a single critical check still passes, so ungrounded and
    wrong answers sail through."""
    p = passed(case, system, config)
    return not all(c not in p for c in config["critical"])


def aggregate(cases, system, config, fn):
    return sum(fn(c, system, config) for c in cases) / len(cases)


# --------------------------------------------------- paired gate CI (inter-01)

def gate_diffs(cases, config):
    """Per case, B's gate outcome minus A's (1/0/-1). Paired: same case both."""
    return [int(gate_pass(c, "b", config)) - int(gate_pass(c, "a", config)) for c in cases]


def bootstrap_gate_ci(cases, config, rng):
    n = len(cases)
    diffs = gate_diffs(cases, config)
    boots = []
    for _ in range(BOOT):
        s = 0
        for _ in range(n):
            s += diffs[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def sign_test(cases, config):
    d = gate_diffs(cases, config)
    wins = sum(1 for x in d if x > 0)
    losses = sum(1 for x in d if x < 0)
    n = wins + losses
    tail = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n) if n else 1.0
    return wins, losses, len(cases) - wins - losses, tail


# ------------------------------------------------------------------- printing

def rank(cases, config, fn):
    a = aggregate(cases, "a", config, fn)
    b = aggregate(cases, "b", config, fn)
    if abs(a - b) < 1e-9:
        return a, b, "TIE"
    return a, b, ("B" if b > a else "A")


def show_mean(cases, config):
    a, b, win = rank(cases, config, mean_score)
    print("EQUAL-WEIGHT MEAN (what basic-01 did)")
    print("-" * 60)
    print("  system A  = %.4f" % a)
    print("  system B  = %.4f" % b)
    print("  winner    = %s" % win)
    print("  every check counts the same, so a wrong answer and a formatting")
    print("  nitpick are both worth 1/6. A and B fail the same count -> tie.")


def show_weighted(cases, config):
    a, b, win = rank(cases, config, weighted_score)
    print("WEIGHTED MEAN (critical checks 3x, cosmetic 1x)")
    print("-" * 60)
    print("  system A  = %.4f" % a)
    print("  system B  = %.4f" % b)
    print("  winner    = %s" % win)
    print("  A's misses are on weight-3 checks, B's on weight-1 -> B pulls ahead.")


def show_gate(cases, config):
    a = aggregate(cases, "a", config, lambda c, s, cf: int(gate_pass(c, s, cf)))
    b = aggregate(cases, "b", config, lambda c, s, cf: int(gate_pass(c, s, cf)))
    rng = random.Random(SEED)
    lo, hi = bootstrap_gate_ci(cases, config, rng)
    wins, losses, ties, p = sign_test(cases, config)
    print("CRITICAL GATE (a case passes only if every critical check passes)")
    print("-" * 60)
    print("  system A gate-pass rate = %.4f" % a)
    print("  system B gate-pass rate = %.4f" % b)
    print("  paired difference B - A = %+.4f" % (b - a))
    print("  95%% CI (bootstrap)      = [%+.4f, %+.4f]  seed=%d, B=%d" % (lo, hi, SEED, BOOT))
    print("  CI clears zero          = %s" % (lo > 0 or hi < 0))
    print("  sign test: B passes %d cases A failed, A passes %d B failed, ties %d"
          % (wins, losses, ties))
    print("  sign-test p (exact)     = %.6f" % p)
    print("  winner = B, decisively: the mean called it a tie.")


def show_bug(cases, config):
    a_ok = aggregate(cases, "a", config, lambda c, s, cf: int(gate_pass(c, s, cf)))
    a_bug = aggregate(cases, "a", config, lambda c, s, cf: int(gate_pass_buggy(c, s, cf)))
    print("THE BUG — the gate written 'fails only if ALL critical fail'")
    print("-" * 60)
    print("  system A gate-pass, correct (any critical miss fails) = %.4f" % a_ok)
    print("  system A gate-pass, buggy  (only all-critical-miss fails) = %.4f" % a_bug)
    print("  the buggy gate passes every A case that failed just ONE critical")
    print("  check -- ungrounded and wrong answers sail through at %.0f%%." % (a_bug * 100))


def show_all(cases, config):
    print("THREE AGGREGATIONS OF THE SAME SIX CHECKS")
    print("-" * 60)
    ma, mb, mw = rank(cases, config, mean_score)
    wa, wb, ww = rank(cases, config, weighted_score)
    ga = aggregate(cases, "a", config, lambda c, s, cf: int(gate_pass(c, s, cf)))
    gb = aggregate(cases, "b", config, lambda c, s, cf: int(gate_pass(c, s, cf)))
    gw = "TIE" if abs(ga - gb) < 1e-9 else ("B" if gb > ga else "A")
    print("  aggregation        A        B        winner")
    print("  equal-weight mean  %.4f   %.4f   %s" % (ma, mb, mw))
    print("  weighted mean      %.4f   %.4f   %s" % (wa, wb, ww))
    print("  critical gate      %.4f   %.4f   %s" % (ga, gb, gw))
    print("-" * 60)
    print("  same 360 check results, three totals: from a dead TIE to a rout.")
    print("  the aggregation is not a display choice -- it is the rubric.")


def check(cases, config):
    print("SELF-TEST — re-derive the mean, prove the gate assertion, seeds")
    print("-" * 60)
    # mean two ways: per-case average, and one flat pool of all 180 checks.
    a_percase = aggregate(cases, "a", config, mean_score)
    total = hits = 0
    for c in cases:
        total += len(config["order"])
        hits += len(passed(c, "a", config))
    a_flat = hits / total
    print("  A mean via per-case    = %.6f" % a_percase)
    print("  A mean via flat pool   = %.6f" % a_flat)
    agree = abs(a_percase - a_flat) < 1e-9
    print("  routes agree           = %s" % agree)

    # the assertion: any case with a failed critical check must fail the gate.
    violations = 0
    for c in cases:
        for system in ("a", "b"):
            p = passed(c, system, config)
            missing_critical = any(cc not in p for cc in config["critical"])
            if missing_critical and gate_pass(c, system, config):
                violations += 1
    # and the buggy gate does violate it:
    bug_violations = 0
    for c in cases:
        for system in ("a", "b"):
            p = passed(c, system, config)
            missing_critical = any(cc not in p for cc in config["critical"])
            if missing_critical and gate_pass_buggy(c, system, config):
                bug_violations += 1
    print("  correct gate: critical-miss cases that still passed = %d  (must be 0)" % violations)
    print("  buggy gate:   critical-miss cases that still passed = %d  (the bug)" % bug_violations)
    gate_ok = violations == 0 and bug_violations > 0

    lo1, hi1 = bootstrap_gate_ci(cases, config, random.Random(SEED))
    lo2, hi2 = bootstrap_gate_ci(cases, config, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  gate CI run 1          = [%+.4f, %+.4f]" % (lo1, hi1))
    print("  gate CI run 2          = [%+.4f, %+.4f]" % (lo2, hi2))
    print("  deterministic          = %s" % deterministic)
    print("-" * 60)
    ok = agree and gate_ok and deterministic
    print("SELF-TEST %s  routes_agree=%s  gate_sound=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, gate_ok, deterministic))
    return ok


def main():
    parser = argparse.ArgumentParser(description="Aggregate a rubric three ways.")
    for flag in ("mean", "weighted", "gate", "bug", "all", "check"):
        parser.add_argument("--" + flag, action="store_true")
    args = parser.parse_args()

    config, cases = load()
    print("cases=%d  checks=%d  systems=A,B  file=%s  (results are a fixture)"
          % (len(cases), len(config["order"]), GRADED_FILE.name))
    print("")

    if args.check:
        return 0 if check(cases, config) else 1
    if args.mean:
        show_mean(cases, config)
    elif args.weighted:
        show_weighted(cases, config)
    elif args.gate:
        show_gate(cases, config)
    elif args.bug:
        show_bug(cases, config)
    elif args.all:
        show_all(cases, config)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
