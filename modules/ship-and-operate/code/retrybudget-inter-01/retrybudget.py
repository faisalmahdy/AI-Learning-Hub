"""Cap retries with a budget -- a bound on retry volume as a fraction of requests -- not one retry per failure, or a dependency's bad moment becomes a retry storm that piles load on it exactly when it is weakest.

Retrying a failed request is usually the right move: most failures are transient blips, and a single retry recovers them for almost nothing. The trap is that a retry is extra load, and the assumption that failures are rare -- which makes retrying cheap -- is exactly the assumption that breaks during an incident. When a dependency degrades and most requests start failing, retrying every failure roughly doubles the load on the struggling dependency at the worst possible moment, driving it further down and keeping it down: a retry storm, one of the classic ways a recoverable blip becomes a sustained, self-inflicted outage (a metastable failure).

Two familiar fixes help but do not bound the volume. Jitter spreads retries out in time so they do not arrive in a synchronized spike. Retrying at only one layer of the stack stops retries from multiplying geometrically as each layer retries the layer below. Both are necessary and neither caps the total: with per-failure retries, jittered and single-layer, an outage where 80% of requests fail still offers nearly 1.8x the load, because every one of those failures still gets its retry.

A retry budget bounds the volume directly. Treat retries as a scarce resource -- allow them only up to a small fraction of the request rate, refilled like a token bucket -- and once the budget is spent, fail fast instead of retrying. The elegance is that the budget is invisible in normal operation: transient failures are a tiny fraction of traffic, far under the budget, so every one still gets retried and recovery is unaffected. It only engages during a broad outage, where the failure rate blows past the budget and the budget caps the amplification, protecting the dependency from the retry storm while still absorbing ordinary blips.

The rule: bound retries with a budget -- a cap on retry volume as a fraction of requests -- rather than retrying every failure, because per-failure retries amplify load precisely during a widespread outage; the budget is transparent when failures are rare and caps the retry storm when they are not.

On this fixture the retry budget is 10% of the 100 requests. In the healthy period (5 failures) both policies retry all 5 -- the budget is transparent. In the outage (80 failures) per-failure retries push the load to 1.8x, while the budget caps retries at 10 for 1.1x. This computes both.

  --scenarios   per period: failures, retries and total load with vs without the budget
  --amplify     the load amplification factor each policy produces, healthy vs outage
  --check       per-failure retries amplify load in the outage; the budget caps it while staying transparent when failures are rare

requests, budget_fraction, and scenarios are the fixture; the retry counts, total load, and amplification are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "retrybudget.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def budget(requests, fraction):
    return math.ceil(fraction * requests)


def retries_no_budget(failures):
    """Retry every failure."""
    return failures


def retries_with_budget(failures, requests, fraction):
    """Retry up to the budget, then fail fast."""
    return min(failures, budget(requests, fraction))


def amplification(requests, retries):
    return (requests + retries) / requests


# ----------------------------------------------------------------- printing

def scenarios_view(data):
    requests, frac = data["requests"], data["budget_fraction"]
    print("SCENARIOS — retries and total offered load (requests=%d, budget=%d)" % (requests, budget(requests, frac)))
    print("-" * 72)
    print("  period    failures   no-budget retries/load   budget retries/load")
    for s in data["scenarios"]:
        f = s["failures"]
        nb = retries_no_budget(f)
        bg = retries_with_budget(f, requests, frac)
        print("  %-8s  %-9d  %-3d / %-18d %-3d / %d"
              % (s["name"], f, nb, requests + nb, bg, requests + bg))
    print("-" * 72)
    print("  the budget matches per-failure retries when failures are few, and caps them when many")


def amplify_view(data):
    requests, frac = data["requests"], data["budget_fraction"]
    print("AMPLIFY — offered-load multiplier each policy produces")
    print("-" * 60)
    for s in data["scenarios"]:
        f = s["failures"]
        nb = amplification(requests, retries_no_budget(f))
        bg = amplification(requests, retries_with_budget(f, requests, frac))
        print("  %-8s  no-budget %.2fx   budget %.2fx" % (s["name"], nb, bg))
    print("-" * 60)
    print("  the budget bounds the multiplier at 1 + budget_fraction (%.2fx) no matter the failure rate" % (1 + frac))


def check(data):
    print("SELF-TEST — per-failure retries amplify load in the outage; the budget caps it while staying transparent when failures are rare")
    print("-" * 128)
    requests, frac = data["requests"], data["budget_fraction"]
    healthy = next(s for s in data["scenarios"] if s["name"] == "healthy")
    outage = next(s for s in data["scenarios"] if s["name"] == "outage")
    b = budget(requests, frac)

    hf, of = healthy["failures"], outage["failures"]

    budget_transparent_when_healthy = retries_with_budget(hf, requests, frac) == retries_no_budget(hf)
    print("  when failures are rare the budget retries every one (transparent) = %s (%d == %d)"
          % (budget_transparent_when_healthy, retries_with_budget(hf, requests, frac), retries_no_budget(hf)))

    no_budget_amplifies_outage = amplification(requests, retries_no_budget(of)) >= 1.5
    print("  per-failure retries amplify load in the outage = %s (%.2fx)"
          % (no_budget_amplifies_outage, amplification(requests, retries_no_budget(of))))

    budget_caps_outage_retries = retries_with_budget(of, requests, frac) < retries_no_budget(of)
    print("  the budget caps retries in the outage = %s (%d < %d)"
          % (budget_caps_outage_retries, retries_with_budget(of, requests, frac), retries_no_budget(of)))

    budget_bounds_amplification = amplification(requests, retries_with_budget(of, requests, frac)) <= 1 + frac + 1e-9
    print("  the budget bounds outage amplification at 1+fraction = %s (%.2fx <= %.2fx)"
          % (budget_bounds_amplification, amplification(requests, retries_with_budget(of, requests, frac)), 1 + frac))

    failures_exceed_budget_in_outage = of > b
    print("  the outage's failures exceed the budget (so the cap engages) = %s (%d > %d)" % (failures_exceed_budget_in_outage, of, b))

    ok = (budget_transparent_when_healthy and no_budget_amplifies_outage and budget_caps_outage_retries
          and budget_bounds_amplification and failures_exceed_budget_in_outage)
    print("-" * 128)
    print("SELF-TEST %s  budget_transparent_when_healthy=%s  no_budget_amplifies_outage=%s  budget_caps_outage_retries=%s  budget_bounds_amplification=%s  failures_exceed_budget_in_outage=%s"
          % ("PASS" if ok else "FAIL", budget_transparent_when_healthy, no_budget_amplifies_outage, budget_caps_outage_retries, budget_bounds_amplification, failures_exceed_budget_in_outage))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retry budget: bound retries with a budget -- a cap on retry volume as a fraction of requests -- rather than retrying every failure, because per-failure retries amplify load precisely during a widespread outage; the budget is transparent when failures are rare and caps the retry storm when they are not.")
    p.add_argument("--scenarios", action="store_true")
    p.add_argument("--amplify", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  budget_fraction=%.2f  budget=%d  file=%s  (the traffic is a fixture)"
          % (data["requests"], data["budget_fraction"], budget(data["requests"], data["budget_fraction"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scenarios:
        scenarios_view(data)
    elif args.amplify:
        amplify_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
