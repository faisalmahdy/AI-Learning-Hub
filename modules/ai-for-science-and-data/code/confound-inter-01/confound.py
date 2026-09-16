"""A correlation can be entirely a confounder's shadow -- control for the common cause, and check whether the association survives.

Two things move together in the data, so it is tempting to say one drives the other. But a correlation between X and Y has three possible sources: X causes Y, Y causes X, or a third variable causes BOTH. That third variable is a CONFOUNDER, and when it is the real story, the X-Y correlation is genuine in the data and entirely non-causal -- intervening on X would do nothing to Y, because the link runs through the confounder, not between them. Ice-cream sales and drownings rise together across the year; ice cream does not drown anyone. Hot weather independently drives both -- people buy ice cream, and people swim -- so the two effects of one cause look like a cause and an effect.

The test for confounding is to CONTROL for the suspected common cause: look at the X-Y relationship WITHIN each level of the confounder, holding it fixed, rather than pooled across all levels. If X really affects Y, the association should persist within groups -- among only-hot days, more ice cream would still mean more drownings. If the confounder is the whole story, the association vanishes within groups -- once the weather is held fixed, ice-cream sales vary but drownings do not track them, because the thing that was making both move (temperature) is no longer varying. The pooled correlation was real; it was just the confounder's shadow, and conditioning on the confounder makes the shadow disappear.

This is why 'correlation is not causation' is not merely a caution but a procedure: when you see an association, name the plausible common causes and check whether the association survives controlling for them. An association that survives control for every plausible confounder is a candidate for causation; one that evaporates was confounded. (Confounding is also why randomized experiments are the gold standard: randomizing X breaks any confounder's link to X, so a surviving X-Y association cannot be the confounder's shadow.)

The rule: before reading a correlation as causal, control for plausible common causes by examining the association within each level of the confounder -- because a confounder that drives both variables produces a real but non-causal correlation that vanishes once the confounder is held fixed, while a genuine causal effect persists within groups.

On this fixture ice cream and drownings are strongly associated pooled (above-median-ice-cream days have 4 more drownings on average), but within each temperature group the association is 0 -- holding weather fixed, ice cream does not track drownings. The correlation was temperature's shadow. This computes both.

  --pooled    the pooled association between ice cream and drownings across all days
  --control   the association within each temperature group (holding the confounder fixed)
  --check     the pooled association is large but vanishes within every temperature group -- confounded, not causal

groups are the fixture; the pooled and within-group associations are computed. Stdlib only.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "confound.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def association(points):
    """Mean y on above-median-x points minus mean y on below-median-x points -- how much y tracks x."""
    xs = [p["x"] for p in points]
    med = statistics.median(xs)
    hi = [p["y"] for p in points if p["x"] > med]
    lo = [p["y"] for p in points if p["x"] < med]
    if not hi or not lo:
        return 0.0
    return statistics.mean(hi) - statistics.mean(lo)


def all_points(groups):
    return [p for g in groups.values() for p in g]


def pooled_association(groups):
    return association(all_points(groups))


def within_group_associations(groups):
    return {name: association(pts) for name, pts in groups.items()}


# ----------------------------------------------------------------- printing

def pooled_view(data):
    groups = data["groups"]
    print("POOLED — %s vs %s across all days (ignoring %s)" % (data["x"], data["y"], data["confounder"]))
    print("-" * 60)
    for name, pts in groups.items():
        for p in pts:
            print("  %s=%-3d  %s=%d   (%s)" % (data["x"], p["x"], data["y"], p["y"], name))
    print("-" * 60)
    print("  pooled association (above-median vs below-median %s): +%.0f more %s" % (data["x"], pooled_association(groups), data["y"]))


def control_view(data):
    groups = data["groups"]
    print("CONTROL — association within each %s group (held fixed)" % data["confounder"])
    print("-" * 58)
    for name, assoc in within_group_associations(groups).items():
        pts = groups[name]
        print("  %-6s: %s ranges %d-%d, %s association = %+.0f" % (name, data["x"], min(p["x"] for p in pts), max(p["x"] for p in pts), data["y"], assoc))
    print("-" * 58)
    print("  holding %s fixed, %s does not track %s" % (data["confounder"], data["x"], data["y"]))


def check(data):
    print("SELF-TEST — the pooled association is large but vanishes within every temperature group -- confounded, not causal")
    print("-" * 118)
    groups = data["groups"]
    pooled = pooled_association(groups)
    within = within_group_associations(groups)

    pooled_association_large = abs(pooled) >= 3
    print("  the pooled association is large = %s (+%.0f more %s on high-%s days)" % (pooled_association_large, pooled, data["y"], data["x"]))

    within_all_zero = all(abs(a) < 1e-9 for a in within.values())
    print("  the association is 0 within every %s group = %s (%s)" % (data["confounder"], within_all_zero, {k: round(v, 1) for k, v in within.items()}))

    confounder_drives_x = statistics.mean(p["x"] for p in groups["hot"]) > statistics.mean(p["x"] for p in groups["cold"])
    print("  the confounder drives x (hot days have higher %s) = %s" % (data["x"], confounder_drives_x))

    confounder_drives_y = statistics.mean(p["y"] for p in groups["hot"]) > statistics.mean(p["y"] for p in groups["cold"])
    print("  the confounder drives y (hot days have higher %s) = %s" % (data["y"], confounder_drives_y))

    control_removes_association = abs(max(within.values(), key=abs)) < abs(pooled)
    print("  controlling for the confounder removes the association = %s (pooled +%.0f -> within ~0)" % (control_removes_association, pooled))

    not_causal = within_all_zero
    print("  x does not causally affect y (no within-group effect) = %s" % not_causal)

    ok = (pooled_association_large and within_all_zero and confounder_drives_x and confounder_drives_y
          and control_removes_association and not_causal)
    print("-" * 118)
    print("SELF-TEST %s  pooled_association_large=%s  within_all_zero=%s  confounder_drives_x=%s  confounder_drives_y=%s  control_removes_association=%s  not_causal=%s"
          % ("PASS" if ok else "FAIL", pooled_association_large, within_all_zero, confounder_drives_x, confounder_drives_y, control_removes_association, not_causal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Confounding: before reading a correlation as causal, control for plausible common causes by examining the association within each level of the confounder, because a confounder that drives both variables produces a real but non-causal correlation that vanishes once the confounder is held fixed, while a genuine causal effect persists within groups.")
    p.add_argument("--pooled", action="store_true")
    p.add_argument("--control", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("x=%s  y=%s  confounder=%s  groups=%s  file=%s  (the grouped data is a fixture)"
          % (data["x"], data["y"], data["confounder"], list(data["groups"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pooled:
        pooled_view(data)
    elif args.control:
        control_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
