"""A crossover experiment measures each unit under both treatments in sequence, which cancels the huge between-unit baseline differences that would swamp a between-subjects comparison -- but without a washout period the first treatment's effect carries over into the period where the second is measured, biasing the estimate, and a washout removes that bias by letting the first effect decay before the second is measured.

Comparing two treatments across separate groups of units wastes power, because units differ from each other far more than the treatments differ, and that between-unit variance drowns the signal. A crossover design fixes this by making each unit its own control: give it treatment A in period 1 and treatment B in period 2, and compare period 2 to period 1 within the unit, so the unit's baseline subtracts out. Units with wildly different baselines then all contribute the same clean within-unit difference.

The danger the sequence introduces is carryover. If treatment A leaves a residual -- a learned habit, a lingering physiological effect, a warmed cache -- then when B is measured in period 2, some of what is measured is A's leftover, not B. The within-unit difference is now the true effect of B over A plus the carryover of A into B's period, and it is biased. The baseline still cancels, so the estimate is precise -- every unit agrees -- and precisely wrong.

A washout period is the fix: leave enough time (or reset enough state) between the two treatments that the first one's residual has decayed to zero before the second is measured. Then period 2 measures B alone, the carryover term vanishes, and the within-unit difference is the true effect.

On this fixture the true effect of B over A is 10 - 4 = 6, and carryover is half the previous treatment's effect. Without a washout every unit's within-unit estimate is 8 -- the true 6 plus the carryover of A into B's period, 0.5 * 4 = 2 -- identical across units of very different baselines. With a washout every unit's estimate is 6. This computes both.

  --nowashout  the crossover with carryover: baseline cancels (every unit agrees) but the estimate is biased high by the carryover
  --washout    the crossover with a washout: carryover has decayed, so each unit's estimate is the true effect
  --check      the design cancels baseline under both, but no-washout is biased by exactly the carryover while washout recovers the true effect

the unit baselines, the two treatment effects, and the carryover fraction are the fixture; each unit's period measurements and within-unit estimates, and the true effect, are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "washout.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def true_effect(d):
    """The effect of B over A on a fresh unit with no prior treatment: effect_B minus effect_A."""
    return d["effect_b"] - d["effect_a"]


def period1(baseline, d):
    """Period 1 measures treatment A on a fresh unit: baseline plus A's effect, no carryover."""
    return baseline + d["effect_a"]


def period2(baseline, d, carryover_fraction):
    """Period 2 measures treatment B, plus a fraction of A's effect carried over from period 1."""
    return baseline + d["effect_b"] + carryover_fraction * d["effect_a"]


def within_estimate(baseline, d, carryover_fraction):
    """The crossover estimate of B minus A for one unit: its period-2 minus its period-1 measurement."""
    return period2(baseline, d, carryover_fraction) - period1(baseline, d)


# ----------------------------------------------------------------- printing

def _view(d, carryover_fraction, label, note):
    print("%s — within-unit estimate of B minus A per unit (true effect = %d)" % (label, true_effect(d)))
    print("-" * 64)
    for b in d["unit_baselines"]:
        p1 = period1(b, d)
        p2 = period2(b, d, carryover_fraction)
        print("  baseline %3d:  period1(A)=%d  period2(B)=%g  ->  estimate %g" % (b, p1, p2, p2 - p1))
    print("-" * 64)
    print("  %s" % note)


def nowashout_view(d):
    _view(d, d["carryover_fraction"], "NO-WASHOUT",
          "every unit agrees (baseline cancels), but each estimate is high by the carryover")


def washout_view(d):
    _view(d, 0.0, "WASHOUT",
          "A's residual has decayed, so each unit's estimate is the true effect")


def check(d):
    print("SELF-TEST — the design cancels baseline under both, but no-washout is biased by exactly the carryover while washout recovers the true effect")
    print("-" * 112)
    truth = true_effect(d)
    cf = d["carryover_fraction"]

    nw = [within_estimate(b, d, cf) for b in d["unit_baselines"]]
    wo = [within_estimate(b, d, 0.0) for b in d["unit_baselines"]]

    baseline_cancels = len(set(nw)) == 1 and len(set(wo)) == 1
    print("  every unit gives the same within-unit estimate (baseline cancels) = %s (no-washout %s, washout %s)" % (baseline_cancels, nw, wo))

    nowashout_biased = nw[0] != truth
    print("  no-washout estimate is biased (not the true effect) = %s (%g vs %d)" % (nowashout_biased, nw[0], truth))

    washout_recovers = wo[0] == truth
    print("  washout estimate recovers the true effect = %s (%g == %d)" % (washout_recovers, wo[0], truth))

    bias_is_carryover = abs((nw[0] - truth) - cf * d["effect_a"]) < 1e-9
    print("  the bias equals the carryover (fraction times A's effect) = %s (%g == %g)" % (bias_is_carryover, nw[0] - truth, cf * d["effect_a"]))

    ok = (baseline_cancels and nowashout_biased and washout_recovers and bias_is_carryover)
    print("-" * 112)
    print("SELF-TEST %s  baseline_cancels=%s  nowashout_biased=%s  washout_recovers=%s  bias_is_carryover=%s"
          % ("PASS" if ok else "FAIL", baseline_cancels, nowashout_biased, washout_recovers, bias_is_carryover))
    return ok


def main():
    p = argparse.ArgumentParser(description="Crossover washout: a within-unit crossover design cancels the between-unit baseline variance that would swamp a between-subjects comparison, but without a washout period the first treatment's residual carries into the period where the second is measured and biases the estimate by that carryover; a washout lets the first effect decay so the second is measured alone and the within-unit difference is the true effect.")
    p.add_argument("--nowashout", action="store_true")
    p.add_argument("--washout", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("effect_a=%d  effect_b=%d  carryover=%g  units=%d  file=%s"
          % (d["effect_a"], d["effect_b"], d["carryover_fraction"], len(d["unit_baselines"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.nowashout:
        nowashout_view(d)
    elif args.washout:
        washout_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
