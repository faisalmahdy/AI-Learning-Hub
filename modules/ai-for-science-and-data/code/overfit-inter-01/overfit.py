"""Judge a model on held-out data, not the data it was fit to -- a flexible model drives its training error to zero by memorizing the noise, so its in-sample error is optimistic and only a test set reveals whether it generalizes.

Training data is signal plus noise. The signal is the real relationship you want the model to learn; the noise is the random part that will not recur in new data. A flexible enough model can pass through every training point exactly, driving its training error to zero -- but doing so means it has fit the noise as well as the signal, memorizing quirks specific to this sample. Its training error is then a badly optimistic estimate of its true error: near zero on the points it memorized, large on points it has never seen.

A simpler model cannot bend to every point. It has a larger training error, because it does not chase the noise, but that is the point -- it captures the signal and leaves the noise alone. So its error on new data is close to its training error, and far below the flexible model's error on new data. The very thing that made the flexible model look better in training -- zero error -- is the symptom of the disease.

This is why training error cannot be trusted to compare models. Ranked by training error, the memorizer wins every time, because memorizing is exactly what minimizes training error. The ranking that matters -- which model does better on data it has not seen -- can be the reverse, and the only way to see it is to hold out a test set: data from the same process, never shown to the model during fitting, scored afterward.

The gap between a model's training error and its test error is the tell. A small gap means the training error was an honest estimate; a large gap means the model overfit and its training error was a mirage. A responsible evaluation reports the held-out error and watches that gap, never the training error alone.

The rule: evaluate a model on held-out test data, not on the training data, because a flexible model can memorize the training noise and score a near-zero training error that badly overstates how it will do on new data; the train-to-test error gap is the measure of that overfitting.

On this fixture a flexible memorizer scores zero training error but large test error, while a simple least-squares line has a larger training error yet a far smaller test error -- so the in-sample winner is the out-of-sample loser. This computes both.

  --score    each model's mean absolute error on the training set and on the held-out test set
  --gap      the train-to-test error gap for each model -- small for the honest one, large for the memorizer
  --check    the memorizer wins in-sample and loses out-of-sample; the ranking reverses on held-out data

train and test points are the fixture; the two models' errors and gaps are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "overfit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fit_line(xs, ys):
    """Least-squares line: slope = cov(x,y)/var(x), intercept through the means."""
    n = len(xs)
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    cov = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / n
    var = sum((x - xbar) ** 2 for x in xs) / n
    slope = cov / var
    return slope, ybar - slope * xbar


def line_predict(model, x):
    slope, intercept = model
    return slope * x + intercept


def memorizer_predict(train_x, train_y, x):
    """A flexible model: return the y of the nearest training x (exact on any point it has seen)."""
    best = min(range(len(train_x)), key=lambda i: (abs(train_x[i] - x), train_x[i]))
    return train_y[best]


def mae(preds, targets):
    return sum(abs(p - t) for p, t in zip(preds, targets)) / len(targets)


# ----------------------------------------------------------------- printing

def errors(data):
    tx, ty = data["train_x"], data["train_y"]
    testx, testt = data["test_x"], data["test_true"]
    line = fit_line(tx, ty)

    mem_train = mae([memorizer_predict(tx, ty, x) for x in tx], ty)
    mem_test = mae([memorizer_predict(tx, ty, x) for x in testx], testt)
    line_train = mae([line_predict(line, x) for x in tx], ty)
    line_test = mae([line_predict(line, x) for x in testx], testt)
    return line, mem_train, mem_test, line_train, line_test


def score_view(data):
    line, mt, me, lt, le = errors(data)
    print("SCORE — mean absolute error on the data fit vs held-out data")
    print("-" * 58)
    print("  model         train MAE    test MAE")
    print("  memorizer     %-9.2f    %.2f" % (mt, me))
    print("  simple line   %-9.2f    %.2f  (y = %.2f x + %.2f)" % (lt, le, line[0], line[1]))
    print("-" * 58)
    print("  the memorizer's perfect training error hides a large test error")


def gap_view(data):
    line, mt, me, lt, le = errors(data)
    print("GAP — the train-to-test error gap for each model")
    print("-" * 50)
    print("  memorizer    train %.2f -> test %.2f   gap %.2f" % (mt, me, me - mt))
    print("  simple line  train %.2f -> test %.2f   gap %.2f" % (lt, le, le - lt))
    print("-" * 50)
    print("  a large gap is the signature of overfitting")


def check(data):
    print("SELF-TEST — the memorizer wins in-sample and loses out-of-sample; the ranking reverses on held-out data")
    print("-" * 112)
    line, mt, me, lt, le = errors(data)

    memorizer_train_perfect = mt == 0.0
    print("  memorizer: training error is zero (it memorized the points) = %s (%.2f)" % (memorizer_train_perfect, mt))

    memorizer_wins_in_sample = mt < lt
    print("  in-sample the memorizer beats the line = %s (%.2f < %.2f)" % (memorizer_wins_in_sample, mt, lt))

    line_wins_out_of_sample = le < me
    print("  out-of-sample the line beats the memorizer = %s (%.2f < %.2f)" % (line_wins_out_of_sample, le, me))

    ranking_reverses = memorizer_wins_in_sample and line_wins_out_of_sample
    print("  the ranking reverses from train to test = %s" % ranking_reverses)

    memorizer_gap_larger = (me - mt) > (le - lt)
    print("  the memorizer's train-to-test gap is the larger one = %s (%.2f vs %.2f)"
          % (memorizer_gap_larger, me - mt, le - lt))

    ok = (memorizer_train_perfect and memorizer_wins_in_sample and line_wins_out_of_sample
          and ranking_reverses and memorizer_gap_larger)
    print("-" * 112)
    print("SELF-TEST %s  memorizer_train_perfect=%s  memorizer_wins_in_sample=%s  line_wins_out_of_sample=%s  ranking_reverses=%s  memorizer_gap_larger=%s"
          % ("PASS" if ok else "FAIL", memorizer_train_perfect, memorizer_wins_in_sample,
             line_wins_out_of_sample, ranking_reverses, memorizer_gap_larger))
    return ok


def main():
    p = argparse.ArgumentParser(description="Overfitting: evaluate a model on held-out test data, not on the training data, because a flexible model can memorize the training noise and score a near-zero training error that badly overstates how it will do on new data; the train-to-test error gap is the measure of that overfitting.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--gap", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("train=%d points  test=%d points  truth: y=%d x  file=%s  (the points are a fixture)"
          % (len(data["train_x"]), len(data["test_x"]), data["slope"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.gap:
        gap_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
