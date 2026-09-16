"""To claim two models are equivalent, show the whole CI fits inside the margin -- a non-significant difference is not equivalence.

You want to replace an expensive model with a cheaper one and need to show the cheaper one is "as good." So you run an
eval, find the accuracy gap is not statistically significant -- its confidence interval includes zero -- and conclude
the two are equivalent. That is the wrong test, and it fails in the most dangerous way: it is easiest to pass when the
eval is weakest. A small eval gives a wide confidence interval, and a wide interval includes zero for almost any true
difference, so "not significant" is reached not by proving the models are close but by failing to measure them at all.
The same wide interval that includes zero can also include a gap of ten points -- a difference you would very much care
about -- so it is equally consistent with equivalence and with a real regression. Absence of a significant difference
is not evidence of equivalence; it is often just absence of data.

The correct test flips the burden of proof. To claim equivalence you must show the entire confidence interval lies
INSIDE the margin you chose -- the largest gap you would still call practically the same. This is the two-one-sided-tests
(TOST) procedure: equivalence is established only when both ends of the interval fall within [-margin, +margin], so you
have ruled out a difference bigger than the margin in either direction. A wide interval that spills past the margin does
not establish equivalence no matter how it straddles zero; it means "inconclusive, get more data." Only when the eval is
large enough to pull both interval ends inside the margin have you actually proven the two models are close enough.

On this fixture the gap is estimated at 0.01 with a 95% CI of [-0.08, 0.10] and the margin is 0.05. The naive test sees
the CI includes 0 and declares equivalence -- but the CI reaches 0.10, twice the margin, so a real 10-point gap is still
on the table. TOST correctly refuses: the interval is not inside [-0.05, 0.05]. A larger eval narrows the CI to
[-0.03, 0.04], which fits inside the margin, and only then does TOST conclude equivalence. This computes both.

  --assess   the naive 'not significant, so equivalent' verdict vs the TOST 'is the whole CI within the margin' verdict
  --range    what the wide CI actually admits -- a gap as large as its upper end, far past the margin
  --check    a CI that includes 0 is not equivalence; TOST requires the whole CI inside the margin; a tighter eval earns it

The difference, its intervals, and the margin are the fixture; every verdict is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "equiv.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def ci_includes_zero(lo, hi):
    """The difference is 'not statistically significant' when its confidence interval contains 0."""
    return lo <= 0 <= hi


def tost_equivalent(lo, hi, margin):
    """TOST: equivalence is established only if the WHOLE interval lies within [-margin, +margin]."""
    return lo >= -margin and hi <= margin


def largest_plausible_gap(lo, hi):
    """The biggest absolute difference the interval still admits -- what 'not significant' fails to rule out."""
    return max(abs(lo), abs(hi))


# ----------------------------------------------------------------- printing

def assess_view(data):
    lo, hi, m = data["ci_low"], data["ci_high"], data["margin"]
    tlo, thi = data["tight_ci_low"], data["tight_ci_high"]
    print("ASSESS — 'not significant, so equivalent' vs TOST (whole CI within +/-%.2f)" % m)
    print("-" * 70)
    print("  small eval:  gap %.2f, CI [%.2f, %.2f]" % (data["difference"], lo, hi))
    print("    naive (CI includes 0 -> equivalent): %s" % ci_includes_zero(lo, hi))
    print("    TOST  (CI within margin -> equivalent): %s" % tost_equivalent(lo, hi, m))
    print("  larger eval: gap %.2f, CI [%.2f, %.2f]" % (data["difference"], tlo, thi))
    print("    TOST  (CI within margin -> equivalent): %s" % tost_equivalent(tlo, thi, m))
    print("-" * 70)
    print("  the wide CI is 'not significant' yet not equivalent; only the narrow CI earns equivalence.")


def range_view(data):
    lo, hi, m = data["ci_low"], data["ci_high"], data["margin"]
    print("RANGE — what the 'not significant' interval actually admits")
    print("-" * 60)
    print("  margin of equivalence:        +/- %.2f" % m)
    print("  CI on the gap:                [%.2f, %.2f]" % (lo, hi))
    print("  largest gap still plausible:  %.2f  (%.1fx the margin)" % (largest_plausible_gap(lo, hi), largest_plausible_gap(lo, hi) / m))
    print("  does the CI include 0?        %s" % ci_includes_zero(lo, hi))
    print("-" * 60)
    print("  the same interval that includes 0 also includes a %.0f-point gap -- it proves nothing about closeness." % (largest_plausible_gap(lo, hi) * 100))


def check(data):
    print("SELF-TEST — a CI that includes 0 is not equivalence; TOST requires the whole CI inside the margin; a tighter eval earns it")
    print("-" * 122)
    lo, hi, m = data["ci_low"], data["ci_high"], data["margin"]
    tlo, thi = data["tight_ci_low"], data["tight_ci_high"]

    naive_calls_equivalent = ci_includes_zero(lo, hi)
    print("  the naive test (CI includes 0) calls the small eval equivalent = %s" % naive_calls_equivalent)

    big_gap_still_possible = largest_plausible_gap(lo, hi) > m
    print("  yet a gap larger than the margin is still in the CI = %s (%.2f > %.2f)" % (big_gap_still_possible, largest_plausible_gap(lo, hi), m))

    tost_refuses_wide = not tost_equivalent(lo, hi, m)
    print("  so TOST refuses to call the small eval equivalent = %s" % tost_refuses_wide)

    tost_accepts_tight = tost_equivalent(tlo, thi, m)
    print("  TOST accepts the larger eval whose CI fits the margin = %s ([%.2f, %.2f])" % (tost_accepts_tight, tlo, thi))

    naive_and_tost_disagree = naive_calls_equivalent and not tost_equivalent(lo, hi, m)
    print("  naive and TOST disagree on the small eval = %s" % naive_and_tost_disagree)

    ok = naive_calls_equivalent and big_gap_still_possible and tost_refuses_wide and tost_accepts_tight and naive_and_tost_disagree
    print("-" * 122)
    print("SELF-TEST %s  naive_calls_equivalent=%s  big_gap_still_possible=%s  tost_refuses_wide=%s  tost_accepts_tight=%s  naive_and_tost_disagree=%s"
          % ("PASS" if ok else "FAIL", naive_calls_equivalent, big_gap_still_possible, tost_refuses_wide, tost_accepts_tight, naive_and_tost_disagree))
    return ok


def main():
    p = argparse.ArgumentParser(description="Equivalence testing (TOST): to claim two models are equivalent, show the whole confidence interval on their difference lies within a pre-set margin; a non-significant difference is not equivalence.")
    p.add_argument("--assess", action="store_true")
    p.add_argument("--range", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("difference=%.2f  CI=[%.2f, %.2f]  margin=%.2f  file=%s  (the estimates are a fixture)"
          % (data["difference"], data["ci_low"], data["ci_high"], data["margin"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.assess:
        assess_view(data)
    elif args.range:
        range_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
