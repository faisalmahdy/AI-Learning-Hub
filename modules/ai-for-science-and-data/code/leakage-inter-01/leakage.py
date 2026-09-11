"""Exclude a feature that will not be available at prediction time -- or downstream of the label -- no matter how well it predicts, because it inflates measured accuracy and that accuracy vanishes in production.

You train a model to predict a label and judge it by accuracy. The instinct is to feed it every feature you have and keep whatever raises the score. That instinct has a trap: some features carry information about the label that will not actually be available at the moment you need a prediction. A value recorded only after the outcome is known. A proxy that exists because the outcome happened -- a late-fee flag on an account that predicts default, but is set as a consequence of default. A field that, once you trace it, just re-encodes the label. During development these features make accuracy look wonderful, because in the historical data they genuinely do predict the label -- they were derived from it.

This is data leakage, and it is a mirage. The feature predicts the label in your test set only because your test set already knows the outcome. In production the value is absent, or not yet determined at prediction time, or stale -- and the accuracy it bought disappears. The model that scored 100% in cross-validation falls back to the honest accuracy of the legitimate features, and the drop is discovered in production, at the worst possible time, after the model was trusted.

The defense is not statistical, it is causal and temporal: for every feature, ask whether its value is genuinely known at the instant a prediction must be made, and whether it is a cause the label depends on rather than an effect that depends on the label. A feature that fails either test is a leak and must be excluded from training, however much it helps the metric -- because the metric it helps is measuring a world (the test set, where outcomes are known) that the deployed model will never be in.

The rule: exclude any feature not available at prediction time or causally downstream of the label, because such a feature leaks the answer into training and inflates measured accuracy -- so the reported score reflects the leak, not the model, and collapses to the legitimate-feature accuracy in production.

On this fixture the leak_flag feature equals the label (it is assigned after the outcome), so a classifier using it scores 100%; the legitimate feature honestly scores 75%. The leak inflates the reported accuracy by 25 points, all of which is lost in production where the flag is not yet known. This computes both.

  --features   each feature's best single-threshold accuracy and whether it is available at prediction time
  --accuracy   the reported accuracy WITH the leak vs the honest production accuracy WITHOUT it
  --check      the leaky feature inflates accuracy but is unavailable at prediction time; excluding it gives the honest production score

features and samples are the fixture; every accuracy is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "leakage.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def best_threshold_accuracy(values, labels):
    """A deterministic single-threshold classifier: predict 1 if value >= t, pick the best t."""
    best = 0.0
    for t in sorted(set(values)) + [max(values) + 1]:
        preds = [1 if v >= t else 0 for v in values]
        acc = sum(p == l for p, l in zip(preds, labels)) / len(labels)
        if acc > best:
            best = acc
    return best


def feature_accuracy(data, name):
    labels = [s["label"] for s in data["samples"]]
    values = [s[name] for s in data["samples"]]
    return best_threshold_accuracy(values, labels)


def available(data, name):
    return data["features"][name]["available_at_prediction"]


# ----------------------------------------------------------------- printing

def features_view(data):
    print("FEATURES — each feature's best single-threshold accuracy and availability")
    print("-" * 68)
    print("  feature       accuracy  available at prediction?")
    for name in data["features"]:
        acc = feature_accuracy(data, name)
        av = available(data, name)
        flag = "" if av else "   <- LEAK (known only after the outcome)"
        print("  %-12s  %.0f%%      %s%s" % (name, 100 * acc, av, flag))
    print("-" * 68)
    print("  the leak scores highest but its value does not exist at prediction time")


def accuracy_view(data):
    leak = feature_accuracy(data, "leak_flag")
    legit = feature_accuracy(data, "legit_score")
    print("ACCURACY — reported (with the leak) vs honest production (without it)")
    print("-" * 66)
    print("  reported accuracy, using leak_flag       = %.0f%%" % (100 * leak))
    print("  honest production accuracy, legit_score  = %.0f%%" % (100 * legit))
    print("  inflation bought by the leak             = %+d points" % round(100 * (leak - legit)))
    print("-" * 66)
    print("  in production leak_flag is not yet known, so the real accuracy is the honest %.0f%%" % (100 * legit))


def check(data):
    print("SELF-TEST — the leaky feature inflates accuracy but is unavailable at prediction time; excluding it gives the honest production score")
    print("-" * 132)
    leak = feature_accuracy(data, "leak_flag")
    legit = feature_accuracy(data, "legit_score")

    leak_predicts_perfectly = leak == 1.0
    print("  the leaky feature predicts the label almost perfectly = %s (%.0f%%)" % (leak_predicts_perfectly, 100 * leak))

    leak_unavailable_at_prediction = available(data, "leak_flag") is False
    print("  the leaky feature is NOT available at prediction time = %s" % leak_unavailable_at_prediction)

    leak_inflates_accuracy = leak > legit
    print("  the leak reports higher accuracy than the honest feature = %s (%.0f%% > %.0f%%)"
          % (leak_inflates_accuracy, 100 * leak, 100 * legit))

    legit_available = available(data, "legit_score") is True
    print("  the legitimate feature IS available at prediction time = %s" % legit_available)

    production_matches_legit = round(100 * legit) < round(100 * leak)
    print("  production accuracy (leak excluded) drops to the honest score = %s (%.0f%%, not %.0f%%)"
          % (production_matches_legit, 100 * legit, 100 * leak))

    ok = (leak_predicts_perfectly and leak_unavailable_at_prediction and leak_inflates_accuracy
          and legit_available and production_matches_legit)
    print("-" * 132)
    print("SELF-TEST %s  leak_predicts_perfectly=%s  leak_unavailable_at_prediction=%s  leak_inflates_accuracy=%s  legit_available=%s  production_matches_legit=%s"
          % ("PASS" if ok else "FAIL", leak_predicts_perfectly, leak_unavailable_at_prediction, leak_inflates_accuracy, legit_available, production_matches_legit))
    return ok


def main():
    p = argparse.ArgumentParser(description="Data leakage: exclude any feature not available at prediction time or causally downstream of the label, because such a feature leaks the answer into training and inflates measured accuracy -- so the reported score reflects the leak, not the model, and collapses to the legitimate-feature accuracy in production.")
    p.add_argument("--features", action="store_true")
    p.add_argument("--accuracy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("samples=%d  features=%s  file=%s  (the dataset is a fixture)"
          % (len(data["samples"]), list(data["features"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.features:
        features_view(data)
    elif args.accuracy:
        accuracy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
