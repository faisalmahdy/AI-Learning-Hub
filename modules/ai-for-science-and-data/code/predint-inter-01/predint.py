"""The confidence interval for a fitted line and the prediction interval for a new point are different intervals -- the confidence band can be narrower than the noise itself, so it contains only a few of the actual points, and using it as 'where the next point will fall' badly understates the spread.

A regression line has two kinds of uncertainty around it, and they answer two different questions.

The confidence interval asks: where is the true average response at this x? Its width comes only from how well the data pins down the line, so it shrinks as the sample grows -- collect enough data and it collapses toward the line, because the mean can be located arbitrarily precisely. At the center of the data it is proportional to the residual standard deviation times the square root of one-over-n.

The prediction interval asks a different question: where will a single new observation land? A new point sits on the true line plus its own random scatter, so its interval is the line's uncertainty PLUS the residual variance of individual points. That extra term does not shrink with n, so the prediction interval never narrows below roughly one residual standard deviation however much data you have -- it cannot, because individual points scatter by that much no matter how well you know the line.

The two get confused because both are bands around the same line. But the confidence band, at a realistic sample size, is often narrower than the cloud of points it is drawn through -- narrower than the noise -- so it contains only a fraction of the actual observations. The prediction band is built to contain about 95% of them. Quoting the confidence band as the range a new measurement will fall in is the mistake, and it makes the process look far more precise than it is.

On this fixture ten points scatter around a line. The confidence half-width is smaller than the residual standard deviation and contains a minority of the points; the prediction half-width exceeds it and contains almost all of them. This computes both.

  --confidence  the confidence band for the line: its half-width, and how few of the points fall inside it
  --prediction  the prediction band for a new observation: its half-width, and how many of the points fall inside it
  --check       the confidence band is narrower than the noise and misses most points, while the prediction band contains almost all of them

x, y, and the multiplier k are the fixture; the fit, the residual sd, both half-widths, and the coverage of each band are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "predint.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fit(x, y):
    """Ordinary least squares: return slope, intercept, residual sd, x-mean, and Sxx."""
    n = len(x)
    xbar, ybar = sum(x) / n, sum(y) / n
    sxx = sum((xi - xbar) ** 2 for xi in x)
    sxy = sum((xi - xbar) * (yi - ybar) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    sse = sum((yi - (intercept + slope * xi)) ** 2 for xi, yi in zip(x, y))
    resid_sd = (sse / (n - 2)) ** 0.5
    return slope, intercept, resid_sd, xbar, sxx


def confidence_halfwidth(x0, n, resid_sd, xbar, sxx, k):
    """Half-width of the interval for the MEAN response at x0 -- uncertainty in the line only."""
    return k * resid_sd * (1.0 / n + (x0 - xbar) ** 2 / sxx) ** 0.5


def prediction_halfwidth(x0, n, resid_sd, xbar, sxx, k):
    """Half-width for a NEW observation at x0 -- the line's uncertainty PLUS the residual scatter (the extra 1)."""
    return k * resid_sd * (1.0 + 1.0 / n + (x0 - xbar) ** 2 / sxx) ** 0.5


def coverage(x, y, band, slope, intercept, n, resid_sd, xbar, sxx, k):
    """Fraction of the actual points whose y falls within the given band around the fitted line."""
    inside = 0
    for xi, yi in zip(x, y):
        half = band(xi, n, resid_sd, xbar, sxx, k)
        if abs(yi - (intercept + slope * xi)) <= half:
            inside += 1
    return inside / len(x)


# ----------------------------------------------------------------- printing

def confidence_view(data):
    x, y, k = data["x"], data["y"], data["k"]
    slope, intercept, sd, xbar, sxx = fit(x, y)
    n = len(x)
    half = confidence_halfwidth(xbar, n, sd, xbar, sxx, k)
    frac = coverage(x, y, confidence_halfwidth, slope, intercept, n, sd, xbar, sxx, k)
    print("CONFIDENCE — the band for the true average line")
    print("-" * 60)
    print("  residual sd (scatter of points) = %.3f" % sd)
    print("  confidence half-width at center = %.3f  (%.2f x the noise)" % (half, half / sd))
    print("  points inside the confidence band = %.0f%% (%d of %d)" % (100 * frac, round(frac * n), n))
    print("-" * 60)
    print("  the band is narrower than the noise, so it covers far fewer than the nominal 95% of points")


