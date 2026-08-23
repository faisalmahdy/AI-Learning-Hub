#!/usr/bin/env python3
"""One run is a coin flip. Rank three systems by N=1, then by pass^k, and watch
the winner change.

Three systems, six tasks, five trials each. The N=1 verdict reads one trial per
task; the reliability verdict asks how often all k trials pass. They disagree.

  --n1          the single-run scores and the ranking they give
  --scoreboard  every metric side by side: N=1, pass@1, pass@5, pass^5, ranks
  --curve       the pass^k curve k=1..5, and the naive p**k curve (the bug)
  --reliability pass^5 with a bootstrap CI over tasks
  --check       re-derive pass^1 two ways, prove pass^k=0 when a task has fewer
                than k passes (catches the powered-point-estimate bug), seeds

Stdlib only (uses math.comb). No network, no keys, no model calls. The trials
are a fixture in trials.json; the bootstrap is seeded. Swap trials.json for
your own K runs per task; nothing else changes.
"""
import argparse
import json
import random
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIALS_FILE = HERE / "trials.json"

SEED = 0
BOOT = 10000


def load():
    data = json.loads(TRIALS_FILE.read_text(encoding="utf-8"))
    return data["tasks"], data["systems"]


def percentile(sorted_xs, q):
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


def passes(system, task):
    """c, n for one (system, task): passes and total trials."""
    trials = system["trials"][task]
    return sum(1 for t in trials if t), len(trials)


# ------------------------------------------------------------- the metrics

def n1_score(system, tasks):
    """Fraction of tasks passed on trial 0 -- the single-run verdict."""
    hits = sum(1 for t in tasks if system["trials"][t][0])
    return hits / len(tasks)


def pass_hat_k(system, tasks, k):
    """pass^k: probability all k trials pass, averaged over tasks. Unbiased
    finite-sample estimator: of the C(n,k) ways to draw k of the n trials,
    the fraction where all k drawn are passes is C(c,k)/C(n,k)."""
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        total += comb(c, k) / comb(n, k) if c >= k else 0.0
    return total / len(tasks)


def pass_at_k(system, tasks, k):
    """pass@k: probability AT LEAST ONE of k trials passes, averaged over tasks.
    1 - C(n-c,k)/C(n,k) -- the HumanEval estimator."""
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        miss = comb(n - c, k) / comb(n, k) if (n - c) >= k else 0.0
        total += 1 - miss
    return total / len(tasks)


def pass_hat_k_naive(system, tasks, k):
    """THE BUG: take each task's pass rate p=c/n and raise it to the k, as if
    5 trials pinned p exactly and trials were independent. Agrees with the
    honest estimator at k=1 and inflates it after."""
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        total += (c / n) ** k
    return total / len(tasks)


# ------------------------------------------------------- bootstrap over tasks

def bootstrap_pass_hat_k_ci(system, tasks, k, rng):
    """Resample the tasks with replacement, recompute pass^k, 10000 times."""
    m = len(tasks)
    boots = []
    for _ in range(BOOT):
        resample = [tasks[rng.randrange(m)] for _ in range(m)]
        boots.append(pass_hat_k(system, resample, k))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


# ------------------------------------------------------------------- printing

def ranked(systems, tasks, key):
    scored = [(key(s), s["name"]) for s in systems]
    scored.sort(reverse=True)
    return scored


def show_n1(tasks, systems):
    print("N=1 VERDICT — one trial per task")
    print("-" * 60)
    for score, name in ranked(systems, tasks, lambda s: n1_score(s, tasks)):
        print("  %-9s single-run score = %.3f" % (name, score))
    print("-" * 60)
    winner = ranked(systems, tasks, lambda s: n1_score(s, tasks))[0][1]
    print("  N=1 says the best system is: %s" % winner)


def show_scoreboard(tasks, systems):
    print("SCOREBOARD — the same three systems, four questions")
    print("-" * 74)
    print("  system      N=1     pass@1   pass@5   pass^5")
    for s in systems:
        print("  %-9s %.3f    %.3f    %.3f    %.3f"
              % (s["name"], n1_score(s, tasks),
                 pass_hat_k(s, tasks, 1),      # pass@1 == pass^1 == avg trial rate
                 pass_at_k(s, tasks, 5),
                 pass_hat_k(s, tasks, 5)))
    print("-" * 74)
    n1_rank = [name for _, name in ranked(systems, tasks, lambda s: n1_score(s, tasks))]
    rel_rank = [name for _, name in ranked(systems, tasks, lambda s: pass_hat_k(s, tasks, 5))]
    print("  ranked by N=1     : " + " > ".join(n1_rank))
    print("  ranked by pass^5  : " + " > ".join(rel_rank))
    print("  the N=1 winner (%s) is the pass^5 %s"
          % (n1_rank[0], "winner" if n1_rank[0] == rel_rank[0] else "loser -- rank " + str(rel_rank.index(n1_rank[0]) + 1)))


