#!/usr/bin/env python3
"""Softmax must subtract the max before exp -- or a large logit overflows to inf, then NaN.

Every step of generation ends in a softmax over the vocabulary logits, and the textbook
formula exp(x_i) / sum(exp(x_j)) is a trap on real logits. A deep network can produce a logit
of 800, and exp(800) is not a big number in float64 -- it is inf, because the largest argument
exp can take before overflow is about 709. Once one term is inf the sum is inf, and inf/inf is
NaN: the whole distribution becomes NaN, the sample is garbage, and nothing raised an error.

The fix is one line and it is free. Softmax is shift-invariant: subtracting any constant from
every logit leaves the result unchanged, because the constant factors out of numerator and
denominator. So subtract the max logit first. Now the largest shifted logit is 0, exp(0) is 1,
every other term is between 0 and 1, and nothing overflows -- the answer is bit-for-bit the
distribution the textbook formula was trying to compute, just without the inf. This builds the
naive softmax and the max-subtracted one, shows the naive one going to NaN on a large logit
while the stable one returns a clean distribution, and shows the two agree exactly where the
naive one still works. The log-sum-exp trick extends the same shift to log-probabilities.

  --logits   the logit vectors, and both softmaxes side by side (naive NaNs, stable holds)
  --shift    the shift-invariance the fix relies on: subtract any constant, same distribution
  --check    the naive softmax NaNs on a large logit; the stable one is a valid distribution

The logit vectors are the fixture; every exp and sum is computed. Deterministic; stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "logits.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the naive softmax (the bug)

def softmax_naive(logits):
    """Textbook formula: exp each logit, divide by the sum. Overflows to inf -> NaN on large logits."""
    exps = [safe_exp(x) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def safe_exp(x):
    """math.exp raises OverflowError above ~709; return inf so the NaN propagates like float exp would."""
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


# ------------------------------------------------------------- the stable softmax (the fix)

def softmax_stable(logits):
    """Subtract the max logit first. Shift-invariant, so identical result -- but nothing overflows."""
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]   # largest term is exp(0)=1; nothing overflows
    total = sum(exps)
    return [e / total for e in exps]


def logsumexp(logits):
    """log(sum(exp(x))) computed stably: m + log(sum(exp(x - m))). Needed for log-probabilities."""
    m = max(logits)
    return m + math.log(sum(math.exp(x - m) for x in logits))


# ------------------------------------------------------------- helpers

def is_valid_dist(p):
    """A valid distribution: all entries finite in [0,1] and summing to 1."""
    if any(math.isnan(x) or math.isinf(x) for x in p):
        return False
    return all(0.0 <= x <= 1.0 for x in p) and abs(sum(p) - 1.0) < 1e-9


def max_abs_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


# ----------------------------------------------------------------- printing

def logits_view(data):
    print("LOGITS — naive softmax vs max-subtracted (stable) softmax")
    print("-" * 70)
    for row in data["logits"]:
        name, vec = row["name"], row["logits"]
        naive = softmax_naive(vec)
        stable = softmax_stable(vec)
        print("  %-10s logits=%s" % (name, vec))
        print("     naive : %s  valid=%s" % (fmt(naive), is_valid_dist(naive)))
        print("     stable: %s  valid=%s" % (fmt(stable), is_valid_dist(stable)))
    print("-" * 70)
    print("  the naive softmax NaNs when a logit exceeds ~709; the stable one never does.")


def shift_view(data):
    vec = next(r["logits"] for r in data["logits"] if r["name"] == "moderate")
    print("SHIFT — softmax is shift-invariant: subtract any constant, same distribution")
    print("-" * 70)
    base = softmax_stable(vec)
    print("  logits           %s -> %s" % (vec, fmt(base)))
    for c in (10, 100, 1000):
        shifted = [x - c for x in vec]
        out = softmax_stable(shifted)
        print("  minus %-5d      %s -> %s  (max diff %.2e)"
              % (c, shifted, fmt(out), max_abs_diff(base, out)))
    print("-" * 70)
    print("  the constant cancels in numerator and denominator -- which is why subtracting max is free.")


def fmt(p):
    return "[" + ", ".join("%.4f" % x if not (math.isnan(x) or math.isinf(x)) else str(x) for x in p) + "]"


def check(data):
    print("SELF-TEST — the naive softmax NaNs on a large logit; the stable one is a valid distribution")
    print("-" * 70)
    rows = {r["name"]: r["logits"] for r in data["logits"]}

    big = rows["large"]
    naive_big = softmax_naive(big)
    naive_nans = any(math.isnan(x) for x in naive_big)
    print("  naive softmax on the large-logit vector produces NaN = %s (%s)" % (naive_nans, fmt(naive_big)))

    stable_big = softmax_stable(big)
    stable_valid = is_valid_dist(stable_big)
    print("  stable softmax on the SAME vector is a valid distribution = %s (%s)" % (stable_valid, fmt(stable_big)))

    mod = rows["moderate"]
    agree = max_abs_diff(softmax_naive(mod), softmax_stable(mod)) < 1e-12
    print("  where the naive one works (moderate logits), the two agree exactly = %s" % agree)

    # shift-invariance: subtracting the max changes nothing about the distribution
    shifted = [x - max(mod) for x in mod]
    shift_ok = max_abs_diff(softmax_stable(mod), softmax_stable(shifted)) < 1e-12
    print("  subtracting the max is shift-invariant (same distribution) = %s" % shift_ok)

    # log-sum-exp stays finite where a naive log(sum(exp)) would be inf
    lse_finite = math.isfinite(logsumexp(big))
    print("  logsumexp on the large vector stays finite = %s (%.3f)" % (lse_finite, logsumexp(big)))

    ok = naive_nans and stable_valid and agree and shift_ok and lse_finite
    print("-" * 70)
    print("SELF-TEST %s  naive_nans=%s  stable_valid=%s  agree=%s  shift_ok=%s  lse_finite=%s"
          % ("PASS" if ok else "FAIL", naive_nans, stable_valid, agree, shift_ok, lse_finite))
    return ok


def main():
    p = argparse.ArgumentParser(description="Numerically stable softmax: subtract the max before exp.")
    p.add_argument("--logits", action="store_true")
    p.add_argument("--shift", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vectors=%d  file=%s  (the logit vectors are a fixture; every exp is computed)"
          % (len(data["logits"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.logits:
        logits_view(data)
    elif args.shift:
        shift_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
