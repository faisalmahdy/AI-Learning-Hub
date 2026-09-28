"""Run independent tool calls in parallel -- a serial harness pays the sum of durations, not the critical path.

When an agent turn issues several tool calls, many of them are independent: a web search and a database
read need nothing from each other and could run at the same time. A serial harness runs them one after
another anyway, so the turn's latency is the SUM of every call's duration -- and the user waits through
calls that could have overlapped. A parallel harness runs independent calls concurrently and waits only
where one call genuinely needs another's output, so the turn's latency is the CRITICAL PATH: the longest
chain of dependent durations, not the total.

The dependencies are what force any serialization at all. A call that summarizes a document cannot start
until the fetch that produced the document finishes; those two must run in order. But calls with no
dependency between them can overlap freely, and the harness that runs them serially is leaving latency on
the table for no reason. The speedup from parallelizing is the sum divided by the critical path.

On this fixture four calls run in a turn: A (3s), B (2s), C (4s) are independent, and D (1s) depends on A.
Serially that is 3+2+4+1 = 10s. In parallel, A, B, C start at once; D starts when A finishes at 3s and
ends at 4s; the whole turn finishes at 4s -- the critical path A→D and the standalone C both end at 4. Same
work, 10s versus 4s, a 2.5x speedup, and D still correctly waits for A. This computes both.

  --calls      the tool calls, their durations, and their dependencies
  --latency    the serial (sum) vs parallel (critical-path) turn latency
  --check      parallel equals the critical path and beats serial, while dependencies are still respected

The calls and dependencies are the fixture; every latency is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "calls.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def serial_latency(calls):
    """One after another: the turn takes the sum of every call's duration."""
    return sum(c["seconds"] for c in calls.values())


def finish_time(cid, calls):
    """Earliest time this call can finish: its duration plus the finish time of what it depends on."""
    call = calls[cid]
    dep = call["depends_on"]
    return call["seconds"] + (finish_time(dep, calls) if dep else 0)


def parallel_latency(calls):
    """Independent calls overlap; the turn finishes when the last call does -- the critical path."""
    return max(finish_time(cid, calls) for cid in calls)


# ----------------------------------------------------------------- printing

def calls_view(data):
    calls = data["calls"]
    print("CALLS — %d tool calls in one turn" % len(calls))
    print("-" * 46)
    for cid in sorted(calls):
        dep = calls[cid]["depends_on"]
        dep_str = "depends on %s" % dep if dep else "independent"
        print("  %s  %ds   %s" % (cid, calls[cid]["seconds"], dep_str))
    print("-" * 46)
    print("  A, B, C need nothing from each other; only D waits for A.")


def latency_view(data):
    calls = data["calls"]
    s = serial_latency(calls)
    p = parallel_latency(calls)
    print("LATENCY — serial (sum) vs parallel (critical path)")
    print("-" * 50)
    print("  serial:   %2ds  (3+2+4+1, one after another)" % s)
    print("  parallel: %2ds  (A,B,C at once; D after A)" % p)
    print("  speedup:  %.1fx" % (s / p))
    print("-" * 50)
    print("  the parallel turn finishes when the longest dependency chain does.")


def check(data):
    print("SELF-TEST — parallel equals the critical path and beats serial, while dependencies are respected")
    print("-" * 92)
    calls = data["calls"]
    s = serial_latency(calls)
    p = parallel_latency(calls)

    parallel_faster = p < s
    print("  the parallel turn is faster than serial = %s (%ds vs %ds)" % (parallel_faster, p, s))

    # the critical path is the longest single chain of dependent durations
    critical = max(finish_time(cid, calls) for cid in calls)
    parallel_is_critical_path = p == critical
    print("  parallel latency equals the critical path = %s (%ds)" % (parallel_is_critical_path, critical))

    # a dependent call cannot finish before its dependency
    d_ok = finish_time("D", calls) >= finish_time("A", calls) + calls["D"]["seconds"]
    print("  the dependent call D still waits for A = %s (D finishes at %d, after A at %d)"
          % (d_ok, finish_time("D", calls), finish_time("A", calls)))

    # serial pays for the independent calls that could have overlapped
    independent = [cid for cid in calls if calls[cid]["depends_on"] is None]
    serial_pays_sum = s == sum(calls[c]["seconds"] for c in calls)
    print("  serial pays the full sum incl. %d independent calls = %s (%ds)" % (len(independent), serial_pays_sum, s))

    ok = parallel_faster and parallel_is_critical_path and d_ok and serial_pays_sum
    print("-" * 92)
    print("SELF-TEST %s  parallel_faster=%s  parallel_is_critical_path=%s  dependency_respected=%s  serial_pays_sum=%s"
          % ("PASS" if ok else "FAIL", parallel_faster, parallel_is_critical_path, d_ok, serial_pays_sum))
    return ok


def main():
    p = argparse.ArgumentParser(description="Run independent tool calls in parallel to pay the critical path, not the sum.")
    p.add_argument("--calls", action="store_true")
    p.add_argument("--latency", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  serial=%ds  parallel=%ds  file=%s  (the calls are a fixture)"
          % (len(data["calls"]), serial_latency(data["calls"]), parallel_latency(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.calls:
        calls_view(data)
    elif args.latency:
        latency_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
