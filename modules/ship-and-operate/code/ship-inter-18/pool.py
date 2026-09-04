"""Size the connection pool by Little's law, or a pool sized by request rate becomes the bottleneck.

Every request borrows a connection from a fixed pool, holds it for the duration of the downstream call, then
returns it. The tempting way to size the pool is by request rate: "we do 60 requests a second, give me 60
connections." That ignores the one number that decides capacity -- how long each request HOLDS its connection.
A pool of N connections, each tied up for hold_time seconds, can free and reuse a connection only hold_time
seconds after it is borrowed, so the pool can complete at most N / hold_time requests per second. If each call
takes 2 seconds, 60 connections complete only 30 requests a second -- half the demand. The other half queue
for a connection, the queue grows without bound, and latency climbs until requests time out. The pool, not the
downstream, is now the bottleneck, and it was sized by a rule that never looked at hold time.

Little's law gives the right size: the average number of connections in use equals the arrival rate times the
hold time, so the pool must be at least arrival_rate * hold_time to keep up. Size it that way and the pool's
throughput ceiling (N / hold_time) meets the demand; size it by rate alone and you are short by exactly the
hold-time factor. The fix is not "add more connections until it works" -- it is to compute N from both the
rate and the hold time, because a pool that is fine at 200ms calls is catastrophically undersized at 2s calls.

On this fixture demand is 60 req/s and each call holds a connection for 2s, so Little's law needs 120
connections. A pool of 60 (sized by rate) tops out at 30 req/s -- it cannot keep up. A pool of 120 tops out at
exactly 60 -- it meets demand. This computes both.

  --capacity   each pool's throughput ceiling (N / hold_time) against the demand
  --sizing     the required pool size from Little's law, and how the by-rate pool falls short
  --check      the by-rate pool bottlenecks; the Little's-law pool meets demand

The arrival rate, hold time, and pool sizes are the fixture; every capacity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pool.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def required_pool(arrival_rate, hold_time):
    """Little's law: connections in use = arrival rate * hold time."""
    return arrival_rate * hold_time


def max_throughput(pool_size, hold_time):
    """The most requests per second a pool can complete: each connection frees every hold_time seconds."""
    return pool_size / hold_time


def keeps_up(pool_size, arrival_rate, hold_time):
    return max_throughput(pool_size, hold_time) >= arrival_rate


# ----------------------------------------------------------------- printing

def capacity_view(data):
    rate, hold = data["arrival_rate"], data["hold_time"]
    print("CAPACITY — throughput ceiling per pool (demand %d req/s, hold %.1fs)" % (rate, hold))
    print("-" * 64)
    for name, n in data["pools"].items():
        tp = max_throughput(n, hold)
        verdict = "meets demand" if tp >= rate else "BOTTLENECK (%.0f short)" % (rate - tp)
        print("  %-10s %3d conns  ->  %5.1f req/s   %s" % (name, n, tp, verdict))
    print("-" * 64)
    print("  a pool completes N/hold_time req/s, not N req/s.")


def sizing_view(data):
    rate, hold = data["arrival_rate"], data["hold_time"]
    req = required_pool(rate, hold)
    print("SIZING — the pool size Little's law requires")
    print("-" * 64)
    print("  required = arrival_rate * hold_time = %d * %.1f = %.0f connections" % (rate, hold, req))
    print("  sizing by rate alone would pick %d -- short by %.0f (a factor of %.1f)" % (rate, req - rate, hold))
    print("-" * 64)
    print("  the missing factor is the hold time; ignore it and you undersize by exactly it.")


def check(data):
    print("SELF-TEST — the by-rate pool bottlenecks; the Little's-law pool meets demand")
    print("-" * 96)
    rate, hold = data["arrival_rate"], data["hold_time"]
    pools = data["pools"]
    req = required_pool(rate, hold)

    required_is_rate_times_hold = req == rate * hold
    print("  required pool = arrival_rate * hold_time = %s (%.0f)" % (required_is_rate_times_hold, req))

    by_rate_undersized = pools["by_rate"] < req
    print("  sizing by rate alone is undersized = %s (%d < %.0f)" % (by_rate_undersized, pools["by_rate"], req))

    by_rate_bottlenecks = not keeps_up(pools["by_rate"], rate, hold)
    print("  the by-rate pool cannot meet demand = %s (%.0f < %d req/s)" % (by_rate_bottlenecks, max_throughput(pools["by_rate"], hold), rate))

    by_little_meets = keeps_up(pools["by_little"], rate, hold)
    print("  the Little's-law pool meets demand = %s (%.0f >= %d req/s)" % (by_little_meets, max_throughput(pools["by_little"], hold), rate))

    hold_time_is_the_missing_factor = pools["by_rate"] == rate and abs(req - rate * hold) < 1e-9 and hold != 1.0
    print("  the by-rate rule drops the hold-time factor = %s (rate %d vs required %.0f)" % (hold_time_is_the_missing_factor, rate, req))

    ok = required_is_rate_times_hold and by_rate_undersized and by_rate_bottlenecks and by_little_meets and hold_time_is_the_missing_factor
    print("-" * 96)
    print("SELF-TEST %s  required_is_rate_times_hold=%s  by_rate_undersized=%s  by_rate_bottlenecks=%s  by_little_meets=%s  hold_time_is_the_missing_factor=%s"
          % ("PASS" if ok else "FAIL", required_is_rate_times_hold, by_rate_undersized, by_rate_bottlenecks, by_little_meets, hold_time_is_the_missing_factor))
    return ok


def main():
    p = argparse.ArgumentParser(description="Size a connection pool by Little's law (rate * hold time), not by rate alone.")
    p.add_argument("--capacity", action="store_true")
    p.add_argument("--sizing", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("arrival_rate=%d req/s  hold_time=%.1fs  file=%s  (the rate, hold time, and pools are a fixture)"
          % (data["arrival_rate"], data["hold_time"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.capacity:
        capacity_view(data)
    elif args.sizing:
        sizing_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
