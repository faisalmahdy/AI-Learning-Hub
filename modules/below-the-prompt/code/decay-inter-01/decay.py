"""Add weight decay, or the model fits the training noise and the weight lands far from the truth.

A model is trained to minimize a loss on the training data. If the training signal is noisy -- and it always
is -- minimizing the training loss alone drives the weights to whatever fits that noise exactly, including the
part that is not real. A weight that fits the noise is large and specific to the training set, and it
generalizes badly: the true relationship is gentler than the noisy data suggests. Nothing in "minimize the
training loss" pushes back on this; the optimizer will happily chase the noise all the way.

Weight decay pushes back. Add a penalty proportional to the squared weight -- lambda * w^2 -- to the loss, so
the optimizer pays a price for large weights and settles for a smaller one that fits the training data a
little worse but generalizes better. Each gradient step now includes a term that pulls the weight toward
zero, so the weight shrinks unless the data pulls back hard enough to justify its size. For this one-weight
model the balance has a closed form: fitting a target t under decay lambda lands the weight at t/(1+lambda),
shrunk toward 0 by the factor 1/(1+lambda). The strength lambda is a dial: too little and you overfit the
noise, too much and you underfit, crushing even the real signal.

On this fixture the noisy training target is 12 but the weight should really be 6 to generalize. With no decay
the weight lands on 12 -- the noise, fully fit. With lambda=1 it lands on 12/2 = 6 -- exactly the truth. With
lambda=4 it lands on 2.4 -- shrunk past the truth, underfit. The best test error is at a moderate lambda, not
at 0 and not at the largest. This computes both.

  --fit        the weight each lambda converges to, and its training vs test error
  --curve      test error across the lambdas -- the U-shape with a best interior value
  --check      no decay overfits the noise; moderate decay generalizes best; too much underfits

The targets, lambdas, and schedule are the fixture; every weight is computed by gradient descent. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "decay.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def train(target, lam, lr, steps):
    """Gradient descent on (w - target)^2 + lam*w^2; the gradient is 2(w-target) + 2*lam*w."""
    w = 0.0
    for _ in range(steps):
        w -= lr * (2 * (w - target) + 2 * lam * w)
    return w


def train_error(w, target):
    return (w - target) ** 2


def test_error(w, true_value):
    return (w - true_value) ** 2


def closed_form(target, lam):
    """The minimizer of (w-target)^2 + lam*w^2 is target/(1+lam)."""
    return target / (1 + lam)


# ----------------------------------------------------------------- printing

def fit_view(data):
    t, tv, lr, steps = data["noisy_target"], data["true_value"], data["lr"], data["steps"]
    print("FIT — weight per lambda (noisy target %.0f, true value %.0f)" % (t, tv))
    print("-" * 64)
    print("  lambda   weight    train err   test err")
    for lam in data["lambdas"]:
        w = train(t, lam, lr, steps)
        print("  %5.1f    %5.2f     %7.2f    %7.2f" % (lam, w, train_error(w, t), test_error(w, tv)))
    print("-" * 64)
    print("  no decay fits the noisy target; decay shrinks the weight toward 0.")


def curve_view(data):
    t, tv, lr, steps = data["noisy_target"], data["true_value"], data["lr"], data["steps"]
    print("CURVE — test error across lambda (the generalization U-shape)")
    print("-" * 64)
    best_lam, best_err = None, None
    for lam in data["lambdas"]:
        w = train(t, lam, lr, steps)
        te = test_error(w, tv)
        bar = "#" * int(round(te))
        print("  lambda %4.1f  test err %6.2f  %s" % (lam, te, bar))
        if best_err is None or te < best_err:
            best_lam, best_err = lam, te
    print("-" * 64)
    print("  lowest test error at lambda %.1f -- an interior value, not 0 or the max." % best_lam)


def check(data):
    print("SELF-TEST — no decay overfits the noise; moderate decay generalizes best; too much underfits")
    print("-" * 100)
    t, tv, lr, steps = data["noisy_target"], data["true_value"], data["lr"], data["steps"]
    lams = data["lambdas"]
    ws = {lam: train(t, lam, lr, steps) for lam in lams}
    tes = {lam: test_error(ws[lam], tv) for lam in lams}
    best_lam = min(lams, key=lambda l: tes[l])

    no_decay_fits_noise = abs(ws[0.0] - t) < 1e-6
    print("  with no decay the weight equals the noisy target = %s (%.2f)" % (no_decay_fits_noise, ws[0.0]))

    decay_shrinks_weight = all(ws[lams[i + 1]] < ws[lams[i]] for i in range(len(lams) - 1))
    print("  more decay shrinks the weight monotonically = %s" % decay_shrinks_weight)

    best_test_is_interior = best_lam != lams[0] and best_lam != lams[-1]
    print("  the best test error is at an interior lambda = %s (lambda %.1f)" % (best_test_is_interior, best_lam))

    moderate_beats_no_decay = tes[best_lam] < tes[0.0]
    print("  moderate decay beats no decay on test error = %s (%.2f < %.2f)" % (moderate_beats_no_decay, tes[best_lam], tes[0.0]))

    matches_closed_form = all(abs(ws[lam] - closed_form(t, lam)) < 1e-4 for lam in lams)
    print("  each weight matches the closed form t/(1+lambda) = %s" % matches_closed_form)

    ok = no_decay_fits_noise and decay_shrinks_weight and best_test_is_interior and moderate_beats_no_decay and matches_closed_form
    print("-" * 100)
    print("SELF-TEST %s  no_decay_fits_noise=%s  decay_shrinks_weight=%s  best_test_is_interior=%s  moderate_beats_no_decay=%s  matches_closed_form=%s"
          % ("PASS" if ok else "FAIL", no_decay_fits_noise, decay_shrinks_weight, best_test_is_interior, moderate_beats_no_decay, matches_closed_form))
    return ok


def main():
    p = argparse.ArgumentParser(description="Add weight decay (lambda*w^2) so the model does not fit the training noise.")
    p.add_argument("--fit", action="store_true")
    p.add_argument("--curve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("noisy_target=%.0f  true_value=%.0f  lambdas=%s  file=%s  (the setup is a fixture)"
          % (data["noisy_target"], data["true_value"], data["lambdas"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fit:
        fit_view(data)
    elif args.curve:
        curve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
