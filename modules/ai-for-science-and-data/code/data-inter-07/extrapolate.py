#!/usr/bin/env python3
"""A fit is only valid inside its data's range -- extrapolate and a great model predicts nonsense.

Fit a line to data and it can be excellent -- small residuals, high R-squared -- and still be
worthless for a prediction outside the range of points you fit it on. The fit only ever saw a
window of the input; what the relationship does beyond that window is not in the data, so a
prediction out there is not a measurement, it is an assumption that the straight line continues
forever. When the true relationship curves -- and most do -- that assumption fails, and the
model that scored beautifully in-range is wildly wrong out-of-range, with no warning from the
fit itself.

The data here is a saturating curve, gently bending over the fitted window x in [10, 50] so a
line fits it well: the in-range predictions are within a couple of units of truth. Asked to
predict at x = 200, far past the last data point, the line marches on to 174 while the true
value has flattened to 80 -- an error of nearly a hundred, larger than any in-range residual by
far. The fix is not a better line; it is knowing the fit's support (the min and max of the
training x) and refusing to extrapolate past it, or at least flagging that a prediction out
there is unvouched-for. This builds a naive predictor that answers any query and a
support-aware one that flags out-of-range queries, and measures the error each incurs.

  --fit       the fitted line, its in-range residuals, and the training support
  --predict   in-range vs out-of-range queries: naive prediction, true value, error, flag
  --check     in-range error is small; the extrapolated error is large and outside the support

The training points and query truths are the fixture; the least-squares fit is computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "curve.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- least-squares line fit

def fit_line(points):
    """Ordinary least-squares slope and intercept for y = m*x + b."""
    n = len(points)
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - m * sx) / n
    return m, b


def predict(m, b, x):
    return m * x + b


def support(points):
    """The range of x the fit actually saw -- predictions outside this are extrapolation."""
    xs = [p[0] for p in points]
    return min(xs), max(xs)


def in_support(x, sup):
    return sup[0] <= x <= sup[1]


# ------------------------------------------------------------- residuals

def max_in_range_residual(points, m, b):
    """The worst the fit does on its own training points -- the honest in-range error bar."""
    return max(abs(p[1] - predict(m, b, p[0])) for p in points)


# ----------------------------------------------------------------- printing

def fit_view(data):
    pts = [tuple(p) for p in data["train"]]
    m, b = fit_line(pts)
    sup = support(pts)
    print("FIT — least-squares line over the training window")
    print("-" * 66)
    print("  fitted line: y = %.3f x + %.3f" % (m, b))
    print("  training support (x range seen): [%g, %g]" % sup)
    print("  worst in-range residual: %.2f" % max_in_range_residual(pts, m, b))
    print("-" * 66)
    print("  the line fits the window well -- but the window is all it ever saw.")


def predict_view(data):
    pts = [tuple(p) for p in data["train"]]
    m, b = fit_line(pts)
    sup = support(pts)
    print("PREDICT — naive prediction vs truth, in-range and out-of-range")
    print("-" * 66)
    print("  x       predicted  true    error   within support?")
    for q in data["queries"]:
        x, ytrue = q["x"], q["true_y"]
        yp = predict(m, b, x)
        flag = "yes" if in_support(x, sup) else "NO (extrapolation)"
        print("  %-7g %-10.2f %-7.2f %-7.2f %s" % (x, yp, ytrue, abs(yp - ytrue), flag))
    print("-" * 66)
    print("  the line's error stays small inside the support and explodes outside it.")


def check(data):
    print("SELF-TEST — in-range error is small; the extrapolated error is large and out of support")
    print("-" * 66)
    pts = [tuple(p) for p in data["train"]]
    m, b = fit_line(pts)
    sup = support(pts)

    in_q = [q for q in data["queries"] if in_support(q["x"], sup)]
    out_q = [q for q in data["queries"] if not in_support(q["x"], sup)]

    in_err = max(abs(predict(m, b, q["x"]) - q["true_y"]) for q in in_q)
    in_range_good = in_err < data["tolerance"]
    print("  in-range predictions are accurate = %s (worst error %.2f < tol %.2f)"
          % (in_range_good, in_err, data["tolerance"]))

    far = max(out_q, key=lambda q: abs(predict(m, b, q["x"]) - q["true_y"]))
    far_err = abs(predict(m, b, far["x"]) - far["true_y"])
    extrapolation_wrong = far_err > 10 * in_err
    print("  the extrapolated prediction is far wrong = %s (error %.2f at x=%g, %.0fx the in-range error)"
          % (extrapolation_wrong, far_err, far["x"], far_err / in_err))

    far_out_of_support = not in_support(far["x"], sup)
    print("  the far query is outside the training support = %s (x=%g not in [%g, %g])"
          % (far_out_of_support, far["x"], sup[0], sup[1]))

    # a support-aware predictor would have flagged it; the naive one gave a confident number
    support_aware_flags = far_out_of_support     # the flag is exactly the support check
    print("  a support-aware predictor flags it while the naive one answers = %s" % support_aware_flags)

    ok = in_range_good and extrapolation_wrong and far_out_of_support and support_aware_flags
    print("-" * 66)
    print("SELF-TEST %s  in_range_good=%s  extrapolation_wrong=%s  out_of_support=%s  flagged=%s"
          % ("PASS" if ok else "FAIL", in_range_good, extrapolation_wrong, far_out_of_support, support_aware_flags))
    return ok


def main():
    p = argparse.ArgumentParser(description="A fit is only valid inside its data's range.")
    p.add_argument("--fit", action="store_true")
    p.add_argument("--predict", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("train_points=%d  queries=%d  file=%s  (the curve and query truths are a fixture)"
          % (len(data["train"]), len(data["queries"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fit:
        fit_view(data)
    elif args.predict:
        predict_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
