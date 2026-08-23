#!/usr/bin/env python3
"""Does the orchestration layer help? An A/B on a SWE-bench slice, defensibly.

Two agent harnesses, vanilla and omc, each attempted every instance K=3 times;
an attempt 'resolved' the instance iff its hidden test suite passed. This is the
capstone: it puts together the paired difference and its interval (inter-01),
the pass@k / pass^k views (inter-03), and the deterministic test oracle that
lets us skip judge calibration (inter-02), then states one defensible claim.

  --slice      the 15 instances, each system's resolve rate, paired
  --headline   resolve rate (pass@1) for both, the paired difference + CI +
               sign test -- the claim you can defend
  --views      pass@1 / pass@3 / pass^3 side by side: three questions, three gaps
  --bug        best-of-k reported as the resolve rate (the planted mistake)
  --sweep      the verdict as the slice grows: first N=5, 10, 15 instances
  --check      cross-derive the difference, prove the best-of-k assertion, seeds

Stdlib only (math.comb). No network, no keys, no model calls. THE RESOLVE
OUTCOMES IN results.json ARE A FIXTURE standing in for a real run; the bootstrap
is seeded. Point it at your own harness's predictions -- that is the capstone.
"""
import argparse
import json
import random
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_FILE = HERE / "results.json"

SEED = 0
BOOT = 10000
PERM = 10000


def load():
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    return data["instances"]


def percentile(sorted_xs, q):
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


def resolves(inst, system):
    """c, n for one (instance, system): resolved attempts and total attempts."""
    a = inst[system]
    return sum(1 for x in a if x), len(a)


def rate(inst, system):
    """Resolve rate on one instance: the fraction of its attempts that passed."""
    c, n = resolves(inst, system)
    return c / n


# ---------------------------------------------------- the headline (inter-01)

def mean(xs):
    return sum(xs) / len(xs)


def resolve_rate(instances, system):
    return mean([rate(i, system) for i in instances])


def paired_diffs(instances):
    """omc rate minus vanilla rate, per instance. Paired: same instance both."""
    return [rate(i, "omc") - rate(i, "vanilla") for i in instances]


def bootstrap_diff_ci(instances, rng):
    """Resample instances with replacement, recompute the mean paired diff."""
    n = len(instances)
    boots = []
    for _ in range(BOOT):
        s = 0.0
        for _ in range(n):
            i = instances[rng.randrange(n)]
            s += rate(i, "omc") - rate(i, "vanilla")
        boots.append(s / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


def sign_test(instances):
    """Instances where omc's rate beats vanilla's, loses, ties; exact tail."""
    wins = sum(1 for i in instances if rate(i, "omc") > rate(i, "vanilla"))
    losses = sum(1 for i in instances if rate(i, "omc") < rate(i, "vanilla"))
    ties = len(instances) - wins - losses
    n = wins + losses
    tail = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n) if n else 1.0
    return wins, losses, ties, tail


# ------------------------------------------------ the three views (inter-03)

def pass_at_k(instances, system, k):
    """At least one of k attempts resolves, averaged over instances."""
    total = 0.0
    for inst in instances:
        c, n = resolves(inst, system)
        miss = comb(n - c, k) / comb(n, k) if (n - c) >= k else 0.0
        total += 1 - miss
    return total / len(instances)


def pass_hat_k(instances, system, k):
    """All k attempts resolve (reliability), averaged over instances."""
    total = 0.0
    for inst in instances:
        c, n = resolves(inst, system)
        total += comb(c, k) / comb(n, k) if c >= k else 0.0
    return total / len(instances)


def best_of_k_rate(instances, system):
    """THE BUG: score each instance 1 if ANY attempt resolved, then average.
    This is pass@3 wearing the resolve-rate's label; it is >= the real rate and
    equal only when every instance is all-or-nothing."""
    return mean([1.0 if any(inst[system]) else 0.0 for inst in instances])


# ------------------------------------------------------------------- printing

