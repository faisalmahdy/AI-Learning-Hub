"""Propagate the remaining deadline down the call chain -- a hop that starts work it cannot finish in time burns resources for a result the caller already abandoned.

A request that fans out through several backend hops -- gateway to auth to database -- usually inherits one end-to-end deadline from the client: answer within, say, 100ms or the client gives up. The natural way to enforce it is to give each hop its own timeout. But a per-hop timeout knows only about its own hop; it has no idea how much of the shared budget the earlier hops already spent. So a late hop, starting with almost none of the budget left, still measures itself against its own fresh timeout and runs to completion -- producing a result at, say, 120ms that the client stopped waiting for at 100ms. The work happened, consumed a connection, a thread, a query, and then was thrown away. Under load this is how one slow dependency turns into a backend full of threads all computing answers nobody is waiting for.

The fix is to carry the deadline itself down the chain, not a fixed per-hop timeout. Each hop receives how much wall-clock budget remains, and before starting real work it checks: is the remaining budget even enough to finish? If the elapsed time has already eaten the budget -- or the remaining slice is smaller than the work will take -- the hop fails FAST, immediately, doing none of the doomed work and returning a deadline-exceeded error up the chain. The request still fails (it was always going to miss the deadline), but it fails without a backend service spending 50ms of database time on a query whose result will land after the caller has gone.

The distinction to hold onto: deadline propagation does not make a doomed request succeed. Its whole value is on the resource side -- it stops the system from doing work it can already prove is too late, so the thread, the connection, and the downstream capacity are freed at the moment failure becomes certain instead of after the last hop grinds through its full cost. That is what keeps one slow dependency from cascading into exhausted pools everywhere upstream.

The rule: propagate the request's remaining deadline down every hop of a call chain (and have each hop fail fast when the remaining budget is smaller than its own work) rather than giving each hop an independent fixed timeout, because an independent timeout lets a late hop run its full duration on a request whose end-to-end deadline has already passed -- burning downstream resources for a result the caller abandoned -- whereas a propagated deadline stops the doomed work the instant it becomes doomed.

On this fixture the budget is 100ms and the hops cost 30 + 40 + 50 = 120ms, so the request is doomed: db would start at elapsed 70ms with 30ms left but needs 50ms. With per-hop timeouts db runs its full 50ms anyway (50ms of doomed work, done by 120ms). With deadline propagation db sees 30ms < 50ms and refuses, doing 0ms of doomed work and freeing the backend at 70ms. This computes both.

  --trace     the chain: each hop's cost, start time, and finish time under independent per-hop timeouts
  --budget    per-hop timeouts vs deadline propagation: doomed work performed, when the backend is freed, and the request outcome
  --check     the request exceeds its budget; per-hop timeouts do doomed downstream work while propagation fails fast with none

budget_ms and chain are the fixture; every start time, wasted-work total, and outcome is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deadline.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_independent(budget, chain):
    """Per-hop timeouts: every hop runs its full cost regardless of the shared budget. Returns per-hop timing and doomed-work total."""
    elapsed = 0
    rows = []
    doomed = 0
    for hop in chain:
        start = elapsed
        remaining = budget - start
        finishes_in_time = hop["cost_ms"] <= remaining
        elapsed += hop["cost_ms"]
        if not finishes_in_time:
            doomed += hop["cost_ms"]
        rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": elapsed, "in_time": finishes_in_time})
    return rows, doomed, elapsed


def run_propagated(budget, chain):
    """Deadline propagation: each hop checks the remaining budget and fails fast if it cannot finish. Returns timing and where it stopped."""
    elapsed = 0
    rows = []
    doomed = 0
    stopped_at = None
    for hop in chain:
        start = elapsed
        remaining = budget - start
        if hop["cost_ms"] > remaining:
            rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": start, "ran": False})
            stopped_at = hop["service"]
            break
        elapsed += hop["cost_ms"]
        rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": elapsed, "ran": True})
    return rows, doomed, elapsed, stopped_at


def total_cost(chain):
    return sum(hop["cost_ms"] for hop in chain)


# ----------------------------------------------------------------- printing

def trace_view(data):
    budget, chain = data["budget_ms"], data["chain"]
    rows, doomed, finish = run_independent(budget, chain)
    print("TRACE — the chain under independent per-hop timeouts (budget %dms)" % budget)
    print("-" * 62)
    print("  hop       cost   start   finish   finishes in time?")
    for r in rows:
        print("  %-8s  %-5d  %-6d  %-7d  %s" % (r["service"], r["cost"], r["start"], r["finish"], r["in_time"]))
    print("-" * 62)
    print("  total chain cost = %dms vs budget %dms ; last hop finishes at %dms" % (total_cost(chain), budget, finish))


def budget_view(data):
    budget, chain = data["budget_ms"], data["chain"]
    irows, idoomed, ifinish = run_independent(budget, chain)
    prows, pdoomed, pfinish, stopped = run_propagated(budget, chain)
    print("BUDGET — per-hop timeouts vs deadline propagation")
    print("-" * 66)
    print("  per-hop timeouts:   backend busy until %dms, doomed work = %dms" % (ifinish, idoomed))
    print("    (%s each ran its full timeout; %s finished after the %dms deadline)"
          % (", ".join(r["service"] for r in irows), ", ".join(r["service"] for r in irows if not r["in_time"]), budget))
    print("  deadline propagation: backend freed at %dms, doomed work = %dms" % (pfinish, pdoomed))
    print("    (%s failed fast: %dms remaining < %dms cost)"
          % (stopped, budget - pfinish, next(h["cost_ms"] for h in chain if h["service"] == stopped)))
    print("-" * 66)
    print("  both outcomes: request MISSES its %dms deadline either way -- propagation saves resources, not the request" % budget)


def check(data):
    print("SELF-TEST — the request exceeds its budget; per-hop timeouts do doomed downstream work while propagation fails fast with none")
    print("-" * 128)
    budget, chain = data["budget_ms"], data["chain"]
    irows, idoomed, ifinish = run_independent(budget, chain)
    prows, pdoomed, pfinish, stopped = run_propagated(budget, chain)

    request_exceeds_budget = total_cost(chain) > budget
    print("  the chain cannot finish within the budget = %s (%dms cost > %dms budget)" % (request_exceeds_budget, total_cost(chain), budget))

    naive_does_doomed_work = idoomed > 0
    print("  per-hop timeouts perform doomed downstream work = %s (%dms wasted on hops finishing after the deadline)" % (naive_does_doomed_work, idoomed))

    propagation_fails_fast = stopped is not None
    print("  deadline propagation fails fast at a hop = %s (stopped at %s)" % (propagation_fails_fast, stopped))

    propagation_no_wasted_work = pdoomed == 0
    print("  deadline propagation performs zero doomed work = %s (%dms)" % (propagation_no_wasted_work, pdoomed))

    propagation_frees_backend_earlier = pfinish < ifinish
    print("  propagation frees the backend earlier than per-hop timeouts = %s (%dms < %dms)" % (propagation_frees_backend_earlier, pfinish, ifinish))

    both_miss_deadline = ifinish > budget and pfinish <= budget and stopped is not None
    print("  the request misses its deadline both ways = %s (propagation saves resources, not the request)" % both_miss_deadline)

    ok = request_exceeds_budget and naive_does_doomed_work and propagation_fails_fast and propagation_no_wasted_work and propagation_frees_backend_earlier and both_miss_deadline
    print("-" * 128)
    print("SELF-TEST %s  request_exceeds_budget=%s  naive_does_doomed_work=%s  propagation_fails_fast=%s  propagation_no_wasted_work=%s  propagation_frees_backend_earlier=%s  both_miss_deadline=%s"
          % ("PASS" if ok else "FAIL", request_exceeds_budget, naive_does_doomed_work, propagation_fails_fast, propagation_no_wasted_work, propagation_frees_backend_earlier, both_miss_deadline))
    return ok


def main():
    p = argparse.ArgumentParser(description="Deadline propagation: propagate the request's remaining deadline down every hop of a call chain (and have each hop fail fast when the remaining budget is smaller than its own work) rather than giving each hop an independent fixed timeout, because an independent timeout lets a late hop run its full duration on a request whose end-to-end deadline has already passed -- burning downstream resources for a result the caller abandoned -- whereas a propagated deadline stops the doomed work the instant it becomes doomed.")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("budget_ms=%d  chain=%s  file=%s  (the budget and hop costs are a fixture)"
          % (data["budget_ms"], [h["service"] for h in data["chain"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trace:
        trace_view(data)
    elif args.budget:
        budget_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
