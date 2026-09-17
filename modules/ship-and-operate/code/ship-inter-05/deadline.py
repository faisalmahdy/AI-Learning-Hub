#!/usr/bin/env python3
"""Propagate the REMAINING deadline to each hop -- or a slow chain overruns its SLA.

A request promises the caller a response within a total deadline. To keep it, every
downstream call the request makes must run under the time that is LEFT, not the full
timeout: if 70ms of a 100ms budget remain, the next hop gets 70ms, and the hop after
that gets whatever is left after it. Propagate the remaining budget and the whole chain
is bounded by the deadline -- a hop that would exceed the remaining time fails fast
instead of running and blowing past it.

The bug is to hand each hop the ORIGINAL timeout. Every hop then thinks it has the full
100ms, none of them knows the global deadline, and a chain whose durations sum past the
deadline runs to completion anyway -- the individual calls each "succeeded" while the
overall request missed its SLA, the caller having already given up, the work wasted.
The bug is invisible on a fast chain that fits inside one hop's timeout, and bites only
when the chain is slow. This measures both.

  --trace CHAIN  step through a chain under correct budget propagation
  --compare      total elapsed under budget propagation vs full-timeout, both chains
  --check        correct is always bounded by the deadline; full-timeout overruns the slow chain

Deterministic: durations are the fixture, not a clock. Stdlib only. Times in ms.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chain.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two policies

def run_with_budget(deadline, durations):
    """Propagate the remaining budget. A hop that exceeds it fails fast at the budget.

    Returns (elapsed, ok): ok is False if a hop ran out of budget (deadline exceeded).
    """
    elapsed = 0
    for d in durations:
        remaining = deadline - elapsed
        if d > remaining:
            elapsed += remaining  # the hop is cut off at the remaining budget
            return elapsed, False  # fail fast: deadline would be exceeded
        elapsed += d
    return elapsed, True


def run_full_timeout(deadline, durations):
    """The bug: each hop gets the full timeout, so the chain runs regardless of the deadline."""
    elapsed = 0
    for d in durations:
        if d > deadline:      # each hop only checks against the ORIGINAL timeout
            elapsed += deadline
            return elapsed, False
        elapsed += d          # otherwise it runs fully, ignorant of the global budget
    return elapsed, True


# ----------------------------------------------------------------- printing

def trace_view(data, chain):
    deadline, durations = data["deadline_ms"], data["chains"][chain]
    print("TRACE — correct budget propagation on '%s' (deadline=%dms)" % (chain, deadline))
    print("-" * 66)
    elapsed = 0
    for i, d in enumerate(durations):
        remaining = deadline - elapsed
        if d > remaining:
            print("  hop %d: needs %dms, only %dms left -> FAIL FAST (deadline exceeded)" % (i, d, remaining))
            elapsed += remaining
            break
        elapsed += d
        print("  hop %d: took %dms, %dms budget remaining" % (i, d, deadline - elapsed))
    print("-" * 66)
    print("  total elapsed = %dms (<= deadline %dms)" % (elapsed, deadline))


def compare_view(data):
    deadline = data["deadline_ms"]
    print("COMPARE — total elapsed: budget propagation vs full-timeout (deadline=%dms)" % deadline)
    print("-" * 66)
    print("  chain   sum    budget-prop (elapsed, ok)   full-timeout (elapsed, ok)")
    for name, durs in data["chains"].items():
        be, bok = run_with_budget(deadline, durs)
        fe, fok = run_full_timeout(deadline, durs)
        print("  %-6s  %-5d  %3dms %-5s              %3dms %-5s%s"
              % (name, sum(durs), be, bok, fe, fok, "  <-- OVERRUN" if fe > deadline else ""))
    print("-" * 66)
    print("  full-timeout runs the slow chain to %dms, past the %dms deadline."
          % (run_full_timeout(deadline, data["chains"]["slow"])[0], deadline))


def check(data):
    print("SELF-TEST — budget propagation is always bounded; full-timeout overruns the slow chain")
    print("-" * 66)
    deadline = data["deadline_ms"]
    slow, fast = data["chains"]["slow"], data["chains"]["fast"]

    be_slow, bok_slow = run_with_budget(deadline, slow)
    bounded = be_slow <= deadline
    print("  budget propagation stays within the deadline on the slow chain = %s (%dms <= %dms)"
          % (bounded, be_slow, deadline))

    fails_fast = not bok_slow
    print("  ...and it fails fast rather than overrunning = %s (deadline exceeded reported)" % fails_fast)

    fe_slow, _ = run_full_timeout(deadline, slow)
    full_overruns = fe_slow > deadline
    print("  full-timeout overruns the deadline on the slow chain = %s (%dms > %dms)"
          % (full_overruns, fe_slow, deadline))

    # On the fast chain, both fit -> the bug is invisible there.
    be_fast, _ = run_with_budget(deadline, fast)
    fe_fast, _ = run_full_timeout(deadline, fast)
    both_ok_fast = be_fast <= deadline and fe_fast <= deadline
    print("  on the fast chain both stay within deadline (bug hides) = %s (%dms, %dms)"
          % (both_ok_fast, be_fast, fe_fast))

    ok = bounded and fails_fast and full_overruns and both_ok_fast
    print("-" * 66)
    print("SELF-TEST %s  bounded=%s  fails_fast=%s  full_overruns=%s  both_ok_fast=%s"
          % ("PASS" if ok else "FAIL", bounded, fails_fast, full_overruns, both_ok_fast))
    return ok


def main():
    p = argparse.ArgumentParser(description="Deadline budget propagation across a call chain.")
    p.add_argument("--trace", metavar="CHAIN")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("deadline=%dms  chains=%s  file=%s  (durations are a fixture)"
          % (data["deadline_ms"], list(data["chains"]), DATA.name))
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
