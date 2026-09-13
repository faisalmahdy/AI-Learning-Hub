"""Analyze a ratio metric at the randomization unit (the user), not the impression -- pooling impressions as independent trials understates the variance and manufactures significance.

A rate metric -- click-through rate, conversion rate, any total-over-total -- is a ratio, and the obvious way to test it is to pool every impression across all users, treat each as an independent coin flip, and use the binomial standard error sqrt(p(1-p)/N). With N the number of impressions, which is enormous, that standard error is tiny, and almost any difference looks significant. The formula is right for independent trials and wrong here, because the trials are not independent.

The experiment randomized users, not impressions. A user's impressions are strongly correlated: some users click nearly everything they see, others click nothing, so the hundred impressions from one user carry far less information than a hundred impressions from a hundred different users. The independent unit -- the thing that was randomly assigned to an arm -- is the user, and the true sample size is the number of users, which is smaller by whatever the impressions-per-user ratio is. Treating impressions as independent inflates the effective sample size by that factor, shrinks the standard error, and turns a difference well inside the noise into a confident 'significant' result.

The correct analysis respects the randomization unit. Compute the metric per user -- each user's own click rate -- and treat each user's value as one observation, so the standard error comes from the variance of per-user rates across the actual number of users. (For a ratio of two per-user totals, the delta method gives the same variance from the per-user numerators and denominators; the per-user-rate version here is the simplest correct case.) The standard error then reflects how much users actually vary, which is the uncertainty that matters.

The rule: analyze a ratio metric at the randomization unit -- per user, not per impression -- because impressions within a user are correlated, so pooling them as independent trials understates the variance by the impressions-per-user factor and inflates significance; the true sample size is the number of units randomized.

On this fixture both arms have four users of a hundred impressions each, with a CTR difference of 0.25. The impression-level analysis reports a standard error of 0.033 and z = 7.6 (wildly significant); the user-level analysis reports a standard error of 0.38 and z = 0.65 (not significant). This computes both.

  --arms      each arm's per-user rates and its pooled CTR
  --test      the CTR difference with the impression-level (naive) SE and z vs the user-level (correct) SE and z
  --check     the impression-level analysis understates the SE and manufactures significance; the user-level analysis does not

arms is the fixture; every rate, standard error, and z is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "analysisunit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def pooled_ctr(arm):
    clicks = sum(k for _, k in arm)
    impressions = sum(i for i, _ in arm)
    return clicks / impressions, impressions


def naive_se(arm):
    """Impression-level: binomial SE with N = number of impressions (trials assumed independent)."""
    p, n = pooled_ctr(arm)
    return math.sqrt(p * (1 - p) / n)


def user_rates(arm):
    return [k / i for i, k in arm]


def user_se(arm):
    """User-level: SE of the mean of per-user rates, with N = number of users."""
    rates = user_rates(arm)
    m = sum(rates) / len(rates)
    var = sum((x - m) ** 2 for x in rates) / (len(rates) - 1)
    return math.sqrt(var / len(rates))


def combine(a, b):
    return math.sqrt(a * a + b * b)


# ----------------------------------------------------------------- printing

def arms_view(data):
    print("ARMS — per-user click rates and pooled CTR")
    print("-" * 56)
    for name, arm in data["arms"].items():
        p, n = pooled_ctr(arm)
        print("  arm %s: %d users, per-user CTR %s, pooled CTR %.2f (%d impressions)"
              % (name, len(arm), user_rates(arm), p, n))
    print("-" * 56)
    print("  within a user the rate is all-or-nothing — impressions are far from independent")


def test_view(data):
    A, B = data["arms"]["A"], data["arms"]["B"]
    pA, pB = pooled_ctr(A)[0], pooled_ctr(B)[0]
    diff = pA - pB
    n_se = combine(naive_se(A), naive_se(B))
    u_se = combine(user_se(A), user_se(B))
    print("TEST — CTR difference under impression-level vs user-level analysis")
    print("-" * 66)
    print("  CTR difference (A - B)                = %.2f" % diff)
    print("  impression-level: SE %.4f, z = %.2f, significant = %s" % (n_se, diff / n_se, abs(diff / n_se) > 1.96))
    print("  user-level:       SE %.4f, z = %.2f, significant = %s" % (u_se, diff / u_se, abs(diff / u_se) > 1.96))
    print("-" * 66)
    print("  the same difference is 'significant' by impression, noise by user")


def check(data):
    print("SELF-TEST — the impression-level analysis understates the SE and manufactures significance; the user-level analysis does not")
    print("-" * 130)
    A, B = data["arms"]["A"], data["arms"]["B"]
    diff = pooled_ctr(A)[0] - pooled_ctr(B)[0]
    n_se = combine(naive_se(A), naive_se(B))
    u_se = combine(user_se(A), user_se(B))
    n_z, u_z = abs(diff / n_se), abs(diff / u_se)

    within_user_correlated = any(r in (0.0, 1.0) for r in user_rates(A) + user_rates(B))
    print("  users are all-or-nothing clickers (impressions correlated within a user) = %s" % within_user_correlated)

    naive_se_smaller = n_se < u_se
    print("  the impression-level SE is smaller than the user-level SE = %s (%.4f < %.4f)" % (naive_se_smaller, n_se, u_se))

    naive_significant = n_z > 1.96
    print("  the impression-level test is 'significant' = %s (z=%.2f)" % (naive_significant, n_z))

    user_not_significant = u_z < 1.96
    print("  the user-level test is NOT significant = %s (z=%.2f)" % (user_not_significant, u_z))

    conclusion_flips = naive_significant and user_not_significant
    print("  the analysis unit flips the conclusion = %s" % conclusion_flips)

    ok = (within_user_correlated and naive_se_smaller and naive_significant
          and user_not_significant and conclusion_flips)
    print("-" * 130)
    print("SELF-TEST %s  within_user_correlated=%s  naive_se_smaller=%s  naive_significant=%s  user_not_significant=%s  conclusion_flips=%s"
          % ("PASS" if ok else "FAIL", within_user_correlated, naive_se_smaller, naive_significant, user_not_significant, conclusion_flips))
    return ok


def main():
    p = argparse.ArgumentParser(description="Analysis unit for ratio metrics: analyze a ratio metric at the randomization unit -- per user, not per impression -- because impressions within a user are correlated, so pooling them as independent trials understates the variance by the impressions-per-user factor and inflates significance; the true sample size is the number of units randomized.")
    p.add_argument("--arms", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("arms=%s  file=%s  (the per-user impressions/clicks are a fixture)"
          % ({k: len(v) for k, v in data["arms"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.arms:
        arms_view(data)
    elif args.test:
        test_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
