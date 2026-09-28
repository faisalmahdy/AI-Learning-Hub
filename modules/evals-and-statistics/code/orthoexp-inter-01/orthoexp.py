"""Randomize concurrent experiments independently, or two A/B tests on the same users confound each other -- X's treated arm carries more of Y's treatment than X's control arm, so Y's effect leaks into X's measured effect.

An A/B test measures its effect as the treated mean minus the control mean, and that difference equals the experiment's own effect only if the two arms are balanced on everything else. Randomization is what buys that balance -- for a single experiment it makes the arms interchangeable except for the treatment.

Two experiments running on the same users at the same time break the guarantee unless they are randomized independently. If assignment to X and assignment to Y are correlated -- users put in X's treatment tend to also be in Y's treatment -- then X's treated arm contains a higher fraction of Y-treated users than X's control arm does. Y is now imbalanced across X's arms, so Y is a confounder of X, and the treated-minus-control difference for X measures X's effect plus a slice of Y's. The slice is exactly the imbalance in Y-treatment fraction between X's arms, times Y's true effect. The confounding is symmetric: X leaks into Y's estimate the same way.

The fix is orthogonal assignment: randomize X and Y by independent coins. Then within each of X's arms, half the users are Y-treated and half are Y-control -- the same fraction on both sides -- so Y's effect is equal in X's treated and control arms and cancels in their difference. Each experiment recovers its own effect, and any number of experiments can share the same traffic as long as their randomizations are independent.

On this fixture X's true effect is 2 and Y's is 5. Under correlated assignment X measures 5 (its 2 plus 0.6 of Y's 5) and Y measures 6.2; under orthogonal assignment X measures 2 and Y measures 5. This computes both.

  --correlated  the correlated design: X's arms are imbalanced on Y, so both measured effects are inflated
  --orthogonal  the orthogonal design: X's arms are balanced on Y, so each measured effect is its own
  --check       correlated assignment biases both estimates while orthogonal assignment recovers the true effects

base, effect_x, effect_y, and the two designs' cell counts are the fixture; the cell outcomes, the measured effects, and the arm imbalance are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "orthoexp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cell_outcome(data, in_x, in_y):
    """The deterministic outcome in a cell: baseline plus each experiment's effect if that arm is treated."""
    return data["base"] + (data["effect_x"] if in_x else 0.0) + (data["effect_y"] if in_y else 0.0)


def arm_means(data, cells, which):
    """Weighted mean outcome of the treated and control arms of experiment `which` ('x' or 'y')."""
    treat = [("xt_yt", 1, 1), ("xt_yc", 1, 0)] if which == "x" else [("xt_yt", 1, 1), ("xc_yt", 0, 1)]
    control = [("xc_yt", 0, 1), ("xc_yc", 0, 0)] if which == "x" else [("xt_yc", 1, 0), ("xc_yc", 0, 0)]
    def wmean(group):
        num = sum(cells[key] * cell_outcome(data, ix, iy) for key, ix, iy in group)
        den = sum(cells[key] for key, _, _ in group)
        return num / den
    return wmean(treat), wmean(control)


def measured_effect(data, cells, which):
    """What experiment `which` measures on these cells: treated-arm mean minus control-arm mean."""
    treat_mean, control_mean = arm_means(data, cells, which)
    return treat_mean - control_mean


def other_arm_fraction(cells, which):
    """Fraction of the OTHER experiment's treatment in each of `which`'s two arms -- balance iff equal."""
    if which == "x":
        t = cells["xt_yt"] / (cells["xt_yt"] + cells["xt_yc"])   # Y-treat share among X-treated
        c = cells["xc_yt"] / (cells["xc_yt"] + cells["xc_yc"])   # Y-treat share among X-control
    else:
        t = cells["xt_yt"] / (cells["xt_yt"] + cells["xc_yt"])
        c = cells["xt_yc"] / (cells["xt_yc"] + cells["xc_yc"])
    return t, c


# ----------------------------------------------------------------- printing

