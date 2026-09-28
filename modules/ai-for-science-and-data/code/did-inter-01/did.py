"""Estimate a treatment effect you could not randomize with difference-in-differences, not a before/after or a treated-versus-control comparison -- the before/after change also contains the time trend that would have moved the group anyway, and the treated-versus-control gap also contains the difference the groups already had, while subtracting the control group's change from the treated group's change cancels both biases and leaves the effect.

You want the effect of a treatment applied to one group -- a policy that hit one state, a feature shipped to one region -- but you could not randomize, so you have four numbers: the treated group before and after, and a control group before and after. The two obvious estimates are each wrong in a different way.

The before/after estimate on the treated group is after_treated minus before_treated. But things change over time for everyone -- the economy moved, the season turned -- so part of that change is a trend the group would have followed with no treatment at all. The estimate is the effect plus the trend.

The cross-sectional estimate is after_treated minus after_control, comparing the two groups once the treatment is in place. But the groups were not identical to begin with; they had a gap before the treatment ever happened. The estimate is the effect plus that pre-existing gap.

Difference-in-differences uses all four numbers: (after_treated - before_treated) minus (after_control - before_control). The control group's before-to-after change is the common time trend, uncontaminated by the treatment it never received; subtracting it from the treated group's change removes the trend and leaves the effect. It is valid under the parallel-trends assumption -- that absent the treatment the treated group would have changed by the same amount as the control -- which the data cannot verify and you must argue for.

On this fixture the treated group goes 100 to 130 and the control 80 to 95. The control's change of 15 is the time trend, so the treated group's counterfactual after value is 100 + 15 = 115, and its actual 130 makes the true effect 15. The before/after estimate is 30 (overstated by the trend), the cross-sectional estimate is 35 (overstated by the pre-existing gap of 20), and difference-in-differences is 15. This computes all of them.

  --naive   the before/after and cross-sectional estimates, each biased in its own way
  --did     the difference-in-differences estimate and the counterfactual it implies
  --check   both naive estimates miss the true effect while difference-in-differences recovers it, and it equals the treated change minus the control's time trend

the four before/after measurements are the fixture; every estimate, the counterfactual, and the true effect are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "did.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def treated_change(d):
    """The treated group's before-to-after change: the treatment effect PLUS the time trend."""
    return d["after_treated"] - d["before_treated"]


def control_change(d):
    """The control group's before-to-after change: the common time trend, with no treatment."""
    return d["after_control"] - d["before_control"]


def cross_section(d):
    """After-period gap, treated minus control: the effect PLUS the groups' pre-existing gap."""
    return d["after_treated"] - d["after_control"]


def pre_gap(d):
    """The gap between the groups before the treatment -- present in the cross-sectional estimate."""
    return d["before_treated"] - d["before_control"]


def did(d):
    """Difference-in-differences: treated change minus control change -- both biases cancel."""
    return treated_change(d) - control_change(d)


def true_effect(d):
    """The effect against the counterfactual: actual after_treated minus (before_treated + time trend)."""
    counterfactual = d["before_treated"] + control_change(d)
    return d["after_treated"] - counterfactual


# ----------------------------------------------------------------- printing

def naive_view(d):
    print("NAIVE — the two obvious estimates, each biased")
    print("-" * 64)
    print("  before/after (treated): %d - %d = %d" % (d["after_treated"], d["before_treated"], treated_change(d)))
    print("      = effect + time trend (trend is the control's change, %d)" % control_change(d))
    print("  cross-section (after):  %d - %d = %d" % (d["after_treated"], d["after_control"], cross_section(d)))
    print("      = effect + pre-existing gap (%d)" % pre_gap(d))
    print("-" * 64)
    print("  one estimate absorbs the time trend, the other the pre-existing gap")


def did_view(d):
    counterfactual = d["before_treated"] + control_change(d)
    print("DID — difference-in-differences")
    print("-" * 64)
    print("  treated change  = %d - %d = %d" % (d["after_treated"], d["before_treated"], treated_change(d)))
    print("  control change  = %d - %d = %d   (the time trend)" % (d["after_control"], d["before_control"], control_change(d)))
    print("  DiD = %d - %d = %d" % (treated_change(d), control_change(d), did(d)))
    print("  counterfactual after_treated (no treatment) = %d + %d = %d" % (d["before_treated"], control_change(d), counterfactual))
    print("  effect = %d - %d = %d" % (d["after_treated"], counterfactual, true_effect(d)))
    print("-" * 64)
    print("  subtracting the control's change removes the trend, leaving the effect (under parallel trends)")


def check(d):
    print("SELF-TEST — both naive estimates miss the true effect while difference-in-differences recovers it, and it equals the treated change minus the control's time trend")
    print("-" * 112)
    truth = true_effect(d)

    beforeafter_overstates = treated_change(d) != truth
    print("  before/after estimate misses the true effect = %s (%d vs %d, off by the trend %d)"
          % (beforeafter_overstates, treated_change(d), truth, control_change(d)))

    crosssection_overstates = cross_section(d) != truth
    print("  cross-sectional estimate misses the true effect = %s (%d vs %d, off by the pre-gap %d)"
          % (crosssection_overstates, cross_section(d), truth, pre_gap(d)))

    did_recovers = did(d) == truth
    print("  difference-in-differences recovers the true effect = %s (%d == %d)" % (did_recovers, did(d), truth))

    did_removes_trend = did(d) == treated_change(d) - control_change(d)
    print("  DiD equals the treated change minus the control's time trend = %s (%d - %d)" % (did_removes_trend, treated_change(d), control_change(d)))

    ok = (beforeafter_overstates and crosssection_overstates and did_recovers and did_removes_trend)
    print("-" * 112)
    print("SELF-TEST %s  beforeafter_overstates=%s  crosssection_overstates=%s  did_recovers=%s  did_removes_trend=%s"
          % ("PASS" if ok else "FAIL", beforeafter_overstates, crosssection_overstates, did_recovers, did_removes_trend))
    return ok


def main():
    p = argparse.ArgumentParser(description="Difference-in-differences: estimate a non-randomized treatment effect by subtracting the control group's before-to-after change from the treated group's change, because the treated group's before/after change also contains the common time trend and the treated-versus-control cross-section also contains the groups' pre-existing gap -- DiD cancels both, recovering the effect under the parallel-trends assumption that, absent treatment, the treated group would have changed by the same amount as the control.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--did", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("treated %d->%d  control %d->%d  file=%s"
          % (d["before_treated"], d["after_treated"], d["before_control"], d["after_control"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.naive:
        naive_view(d)
    elif args.did:
        did_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
