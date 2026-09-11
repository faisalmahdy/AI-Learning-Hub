"""Macro-average when classes are imbalanced, or a micro score hides a total failure on the rare class.

An eval set is rarely balanced -- most examples are the common case and a few are the rare one. When you
collapse per-class performance into one number, how you average decides what the number means. A micro
average pools every example and divides total correct by total examples, so each example counts equally --
which means the common class, having most of the examples, dominates the score. A model that aces the
common case and completely botches the rare one still posts a high micro score, because the rare case is a
rounding error in the pool. The single number looks great and hides the failure that matters.

A macro average instead computes each class's accuracy separately and averages those, so each class counts
equally regardless of how many examples it has. Now failing the rare class costs half the score, and the
number reflects whether the model works across the board rather than just on the majority. The choice is
not cosmetic: on an imbalanced set, micro and macro can rank two models in opposite orders, so reporting
the wrong one crowns the wrong model.

On this fixture two models are scored on 90 common-class and 10 rare-class examples. Model X aces the
common class (0.978) and fails the rare one (0.300); model Y is balanced (0.889 and 0.900). Micro scores
them 0.91 and 0.89, so micro prefers X -- the model that fails the rare class. Macro scores them 0.639 and
0.894, so macro prefers Y. Same data; the averaging flips the winner. This computes both.

  --scores     each model's per-class accuracy, plus its micro and macro average
  --rank       which model each averaging method prefers
  --check      micro hides X's rare-class failure and prefers X; macro reveals it and prefers the balanced Y

The per-class counts are the fixture; every average is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "results.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def class_acc(model):
    """Per-class accuracy: correct / total for each class."""
    return {c: model[c]["correct"] / model[c]["total"] for c in model}


def micro(model):
    """Pool all examples: total correct / total examples -- the majority class dominates."""
    correct = sum(model[c]["correct"] for c in model)
    total = sum(model[c]["total"] for c in model)
    return round(correct / total, 3)


def macro(model):
    """Average the per-class accuracies -- each class counts equally."""
    accs = class_acc(model)
    return round(sum(accs.values()) / len(accs), 3)


def spread(model):
    """Gap between best and worst class accuracy -- how balanced the model is."""
    accs = list(class_acc(model).values())
    return round(max(accs) - min(accs), 3)


def prefer(models, metric):
    """Which model scores highest under the given averaging metric."""
    return max(models, key=lambda m: metric(models[m]))


# ----------------------------------------------------------------- printing

def scores_view(data):
    models = data["models"]
    print("SCORES — per-class accuracy, micro, and macro for each model")
    print("-" * 62)
    for name, model in models.items():
        accs = class_acc(model)
        cells = "   ".join("%s %.3f" % (c, accs[c]) for c in model)
        print("  %s:  %s" % (name, cells))
        print("      micro %.3f   macro %.3f" % (micro(model), macro(model)))
    print("-" * 62)
    counts = {c: data["models"]["model_X"][c]["total"] for c in data["models"]["model_X"]}
    print("  class sizes: %s  (imbalanced)" % counts)


def rank_view(data):
    models = data["models"]
    print("RANK — which model each averaging method prefers")
    print("-" * 62)
    print("  by micro:  %s   (%.3f vs %.3f)" % (prefer(models, micro), micro(models["model_X"]), micro(models["model_Y"])))
    print("  by macro:  %s   (%.3f vs %.3f)" % (prefer(models, macro), macro(models["model_X"]), macro(models["model_Y"])))
    print("-" * 62)
    print("  micro and macro crown different models on the same data.")


def check(data):
    print("SELF-TEST — micro hides X's rare-class failure and prefers X; macro reveals it and prefers the balanced Y")
    print("-" * 106)
    models = data["models"]
    x, y = models["model_X"], models["model_Y"]
    rare = min(x, key=lambda c: x[c]["total"])   # the rare class name

    micro_hides_failure = micro(x) > 0.9 and class_acc(x)[rare] < 0.4
    print("  X's micro is high while it fails the rare class = %s (micro %.3f, rare acc %.3f)"
          % (micro_hides_failure, micro(x), class_acc(x)[rare]))

    macro_reveals = micro(x) - macro(x) > 0.2
    print("  X's macro is far below its micro, exposing the imbalance = %s (%.3f vs %.3f)"
          % (macro_reveals, macro(x), micro(x)))

    ranking_flips = prefer(models, micro) != prefer(models, macro)
    print("  micro and macro prefer different models = %s (micro->%s, macro->%s)"
          % (ranking_flips, prefer(models, micro), prefer(models, macro)))

    macro_prefers_balanced = spread(models[prefer(models, macro)]) < spread(models[prefer(models, micro)])
    print("  the macro-preferred model is the more balanced one = %s (spread %.3f vs %.3f)"
          % (macro_prefers_balanced, spread(models[prefer(models, macro)]), spread(models[prefer(models, micro)])))

    micro_tracks_majority = abs(micro(x) - max(class_acc(x).values())) < 0.1
    print("  X's micro tracks its best (majority) class, not its worst = %s" % micro_tracks_majority)

    ok = micro_hides_failure and macro_reveals and ranking_flips and macro_prefers_balanced and micro_tracks_majority
    print("-" * 106)
    print("SELF-TEST %s  micro_hides_failure=%s  macro_reveals=%s  ranking_flips=%s  macro_prefers_balanced=%s  micro_tracks_majority=%s"
          % ("PASS" if ok else "FAIL", micro_hides_failure, macro_reveals, ranking_flips, macro_prefers_balanced, micro_tracks_majority))
    return ok


def main():
    p = argparse.ArgumentParser(description="Macro-average an imbalanced eval so the rare class is not hidden.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("models=%d  classes=%d  file=%s  (the per-class counts are a fixture)"
          % (len(data["models"]), len(next(iter(data["models"].values()))), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
