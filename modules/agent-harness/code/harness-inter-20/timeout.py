"""Put a timeout on each tool call, or one hung tool blocks the whole loop no iteration bound can rescue.

An agent loop has two ways to run forever, and they need two different guards. The first is an agent that keeps
STEPPING without making progress -- calling tools, reading results, calling more, never converging. The fix is a
loop-iteration bound with a no-progress check: after so many steps, or so many steps without advancing, stop.
The second is subtler and the iteration bound is blind to it: a single tool call that HANGS. A wedged
subprocess, a socket read with no deadline, an endpoint that accepts the request and never responds -- the call
never returns control to the loop, so the loop never gets to count an iteration, never runs its no-progress
check, never does anything. It is stuck inside one call, and no amount of loop-level bounding helps, because the
loop is not looping.

The guard for a hung call is a per-call timeout. Give every tool call a deadline; if it has not returned by then,
cancel it and hand the loop a timeout OBSERVATION -- an error result the agent can read and react to, exactly
like any other tool error -- instead of blocking. Now the worst a single call can cost is the timeout, the loop
regains control, and a wedged tool degrades into a recoverable error rather than a frozen agent. The effective
duration of any call becomes min(its real duration, the timeout), which bounds not just the hang but the whole
loop's wall-clock time.

On this fixture three tool calls take 2, 5, and 6 seconds and one hangs at 600. Without a timeout the loop waits
613 seconds -- dominated entirely by the hang. With an 8-second per-call timeout the fast calls finish untouched,
the hang is cancelled at 8, and the loop's total falls to 21 seconds. This computes both.

  --run        each call's real vs effective duration under a per-call timeout, and which get cancelled
  --total      the loop's wall-clock time with no timeout vs with the per-call timeout
  --check      the hang would block; the timeout caps each call; fast calls are untouched; only the hang is cut

The calls and timeout are the fixture; every duration is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "timeout.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def effective(secs, timeout):
    """A call under a per-call timeout runs for min(its duration, the timeout)."""
    return min(secs, timeout)


def timed_out(secs, timeout):
    """A call is cancelled (timed out) when its real duration exceeds the timeout."""
    return secs > timeout


def total_time(calls, timeout):
    """Loop wall-clock time. timeout=None means no per-call timeout (wait the full duration of each)."""
    return sum(c["secs"] if timeout is None else effective(c["secs"], timeout) for c in calls)


# ----------------------------------------------------------------- printing

def run_view(data):
    calls, t = data["calls"], data["timeout_s"]
    print("RUN — real vs effective duration under a %ds per-call timeout" % t)
    print("-" * 62)
    print("  call         real   effective   outcome")
    for c in calls:
        eff = effective(c["secs"], t)
        outcome = "TIMED OUT (observation)" if timed_out(c["secs"], t) else "completed"
        print("  %-11s  %4d   %4d        %s" % (c["id"], c["secs"], eff, outcome))
    print("-" * 62)
    print("  a call over the limit is cancelled and returns a timeout observation the loop can read.")


def total_view(data):
    calls, t = data["calls"], data["timeout_s"]
    without = total_time(calls, None)
    with_to = total_time(calls, t)
    print("TOTAL — loop wall-clock time with no timeout vs a %ds per-call timeout" % t)
    print("-" * 62)
    print("  no timeout:        %4d s   (the hang dominates)" % without)
    print("  per-call timeout:  %4d s   (worst call capped at %d)" % (with_to, t))
    print("-" * 62)
    print("  the timeout cuts the loop from %d s to %d s by bounding the one hung call." % (without, with_to))


def check(data):
    print("SELF-TEST — the hang would block; the timeout caps each call; fast calls untouched; only the hang is cut")
    print("-" * 104)
    calls, t = data["calls"], data["timeout_s"]
    hang = max(calls, key=lambda c: c["secs"])
    fast = [c for c in calls if c["secs"] <= t]

    hang_would_block = hang["secs"] > 10 * t
    print("  the hung call would block far past the timeout = %s (%d > %d)" % (hang_would_block, hang["secs"], 10 * t))

    timeout_caps_each = all(effective(c["secs"], t) <= t for c in calls)
    print("  every call's effective time is capped at the timeout = %s (max %d <= %d)" % (timeout_caps_each, max(effective(c["secs"], t) for c in calls), t))

    fast_calls_untouched = all(effective(c["secs"], t) == c["secs"] and not timed_out(c["secs"], t) for c in fast)
    print("  calls under the limit complete untouched = %s (%s)" % (fast_calls_untouched, [c["id"] for c in fast]))

    only_hang_times_out = [c["id"] for c in calls if timed_out(c["secs"], t)] == [hang["id"]]
    print("  exactly the hung call times out = %s" % only_hang_times_out)

    timeout_bounds_total = total_time(calls, t) < total_time(calls, None) and total_time(calls, t) <= len(calls) * t
    print("  the timeout bounds the loop's total time = %s (%d < %d, and <= %d*%d)" % (timeout_bounds_total, total_time(calls, t), total_time(calls, None), len(calls), t))

    ok = hang_would_block and timeout_caps_each and fast_calls_untouched and only_hang_times_out and timeout_bounds_total
    print("-" * 104)
    print("SELF-TEST %s  hang_would_block=%s  timeout_caps_each=%s  fast_calls_untouched=%s  only_hang_times_out=%s  timeout_bounds_total=%s"
          % ("PASS" if ok else "FAIL", hang_would_block, timeout_caps_each, fast_calls_untouched, only_hang_times_out, timeout_bounds_total))
    return ok


def main():
    p = argparse.ArgumentParser(description="A per-call timeout cancels a hung tool call and returns a timeout observation, which the loop-iteration bound cannot do.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--total", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  timeout_s=%d  longest=%ds  file=%s  (the calls are a fixture)"
          % (len(data["calls"]), data["timeout_s"], max(c["secs"] for c in data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.total:
        total_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
