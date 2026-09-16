"""Trip a circuit breaker when a dependency fails -- without one, every request waits the full timeout and piles onto the outage.

When a downstream dependency goes down, calls to it do not fail instantly -- they hang until a timeout fires, so each
attempt costs the full timeout, and every one of those attempts is load thrown onto a service that is already failing.
A client that keeps calling a dead dependency on every request therefore does the worst possible thing twice over: it
wastes its own capacity (threads or connections blocked on doomed calls, which can exhaust the client's own resources)
and it hammers the downstream just when the downstream most needs the traffic to stop so it can recover. During an
outage, the naive 'just retry the call' behavior turns a downstream failure into a client failure too.

A circuit breaker is a small state machine that sits in front of the dependency and stops calling it when it is clearly
down. It starts CLOSED (calls pass through). It counts consecutive failures, and after a threshold it trips OPEN: now
every call fails FAST -- it returns an error immediately without touching the downstream -- which protects both sides,
the client's resources and the failing service. After a cooldown it moves to HALF_OPEN and lets a single probe call
through: if the probe succeeds the dependency has recovered, so it closes; if the probe fails it re-opens for another
cooldown. So instead of attempting a dead service on every request, the breaker attempts it a handful of times (the
threshold plus one probe per cooldown) and fails everything else fast.

The trade-off is a small recovery latency: while OPEN, the breaker fails fast even after the dependency has quietly
recovered, until the next HALF_OPEN probe discovers it is back. That is the price of not hammering a failing service, and
it is why the cooldown is a tuning knob -- short enough to notice recovery promptly, long enough not to keep probing a
still-dead service.

On this fixture the dependency is down for 10 ticks then up for 5. A client with no breaker attempts the downstream on all
10 down ticks -- 10 wasted timeouts and 10 failed requests dumped on it. A client with a breaker (threshold 3, cooldown 5)
trips OPEN after 3 failures, fails the next requests fast, probes once at tick 7 (still down, re-opens), probes again at
tick 12 (recovered, closes) -- attempting the down service only 4 times total and fast-failing 8 requests. This computes
both.

  --timeline  the breaker's state at each tick -- CLOSED failures, the trip to OPEN, fast-fails, the HALF_OPEN probes, recovery
  --compare   downstream attempts and fast-fails: no breaker (10 attempts) vs breaker (4 attempts, 8 fast-fails)
  --check     the no-breaker client attempts the down service every tick; the breaker trips after the threshold, fails fast, and recovers

The health timeline and breaker settings are the fixture; every state and count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "breaker.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_no_breaker(health):
    """Attempt the downstream on every tick; count the attempts that hit a down service (each a wasted timeout)."""
    return sum(1 for h in health if h == "down")


def run_breaker(health, threshold, cooldown):
    """Simulate the CLOSED/OPEN/HALF_OPEN state machine, returning the per-tick trace and the attempt/fast-fail counts."""
    state = "CLOSED"
    failures = 0
    opened_at = None
    attempts_down = 0
    fast_fails = 0
    trace = []
    for t, h in enumerate(health):
        if state == "OPEN":
            if t - opened_at >= cooldown:
                state = "HALF_OPEN"
            else:
                fast_fails += 1
                trace.append((t, "OPEN", "fast-fail"))
                continue
        # CLOSED or HALF_OPEN: actually call the downstream
        if h == "up":
            state = "CLOSED"
            failures = 0
            trace.append((t, "->CLOSED", "call ok"))
        else:
            attempts_down += 1
            if state == "HALF_OPEN":
                state = "OPEN"
                opened_at = t
                trace.append((t, "HALF_OPEN", "probe failed -> OPEN"))
            else:
                failures += 1
                if failures >= threshold:
                    state = "OPEN"
                    opened_at = t
                    trace.append((t, "CLOSED", "fail #%d -> trip OPEN" % failures))
                else:
                    trace.append((t, "CLOSED", "fail #%d" % failures))
    return trace, attempts_down, fast_fails, state


# ----------------------------------------------------------------- printing

def timeline_view(data):
    health, thr, cd = data["health"], data["threshold"], data["cooldown"]
    trace, attempts, fast, final = run_breaker(health, thr, cd)
    print("TIMELINE — breaker state per tick (threshold %d, cooldown %d)" % (thr, cd))
    print("-" * 62)
    for t, state, note in trace:
        print("  tick %-2d  %-6s  %-10s  %s" % (t, health[t], state, note))
    print("-" * 62)
    print("  attempted the down service %d times; fast-failed %d; ended %s." % (attempts, fast, final))


def compare_view(data):
    health, thr, cd = data["health"], data["threshold"], data["cooldown"]
    nb = run_no_breaker(health)
    _, attempts, fast, _ = run_breaker(health, thr, cd)
    down_ticks = sum(1 for h in health if h == "down")
    print("COMPARE — downstream attempts during a %d-tick outage" % down_ticks)
    print("-" * 58)
    print("  no breaker : %d attempts to the down service (all %d wasted timeouts)" % (nb, down_ticks))
    print("  breaker    : %d attempts, %d requests failed fast (no downstream call)" % (attempts, fast))
    print("-" * 58)
    print("  the breaker cut load on the failing service from %d to %d." % (nb, attempts))


def check(data):
    print("SELF-TEST — the no-breaker client attempts the down service every tick; the breaker trips after the threshold, fails fast, and recovers")
    print("-" * 128)
    health, thr, cd = data["health"], data["threshold"], data["cooldown"]
    down_ticks = sum(1 for h in health if h == "down")

    nb = run_no_breaker(health)
    no_breaker_hits_all = nb == down_ticks
    print("  no-breaker attempts the down service on every down tick = %s (%d of %d)" % (no_breaker_hits_all, nb, down_ticks))

    trace, attempts, fast, final = run_breaker(health, thr, cd)
    breaker_attempts_fewer = attempts < nb
    print("  the breaker attempts the down service far fewer times = %s (%d < %d)" % (breaker_attempts_fewer, attempts, nb))

    trip_tick = next(t for t, s, note in trace if "trip OPEN" in note)
    trips_after_threshold = trip_tick == thr - 1
    print("  the breaker trips OPEN after exactly %d failures = %s (at tick %d)" % (thr, trips_after_threshold, trip_tick))

    fast_failed_some = fast > 0
    print("  some requests failed fast without calling the downstream = %s (%d)" % (fast_failed_some, fast))

    recovers_closed = final == "CLOSED"
    print("  the breaker closes again after the service recovers = %s (ended %s)" % (recovers_closed, final))

    ok = no_breaker_hits_all and breaker_attempts_fewer and trips_after_threshold and fast_failed_some and recovers_closed
    print("-" * 128)
    print("SELF-TEST %s  no_breaker_hits_all=%s  breaker_attempts_fewer=%s  trips_after_threshold=%s  fast_failed_some=%s  recovers_closed=%s"
          % ("PASS" if ok else "FAIL", no_breaker_hits_all, breaker_attempts_fewer, trips_after_threshold, fast_failed_some, recovers_closed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Circuit breaker: without one, a client calls a down dependency on every request, paying the full timeout each time and piling load onto the outage; a breaker trips OPEN after a threshold of consecutive failures to fail fast, probes HALF_OPEN after a cooldown, and closes on a successful probe -- turning many wasted timeouts into a few probes.")
    p.add_argument("--timeline", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("health=%s  threshold=%d  cooldown=%d  file=%s  (the timeline and settings are a fixture)"
          % (data["health"], data["threshold"], data["cooldown"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.timeline:
        timeline_view(data)
    elif args.compare:
        compare_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
