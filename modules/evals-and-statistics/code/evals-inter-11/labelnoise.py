"""Noisy gold labels cap measured accuracy at 1 minus the noise -- a perfect model cannot score 100%.

An eval scores a model by how often it agrees with the gold label. But gold labels are made by humans or
by an earlier model, and a fraction of them are simply wrong. When a label is wrong, a model that gives
the correct answer DISAGREES with the label and is marked wrong -- penalized for being right. So the
number the eval reports is not the model's true accuracy; it is the agreement between the model and a
noisy reference, and that agreement has a ceiling. If a fraction k of labels are wrong, the highest score
any model can post is 1 - k: even a perfect model loses a point on every mislabeled item.

Under the standard model where the model's errors and the label's errors are independent, the measured
accuracy of a model whose true accuracy is a comes out to a*(1-k) + (1-a)*k. Two consequences bite.
First, the ceiling: measured accuracy cannot exceed 1 - k, so a perfect model scores 1 - k, not 1.
Second, compression: near the ceiling, each real gain in true accuracy moves the measured score by less
than itself, so genuine improvements are partly masked and become hard to see through the label noise.

On this fixture the labels are 10% noisy, so the ceiling is 0.90. A good model (95% true) measures 0.860,
a better model (99%) measures 0.892, and a perfect model (100%) measures exactly 0.900 -- the ceiling.
The true gap from good to perfect is 0.05; the measured gap is 0.040. This computes all of it.

  --models     each model's true accuracy and what the noisy eval measures
  --ceiling    the ceiling 1-k, the perfect model's score, and the gap compression
  --check      measured is capped at 1-k; a perfect model scores 1-k; real gains measure smaller

The noise rate and true accuracies are the fixture; every measured accuracy is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "eval.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def measured_accuracy(true_acc, k):
    """Agreement with a noisy label: right when both right, or both wrong the same way. Capped at 1-k."""
    return round(true_acc * (1 - k) + (1 - true_acc) * k, 4)


def ceiling(k):
    return round(1 - k, 4)


# ----------------------------------------------------------------- printing

def models_view(data):
    k = data["label_noise"]
    print("MODELS — true accuracy vs what a %.0f%%-noisy eval measures" % (k * 100))
    print("-" * 52)
    for name, a in data["models"].items():
        print("  %-8s true %.2f   measured %.3f" % (name, a, measured_accuracy(a, k)))
    print("-" * 52)
    print("  every measured score is below the true one -- the noise costs each model points.")


def ceiling_view(data):
    k = data["label_noise"]
    models = data["models"]
    print("CEILING — the highest possible measured score is 1 - k = %.2f" % ceiling(k))
    print("-" * 60)
    perfect = max(models.values())
    print("  a perfect model (true 1.00) measures %.3f  (= the ceiling %.2f)" % (measured_accuracy(1.0, k), ceiling(k)))
    lo = min(models, key=lambda n: models[n])
    hi = max(models, key=lambda n: models[n])
    true_gap = round(models[hi] - models[lo], 4)
    meas_gap = round(measured_accuracy(models[hi], k) - measured_accuracy(models[lo], k), 4)
    print("  %s -> %s: true gap %.3f, measured gap %.3f  (compressed by 1-2k = %.2f)"
          % (lo, hi, true_gap, meas_gap, 1 - 2 * k))
    print("-" * 60)
    print("  no model can measure above the ceiling; gains near it shrink in the measurement.")


def check(data):
    print("SELF-TEST — measured is capped at 1-k; a perfect model scores 1-k; real gains measure smaller")
    print("-" * 88)
    k = data["label_noise"]
    models = data["models"]
    cap = ceiling(k)

    all_below_ceiling = all(measured_accuracy(a, k) <= cap + 1e-9 for a in models.values())
    print("  no model measures above the ceiling 1-k = %s (cap %.2f)" % (all_below_ceiling, cap))

    perfect_hits_ceiling = abs(measured_accuracy(1.0, k) - cap) < 1e-9
    print("  a perfect model measures exactly the ceiling, not 1.0 = %s (%.3f)" % (perfect_hits_ceiling, measured_accuracy(1.0, k)))

    lo = min(models, key=lambda n: models[n])
    hi = max(models, key=lambda n: models[n])
    true_gap = models[hi] - models[lo]
    meas_gap = measured_accuracy(models[hi], k) - measured_accuracy(models[lo], k)
    gains_compress = meas_gap < true_gap - 1e-9
    print("  a real accuracy gain measures smaller than it is = %s (true %.3f -> measured %.3f)"
          % (gains_compress, round(true_gap, 4), round(meas_gap, 4)))

    ranking_preserved = measured_accuracy(models[hi], k) > measured_accuracy(models[lo], k)
    print("  the better model still ranks higher (order preserved) = %s" % ranking_preserved)

    ok = all_below_ceiling and perfect_hits_ceiling and gains_compress and ranking_preserved
    print("-" * 88)
    print("SELF-TEST %s  all_below_ceiling=%s  perfect_hits_ceiling=%s  gains_compress=%s  ranking_preserved=%s"
          % ("PASS" if ok else "FAIL", all_below_ceiling, perfect_hits_ceiling, gains_compress, ranking_preserved))
    return ok


def main():
    p = argparse.ArgumentParser(description="Noisy gold labels cap measured accuracy at 1-k.")
    p.add_argument("--models", action="store_true")
    p.add_argument("--ceiling", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("label_noise=%.0f%%  models=%s  ceiling=%.2f  file=%s  (the noise and accuracies are a fixture)"
          % (data["label_noise"] * 100, list(data["models"]), ceiling(data["label_noise"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.models:
        models_view(data)
    elif args.ceiling:
        ceiling_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
