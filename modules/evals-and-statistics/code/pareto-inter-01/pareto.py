"""Choose a model from the quality-cost Pareto frontier, not by ranking quality alone -- quality-only ranking crowns the costliest model for a marginal gain and can even place a dominated model (worse and pricier than another) above an efficient one.

Picking a model is a two-objective decision: you want high quality and low cost, and they trade off. Ranking by quality alone throws away the cost axis, and that single simplification causes two distinct errors.

The first is overpaying at the top. Quality-only ranking always names the highest-quality model, no matter what that last increment of quality costs. Quality tends to have diminishing returns, so the top model is frequently a small quality gain over the next one at a large multiple of the cost -- the worst value on the board, chosen precisely because the ranking cannot see cost.

The second is subtler and strictly irrational. A model is dominated when some other model is at least as good on quality and at least as cheap, strictly better on at least one axis: there is never a reason to choose it, because the dominating model wins outright. But a dominated model can still have higher quality than some cheaper, efficient model, and then quality-only ranking lists the dominated model above the efficient one -- ranking a choice nobody should make over one they should.

The Pareto frontier is the set of non-dominated models: those for which no other model beats them on both quality and cost. Every rational choice lies on the frontier; where on it depends on how much quality per unit of cost you are willing to buy. Selection is picking a point on the frontier, not reading the top off a quality sort.

On this fixture five models trade quality against cost. Model D is dominated by C (higher quality, lower cost), so it should never be chosen, yet it outranks the efficient model A on quality; and the top-quality model E costs four times C for two more quality points. This computes the frontier, the dominated set, and the quality-only ranking that gets both wrong.

  --models    each model's quality, cost, and value (quality per unit cost), with its dominated flag
  --frontier  the Pareto frontier vs the quality-only ranking, and the marginal cost of the top model
  --check     a dominated model exists and outranks an efficient one under quality-only ranking; the frontier excludes it and the top model is poor value

models is the fixture; the value ratios, the dominated set, the frontier, the quality ranking, and the top model's marginal cost are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pareto.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dominates(a, b):
    """a dominates b if a is at least as good on both axes and strictly better on one (higher quality, lower cost)."""
    at_least_as_good = a["quality"] >= b["quality"] and a["cost"] <= b["cost"]
    strictly_better = a["quality"] > b["quality"] or a["cost"] < b["cost"]
    return at_least_as_good and strictly_better


def dominated_set(models):
    """Models for which some other model dominates them -- never rational to choose."""
    return [n for n, m in models.items() if any(dominates(o, m) for k, o in models.items() if k != n)]


def frontier(models):
    """The Pareto frontier: the non-dominated models, ordered by cost."""
    dom = set(dominated_set(models))
    return sorted((n for n in models if n not in dom), key=lambda n: models[n]["cost"])


def quality_ranking(models):
    """Models ranked by quality alone, best first -- the cost-blind ordering."""
    return sorted(models, key=lambda n: models[n]["quality"], reverse=True)


def value(m):
    """Quality per unit cost."""
    return m["quality"] / m["cost"]


# ----------------------------------------------------------------- printing

def models_view(data):
    models = data["models"]
    dom = set(dominated_set(models))
    print("MODELS — quality (higher better), cost (lower better), value (quality/cost)")
    print("-" * 56)
    print("  model   quality   cost   value    dominated?")
    for n in sorted(models, key=lambda n: models[n]["cost"]):
        m = models[n]
        print("  %-6s  %-8d  %-5d  %-7.2f  %s" % (n, m["quality"], m["cost"], value(m), n in dom))
    print("-" * 56)
    print("  a dominated model is beaten on both axes -- it should never be chosen")


def frontier_view(data):
    models = data["models"]
    f = frontier(models)
    qr = quality_ranking(models)
    print("FRONTIER — the Pareto frontier vs the quality-only ranking")
    print("-" * 56)
    print("  Pareto frontier (by cost): %s" % f)
    print("  quality-only ranking     : %s" % qr)
    print("  dominated, excluded      : %s" % dominated_set(models))
    top = qr[0]
    # marginal cost of the top model over the best-quality frontier model below it
    below = [n for n in f if models[n]["quality"] < models[top]["quality"]]
    ref = max(below, key=lambda n: models[n]["quality"])
    dq = models[top]["quality"] - models[ref]["quality"]
    dc = models[top]["cost"] - models[ref]["cost"]
    print("  top-quality model %s costs %+d for %+d quality over %s -> %.1f cost per quality point"
          % (top, dc, dq, ref, dc / dq))
    print("-" * 56)
    print("  quality-only picks the costliest and lists the dominated model above an efficient one")


def check(data):
    print("SELF-TEST — a dominated model exists and outranks an efficient one under quality-only ranking; the frontier excludes it and the top model is poor value")
    print("-" * 112)
    models = data["models"]
    dom = dominated_set(models)
    f = frontier(models)
    qr = quality_ranking(models)

    dominated_exists = len(dom) > 0
    print("  at least one model is dominated = %s (%s)" % (dominated_exists, dom))

    frontier_excludes_dominated = all(n not in f for n in dom)
    print("  the Pareto frontier excludes every dominated model = %s (frontier %s)" % (frontier_excludes_dominated, f))

    top = qr[0]
    quality_only_picks_costliest = top == max(models, key=lambda n: models[n]["cost"])
    print("  quality-only ranking crowns the costliest model = %s (%s)" % (quality_only_picks_costliest, top))

    # a dominated model ranks above a frontier model in the quality-only order
    quality_rank_prefers_dominated = any(
        qr.index(d) < qr.index(fr) for d in dom for fr in f if models[d]["quality"] > models[fr]["quality"]
    )
    print("  quality-only ranking lists a dominated model above an efficient one = %s" % quality_rank_prefers_dominated)

    below = [n for n in f if models[n]["quality"] < models[top]["quality"]]
    ref = max(below, key=lambda n: models[n]["quality"])
    marginal = (models[top]["cost"] - models[ref]["cost"]) / (models[top]["quality"] - models[ref]["quality"])
    top_avg = models[top]["cost"] / models[top]["quality"]  # top's average cost per quality point
    top_is_poor_value = marginal > top_avg
    print("  the top model's marginal cost per quality point exceeds its own average = %s (%.1f > %.2f)" % (top_is_poor_value, marginal, top_avg))

    ok = (dominated_exists and frontier_excludes_dominated and quality_only_picks_costliest
          and quality_rank_prefers_dominated and top_is_poor_value)
    print("-" * 112)
    print("SELF-TEST %s  dominated_exists=%s  frontier_excludes_dominated=%s  quality_only_picks_costliest=%s  quality_rank_prefers_dominated=%s  top_is_poor_value=%s"
          % ("PASS" if ok else "FAIL", dominated_exists, frontier_excludes_dominated, quality_only_picks_costliest,
             quality_rank_prefers_dominated, top_is_poor_value))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pareto frontier: choose a model from the quality-cost Pareto frontier, not by ranking quality alone, because quality-only ranking crowns the costliest model for a marginal gain and can place a dominated model (worse and pricier than another) above an efficient one.")
    p.add_argument("--models", action="store_true")
    p.add_argument("--frontier", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("models=%s  file=%s  (these are a fixture)" % (list(data["models"].keys()), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.models:
        models_view(data)
    elif args.frontier:
        frontier_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
