#!/usr/bin/env python3
"""Is system B actually better than system A, or is the gap inside the noise?

Two systems graded on the SAME 30 cases (paired). This script answers the
question evals-basic-01 deferred: it puts an interval on every mean and a
significance test on the difference.

  --means        the two point means and their difference (no uncertainty)
  --marginal     bootstrap a 95% CI for each mean separately, then the
                 OVERLAP verdict (this is the planted bug: overlapping
                 marginal CIs do NOT mean 'no difference')
  --paired       bootstrap a 95% CI on the paired difference (the right CI)
                 and a paired permutation test for a p-value
  --all          every number, side by side, with the verdict of each method
  --check        re-derive the difference two ways and prove the bootstrap
                 is deterministic under its seed

Stdlib only. No network, no API keys, no model calls. The per-case scores are
fixtures in runs.json; the bootstrap and permutation draws are seeded, so
every run prints identical numbers. Change runs.json for your own two systems;
nothing else needs to change.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS_FILE = HERE / "runs.json"

SEED = 0            # fixes every random draw below; reported in the run stamp
BOOT = 10000        # bootstrap resamples
PERM = 10000        # permutation resamples
CHECKS_OUT_OF = 6   # each case is graded 0..6 by the evals-basic-01 rubric


def load_runs():
    data = json.loads(RUNS_FILE.read_text(encoding="utf-8"))
    cases = data["cases"]
    # per-case fraction of the six rubric checks passed, one number per system
    a = [c["a"] / CHECKS_OUT_OF for c in cases]
    b = [c["b"] / CHECKS_OUT_OF for c in cases]
    return cases, a, b


def mean(xs):
    return sum(xs) / len(xs)


def percentile(sorted_xs, q):
    """The q-th percentile (0..100) by nearest-rank on an already-sorted list."""
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


# --------------------------------------------------------------- point means

def means(a, b):
    ma, mb = mean(a), mean(b)
    return ma, mb, mb - ma


# ------------------------------------------------ marginal (per-mean) bootstrap

def bootstrap_mean_ci(xs, rng):
    """Resample the cases with replacement, recompute the mean, 10000 times.
    Return the 2.5th and 97.5th percentiles: a 95% CI for THIS mean alone."""
    n = len(xs)
    boots = []
    for _ in range(BOOT):
        resample = [xs[rng.randrange(n)] for _ in range(n)]
        boots.append(mean(resample))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def intervals_overlap(lo1, hi1, lo2, hi2):
    return not (hi1 < lo2 or hi2 < lo1)


# -------------------------------------------------- paired-difference bootstrap

def bootstrap_diff_ci(a, b, rng):
    """Resample the SAME case index for both systems, so the pair stays intact,
    recompute mean(B) - mean(A). The case's difficulty rides in both terms and
    cancels. Return the 95% percentile CI on the difference."""
    n = len(a)
    boots = []
    for _ in range(BOOT):
        sa = 0.0
        sb = 0.0
        for _ in range(n):
            i = rng.randrange(n)     # one index, used for both A and B
            sa += a[i]
            sb += b[i]
        boots.append((sb - sa) / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def permutation_p(a, b, rng):
    """Paired sign-flip permutation test. Under the null 'B is no better than
    A', the sign of each per-case difference is a coin flip. Flip all 30 signs
    at random 10000 times; count how often the reshuffled mean difference is at
    least the observed one (one-sided)."""
    d = [b[i] - a[i] for i in range(len(a))]
    observed = mean(d)
    at_least = 0
    for _ in range(PERM):
        flipped = mean([di if rng.random() < 0.5 else -di for di in d])
        if flipped >= observed:
            at_least += 1
    return observed, (at_least + 1) / (PERM + 1)   # +1: the observed arrangement


def sign_test(a, b):
    """Exact one-sided sign test on the discordant pairs, as a check on the
    permutation p. Ties (B == A) are dropped; count wins for B out of the rest,
    then the exact binomial tail P(X >= wins | p=0.5)."""
    wins = sum(1 for i in range(len(a)) if b[i] > a[i])
    losses = sum(1 for i in range(len(a)) if b[i] < a[i])
    ties = len(a) - wins - losses
    n = wins + losses
    # exact upper binomial tail with p=0.5, stdlib only
    from math import comb
    tail = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    return wins, losses, ties, tail


# ------------------------------------------------------------------- printing

def show_means(a, b):
    ma, mb, diff = means(a, b)
    print("POINT MEANS (no uncertainty)")
    print("-" * 70)
    print("  system A (baseline)          mean = %.4f" % ma)
    print("  system B (baseline+grounding) mean = %.4f" % mb)
    print("  difference  B - A                  = %+.4f" % diff)
    print("")
    print("  A bare point estimate says: B wins. By how much we cannot yet say.")
    return ma, mb, diff


def show_marginal(a, b):
    rng = random.Random(SEED)
    la, ha = bootstrap_mean_ci(a, rng)
    lb, hb = bootstrap_mean_ci(b, rng)
    overlap = intervals_overlap(la, ha, lb, hb)
    print("MARGINAL 95%% CIs (bootstrap, B=%d, seed=%d)" % (BOOT, SEED))
    print("-" * 70)
    print("  A: %.4f   95%% CI [%.4f, %.4f]" % (mean(a), la, ha))
    print("  B: %.4f   95%% CI [%.4f, %.4f]" % (mean(b), lb, hb))
    print("  intervals overlap: %s" % overlap)
    print("")
    verdict = "NOT SIGNIFICANT (the CIs overlap)" if overlap else "significant"
    print("  VERDICT BY OVERLAP RULE: %s" % verdict)
    return (la, ha), (lb, hb), overlap


def show_paired(a, b):
    rng = random.Random(SEED)
    lo, hi = bootstrap_diff_ci(a, b, rng)
    excludes_zero = lo > 0 or hi < 0
    observed, p_perm = permutation_p(a, b, rng)
    wins, losses, ties, p_sign = sign_test(a, b)
    print("PAIRED DIFFERENCE (bootstrap CI + permutation test, seed=%d)" % SEED)
    print("-" * 70)
    print("  observed mean(B - A)          = %+.4f" % observed)
    print("  95%% CI on the difference      = [%+.4f, %+.4f]" % (lo, hi))
    print("  CI excludes zero              = %s" % excludes_zero)
    print("  permutation p (one-sided)     = %.4f" % p_perm)
    print("  sign test: B wins %d, loses %d, ties %d" % (wins, losses, ties))
    print("  sign-test p (exact binomial)  = %.4f" % p_sign)
    print("")
    verdict = "SIGNIFICANT (difference CI clears zero)" if excludes_zero else "not significant"
    print("  VERDICT BY PAIRED CI: %s" % verdict)
    return (lo, hi), excludes_zero, p_perm, p_sign


def show_all(a, b):
    ma, mb, diff = show_means(a, b)
    print("")
    (la, ha), (lb, hb), overlap = show_marginal(a, b)
    print("")
    (lo, hi), excludes_zero, p_perm, p_sign = show_paired(a, b)
    print("")
    print("THE TWO METHODS DISAGREE" if overlap and excludes_zero
          else "the two methods agree")
    print("-" * 70)
    print("  overlap rule  -> %s" % ("no difference" if overlap else "difference"))
    print("  paired CI     -> %s" % ("difference" if excludes_zero else "no difference"))
    print("  when they disagree, the paired CI is the one to trust: it asks the")
    print("  question you actually have (is B - A above zero?), the overlap rule")
    print("  asks a different, looser one (do the two clouds touch?).")


def check(a, b):
    print("SELF-TEST — cross-derive the difference and prove seed-determinism")
    print("-" * 70)
    # Route A: difference of the two means.
    diff_route_a = mean(b) - mean(a)
    # Route B: mean of the per-case differences. Algebraically identical.
    diff_route_b = mean([b[i] - a[i] for i in range(len(a))])
    print("  route A  mean(B) - mean(A)      = %+.6f" % diff_route_a)
    print("  route B  mean(B[i] - A[i])      = %+.6f" % diff_route_b)
    agree = abs(diff_route_a - diff_route_b) < 1e-12
    print("  routes agree                   = %s" % agree)

    # Same seed -> identical CI, twice.
    lo1, hi1 = bootstrap_diff_ci(a, b, random.Random(SEED))
    lo2, hi2 = bootstrap_diff_ci(a, b, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  paired CI, run 1               = [%+.4f, %+.4f]" % (lo1, hi1))
    print("  paired CI, run 2 (same seed)   = [%+.4f, %+.4f]" % (lo2, hi2))
    print("  deterministic under seed       = %s" % deterministic)

    # A DIFFERENT seed moves the CI a little -- the bootstrap is itself noisy.
    lo3, hi3 = bootstrap_diff_ci(a, b, random.Random(SEED + 1))
    print("  paired CI, seed=%d              = [%+.4f, %+.4f]  (bootstrap noise)"
          % (SEED + 1, lo3, hi3))

    print("-" * 70)
    ok = agree and deterministic
    print("SELF-TEST %s  routes_agree=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, deterministic))
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Put an interval on an A/B eval and test the difference.")
    parser.add_argument("--means", action="store_true")
    parser.add_argument("--marginal", action="store_true")
    parser.add_argument("--paired", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    cases, a, b = load_runs()
    print("cases=%d  file=%s  paired A/B, graded 0..%d by the basic-01 rubric"
          % (len(cases), RUNS_FILE.name, CHECKS_OUT_OF))
    print("")

    if args.check:
        return 0 if check(a, b) else 1
    if args.means:
        show_means(a, b)
    elif args.marginal:
        show_marginal(a, b)
    elif args.paired:
        show_paired(a, b)
    elif args.all:
        show_all(a, b)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
