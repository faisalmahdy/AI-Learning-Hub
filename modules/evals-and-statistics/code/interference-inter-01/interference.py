"""Randomize by cluster when the treatment can affect other units -- individual A/B randomization is biased when treated units contaminate the control group, because the control is no longer an untreated counterfactual.

A/B testing rests on a quiet assumption: each unit's outcome depends only on its own assignment, not on anyone else's (the stable unit treatment value assumption, SUTVA). It is true for most product changes -- your button color does not affect my checkout -- and it is false exactly where units interact. A social feature where a treated user's new activity draws in their control-group friends. A marketplace or any shared, finite resource where treated users consuming more leaves less for control users. A pricing or ranking change that shifts demand from one arm to the other. Whenever a treated unit can change a control unit's outcome, the control group has been touched by the treatment.

When that happens, the control group stops being an untreated counterfactual, and the treated-minus-control difference no longer measures the treatment's effect alone -- it measures the effect plus the contamination. In the resource-competition case here, treated users grab more of a fixed resource and cannibalize the control users sharing it, so under individual randomization the control conversion rate is pushed below its true untreated level while the treated rate is pushed above its true level. Both distortions widen the gap, so the measured lift is inflated -- an effect that is partly real and partly just treated users taking from control.

Cluster randomization fixes it by assigning whole clusters -- markets, regions, social communities -- to a single arm, so a treated unit's spillover lands on other treated units in the same cluster rather than on the control group. The comparison is then between an all-treated cluster and an all-control cluster, each internally consistent, and the between-cluster difference recovers the true effect. The cost is statistical power (you have as many independent units as clusters, not as users), which is why cluster randomization is reserved for exactly the situations where interference makes individual randomization wrong.

The rule: randomize by cluster, not by individual, when the treatment can affect other units, because interference makes the control group no longer an untreated counterfactual -- so individual randomization measures the effect plus the contamination (here, cannibalization inflates the lift), while cluster randomization keeps the spillover within an arm and recovers the true effect.

On this fixture the true effect (from cluster randomization) is a 0.20 lift. Individual randomization in a shared-resource market reports 0.60 -- three times too high -- because the control conversion rate was cannibalized from its true 0.40 down to 0.20. This computes both.

  --designs   the conversion rates and measured lift under individual vs cluster randomization
  --bias      the naive lift vs the true lift, and the cannibalized control rate
  --check     individual randomization overstates the lift because the control group is contaminated; cluster randomization recovers the true effect

mixed and clusters are the fixture; the lifts and the cannibalization are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "interference.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rate(cell):
    return cell["conv"] / cell["n"]


def naive_lift(mixed):
    """Individual randomization: treated rate minus control rate, within the shared-resource market."""
    return rate(mixed["treated"]) - rate(mixed["control"])


def cluster_lift(clusters):
    """Cluster randomization: all-treated market rate minus all-control market rate."""
    return rate(clusters["treated_market"]) - rate(clusters["control_market"])


# ----------------------------------------------------------------- printing

def designs_view(data):
    mixed, clusters = data["mixed"], data["clusters"]
    print("DESIGNS — conversion rate and measured lift under each randomization")
    print("-" * 66)
    print("  individual (shared market): treated %.2f, control %.2f -> lift %+.2f"
          % (rate(mixed["treated"]), rate(mixed["control"]), naive_lift(mixed)))
    print("  cluster (whole markets):    treated %.2f, control %.2f -> lift %+.2f"
          % (rate(clusters["treated_market"]), rate(clusters["control_market"]), cluster_lift(clusters)))
    print("-" * 66)
    print("  same treatment, two designs, very different measured lifts")


def bias_view(data):
    mixed, clusters = data["mixed"], data["clusters"]
    true_untreated = rate(clusters["control_market"])
    observed_control = rate(mixed["control"])
    print("BIAS — the naive lift vs the true lift, and the contaminated control")
    print("-" * 62)
    print("  true lift (cluster)              = %+.2f" % cluster_lift(clusters))
    print("  naive lift (individual)          = %+.2f" % naive_lift(mixed))
    print("  true untreated rate              = %.2f" % true_untreated)
    print("  control rate under individual A/B = %.2f  (cannibalized)" % observed_control)
    print("-" * 62)
    print("  the control group was pushed below its true untreated rate, inflating the lift")


def check(data):
    print("SELF-TEST — individual randomization overstates the lift because the control group is contaminated; cluster randomization recovers the true effect")
    print("-" * 146)
    mixed, clusters = data["mixed"], data["clusters"]
    nl = naive_lift(mixed)
    cl = cluster_lift(clusters)
    true_untreated = rate(clusters["control_market"])
    observed_control = rate(mixed["control"])

    naive_overstates = nl > cl
    print("  individual randomization reports a larger lift than cluster = %s (%+.2f > %+.2f)" % (naive_overstates, nl, cl))

    control_cannibalized = observed_control < true_untreated
    print("  the individual-A/B control rate is below the true untreated rate = %s (%.2f < %.2f)" % (control_cannibalized, observed_control, true_untreated))

    treated_inflated = rate(mixed["treated"]) > rate(clusters["treated_market"])
    print("  the individual-A/B treated rate is above the true treated rate = %s (%.2f > %.2f)"
          % (treated_inflated, rate(mixed["treated"]), rate(clusters["treated_market"])))

    interference_present = observed_control != true_untreated
    print("  the control group was affected by the treatment (interference) = %s" % interference_present)

    naive_biased_high = nl > cl * 1.5
    print("  the naive lift is inflated well beyond the true effect = %s (%.2fx)" % (naive_biased_high, nl / cl))

    ok = (naive_overstates and control_cannibalized and treated_inflated and interference_present and naive_biased_high)
    print("-" * 146)
    print("SELF-TEST %s  naive_overstates=%s  control_cannibalized=%s  treated_inflated=%s  interference_present=%s  naive_biased_high=%s"
          % ("PASS" if ok else "FAIL", naive_overstates, control_cannibalized, treated_inflated, interference_present, naive_biased_high))
    return ok


def main():
    p = argparse.ArgumentParser(description="Interference / SUTVA: randomize by cluster, not by individual, when the treatment can affect other units, because interference makes the control group no longer an untreated counterfactual -- so individual randomization measures the effect plus the contamination (here, cannibalization inflates the lift), while cluster randomization keeps the spillover within an arm and recovers the true effect.")
    p.add_argument("--designs", action="store_true")
    p.add_argument("--bias", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("mixed=%s  clusters=%s  file=%s  (the conversion counts are a fixture)"
          % ({k: (v["conv"], v["n"]) for k, v in data["mixed"].items()},
             {k: (v["conv"], v["n"]) for k, v in data["clusters"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.designs:
        designs_view(data)
    elif args.bias:
        bias_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