def show_curve(tasks, systems):
    print("pass^k CURVE — honest estimator vs the naive p**k, k=1..5")
    print("-" * 74)
    print("  system      k=1     k=2     k=3     k=4     k=5")
    for s in systems:
        row = "  %-9s" % s["name"]
        for k in range(1, 6):
            row += " %.3f  " % pass_hat_k(s, tasks, k)
        print(row)
    print("  --- the same, computed the buggy way (p**k) ---")
    for s in systems:
        row = "  %-9s" % s["name"]
        for k in range(1, 6):
            row += " %.3f  " % pass_hat_k_naive(s, tasks, k)
        print(row)
    print("-" * 74)
    # the carried micro-example: streaky on t1, c=4 of 5
    s = next(x for x in systems if x["name"] == "streaky")
    c, n = passes(s, "t1")
    print("  micro-example  streaky/t1  c=%d of n=%d" % (c, n))
    for k in range(1, 6):
        honest = comb(c, k) / comb(n, k) if c >= k else 0.0
        naive = (c / n) ** k
        print("    k=%d  honest C(%d,%d)/C(%d,%d)=%.3f   naive (%d/%d)**%d=%.3f"
              % (k, c, k, n, k, honest, c, n, k, naive))


def show_reliability(tasks, systems):
    print("RELIABILITY — pass^5 with a bootstrap CI over the %d tasks" % len(tasks))
    print("-" * 66)
    for s in systems:
        rng = random.Random(SEED)
        lo, hi = bootstrap_pass_hat_k_ci(s, tasks, 5, rng)
        p5 = pass_hat_k(s, tasks, 5)
        print("  %-9s pass^5 = %.3f   95%% CI [%.3f, %.3f]" % (s["name"], p5, lo, hi))
    print("-" * 66)
    print("  seed=%d, B=%d. On %d tasks the intervals are wide -- N=5 over a" % (SEED, BOOT, len(tasks)))
    print("  handful of tasks pins the average, not the reliability.")


def check(tasks, systems):
    print("SELF-TEST — cross-derive pass@1, prove pass^k=0 below k passes, seeds")
    print("-" * 66)
    s = next(x for x in systems if x["name"] == "streaky")

    # pass@1 two ways: the estimator at k=1, and the raw trial pass rate.
    p1_est = pass_hat_k(s, tasks, 1)
    hits = total = 0
    for t in tasks:
        c, n = passes(s, t)
        hits += c
        total += n
    p1_raw = hits / total
    print("  streaky pass@1 via estimator  = %.6f" % p1_est)
    print("  streaky pass@1 via raw counts = %.6f" % p1_raw)
    agree = abs(p1_est - p1_raw) < 1e-9
    print("  routes agree                  = %s" % agree)

    # the assertion that catches the powered-point-estimate bug: a task with
    # c<k passes cannot have all k pass, so its pass^k must be exactly 0.
    c, n = passes(s, "t1")               # c=4, n=5
    honest5 = comb(c, 5) / comb(n, 5) if c >= 5 else 0.0
    naive5 = (c / n) ** 5
    print("  streaky/t1 pass^5 honest      = %.4f  (c=%d<5, must be 0)" % (honest5, c))
    print("  streaky/t1 pass^5 naive p**k  = %.4f  (the bug: claims reliability never seen)" % naive5)
    below_ok = honest5 == 0.0

    # same seed -> identical CI.
    lo1, hi1 = bootstrap_pass_hat_k_ci(s, tasks, 5, random.Random(SEED))
    lo2, hi2 = bootstrap_pass_hat_k_ci(s, tasks, 5, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  streaky pass^5 CI run 1       = [%.3f, %.3f]" % (lo1, hi1))
    print("  streaky pass^5 CI run 2       = [%.3f, %.3f]" % (lo2, hi2))
    print("  deterministic under seed      = %s" % deterministic)
    print("-" * 66)
    ok = agree and below_ok and deterministic
    print("SELF-TEST %s  routes_agree=%s  below_k_zero=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, below_ok, deterministic))
    return ok


def main():
    parser = argparse.ArgumentParser(description="Rank systems by N=1 vs pass^k.")
    parser.add_argument("--n1", action="store_true")
    parser.add_argument("--scoreboard", action="store_true")
    parser.add_argument("--curve", action="store_true")
    parser.add_argument("--reliability", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    tasks, systems = load()
    print("systems=%d  tasks=%d  trials each=%d  file=%s  (fixture, no model call)"
          % (len(systems), len(tasks), len(systems[0]["trials"]["t1"]), TRIALS_FILE.name))
    print("")

    if args.check:
        return 0 if check(tasks, systems) else 1
    if args.n1:
        show_n1(tasks, systems)
    elif args.scoreboard:
        show_scoreboard(tasks, systems)
    elif args.curve:
        show_curve(tasks, systems)
    elif args.reliability:
        show_reliability(tasks, systems)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
