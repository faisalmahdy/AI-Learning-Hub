"""A statistically significant result from an underpowered study is not reassuring -- it exaggerates the effect and can even get its sign wrong, so 'small study, but significant!' is a red flag, not a green light.

The estimator is honest. If you could rerun the two-arm comparison forever, the estimated difference would average out to the true effect: it is unbiased, and its errors are symmetric around the truth. Nothing is wrong with the measurement.

What is wrong is the filter we put after it. We do not report, act on, or believe every estimate -- we keep the ones that clear a significance bar (here, |estimate| larger than z*standard_error). Conditioning on significance is a selection, and selection on a noisy quantity keeps the extremes.

In an underpowered design -- true effect small relative to the standard error -- the estimate is only rarely large enough to clear the bar. The runs that do clear it are exactly the runs where noise happened to push the estimate far from zero. So every survivor is large in magnitude: the mean estimate among significant results is several times the true effect (a Type M, magnitude, error). And because the estimate straddles zero, some of the survivors are large in the wrong direction: a nonzero fraction of significant results have the opposite sign from the truth (a Type S, sign, error).

The naive reading treats the surviving estimate at face value -- 'we measured 0.5's effect as 2.4, and it's significant, so the effect is about 2.4.' That number is a selection artifact. The fix is to know the power of the design: at low power a significant estimate is systematically inflated, so it bounds nothing and 'significant' certifies nothing about magnitude or even direction. Raise power (more units, less noise) and the exaggeration and sign errors both shrink toward zero.

This integrates the sampling distribution of the estimate on a fixed grid and computes the power, the unconditional mean, the mean conditional on significance, the exaggeration ratio, and the sign-error rate.

  --sample   the sampling distribution: power, and that the estimator is unbiased over all runs
  --filter   the estimates that clear the significance bar: their inflated mean and wrong-sign fraction
  --check    the estimator is unbiased overall, yet conditional on significance it exaggerates the effect and admits sign errors

true_effect, standard_error, and z_threshold are the fixture; the power, the exaggeration ratio, and the sign-error rate are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "typesm.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def normal_pdf(x, mu, sigma):
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))


def grid(data):
    """The sampling distribution of the estimate as (value, weight) pairs, normalized to sum 1."""
    lo, hi, step = data["grid_lo"], data["grid_hi"], data["grid_step"]
    mu, sigma = data["true_effect"], data["standard_error"]
    n = int(round((hi - lo) / step)) + 1
    pts = [lo + i * step for i in range(n)]
    raw = [normal_pdf(x, mu, sigma) * step for x in pts]
    total = sum(raw)
    return [(x, w / total) for x, w in zip(pts, raw)]


def is_significant(estimate, data):
    """A run is 'significant' when its estimate clears the two-sided bar |estimate| > z*se."""
    return abs(estimate) > data["z_threshold"] * data["standard_error"]


def summarize(data):
    """Power, unconditional mean, and the significance-conditional mean / exaggeration / sign-error."""
    g = grid(data)
    truth = data["true_effect"]
    uncond_mean = sum(w * x for x, w in g)
    sig = [(x, w) for x, w in g if is_significant(x, data)]
    power = sum(w for _, w in sig)
    cond_mean = sum(w * x for x, w in sig) / power
    cond_absmean = sum(w * abs(x) for x, w in sig) / power
    exaggeration = cond_absmean / abs(truth)
    wrong_sign = sum(w for x, w in sig if (x > 0) != (truth > 0)) / power
    return {
        "uncond_mean": uncond_mean, "power": power, "cond_mean": cond_mean,
        "cond_absmean": cond_absmean, "exaggeration": exaggeration, "wrong_sign": wrong_sign,
    }


# ----------------------------------------------------------------- printing

def sample_view(data):
    s = summarize(data)
    print("SAMPLE — the sampling distribution of the estimate (all possible runs)")
    print("-" * 56)
    print("  true effect            = %.4f" % data["true_effect"])
    print("  standard error (1 run) = %.4f" % data["standard_error"])
    print("  mean estimate over ALL runs = %.4f  (unbiased: equals the truth)" % s["uncond_mean"])
    print("  significance bar |estimate| > %.4f" % (data["z_threshold"] * data["standard_error"]))
    print("  power = P(significant)  = %.4f" % s["power"])
    print("-" * 56)
    print("  the estimator is honest and the study is underpowered: it clears the bar %.1f%% of the time" % (100 * s["power"]))


def filter_view(data):
    s = summarize(data)
    print("FILTER — only the runs that reached significance (the ones we would report)")
    print("-" * 56)
    print("  true effect                    = %.4f" % data["true_effect"])
    print("  mean estimate | significant    = %.4f" % s["cond_mean"])
    print("  mean |estimate| | significant  = %.4f" % s["cond_absmean"])
    print("  exaggeration ratio (Type M)    = %.4f  (reported magnitude / truth)" % s["exaggeration"])
    print("  wrong-sign rate  (Type S)      = %.4f  (%.1f%% point the wrong way)" % (s["wrong_sign"], 100 * s["wrong_sign"]))
    print("-" * 56)
    print("  a significant result from this design overstates the effect ~%.1fx and is wrong-signed ~%.0f%% of the time" % (s["exaggeration"], 100 * s["wrong_sign"]))


def check(data):
    print("SELF-TEST — the estimator is unbiased overall, yet conditional on significance it exaggerates the effect and admits sign errors")
    print("-" * 112)
    s = summarize(data)
    truth = data["true_effect"]

    estimator_unbiased = abs(s["uncond_mean"] - truth) < 1e-6
    print("  averaged over all runs the estimate equals the truth = %s (%.6f vs %.4f)" % (estimator_unbiased, s["uncond_mean"], truth))

    power_is_low = s["power"] < 0.30
    print("  the study is underpowered = %s (power %.4f)" % (power_is_low, s["power"]))

    significant_exaggerates = s["exaggeration"] > 2.0
    print("  a significant estimate exaggerates the effect = %s (%.2fx the truth)" % (significant_exaggerates, s["exaggeration"]))

    sign_errors_occur = s["wrong_sign"] > 0.0
    print("  some significant estimates have the wrong sign = %s (%.4f)" % (sign_errors_occur, s["wrong_sign"]))

    significance_certifies_nothing = significant_exaggerates and sign_errors_occur
    print("  so 'significant' certifies neither magnitude nor direction = %s" % significance_certifies_nothing)

    ok = (estimator_unbiased and power_is_low and significant_exaggerates
          and sign_errors_occur and significance_certifies_nothing)
    print("-" * 112)
    print("SELF-TEST %s  estimator_unbiased=%s  power_is_low=%s  significant_exaggerates=%s  sign_errors_occur=%s  significance_certifies_nothing=%s"
          % ("PASS" if ok else "FAIL", estimator_unbiased, power_is_low, significant_exaggerates,
             sign_errors_occur, significance_certifies_nothing))
    return ok


def main():
    p = argparse.ArgumentParser(description="Type S and Type M errors: a significant result from an underpowered study exaggerates the effect (magnitude, Type M) and can flip its sign (Type S), because conditioning on significance selects the noisy extremes -- so 'small study, but significant' is a red flag, not reassurance.")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--filter", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("true_effect=%.2f  standard_error=%.2f  z_threshold=%.2f  file=%s  (these are a fixture)"
          % (data["true_effect"], data["standard_error"], data["z_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sample:
        sample_view(data)
    elif args.filter:
        filter_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
