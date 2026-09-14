"""Estimate the effect by intention-to-treat -- compare the arms as randomized -- not by comparing adherers to non-adherers, because adherence is self-selected and predicts the outcome on its own, so an adherence-based comparison confounds the drug with the health of the adhering type.

A randomized trial assigns patients to treatment or control at random, which balances every hidden trait across the arms and is what makes the comparison causal. But who actually takes the assigned pill is not random: healthier, more organized, more health-conscious patients adhere, and those traits improve outcomes on their own. Adherence is a downstream, self-selected variable, and conditioning on it re-introduces exactly the confounding that randomization removed.

The proof lives in the placebo arm. Patients given a sugar pill who adhered to it did better than those who did not -- with a pill that does nothing. That gap is pure selection: the adhering type is healthier, and their adherence to an inert pill reveals it. So any analysis that compares people who took the drug to people who did not is measuring the drug's effect plus that health gap, and reports a number larger than the drug earns.

Intention-to-treat sidesteps this by analyzing patients by the arm they were randomized into, regardless of what they actually took. Randomization made the arms' health-type mixes identical, so their difference is unconfounded. The price is that ITT includes the non-adherers who got no drug, so it estimates real-world effectiveness (effect of being prescribed the drug) rather than the effect on perfect-takers -- which is usually the more honest number for a decision, and never inflated by the healthy-adherer selection.

The rule: estimate a randomized treatment's effect by intention-to-treat, comparing the arms as assigned, not by comparing adherers to non-adherers -- because adherence is self-selected and predicts the outcome (adherers to a placebo do better), so a per-protocol or as-treated comparison confounds the treatment with the health of the adhering type and inflates the effect.

On this fixture the treatment arm's adherers beat its non-adherers by 30, which a naive analysis credits to the drug; but the control arm's adherers beat its non-adherers by 20 on a placebo, so 20 of that 30 is pure adherence selection and only 10 is drug. Intention-to-treat compares the full arms and reports 5. This computes all three.

  --gaps    the within-arm adherer-minus-non-adherer gap in each arm, including the drug-free placebo gap
  --effect  the naive per-protocol gap vs the intention-to-treat arm comparison
  --check   adherers beat non-adherers even on placebo; a per-protocol gap inflates the effect, ITT is by assignment

the cells (arm x adherence outcomes and sizes) are the fixture; the gaps and the two effect estimates are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "itt.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cell(cells, arm, adherent):
    return next(c for c in cells if c["arm"] == arm and c["adherent"] == adherent)


def arm_mean(cells, arm):
    """Mean outcome over a whole arm, weighting the cells by size -- the intention-to-treat view."""
    rows = [c for c in cells if c["arm"] == arm]
    total = sum(c["outcome"] * c["n"] for c in rows)
    n = sum(c["n"] for c in rows)
    return total / n


def adherer_gap(cells, arm):
    """Within one arm: how much better adherers did than non-adherers."""
    return cell(cells, arm, True)["outcome"] - cell(cells, arm, False)["outcome"]


# ----------------------------------------------------------------- printing

def gaps_view(data):
    cells = data["cells"]
    print("GAPS — within each arm, adherers minus non-adherers")
    print("-" * 56)
    print("  arm         adherent   non-adherent   gap")
    for arm in ("treatment", "control"):
        print("  %-10s  %-9d  %-13d  %d"
              % (arm, cell(cells, arm, True)["outcome"], cell(cells, arm, False)["outcome"], adherer_gap(cells, arm)))
    print("-" * 56)
    print("  the control (placebo) gap is drug-free -- pure adherence selection")


def effect_view(data):
    cells = data["cells"]
    per_protocol = adherer_gap(cells, "treatment")
    placebo_gap = adherer_gap(cells, "control")
    itt = arm_mean(cells, "treatment") - arm_mean(cells, "control")
    print("EFFECT — three estimates of the treatment effect")
    print("-" * 58)
    print("  naive per-protocol (treatment adherer gap) = %d" % per_protocol)
    print("    of which adherence selection (placebo gap) = %d" % placebo_gap)
    print("    of which drug (per-protocol - placebo gap) = %d" % (per_protocol - placebo_gap))
    print("  intention-to-treat (arm %.0f vs arm %.0f)      = %d"
          % (arm_mean(cells, "treatment"), arm_mean(cells, "control"), itt))
    print("-" * 58)
    print("  the per-protocol gap is inflated by the placebo adherence gap; ITT is by assignment")


def check(data):
    print("SELF-TEST — adherers beat non-adherers even on placebo; a per-protocol gap inflates the effect, ITT is by assignment")
    print("-" * 120)
    cells = data["cells"]
    per_protocol = adherer_gap(cells, "treatment")
    placebo_gap = adherer_gap(cells, "control")
    itt = arm_mean(cells, "treatment") - arm_mean(cells, "control")

    adherence_confounded = placebo_gap > 0
    print("  adherers beat non-adherers on placebo (adherence predicts outcome) = %s (%d)" % (adherence_confounded, placebo_gap))

    per_protocol_inflated = per_protocol > (per_protocol - placebo_gap)
    print("  the naive per-protocol gap exceeds the drug-only effect = %s (%d > %d)"
          % (per_protocol_inflated, per_protocol, per_protocol - placebo_gap))

    itt_smaller_than_per_protocol = itt < per_protocol
    print("  intention-to-treat is smaller than the per-protocol gap = %s (%d < %d)" % (itt_smaller_than_per_protocol, itt, per_protocol))

    itt_positive = itt > 0
    print("  intention-to-treat still finds a real effect = %s (%d)" % (itt_positive, itt))

    bias_is_placebo_gap = (per_protocol - (per_protocol - placebo_gap)) == placebo_gap
    print("  the per-protocol inflation equals the placebo adherence gap = %s (%d)" % (bias_is_placebo_gap, placebo_gap))

    ok = (adherence_confounded and per_protocol_inflated and itt_smaller_than_per_protocol
          and itt_positive and bias_is_placebo_gap)
    print("-" * 120)
    print("SELF-TEST %s  adherence_confounded=%s  per_protocol_inflated=%s  itt_smaller_than_per_protocol=%s  itt_positive=%s  bias_is_placebo_gap=%s"
          % ("PASS" if ok else "FAIL", adherence_confounded, per_protocol_inflated,
             itt_smaller_than_per_protocol, itt_positive, bias_is_placebo_gap))
    return ok


def main():
    p = argparse.ArgumentParser(description="Intention-to-treat: estimate a randomized treatment's effect by intention-to-treat, comparing the arms as assigned, not by comparing adherers to non-adherers -- because adherence is self-selected and predicts the outcome (adherers to a placebo do better), so a per-protocol or as-treated comparison confounds the treatment with the health of the adhering type and inflates the effect.")
    p.add_argument("--gaps", action="store_true")
    p.add_argument("--effect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cells=%d  arms=2  file=%s  (the arm x adherence outcomes are a fixture)"
          % (len(data["cells"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gaps:
        gaps_view(data)
    elif args.effect:
        effect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
