"""The softmax cross-entropy gradient is just (softmax - onehot) -- not -1/p; the clean form is why backprop is cheap and stable.

Softmax cross-entropy is the standard classification loss: the model emits raw scores (logits), softmax turns them into a
probability distribution, and the loss is the negative log of the probability placed on the true class. Minimizing it
pushes probability toward the correct class. To train, backprop needs the gradient of this loss with respect to the
logits -- and here something remarkable happens. The loss is a composition of a log and a softmax (whose derivative is a
full Jacobian coupling every output to every input), so you would expect a messy gradient. Instead it collapses to one of
the cleanest results in deep learning: the gradient with respect to logit i is simply p_i - y_i, the predicted
probability minus the target (1 for the true class, 0 otherwise). Softmax(logits) minus the one-hot label, nothing more.

That clean form is not a convenience, it is why the training loop is fast and numerically stable. Each gradient component
is a probability minus a 0-or-1 target, so it is bounded in [-1, 1]: never explosive, always pointing the right way --
negative for the true class (raise its logit) and positive for the others (lower theirs) -- and the components sum to
zero, because softmax outputs and the one-hot label each sum to 1. Frameworks fuse softmax and cross-entropy into one op
precisely so they can emit p - y directly, skipping the ill-conditioned intermediate of computing softmax, then log,
then dividing by a possibly-tiny probability.

The common mistake is to differentiate only the visible -log(p_true) term and stop: d/dp_true of -log(p_true) is
-1/p_true, so the naive gradient is -1/p_true for the true class and 0 for the rest. This treats the logit as if it were
the probability and forgets that softmax couples all the logits, so raising one logit lowers the others' probabilities.
The naive gradient is wrong (it does not match the true gradient), unbounded (it blows up as p_true -> 0), and it zeroes
the other classes that should be pushed down.

On this fixture the logits are [2.0, 1.0, 0.1] with class 0 correct. Softmax gives [0.659, 0.242, 0.099]. The correct
gradient p - y is [-0.341, 0.242, 0.099] -- it matches a numerical (finite-difference) gradient and sums to 0. The naive
-1/p gradient is [-1.517, 0, 0], which does NOT match the numerical gradient. This computes all of them.

  --gradient  the softmax, the analytic p - y gradient, and the naive -1/p gradient, side by side
  --numeric   a finite-difference gradient of the loss, matching p - y and NOT matching the naive form
  --check     the analytic gradient equals p - y, matches the numerical gradient, sums to zero, and the naive form is wrong

The logits and true class are the fixture; every probability and gradient is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "xentgrad.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(logits):
    """Numerically stable softmax: subtract the max before exponentiating."""
    m = max(logits)
    e = [math.exp(x - m) for x in logits]
    s = sum(e)
    return [v / s for v in e]


def cross_entropy(logits, true_class):
    """Negative log probability of the true class under the softmax."""
    return -math.log(softmax(logits)[true_class])


def analytic_grad(logits, true_class):
    """The clean gradient of softmax cross-entropy wrt the logits: p_i - y_i (softmax minus one-hot)."""
    p = softmax(logits)
    return [p[i] - (1.0 if i == true_class else 0.0) for i in range(len(logits))]


def naive_grad(logits, true_class):
    """The WRONG gradient: differentiate only -log(p_true), get -1/p_true, and leave the other classes at 0."""
    p = softmax(logits)
    return [-1.0 / p[i] if i == true_class else 0.0 for i in range(len(logits))]


def numerical_grad(logits, true_class, h=1e-5):
    """Finite-difference gradient of the loss wrt each logit -- the ground truth to check against."""
    g = []
    for i in range(len(logits)):
        up = list(logits); up[i] += h
        dn = list(logits); dn[i] -= h
        g.append((cross_entropy(up, true_class) - cross_entropy(dn, true_class)) / (2 * h))
    return g


# ----------------------------------------------------------------- printing

def _fmt(v):
    return "[" + ", ".join("%+.3f" % x for x in v) + "]"


def gradient_view(data):
    logits, tc = data["logits"], data["true_class"]
    print("GRADIENT — softmax and the analytic vs naive gradient (true class = %d)" % tc)
    print("-" * 62)
    print("  logits           = %s" % _fmt(logits))
    print("  softmax p        = %s  (sums to %.3f)" % (_fmt(softmax(logits)), sum(softmax(logits))))
    print("-" * 62)
    print("  analytic  p - y  = %s   <- correct, bounded in [-1,1]" % _fmt(analytic_grad(logits, tc)))
    print("  naive   -1/p_true= %s   <- wrong: ignores softmax coupling, unbounded" % _fmt(naive_grad(logits, tc)))


def numeric_view(data):
    logits, tc = data["logits"], data["true_class"]
    num = numerical_grad(logits, tc)
    ana = analytic_grad(logits, tc)
    nai = naive_grad(logits, tc)
    print("NUMERIC — finite-difference gradient vs the two formulas")
    print("-" * 60)
    print("  numerical (truth)  = %s" % _fmt(num))
    print("  analytic  p - y    = %s   diff %.2e" % (_fmt(ana), max(abs(a - n) for a, n in zip(ana, num))))
    print("  naive   -1/p_true  = %s   diff %.2e" % (_fmt(nai), max(abs(a - n) for a, n in zip(nai, num))))
    print("-" * 60)
    print("  p - y matches the numerical gradient; the naive form does not.")


def check(data):
    print("SELF-TEST — the analytic gradient equals p - y, matches the numerical gradient, sums to zero, and the naive form is wrong")
    print("-" * 124)
    logits, tc = data["logits"], data["true_class"]
    p = softmax(logits)
    ana = analytic_grad(logits, tc)
    num = numerical_grad(logits, tc)
    nai = naive_grad(logits, tc)

    is_p_minus_y = ana == [p[i] - (1.0 if i == tc else 0.0) for i in range(len(logits))]
    print("  the analytic gradient is exactly softmax minus one-hot = %s (%s)" % (is_p_minus_y, _fmt(ana)))

    matches_numeric = max(abs(a - n) for a, n in zip(ana, num)) < 1e-4
    print("  it matches the numerical gradient = %s (max diff %.2e)" % (matches_numeric, max(abs(a - n) for a, n in zip(ana, num))))

    sums_to_zero = abs(sum(ana)) < 1e-9
    print("  the gradient components sum to zero = %s (%.2e)" % (sums_to_zero, sum(ana)))

    true_class_negative = ana[tc] < 0 and all(ana[i] > 0 for i in range(len(logits)) if i != tc)
    print("  true-class gradient is negative, others positive = %s" % true_class_negative)

    naive_wrong = max(abs(a - n) for a, n in zip(nai, num)) > 1e-4
    print("  the naive -1/p gradient does NOT match the truth = %s (max diff %.2e)" % (naive_wrong, max(abs(a - n) for a, n in zip(nai, num))))

    ok = is_p_minus_y and matches_numeric and sums_to_zero and true_class_negative and naive_wrong
    print("-" * 124)
    print("SELF-TEST %s  is_p_minus_y=%s  matches_numeric=%s  sums_to_zero=%s  true_class_negative=%s  naive_wrong=%s"
          % ("PASS" if ok else "FAIL", is_p_minus_y, matches_numeric, sums_to_zero, true_class_negative, naive_wrong))
    return ok


def main():
    p = argparse.ArgumentParser(description="Softmax cross-entropy gradient: despite composing a softmax and a log, the gradient wrt the logits collapses to softmax minus the one-hot label (p - y), which is bounded and sums to zero and is why softmax+cross-entropy are fused; the naive -1/p_true gradient forgets softmax couples the logits and is wrong and unbounded.")
    p.add_argument("--gradient", action="store_true")
    p.add_argument("--numeric", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("logits=%s  true_class=%d  file=%s  (the logits and true class are a fixture)"
          % (data["logits"], data["true_class"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gradient:
        gradient_view(data)
    elif args.numeric:
        numeric_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
