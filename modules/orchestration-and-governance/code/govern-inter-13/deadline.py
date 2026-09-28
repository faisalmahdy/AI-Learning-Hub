"""Propagate the deadline down the call chain, or a hop keeps working after the client gave up.

A request arrives with a total time budget -- the client will wait 1000 ms and no longer. That
request fans out into a chain of downstream calls: A calls B calls C calls D. The naive way to bound
each call is a fixed per-hop timeout: give every hop the same generous limit, say 600 ms, so no single
hop hangs forever. That bounds each hop but not the chain. Four hops at up to 600 ms each can run 2400
ms in total -- long after the client stopped waiting at 1000 ms. Every millisecond a hop spends
computing past the client's deadline is pure waste: the answer, when it finally comes, is thrown away
because the client already timed out and moved on. Worse, hops that could never have finished in time
still start and run to completion, burning capacity on work no one will read.

Deadline propagation fixes it. Instead of a fixed per-hop timeout, pass the absolute deadline down the
chain. At each hop, compute the time remaining until the deadline; if none is left, do not start the
hop at all; otherwise cap the hop's timeout at the remaining budget. Now the whole chain is bounded by
the one budget the client actually cares about, no hop runs past the deadline, and hops that cannot
finish in the remaining time are skipped instead of started -- the work stops the moment it can no
longer matter.

On this fixture the budget is 1000 ms and four hops each take 400 ms. With fixed 600 ms per-hop
timeouts the chain runs to 1600 ms and does 600 ms of work after the deadline, and the last hop starts
even though it had no chance of finishing. Propagating the deadline caps the chain at the 1000 ms
budget, does zero work past it, and never starts the doomed hop. This computes both.

  --run        walk the chain both ways, showing when each hop runs and whether it beats the deadline
  --waste      the work done after the deadline and whether each doomed hop was started
  --check      fixed timeouts overrun the budget and waste work; propagation caps the chain and wastes none

The budget and hop durations are the fixture; every timing is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chain.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_fixed(hops, per_hop, budget):
    """Each hop gets a fixed timeout; a hop starts as long as the previous one returned."""
    trace, elapsed = [], 0
    for h in hops:
        ran = min(h["ms"], per_hop)              # capped only by the fixed per-hop timeout
        start, elapsed = elapsed, elapsed + ran
        trace.append({"hop": h["hop"], "start": start, "end": elapsed, "started": True})
    return trace


def run_propagated(hops, budget):
    """Each hop gets the remaining budget; a hop with no budget left is not started."""
    trace, elapsed = [], 0
    for h in hops:
        remaining = budget - elapsed
        if remaining <= 0:
            trace.append({"hop": h["hop"], "start": elapsed, "end": elapsed, "started": False})
            continue
        ran = min(h["ms"], remaining)            # capped by whatever budget is left
        start, elapsed = elapsed, elapsed + ran
        trace.append({"hop": h["hop"], "start": start, "end": elapsed, "started": True})
    return trace


def wasted_after(trace, budget):
    """Total time a hop spent computing past the deadline -- work whose result is discarded."""
    return sum(max(0, t["end"] - max(t["start"], budget)) for t in trace if t["started"])


def total_time(trace):
    return max((t["end"] for t in trace), default=0)


# ----------------------------------------------------------------- printing

def run_view(data):
    hops, per_hop, budget = data["hops"], data["per_hop_ms"], data["budget_ms"]
    for name, trace in (("FIXED per-hop timeout %d ms" % per_hop, run_fixed(hops, per_hop, budget)),
                        ("PROPAGATED deadline", run_propagated(hops, budget))):
        print("%s   (budget %d ms)" % (name, budget))
        print("-" * 58)
        for t in trace:
            if not t["started"]:
                print("  %s  SKIPPED (no budget left)" % t["hop"])
            else:
                tag = "  <-- past deadline" if t["end"] > budget else ""
                print("  %s  %4d..%4d ms%s" % (t["hop"], t["start"], t["end"], tag))
        print("  total %d ms" % total_time(trace))
        print("")


def waste_view(data):
    hops, per_hop, budget = data["hops"], data["per_hop_ms"], data["budget_ms"]
    fx, pr = run_fixed(hops, per_hop, budget), run_propagated(hops, budget)
    print("WASTE — work done after the %d ms deadline" % budget)
    print("-" * 58)
    print("  fixed:       total %4d ms   wasted %4d ms" % (total_time(fx), wasted_after(fx, budget)))
    print("  propagated:  total %4d ms   wasted %4d ms" % (total_time(pr), wasted_after(pr, budget)))
    print("-" * 58)
    skipped = [t["hop"] for t in pr if not t["started"]]
    print("  propagation skipped the doomed hop(s): %s" % (skipped or "none"))


def check(data):
    print("SELF-TEST — fixed timeouts overrun the budget and waste work; propagation caps and wastes none")
    print("-" * 92)
    hops, per_hop, budget = data["hops"], data["per_hop_ms"], data["budget_ms"]
    fx, pr = run_fixed(hops, per_hop, budget), run_propagated(hops, budget)

    fixed_overruns = total_time(fx) > budget
    print("  fixed timeouts run the chain past the budget = %s (%d ms > %d ms)"
          % (fixed_overruns, total_time(fx), budget))

    fixed_wastes = wasted_after(fx, budget) > 0
    print("  fixed timeouts do work after the deadline = %s (%d ms wasted)"
          % (fixed_wastes, wasted_after(fx, budget)))

    propagated_caps = total_time(pr) <= budget
    print("  propagation caps the chain at the budget = %s (%d ms <= %d ms)"
          % (propagated_caps, total_time(pr), budget))

    propagated_no_waste = wasted_after(pr, budget) == 0
    print("  propagation does no work past the deadline = %s (%d ms wasted)"
          % (propagated_no_waste, wasted_after(pr, budget)))

    fixed_started_all = all(t["started"] for t in fx)
    propagation_skips = any(not t["started"] for t in pr)
    aborts_doomed = fixed_started_all and propagation_skips
    print("  fixed starts every hop but propagation skips the doomed one = %s" % aborts_doomed)

    ok = fixed_overruns and fixed_wastes and propagated_caps and propagated_no_waste and aborts_doomed
    print("-" * 92)
    print("SELF-TEST %s  fixed_overruns=%s  fixed_wastes=%s  propagated_caps=%s  propagated_no_waste=%s  aborts_doomed=%s"
          % ("PASS" if ok else "FAIL", fixed_overruns, fixed_wastes, propagated_caps, propagated_no_waste, aborts_doomed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Propagate the deadline down the call chain instead of a fixed per-hop timeout.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--waste", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("budget=%d ms  hops=%d  per_hop=%d ms  file=%s  (the budget and durations are a fixture)"
          % (data["budget_ms"], len(data["hops"]), data["per_hop_ms"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.waste:
        waste_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
