"""Check the A/B split ratio before trusting any metric -- a sample ratio mismatch means the randomization is broken.

Every A/B experiment starts with an intended split -- most often 50/50 -- and a randomizer that is supposed to send
each unit to an arm independently with that probability. Almost nobody checks that the split actually came out as
intended, and that is a mistake, because when the observed split is meaningfully off (5200 in one arm, 4800 in the other,
when you asked for 5000/5000) something in the pipeline is broken: a redirect that drops some users before assignment, a
bot filter that removes one arm's traffic unevenly, a logging join that loses rows, a caching layer that reassigns. This
is a Sample Ratio Mismatch (SRM), and its consequence is severe: if the arms were not populated by the fair coin you
assumed, then the two groups are not exchangeable, so ANY difference you measure between them -- however large, however
statistically significant -- may be an artifact of the broken assignment rather than the treatment. An SRM invalidates
the whole experiment, not just the split.

The check is a chi-square goodness-of-fit test on the assignment counts alone (not the metric): compare the observed
counts per arm to the expected counts under the intended split, and compute how surprising the deviation is. The reason a
'52/48' split that looks fine to the eye is actually alarming is scale: at 10000 units the standard error of a count is
sqrt(N*p*(1-p)) = sqrt(10000*0.25) = 50, so being 200 off from 5000 is 4 standard errors, a roughly 1-in-16000 event
under fair randomization. Because a true SRM should almost never happen by chance, the alarm threshold is set very strict
(p < 0.001), so that firing it is strong evidence of a real pipeline bug rather than a fluke. The SRM check is a
GUARDRAIL you run first: if it fails, you stop and fix the assignment, and you do not report the metric at all.

The rule: before reading any A/B metric, test the arm counts against the intended split with a chi-square goodness-of-fit
test, and if the split is off beyond a strict threshold (p < 0.001), treat the experiment as invalid -- a sample ratio
mismatch means the groups are not exchangeable, so no downstream comparison can be trusted, and 'the split looks close
enough' is exactly the intuition that scale defeats.

On this fixture the healthy experiment (5030/4970) is 0.6 standard errors off -- an ordinary wobble, p about 0.55, no SRM.
The broken experiment (5200/4800) is 4 standard errors off, chi-square 16, p about 0.00006, which trips the SRM guard, so
its metric must not be trusted no matter what it says. This computes both.

  --split   each experiment's observed vs expected counts, the chi-square statistic, the p-value, and the SRM verdict
  --why     why '5200/4800 looks close' is wrong: the standard error of the count is 50, so 200 off is 4 SE, not noise
  --check   the healthy split passes the SRM guard and the broken split trips it -- so the broken experiment is invalid

The arm counts and intended split are the fixture; every chi-square statistic, p-value, and verdict is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "srm.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def chi_square_stat(a, b, p_a):
    """Goodness-of-fit chi-square (df=1) of the split (a, b) against the intended fraction p_a for arm A."""
    n = a + b
    exp_a = n * p_a
    exp_b = n * (1.0 - p_a)
    return (a - exp_a) ** 2 / exp_a + (b - exp_b) ** 2 / exp_b


def chi_square_p_df1(chi2):
    """Upper-tail p-value of a chi-square statistic with 1 degree of freedom, via the complementary error function."""
    return math.erfc(math.sqrt(chi2 / 2.0))


def standard_errors_off(a, b, p_a):
    """How many standard errors arm A's count is from its expected count (the z behind the chi-square)."""
    n = a + b
    exp_a = n * p_a
    se = math.sqrt(n * p_a * (1.0 - p_a))
    return (a - exp_a) / se


def evaluate(exp, p_a, threshold):
    a, b = exp["a"], exp["b"]
    chi2 = chi_square_stat(a, b, p_a)
    p = chi_square_p_df1(chi2)
    return {
        "name": exp["name"], "a": a, "b": b, "exp_a": (a + b) * p_a, "exp_b": (a + b) * (1 - p_a),
        "chi2": chi2, "p": p, "z": standard_errors_off(a, b, p_a), "srm": p < threshold,
    }


# ----------------------------------------------------------------- printing