def show_slice(instances):
    print("SLICE — 15 instances, resolve rate per system (fixture outcomes)")
    print("-" * 74)
    print("  instance                              vanilla   omc     diff")
    for inst in instances:
        v, o = rate(inst, "vanilla"), rate(inst, "omc")
        flag = "" if abs(o - v) < 1e-9 else ("  omc+" if o > v else "  van+")
        print("  %-36s  %.2f     %.2f    %+.2f%s" % (inst["id"], v, o, o - v, flag))
    print("-" * 74)
    print("  vanilla resolve rate = %.3f    omc resolve rate = %.3f"
          % (resolve_rate(instances, "vanilla"), resolve_rate(instances, "omc")))


def show_headline(instances):
    v = resolve_rate(instances, "vanilla")
    o = resolve_rate(instances, "omc")
    diff = o - v
    rng = random.Random(SEED)
    lo, hi = bootstrap_diff_ci(instances, rng)
    wins, losses, ties, p = sign_test(instances)
    print("HEADLINE — resolve rate (pass@1) and the paired difference")
    print("-" * 66)
    print("  vanilla  resolve rate = %.4f" % v)
    print("  omc      resolve rate = %.4f" % o)
    print("  paired difference     = %+.4f" % diff)
    print("  95%% CI (bootstrap)    = [%+.4f, %+.4f]  seed=%d, B=%d" % (lo, hi, SEED, BOOT))
    print("  CI clears zero        = %s" % (lo > 0 or hi < 0))
    print("  sign test: omc wins %d, loses %d, ties %d" % (wins, losses, ties))
    print("  sign-test p (exact)   = %.4f" % p)
    print("-" * 66)
    settled = (lo > 0 or hi < 0)
    print("  DEFENSIBLE CLAIM: omc resolves %.0f%% vs %.0f%%, +%.0f points"
          % (o * 100, v * 100, diff * 100))
    print("  on this %d-instance slice the difference %s zero (p=%.3f)."
          % (len(instances), "clears" if settled else "does NOT clear", p))
    if settled:
        print("  It helps -- but the interval is [%.0f, %.0f] points wide, so 'how much'"
              % (lo * 100, hi * 100))
        print("  is far from pinned on 15 instances.")


def show_views(instances):
    print("THREE VIEWS — the same A/B, three questions (inter-03)")
    print("-" * 66)
    print("  metric      question                       vanilla   omc")
    rows = [
        ("pass@1", "avg attempt resolves?", pass_hat_k, 1),
        ("pass@3", "at least one of 3?",    pass_at_k, 3),
        ("pass^3", "all three resolve?",    pass_hat_k, 3),
    ]
    for name, q, fn, k in rows:
        print("  %-10s %-30s %.3f     %.3f"
              % (name, q, fn(instances, "vanilla", k), fn(instances, "omc", k)))
    print("-" * 66)
    print("  the omc advantage is +%.0f pts on pass@1, +%.0f on pass@3, +%.0f on pass^3."
          % ((pass_hat_k(instances, "omc", 1) - pass_hat_k(instances, "vanilla", 1)) * 100,
             (pass_at_k(instances, "omc", 3) - pass_at_k(instances, "vanilla", 3)) * 100,
             (pass_hat_k(instances, "omc", 3) - pass_hat_k(instances, "vanilla", 3)) * 100))
    print("  'omc helps' means MORE OFTEN (pass@1), not RELIABLY (pass^3 is low for both).")


def show_bug(instances):
    print("THE BUG — best-of-3 reported as the resolve rate")
    print("-" * 66)
    for system in ("vanilla", "omc"):
        true_rate = resolve_rate(instances, system)
        best = best_of_k_rate(instances, system)
        print("  %-8s  true resolve rate = %.3f   best-of-3 'rate' = %.3f  (+%.3f inflated)"
              % (system, true_rate, best, best - true_rate))
    print("-" * 66)
    o_true = resolve_rate(instances, "omc")
    o_best = best_of_k_rate(instances, "omc")
    print("  best-of-3 inflates each level by +0.267: omc's %.0f%% resolver is reported"
          % (o_true * 100))
    print("  as a %.0f%%. it IS pass@3, a different question; whether the GAP happens to"
          % (o_best * 100))
    print("  survive (it does here, both +0.200) is luck -- the published LEVELS are wrong.")


