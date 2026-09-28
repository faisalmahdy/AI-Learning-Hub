"""Wrap every tool dispatch in a per-call timeout -- a harness that calls a tool and blocks on the return with no timeout freezes the whole agent the moment one call never returns, and no iteration cap saves it because the wedged step never completes to be counted, while a per-call timeout turns the hang into an ordinary error the loop records and steps past.

An agent loop's tools are I/O: a network request, a subprocess, a database query, another model. Any of them can hang -- a socket with no timeout, a deadlocked lock, a dependency that is down but holding the connection open. The naive loop dispatches the call and blocks on its return, so a call that never returns blocks the loop forever. The agent is not crashed and not oscillating; it is wedged on one call. The loop-iteration bound and the tool-call budget both count completed steps, and this step never completes, so neither ever fires -- the run just stops making progress, silently, with no error and no result.

The fix is a per-call timeout, a watchdog around each dispatch. If the tool has not returned within the budget, abort the wait and hand the loop a timeout error for that call, exactly as if the tool had raised. The agent proceeds on that error -- retry, try an alternative, or report the failure -- and the whole run is bounded by the number of calls times the timeout instead of being hostage to the slowest tool. Calls that finish inside the budget are untouched: the timeout is a ceiling, not a delay.

On this fixture the plan is three calls -- read_config (20 ms), call_flaky_api (never returns), write_output (30 ms) -- with a 100 ms per-call budget. With no timeout the loop runs c1, blocks on c2 forever, and never reaches c3: the run does not complete. With the timeout, c1 finishes normally, c2 is aborted at 100 ms and recorded as a timeout error, c3 finishes normally, and the run completes in 150 ms with every step accounted for. This computes both.

  --notimeout  dispatch and block: the run wedges on the first hung call and never finishes
  --timeout    per-call watchdog: the hung call becomes a timeout error, fast calls run normally, the run completes and is bounded
  --check      the no-timeout run hangs while the timeout run completes, bounds its total time, surfaces the hung call as an error, and leaves the fast calls untouched

the plan, each call's duration (null = never returns), and the per-call timeout are the fixture; whether the run completes, its elapsed time, and every call's outcome under each strategy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tooltimeout.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def hangs(call):
    """A call with no return duration never returns -- it hangs the caller that blocks on it."""
    return call["duration_ms"] is None


def run_no_timeout(plan):
    """Dispatch each call and block on its return; a hung call wedges the loop and later steps never run."""
    elapsed, outcomes = 0, []
    for call in plan:
        if hangs(call):
            return {"completed": False, "elapsed": None, "wedged_at": call["id"], "outcomes": outcomes}
        elapsed += call["duration_ms"]
        outcomes.append({"id": call["id"], "outcome": "ok", "ms": call["duration_ms"]})
    return {"completed": True, "elapsed": elapsed, "wedged_at": None, "outcomes": outcomes}


def run_with_timeout(plan, timeout_ms):
    """Bound each call by the timeout; an over-budget call is aborted and recorded as a timeout error."""
    elapsed, outcomes = 0, []
    for call in plan:
        if hangs(call) or call["duration_ms"] > timeout_ms:
            elapsed += timeout_ms
            outcomes.append({"id": call["id"], "outcome": "timeout", "ms": timeout_ms})
        else:
            elapsed += call["duration_ms"]
            outcomes.append({"id": call["id"], "outcome": "ok", "ms": call["duration_ms"]})
    return {"completed": True, "elapsed": elapsed, "wedged_at": None, "outcomes": outcomes}


# ----------------------------------------------------------------- printing

def _dur(call):
    return "hangs" if hangs(call) else "%d ms" % call["duration_ms"]


def notimeout_view(data):
    plan = data["plan"]
    r = run_no_timeout(plan)
    print("NO-TIMEOUT — dispatch each call and block on its return")
    print("-" * 64)
    for call in plan:
        done = any(o["id"] == call["id"] for o in r["outcomes"])
        mark = "ok" if done else ("BLOCKS FOREVER" if call["id"] == r["wedged_at"] else "never reached")
        print("  %s %-16s %-8s -> %s" % (call["id"], call["tool"], _dur(call), mark))
    print("-" * 64)
    print("  run completed = %s   wedged on %s   (c3 never ran)" % (r["completed"], r["wedged_at"]))


def timeout_view(data):
    plan, t = data["plan"], data["timeout_ms"]
    r = run_with_timeout(plan, t)
    print("TIMEOUT — bound each call by %d ms; over-budget calls become timeout errors" % t)
    print("-" * 64)
    for o in r["outcomes"]:
        print("  %s %-8s at %d ms" % (o["id"], o["outcome"].upper(), o["ms"]))
    print("-" * 64)
    print("  run completed = %s   total elapsed = %d ms   (bounded by %d x %d)" % (r["completed"], r["elapsed"], len(plan), t))


def check(data):
    print("SELF-TEST — the no-timeout run hangs while the timeout run completes, bounds its total time, surfaces the hung call as an error, and leaves the fast calls untouched")
    print("-" * 112)
    plan, t = data["plan"], data["timeout_ms"]
    nt = run_no_timeout(plan)
    wt = run_with_timeout(plan, t)

    notimeout_hangs = not nt["completed"]
    print("  no-timeout run does not complete (wedged on %s) = %s" % (nt["wedged_at"], notimeout_hangs))

    timeout_completes = wt["completed"]
    print("  timeout run completes = %s (elapsed %d ms)" % (timeout_completes, wt["elapsed"]))

    timeout_bounds_total = wt["elapsed"] <= len(plan) * t
    print("  timeout run total is bounded by n_calls x timeout = %s (%d <= %d)" % (timeout_bounds_total, wt["elapsed"], len(plan) * t))

    hung_becomes_error = any(o["outcome"] == "timeout" for o in wt["outcomes"] if o["id"] == nt["wedged_at"])
    print("  the hung call is surfaced as a timeout error, not a freeze = %s" % hung_becomes_error)

    fast = [c for c in plan if not hangs(c) and c["duration_ms"] <= t]
    fast_untouched = all(
        any(o["id"] == c["id"] and o["outcome"] == "ok" and o["ms"] == c["duration_ms"] for o in wt["outcomes"])
        for c in fast)
    print("  calls within budget run to completion, not aborted = %s (%d fast calls)" % (fast_untouched, len(fast)))

    ok = (notimeout_hangs and timeout_completes and timeout_bounds_total
          and hung_becomes_error and fast_untouched)
    print("-" * 112)
    print("SELF-TEST %s  notimeout_hangs=%s  timeout_completes=%s  timeout_bounds_total=%s  hung_becomes_error=%s  fast_untouched=%s"
          % ("PASS" if ok else "FAIL", notimeout_hangs, timeout_completes, timeout_bounds_total,
             hung_becomes_error, fast_untouched))
    return ok


def main():
    p = argparse.ArgumentParser(description="Per-call tool timeout: wrap every tool dispatch in a timeout, because a harness that blocks on a call's return freezes the whole agent the moment one tool never returns -- and no iteration or step budget helps, since the wedged step never completes to be counted -- while a per-call timeout turns the hang into an ordinary error the loop records and steps past, leaving fast calls untouched and bounding the run by n_calls times the timeout.")
    p.add_argument("--notimeout", action="store_true")
    p.add_argument("--timeout", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("timeout_ms=%d  plan=%d calls  file=%s" % (data["timeout_ms"], len(data["plan"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.notimeout:
        notimeout_view(data)
    elif args.timeout:
        timeout_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
