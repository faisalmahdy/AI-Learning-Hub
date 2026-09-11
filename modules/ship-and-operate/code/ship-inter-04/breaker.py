#!/usr/bin/env python3
"""A circuit breaker trips on CONSECUTIVE failures -- reset on success, or it false-trips.

When a downstream dependency fails, retrying it immediately makes things worse: you
pile load onto a service that is already struggling. A circuit breaker watches the
call outcomes and, after enough failures, OPENS -- it stops attempting calls and fails
fast, giving the dependency room to recover. The question is what 'enough failures'
means. The right answer is consecutive failures: a run of them signals the dependency
is actually down. A single blip among successes does not.

The bug is to count total failures instead, never resetting the counter when a call
succeeds. On a real outage both behave the same. But on a basically-healthy service
with scattered transient blips, the total-failure counter creeps up over time and
eventually trips the breaker on a dependency that is fine -- a false open that takes
down a working service because it had a few unrelated hiccups. The fix is one line:
reset the failure count to zero on every success. This measures both.

  --trace SCEN   step through a scenario under the correct breaker; watch it open or not
  --compare      correct vs buggy breaker on the flaky (healthy) service: who false-trips
  --check        correct opens on outage, stays closed on flaky; buggy false-trips on flaky

Stdlib only. Deterministic. 1 = call ok, 0 = call failed.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "calls.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the breakers

def run_breaker(outcomes, threshold, reset_on_success=True):
    """Trip when the failure counter reaches threshold. Returns (opened, trip_index, states).

    reset_on_success=True counts CONSECUTIVE failures (correct). False counts TOTAL
    failures and never resets (the bug). Once open, it stays open (recovery is elsewhere).
    """
    failures = 0
    opened = False
    trip_index = None
    states = []
    for i, ok in enumerate(outcomes):
        if opened:
            states.append("OPEN")  # fail fast: not even attempted
            continue
        if ok:
            if reset_on_success:
                failures = 0  # THE RESET: a success clears the consecutive count
        else:
            failures += 1
        if failures >= threshold:
            opened = True
            trip_index = i
        states.append("OPEN" if opened else "closed")
    return opened, trip_index, states


def max_consecutive_failures(outcomes):
    run = best = 0
    for ok in outcomes:
        run = 0 if ok else run + 1
        best = max(best, run)
    return best


# ----------------------------------------------------------------- printing

def trace_view(data, scenario):
    outcomes = data["scenarios"][scenario]
    thr = data["threshold"]
    opened, trip, states = run_breaker(outcomes, thr, reset_on_success=True)
    print("TRACE — correct breaker on '%s' (threshold=%d consecutive failures)" % (scenario, thr))
    print("-" * 66)
    print("  step:    " + " ".join("%2d" % i for i in range(len(outcomes))))
    print("  outcome: " + " ".join(" %d" % o for o in outcomes))
    print("  state:   " + " ".join("%2s" % ("Op" if s == "OPEN" else "cl") for s in states))
    print("-" * 66)
    if opened:
        print("  OPENED at step %d after %d consecutive failures." % (trip, thr))
    else:
        print("  stayed CLOSED: longest failure run was %d (< %d)." % (max_consecutive_failures(outcomes), thr))


def compare_view(data):
    outcomes = data["scenarios"]["flaky"]
    thr = data["threshold"]
    good_open, good_i, _ = run_breaker(outcomes, thr, reset_on_success=True)
    bug_open, bug_i, _ = run_breaker(outcomes, thr, reset_on_success=False)
    print("COMPARE — correct vs buggy breaker on the FLAKY (healthy) service")
    print("-" * 66)
    print("  outcomes: %s   (%d scattered failures, longest run %d)"
          % (outcomes, outcomes.count(0), max_consecutive_failures(outcomes)))
    print("  correct (reset on success): opened=%s" % good_open)
    print("  buggy (counts all failures): opened=%s  at step %s" % (bug_open, bug_i))
    print("-" * 66)
    print("  the buggy breaker trips a healthy service because blips accumulated forever.")


def check(data):
    print("SELF-TEST — correct opens on outage, holds on flaky; buggy false-trips on flaky")
    print("-" * 66)
    thr = data["threshold"]
    outage = data["scenarios"]["outage"]
    flaky = data["scenarios"]["flaky"]

    correct_outage, _, _ = run_breaker(outage, thr, reset_on_success=True)
    opens_on_outage = correct_outage
    print("  correct breaker OPENS on the real outage = %s" % opens_on_outage)

    correct_flaky, _, _ = run_breaker(flaky, thr, reset_on_success=True)
    holds_on_flaky = not correct_flaky
    print("  correct breaker STAYS CLOSED on the flaky service = %s (longest run %d < %d)"
          % (holds_on_flaky, max_consecutive_failures(flaky), thr))

    buggy_flaky, bug_i, _ = run_breaker(flaky, thr, reset_on_success=False)
    buggy_false_trips = buggy_flaky
    print("  buggy breaker FALSE-TRIPS on the flaky service = %s (opened at step %s)"
          % (buggy_false_trips, bug_i))

    # Both agree on a genuine outage -> the bug is specific to scattered failures.
    buggy_outage, _, _ = run_breaker(outage, thr, reset_on_success=False)
    agree_on_outage = buggy_outage and correct_outage
    print("  both breakers open on the outage (bug is flaky-only) = %s" % agree_on_outage)

    ok = opens_on_outage and holds_on_flaky and buggy_false_trips and agree_on_outage
    print("-" * 66)
    print("SELF-TEST %s  opens_on_outage=%s  holds_on_flaky=%s  buggy_false_trips=%s  agree_on_outage=%s"
          % ("PASS" if ok else "FAIL", opens_on_outage, holds_on_flaky, buggy_false_trips, agree_on_outage))
    return ok


def main():
    p = argparse.ArgumentParser(description="Circuit breaker: consecutive vs total failure counting.")
    p.add_argument("--trace", metavar="SCEN")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("threshold=%d  scenarios=%s  file=%s  (call outcomes are a fixture)"
          % (data["threshold"], list(data["scenarios"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trace:
        trace_view(data, args.trace)
    elif args.compare:
        compare_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
