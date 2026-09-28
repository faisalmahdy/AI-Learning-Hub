"""Count independent units, not measurements, or repeated looks at the same subject fake a tiny standard error.

Statistical significance rests on how much INDEPENDENT information you have. Twenty measurements sound like
twenty data points, but if they are five measurements each of four subjects, they are not twenty independent
looks at the world -- they are four, sampled five times over. Measurements of the same subject are correlated:
knowing one tells you a lot about the next, so the fifth reading adds far less information than the first.
Treating all twenty as independent -- pseudoreplication -- inflates the sample size, and an inflated sample size
shrinks the standard error, tightens the confidence interval, and pushes the p-value down. The result looks more
certain than the data can support, and a difference that is really noise crosses the significance line.

The standard error falls like one over the square root of the sample size, so the whole error is in which N you
use. The naive analysis uses N = 20 measurements and gets sd/sqrt(20). The correct analysis recognizes the
independent units are the 4 subjects: it reduces each subject to its mean and takes the standard error of those 4
means, sd_of_means/sqrt(4). The correct standard error is larger -- the honest reflection of having four
independent units, not twenty -- and the confidence interval it produces is wide enough to tell the truth about
how little you actually know.

On this fixture the grand mean is 13 and we test it against a reference of 11. The naive standard error is 0.607
(N=20), which puts the mean 3.3 standard errors from 11 -- comfortably 'significant'. The correct standard error
is 1.291 (4 subjects), which puts it only 1.5 standard errors away -- not significant. The naive analysis
manufactured a result the data does not contain. This computes both.

  --se         the naive standard error (N measurements) vs the correct one (independent subjects)
  --test       how many standard errors the mean sits from the reference, under each analysis
  --check      the naive SE understates; the independent units are the subjects; the naive test fakes significance

The measurements are the fixture; every statistic is computed. Stdlib only.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pseudorep.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def all_measurements(subjects):
    return [x for vals in subjects.values() for x in vals]


def subject_means(subjects):
    return [statistics.mean(vals) for vals in subjects.values()]


def naive_se(subjects):
    """Treat every measurement as independent: sd over all N measurements / sqrt(N)."""
    m = all_measurements(subjects)
    return statistics.stdev(m) / len(m) ** 0.5


def correct_se(subjects):
    """The independent units are the subjects: sd of the subject means / sqrt(number of subjects)."""
    means = subject_means(subjects)
    return statistics.stdev(means) / len(means) ** 0.5


def sigmas_from(subjects, se, ref):
    """How many standard errors the grand mean sits from the reference value."""
    return abs(statistics.mean(all_measurements(subjects)) - ref) / se


# ----------------------------------------------------------------- printing

def se_view(data):
    subs = data["subjects"]
    n, k = len(all_measurements(subs)), len(subs)
    print("SE — standard error: all measurements vs independent subjects")
    print("-" * 60)
    print("  grand mean:                %.1f" % statistics.mean(all_measurements(subs)))
    print("  naive  (N=%2d measurements): SE %.3f" % (n, naive_se(subs)))
    print("  correct(k=%2d subjects):     SE %.3f  (%.1fx larger)" % (k, correct_se(subs), correct_se(subs) / naive_se(subs)))
    print("-" * 60)
    print("  the naive SE divides by sqrt(%d); the honest one divides by sqrt(%d)." % (n, k))


def test_view(data):
    subs, ref = data["subjects"], data["reference"]
    ns, cs = sigmas_from(subs, naive_se(subs), ref), sigmas_from(subs, correct_se(subs), ref)
    print("TEST — distance of the mean from the reference %d, in standard errors" % ref)
    print("-" * 60)
    print("  naive:    %.2f SE  ->  %s" % (ns, "SIGNIFICANT (>2)" if ns > 2 else "not significant"))
    print("  correct:  %.2f SE  ->  %s" % (cs, "significant" if cs > 2 else "NOT significant (<2)"))
    print("-" * 60)
    print("  the same mean is 'significant' pseudoreplicated and not significant counted honestly.")


def check(data):
    print("SELF-TEST — the naive SE understates; the independent units are the subjects; the naive test fakes significance")
    print("-" * 112)
    subs, ref = data["subjects"], data["reference"]
    n, k = len(all_measurements(subs)), len(subs)

    naive_understates = naive_se(subs) < correct_se(subs)
    print("  the naive standard error is smaller than the correct one = %s (%.3f < %.3f)" % (naive_understates, naive_se(subs), correct_se(subs)))

    understated_by_2x = correct_se(subs) / naive_se(subs) > 2
    print("  the naive SE understates by more than 2x = %s (%.2fx)" % (understated_by_2x, correct_se(subs) / naive_se(subs)))

    independent_units_are_subjects = k < n
    print("  the independent units are the %d subjects, not the %d measurements = %s" % (k, n, independent_units_are_subjects))

    naive_looks_significant = sigmas_from(subs, naive_se(subs), ref) > 2
    print("  the naive test crosses 2 SE (looks significant) = %s (%.2f SE)" % (naive_looks_significant, sigmas_from(subs, naive_se(subs), ref)))

    correct_not_significant = sigmas_from(subs, correct_se(subs), ref) < 2
    print("  the correct test is under 2 SE (not significant) = %s (%.2f SE)" % (correct_not_significant, sigmas_from(subs, correct_se(subs), ref)))

    ok = naive_understates and understated_by_2x and independent_units_are_subjects and naive_looks_significant and correct_not_significant
    print("-" * 112)
    print("SELF-TEST %s  naive_understates=%s  understated_by_2x=%s  independent_units_are_subjects=%s  naive_looks_significant=%s  correct_not_significant=%s"
          % ("PASS" if ok else "FAIL", naive_understates, understated_by_2x, independent_units_are_subjects, naive_looks_significant, correct_not_significant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pseudoreplication: treating repeated measurements as independent inflates N, shrinks the standard error, and fakes significance.")
    p.add_argument("--se", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    subs = data["subjects"]
    print("subjects=%d  measurements=%d  reference=%d  file=%s  (the measurements are a fixture)"
          % (len(subs), len(all_measurements(subs)), data["reference"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.se:
        se_view(data)
    elif args.test:
        test_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
