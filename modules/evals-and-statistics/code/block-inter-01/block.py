"""Block the randomization on a strong covariate -- simple randomization does not guarantee balance in a small sample, so a strong predictor can land unevenly in the two arms by luck and confound the estimate.

An A/B estimate is the treated mean minus the control mean, and it equals the true effect only when the two arms are balanced on everything that affects the outcome. Randomization is what usually buys that balance -- but 'usually' is doing a lot of work. Randomization makes the arms balanced in expectation and near-certain to balance in a large sample; in a small sample, any single random split can, by luck, put more of a strong covariate in one arm.

When it does, that arm's outcome is higher for a reason that has nothing to do with the treatment. A pre-existing covariate that predicts the outcome -- baseline severity, prior score, account size -- is a confounder the moment it is unevenly split, and the treated-minus-control difference is then the true effect plus the outcome gap that the covariate imbalance alone would produce. Nothing about the randomization was done wrong; it just drew an unlucky split, which small samples do at a rate you cannot ignore.

Blocking removes the luck by design. Stratify the units into blocks by the covariate -- here high-baseline and low-baseline -- and randomize to treatment and control within each block. Now each arm is guaranteed the same covariate composition, because the balance is enforced stratum by stratum rather than left to a single draw over the whole sample. The confounder cannot be unevenly split, so it cannot bias the estimate.

On this fixture four units have baseline 100 and four have baseline 0, and the true treatment effect is 5. A simple split that happened to give treatment three high-baseline units and control three low-baseline ones estimates the effect at 55 -- the true 5 plus a covariate gap of 50. The blocked split puts two high and two low in each arm and estimates the true 5. This computes both.

  --simple   the unlucky simple split: the covariate is imbalanced and the estimate is inflated
  --blocked  the blocked split: the covariate is balanced in each arm and the estimate is correct
  --check    the simple split imbalances the covariate and biases the estimate by exactly that imbalance, while the blocked split balances it and recovers the true effect

units, the true effect, and the two assignments are the fixture; the covariate balance and the estimated effect under each design are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "block.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def arms(data, treatment_ids):
    """Split the units into the treated arm (ids in treatment_ids) and the control arm (the rest)."""
    treated = [u for u in data["units"] if u["id"] in treatment_ids]
    control = [u for u in data["units"] if u["id"] not in treatment_ids]
    return treated, control


def mean_baseline(units):
    """The average covariate value of an arm -- the thing that must match between arms for a clean estimate."""
    return sum(u["baseline"] for u in units) / len(units)


def estimate(data, treatment_ids):
    """Treated-mean minus control-mean of the outcome (baseline + true_effect when treated)."""
    treated, control = arms(data, treatment_ids)
    eff = data["true_effect"]
    treated_mean = sum(u["baseline"] + eff for u in treated) / len(treated)
    control_mean = sum(u["baseline"] for u in control) / len(control)
    return treated_mean - control_mean


# ----------------------------------------------------------------- printing

def _report(data, treatment_ids):
    treated, control = arms(data, treatment_ids)
    bt, bc = mean_baseline(treated), mean_baseline(control)
    print("  treatment ids: %s" % treatment_ids)
    print("  mean baseline: treated %.1f vs control %.1f   (imbalance %.1f)" % (bt, bc, bt - bc))
    print("  estimated effect = %.1f   (true %.1f)" % (estimate(data, treatment_ids), data["true_effect"]))


def simple_view(data):
    print("SIMPLE — one random split that happened to imbalance the covariate")
    print("-" * 60)
    _report(data, data["simple_treatment"])
    print("-" * 60)
    print("  the treated arm is higher-baseline, so its outcome is up for a non-treatment reason")


def blocked_view(data):
    print("BLOCKED — randomize within high- and low-baseline strata")
    print("-" * 60)
    _report(data, data["blocked_treatment"])
    print("-" * 60)
    print("  each arm has the same baseline mix, so the difference is the treatment alone")


def check(data):
    print("SELF-TEST — the simple split imbalances the covariate and biases the estimate by exactly that imbalance, while the blocked split balances it and recovers the true effect")
    print("-" * 112)
    eff = data["true_effect"]

    s_treated, s_control = arms(data, data["simple_treatment"])
    s_gap = mean_baseline(s_treated) - mean_baseline(s_control)
    simple_imbalances = abs(s_gap) > 1e-9
    print("  the simple split imbalances the covariate = %s (treated %.1f vs control %.1f)" % (simple_imbalances, mean_baseline(s_treated), mean_baseline(s_control)))

    s_est = estimate(data, data["simple_treatment"])
    simple_biased = abs(s_est - eff) > 1e-9
    print("  the simple estimate is biased = %s (%.1f vs true %.1f)" % (simple_biased, s_est, eff))

    bias_equals_imbalance = abs((s_est - eff) - s_gap) < 1e-9
    print("  the bias equals the covariate imbalance = %s (%.1f == %.1f)" % (bias_equals_imbalance, s_est - eff, s_gap))

    b_treated, b_control = arms(data, data["blocked_treatment"])
    blocked_balances = abs(mean_baseline(b_treated) - mean_baseline(b_control)) < 1e-9
    print("  the blocked split balances the covariate = %s (treated %.1f vs control %.1f)" % (blocked_balances, mean_baseline(b_treated), mean_baseline(b_control)))

    b_est = estimate(data, data["blocked_treatment"])
    blocked_correct = abs(b_est - eff) < 1e-9
    print("  the blocked estimate recovers the true effect = %s (%.1f)" % (blocked_correct, b_est))

    ok = (simple_imbalances and simple_biased and bias_equals_imbalance
          and blocked_balances and blocked_correct)
    print("-" * 112)
    print("SELF-TEST %s  simple_imbalances=%s  simple_biased=%s  bias_equals_imbalance=%s  blocked_balances=%s  blocked_correct=%s"
          % ("PASS" if ok else "FAIL", simple_imbalances, simple_biased, bias_equals_imbalance,
             blocked_balances, blocked_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Blocked randomization: stratify the assignment on a strong covariate and randomize within strata, because simple randomization does not guarantee balance in a small sample -- a covariate can land unevenly in the two arms by luck and confound the estimate, while blocking forces each arm to the same covariate composition.")
    p.add_argument("--simple", action="store_true")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    highs = [u["id"] for u in data["units"] if u["baseline"] > 0]
    print("units=%d (high-baseline %s)  true_effect=%.1f  file=%s  (fixture)"
          % (len(data["units"]), highs, data["true_effect"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.simple:
        simple_view(data)
    elif args.blocked:
        blocked_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