def split_view(data):
    p_a = data["expected_fraction"]
    thr = data["srm_threshold"]
    print("SPLIT — observed vs intended (%.0f/%.0f) assignment; SRM alarm at p < %g" % (p_a * 100, (1 - p_a) * 100, thr))
    print("-" * 78)
    print("  experiment  arm A / arm B   expected      chi-square   p-value     SRM?")
    for exp in data["experiments"]:
        r = evaluate(exp, p_a, thr)
        print("  %-11s %5d / %-5d   %.0f / %-.0f   %-11.4g %-11.5g %s"
              % (r["name"], r["a"], r["b"], r["exp_a"], r["exp_b"], r["chi2"], r["p"],
                 "SRM! invalid" if r["srm"] else "ok"))
    print("-" * 78)
    print("  a tripped SRM means the arms are not exchangeable, so the metric cannot be trusted at all.")


def why_view(data):
    p_a = data["expected_fraction"]
    print("WHY — '5200/4800 looks close' fails because the standard error of the count is tiny at this scale")
    print("-" * 76)
    for exp in data["experiments"]:
        n = exp["a"] + exp["b"]
        se = math.sqrt(n * p_a * (1 - p_a))
        r = evaluate(exp, p_a, data["srm_threshold"])
        print("  %-8s N=%d  expected A=%.0f  observed A=%d  off by %+d  = %.1f standard errors (SE=%.0f)"
              % (exp["name"], n, n * p_a, exp["a"], exp["a"] - int(n * p_a), r["z"], se))
    print("-" * 76)
    print("  the eye reads 52% vs 50% as 'about the same'; at N=10000 it is 4 SE, a ~1-in-16000 fluke.")


def check(data):
    print("SELF-TEST — the healthy split passes the SRM guard and the broken split trips it, invalidating its metric")
    print("-" * 104)
    p_a, thr = data["expected_fraction"], data["srm_threshold"]
    healthy = evaluate(data["experiments"][0], p_a, thr)
    broken = evaluate(data["experiments"][1], p_a, thr)

    expected_balanced = abs(healthy["exp_a"] - healthy["exp_b"]) < 1e-9 and abs(healthy["exp_a"] - 5000) < 1e-9
    print("  the intended split expects 5000/5000 = %s (%.0f/%.0f)" % (expected_balanced, healthy["exp_a"], healthy["exp_b"]))

    healthy_passes = not healthy["srm"]
    print("  healthy (5030/4970) passes the SRM guard = %s (p=%.4g, %.1f SE off)" % (healthy_passes, healthy["p"], healthy["z"]))

    broken_flagged = broken["srm"]
    print("  broken (5200/4800) trips the SRM guard = %s (p=%.5g, %.1f SE off)" % (broken_flagged, broken["p"], broken["z"]))

    broken_is_4_se = abs(broken["z"] - 4.0) < 1e-9
    print("  the broken split is exactly 4 standard errors off = %s (z=%.1f, chi2=%.0f)" % (broken_is_4_se, broken["z"], broken["chi2"]))

    verdicts_differ = healthy["srm"] != broken["srm"]
    print("  the guard separates the two experiments = %s (healthy ok, broken invalid)" % verdicts_differ)

    ok = expected_balanced and healthy_passes and broken_flagged and broken_is_4_se and verdicts_differ
    print("-" * 104)
    print("SELF-TEST %s  expected_balanced=%s  healthy_passes=%s  broken_flagged=%s  broken_is_4_se=%s  verdicts_differ=%s"
          % ("PASS" if ok else "FAIL", expected_balanced, healthy_passes, broken_flagged, broken_is_4_se, verdicts_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Sample ratio mismatch: before reading any A/B metric, test the arm counts against the intended split with a chi-square goodness-of-fit test, and if the split is off beyond a strict threshold (p < 0.001) treat the experiment as invalid -- a mismatch means the arms are not exchangeable, so no downstream comparison can be trusted, however significant it looks.")
    p.add_argument("--split", action="store_true")
    p.add_argument("--why", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("expected_fraction=%.2f  srm_threshold=%g  experiments=%d  file=%s  (the arm counts and split are a fixture)"
          % (data["expected_fraction"], data["srm_threshold"], len(data["experiments"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.split:
        split_view(data)
    elif args.why:
        why_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