def show_sweep(instances):
    print("SWEEP — the verdict as the slice grows (first N instances)")
    print("-" * 66)
    print("  N     omc-vanilla   95%% CI               clears 0?   sign p")
    for N in (5, 10, 15):
        sub = instances[:N]
        diff = resolve_rate(sub, "omc") - resolve_rate(sub, "vanilla")
        rng = random.Random(SEED)
        lo, hi = bootstrap_diff_ci(sub, rng)
        _, _, _, p = sign_test(sub)
        clears = lo > 0 or hi < 0
        print("  %-4d  %+.3f        [%+.3f, %+.3f]     %-9s   %.3f"
              % (N, diff, lo, hi, "yes" if clears else "NO", p))
    print("-" * 66)
    print("  the bootstrap CI clears zero at every N, but the exact sign test cannot:")
    print("  at N=5 only 3 instances are discordant, so its smallest possible p is")
    print("  0.5**3 = 0.125. the two tests agree only at N=15. one clearing interval is")
    print("  not a verdict -- demand the exact test too, and enough discordant pairs.")


def check(instances):
    print("SELF-TEST — cross-derive the difference, the best-of-k assertion, seeds")
    print("-" * 66)
    # difference two ways: difference of rates vs mean of paired diffs.
    d_a = resolve_rate(instances, "omc") - resolve_rate(instances, "vanilla")
    d_b = mean(paired_diffs(instances))
    print("  diff via rate means     = %+.6f" % d_a)
    print("  diff via paired diffs   = %+.6f" % d_b)
    agree = abs(d_a - d_b) < 1e-9
    print("  routes agree            = %s" % agree)

    # the assertion that catches best-of-k: pass@3 >= resolve rate always, and
    # best-of-k IS pass@3, so a reported 'rate' equal to pass@3 has collapsed
    # the attempts. Here they differ, proving the rate is not best-of-k.
    rr = resolve_rate(instances, "omc")
    p3 = pass_at_k(instances, "omc", 3)
    best = best_of_k_rate(instances, "omc")
    print("  omc resolve rate        = %.4f" % rr)
    print("  omc pass@3              = %.4f" % p3)
    print("  omc best-of-3           = %.4f  (== pass@3: %s)" % (best, abs(best - p3) < 1e-9))
    ordering_ok = rr <= p3 + 1e-9 and abs(best - p3) < 1e-9

    # same seed -> identical CI.
    lo1, hi1 = bootstrap_diff_ci(instances, random.Random(SEED))
    lo2, hi2 = bootstrap_diff_ci(instances, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  paired CI run 1         = [%+.4f, %+.4f]" % (lo1, hi1))
    print("  paired CI run 2         = [%+.4f, %+.4f]" % (lo2, hi2))
    print("  deterministic under seed= %s" % deterministic)
    print("-" * 66)
    ok = agree and ordering_ok and deterministic
    print("SELF-TEST %s  routes_agree=%s  rate<=pass@3=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, ordering_ok, deterministic))
    return ok


def main():
    parser = argparse.ArgumentParser(description="A/B an agent harness on a SWE-bench slice.")
    for flag in ("slice", "headline", "views", "bug", "sweep", "check"):
        parser.add_argument("--" + flag, action="store_true")
    args = parser.parse_args()

    instances = load()
    print("instances=%d  attempts each=%d  file=%s  (resolve outcomes are a fixture)"
          % (len(instances), len(instances[0]["vanilla"]), RESULTS_FILE.name))
    print("")

    if args.check:
        return 0 if check(instances) else 1
    if args.slice:
        show_slice(instances)
    elif args.headline:
        show_headline(instances)
    elif args.views:
        show_views(instances)
    elif args.bug:
        show_bug(instances)
    elif args.sweep:
        show_sweep(instances)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
