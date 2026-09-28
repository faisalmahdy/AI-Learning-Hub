"""Route easy steps to a cheap model and hard steps to a strong one -- or you overpay for quality you didn't need everywhere.

Most steps an agent takes are easy: look up a value, format a string, call a tool with obvious arguments. A few are
hard: a subtle plan, an ambiguous judgment, a tricky bit of code. Run everything on the strong, expensive model and it
handles both -- but you pay the strong price on every trivial step too, and most steps are trivial, so the bill is
dominated by quality you did not need. Run everything on the cheap model and the bill collapses, but the cheap model
fails the hard steps, and a handful of botched hard steps can wreck a whole run. Neither one-model policy is right: one
overpays for easy work, the other underperforms on hard work.

Routing pays for quality only where it matters. Classify each step's difficulty and send the easy ones to the cheap
model -- which is nearly as good as the strong model on easy steps anyway -- and escalate only the hard ones to the
strong model. Because easy steps dominate the workload, the cheap model does most of the calls at a tenth of the price,
while the strong model is reserved for the minority of steps that actually need it. The result captures almost all of
the strong model's accuracy at a fraction of its cost: you buy the expensive model's judgment on the 20% of steps that
are hard and the cheap model's speed on the 80% that are easy. This is the model-cascade pattern -- a cheap model first,
an expensive one only on escalation.

On this fixture 80 of 100 steps are easy and 20 hard; the cheap model costs 1 and the strong 10. Always-strong scores
0.964 accuracy for a cost of 1000. Always-cheap costs 100 but scores only 0.84, because it fails most hard steps.
Routing costs 280 -- cheap on the 80 easy, strong on the 20 hard -- and scores 0.94, keeping the strong model's accuracy
within about two points at 28% of its cost. This computes all three.

  --route     each policy's total cost and overall accuracy: always-cheap, always-strong, routed
  --savings   routing's cost saving vs always-strong and its accuracy gain vs always-cheap
  --check     always-cheap fails hard steps; always-strong overpays; routing nears strong's accuracy at a fraction of the cost

The step mix, model accuracies, and costs are the fixture; every total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "route.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def total_steps(steps):
    return steps["easy"] + steps["hard"]


def single_model(steps, model):
    """Cost and accuracy of running every step on one model."""
    n = total_steps(steps)
    cost = n * model["cost"]
    correct = steps["easy"] * model["acc_easy"] + steps["hard"] * model["acc_hard"]
    return cost, correct / n


def routed(steps, cheap, strong):
    """Cost and accuracy of sending easy steps to `cheap` and hard steps to `strong`."""
    n = total_steps(steps)
    cost = steps["easy"] * cheap["cost"] + steps["hard"] * strong["cost"]
    correct = steps["easy"] * cheap["acc_easy"] + steps["hard"] * strong["acc_hard"]
    return cost, correct / n


# ----------------------------------------------------------------- printing

def route_view(data):
    steps, cheap, strong = data["steps"], data["cheap"], data["strong"]
    cc, ca = single_model(steps, cheap)
    sc, sa = single_model(steps, strong)
    rc, ra = routed(steps, cheap, strong)
    print("ROUTE — cost and accuracy of each model policy (%d easy, %d hard)" % (steps["easy"], steps["hard"]))
    print("-" * 58)
    print("  policy          cost    accuracy")
    print("  always-cheap    %-6d  %.3f" % (cc, ca))
    print("  always-strong   %-6d  %.3f" % (sc, sa))
    print("  routed          %-6d  %.3f" % (rc, ra))
    print("-" * 58)
    print("  routed runs cheap on the easy majority and strong on the hard minority.")


def savings_view(data):
    steps, cheap, strong = data["steps"], data["cheap"], data["strong"]
    cc, ca = single_model(steps, cheap)
    sc, sa = single_model(steps, strong)
    rc, ra = routed(steps, cheap, strong)
    print("SAVINGS — routing vs the two one-model policies")
    print("-" * 60)
    print("  vs always-strong:  cost %d -> %d  (%.0f%% cheaper), accuracy %.3f -> %.3f" % (sc, rc, 100 * (sc - rc) / sc, sa, ra))
    print("  vs always-cheap:   cost %d -> %d  (%dx),           accuracy %.3f -> %.3f" % (cc, rc, rc // cc, ca, ra))
    print("-" * 60)
    print("  routing buys most of strong's accuracy for a fraction of its cost, by spending only where it helps.")


def check(data):
    print("SELF-TEST — always-cheap fails hard steps; always-strong overpays; routing nears strong's accuracy at a fraction of the cost")
    print("-" * 122)
    steps, cheap, strong = data["steps"], data["cheap"], data["strong"]
    cc, ca = single_model(steps, cheap)
    sc, sa = single_model(steps, strong)
    rc, ra = routed(steps, cheap, strong)

    cheap_underperforms = ca < ra - 0.05
    print("  always-cheap is far less accurate (it fails hard steps) = %s (%.3f vs routed %.3f)" % (cheap_underperforms, ca, ra))

    strong_overpays = sc > rc
    print("  always-strong costs more than routing = %s (%d > %d)" % (strong_overpays, sc, rc))

    routed_near_strong = sa - ra < 0.05
    print("  routing stays within a few points of strong's accuracy = %s (%.3f vs %.3f)" % (routed_near_strong, ra, sa))

    routed_much_cheaper = rc < sc / 2
    print("  routing costs far less than always-strong = %s (%d < %d)" % (routed_much_cheaper, rc, sc))

    routed_beats_cheap_accuracy = ra > ca
    print("  routing is more accurate than always-cheap = %s (%.3f > %.3f)" % (routed_beats_cheap_accuracy, ra, ca))

    ok = cheap_underperforms and strong_overpays and routed_near_strong and routed_much_cheaper and routed_beats_cheap_accuracy
    print("-" * 122)
    print("SELF-TEST %s  cheap_underperforms=%s  strong_overpays=%s  routed_near_strong=%s  routed_much_cheaper=%s  routed_beats_cheap_accuracy=%s"
          % ("PASS" if ok else "FAIL", cheap_underperforms, strong_overpays, routed_near_strong, routed_much_cheaper, routed_beats_cheap_accuracy))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cost-aware model routing (a cascade): send easy steps to a cheap model and escalate only hard steps to a strong one, capturing near-strong accuracy at a fraction of the cost.")
    p.add_argument("--route", action="store_true")
    p.add_argument("--savings", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%s  cheap_cost=%d  strong_cost=%d  file=%s  (the workload and models are a fixture)"
          % (data["steps"], data["cheap"]["cost"], data["strong"]["cost"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.route:
        route_view(data)
    elif args.savings:
        savings_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