def prediction_view(data):
    x, y, k = data["x"], data["y"], data["k"]
    slope, intercept, sd, xbar, sxx = fit(x, y)
    n = len(x)
    half = prediction_halfwidth(xbar, n, sd, xbar, sxx, k)
    frac = coverage(x, y, prediction_halfwidth, slope, intercept, n, sd, xbar, sxx, k)
    print("PREDICTION — the band for a new observation")
    print("-" * 60)
    print("  residual sd (scatter of points) = %.3f" % sd)
    print("  prediction half-width at center = %.3f  (%.2f x the noise)" % (half, half / sd))
    print("  points inside the prediction band = %.0f%% (%d of %d)" % (100 * frac, round(frac * n), n))
    print("-" * 60)
    print("  the band adds the residual scatter, so it contains almost every point")


def check(data):
    print("SELF-TEST — the confidence band is narrower than the noise and covers far fewer than 95% of points, while the prediction band contains almost all of them")
    print("-" * 112)
    x, y, k = data["x"], data["y"], data["k"]
    slope, intercept, sd, xbar, sxx = fit(x, y)
    n = len(x)
    ci = confidence_halfwidth(xbar, n, sd, xbar, sxx, k)
    pi = prediction_halfwidth(xbar, n, sd, xbar, sxx, k)
    ci_frac = coverage(x, y, confidence_halfwidth, slope, intercept, n, sd, xbar, sxx, k)
    pi_frac = coverage(x, y, prediction_halfwidth, slope, intercept, n, sd, xbar, sxx, k)

    prediction_wider = pi > 2 * ci
    print("  the prediction band is much wider than the confidence band = %s (%.3f vs %.3f)" % (prediction_wider, pi, ci))

    confidence_below_noise = ci < sd
    print("  the confidence half-width is narrower than the noise = %s (%.3f < %.3f)" % (confidence_below_noise, ci, sd))

    prediction_above_noise = pi > sd
    print("  the prediction half-width exceeds the noise = %s (%.3f > %.3f)" % (prediction_above_noise, pi, sd))

    confidence_undercovers = ci_frac < 0.7
    print("  the confidence band covers far fewer than the nominal 95%% of points = %s (%.0f%%)" % (confidence_undercovers, 100 * ci_frac))

    prediction_contains_most = pi_frac >= 0.9
    print("  the prediction band contains almost all the points = %s (%.0f%%)" % (prediction_contains_most, 100 * pi_frac))

    ok = (prediction_wider and confidence_below_noise and prediction_above_noise
          and confidence_undercovers and prediction_contains_most)
    print("-" * 112)
    print("SELF-TEST %s  prediction_wider=%s  confidence_below_noise=%s  prediction_above_noise=%s  confidence_undercovers=%s  prediction_contains_most=%s"
          % ("PASS" if ok else "FAIL", prediction_wider, confidence_below_noise, prediction_above_noise,
             confidence_undercovers, prediction_contains_most))
    return ok


def main():
    p = argparse.ArgumentParser(description="Confidence vs prediction interval: the confidence band for a fitted line (uncertainty in the mean, shrinks with n) is not the prediction interval for a new observation (which adds the residual scatter and never shrinks below the noise), so a confidence band -- often narrower than the noise -- badly understates where a new point will fall.")
    p.add_argument("--confidence", action="store_true")
    p.add_argument("--prediction", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    slope, intercept, sd, xbar, sxx = fit(data["x"], data["y"])
    print("fit: y = %.3f x + %.3f  residual_sd=%.3f  n=%d  file=%s"
          % (slope, intercept, sd, len(data["x"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.confidence:
        confidence_view(data)
    elif args.prediction:
        prediction_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