def _report(data, cells, label):
    tx, cx = other_arm_fraction(cells, "x")
    print("  X arms' Y-treated share: treated %.2f vs control %.2f  (imbalance %.2f)" % (tx, cx, tx - cx))
    print("  measured X effect = %.2f   (true %.1f)" % (measured_effect(data, cells, "x"), data["effect_x"]))
    print("  measured Y effect = %.2f   (true %.1f)" % (measured_effect(data, cells, "y"), data["effect_y"]))


def correlated_view(data):
    print("CORRELATED — X and Y assignment overlap (X-treated are mostly Y-treated)")
    print("-" * 64)
    _report(data, data["correlated_cells"], "correlated")
    print("-" * 64)
    print("  Y is imbalanced across X's arms, so Y's effect leaks into X's (and vice versa)")


def orthogonal_view(data):
    print("ORTHOGONAL — X and Y assigned by independent coins")
    print("-" * 64)
    _report(data, data["orthogonal_cells"], "orthogonal")
    print("-" * 64)
    print("  each arm has the same share of the other's treatment, so the other effect cancels")


def check(data):
    print("SELF-TEST — correlated assignment biases both estimates while orthogonal assignment recovers the true effects")
    print("-" * 112)
    corr, orth = data["correlated_cells"], data["orthogonal_cells"]

    corr_x_biased = abs(measured_effect(data, corr, "x") - data["effect_x"]) > 1e-9
    print("  correlated design biases X's estimate = %s (measured %.2f vs true %.1f)" % (corr_x_biased, measured_effect(data, corr, "x"), data["effect_x"]))

    corr_y_biased = abs(measured_effect(data, corr, "y") - data["effect_y"]) > 1e-9
    print("  correlated design biases Y's estimate = %s (measured %.2f vs true %.1f)" % (corr_y_biased, measured_effect(data, corr, "y"), data["effect_y"]))

    tx, cx = other_arm_fraction(corr, "x")
    corr_arms_imbalanced = abs(tx - cx) > 1e-9
    print("  correlated design's X arms are imbalanced on Y = %s (%.2f vs %.2f)" % (corr_arms_imbalanced, tx, cx))

    orth_x_clean = abs(measured_effect(data, orth, "x") - data["effect_x"]) < 1e-9
    orth_y_clean = abs(measured_effect(data, orth, "y") - data["effect_y"]) < 1e-9
    print("  orthogonal design recovers both true effects = %s (X %.2f, Y %.2f)" % (orth_x_clean and orth_y_clean, measured_effect(data, orth, "x"), measured_effect(data, orth, "y")))

    ox_t, ox_c = other_arm_fraction(orth, "x")
    orth_arms_balanced = abs(ox_t - ox_c) < 1e-9
    print("  orthogonal design's X arms are balanced on Y = %s (%.2f vs %.2f)" % (orth_arms_balanced, ox_t, ox_c))

    ok = (corr_x_biased and corr_y_biased and corr_arms_imbalanced
          and (orth_x_clean and orth_y_clean) and orth_arms_balanced)
    print("-" * 112)
    print("SELF-TEST %s  corr_x_biased=%s  corr_y_biased=%s  corr_arms_imbalanced=%s  orth_effects_clean=%s  orth_arms_balanced=%s"
          % ("PASS" if ok else "FAIL", corr_x_biased, corr_y_biased, corr_arms_imbalanced,
             orth_x_clean and orth_y_clean, orth_arms_balanced))
    return ok


def main():
    p = argparse.ArgumentParser(description="Orthogonal experiments: randomize concurrent A/B tests independently, because correlated assignment makes each experiment's arms imbalanced on the other experiment, so the other's effect leaks into the measured effect -- and orthogonal assignment balances the arms so the other effect cancels.")
    p.add_argument("--correlated", action="store_true")
    p.add_argument("--orthogonal", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("effect_x=%.1f  effect_y=%.1f  base=%.1f  file=%s  (these are a fixture)"
          % (data["effect_x"], data["effect_y"], data["base"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.correlated:
        correlated_view(data)
    elif args.orthogonal:
        orthogonal_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
