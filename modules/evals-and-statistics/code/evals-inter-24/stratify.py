"""Weight the eval by the production mix, or an eval set that over-samples easy cases reports a score you won't see.

An eval's headline number is an average of per-category accuracies weighted by how many of each category the eval
set happens to contain. That makes the number depend on the eval set's MIX, not just the model. If the eval set
over-represents the easy categories -- because they were cheaper to collect, or because whoever built the set did
not match production -- the average leans on the high accuracies and comes out too high. The model has not
changed; the eval merely asked it more of the questions it is good at. So the reported score is a biased estimate
of what the model will actually do in production, biased by exactly the difference between the eval mix and the
real mix, and a team can ship on a 90% eval only to watch production come in far lower.

The fix is to weight the per-category accuracies by the PRODUCTION distribution, not the eval set's counts. The
production-weighted average answers the question you actually care about -- what accuracy will the model deliver
on the traffic it will really face -- and it uses the very same per-category numbers, just combined by the right
weights. When the eval set matches production, the two averages agree and nothing changes; when it does not, the
production-weighted number is the honest one, and the gap between them is a measurement of how unrepresentative
your eval set is, not of the model.

On this fixture the model is 95% accurate on easy inputs and 50% on hard ones. The eval set is 90 easy and 10
hard, so its aggregate is 0.905. Production is a 50/50 mix, so the production-weighted accuracy is 0.725. The eval
overstates real-world accuracy by 0.18, entirely because it over-sampled the easy category. This computes both.

  --score      the eval-set aggregate vs the production-weighted accuracy, and the gap
  --attribute  that the gap comes entirely from the mix (same per-category accuracy, different weights)
  --check      the eval over-samples easy and inflates the score; reweighting to production recovers the honest one

The accuracies and mixes are the fixture; every average is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "stratify.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def weighted(accuracy, weights):
    """Accuracy averaged over categories weighted by `weights` (counts or a distribution)."""
    total = sum(weights.values())
    return sum(accuracy[c] * weights[c] for c in accuracy) / total


def eval_aggregate(data):
    """The eval's headline number: accuracy weighted by the eval set's category counts."""
    return weighted(data["accuracy"], data["eval_counts"])


def production_estimate(data):
    """The honest number: accuracy weighted by the production category distribution."""
    return weighted(data["accuracy"], data["production"])


# ----------------------------------------------------------------- printing

def score_view(data):
    acc = data["accuracy"]
    print("SCORE — eval-set aggregate vs production-weighted accuracy")
    print("-" * 60)
    print("  per-category accuracy:  %s" % {c: acc[c] for c in acc})
    print("  eval set mix:           %s  -> aggregate %.3f" % (data["eval_counts"], eval_aggregate(data)))
    print("  production mix:         %s -> estimate  %.3f" % (data["production"], production_estimate(data)))
    print("  eval overstates by:     %.3f" % (eval_aggregate(data) - production_estimate(data)))
    print("-" * 60)
    print("  the eval over-samples the easy category, so its average leans high.")


def attribute_view(data):
    acc, ev, prod = data["accuracy"], data["eval_counts"], data["production"]
    ev_total = sum(ev.values())
    print("ATTRIBUTE — the gap is the mix, not the model (same accuracies, different weights)")
    print("-" * 66)
    print("  category   accuracy   eval weight   prod weight")
    for c in acc:
        print("  %-8s   %.2f       %.2f          %.2f" % (c, acc[c], ev[c] / ev_total, prod[c]))
    print("  gap = sum(accuracy * (eval_weight - prod_weight)) = %.3f" % sum(acc[c] * (ev[c] / ev_total - prod[c]) for c in acc))
    print("-" * 66)
    print("  the accuracies are identical; only the weights differ, and that difference is the whole gap.")


def check(data):
    print("SELF-TEST — the eval over-samples easy and inflates the score; reweighting to production recovers the honest one")
    print("-" * 116)
    acc, ev, prod = data["accuracy"], data["eval_counts"], data["production"]
    ev_total = sum(ev.values())

    eval_inflated = eval_aggregate(data) > production_estimate(data)
    print("  the eval aggregate is higher than the production estimate = %s (%.3f > %.3f)" % (eval_inflated, eval_aggregate(data), production_estimate(data)))

    gap_is_large = eval_aggregate(data) - production_estimate(data) > 0.1
    print("  the overstatement is large, not rounding = %s (%.3f)" % (gap_is_large, eval_aggregate(data) - production_estimate(data)))

    mix_differs = {c: ev[c] / ev_total for c in ev} != prod
    print("  the eval mix differs from production = %s" % mix_differs)

    gap_from_mix = abs((eval_aggregate(data) - production_estimate(data)) - sum(acc[c] * (ev[c] / ev_total - prod[c]) for c in acc)) < 1e-9
    print("  the gap equals sum(accuracy * weight difference) -- the mix, not the model = %s" % gap_from_mix)

    reweight_recovers = abs(weighted(acc, prod) - production_estimate(data)) < 1e-9
    print("  reweighting the same accuracies by the production mix recovers the honest number = %s (%.3f)" % (reweight_recovers, weighted(acc, prod)))

    ok = eval_inflated and gap_is_large and mix_differs and gap_from_mix and reweight_recovers
    print("-" * 116)
    print("SELF-TEST %s  eval_inflated=%s  gap_is_large=%s  mix_differs=%s  gap_from_mix=%s  reweight_recovers=%s"
          % ("PASS" if ok else "FAIL", eval_inflated, gap_is_large, mix_differs, gap_from_mix, reweight_recovers))
    return ok


def main():
    p = argparse.ArgumentParser(description="Weighting an eval by its own category counts biases the score when the eval mix differs from production; reweight to the production distribution.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--attribute", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("categories=%s  eval_mix=%s  production=%s  file=%s  (the setup is a fixture)"
          % (list(data["accuracy"]), data["eval_counts"], data["production"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.attribute:
        attribute_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
