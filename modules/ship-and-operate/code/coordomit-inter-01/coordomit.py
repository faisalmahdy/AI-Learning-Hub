"""Count the requests a stall omitted, not just the one it caught -- or your latency tail hides the worst of the outage.

A load tester measures latency by sending requests and timing the responses, and the common design is closed-loop: send
a request, wait for its response, then send the next. That feedback is the bug. When the server stalls -- freezes for a
second under a garbage-collection pause, a lock, a failover -- the one request that was in flight records the full stall
as its latency, which is correct. But while the tester sits blocked waiting for that response, it does NOT send the
requests that were scheduled to go out during the freeze. Those requests never happen, so they never get measured -- and
they are exactly the requests that would have measured the tail, because every one of them would have been stuck behind
the same stall. The tester recorded one slow request and silently omitted the several equally-slow ones its own blocking
prevented. This is coordinated omission: the measurement process colludes with the stall to hide it.

The consequence is a latency distribution that looks far healthier than reality. A one-second freeze that should show up
as a cluster of slow requests shows up as a single outlier, so the mean barely moves and the high percentiles -- the p99
you page on -- stay green through an outage that made a fifth of the intended requests slow. The fix is to stop letting
the response gate the send: either drive the load open-loop (send on the schedule regardless of when responses come
back), or correct after the fact by backfilling each omitted request with the latency it would have had -- the time from
its intended send until the stall cleared. Then the tail shows the whole stall, not the tip of it.

On this fixture 20 requests are scheduled one per unit and the server freezes for 5 units starting at time 5. The
closed-loop tester records just 1 slow request (the in-flight one, latency 5) and omits the 4 scheduled during the
freeze. The corrected measurement records all 5 (latencies 5, 4, 3, 2, 1), so its mean and tail are far higher: the p90
jumps from 0 to 4. This computes both.

  --measure  the closed-loop latency samples vs the corrected (open-loop) ones, with mean and max
  --tail     how many requests the stall actually slowed (1 measured vs 5 real) and the p90 each reports
  --check    closed-loop omits the requests scheduled during the stall; correcting them raises the mean and the tail

The schedule and stall are the fixture; every latency and percentile is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "coordomit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def true_latency(t, stall_start, stall_end):
    """Latency of a request intended at time t: 0 normally, or the wait until the stall clears if it hit the freeze."""
    return stall_end - t if stall_start <= t < stall_end else 0


def corrected_latencies(data):
    """Open-loop: every scheduled request with the latency it would truly have had."""
    end = data["stall_start"] + data["stall_duration"]
    return [true_latency(t * data["interval"], data["stall_start"], end) for t in range(data["requests"])]


def closed_loop_latencies(data):
    """Closed-loop: the tester blocks during the stall, so requests scheduled strictly inside the freeze never send."""
    start, end = data["stall_start"], data["stall_start"] + data["stall_duration"]
    return [true_latency(t * data["interval"], start, end)
            for t in range(data["requests"]) if not (start < t * data["interval"] < end)]


def percentile(values, p):
    """The p-th percentile by nearest-rank on the sorted samples."""
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100.0 * len(s) + 0.5)) - 1))
    return s[k]


def mean(values):
    return sum(values) / len(values) if values else 0.0


# ----------------------------------------------------------------- printing

def measure_view(data):
    cl = closed_loop_latencies(data)
    co = corrected_latencies(data)
    print("MEASURE — closed-loop samples vs corrected (open-loop) samples")
    print("-" * 62)
    print("  closed-loop latencies:  %s" % cl)
    print("    samples %d   mean %.3f   max %d" % (len(cl), mean(cl), max(cl)))
    print("  corrected latencies:    %s" % co)
    print("    samples %d   mean %.3f   max %d" % (len(co), mean(co), max(co)))
    print("-" * 62)
    print("  the closed-loop set is missing the requests the stall would have slowed.")


def tail_view(data):
    cl = closed_loop_latencies(data)
    co = corrected_latencies(data)
    print("TAIL — how many requests the stall actually slowed, and the p90")
    print("-" * 56)
    print("  requests the stall slowed, closed-loop measured:  %d" % sum(1 for x in cl if x > 0))
    print("  requests the stall slowed, actually:              %d" % sum(1 for x in co if x > 0))
    print("  p90 latency, closed-loop:  %d" % percentile(cl, 90))
    print("  p90 latency, corrected:    %d" % percentile(co, 90))
    print("-" * 56)
    print("  the stall hit %d requests; closed-loop saw 1 of them, so its p90 stays flat." % sum(1 for x in co if x > 0))


def check(data):
    print("SELF-TEST — closed-loop omits the requests scheduled during the stall; correcting them raises the mean and the tail")
    print("-" * 118)
    cl = closed_loop_latencies(data)
    co = corrected_latencies(data)

    omitted = len(co) - len(cl)
    omits_requests = omitted == data["stall_duration"] - 1
    print("  closed-loop omits the requests scheduled inside the freeze = %s (%d omitted)" % (omits_requests, omitted))

    same_max = max(cl) == max(co)
    print("  both see the same single worst request (the in-flight one) = %s (max %d)" % (same_max, max(cl)))

    more_slow_when_corrected = sum(1 for x in co if x > 0) > sum(1 for x in cl if x > 0)
    print("  correcting reveals more slow requests than closed-loop saw = %s (%d vs %d)"
          % (more_slow_when_corrected, sum(1 for x in co if x > 0), sum(1 for x in cl if x > 0)))

    mean_rises = mean(co) > mean(cl)
    print("  the corrected mean latency is higher = %s (%.3f > %.3f)" % (mean_rises, mean(co), mean(cl)))

    tail_rises = percentile(co, 90) > percentile(cl, 90)
    print("  the corrected p90 is higher (the hidden tail) = %s (%d > %d)" % (tail_rises, percentile(co, 90), percentile(cl, 90)))

    ok = omits_requests and same_max and more_slow_when_corrected and mean_rises and tail_rises
    print("-" * 118)
    print("SELF-TEST %s  omits_requests=%s  same_max=%s  more_slow_when_corrected=%s  mean_rises=%s  tail_rises=%s"
          % ("PASS" if ok else "FAIL", omits_requests, same_max, more_slow_when_corrected, mean_rises, tail_rises))
    return ok


def main():
    p = argparse.ArgumentParser(description="Coordinated omission: a closed-loop load tester blocks during a stall and never sends the requests scheduled during it, so it omits the tail; correct by measuring open-loop or backfilling the omitted latencies.")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--tail", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  interval=%d  stall_start=%d  stall_duration=%d  file=%s  (the load test is a fixture)"
          % (data["requests"], data["interval"], data["stall_start"], data["stall_duration"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.measure:
        measure_view(data)
    elif args.tail:
        tail_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
