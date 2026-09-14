"""Check the guardrail metrics, not just the primary -- an intervention that improves the metric you optimized can degrade one you also care about, and deciding on the primary alone ships that harm.

A team optimizes a primary metric and the A/B test shows it improved. That reads as a clean win, and the temptation is to ship on it. But an intervention almost never moves only its target: making a feature stickier can slow the page, surface more errors, or cannibalize revenue. Optimizing one number rarely leaves the others untouched, and some of those others matter too.

Guardrail metrics are the secondary metrics you watch precisely to catch these side effects. Each has a direction -- higher-is-better or lower-is-better -- and a regression limit, the worst move in the bad direction you are willing to tolerate. A guardrail is breached when it moves in its bad direction by more than its limit: latency up past its budget, error rate up past its threshold, revenue down past what the engagement gain is worth.

Deciding on the primary alone is blind to all of this. The primary improved, so the primary-only rule ships -- and it ships whatever the guardrails did, because it never looked at them. A real regression in latency or errors or revenue rides along with the celebrated engagement win, discovered later in production as a mysterious degradation no one connects to the 'successful' launch.

The guardrail-aware rule is a conjunction, not a single check: ship only if the primary improved AND no guardrail is breached. The primary tells you the feature did the thing you wanted; the guardrails tell you it did not do things you did not want. A launch has to clear both to be a real win, because a metric bought at the cost of latency, errors, or revenue is often not worth buying.

The rule: gate the ship decision on the guardrail metrics as well as the primary -- ship only if the primary improved and no guardrail moved past its regression limit -- because an intervention that wins on its target metric can breach a guardrail (latency, errors, revenue), and a primary-only decision ships that harm unseen.

On this fixture engagement (primary) improved by 5, but latency rose 200ms past its 50ms budget and error rate rose 0.5 past its 0.1 limit -- two breached guardrails. The primary-only rule ships; the guardrail-aware rule holds. This computes both.

  --metrics   each metric's delta, direction, limit, and whether it is breached
  --decide    the ship decision under a primary-only rule vs a guardrail-aware rule
  --check     the primary improves while guardrails are breached; primary-only ships the harm, guardrail-aware holds

metrics is the fixture; the breach status and the two decisions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "guardrail.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def improved(m):
    """Did the metric move in its good direction at all?"""
    return m["delta"] > 0 if m["higher_is_better"] else m["delta"] < 0


def breached(m):
    """A guardrail is breached if it moved in its bad direction by more than its limit."""
    bad_move = -m["delta"] if m["higher_is_better"] else m["delta"]
    return bad_move > m["limit"]


def primary(metrics):
    return next(m for m in metrics if m["primary"])


def guardrails(metrics):
    return [m for m in metrics if not m["primary"]]


# ----------------------------------------------------------------- printing

def metrics_view(data):
    metrics = data["metrics"]
    print("METRICS — each metric's move and whether it breaches its guardrail")
    print("-" * 68)
    print("  metric       delta    better    limit   role       breached?")
    for m in metrics:
        role = "primary" if m["primary"] else "guardrail"
        b = "-" if m["primary"] else breached(m)
        print("  %-11s  %-7.1f  %-8s  %-6.1f  %-9s  %s"
              % (m["name"], m["delta"], "higher" if m["higher_is_better"] else "lower", m["limit"], role, b))
    print("-" * 68)
    print("  a guardrail breaches when it moves the wrong way past its limit")


def decide_view(data):
    metrics = data["metrics"]
    p = primary(metrics)
    gr = guardrails(metrics)
    primary_only = "SHIP" if improved(p) else "HOLD"
    guardrail_aware = "SHIP" if (improved(p) and not any(breached(g) for g in gr)) else "HOLD"
    print("DECIDE — ship decision under each rule")
    print("-" * 54)
    print("  primary improved: %s (%s %+.1f)" % (improved(p), p["name"], p["delta"]))
    print("  guardrails breached: %s" % [g["name"] for g in gr if breached(g)])
    print("  primary-only rule    -> %s" % primary_only)
    print("  guardrail-aware rule -> %s" % guardrail_aware)
    print("-" * 54)
    print("  the primary-only rule ships a launch that regressed latency and errors")


def check(data):
    print("SELF-TEST — the primary improves while guardrails are breached; primary-only ships the harm, guardrail-aware holds")
    print("-" * 120)
    metrics = data["metrics"]
    p = primary(metrics)
    gr = guardrails(metrics)

    primary_improved = improved(p)
    print("  the primary metric improved = %s (%s %+.1f)" % (primary_improved, p["name"], p["delta"]))

    some_guardrail_breached = any(breached(g) for g in gr)
    print("  at least one guardrail is breached = %s (%s)" % (some_guardrail_breached, [g["name"] for g in gr if breached(g)]))

    primary_only_ships = primary_improved
    print("  primary-only rule ships = %s" % primary_only_ships)

    guardrail_aware_holds = not (primary_improved and not some_guardrail_breached)
    print("  guardrail-aware rule holds = %s" % guardrail_aware_holds)

    decisions_differ = primary_only_ships and guardrail_aware_holds
    print("  the two rules disagree (one ships, one holds) = %s" % decisions_differ)

    ok = (primary_improved and some_guardrail_breached and primary_only_ships
          and guardrail_aware_holds and decisions_differ)
    print("-" * 120)
    print("SELF-TEST %s  primary_improved=%s  some_guardrail_breached=%s  primary_only_ships=%s  guardrail_aware_holds=%s  decisions_differ=%s"
          % ("PASS" if ok else "FAIL", primary_improved, some_guardrail_breached,
             primary_only_ships, guardrail_aware_holds, decisions_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Guardrail metrics: gate the ship decision on the guardrail metrics as well as the primary -- ship only if the primary improved and no guardrail moved past its regression limit -- because an intervention that wins on its target metric can breach a guardrail (latency, errors, revenue), and a primary-only decision ships that harm unseen.")
    p.add_argument("--metrics", action="store_true")
    p.add_argument("--decide", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    n = len(data["metrics"])
    print("metrics=%d  guardrails=%d  file=%s  (the metrics are a fixture)"
          % (n, sum(not m["primary"] for m in data["metrics"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.metrics:
        metrics_view(data)
    elif args.decide:
        decide_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
