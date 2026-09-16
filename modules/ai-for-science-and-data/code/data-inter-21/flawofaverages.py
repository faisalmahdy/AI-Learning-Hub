"""Do not plug the average into a curved model, or the answer is biased and you never see the error.

The tempting shortcut is to summarize inputs by their average and run that one number through the model:
average demand, average load, average return. It is exact only when the model is a straight line. The moment
the model curves -- and most real ones do -- the average of the outputs is not the output of the average, and
the gap is a real, one-directional bias, not noise that washes out. This is Jensen's inequality, and its
everyday name is the flaw of averages: the statistician who drowned crossing a river that was on average three
feet deep.

The direction of the error is set by the curvature. For a CONVEX function -- one curving upward, like squaring,
exponentiating, or a queue's delay as it fills -- the true average output is LARGER than the output of the
average input, so plugging in the mean UNDERESTIMATES. For a CONCAVE function -- curving downward, like a square
root, a logarithm, or a saturating yield -- it is the reverse: the mean OVERESTIMATES. A linear function is the
only one where the shortcut is exact. And the size of the bias grows with the spread of the input: for squaring,
the gap between mean(x^2) and (mean x)^2 is exactly the variance of x, so the more variable your inputs, the more
the average lies to you.

On this fixture two datasets share a mean of 5 but not their spread. Squaring, the spread set's true average is
35.67 while the average-then-square shortcut gives 25.00 -- a gap of 10.67, exactly its variance; the tight set's
gap is only 0.67, its smaller variance. Square-rooting reverses the sign. This computes all of it.

  --gap        for each dataset and function, the true average output vs the output of the average, and the gap
  --spread     the convex gap equals the variance and grows with spread; the same mean gives the same shortcut
  --check      convex underestimates, concave overestimates, linear is exact, the square gap is the variance

The datasets are the fixture; every average is computed exactly. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "flawofaverages.json"

FUNCS = {"square": lambda v: v * v, "sqrt": math.sqrt, "identity": lambda v: v}


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((v - m) ** 2 for v in xs) / len(xs)


def mean_of_f(xs, f):
    """The true average output: average f over the data."""
    return mean([f(v) for v in xs])


def f_of_mean(xs, f):
    """The shortcut: apply f to the average input."""
    return f(mean(xs))


# ----------------------------------------------------------------- printing

def gap_view(data):
    print("GAP — true average output mean(f(x)) vs the shortcut f(mean(x))")
    print("-" * 68)
    print("  dataset   function   mean(f(x))   f(mean(x))   gap        direction")
    for name in ("spread", "tight"):
        xs = data[name]
        for fn in ("square", "sqrt", "identity"):
            f = FUNCS[fn]
            mf, fm = mean_of_f(xs, f), f_of_mean(xs, f)
            gap = mf - fm
            direction = "underestimate" if gap > 1e-9 else ("overestimate" if gap < -1e-9 else "exact")
            print("  %-8s  %-8s   %8.4f     %8.4f     %+8.4f   %s" % (name, fn, mf, fm, gap, direction))
    print("-" * 68)
    print("  convex (square) underestimates, concave (sqrt) overestimates, linear (identity) is exact.")


def spread_view(data):
    print("SPREAD — the convex gap is the variance and grows with spread (both means = %.0f)" % mean(data["spread"]))
    print("-" * 68)
    sq = FUNCS["square"]
    for name in ("spread", "tight"):
        xs = data[name]
        gap = mean_of_f(xs, sq) - f_of_mean(xs, sq)
        print("  %-8s  values %s  mean %.0f  f(mean)=%.2f  gap %.4f  variance %.4f" % (name, xs, mean(xs), f_of_mean(xs, sq), gap, variance(xs)))
    print("-" * 68)
    print("  same mean -> same f(mean); the wider set's larger variance is exactly its larger bias.")


def check(data):
    print("SELF-TEST — convex underestimates, concave overestimates, linear is exact, the square gap is the variance")
    print("-" * 108)
    xs = data["spread"]
    sq, sr, idn = FUNCS["square"], FUNCS["sqrt"], FUNCS["identity"]

    convex_underestimates = f_of_mean(xs, sq) < mean_of_f(xs, sq)
    print("  convex: f(mean) underestimates the true average = %s (%.2f < %.2f)" % (convex_underestimates, f_of_mean(xs, sq), mean_of_f(xs, sq)))

    concave_overestimates = f_of_mean(xs, sr) > mean_of_f(xs, sr)
    print("  concave: f(mean) overestimates the true average = %s (%.4f > %.4f)" % (concave_overestimates, f_of_mean(xs, sr), mean_of_f(xs, sr)))

    linear_exact = abs(f_of_mean(xs, idn) - mean_of_f(xs, idn)) < 1e-9
    print("  linear: the shortcut is exact = %s (%.2f = %.2f)" % (linear_exact, f_of_mean(xs, idn), mean_of_f(xs, idn)))

    square_gap_is_variance = abs((mean_of_f(xs, sq) - f_of_mean(xs, sq)) - variance(xs)) < 1e-9
    print("  the squaring gap equals the variance = %s (%.4f = %.4f)" % (square_gap_is_variance, mean_of_f(xs, sq) - f_of_mean(xs, sq), variance(xs)))

    tight = data["tight"]
    gap_grows_with_spread = (mean_of_f(xs, sq) - f_of_mean(xs, sq)) > (mean_of_f(tight, sq) - f_of_mean(tight, sq)) and mean(xs) == mean(tight)
    print("  wider spread, same mean, bigger gap = %s (%.4f > %.4f)" % (gap_grows_with_spread, mean_of_f(xs, sq) - f_of_mean(xs, sq), mean_of_f(tight, sq) - f_of_mean(tight, sq)))

    ok = convex_underestimates and concave_overestimates and linear_exact and square_gap_is_variance and gap_grows_with_spread
    print("-" * 108)
    print("SELF-TEST %s  convex_underestimates=%s  concave_overestimates=%s  linear_exact=%s  square_gap_is_variance=%s  gap_grows_with_spread=%s"
          % ("PASS" if ok else "FAIL", convex_underestimates, concave_overestimates, linear_exact, square_gap_is_variance, gap_grows_with_spread))
    return ok


def main():
    p = argparse.ArgumentParser(description="The flaw of averages: for a curved model, the average of the outputs is not the output of the average.")
    p.add_argument("--gap", action="store_true")
    p.add_argument("--spread", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("spread=%s (mean %.0f)  tight=%s (mean %.0f)  file=%s  (the datasets are a fixture)"
          % (data["spread"], mean(data["spread"]), data["tight"], mean(data["tight"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gap:
        gap_view(data)
    elif args.spread:
        spread_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
