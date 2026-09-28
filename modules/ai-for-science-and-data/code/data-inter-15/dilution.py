"""Noise in the predictor flattens the slope, or a real relationship measured with error looks weaker than it is.

Fit a line of y on x and the slope is the effect: how much y moves per unit of x. But you rarely measure x
exactly -- the predictor has measurement error (a noisy sensor, a self-reported value, a proxy). And that
error does something specific and counterintuitive: it biases the estimated slope toward zero. A true
relationship of slope 2 gets measured as a slope of 1.4, not because the effect changed but because the
noise in x scattered the points horizontally, which flattens the best-fit line. This is regression
dilution (attenuation), and it makes real effects look weaker -- so you under-report the influence of a
noisily-measured variable and may wrongly conclude it barely matters.

The asymmetry is the surprising part: noise in the RESPONSE y does NOT bias the slope. Scatter the points
vertically and the best-fit line still has the right slope, just more scatter around it. Only noise in the
PREDICTOR x tilts the line, because least-squares divides the covariance by the variance of x, and
measurement error inflates that variance (the denominator) without adding to the covariance (the
numerator). The slope shrinks by exactly the reliability of x -- the fraction of x's variance that is real
signal rather than noise. Knowing that fraction, you can correct the slope back up.

On this fixture the true relationship is y = 2x exactly. Fit on the clean x and the slope is 2.00. Add
measurement noise to x and the slope drops to 1.43 -- shrunk by the reliability 0.714. Add the same noise
to y instead and the slope stays 2.00, unbiased. Dividing the diluted 1.43 by the reliability recovers
2.00. This computes all of it.

  --fit        the slope fitted three ways: clean, noisy predictor, noisy response
  --correct    the attenuation factor (reliability) and the recovered slope
  --check      predictor noise attenuates the slope, response noise does not, and the reliability corrects it

The x, y, and noise are the fixture; every slope is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def covariance(xs, ys):
    mx, my = mean(xs), mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)


def slope(xs, ys):
    """Least-squares slope of y on x: covariance divided by the variance of x."""
    return round(covariance(xs, ys) / variance(xs), 3)


def correlation(xs, ys):
    return round(covariance(xs, ys) / math.sqrt(variance(xs) * variance(ys)), 3)


def add(xs, noise):
    return [x + n for x, n in zip(xs, noise)]


def reliability(x, noise):
    """Fraction of the observed predictor's variance that is real signal: var(x) / var(x + noise)."""
    return round(variance(x) / variance(add(x, noise)), 3)


# ----------------------------------------------------------------- printing

def fit_view(data):
    x, y, noise = data["x"], data["y"], data["noise"]
    x_obs, y_obs = add(x, noise), add(y, noise)
    print("FIT — slope of y on x, fitted three ways")
    print("-" * 58)
    print("  clean (y on true x):        slope %.3f   r %.3f" % (slope(x, y), correlation(x, y)))
    print("  noisy predictor (y on x+e): slope %.3f   r %.3f" % (slope(x_obs, y), correlation(x_obs, y)))
    print("  noisy response (y+e on x):  slope %.3f   r %.3f" % (slope(x, y_obs), correlation(x, y_obs)))
    print("-" * 58)
    print("  noise in x flattens the slope; noise in y leaves it alone.")


def correct_view(data):
    x, y, noise = data["x"], data["y"], data["noise"]
    x_obs = add(x, noise)
    rel = reliability(x, noise)
    print("CORRECT — attenuation is the reliability; dividing by it recovers the slope")
    print("-" * 58)
    print("  true slope:            %.3f" % slope(x, y))
    print("  diluted slope:         %.3f" % slope(x_obs, y))
    print("  reliability var(x)/var(x+e): %.3f" % rel)
    print("  diluted / reliability: %.3f" % round(slope(x_obs, y) / rel, 3))
    print("-" * 58)
    print("  the diluted slope is the true slope times the reliability.")


def check(data):
    print("SELF-TEST — predictor noise attenuates the slope, response noise does not, and the reliability corrects it")
    print("-" * 104)
    x, y, noise = data["x"], data["y"], data["noise"]
    x_obs, y_obs = add(x, noise), add(y, noise)
    true_s = slope(x, y)
    diluted_s = slope(x_obs, y)
    response_s = slope(x, y_obs)
    rel = reliability(x, noise)

    predictor_noise_attenuates = diluted_s < true_s
    print("  noise in the predictor shrinks the slope = %s (%.3f < %.3f)" % (predictor_noise_attenuates, diluted_s, true_s))

    response_noise_unbiased = abs(response_s - true_s) < 1e-9
    print("  noise in the response leaves the slope unbiased = %s (%.3f)" % (response_noise_unbiased, response_s))

    attenuation_is_reliability = abs(diluted_s - true_s * rel) < 5e-3   # tolerance for display rounding
    print("  the diluted slope equals true slope times reliability = %s (%.3f = %.3f x %.3f)"
          % (attenuation_is_reliability, diluted_s, true_s, rel))

    correction_recovers = abs(round(diluted_s / rel, 3) - true_s) < 1e-2
    print("  dividing the diluted slope by reliability recovers the truth = %s (%.3f)" % (correction_recovers, round(diluted_s / rel, 3)))

    correlation_also_attenuates = correlation(x_obs, y) < correlation(x, y)
    print("  the correlation is attenuated too = %s (%.3f < %.3f)" % (correlation_also_attenuates, correlation(x_obs, y), correlation(x, y)))

    ok = predictor_noise_attenuates and response_noise_unbiased and attenuation_is_reliability and correction_recovers and correlation_also_attenuates
    print("-" * 104)
    print("SELF-TEST %s  predictor_noise_attenuates=%s  response_noise_unbiased=%s  attenuation_is_reliability=%s  correction_recovers=%s  correlation_also_attenuates=%s"
          % ("PASS" if ok else "FAIL", predictor_noise_attenuates, response_noise_unbiased, attenuation_is_reliability, correction_recovers, correlation_also_attenuates))
    return ok


def main():
    p = argparse.ArgumentParser(description="Regression dilution: measurement error in the predictor biases the slope toward zero.")
    p.add_argument("--fit", action="store_true")
    p.add_argument("--correct", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  true_slope=%.1f  file=%s  (the x, y, and noise are a fixture)"
          % (len(data["x"]), slope(data["x"], data["y"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fit:
        fit_view(data)
    elif args.correct:
        correct_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
