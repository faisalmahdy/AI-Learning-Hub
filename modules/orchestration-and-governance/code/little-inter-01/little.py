"""Size the pool by Little's Law -- concurrency = rate x latency -- or a slower dependency silently caps your throughput.

A service serves a request by holding a slot -- a connection, a worker, a thread -- for as long as the request takes.
How many slots do you need? The tempting answer is "one per request per second" -- read the peak rate off a dashboard,
round it up, done. That confuses rate with concurrency. Little's Law says the average number of requests IN FLIGHT is
L = arrival_rate x latency: at 200 requests per second each holding a slot for 0.05 seconds, only 10 are in flight at
once, so 10 slots suffice and 200 would sit mostly idle. The pool size you need is not the rate; it is the rate times
how long each request stays.

That is the trap, because latency is not constant. When a downstream dependency slows, the same requests arrive at the
same rate but each holds its slot longer, so the concurrency you need -- L = rate x latency -- goes UP. A pool sized for
the fast case cannot grow to meet it. With only pool_size slots each freed every `latency` seconds, the most you can
complete is pool_size / latency requests per second; once that ceiling drops below the arrival rate, requests queue
faster than they drain and the backlog grows without bound. The service did not run out of CPU; it ran out of slots,
and the ceiling moved because latency moved, exactly the variable the rate-based sizing ignored.

On this fixture the load is a steady 200 req/s. When the dependency is fast (0.05 s) the service needs L = 10 slots and
the 20-slot pool has room to spare, sustaining 20/0.05 = 400 req/s. When the dependency slows to 0.25 s the service
needs L = 50 slots, but the pool is still 20, so throughput is capped at 20/0.25 = 80 req/s -- 120 req/s short of the
offered load, a backlog that grows by 120 every second. Sizing the pool to L = rate x latency = 50 restores 200 req/s.

  --size        the concurrency Little's Law requires (rate x latency) fast vs slow, against the fixed 20-slot pool
  --throughput  the throughput ceiling pool/latency imposes, the shortfall vs the offered load, and the backlog rate
  --check       required concurrency = rate x latency; the fixed pool caps throughput below the load when latency rises

The rate, the two latencies, and the pool size are the fixture; every concurrency and ceiling is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "little.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def required_concurrency(rate, latency):
    """Little's Law: the average number of in-flight requests L = arrival_rate * latency."""
    return rate * latency


def max_throughput(pool, latency):
    """The most requests per second `pool` slots can complete when each is held for `latency` seconds."""
    return pool / latency


def backlog_rate(rate, pool, latency):
    """How fast the queue grows: offered load minus what the pool can drain (0 if the pool keeps up)."""
    return max(0.0, rate - max_throughput(pool, latency))


# ----------------------------------------------------------------- printing

def size_view(data):
    rate, wf, ws, pool = data["arrival_rate"], data["latency_fast"], data["latency_slow"], data["pool_size"]
    print("SIZE — Little's Law: concurrency needed = arrival_rate x latency (pool is fixed at %d)" % pool)
    print("-" * 68)
    print("  offered load           = %d req/s (unchanged)" % rate)
    print("  fast dependency %.2fs:  need L = %d x %.2f = %.0f slots   pool %d -> %s"
          % (wf, rate, wf, required_concurrency(rate, wf), pool, "fits" if pool >= required_concurrency(rate, wf) else "SHORT"))
    print("  slow dependency %.2fs:  need L = %d x %.2f = %.0f slots   pool %d -> %s"
          % (ws, rate, ws, required_concurrency(rate, ws), pool, "fits" if pool >= required_concurrency(rate, ws) else "SHORT"))
    print("-" * 68)
    print("  same request rate; the slower dependency needs 5x the slots, and 20 no longer covers it.")


def throughput_view(data):
    rate, ws, pool = data["arrival_rate"], data["latency_slow"], data["pool_size"]
    ceiling = max_throughput(pool, ws)
    need = required_concurrency(rate, ws)
    print("THROUGHPUT — a fixed pool caps throughput at pool/latency once latency rises")
    print("-" * 66)
    print("  offered load                 = %d req/s" % rate)
    print("  throughput ceiling pool/lat  = %d / %.2f = %.0f req/s" % (pool, ws, ceiling))
    print("  shortfall vs offered load    = %.0f req/s" % (rate - ceiling))
    print("  backlog grows by             = %.0f req/s" % backlog_rate(rate, pool, ws))
    print("  pool needed for %d req/s      = ceil(%d x %.2f) = %d slots" % (rate, rate, ws, math.ceil(need)))
    print("-" * 66)
    print("  raising the pool to the Little's-Law number clears the backlog; nothing else changed.")


def check(data):
    print("SELF-TEST — required concurrency = rate x latency; a fixed pool caps throughput below the load when latency rises")
    print("-" * 116)
    rate, wf, ws, pool = data["arrival_rate"], data["latency_fast"], data["latency_slow"], data["pool_size"]

    littles_law = required_concurrency(rate, wf) == rate * wf and required_concurrency(rate, ws) == rate * ws
    print("  required concurrency equals arrival_rate x latency = %s (%.0f fast, %.0f slow)"
          % (littles_law, required_concurrency(rate, wf), required_concurrency(rate, ws)))

    fits_when_fast = pool >= required_concurrency(rate, wf)
    print("  the fixed pool covers the fast case = %s (%d >= %.0f)" % (fits_when_fast, pool, required_concurrency(rate, wf)))

    short_when_slow = pool < required_concurrency(rate, ws)
    print("  the fixed pool is short once latency rises = %s (%d < %.0f)" % (short_when_slow, pool, required_concurrency(rate, ws)))

    throughput_capped = max_throughput(pool, ws) < rate
    print("  throughput is capped below the offered load = %s (%.0f < %d req/s)" % (throughput_capped, max_throughput(pool, ws), rate))

    backlog_grows = backlog_rate(rate, pool, ws) > 0
    print("  the backlog grows without bound = %s (+%.0f req/s)" % (backlog_grows, backlog_rate(rate, pool, ws)))

    resize_fixes = max_throughput(math.ceil(required_concurrency(rate, ws)), ws) >= rate
    print("  sizing the pool to rate x latency restores the load = %s (%d slots -> %.0f req/s)"
          % (resize_fixes, math.ceil(required_concurrency(rate, ws)), max_throughput(math.ceil(required_concurrency(rate, ws)), ws)))

    ok = littles_law and fits_when_fast and short_when_slow and throughput_capped and backlog_grows and resize_fixes
    print("-" * 116)
    print("SELF-TEST %s  littles_law=%s  fits_when_fast=%s  short_when_slow=%s  throughput_capped=%s  backlog_grows=%s  resize_fixes=%s"
          % ("PASS" if ok else "FAIL", littles_law, fits_when_fast, short_when_slow, throughput_capped, backlog_grows, resize_fixes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Little's Law: the concurrency a service needs is arrival_rate x latency, so a pool sized without latency caps throughput at pool/latency when a dependency slows.")
    p.add_argument("--size", action="store_true")
    p.add_argument("--throughput", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("arrival_rate=%d req/s  latency_fast=%.2fs  latency_slow=%.2fs  pool_size=%d  file=%s  (the parameters are a fixture)"
          % (data["arrival_rate"], data["latency_fast"], data["latency_slow"], data["pool_size"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.size:
        size_view(data)
    elif args.throughput:
        throughput_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
