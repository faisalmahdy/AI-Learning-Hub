"""On an imbalanced test set, accuracy rewards the do-nothing classifier -- score the rare class with recall, F1, balance.

Accuracy is the fraction of predictions that are correct, and it is the default metric everyone reaches for. It is also
almost useless when the classes are imbalanced, because it lets a classifier score well by ignoring the rare class
entirely. If 95% of your examples are negative -- the normal case for fraud, disease, defect detection, any rare-event
problem -- then a classifier that predicts 'negative' for EVERYTHING is 95% accurate while catching zero positives. It
has done nothing, learned nothing, and is worthless for the task (which is to find the positives), yet accuracy calls it
a strong model. Worse, accuracy can rank that do-nothing classifier ABOVE a genuinely useful one: a real model that
catches most positives but pays for it with some false positives can have LOWER accuracy than the majority-class
baseline, because each false positive is a wrong answer that the do-nothing model never risks.

The fix is to score the rare class directly, with metrics that do not let the majority class drown it out. Recall (of
the actual positives, how many did we catch?) exposes the do-nothing classifier immediately: its recall is 0. Precision
(of our positive predictions, how many were right?) measures the false-positive cost. F1 combines the two as their
harmonic mean, which is 0 whenever either is 0 -- so a classifier that catches nothing scores F1 = 0 no matter how high
its accuracy. Balanced accuracy averages the true-positive rate and the true-negative rate, giving the rare class equal
weight to the common one, so the do-nothing baseline scores 0.5 (chance) rather than 0.95. Any of these separates the
useful model from the useless one that accuracy confuses.

On this fixture the test set is 50 positives and 950 negatives. The majority-negative classifier scores accuracy 0.95
but recall 0, F1 0, and balanced accuracy 0.5 -- a flat 'it does nothing.' The real model scores accuracy 0.94 (LOWER
than the do-nothing baseline) but recall 0.80, F1 0.57, and balanced accuracy 0.87. Accuracy ranks the do-nothing
classifier first; every rare-class metric ranks the real model far ahead. This computes both.

  --accuracy   both classifiers' confusion counts and accuracy -- the do-nothing baseline outscores the real model
  --metrics    precision, recall, F1, and balanced accuracy -- the real model wins on every rare-class metric
  --check      the majority classifier has 0.95 accuracy but 0 recall/F1; accuracy prefers it; F1 and balance prefer the real model

The confusion counts are the fixture; every metric is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "imbalance.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def accuracy(c):
    return (c["tp"] + c["tn"]) / (c["tp"] + c["fp"] + c["fn"] + c["tn"])


def precision(c):
    return c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0


def recall(c):
    return c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0


def specificity(c):
    return c["tn"] / (c["tn"] + c["fp"]) if (c["tn"] + c["fp"]) else 0.0


def f1(c):
    p, r = precision(c), recall(c)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def balanced_accuracy(c):
    """Average of the true-positive rate (recall) and the true-negative rate (specificity) -- classes weighted equally."""
    return (recall(c) + specificity(c)) / 2


# ----------------------------------------------------------------- printing

def accuracy_view(data):
    cs = data["classifiers"]
    print("ACCURACY — imbalanced test set: %d positives, %d negatives" % (data["positives"], data["negatives"]))
    print("-" * 66)
    print("  classifier          tp   fp   fn   tn    accuracy")
    for name, c in cs.items():
        print("  %-18s  %-4d %-4d %-4d %-5d %.4f" % (name, c["tp"], c["fp"], c["fn"], c["tn"], accuracy(c)))
    print("-" * 66)
    best = max(cs, key=lambda n: accuracy(cs[n]))
    print("  accuracy's top model: %s -- the do-nothing baseline, which catches ZERO positives." % best)


def metrics_view(data):
    cs = data["classifiers"]
    print("METRICS — score the rare (positive) class directly")
    print("-" * 68)
    print("  classifier          precision  recall   F1       balanced_acc")
    for name, c in cs.items():
        print("  %-18s  %-9.3f  %-7.3f  %-8.3f %.3f" % (name, precision(c), recall(c), f1(c), balanced_accuracy(c)))
    print("-" * 68)
    best = max(cs, key=lambda n: f1(cs[n]))
    print("  F1's top model: %s -- the real classifier, which actually catches positives." % best)


def check(data):
    print("SELF-TEST — the majority classifier has 0.95 accuracy but 0 recall/F1; accuracy prefers it; F1 and balance prefer the real model")
    print("-" * 128)
    cs = data["classifiers"]
    maj, real = cs["majority_negative"], cs["real_model"]

    maj_accuracy_high = abs(accuracy(maj) - 0.95) < 1e-9
    print("  the do-nothing classifier's accuracy is 0.95 = %s (%.4f)" % (maj_accuracy_high, accuracy(maj)))

    maj_useless = recall(maj) == 0.0 and f1(maj) == 0.0
    print("  yet it has zero recall and zero F1 (catches no positives) = %s" % maj_useless)

    accuracy_prefers_donothing = accuracy(maj) > accuracy(real)
    print("  accuracy ranks the do-nothing classifier ABOVE the real model = %s (%.4f > %.4f)"
          % (accuracy_prefers_donothing, accuracy(maj), accuracy(real)))

    f1_prefers_real = f1(real) > f1(maj)
    print("  F1 ranks the real model far above = %s (%.3f vs %.3f)" % (f1_prefers_real, f1(real), f1(maj)))

    balance_prefers_real = balanced_accuracy(real) > balanced_accuracy(maj)
    print("  balanced accuracy also prefers the real model = %s (%.3f vs %.3f)"
          % (balance_prefers_real, balanced_accuracy(real), balanced_accuracy(maj)))

    ok = maj_accuracy_high and maj_useless and accuracy_prefers_donothing and f1_prefers_real and balance_prefers_real
    print("-" * 128)
    print("SELF-TEST %s  maj_accuracy_high=%s  maj_useless=%s  accuracy_prefers_donothing=%s  f1_prefers_real=%s  balance_prefers_real=%s"
          % ("PASS" if ok else "FAIL", maj_accuracy_high, maj_useless, accuracy_prefers_donothing, f1_prefers_real, balance_prefers_real))
    return ok


def main():
    p = argparse.ArgumentParser(description="Accuracy under class imbalance: on a mostly-negative test set a classifier that predicts the majority class scores high accuracy while catching none of the rare positives, and accuracy can rank it above a useful model; score the rare class with recall, precision, F1, and balanced accuracy instead.")
    p.add_argument("--accuracy", action="store_true")
    p.add_argument("--metrics", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("positives=%d  negatives=%d  classifiers=%s  file=%s  (the confusion counts are a fixture)"
          % (data["positives"], data["negatives"], list(data["classifiers"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.accuracy:
        accuracy_view(data)
    elif args.metrics:
        metrics_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
